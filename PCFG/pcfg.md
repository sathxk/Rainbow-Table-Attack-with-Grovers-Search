# PCFG-Based Password Set Generation — Detailed Methodology

## Overview

This document describes the methodology used to generate `wordset_len8.txt`, a set of 38,285,441 length-8 candidate passwords derived from the RockYou 2009 breach dataset using a Probabilistic Context-Free Grammar (PCFG) pipeline. This password set forms the input to a hybrid classical-quantum rainbow table attack prototype, where PCFG is used to reduce and structure the search space prior to Grover's algorithm-based quantum search.

---

## 1. Raw Data

The starting point is `rockyou.txt` — a plaintext file of approximately 14 million passwords leaked from the RockYou breach in 2009. It is a raw database dump, meaning it contains encoding errors, SQL artifacts, email addresses, duplicate entries, and passwords of wildly varying lengths.

---

## 2. Length Analysis

Before any cleaning, `analyze_lengths.ipynb` was run on the raw file to understand the length distribution. This produced a frequency table and bar chart showing how passwords were distributed across lengths. Based on the cumulative coverage table, a range of **6 to 10 characters** was selected — this range covers the vast majority of real-world passwords while excluding very short noise entries and unusually long ones.

---

## 3. Cleaning

`clean_rockyou.py` was run on `rockyou.txt` with the following parameters:

```
--min_length 6
--max_length 10
--freq_cap   10
```

The script made two passes over the raw file. The first pass counted how many times each unique password appeared. The second pass applied the following filters in sequence to every line:

- Leading and trailing whitespace was stripped
- Empty lines were discarded
- Lines containing encoding errors (UTF-8 replacement characters) were discarded
- Lines matching noise patterns — email addresses, URLs, SQL dump lines, non-printable characters — were discarded
- Passwords shorter than 6 characters were discarded
- Passwords longer than 10 characters were discarded
- Passwords that had already appeared 10 times in the output were discarded — this is **frequency dampening**, which preserves structural diversity in the dataset without completely removing popular passwords

The output was `rockyou_cleaned1.txt` — a noise-free file of passwords within the 6–10 character range, with no single password appearing more than 10 times.

---

## 4. Splitting by Length

`split_by_length.py` was run on `rockyou_cleaned1.txt`. It read the file once and distributed each password into a bucket based on its character length, producing five files:

```
split_output/
├── rockyou_len6.txt
├── rockyou_len7.txt
├── rockyou_len8.txt
├── rockyou_len9.txt
└── rockyou_len10.txt
```

The reason for splitting is that PCFG training and password generation are more meaningful when confined to a single length — structural patterns like `L6D2` only make sense in the context of 8-character passwords.

---

## 5. PCFG Training

`pcfg_trainer.ipynb` was run with `rockyou_len8.txt` as input. Every password in the file was tokenised into typed segments using a regex that identified consecutive runs of:

- **L** — letters
- **D** — digits
- **S** — symbols

For example:

| Password | Segments | Structural Tag |
|---|---|---|
| `dragon12` | `(L, dragon)(D, 12)` | `L6D2` |
| `password` | `(L, password)` | `L8` |
| `hello123` | `(L, hello)(D, 123)` | `L5D3` |

After tokenising every password, the trainer counted frequencies across the following dimensions:

- **Structural patterns** — the full skeleton tag of each password
- **Base words** — letter segments stored in lowercase, indexed by character length
- **Capitalisation masks** — the upper/lower pattern of each letter segment (e.g. `Ullllll` for first-letter capitalised)
- **Digit strings** — actual digit sequences, indexed by character length
- **Symbol strings** — actual symbol sequences
- **Digit and symbol positions** — whether each segment appeared at the start, middle, or end of the password

Every counter was then converted to a probability table by dividing each count by the total. The top structural patterns observed for length-8 passwords were:

| Pattern | Count | Probability |
|---|---|---|
| `L8` | 757,634 | 25.54% |
| `L6D2` | 485,884 | 16.38% |
| `D8` | 428,311 | 14.44% |
| `L4D4` | 259,975 | 8.76% |
| `L7D1` | 223,301 | 7.53% |
| `L5D3` | 171,265 | 5.77% |

