#!/usr/bin/env python3
"""
Redistribute Rainbow Table Buckets for Different Qubit Configurations

Reads all chains from the existing 10-qubit database and redistributes
them into a new database with a different qubit count (8 or 12).

The bucketing formula stays the same:
    bucket_key  = int(endpoint[:8], 16) % num_buckets
    intra_value = int(endpoint[:8], 16) % bucket_size

Only num_buckets and bucket_size change based on qubit_count.

Usage:
    python scripts/redistribute_buckets.py --qubits 8
    python scripts/redistribute_buckets.py --qubits 12
    python scripts/redistribute_buckets.py --qubits 8 --fill-factor 0.75
"""

import argparse
import math
import sqlite3
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def compute_bucket_params(total_entries: int, qubit_count: int, fill_factor: float):
    """Compute bucket_size and num_buckets for given qubit config."""
    bucket_size = 2 ** qubit_count
    effective_capacity = bucket_size * fill_factor
    num_buckets = math.ceil(total_entries / effective_capacity)
    return bucket_size, num_buckets


def assign_bucket(endpoint: str, num_buckets: int, bucket_size: int):
    """Compute bucket_key and intra_value for an endpoint."""
    hash_value = int(endpoint[:8], 16)
    bucket_key = hash_value % num_buckets
    intra_value = hash_value % bucket_size
    return bucket_key, intra_value


def redistribute(
    source_db: str,
    target_db: str,
    qubit_count: int,
    fill_factor: float = 0.75,
    batch_size: int = 100_000,
):
    """
    Read all chains from source_db and write to target_db with new bucketing.

    Args:
        source_db:   Path to existing rainbow_table.db
        target_db:   Path for new database
        qubit_count: Target qubit count (8 or 12)
        fill_factor: Bucket fill factor (default 0.75)
        batch_size:  Rows to process per batch
    """
    source_path = Path(source_db)
    target_path = Path(target_db)

    if not source_path.exists():
        print(f"[ERROR] Source database not found: {source_db}")
        sys.exit(1)

    if target_path.exists():
        print(f"[ERROR] Target database already exists: {target_db}")
        print(f"        Delete it first if you want to regenerate.")
        sys.exit(1)

    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Count total entries
    print(f"[*] Counting entries in source database...")
    src_conn = sqlite3.connect(source_db)
    src_cursor = src_conn.cursor()
    src_cursor.execute("SELECT COUNT(*) FROM chains")
    total_entries = src_cursor.fetchone()[0]
    print(f"[+] Total entries: {total_entries:,}")

    # Step 2: Compute new bucket parameters
    bucket_size, num_buckets = compute_bucket_params(total_entries, qubit_count, fill_factor)
    grover_iterations = max(1, math.floor((math.pi / 4) * math.sqrt(bucket_size)))

    print(f"\n[*] New configuration:")
    print(f"    Qubit count:       {qubit_count}")
    print(f"    Bucket size:       {bucket_size} (2^{qubit_count})")
    print(f"    Fill factor:       {fill_factor}")
    print(f"    Num buckets:       {num_buckets:,}")
    print(f"    Grover iterations: {grover_iterations}")
    print(f"    Target database:   {target_db}")

    # Step 3: Create target database
    print(f"\n[*] Creating target database...")
    tgt_conn = sqlite3.connect(target_db)
    tgt_cursor = tgt_conn.cursor()

    tgt_cursor.execute("""
        CREATE TABLE chains (
            bucket_key  INTEGER NOT NULL,
            intra_value INTEGER NOT NULL,
            start_point TEXT NOT NULL,
            end_point   TEXT NOT NULL
        )
    """)
    tgt_cursor.execute("""
        CREATE TABLE metadata (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    tgt_conn.commit()

    # Step 4: Stream and redistribute
    print(f"[*] Redistributing chains (batch_size={batch_size:,})...")
    start_time = time.time()

    src_cursor.execute("SELECT start_point, end_point FROM chains")

    processed = 0
    batch = []

    while True:
        rows = src_cursor.fetchmany(batch_size)
        if not rows:
            break

        for start_point, end_point in rows:
            bucket_key, intra_value = assign_bucket(end_point, num_buckets, bucket_size)
            batch.append((bucket_key, intra_value, start_point, end_point))

        tgt_cursor.executemany(
            "INSERT INTO chains (bucket_key, intra_value, start_point, end_point) VALUES (?,?,?,?)",
            batch
        )
        tgt_conn.commit()
        processed += len(batch)
        batch = []

        elapsed = time.time() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        pct = 100 * processed / total_entries
        print(f"    {processed:>12,} / {total_entries:,}  ({pct:.1f}%)  {rate:,.0f} rows/s", end='\r')

    print(f"\n[+] Redistributed {processed:,} chains in {time.time()-start_time:.1f}s")

    # Step 5: Create index
    print(f"[*] Creating index on bucket_key...")
    t0 = time.time()
    tgt_cursor.execute("CREATE INDEX idx_bucket_key ON chains(bucket_key)")
    tgt_conn.commit()
    print(f"[+] Index created in {time.time()-t0:.1f}s")

    # Step 6: Validate
    print(f"\n[*] Validating...")
    tgt_cursor.execute("SELECT COUNT(*) FROM chains")
    final_count = tgt_cursor.fetchone()[0]

    tgt_cursor.execute("SELECT COUNT(DISTINCT bucket_key) FROM chains")
    actual_buckets = tgt_cursor.fetchone()[0]

    tgt_cursor.execute("""
        SELECT MAX(cnt), MIN(cnt), AVG(cnt)
        FROM (SELECT COUNT(*) as cnt FROM chains GROUP BY bucket_key)
    """)
    max_fill, min_fill, avg_fill = tgt_cursor.fetchone()

    overflow = 0
    if max_fill > bucket_size:
        tgt_cursor.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT bucket_key FROM chains
                GROUP BY bucket_key
                HAVING COUNT(*) > {bucket_size}
            )
        """)
        overflow = tgt_cursor.fetchone()[0]

    print(f"[+] Total chains:      {final_count:,}")
    print(f"[+] Actual buckets:    {actual_buckets:,} (expected ~{num_buckets:,})")
    print(f"[+] Max bucket fill:   {max_fill} / {bucket_size} ({100*max_fill/bucket_size:.1f}%)")
    print(f"[+] Avg bucket fill:   {avg_fill:.1f} / {bucket_size} ({100*avg_fill/bucket_size:.1f}%)")
    print(f"[+] Overflow buckets:  {overflow}")

    if overflow > 0:
        print(f"[!] WARNING: {overflow} buckets exceed capacity!")
        print(f"    Consider increasing fill_factor or qubit_count.")
    else:
        print(f"[+] No overflow buckets ✓")

    # Step 7: Write metadata
    metadata = {
        "qubit_count": str(qubit_count),
        "bucket_size": str(bucket_size),
        "num_buckets": str(actual_buckets),
        "fill_factor": str(fill_factor),
        "total_chains": str(final_count),
        "grover_iterations": str(grover_iterations),
        "hash_algorithm": "sha1",
        "chain_length": "1000",
        "max_bucket_fill": str(max_fill),
        "avg_bucket_fill": str(round(avg_fill, 2)),
        "overflow_buckets": str(overflow),
    }
    tgt_cursor.executemany(
        "INSERT INTO metadata (key, value) VALUES (?, ?)",
        metadata.items()
    )
    tgt_conn.commit()

    src_conn.close()
    tgt_conn.close()

    db_size_mb = target_path.stat().st_size / 1024 / 1024
    print(f"\n[+] Database size: {db_size_mb:.1f} MB")
    print(f"[+] Done! Target database: {target_db}")


