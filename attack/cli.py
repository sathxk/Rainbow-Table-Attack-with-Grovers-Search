"""
CLI for the Quantum Rainbow Table Attack phase.

Usage:
    python3 -m attack crack <target_hash> [options]
    python3 -m attack build-bloom [options]
    python3 -m attack info

Commands:
    crack        Attempt to crack a SHA-1 hash using the rainbow table.
    build-bloom  Build and save a Bloom filter from the rainbow table DB.
    info         Print DB and config statistics.

Examples:
    # Crack a hash (Bloom filter pre-loaded from disk):
    python3 -m attack crack 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8 \\
        --db rainbow_tables/output/rainbow_table.db \\
        --bloom-bits bloom_filter.bin --bloom-meta bloom_filter.json \\
        --num-buckets 49851

    # Build the Bloom filter first (one-time, ~30-60s):
    python3 -m attack build-bloom \\
        --db rainbow_tables/output/rainbow_table.db \\
        --output-bits bloom_filter.bin --output-meta bloom_filter.json \\
        --n-items 38285441 --fpr 0.001

    # Show DB and config info:
    python3 -m attack info --db rainbow_tables/output/rainbow_table.db
"""

import argparse
import os
import sys
import time

from rainbow_table_generator.config import load_config
from attack.bloom_filter import BloomFilter
from attack.orchestrator import RainbowAttack


# ---------------------------------------------------------------------------
# Sub-command: crack
# ---------------------------------------------------------------------------

def cmd_crack(args) -> int:
    """Crack a target SHA-1 hash."""
    # Validate hash format
    if len(args.target_hash) != 40:
        print(f"[ERROR] target_hash must be a 40-char SHA-1 hex string, "
              f"got {len(args.target_hash)} chars.", file=sys.stderr)
        return 1
    try:
        bytes.fromhex(args.target_hash)
    except ValueError:
        print("[ERROR] target_hash is not valid hex.", file=sys.stderr)
        return 1

    # Load config
    config = load_config(args.config)

    # Load or build Bloom filter
    bloom = None
    if args.bloom_bits and args.bloom_meta:
        if os.path.exists(args.bloom_bits) and os.path.exists(args.bloom_meta):
            print("[*] Loading Bloom filter from disk...", flush=True)
            t0 = time.perf_counter()
            bloom = BloomFilter.load(args.bloom_bits, args.bloom_meta)
            print(f"[*] Bloom filter loaded in {time.perf_counter()-t0:.2f}s  "
                  f"({bloom.count:,} items, {bloom.memory_bytes/1024/1024:.1f} MB)")
        else:
            print("[!] Bloom filter files not found — running without pre-screening "
                  "(slower). Build with: python3 -m attack build-bloom ...", file=sys.stderr)

    # Run the attack
    print(f"\n[*] Target hash : {args.target_hash}")
    print(f"[*] Database    : {args.db}")
    print(f"[*] Num buckets : {args.num_buckets:,}")
    print(f"[*] Chain length: {config.chain_length}")
    print(f"[*] Qubits      : {config.qubit_count}  (bucket_size={2**config.qubit_count})")
    print(f"[*] Bloom filter: {'enabled' if bloom else 'disabled'}")
    print()

    t0 = time.perf_counter()
    attack = RainbowAttack(config, args.db, num_buckets=args.num_buckets,
                           bloom_filter=bloom)
    result = attack.crack(args.target_hash, verbose=args.verbose)
    elapsed = time.perf_counter() - t0

    print()
    if result:
        print(f"[+] SUCCESS! Password cracked in {elapsed:.2f}s")
        print(f"[+] Plaintext password: {result!r}")
        return 0
    else:
        print(f"[-] FAILURE: Hash not found in rainbow table (took {elapsed:.2f}s)")
        print("[-] This hash may not be covered by the current table.")
        return 2


# ---------------------------------------------------------------------------
# Sub-command: build-bloom
# ---------------------------------------------------------------------------

def cmd_build_bloom(args) -> int:
    """Build and save a Bloom filter from the rainbow table database."""
    if not os.path.exists(args.db):
        print(f"[ERROR] Database not found: {args.db}", file=sys.stderr)
        return 1

    print(f"[*] Building Bloom filter from: {args.db}")
    print(f"[*] n_items={args.n_items:,}, fpr={args.fpr}")
    print(f"[*] This will take 30-90 seconds for large tables...\n", flush=True)

    bloom = BloomFilter(n_items=args.n_items, fpr=args.fpr)
    t0 = time.perf_counter()
    count = bloom.build_from_db(args.db, batch_size=args.batch_size)
    elapsed = time.perf_counter() - t0

    print(f"[+] Inserted {count:,} endpoints in {elapsed:.1f}s")
    print(f"[+] Bloom filter: m={bloom.m:,} bits, k={bloom.k} hashes, "
          f"memory={bloom.memory_bytes/1024/1024:.1f} MB, "
          f"fill_ratio={bloom.fill_ratio:.4f}")

    bloom.save(args.output_bits, args.output_meta)
    print(f"[+] Saved to: {args.output_bits}, {args.output_meta}")
    return 0