The trained ruleset was saved to `pcfg_output/pcfg_len8/ruleset.json`, a structured JSON file containing all probability tables including `base_words_by_length` — base words grouped by character length for efficient lookup during generation.

---

## 6. Pattern Selection

From the top structural patterns, the following four were selected for generation:

| Pattern | Probability | Meaning |
|---|---|---|
| `L8` | 25.54% | 8 consecutive letters |
| `L6D2` | 16.38% | 6 letters followed by 2 digits |
| `L7D1` | 7.53% | 7 letters followed by 1 digit |
| `L5D3` | 5.77% | 5 letters followed by 3 digits |

Two patterns were deliberately excluded:

**`D8` — excluded.** All-digit passwords are an outdated pattern largely associated with older systems such as WiFi passwords. They are not representative of modern human password behaviour and would skew the dataset without adding meaningful coverage for the attack.

**`L4D4` — deferred.** With approximately 3,500 four-letter base words and 4,500 four-digit strings, this pattern alone would produce approximately 15.75 million combinations — disproportionately inflating the dataset at prototype stage. It is deferred for later inclusion.

The combined probability mass of the four selected patterns is approximately **55%** of all length-8 passwords in the dataset.

---

## 7. Password Set Generation

`wordset_generator.ipynb` was run with the four selected patterns. The generator read `ruleset.json` and for each pattern computed the **cartesian product** of its component slots:

- For every `L` slot — all base words of the matching length from `base_words_by_length`, lowercased
- For every `D` slot — all digit strings of the matching length from `digit_strings`

The **lowercase-only capitalisation mask** was applied throughout — no mixed-case or all-caps variants were generated. This decision was made because the vast majority of real-world passwords use all-lowercase letters, and restricting to a single cap mask reduces dataset size without meaningfully reducing coverage.

Passwords were streamed directly to disk using `itertools.product` one at a time, avoiding loading the entire candidate set into memory. The output was:

```
wordset_output/wordset_len8.txt
38,285,441 passwords
340 MB
```

---

## 8. Summary of Key Design Decisions

| Decision | Choice | Justification |
|---|---|---|
| Length range | 6–10 characters | Covers the majority of real-world passwords |
| Frequency cap | 10 occurrences | Preserves diversity without full deduplication |
| Training scope | Length 8 only | PCFG structural patterns are length-specific |
| Capitalisation mask | Lowercase only | Most common real-world pattern; keeps set tractable |
| `D8` excluded | Yes | Outdated all-digit pattern, not representative |
| `L4D4` excluded | Yes (deferred) | Combinatorial explosion at prototype scale |
| Generation method | Exhaustive cartesian product | Ensures complete coverage of the learned grammar |
| Output streaming | `itertools.product` to disk | Memory-efficient for large outputs |

---

## 9. Output File Structure

```
PCFG/
├── split_output/
│   ├── rockyou_len6.txt
│   ├── rockyou_len7.txt
│   ├── rockyou_len8.txt
│   ├── rockyou_len9.txt
│   └── rockyou_len10.txt
├── pcfg_output/
│   └── pcfg_len8/
│       ├── ruleset.json
│       ├── probability_tables.txt
│       └── charts/
├── wordset_output/
│   └── wordset_len8.txt        <- 38,285,441 passwords, 340 MB
├── analyze_lengths.ipynb
├── pcfg_trainer.ipynb
├── wordset_generator.ipynb
├── clean_rockyou.py
├── split_by_length.py
├── rockyou.txt
└── rockyou_cleaned1.txt
```

---

## 10. Limitations and Future Work

- The RockYou dataset is from 2009 and reflects older password policies. Recent breach statistics (RockYou2024, Pwdb-Public) suggest the structural patterns remain broadly consistent but should be referenced for validation in the final research.
- `L4D4` has been deferred and should be incorporated with a digit string cap to avoid combinatorial explosion.
- Only the lowercase capitalisation mask has been applied. Future iterations could include the top 2–3 masks (e.g. first-letter capitalised) to improve coverage of real-world passwords.
- The wordset currently covers approximately 55% of the probability mass for length-8 passwords. Adding `L4D4` would raise this to approximately 64%.