def main():
    parser = argparse.ArgumentParser(
        description="Redistribute rainbow table chains for a different qubit configuration"
    )
    parser.add_argument(
        "--qubits", type=int, required=True,
        help="Target qubit count (e.g. 8 or 12)"
    )
    parser.add_argument(
        "--source-db", default="rainbow_tables/output/rainbow_table.db",
        help="Source database path (default: rainbow_tables/output/rainbow_table.db)"
    )
    parser.add_argument(
        "--target-db", default=None,
        help="Target database path (default: rainbow_tables/output/rainbow_table_Nq.db)"
    )
    parser.add_argument(
        "--fill-factor", type=float, default=0.75,
        help="Bucket fill factor (default: 0.75)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=100_000,
        help="Rows per batch (default: 100000)"
    )
    args = parser.parse_args()

    if args.qubits < 1 or args.qubits > 20:
        print(f"[ERROR] --qubits must be between 1 and 20, got {args.qubits}")
        sys.exit(1)

    if not (0 < args.fill_factor <= 1.0):
        print(f"[ERROR] --fill-factor must be in (0, 1], got {args.fill_factor}")
        sys.exit(1)

    target_db = args.target_db or f"rainbow_tables/output/rainbow_table_{args.qubits}q.db"

    print("=" * 60)
    print(f"  Rainbow Table Bucket Redistribution")
    print("=" * 60)
    print(f"  Source:      {args.source_db}")
    print(f"  Target:      {target_db}")
    print(f"  Qubits:      {args.qubits}")
    print(f"  Fill factor: {args.fill_factor}")
    print("=" * 60)

    redistribute(
        source_db=args.source_db,
        target_db=target_db,
        qubit_count=args.qubits,
        fill_factor=args.fill_factor,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
