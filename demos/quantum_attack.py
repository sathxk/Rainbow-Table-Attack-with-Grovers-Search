#!/usr/bin/env python3
"""
Quantum Rainbow Table Attack

Reads hashes from hashes.txt and cracks each one using Grover's search.
Reports: hash, password found, chain position, and time taken.

Usage:
    python examples/quantum_attack.py [--qubits 8|10|12]
"""

import argparse
import sqlite3
import time
import sys
sys.path.insert(0, '.')

from rainbow_table_generator.config import load_config
from rainbow_table_generator.hash_functions import hash_factory
from attack.bloom_filter import BloomFilter
from attack.orchestrator import RainbowAttack
from attack.classical_attack import load_hashes


def load_db_metadata(db_path: str, fallback_qubits: int = 10):
    """Load metadata from database, with fallback for legacy databases."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if metadata table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")
    if cursor.fetchone() is None:
        # Legacy database - derive metadata from actual data
        cursor.execute("SELECT COUNT(*) FROM chains")
        total_chains = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(DISTINCT bucket_key) FROM chains")
        num_buckets = cursor.fetchone()[0]
        conn.close()
        import math
        bucket_size = 2 ** fallback_qubits
        grover_iterations = max(1, math.floor((math.pi / 4) * math.sqrt(bucket_size)))
        return {
            "qubit_count": str(fallback_qubits),
            "bucket_size": str(bucket_size),
            "num_buckets": str(num_buckets),
            "grover_iterations": str(grover_iterations),
            "total_chains": str(total_chains),
        }
    
    cursor.execute("SELECT key, value FROM metadata")
    metadata = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return metadata


def main():
    parser = argparse.ArgumentParser(description="Quantum rainbow table attack")
    parser.add_argument("--qubits", type=int, default=10, choices=[8, 10, 12, 14],
                        help="Qubit configuration (8, 10, 12, or 14)")
    parser.add_argument("--hashes", default="hashes.txt", help="Path to hashes file")
    parser.add_argument("--use-dega", action="store_true",
                        help="Use DEGA (Distributed Exact Grover) instead of standard Grover (6-100× faster)")
    args = parser.parse_args()
    
    # Determine database path
    if args.qubits == 10:
        db_path = "rainbow_tables/output/rainbow_table.db"
    else:
        db_path = f"rainbow_tables/output/rainbow_table_{args.qubits}q.db"
    
    print("=" * 90)
    algorithm_name = "DEGA (Distributed Exact Grover)" if args.use_dega else "Grover's Search"
    print(f"  QUANTUM RAINBOW TABLE ATTACK ({algorithm_name}) - {args.qubits} Qubits")
    print("=" * 90)
    
    # Load database metadata
    print(f"\n[*] Loading database metadata from {db_path}")
    metadata = load_db_metadata(db_path, fallback_qubits=args.qubits)
    qubit_count = int(metadata.get("qubit_count", args.qubits))
    num_buckets = int(metadata.get("num_buckets", 0))
    bucket_size = int(metadata.get("bucket_size", 2**qubit_count))
    grover_iterations = int(metadata.get("grover_iterations", 0))
    
    print(f"[+] Database configuration:")
    print(f"    Qubit count:       {qubit_count}")
    print(f"    Bucket size:       {bucket_size:,} (2^{qubit_count})")
    print(f"    Num buckets:       {num_buckets:,}")
    print(f"    Grover iterations: {grover_iterations}")
    
    # Load configuration
    config = load_config("config.json")
    # Override qubit_count from database
    config.qubit_count = qubit_count
    hash_func = hash_factory(config.hash_algorithm)
    
    # Load hashes
    hashes = load_hashes(args.hashes)
    print(f"\n[*] Loaded {len(hashes)} hashes from {args.hashes}")
    
    # Load Bloom filter
    print(f"[*] Loading Bloom filter...")
    t0 = time.perf_counter()
    bloom = BloomFilter.load("bloom_filter.bin", "bloom_filter.json")
    print(f"[+] Bloom filter loaded in {time.perf_counter()-t0:.2f}s "
          f"({bloom.count:,} items, {bloom.memory_bytes/1024/1024:.1f} MB)")
    
    # Initialize attack
    print(f"[*] Initializing quantum attack...")
    attack = RainbowAttack(
        config=config,
        db_path=db_path,
        num_buckets=num_buckets,
        bloom_filter=bloom,
        use_dega=args.use_dega  # Pass DEGA flag
    )

    # Run attack
    print(f"\n{'='*80}")
    print(f"{'#':<4} {'Hash':<42} {'Password':<12} {'Time'}")
    print("=" * 80)
    
    results = []
    for i, target_hash in enumerate(hashes, 1):
        t0 = time.perf_counter()
        password = attack.crack(target_hash, verbose=False)
        elapsed = time.perf_counter() - t0
        
        if password:
            results.append((password, elapsed, True))
            print(f"{i:<4} {target_hash:<42} {password:<12} {elapsed:.3f}s  ✓")
        else:
            results.append((None, elapsed, False))
            print(f"{i:<4} {target_hash:<42} {'NOT FOUND':<12} {elapsed:.3f}s  ✗")
    
    print("=" * 80)
    
    # Summary
    found = sum(1 for _, _, success in results if success)
    total = len(results)
    total_time = sum(t for _, t, _ in results)
    avg_time = total_time / total if total > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"  SUMMARY - {args.qubits} Qubits")
    print(f"{'='*80}")
    print(f"  Success rate:      {found}/{total} ({100*found/total:.1f}%)")
    print(f"  Total time:        {total_time:.3f}s")
    print(f"  Average time:      {avg_time:.3f}s per hash")
    print(f"  Throughput:        {total/total_time:.2f} hashes/second")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
