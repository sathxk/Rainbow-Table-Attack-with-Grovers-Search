"""
clean_rockyou.py
================
Run this AFTER analyze_lengths.py.

Cleans a raw password file and writes rockyou_cleaned.txt.
Re-runs overwrite the output file safely.

What it cleans:
  - Encoding errors / non-printable characters
  - Empty and whitespace-only lines
  - Email addresses, URLs, SQL dump artifacts
  - Passwords outside your chosen length range
  - Leading / trailing whitespace
  - Frequency dampening  →  caps how many times one password is counted

Usage:
    python clean_rockyou.py \\
        --input  /path/to/rockyou.txt \\
        --output /path/to/rockyou_cleaned.txt \\
        --min_length 6 \\
        --max_length 20 \\
        --freq_cap 10
"""

import argparse
import os
import re
import sys
from collections import Counter

# ── ANSI colours ───────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
DIM    = "\033[2m"
ORANGE = "\033[38;5;208m"

# ── Noise patterns to reject entirely ─────────────────────────────
REJECT_PATTERNS = [
    re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$'),          # email addresses
    re.compile(r'^https?://', re.IGNORECASE),           # URLs
    re.compile(r'^ftp://',    re.IGNORECASE),           # FTP URLs
    re.compile(r'^INSERT\s+INTO', re.IGNORECASE),       # SQL dump lines
    re.compile(r'^--'),                                 # SQL comments
    re.compile(r'^\s*$'),                               # whitespace only
    re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]'),  # non-printable chars
]


def is_noisy(pw: str) -> str | None:
    """Return a rejection reason string, or None if the password is clean."""
    for pattern in REJECT_PATTERNS:
        if pattern.search(pw):
            return "noise_pattern"
    if "\ufffd" in pw:
        return "encoding_error"
    return None


