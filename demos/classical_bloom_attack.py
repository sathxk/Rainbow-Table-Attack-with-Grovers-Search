#!/usr/bin/env python3
"""
Memory-Efficient Classical Rainbow Table Attack with Bloom Filter

Reads hashes from a file and cracks each one using Bloom filter + direct SQL query.
Reports: hash, password found, and time taken.

This demonstrates a memory-efficient classical approach that uses the same
memory footprint as the quantum attack (65.6 MB) but with traditional rainbow
table direct endpoint lookup O(1) instead of Grover's O(√N).

Usage:
    python examples/classical_bloom_attack.py [--hashes hashes.txt]
"""

import argparse
import sqlite3
import time
import sys
sys.path.insert(0, '.')

from rainbow_table_generator.config import load_config
from rainbow_table_generator.hash_functions import hash_factory
from attack.bloom_filter import BloomFilter
from attack.classical_bloom_attack import ClassicalBloomAttack
from attack.classical_attack import load_hashes


def load_db_metadata(db_path: str, fallback_qubits: int = 10):
    """Load metadata from database, with fallback for legacy databases."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if metadata table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")
    if cursor.fetchone() is None:
        # Legacy database - derive metadata from actual data
        cursor.execute("SELECT COUNT(DISTINCT bucket_key) FROM chains")
        num_buckets = cursor.fetchone()[0]
        conn.close()
        return {"num_buckets": str(num_buckets)}
    
    cursor.execute("SELECT key, value FROM metadata")
    metadata = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return metadata


parser = argparse.ArgumentParser(description="Memory-efficient classical rainbow table attack")
parser.add_argument("--hashes", default="hashes.txt", help="Path to hashes file")
args = parser.parse_args()

print("=" * 90)
print("  MEMORY-EFFICIENT CLASSICAL ATTACK (Bloom Filter + Direct SQL Query)")
print("=" * 90)

# Load configuration
config = load_config("config.json")
hash_func = hash_factory(config.hash_algorithm)
db_path = "rainbow_tables/output/rainbow_table.db"

# Load database metadata
print(f"\n[*] Loading database metadata from {db_path}")
metadata = load_db_metadata(db_path)
num_buckets = int(metadata.get("num_buckets", 49851))
print(f"[+] Num buckets: {num_buckets:,}")

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
print(f"[*] Initializing memory-efficient classical attack...")
attack = ClassicalBloomAttack(
    config=config,
    db_path=db_path,
    num_buckets=num_buckets,
    bloom_filter=bloom
)
print(f"[+] Memory usage: {attack.memory_mb:.1f} MB (Bloom filter only)")

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
print(f"  SUMMARY")
print(f"{'='*80}")
print(f"  Success rate:      {found}/{total} ({100*found/total:.1f}%)")
print(f"  Total time:        {total_time:.3f}s")
print(f"  Average time:      {avg_time:.3f}s per hash")
print(f"  Throughput:        {total/total_time:.2f} hashes/second")
print(f"  Memory usage:      {attack.memory_mb:.1f} MB")
print(f"{'='*80}\n")
