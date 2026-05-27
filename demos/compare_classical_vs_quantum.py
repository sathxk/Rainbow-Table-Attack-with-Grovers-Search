#!/usr/bin/env python3
"""
Classical vs Quantum Rainbow Table Attack - Comparison

Reads hashes from hashes.txt and runs both attacks on each hash,
reporting timing and results side by side.

Usage:
    python examples/compare_classical_vs_quantum.py [--qubits 8|10|12]
"""

import argparse
import sqlite3
import sys
import time
sys.path.insert(0, '.')

from rainbow_table_generator.config import load_config
from attack.bloom_filter import BloomFilter
from attack.orchestrator import RainbowAttack
from attack.classical_attack import ClassicalRainbowAttack, load_hashes


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
    parser = argparse.ArgumentParser(description="Compare classical vs quantum rainbow table attack")
    parser.add_argument("--qubits", type=int, default=10, choices=[8, 10, 12],
                        help="Qubit configuration for quantum attack (8, 10, or 12)")
    args = parser.parse_args()
    
    # Determine database path
    if args.qubits == 10:
        db_path = "rainbow_tables/output/rainbow_table.db"
    else:
        db_path = f"rainbow_tables/output/rainbow_table_{args.qubits}q.db"
    
    print("=" * 80)
    print(f"  CLASSICAL vs QUANTUM RAINBOW TABLE ATTACK - COMPARISON")
    print(f"  Quantum Configuration: {args.qubits} Qubits")
    print("=" * 80)
    
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
    
    # Load hashes from file
    hashes = load_hashes("hashes.txt")
    print(f"\n[*] Loaded {len(hashes)} hashes from hashes.txt")
    
    # Load config
    config = load_config("config.json")
    config.qubit_count = qubit_count
    
    # ── Classical Attack ──────────────────────────────────────────────────────────
    print("\n[1] Initializing Classical Attack...")
    t0 = time.time()
    classical_attack = ClassicalRainbowAttack(
        config=config,
        db_path=db_path
    )
    print(f"    Init time: {time.time()-t0:.2f}s")
    print(f"    Memory: {classical_attack.memory_mb:.1f} MB")
    
    # ── Quantum Attack ────────────────────────────────────────────────────────────
    print(f"\n[2] Initializing Quantum Attack ({args.qubits} qubits)...")
    t0 = time.time()
    bloom = BloomFilter.load("bloom_filter.bin", "bloom_filter.json")
    print(f"    Bloom filter: {bloom.count:,} items, {bloom.memory_bytes/1024/1024:.1f} MB")
    quantum_attack = RainbowAttack(
        config=config,
        db_path=db_path,
        num_buckets=num_buckets,
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
    print(f"\nSUMMARY - Quantum: {args.qubits} Qubits")
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
        print(f"\nNote: Classical uses O(1) hash table lookup.")
        print(f"      Quantum uses O(√N) Grover's search with {grover_iterations} iterations per bucket.")
    
    print()


if __name__ == "__main__":
    main()