# ---------------------------------------------------------------------------
# Sub-command: info
# ---------------------------------------------------------------------------

def cmd_info(args) -> int:
    """Print statistics about the existing rainbow table database."""
    import sqlite3, math

    if not os.path.exists(args.db):
        print(f"[ERROR] Database not found: {args.db}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(args.db)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM chains")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT bucket_key) FROM chains")
    num_buckets = c.fetchone()[0]

    c.execute("SELECT MAX(cnt), MIN(cnt), AVG(cnt) FROM "
              "(SELECT bucket_key, COUNT(*) as cnt FROM chains GROUP BY bucket_key)")
    max_e, min_e, avg_e = c.fetchone()

    c.execute("SELECT bucket_key, COUNT(*) as cnt FROM chains "
              "GROUP BY bucket_key ORDER BY cnt DESC LIMIT 1")
    heaviest = c.fetchone()
    conn.close()

    bucket_size = 1024  # 2^10
    expected_ff75 = math.ceil(total / (bucket_size * 0.75))

    print(f"\n{'='*52}")
    print(f"  Rainbow Table Database: {os.path.basename(args.db)}")
    print(f"{'='*52}")
    print(f"  Total chains              : {total:,}")
    print(f"  Distinct bucket_keys      : {num_buckets:,}")
    print(f"  Bucket size (2^10)        : {bucket_size}")
    print(f"  Max entries in bucket     : {max_e}  ({100*max_e/bucket_size:.1f}% full)")
    print(f"  Min entries in bucket     : {min_e}  ({100*min_e/bucket_size:.1f}% full)")
    print(f"  Avg entries per bucket    : {avg_e:.1f}  ({100*avg_e/bucket_size:.1f}% full)")
    print(f"  Heaviest bucket_key       : {heaviest[0]}  ({heaviest[1]} entries)")
    print(f"\n  Expected buckets (fill_factor=0.75) : {expected_ff75:,}")
    print(f"  Actual   buckets in DB              : {num_buckets:,}")

    if abs(num_buckets - expected_ff75) < 500:
        print(f"\n  ✅ Over-provisioned bucketing confirmed (fill_factor≈0.75)")
    else:
        print(f"\n  ⚠️  Bucket count doesn't match fill_factor=0.75 formula.")
        print(f"      Expected {expected_ff75:,}, got {num_buckets:,}")
    print()
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m attack",
        description="Quantum Rainbow Table Attack CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # --- crack ---
    p_crack = sub.add_parser("crack", help="Crack a SHA-1 hash")
    p_crack.add_argument("target_hash", help="40-char SHA-1 hex string to crack")
    p_crack.add_argument("--db", default="rainbow_tables/output/rainbow_table.db",
                         help="Path to rainbow_table.db (default: %(default)s)")
    p_crack.add_argument("--config", default="config.json",
                         help="Path to config.json (default: %(default)s)")
    p_crack.add_argument("--num-buckets", type=int, default=49851,
                         help="Number of buckets in the table (default: %(default)s)")
    p_crack.add_argument("--bloom-bits", metavar="PATH",
                         help="Path to saved Bloom filter .bin file")
    p_crack.add_argument("--bloom-meta", metavar="PATH",
                         help="Path to saved Bloom filter .json metadata file")
    p_crack.add_argument("-v", "--verbose", action="store_true",
                         help="Print progress for each chain position tried")
    p_crack.set_defaults(func=cmd_crack)

    # --- build-bloom ---
    p_bloom = sub.add_parser("build-bloom", help="Build and save a Bloom filter")
    p_bloom.add_argument("--db", default="rainbow_tables/output/rainbow_table.db",
                         help="Path to rainbow_table.db")
    p_bloom.add_argument("--n-items", type=int, required=True,
                         help="Approximate number of chains in the DB (e.g. 38285441)")
    p_bloom.add_argument("--fpr", type=float, default=0.001,
                         help="Target false positive rate (default: 0.001 = 0.1%%)")
    p_bloom.add_argument("--output-bits", default="bloom_filter.bin",
                         help="Output path for bitarray file (default: %(default)s)")
    p_bloom.add_argument("--output-meta", default="bloom_filter.json",
                         help="Output path for metadata JSON (default: %(default)s)")
    p_bloom.add_argument("--batch-size", type=int, default=100_000,
                         help="DB rows per batch (default: %(default)s)")
    p_bloom.set_defaults(func=cmd_build_bloom)

    # --- info ---
    p_info = sub.add_parser("info", help="Print DB statistics")
    p_info.add_argument("--db", default="rainbow_tables/output/rainbow_table.db",
                        help="Path to rainbow_table.db")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
