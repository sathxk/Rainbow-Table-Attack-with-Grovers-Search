"""
Parallel chain generation module for rainbow table generation.

This module provides multiprocessing support to generate chains in parallel
across multiple CPU cores, significantly improving generation speed.
"""

import multiprocessing as mp
from typing import List, Tuple, Optional
from queue import Empty

from rainbow_table_generator.hash_functions import hash_factory
from rainbow_table_generator.reduction import reduce
from rainbow_table_generator.chain_generator import ChainGenerator


def worker_process(
    worker_id: int,
    passwords: List[str],
    hash_algorithm: str,
    chain_length: int,
    password_length: int,
    num_buckets: int,
    bucket_size: int,
    result_queue: mp.Queue,
    progress_queue: mp.Queue
) -> None:
    """
    Worker process that generates chains from a list of passwords.
    
    Args:
        worker_id: Unique identifier for this worker
        passwords: List of start point passwords to process
        hash_algorithm: Hash algorithm to use (md5, sha1, sha256)
        chain_length: Number of hash-reduce iterations
        password_length: Length of passwords
        num_buckets: Total number of buckets
        bucket_size: Size of each bucket (2^N)
        result_queue: Queue to send completed chains
        progress_queue: Queue to send progress updates
    """
    try:
        # Initialize hash function and chain generator
        hash_func = hash_factory(hash_algorithm)
        chain_gen = ChainGenerator(hash_func, chain_length, password_length)
        
        batch = []
        batch_size = 100  # Send results in batches of 100
        
        for i, start_point in enumerate(passwords):
            try:
                # Generate chain
                sp, final_password = chain_gen.generate_chain(start_point, reduce)
                
                # Hash the final password to get the endpoint
                ep_bytes = hash_func.hash(final_password)
                ep = ep_bytes.hex()
                
                # Calculate bucket assignment using hash directly
                hash_value = int(ep[:8], 16)
                bucket_key = hash_value % num_buckets
                intra_value = hash_value % bucket_size
                
                # Add to batch
                batch.append((bucket_key, sp, ep, intra_value))
                
                # Send batch when full
                if len(batch) >= batch_size:
                    result_queue.put(('chains', batch))
                    progress_queue.put(('progress', len(batch)))
                    batch = []
                
            except Exception as e:
                # Log error and continue
                progress_queue.put(('error', f"Worker {worker_id}: Failed chain for '{start_point}': {e}"))
                continue
        
        # Send remaining batch
        if batch:
            result_queue.put(('chains', batch))
            progress_queue.put(('progress', len(batch)))
        
        # Signal completion
        result_queue.put(('done', worker_id))
        
    except Exception as e:
        result_queue.put(('error', f"Worker {worker_id} crashed: {e}"))


def writer_process(
    result_queue: mp.Queue,
    storage_manager,
    num_workers: int,
    commit_interval: int
) -> None:
    """
    Writer process that receives chains from workers and writes to SQLite.
    
    Args:
        result_queue: Queue to receive chains from workers
        storage_manager: StorageManager instance
        num_workers: Number of worker processes
        commit_interval: Number of chains between commits
    """
    workers_done = 0
    chains_written = 0
    
    while workers_done < num_workers:
        try:
            msg_type, data = result_queue.get(timeout=1.0)
            
            if msg_type == 'chains':
                # data is a list of (bucket_key, sp, ep, intra_value)
                # Group by bucket_key for writing
                bucket_groups = {}
                for bucket_key, sp, ep, intra_value in data:
                    if bucket_key not in bucket_groups:
                        bucket_groups[bucket_key] = []
                    bucket_groups[bucket_key].append((sp, ep, intra_value))
                
                # Write each bucket group
                for bucket_key, entries in bucket_groups.items():
                    storage_manager.write_bucket(bucket_key, entries, commit=False)
                
                chains_written += len(data)
                
                # Commit periodically
                if chains_written % commit_interval == 0:
                    storage_manager.commit()
            
            elif msg_type == 'done':
                workers_done += 1
            
            elif msg_type == 'error':
                print(f"Error: {data}")
        
        except Empty:
            continue
    
    # Final commit
    storage_manager.commit()


def partition_wordset(filepath: str, password_length: int, num_partitions: int) -> List[List[str]]:
    """
    Partition wordset file into chunks for parallel processing.
    
    Args:
        filepath: Path to wordset file
        password_length: Expected password length
        num_partitions: Number of partitions to create
    
    Returns:
        List of password lists, one per partition
    """
    from rainbow_table_generator.utils import stream_wordset
    
    partitions = [[] for _ in range(num_partitions)]
    
    for i, password in enumerate(stream_wordset(filepath, password_length)):
        partition_idx = i % num_partitions
        partitions[partition_idx].append(password)
    
    return partitions
