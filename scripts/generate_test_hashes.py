#!/usr/bin/env python3
"""
Generate extended test hash sets from the rainbow table database.

Produces three files:
  hashes_200.txt   - 100 covered + 100 uncovered
  hashes_500.txt   - 250 covered + 250 uncovered
  hashes_1000.txt  - 500 covered + 500 uncovered

Covered hashes are sampled from actual chains in the database across
all four categories used in hashes_100.txt:
  - Mid-chain hashes  (k=100..900)
  - Endpoint hashes   (k=999, stored as end_point)
  - k=0 hashes        (hash of start_point directly)
  - Random hashes     (guaranteed NOT FOUND)

Usage:
    ./venv/bin/python scripts/generate_test_hashes.py
"""

import sqlite3
import hashlib
import random
import os
import sys

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH    = "rainbow_tables/output/rainbow_table.db"
CHAIN_LEN  = 1000
CHARSET    = "abcdefghijklmnopqrstuvwxyz0123456789"
CHARSET_LEN = 36
SEED       = 2024   # fixed seed for reproducibility

SETS = [
    ("hashes_200.txt",  100, 100),
    ("hashes_500.txt",  250, 250),
    ("hashes_1000.txt", 500, 500),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def sha1(text: str) -> str:
    return hashlib.sha1(text.encode()).hexdigest()

def sha1_bytes(text: str) -> bytes:
    return hashlib.sha1(text.encode()).digest()

def reduce(hash_bytes: bytes, iteration: int, length: int = 8) -> str:
    search_space = CHARSET_LEN ** length
    value = (int.from_bytes(hash_bytes, "big") + iteration) % search_space
    pwd = []
    for _ in range(length):
        pwd.append(CHARSET[value % CHARSET_LEN])
        value //= CHARSET_LEN
    return "".join(pwd)

def walk_chain(start_point: str, target_k: int):
    """
    Walk chain from start_point to position target_k.
    Returns the hash at that position.
    """
    current = start_point
    for i in range(target_k):
        h = sha1_bytes(current)
        current = reduce(h, i)
    return sha1(current)   # hash at position target_k

def random_sha1_hex(rng: random.Random) -> str:
    """Generate a random 40-char hex string that looks like a SHA-1 hash."""
    return "".join(rng.choice("0123456789abcdef") for _ in range(40))

# ── Main ──────────────────────────────────────────────────────────────────────

def generate_covered(cursor, n: int, rng: random.Random, already_used: set):
    """
    Sample n covered hashes from the database.
    Mix of k=0, mid-chain, and endpoint hashes.
    Returns list of (hash_hex, comment_str)
    """
    # Proportions matching hashes_100.txt style
    n_k0       = max(1, int(n * 0.34))   # ~34% k=0
    n_mid      = max(1, int(n * 0.50))   # ~50% mid-chain
    n_endpoint = n - n_k0 - n_mid        # remainder as endpoints

    total_chains = cursor.execute("SELECT COUNT(*) FROM chains").fetchone()[0]
    results = []

    # ── k=0 hashes ────────────────────────────────────────────────────────────
    print(f"  Sampling {n_k0} k=0 hashes...")
    sampled = 0
    attempts = 0
    while sampled < n_k0 and attempts < n_k0 * 20:
        attempts += 1
        row_id = rng.randint(1, total_chains)
        row = cursor.execute(
            "SELECT start_point FROM chains WHERE rowid = ?", (row_id,)
        ).fetchone()
        if row is None:
            continue
        sp = row[0]
        h = sha1(sp)
        if h in already_used:
            continue
        already_used.add(h)
        results.append((h, f"k=0, sp={sp}"))
        sampled += 1

    # ── Mid-chain hashes ──────────────────────────────────────────────────────
    print(f"  Sampling {n_mid} mid-chain hashes (this takes a moment)...")
    sampled = 0
    attempts = 0
    while sampled < n_mid and attempts < n_mid * 20:
        attempts += 1
        row_id = rng.randint(1, total_chains)
        row = cursor.execute(
            "SELECT start_point FROM chains WHERE rowid = ?", (row_id,)
        ).fetchone()
        if row is None:
            continue
        sp = row[0]
        k = rng.randint(100, 900)
        h = walk_chain(sp, k)
        if h in already_used:
            continue
        already_used.add(h)
        results.append((h, f"k={k}, sp={sp}"))
        sampled += 1
        if sampled % 50 == 0:
            print(f"    {sampled}/{n_mid} mid-chain hashes done...")

    # ── Endpoint hashes ───────────────────────────────────────────────────────
    print(f"  Sampling {n_endpoint} endpoint hashes...")
    sampled = 0
    attempts = 0
    while sampled < n_endpoint and attempts < n_endpoint * 20:
        attempts += 1
        row_id = rng.randint(1, total_chains)
        row = cursor.execute(
            "SELECT start_point, end_point FROM chains WHERE rowid = ?", (row_id,)
        ).fetchone()
        if row is None:
            continue
        sp, ep = row
        if ep in already_used:
            continue
        already_used.add(ep)
        results.append((ep, f"endpoint, sp={sp}"))
        sampled += 1

    rng.shuffle(results)
    return results


def generate_uncovered(n: int, rng: random.Random, already_used: set):
    """
    Generate n random SHA-1-like hashes guaranteed not in the table.
    """
    print(f"  Generating {n} random (NOT FOUND) hashes...")
    results = []
    while len(results) < n:
        h = random_sha1_hex(rng)
        if h not in already_used:
            already_used.add(h)
            results.append(h)
    return results


def write_file(path: str, covered: list, uncovered: list, n_covered: int, n_uncovered: int):
    """Write the hash file in the same format as hashes_100.txt."""
    total = n_covered + n_uncovered
    with open(path, "w") as f:
        f.write(f"# {os.path.basename(path)} - {total} test hashes\n")
        f.write(f"# Total: {total} hashes ({n_covered} covered + {n_uncovered} uncovered)\n")
        f.write("#\n")

        # Split covered into categories for the header
        k0    = [(h, c) for h, c in covered if "k=0"      in c]
        mid   = [(h, c) for h, c in covered if "k=" in c and "k=0" not in c]
        endpt = [(h, c) for h, c in covered if "endpoint" in c]

        f.write(f"# ── Category 1: Mid-chain hashes ({len(mid)}) ──────────────────────────────────\n")
        f.write("# Hashes at chain positions k=100 to k=900\n#\n")
        for h, comment in mid:
            f.write(f"{h}  # {comment}\n")

        f.write(f"#\n# ── Category 2: Endpoint hashes ({len(endpt)}) ────────────────────────────────────\n")
        f.write("# Directly stored as end_point in the database\n#\n")
        for h, comment in endpt:
            f.write(f"{h}  # {comment}\n")

        f.write(f"#\n# ── Category 3: k=0 hashes ({len(k0)}) ────────────────────────────────────────\n")
        f.write("# Hash of start_point password directly (first hash in chain)\n#\n")
        for h, comment in k0:
            f.write(f"{h}  # {comment}\n")

        f.write(f"#\n# ── Category 4: Random hashes ({len(uncovered)}) ─────────────────────────────────────\n")
        f.write("# Completely outside the 38M chains - should return NOT FOUND\n#\n")
        for h in uncovered:
            f.write(f"{h}\n")

    print(f"  ✓ Written {path}  ({n_covered} covered + {n_uncovered} uncovered = {total} total)")


def main():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        sys.exit(1)

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total = cursor.execute("SELECT COUNT(*) FROM chains").fetchone()[0]
    print(f"Total chains in database: {total:,}\n")

    rng = random.Random(SEED)
    all_used = set()

    # Load existing hashes_100.txt hashes so we don't duplicate them
    existing_file = "hashes_100.txt"
    if os.path.exists(existing_file):
        with open(existing_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    h = line.split()[0]
                    all_used.add(h)
        print(f"Loaded {len(all_used)} existing hashes from {existing_file} (will not duplicate)\n")

    for filename, n_covered, n_uncovered in SETS:
        print(f"{'='*60}")
        print(f"Generating {filename}  ({n_covered} covered + {n_uncovered} uncovered)")
        print(f"{'='*60}")

        covered   = generate_covered(cursor, n_covered, rng, all_used)
        uncovered = generate_uncovered(n_uncovered, rng, all_used)

        write_file(filename, covered, uncovered, n_covered, n_uncovered)
        print()

    conn.close()
    print("All test sets generated successfully!")
    print("\nFiles created:")
    for filename, nc, nu in SETS:
        size = os.path.getsize(filename)
        print(f"  {filename:<20} {nc+nu:>5} hashes  ({size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