def main():
    parser = argparse.ArgumentParser(description="RockYou dataset cleaner")
    parser.add_argument("--input",      required=True,       help="Path to raw password file")
    parser.add_argument("--output",     default="rockyou_cleaned.txt",
                                                             help="Output file path (overwritten each run)")
    parser.add_argument("--min_length", type=int, default=6, help="Minimum password length to keep")
    parser.add_argument("--max_length", type=int, default=20,help="Maximum password length to keep")
    parser.add_argument("--freq_cap",   type=int, default=10,
                        help="Max times one password is written to output (frequency dampening)")
    args = parser.parse_args()

    # ── Validate ───────────────────────────────────────────────────
    if not os.path.isfile(args.input):
        print(f"\n{RED}  ERROR: Input file not found: {args.input}{RESET}\n")
        sys.exit(1)

    if args.min_length < 1 or args.max_length < args.min_length:
        print(f"\n{RED}  ERROR: Invalid length range "
              f"({args.min_length}–{args.max_length}){RESET}\n")
        sys.exit(1)

    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}{CYAN}  RockYou Dataset Cleaner{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")
    print(f"  {DIM}Input       : {args.input}{RESET}")
    print(f"  {DIM}Output      : {args.output}{RESET}")
    print(f"  {DIM}Length range: {args.min_length}–{args.max_length} chars{RESET}")
    print(f"  {DIM}Freq cap    : {args.freq_cap} per unique password{RESET}\n")

    # ── Counters ───────────────────────────────────────────────────
    seen_counts  = Counter()   # how many times each password has been written
    capped_log   = {}          # password → total occurrences in input (for capped ones)

    stats = {
        "total_lines":      0,
        "empty":            0,
        "encoding_errors":  0,
        "noise_pattern":    0,
        "too_short":        0,
        "too_long":         0,
        "capped":           0,       # lines dropped due to freq cap
        "written":          0,
    }

    print(f"{BOLD}  CLEANING  {DIM}(capped passwords printed below){RESET}\n")
    print(f"  {DIM}{'Password':<30} {'Total in file':>14}  {'Cap limit':>10}{RESET}")
    print(f"  {'─'*30}  {'─'*14}  {'─'*10}")

    # ── First pass: count ALL occurrences to know what will be capped ──
    # (so we can print the total-in-file count accurately)
    print(f"  {DIM}Pre-scanning for frequency counts …{RESET}")
    raw_counts = Counter()
    with open(args.input, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            pw = line.rstrip("\n").strip()
            if pw:
                raw_counts[pw] += 1
    print(f"  {DIM}Pre-scan complete — {len(raw_counts):,} unique passwords found{RESET}\n")
    print(f"  {DIM}{'Password':<30} {'Total in file':>14}  {'Cap limit':>10}{RESET}")
    print(f"  {'─'*30}  {'─'*14}  {'─'*10}")

    # ── Second pass: clean and write ───────────────────────────────
    with open(args.input, "r", encoding="utf-8", errors="replace") as fin, \
         open(args.output, "w", encoding="utf-8") as fout:

        for line in fin:
            stats["total_lines"] += 1
            pw = line.rstrip("\n")

            # 1. Strip leading/trailing whitespace
            pw_clean = pw.strip()

            # 2. Empty line
            if not pw_clean:
                stats["empty"] += 1
                continue

            # 3. Encoding errors
            if "\ufffd" in pw_clean:
                stats["encoding_errors"] += 1
                continue

            # 4. Noise patterns (email, URL, SQL, non-printable)
            reason = is_noisy(pw_clean)
            if reason:
                stats["noise_pattern"] += 1
                continue

            # 5. Length filter
            if len(pw_clean) < args.min_length:
                stats["too_short"] += 1
                continue
            if len(pw_clean) > args.max_length:
                stats["too_long"] += 1
                continue

            # 6. Frequency dampening
            seen_counts[pw_clean] += 1
            if seen_counts[pw_clean] > args.freq_cap:
                stats["capped"] += 1
                # Log it (only print the first time we exceed the cap)
                if seen_counts[pw_clean] == args.freq_cap + 1:
                    total_occ = raw_counts[pw_clean]
                    capped_log[pw_clean] = total_occ
                    dropped = total_occ - args.freq_cap
                    print(f"  {ORANGE}{pw_clean:<30}{RESET}  "
                          f"{total_occ:>14,}  "
                          f"{args.freq_cap:>10,}  "
                          f"{DIM}(drops {dropped:,}){RESET}")
                continue

            # ✓ Write clean password
            fout.write(pw_clean + "\n")
            stats["written"] += 1

            if stats["total_lines"] % 500_000 == 0:
                print(f"\n  {DIM}… processed {stats['total_lines']:,} lines, "
                      f"written {stats['written']:,}{RESET}\n")

    # ── Summary ────────────────────────────────────────────────────
    total = stats["total_lines"]
    removed = total - stats["written"]

    print(f"\n{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"{BOLD}  CLEANING SUMMARY{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")

    print(f"  {'Total lines read':<35} {total:>12,}")
    print(f"  {DIM}{'  Empty / blank lines':<35} {stats['empty']:>12,}{RESET}")
    print(f"  {DIM}{'  Encoding errors':<35} {stats['encoding_errors']:>12,}{RESET}")
    print(f"  {DIM}{'  Noise (email, URL, SQL…)':<35} {stats['noise_pattern']:>12,}{RESET}")
    print(f"  {DIM}{'  Too short (< ' + str(args.min_length) + ' chars)':<35} {stats['too_short']:>12,}{RESET}")
    print(f"  {DIM}{'  Too long  (> ' + str(args.max_length) + ' chars)':<35} {stats['too_long']:>12,}{RESET}")
    print(f"  {ORANGE}{'  Frequency capped (duplicates)':<35} {stats['capped']:>12,}{RESET}")
    print(f"  {'─'*47}")
    print(f"  {RED}{'Total removed':<35} {removed:>12,}{RESET}")
    print(f"  {GREEN}{BOLD}{'Written to output':<35} {stats['written']:>12,}{RESET}")
    print(f"\n  {DIM}Unique passwords capped : {len(capped_log):,}{RESET}")
    print(f"  {DIM}Retention rate          : "
          f"{stats['written']/total*100:.1f}%{RESET}")
    print(f"\n  {GREEN}Output saved to: {args.output}{RESET}")
    print(f"{BOLD}{CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")


if __name__ == "__main__":
    main()
