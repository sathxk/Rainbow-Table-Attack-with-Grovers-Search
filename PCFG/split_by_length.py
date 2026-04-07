"""
split_by_length.py
==================
Reads a cleaned password file and splits it into individual files,
one per password length.

If you re-run clean_rockyou.py with a new length range, just re-run
this script and all output files will be regenerated automatically.

Usage:
    python3 split_by_length.py --input rockyou_cleaned1.txt --output_dir ./split_output
"""

import argparse
import os
from collections import defaultdict

EXPECTED_LENGTHS = [6, 7, 8, 9, 10]   # <-- update this list if your range changes

# Output filename pattern — {length} will be replaced with the actual number
# e.g. "rockyou_len{length}.txt" → "rockyou_len6.txt"
OUTPUT_FILENAME_PATTERN = "rockyou_len{length}.txt"

# ══════════════════════════════════════════════════════════════════

# ANSI colours
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"


def main():
    parser = argparse.ArgumentParser(description="Split cleaned password file by length")
    parser.add_argument("--input",      required=True, help="Path to cleaned password file")
    parser.add_argument("--output_dir", default="./split_output", help="Directory for output files")
    args = parser.parse_args()

    # ── Validate input ─────────────────────────────────────────────
    if not os.path.isfile(args.input):
        print(f"\n{RED}  ERROR: Input file not found: {args.input}{RESET}\n")
        return

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}{CYAN}  Password File Splitter{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
    print(f"  {DIM}Input      : {args.input}{RESET}")
    print(f"  {DIM}Output dir : {args.output_dir}{RESET}")
    print(f"  {DIM}Lengths    : {EXPECTED_LENGTHS}{RESET}\n")

    # ── Read and bucket by length ──────────────────────────────────
    buckets      = defaultdict(list)
    total_lines  = 0
    skipped      = 0
    unexpected   = set()

    with open(args.input, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            pw = line.rstrip("\n")
            if not pw:
                skipped += 1
                continue

            total_lines += 1
            length = len(pw)

            if length not in EXPECTED_LENGTHS:
                unexpected.add(length)
                skipped += 1
                continue

            buckets[length].append(pw)

    # ── Write one file per length ──────────────────────────────────
    print(f"  {BOLD}OUTPUT FILES{RESET}\n")
    print(f"  {DIM}{'Length':<10} {'Passwords':>12}  {'File'}{RESET}")
    print(f"  {'─'*10}  {'─'*12}  {'─'*30}")

    total_written = 0
    for length in sorted(EXPECTED_LENGTHS):
        passwords = buckets.get(length, [])
        filename  = OUTPUT_FILENAME_PATTERN.format(length=length)
        filepath  = os.path.join(args.output_dir, filename)

        # Always overwrite — safe to rerun
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(passwords))
            if passwords:
                f.write("\n")

        total_written += len(passwords)
        status = GREEN if passwords else YELLOW
        count_str = f"{len(passwords):,}" if passwords else "0  ⚠ empty"
        print(f"  {status}{length:<10}{RESET}  {count_str:>12}  {DIM}{filepath}{RESET}")

    # ── Warn about unexpected lengths ──────────────────────────────
    if unexpected:
        print(f"\n  {YELLOW}⚠  Skipped passwords with unexpected lengths: "
              f"{sorted(unexpected)}{RESET}")
        print(f"  {DIM}   Add them to EXPECTED_LENGTHS if you want them split out.{RESET}")

    # ── Summary ────────────────────────────────────────────────────
    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"  {DIM}Total read    : {total_lines:,}{RESET}")
    print(f"  {DIM}Skipped       : {skipped:,}{RESET}")
    print(f"  {GREEN}{BOLD}Total written : {total_written:,}{RESET}")
    print(f"  {GREEN}Files saved to: {args.output_dir}/{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")


if __name__ == "__main__":
    main()
