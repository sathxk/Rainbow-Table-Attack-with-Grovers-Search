#!/usr/bin/env python3
"""
Generate hashes_100.txt with 4 categories of hashes:
  - 25 mid-chain hashes (k=100 to k=900, major portion)
  - 6  endpoint hashes (directly in DB as end_point)
  - 35 random hashes (completely outside the 38M chains, NOT FOUND)
  - 34 k=0 hashes (hash of start_point password directly)
  Total: 100 hashes
"""

import sqlite3
import random
import sys
sys.path.insert(0, '.')

from rainbow_table_generator.hash_functions import hash_factory
from rainbow_table_generator.reduction import reduce

DB_PATH = "rainbow_tables/output/rainbow_table.db"
OUTPUT  = "hashes_100.txt"

random.seed(42)
hash_func = hash_factory("sha1")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Category 1: Mid-chain hashes (25) ────────────────────────────────────────
# Pick start_points, walk to a random mid position, take the hash there
print("[*] Generating 25 mid-chain hashes (k=100 to k=900)...")
cursor.execute("SELECT start_point FROM chains ORDER BY RANDOM() LIMIT 25")
start_points_mid = [row[0] for row in cursor.fetchall()]

mid_hashes = []
for sp in start_points_mid:
    k = random.randint(100, 900)
    # Walk chain to position k
    current = sp
    for i in range(k):
        h = hash_func.hash_hex(current)
        current = reduce(bytes.fromhex(h), iteration=i, password_length=8)
    # Hash at position k
    h_at_k = hash_func.hash_hex(current)
    mid_hashes.append((h_at_k, k, sp))
    print(f"    [{len(mid_hashes):>2}/25] sp={sp}, k={k}, hash={h_at_k[:16]}...")

print(f"[+] Got {len(mid_hashes)} mid-chain hashes")

# ── Category 2: Endpoint hashes (6) ──────────────────────────────────────────
print("\n[*] Sampling 6 endpoint hashes...")
cursor.execute("SELECT end_point, start_point FROM chains ORDER BY RANDOM() LIMIT 6")
endpoint_hashes = [(row[0], row[1]) for row in cursor.fetchall()]
print(f"[+] Got {len(endpoint_hashes)} endpoint hashes")

# ── Category 3: k=0 hashes (34) ──────────────────────────────────────────────
# Hash of the start_point password directly (first hash in chain)
print("\n[*] Generating 34 k=0 hashes (hash of start_point)...")
cursor.execute("SELECT start_point FROM chains ORDER BY RANDOM() LIMIT 34")
start_points_k0 = [row[0] for row in cursor.fetchall()]

k0_hashes = []
for sp in start_points_k0:
    h = hash_func.hash_hex(sp)
    k0_hashes.append((h, sp))

print(f"[+] Got {len(k0_hashes)} k=0 hashes")

# ── Category 4: Random hashes not in DB (35) ─────────────────────────────────
print("\n[*] Generating 35 random hashes not in the database...")
random_hashes = []
attempts = 0
while len(random_hashes) < 35:
    rand_bytes = random.randbytes(20)
    h = rand_bytes.hex()
    random_hashes.append(h)
    attempts += 1

print(f"[+] Got {len(random_hashes)} random hashes")

conn.close()

# ── Write hashes_100.txt ──────────────────────────────────────────────────────
total = len(mid_hashes) + len(endpoint_hashes) + len(k0_hashes) + len(random_hashes)
print(f"\n[*] Writing {OUTPUT} ({total} hashes)...")

with open(OUTPUT, 'w') as f:
    f.write("# hashes_100.txt - 100 test hashes for comprehensive attack testing\n")
    f.write(f"# Total: {total} hashes across 4 categories\n")
    f.write("#\n")

    f.write("# ── Category 1: Mid-chain hashes (25) ──────────────────────────────────\n")
    f.write("# Hashes at chain positions k=100 to k=900\n")
    f.write("# These exist inside chains but not as endpoints\n")
    f.write("#\n")
    for h, k, sp in mid_hashes:
        f.write(f"{h}  # k={k}, sp={sp}\n")

    f.write("#\n")
    f.write("# ── Category 2: Endpoint hashes (6) ────────────────────────────────────\n")
    f.write("# Directly stored as end_point in the database\n")
    f.write("#\n")
    for h, sp in endpoint_hashes:
        f.write(f"{h}  # endpoint, sp={sp}\n")

    f.write("#\n")
    f.write("# ── Category 3: k=0 hashes (34) ────────────────────────────────────────\n")
    f.write("# Hash of start_point password directly (first hash in chain)\n")
    f.write("#\n")
    for h, sp in k0_hashes:
        f.write(f"{h}  # k=0, sp={sp}\n")

    f.write("#\n")
    f.write("# ── Category 4: Random hashes (35) ─────────────────────────────────────\n")
    f.write("# Completely outside the 38M chains - should return NOT FOUND\n")
    f.write("#\n")
    for h in random_hashes:
        f.write(f"{h}\n")

print(f"[+] Written {OUTPUT}")
print(f"\nSummary:")
print(f"  Category 1 (mid-chain k=100-900): {len(mid_hashes):>3} hashes  → should be FOUND")
print(f"  Category 2 (endpoints):           {len(endpoint_hashes):>3} hashes  → should be FOUND")
print(f"  Category 3 (k=0 hashes):          {len(k0_hashes):>3} hashes  → should be FOUND")
print(f"  Category 4 (random/not in table): {len(random_hashes):>3} hashes  → should be NOT FOUND")
print(f"  Total:                            {total:>3} hashes")
