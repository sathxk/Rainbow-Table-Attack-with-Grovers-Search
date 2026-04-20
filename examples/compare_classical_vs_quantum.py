#!/usr/bin/env python3
"""
Classical vs Quantum Rainbow Table Attack - Comparison

Reads hashes from hashes.txt and runs both attacks on each hash,
reporting timing and results side by side.
"""

import sys
import time
sys.path.insert(0, '.')

from rainbow_table_generator.config import load_config
from attack.bloom_filter import BloomFilter
from attack.orchestrator import RainbowAttack
from attack.classical_attack import ClassicalRainbowAttack, load_hashes

print("=" * 80)
print("  CLASSICAL vs QUANTUM RAINBOW TABLE ATTACK - COMPARISON")
print("=" * 80)

# Load hashes from file
hashes = load_hashes("hashes.txt")
print(f"\n[*] Loaded {len(hashes)} hashes from hashes.txt")

# Load config
from rainbow_table_generator.config import load_config
config = load_config("config.json")

# ── Classical Attack ──────────────────────────────────────────────────────────
print("\n[1] Initializing Classical Attack...")
t0 = time.time()
classical_attack = ClassicalRainbowAttack(
    config=config,
    db_path="rainbow_tables/output/rainbow_table.db"
)
print(f"    Init time: {time.time()-t0:.2f}s")

# ── Quantum Attack ────────────────────────────────────────────────────────────
print("\n[2] Initializing Quantum Attack...")
t0 = time.time()
bloom = BloomFilter.load("bloom_filter.bin", "bloom_filter.json")
print(f"    Bloom filter: {bloom.count:,} items, {bloom.memory_bytes/1024/1024:.1f} MB")
quantum_attack = RainbowAttack(
    config=config,
    db_path="rainbow_tables/output/rainbow_table.db",
    num_buckets=49851,
    bloom_filter=bloom
)
print(f"    Init time: {time.time()-t0:.2f}s")

# ── Run Comparison ────────────────────────────────────────────────────────────
print(f"\n{'='*80}")
print(f"{'#':<4} {'Hash':<42} {'Classical':<14} {'Quantum':<14} {'Speedup'}")
print("=" * 80)

classical_times = []
quantum_times = []

for i, target_hash in enumerate(hashes, 1):
    # Classical
    t0 = time.time()
    c_result = classical_attack.crack(target_hash)
    c_time = time.time() - t0

    # Quantum
    t0 = time.time()
    q_result = quantum_attack.crack(target_hash)
    q_time = time.time() - t0

    c_str = f"{c_time:.3f}s {'✓' if c_result else '✗'}"
    q_str = f"{q_time:.3f}s {'✓' if q_result else '✗'}"
    speedup = f"{c_time/q_time:.2f}×" if q_time > 0 else "N/A"

    print(f"{i:<4} {target_hash:<42} {c_str:<14} {q_str:<14} {speedup}")

    if c_result:
        classical_times.append(c_time)
    if q_result:
        quantum_times.append(q_time)

# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 80)
print("\nSUMMARY")
print("=" * 80)

if classical_times:
    c_avg = sum(classical_times) / len(classical_times)
    print(f"\nClassical:  {len(classical_times)}/{len(hashes)} found | "
          f"avg {c_avg:.3f}s | {1/c_avg:.2f} h/s")

if quantum_times:
    q_avg = sum(quantum_times) / len(quantum_times)
    print(f"Quantum:    {len(quantum_times)}/{len(hashes)} found | "
          f"avg {q_avg:.3f}s | {1/q_avg:.2f} h/s")

if classical_times and quantum_times:
    ratio = c_avg / q_avg
    faster = "Quantum" if ratio > 1 else "Classical"
    print(f"\n→ {faster} is {max(ratio, 1/ratio):.2f}× faster overall")
