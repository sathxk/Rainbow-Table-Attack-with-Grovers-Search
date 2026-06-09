#!/usr/bin/env python3
"""
Reduction Function Collision Rate Analysis

Analyses two types of collisions in the reduction function:

1. Cross-chain collisions: reduce(h, i) == reduce(h, j) for i != j
   (same hash reduced at different iterations produces same password)

2. Within-chain collisions: does the same intermediate password appear
   twice in the same chain? (causes chain merging)

3. Output distribution: character frequency across positions to check
   for bias in the reduction function.

Usage:
    python analysis/reduction_collision_analysis.py
"""

import hashlib
import random
import sys
import time
from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, '.')
from rainbow_table_generator.reduction import reduce
from rainbow_table_generator.hash_functions import SHA1HashFunction

# ── Config ────────────────────────────────────────────────────────────────────
PASSWORD_LENGTH = 8
CHARSET         = "abcdefghijklmnopqrstuvwxyz0123456789"
CHAIN_LENGTH    = 1000
NUM_CHAINS      = 5_000    # chains for within-chain analysis
NUM_HASHES      = 100_000  # hashes for cross-iteration analysis
SAMPLE_ITERS    = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 999]

# ── Helpers ───────────────────────────────────────────────────────────────────

def random_sha1() -> bytes:
    return hashlib.sha1(random.randbytes(32)).digest()

# ── Analysis 1: Cross-iteration collisions ────────────────────────────────────

def cross_iteration_collision_analysis(hashes, iterations):
    """
    For each pair of iterations (i, j), count how many hashes produce
    the same reduced password: reduce(h, i) == reduce(h, j).
    """
    print("[*] Analysis 1: Cross-iteration collisions")
    print(f"    {len(hashes):,} hashes × {len(iterations)} iterations")

    # Build reduced outputs per iteration
    reduced = {}
    for it in iterations:
        reduced[it] = [reduce(h, it, PASSWORD_LENGTH) for h in hashes]

    # Count collisions between iteration pairs
    collision_matrix = np.zeros((len(iterations), len(iterations)))
    for i, it_i in enumerate(iterations):
        for j, it_j in enumerate(iterations):
            if i >= j:
                continue
            matches = sum(1 for a, b in zip(reduced[it_i], reduced[it_j]) if a == b)
            rate = matches / len(hashes)
            collision_matrix[i][j] = rate
            collision_matrix[j][i] = rate

    total_pairs = len(iterations) * (len(iterations) - 1) // 2
    all_rates = [collision_matrix[i][j]
                 for i in range(len(iterations))
                 for j in range(i+1, len(iterations))]
    avg = np.mean(all_rates)
    mx  = np.max(all_rates)

    print(f"    Avg cross-iteration collision rate: {avg:.6f}")
    print(f"    Max cross-iteration collision rate: {mx:.6f}")
    print(f"    Expected (random):                  {1/len(CHARSET)**PASSWORD_LENGTH:.2e}\n")

    return collision_matrix, iterations


# ── Analysis 2: Within-chain collisions ───────────────────────────────────────

def within_chain_collision_analysis(num_chains):
    """
    Reconstruct chains and check if any intermediate password appears
    twice within the same chain.
    """
    print(f"[*] Analysis 2: Within-chain collisions ({num_chains:,} chains)")
    hash_func = SHA1HashFunction()

    chains_with_collision = 0
    total_collisions = 0
    collision_positions = []
    chain_lengths_until_collision = []

    for idx in range(num_chains):
        if (idx + 1) % 1000 == 0:
            print(f"    Processed {idx+1:,}/{num_chains:,} chains...", end='\r')

        # Generate random start point
        start = ''.join(random.choices(CHARSET, k=PASSWORD_LENGTH))
        current = start
        seen = {}
        collided = False

        for i in range(CHAIN_LENGTH):
            if current in seen:
                if not collided:
                    chains_with_collision += 1
                    chain_lengths_until_collision.append(i)
                    collision_positions.append((seen[current], i))
                    collided = True
                total_collisions += 1
            seen[current] = i

            h = hash_func.hash(current)
            current = reduce(h, i, PASSWORD_LENGTH)

    print(f"    Processed {num_chains:,}/{num_chains:,} chains... Done!   ")

    collision_rate = chains_with_collision / num_chains
    print(f"\n    Chains with within-chain collision: {chains_with_collision:,} / {num_chains:,}")
    print(f"    Within-chain collision rate:        {collision_rate:.4%}")
    print(f"    Total collision events:             {total_collisions:,}")
    if chain_lengths_until_collision:
        print(f"    Avg position of first collision:    {np.mean(chain_lengths_until_collision):.1f}")
    print()

    return collision_rate, collision_positions, chain_lengths_until_collision


