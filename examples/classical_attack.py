#!/usr/bin/env python3
"""
Classical Rainbow Table Attack

Reads hashes from hashes.txt and cracks each one using hash table lookup.
Reports: hash, password found, chain position, and time taken.
"""

import time
import sys
sys.path.insert(0, '.')

from rainbow_table_generator.config import load_config
from rainbow_table_generator.hash_functions import hash_factory
from attack.classical_attack import ClassicalRainbowAttack, load_hashes

print("=" * 90)
print("  CLASSICAL RAINBOW TABLE ATTACK (Hash Table Lookup)")
print("=" * 90)

# Load configuration
config = load_config("config.json")
hash_func = hash_factory(config.hash_algorithm)

# Load hashes
hashes = load_hashes("hashes.txt")
print(f"\n[*] Loaded {len(hashes)} hashes from hashes.txt")

# Initialize attack (loads all endpoints into memory)
print(f"[*] Initializing classical attack...")
attack = ClassicalRainbowAttack(
    config=config,
    db_path="rainbow_tables/output/rainbow_table.db"
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
print(f"  SUMMARY")
print(f"{'='*80}")
print(f"  Success rate:      {found}/{total} ({100*found/total:.1f}%)")
print(f"  Total time:        {total_time:.3f}s")
print(f"  Average time:      {avg_time:.3f}s per hash")
print(f"  Throughput:        {total/total_time:.2f} hashes/second")
print(f"{'='*80}\n")
