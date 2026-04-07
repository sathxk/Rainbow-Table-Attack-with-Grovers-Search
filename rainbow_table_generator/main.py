"""
Main orchestration module for rainbow table generation.

This module provides the RainbowTableGenerator class that coordinates all
components (config, hash functions, reduction, chain generation, bucket
organization, storage, and progress logging) to generate rainbow tables
from PCFG wordsets.
"""

import logging
import time
from pathlib import Path
from typing import Optional

from rainbow_table_generator.config import Config, load_config, validate_config
from rainbow_table_generator.hash_functions import hash_factory, HashFunction
from rainbow_table_generator.reduction import reduce
from rainbow_table_generator.chain_generator import ChainGenerator
from rainbow_table_generator.bucket_organizer import BucketOrganizer
from rainbow_table_generator.storage import StorageManager
from rainbow_table_generator.progress import ProgressLogger
from rainbow_table_generator.utils import stream_wordset, count_wordset_lines


class RainbowTableGenerator:
    """
    Main orchestration class for rainbow table generation.
    
    The RainbowTableGenerator coordinates all components of the rainbow table
    generation system. It initializes the configuration, hash functions,
    reduction functions, chain generator, bucket organizer, storage manager,
    and progress logger. It provides the main generate() method that orchestrates
    the entire rainbow table construction process.
    
    The generator processes passwords from a PCFG wordset file, generates
    hash-reduction chains, organizes them into buckets for quantum search,
    and writes the results to disk with checkpointing for recovery.
    
    Attributes:
        config: Configuration object with all generation parameters
        hash_function: Hash function instance for computing password hashes
        chain_generator: Chain generator for creating hash-reduction chains
        bucket_organizer: Bucket organizer for distributing SP-EP pairs
        storage_manager: Storage manager for file I/O operations
        progress_logger: Progress logger for tracking and reporting progress
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the RainbowTableGenerator with configuration.

        This method loads the configuration from the specified file path,
        validates it, and initializes all required components for rainbow
        table generation. The components are initialized but not yet used;
        the actual generation process is triggered by calling generate().

        Components initialized:
        - Configuration: Loaded from file and validated
        - Hash Function: Instantiated based on configured algorithm
        - Bucket Organizer: Initialized with qubit count for bucket sizing
        - Storage Manager: Initialized with output directory and retry settings

        Components deferred to generate():
        - Chain Generator: Requires password_length from wordset file
        - Progress Logger: Requires total_chains count from wordset file

        Args:
            config_path: Path to the configuration file (JSON or YAML)

        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the configuration is invalid
            IOError: If output directory cannot be created or is not writable

        Example:
            >>> generator = RainbowTableGenerator("config.json")
            >>> generator.generate()
        """
        # Load and validate configuration
        self.config = load_config(config_path)
        validate_config(self.config)

        # Initialize hash function based on configured algorithm
        self.hash_function: HashFunction = hash_factory(self.config.hash_algorithm)

        # Count total entries for bucket calculation
        # Note: BucketOrganizer initialization is deferred until we know total_entries
        self.bucket_organizer: Optional[BucketOrganizer] = None

        # Initialize storage manager with output directory and retry settings
        self.storage_manager = StorageManager(
            output_directory=self.config.output_directory,
            max_retries=self.config.max_retries
        )

        # Initialize output directory structure (buckets/, checkpoints/, logs/)
        # This ensures the directory exists and is writable before generation starts
        self.storage_manager.initialize_output_directory()

        # Initialize progress logger for configuration logging
        # We'll create a temporary logger just for startup logging
        # The actual progress logger will be created in generate() with total_chains
        import logging
        startup_logger = logging.getLogger("RainbowTableGenerator.Startup")
        startup_logger.setLevel(getattr(logging, self.config.log_level.upper(), logging.INFO))

        # Clear any existing handlers
        startup_logger.handlers.clear()

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.log_level.upper(), logging.INFO))
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        startup_logger.addHandler(console_handler)

        # Log the active configuration at startup (Requirement 7.5)
        startup_logger.info("Rainbow Table Generator initialized")
        startup_logger.info(f"Configuration loaded from: {config_path}")
        startup_logger.info(f"Hash algorithm: {self.config.hash_algorithm}")
        startup_logger.info(f"Chain length: {self.config.chain_length}")
        startup_logger.info(f"Qubit count: {self.config.qubit_count} (bucket size: {2**self.config.qubit_count})")
        startup_logger.info(f"Input wordset: {self.config.input_wordset_path}")
        startup_logger.info(f"Output directory: {self.config.output_directory}")
        startup_logger.info(f"Checkpoint interval: {self.config.checkpoint_interval} chains")
        startup_logger.info(f"Flush interval: {self.config.flush_interval} chains")
        startup_logger.info(f"Log level: {self.config.log_level}")

        # Components that will be initialized during generate()
        # These require information from the wordset file
        self.chain_generator: Optional[ChainGenerator] = None  # Needs password_length
        self.progress_logger: Optional[ProgressLogger] = None  # Needs total_chains

    
    def __repr__(self) -> str:
        """Return string representation of RainbowTableGenerator."""
        return (
            f"RainbowTableGenerator("
            f"config={self.config!r})"
        )
    
    def generate(self) -> None:
        """
        Generate the rainbow table from the configured wordset.
        
        This method orchestrates the entire rainbow table generation process:
        1. Load configuration and initialize components
        2. Check for existing checkpoint and resume if found
        3. Stream wordset and generate chains
        4. Assign chains to buckets
        5. Flush buckets to disk periodically
        6. Save checkpoints every N chains
        7. Write final metadata and index files
        
        The implementation of this method will be completed in subsequent tasks
        (Task 10.3).
        
        Raises:
            FileNotFoundError: If the wordset file doesn't exist
            IOError: If there are file I/O errors
            RuntimeError: If generation fails
        """
        from rainbow_table_generator.reduction import reduce
        from datetime import datetime, UTC
        
        # Sub-task 10.3.1: Load configuration (count wordset for progress tracking)
        try:
            total_chains = count_wordset_lines(self.config.input_wordset_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Input wordset file not found: {self.config.input_wordset_path}"
            ) from e
        except IOError as e:
            raise IOError(
                f"Failed to read wordset file: {self.config.input_wordset_path}"
            ) from e
        
        # Determine password length from config (assuming it's in the filename or we read first line)
        # For now, we'll read the first valid password to determine length
        password_length = None
        try:
            with open(self.config.input_wordset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    password = line.strip()
                    if password:
                        password_length = len(password)
                        break
        except Exception as e:
            raise RuntimeError(f"Failed to determine password length: {e}") from e
        
        if password_length is None:
            raise RuntimeError("Wordset file is empty or contains no valid passwords")
        
        # Sub-task 10.3.2: Initialize remaining components
        # Initialize bucket organizer with qubit count and total entries
        self.bucket_organizer = BucketOrganizer(
            qubit_count=self.config.qubit_count,
            total_entries=total_chains
        )
        
        # Initialize chain generator with password length
        self.chain_generator = ChainGenerator(
            hash_function=self.hash_function,
            chain_length=self.config.chain_length,
            password_length=password_length
        )
        
        # Initialize progress logger with total chains and log file
        log_file = str(self.storage_manager.logs_dir / "generation.log")
        self.progress_logger = ProgressLogger(
            total_chains=total_chains,
            log_interval=10000,
            log_file=log_file,
            log_level=self.config.log_level
        )
        
        # Start progress tracking
        self.progress_logger.start()
        self.progress_logger.log_start(
            hash_algorithm=self.config.hash_algorithm,
            chain_length=self.config.chain_length,
            qubit_count=self.config.qubit_count,
            input_file=self.config.input_wordset_path,
            output_directory=self.config.output_directory
        )
        
        # Sub-task 10.3.3: Check for existing checkpoint and resume if found
        checkpoint = self.storage_manager.load_checkpoint()
        
        if checkpoint:
            chains_processed = checkpoint["chains_processed"]
            last_start_point = checkpoint["last_start_point"]
            bucket_counts = checkpoint["bucket_counts"]
            
            self.progress_logger.log_info(
                f"Resuming from checkpoint: {chains_processed:,} chains already processed"
            )
            self.progress_logger.log_info(f"Last start point: {last_start_point}")
            
            # Restore bucket counts
            for bucket_idx, count in bucket_counts.items():
                # Note: We don't restore the actual SP-EP pairs to memory,
                # they're already on disk. We just track the counts.
                pass
            
            # Use resume_from_checkpoint to skip already processed passwords
            from rainbow_table_generator.utils import resume_from_checkpoint
            wordset_stream = resume_from_checkpoint(
                self.config.input_wordset_path,
                password_length,
                last_start_point
            )
        else:
            chains_processed = 0
            bucket_counts = {}
            wordset_stream = stream_wordset(
                self.config.input_wordset_path,
                password_length
            )
        
        # Track generation start time for metadata
        generation_start_time = self.progress_logger.start_time
        
        # Sub-task 10.3.4: Stream wordset and generate chains
        # Sub-task 10.3.5: Assign chains to buckets
        # Sub-task 10.3.6: Flush buckets to disk periodically
        # Sub-task 10.3.7: Save checkpoints every checkpoint_interval chains
        
        last_start_point = None
        
        try:
            for start_point in wordset_stream:
                last_start_point = start_point
                
                try:
                    # Generate hash-reduction chain
                    sp, final_password = self.chain_generator.generate_chain(start_point, reduce)
                    
                    # The endpoint is the hash of the final password (as hex string)
                    ep_bytes = self.hash_function.hash(final_password)
                    ep = ep_bytes.hex()
                    
                    # Assign chain to bucket
                    self.bucket_organizer.add_to_bucket(sp, ep)
                    
                    # Increment chains processed
                    chains_processed += 1
                    
                    # Update bucket counts
                    bucket_key = self.bucket_organizer.assign_bucket(ep)
                    bucket_counts[bucket_key] = bucket_counts.get(bucket_key, 0) + 1
                    
                    # Sub-task 10.3.6: Flush buckets to disk periodically
                    if chains_processed % self.config.flush_interval == 0:
                        self._flush_buckets_to_disk()
                    
                    # Sub-task 10.3.7: Save checkpoints every checkpoint_interval chains
                    if chains_processed % self.config.checkpoint_interval == 0:
                        # Commit all pending SQLite transactions
                        self.storage_manager.commit()
                        
                        self.storage_manager.save_checkpoint(
                            chains_processed=chains_processed,
                            last_start_point=last_start_point,
                            bucket_counts=bucket_counts
                        )
                        self.progress_logger.log_checkpoint(chains_processed)
                    
                    # Log progress at regular intervals
                    if self.progress_logger.should_log(chains_processed):
                        self.progress_logger.log_progress(chains_processed)
                
                except Exception as e:
                    # Requirement 9.3: If a chain generation fails, log and continue
                    self.progress_logger.log_warning(
                        f"Failed to generate chain for '{start_point}': {str(e)}"
                    )
                    continue
        
        except KeyboardInterrupt:
            # Handle graceful shutdown on Ctrl+C
            self.progress_logger.log_warning("Generation interrupted by user")
            self.progress_logger.log_info("Saving checkpoint before exit...")
            
            # Flush remaining buckets
            self._flush_buckets_to_disk()
            
            # Commit pending transactions
            self.storage_manager.commit()
            
            # Save final checkpoint
            if last_start_point:
                self.storage_manager.save_checkpoint(
                    chains_processed=chains_processed,
                    last_start_point=last_start_point,
                    bucket_counts=bucket_counts
                )
            
            raise
        
        # Flush any remaining bucket data to disk
        self._flush_buckets_to_disk()
        
        # Commit all pending transactions
        self.storage_manager.commit()
        
        # Calculate generation statistics
        generation_end_time = time.time()
        generation_time_seconds = generation_end_time - generation_start_time
        average_rate = chains_processed / generation_time_seconds if generation_time_seconds > 0 else 0
        
        # Sub-task 10.3.8: Write final metadata and index files
        
        # Get actual bucket count from database
        actual_bucket_count = self.storage_manager.get_bucket_count()
        
        # Write metadata.json
        from rainbow_table_generator.reduction import CHARSET
        self.storage_manager.write_metadata(
            hash_algorithm=self.config.hash_algorithm,
            chain_length=self.config.chain_length,
            qubit_count=self.config.qubit_count,
            bucket_count=actual_bucket_count,
            num_buckets=self.bucket_organizer.num_buckets,
            password_length=password_length,
            charset=CHARSET,
            reduction_function="iteration_dependent_v1",
            generation_timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            total_chains=chains_processed,
            generation_time_seconds=generation_time_seconds
        )
        
        # Write index.json
        # Query SQLite for bucket statistics
        cursor = self.storage_manager.conn.execute("""
            SELECT bucket_key, COUNT(*) as entry_count
            FROM chains
            GROUP BY bucket_key
            ORDER BY bucket_key
        """)
        
        bucket_info = []
        for bucket_key, entry_count in cursor.fetchall():
            bucket_info.append({
                "bucket_key": bucket_key,
                "entry_count": entry_count
            })
        
        self.storage_manager.write_index(bucket_info)
        
        # Log final summary
        self.progress_logger.log_summary(
            total_chains=chains_processed,
            total_buckets=actual_bucket_count,
            generation_time_seconds=generation_time_seconds,
            average_rate=average_rate
        )
    
    def _flush_buckets_to_disk(self) -> None:
        """
        Flush all bucket buffers to disk and clear memory.

        Iterates over all active bucket keys, writes their buffered entries
        to the corresponding CSV file, then clears the in-memory buffer.

        Raises:
            IOError: If writing to disk fails after all retry attempts
        """
        for bucket_key in self.bucket_organizer.all_bucket_keys():
            entries = self.bucket_organizer.get_bucket(bucket_key)
            if entries:
                self.storage_manager.write_bucket(
                    bucket_key=bucket_key,
                    entries=entries,
                    mode='a'
                )
                self.bucket_organizer.clear_bucket(bucket_key)
    def generate_parallel(self, num_workers: int = None) -> None:
        """
        Generate rainbow table using parallel processing.

        Args:
            num_workers: Number of worker processes (defaults to CPU count - 2)
        """
        import multiprocessing as mp
        from rainbow_table_generator.parallel import worker_process, partition_wordset
        from rainbow_table_generator.reduction import CHARSET
        from datetime import datetime, UTC

        if num_workers is None:
            num_workers = max(1, mp.cpu_count() - 2)

        # Count total chains and determine password length
        try:
            total_chains = count_wordset_lines(self.config.input_wordset_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Input wordset file not found: {self.config.input_wordset_path}") from e

        password_length = None
        with open(self.config.input_wordset_path, 'r', encoding='utf-8') as f:
            for line in f:
                password = line.strip()
                if password:
                    password_length = len(password)
                    break

        if password_length is None:
            raise RuntimeError("Wordset file is empty")

        # Initialize bucket organizer with total entries
        self.bucket_organizer = BucketOrganizer(
            qubit_count=self.config.qubit_count,
            total_entries=total_chains
        )

        # Initialize progress logger
        log_file = str(self.storage_manager.logs_dir / "generation.log")
        self.progress_logger = ProgressLogger(
            total_chains=total_chains,
            log_interval=10000,
            log_file=log_file,
            log_level=self.config.log_level
        )

        self.progress_logger.start()
        self.progress_logger.log_start(
            hash_algorithm=self.config.hash_algorithm,
            chain_length=self.config.chain_length,
            qubit_count=self.config.qubit_count,
            input_file=self.config.input_wordset_path,
            output_directory=self.config.output_directory
        )
        self.progress_logger.log_info(f"Starting parallel generation with {num_workers} workers")

        generation_start_time = self.progress_logger.start_time

        # Partition wordset
        self.progress_logger.log_info("Partitioning wordset across workers...")
        partitions = partition_wordset(self.config.input_wordset_path, password_length, num_workers)
        self.progress_logger.log_info(f"Created {len(partitions)} partitions")

        # Create queues
        result_queue = mp.Queue(maxsize=1000)
        progress_queue = mp.Queue()

        # Start workers
        workers = []
        for worker_id in range(num_workers):
            p = mp.Process(
                target=worker_process,
                args=(
                    worker_id,
                    partitions[worker_id],
                    self.config.hash_algorithm,
                    self.config.chain_length,
                    password_length,
                    self.bucket_organizer.num_buckets,
                    self.bucket_organizer.bucket_size,
                    result_queue,
                    progress_queue
                )
            )
            p.start()
            workers.append(p)

        self.progress_logger.log_info(f"Started {num_workers} worker processes")

        # Process results from workers
        workers_done = 0
        chains_processed = 0
        bucket_counts = {}

        while workers_done < num_workers:
            try:
                msg_type, data = result_queue.get(timeout=0.1)

                if msg_type == 'chains':
                    bucket_groups = {}
                    for bucket_key, sp, ep, intra_value in data:
                        if bucket_key not in bucket_groups:
                            bucket_groups[bucket_key] = []
                        bucket_groups[bucket_key].append((sp, ep, intra_value))
                        bucket_counts[bucket_key] = bucket_counts.get(bucket_key, 0) + 1

                    for bucket_key, entries in bucket_groups.items():
                        self.storage_manager.write_bucket(bucket_key, entries, commit=False)

                    chains_processed += len(data)

                    if chains_processed % self.config.checkpoint_interval == 0:
                        self.storage_manager.commit()
                        self.storage_manager.save_checkpoint(
                            chains_processed=chains_processed,
                            last_start_point="parallel_mode",
                            bucket_counts=bucket_counts
                        )
                        self.progress_logger.log_checkpoint(chains_processed)

                    if self.progress_logger.should_log(chains_processed):
                        self.progress_logger.log_progress(chains_processed)

                elif msg_type == 'done':
                    workers_done += 1
                    self.progress_logger.log_info(f"Worker {data} completed")

                elif msg_type == 'error':
                    self.progress_logger.log_error(data)

            except Exception:
                pass

        for p in workers:
            p.join()

        # Final commit
        self.storage_manager.commit()

        generation_end_time = time.time()
        generation_time_seconds = generation_end_time - generation_start_time
        average_rate = chains_processed / generation_time_seconds if generation_time_seconds > 0 else 0
        actual_bucket_count = self.storage_manager.get_bucket_count()

        self.storage_manager.write_metadata(
            hash_algorithm=self.config.hash_algorithm,
            chain_length=self.config.chain_length,
            qubit_count=self.config.qubit_count,
            bucket_count=actual_bucket_count,
            num_buckets=self.bucket_organizer.num_buckets,
            password_length=password_length,
            charset=CHARSET,
            reduction_function="iteration_dependent_v1",
            generation_timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            total_chains=chains_processed,
            generation_time_seconds=generation_time_seconds
        )

        cursor = self.storage_manager.conn.execute("""
            SELECT bucket_key, COUNT(*) as entry_count
            FROM chains GROUP BY bucket_key ORDER BY bucket_key
        """)
        bucket_info = [{"bucket_key": k, "entry_count": c} for k, c in cursor.fetchall()]
        self.storage_manager.write_index(bucket_info)

        self.progress_logger.log_summary(
            total_chains=chains_processed,
            total_buckets=actual_bucket_count,
            generation_time_seconds=generation_time_seconds,
            average_rate=average_rate
        )


def main():
    """
    Command-line interface for the Rainbow Table Generator.
    
    This function provides a CLI for generating and validating rainbow tables.
    It supports the following operations:
    - Generate a new rainbow table from a wordset
    - Resume generation from a checkpoint
    - Validate an existing rainbow table
    
    Command-line arguments:
        --config: Path to configuration file (required for generation)
        --resume: Resume from checkpoint if available (optional)
        --validate: Validate existing rainbow table instead of generating (optional)
    
    Examples:
        # Generate a new rainbow table
        python -m rainbow_table_generator.main --config config.json
        
        # Resume from checkpoint
        python -m rainbow_table_generator.main --config config.json --resume
        
        # Validate existing table
        python -m rainbow_table_generator.main --validate rainbow_tables/len8/
    
    Exit codes:
        0: Success
        1: Configuration error
        2: File I/O error
        3: Validation error
        4: Runtime error
    """
    import argparse
    import sys
    
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Rainbow Table Generator - Generate rainbow tables from PCFG wordsets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a new rainbow table
  python -m rainbow_table_generator.main --config config.json
  
  # Resume from checkpoint
  python -m rainbow_table_generator.main --config config.json --resume
  
  # Validate existing table
  python -m rainbow_table_generator.main --validate rainbow_tables/len8/
        """
    )
    
    # Sub-task 10.4.1: Add --config argument for config file path
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file (JSON or YAML). Required for generation mode.',
        metavar='PATH'
    )
    
    # Sub-task 10.4.2: Add --resume flag for checkpoint resumption
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume generation from checkpoint if available. Requires --config.'
    )
    
    # Sub-task 10.4.3: Add --validate flag for validation mode
    parser.add_argument(
        '--validate',
        type=str,
        help='Validate existing rainbow table at specified directory instead of generating.',
        metavar='DIRECTORY'
    )
    
    # Add --workers argument for parallel processing
    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of worker processes for parallel generation (default: CPU count - 2)',
        metavar='N'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Validate argument combinations
    if args.validate:
        # Validation mode
        if args.config or args.resume:
            parser.error("--validate cannot be used with --config or --resume")
        
        # TODO: Implement validation mode (Task 11)
        print(f"Validation mode not yet implemented. Would validate: {args.validate}")
        sys.exit(3)
    
    else:
        # Generation mode
        if not args.config:
            parser.error("--config is required for generation mode")
        
        try:
            # Initialize generator
            generator = RainbowTableGenerator(config_path=args.config)
            
            # Note: The --resume flag is informational only
            # The generator automatically detects and resumes from checkpoints
            # (progress_logger is initialized inside generate(), so we can't log here)
            
            # Generate rainbow table (parallel or sequential)
            if args.workers and args.workers > 1:
                generator.generate_parallel(num_workers=args.workers)
            else:
                generator.generate()
            
            print("\nRainbow table generation completed successfully!")
            sys.exit(0)
        
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(2)
        
        except ValueError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)
        
        except IOError as e:
            print(f"I/O error: {e}", file=sys.stderr)
            sys.exit(2)
        
        except KeyboardInterrupt:
            print("\nGeneration interrupted by user", file=sys.stderr)
            sys.exit(130)  # Standard exit code for SIGINT
        
        except Exception as e:
            print(f"Runtime error: {e}", file=sys.stderr)
            sys.exit(4)


if __name__ == "__main__":
    main()