# ── Analysis 3: Output character distribution ─────────────────────────────────

def distribution_analysis(num_hashes=50_000):
    """Check if each character position has uniform distribution."""
    print(f"[*] Analysis 3: Output character distribution ({num_hashes:,} hashes)")
    hashes = [random_sha1() for _ in range(num_hashes)]

    # Check at iteration 0, 500, 999
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    check_iters = [0, 500, 999]

    for ax, it in zip(axes, check_iters):
        reduced = [reduce(h, it, PASSWORD_LENGTH) for h in hashes]
        # Count character frequency across all positions
        freq = Counter(''.join(reduced))
        chars = sorted(freq.keys())
        counts = [freq[c] for c in chars]
        expected = num_hashes * PASSWORD_LENGTH / len(CHARSET)

        ax.bar(range(len(chars)), counts, color="#42A5F5", edgecolor="white", width=0.8)
        ax.axhline(expected, color="#FF5722", linewidth=1.5, linestyle="--",
                   label=f"Expected ({expected:,.0f})")
        ax.set_xticks(range(len(chars)))
        ax.set_xticklabels(chars, fontsize=6.5)
        ax.set_title(f"Iteration {it}", fontsize=11, fontweight="bold")
        ax.set_ylabel("Frequency", fontsize=10)
        ax.legend(fontsize=9)
        ax.yaxis.grid(True, linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)

    plt.suptitle("Character Frequency Distribution Across Iterations\n(uniform = good reduction function)",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig("analysis/reduction_char_distribution.png", dpi=150, bbox_inches="tight")
    print("[+] Saved: analysis/reduction_char_distribution.png\n")
    plt.close()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  REDUCTION FUNCTION COLLISION RATE ANALYSIS")
    print("=" * 70)
    print(f"  Password length : {PASSWORD_LENGTH}")
    print(f"  Charset size    : {len(CHARSET)}")
    print(f"  Search space    : {len(CHARSET)**PASSWORD_LENGTH:,}  (36^8)")
    print(f"  Chain length    : {CHAIN_LENGTH}\n")

    t0 = time.time()

    # ── Analysis 1 ────────────────────────────────────────────────────────────
    hashes = [random_sha1() for _ in range(NUM_HASHES)]
    matrix, iters = cross_iteration_collision_analysis(hashes, SAMPLE_ITERS)

    # Plot heatmap
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(iters)))
    ax.set_yticks(range(len(iters)))
    ax.set_xticklabels(iters, fontsize=9)
    ax.set_yticklabels(iters, fontsize=9)
    ax.set_xlabel("Iteration", fontsize=11)
    ax.set_ylabel("Iteration", fontsize=11)
    ax.set_title("Cross-Iteration Collision Rate Heatmap\n(darker = more collisions between iteration pair)",
                 fontsize=11, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Collision Rate")
    plt.tight_layout()
    plt.savefig("analysis/reduction_cross_iteration_heatmap.png", dpi=150, bbox_inches="tight")
    print("[+] Saved: analysis/reduction_cross_iteration_heatmap.png\n")
    plt.close()

    # ── Analysis 2 ────────────────────────────────────────────────────────────
    collision_rate, positions, first_collision_pos = within_chain_collision_analysis(NUM_CHAINS)

    # Plot within-chain collision position distribution
    if first_collision_pos:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.hist(first_collision_pos, bins=40, color="#EF5350", edgecolor="white", linewidth=0.8)
        ax.set_xlabel("Chain Position of First Collision", fontsize=11)
        ax.set_ylabel("Number of Chains", fontsize=11)
        ax.set_title(f"Within-Chain Collision Position Distribution\n"
                     f"({NUM_CHAINS:,} chains, {collision_rate:.3%} collision rate)",
                     fontsize=12, fontweight="bold")
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)
        plt.tight_layout()
        plt.savefig("analysis/reduction_within_chain_collisions.png", dpi=150, bbox_inches="tight")
        print("[+] Saved: analysis/reduction_within_chain_collisions.png\n")
        plt.close()
    else:
        print("    No within-chain collisions found — reduction function is excellent.\n")

    # ── Analysis 3 ────────────────────────────────────────────────────────────
    distribution_analysis()

    print(f"[+] Total analysis time: {time.time()-t0:.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
