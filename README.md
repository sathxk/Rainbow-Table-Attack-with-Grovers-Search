# Quantum-Enhanced Rainbow Table Attack System

A hybrid classical-quantum password cracking system that combines rainbow table cryptanalysis with quantum search algorithms (DEGA and Grover's).

## Overview

This project implements a production-scale rainbow table attack system with four attack approaches:

1. **Quantum Attack (DEGA)**: Uses Distributed Exact Grover's Algorithm for deterministic search
2. **Quantum Attack (Standard Grover)**: Uses standard Grover's algorithm for O(√N) search
3. **Classical Attack (Hash Table)**: Uses hash table lookups for O(1) endpoint matching
4. **Classical Attack (Bloom Filter)**: Memory-efficient variant with Bloom filter pre-screening

All approaches achieve approximately **99% accuracy** on the test dataset. The ~1% false negative rate is caused by endpoint collisions in the rainbow table structure.

## Performance Comparison

### System Specifications
- **OS**: Ubuntu 24.04.2 LTS
- **CPU**: Intel Core Ultra 5 125H (14 cores, 18 threads)
- **Storage**: NVMe SSD (PCIe 4.0)
- **Python**: 3.12.3
- **Qiskit**: 1.0.2

### Performance Results (1000 hashes per test set, averaged over 10 runs)

| Configuration | Avg Total Time | Avg Time/Hash | Throughput | Accuracy |
|--------------|----------------|---------------|------------|----------|
| **DEGA 8-qubit** | **7m 29s** | **0.449s** | **2.23 h/s** | 99.0% |
| **DEGA 10-qubit** | **7m 33s** | **0.453s** | **2.21 h/s** | 98.9% |
| Classical + Bloom | 8m 15s | 0.495s | 2.02 h/s | 99.1% |
| Classical (no Bloom) | 8m 19s | 0.499s | 2.00 h/s | 99.0% |
| Grover 8-qubit | 10m 32s | 0.632s | 1.58 h/s | 98.9% |
| DEGA 12-qubit | 10m 45s | 0.645s | 1.55 h/s | 98.8% |
| DEGA 14-qubit | 13m 17s | 0.797s | 1.25 h/s | 99.0% |
| DEGA 16-qubit | 19m 38s | 1.178s | 0.85 h/s | 99.1% |
| Grover 10-qubit | 27m 49s | 1.669s | 0.60 h/s | 99.0% |

**Key Findings:**
- **DEGA 8-qubit achieves best performance** — 10% faster than classical Bloom filter
- **DEGA outperforms standard Grover** — 1.4× faster (8q) and 3.7× faster (10q)
- **99% accuracy across all configurations** — ~1% false negatives due to endpoint collisions
- **Zero false positives** — All uncovered passwords correctly identified as "NOT FOUND"

### DEGA vs Standard Grover

| Metric | Standard Grover (8q) | DEGA (8q) | Advantage |
|--------|---------------------|-----------|-----------|
| **Time per hash** | 0.632s | **0.449s** | **1.4× faster** |
| **Circuit Depth** | ~96 gates | **9 gates** | **10.7× shallower** |
| **Grover Iterations** | 12 | **0** | **No iterations** |
| **Success Rate** | Probabilistic | **Deterministic** | Guaranteed |
| **Algorithm** | Single n-qubit search | ⌊n/2⌋ sub-searches | Distributed |

*DEGA partitions an n-qubit search into multiple smaller searches, achieving constant circuit depth and deterministic results.*

## Quick Start

### Prerequisites

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running Attacks

```bash
# DEGA quantum attack (recommended - fastest and deterministic)
./venv/bin/python demos/quantum_attack.py --qubits 8 --use-dega    # Fastest
./venv/bin/python demos/quantum_attack.py --qubits 10 --use-dega   # Default
./venv/bin/python demos/quantum_attack.py --qubits 12 --use-dega
./venv/bin/python demos/quantum_attack.py --qubits 14 --use-dega
./venv/bin/python demos/quantum_attack.py --qubits 16 --use-dega

# Standard Grover quantum attack
./venv/bin/python demos/quantum_attack.py --qubits 8
./venv/bin/python demos/quantum_attack.py --qubits 10

# Classical attacks
./venv/bin/python demos/classical_attack.py              # Hash table
./venv/bin/python demos/classical_bloom_attack.py        # Bloom filter

# Side-by-side comparison
./venv/bin/python demos/compare_classical_vs_quantum.py --qubits 8
```

All attacks read hashes from test files (1000 hashes: 500 covered + 500 uncovered).

### Using the CLI

```bash
# Crack a single hash
./venv/bin/python -m attack crack 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8

# Build Bloom filter (one-time setup)
./venv/bin/python -m attack build-bloom --n-items 38285442 --fpr 0.001

# Show database info
./venv/bin/python -m attack info
```

## System Architecture

```
Phase 1: Rainbow Table Generation (Classical)
    ↓
    PCFG-guided sampling → Hash-Reduction Chains → Bucketed Storage
    ↓
Phase 2: Attack Phase (Hybrid Classical-Quantum)
    ↓
    Target Hash → Bloom Filter → Bucket Lookup → DEGA/Grover/Linear Search → Password
```

## Phase 1: Rainbow Table Generation

### Password Sample: PCFG-Guided Generation

The rainbow table uses **PCFG (Probabilistic Context-Free Grammar)** to concentrate coverage on high-probability passwords:

```
rockyou.txt (raw dataset)
    ↓
clean_rockyou.py       — removes noise, filters by length
    ↓
split_by_length.py     — splits by password length
    ↓
pcfg_trainer.ipynb     — trains PCFG model per length
    ↓
ruleset.json           — probability tables for generation
```

**8-character model statistics:**
- Training set: 2,966,956 passwords
- Unique structural patterns: 3,220
- Probability mass coverage: 55%

### Current Database Statistics

- **Total chains**: 38,285,442
- **Unique endpoints**: 37,526,594 (98.02%)
- **Endpoint collision rate**: 1.98%
- **Chain length**: 1,000 iterations
- **Password space**: 8-character alphanumeric (lowercase)
- **Hash function**: SHA-1

### Collision Analysis Results

**Endpoint Collisions:**
- Rate: 1.98% (758,848 collisions)
- Distribution: 98% unique, 1.98% 2-way, 0.02% 3-way+
- Maximum: 5 chains per endpoint

**Internal Collisions (disk-based sampling):**
- Sample sizes: 191,427 chains (0.5%) and 382,854 chains (1.0%)
- Collision rate: 0.01148%-0.02174%
- Chains affected: 6.48%-12.62%
- Extrapolated full dataset: 10%-15% chains affected
- Final effective coverage: **95.8%-96.6%**

**Bucket Distribution:**
- Standard deviation: 3.7% of mean (excellent uniformity)
- Overflow rate: 0% (achieved through fill factor design)
- SHA-1-based bucketing validated across all configurations

### Available Qubit Configurations

| Qubits | Bucket Size | Num Buckets | Fill Factor | Database File |
|--------|-------------|-------------|-------------|---------------|
| 8      | 256         | 199,404     | 0.75        | `rainbow_table_8q.db` |
| 10     | 1,024       | 49,851      | 0.75        | `rainbow_table.db` |
| 12     | 4,096       | 12,463      | 0.75        | `rainbow_table_12q.db` |
| 14     | 16,384      | 2,460       | 0.95        | `rainbow_table_14q.db` |
| 16     | 65,536      | 615         | 0.95        | `rainbow_table_16q.db` |

### Redistributing to Different Qubit Configurations

```bash
# Redistribute from base 10-qubit database
./venv/bin/python scripts/redistribute_buckets.py --qubits 8
./venv/bin/python scripts/redistribute_buckets.py --qubits 12
./venv/bin/python scripts/redistribute_buckets.py --qubits 14 --fill-factor 0.95
./venv/bin/python scripts/redistribute_buckets.py --qubits 16 --fill-factor 0.95
```

### Generate Your Own Table

```bash
# Configure in config.json, then:
python -m rainbow_table_generator.main --config config.json
```

## Phase 2: Attack Phase

### DEGA Quantum Attack (Recommended)

**What is DEGA?**

DEGA (Distributed Exact Grover's Algorithm) partitions an n-qubit search into ⌊n/2⌋ smaller sub-searches:

- **Constant circuit depth**: 9 gates (even qubits) or 17 gates (odd qubits)
- **Deterministic success**: 100% guaranteed (no probabilistic failures)
- **No Grover iterations**: Uses partitioned search strategy
- **NISQ-friendly**: Shallow circuits ideal for noisy quantum hardware

**How it works:**
1. Bloom filter pre-screens endpoints (99.9% rejection rate)
2. Load matching bucket from database
3. Partition bucket into ⌊n/2⌋ sub-searches
4. Run DEGA search (deterministic, constant depth)
5. Verify result classically

**Performance (8-qubit - fastest):**
- Time: 0.449s per hash
- Throughput: 2.23 hashes/second
- Circuit depth: 9 gates
- Accuracy: 99.0%

See [DEGA/DEGA_EXPLAINED.md](DEGA/DEGA_EXPLAINED.md) for detailed theory.

### Standard Grover Quantum Attack

**How it works:**
1. Bloom filter pre-screens endpoints (99.9% rejection rate)
2. Load matching bucket from database
3. Pad bucket to 2^n entries
4. Run Grover's search with ⌊π/4 × √N⌋ iterations
5. Verify result classically

**Performance (8-qubit):**
- Time: 0.632s per hash
- Throughput: 1.58 hashes/second
- Circuit depth: ~96 gates
- Grover iterations: 12
- Accuracy: 98.9%

### Classical Attacks

**Standard Classical (Hash Table):**
- Time: 0.499s per hash
- O(1) endpoint lookup
- Accuracy: 99.0%

**Memory-Efficient Classical (Bloom Filter):**
- Time: 0.495s per hash
- Bloom filter pre-screening
- Accuracy: 99.1%

## Accuracy Analysis

### Test Methodology

Each test set contains 1000 hashes:
- **500 covered hashes**: Generated by `generate_covered_hashes.py` (guaranteed to exist in table)
- **500 uncovered hashes**: Random passwords not in table

All nine configurations tested on 10 independent test sets.

### Results

**Covered passwords (500 per test set):**
- Approximately 490-495 correctly identified as "FOUND"
- Approximately 5-10 false negatives (reported as "NOT FOUND")
- False negative rate: ~1-2%

**Uncovered passwords (500 per test set):**
- All 500 correctly identified as "NOT FOUND"
- Zero false positives
- False positive rate: 0%

### Why ~1% False Negatives?

**Root cause: Endpoint collisions**

Validation experiment:
- Created deduplicated rainbow table (all collisions removed)
- Re-ran identical test sets
- Result: **100% accuracy achieved**
- Conclusion: False negatives caused exclusively by endpoint collisions

**Mechanism:** When multiple chains share the same endpoint, only one is stored. The attack retrieves one chain per endpoint, so passwords in other chains with that endpoint cannot be found.

**Design decision:** We retained collisions to represent realistic, production-scale rainbow tables. The 99% accuracy reflects real-world effectiveness.

## Project Structure

```
.
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── config.json                   # System configuration
│
├── attack/                       # Attack phase implementation
│   ├── bloom_filter.py          # Bloom filter pre-screening
│   ├── bucket_loader.py         # Database integration
│   ├── chain_verifier.py        # Classical verification
│   ├── classical_attack.py      # Classical hash table attack
│   ├── classical_bloom_attack.py # Classical Bloom filter attack
│   ├── grover_search.py         # Standard Grover's search
│   ├── orchestrator.py          # Quantum attack orchestrator
│   └── cli.py                   # Command-line interface
│
├── DEGA/                         # DEGA implementation
│   ├── dega_search.py           # Distributed Exact Grover's Algorithm
│   ├── test_dega.py             # DEGA test suite
│   ├── DEGA_EXPLAINED.md        # Theory and explanation
│   └── README.md                # Usage guide
│
├── PCFG/                         # PCFG pipeline
│   ├── clean_rockyou.py         # Dataset cleaning
│   ├── split_by_length.py       # Length-based splitting
│   ├── pcfg_trainer.ipynb       # PCFG model training
│   ├── pcfg_output/             # Trained rulesets (len6-len10)
│   └── split_output/            # Per-length password files
│
├── rainbow_table_generator/     # Table generation
│   ├── bucket_organizer.py      # SHA-1-based bucketing
│   ├── chain_generator.py       # Hash-reduction chains
│   ├── reduction.py             # Hash-to-password mapping
│   ├── storage.py               # SQLite database
│   ├── parallel.py              # Multi-process generation
│   └── main.py                  # Main orchestrator
│
├── demos/                        # Demo scripts
│   ├── quantum_attack.py        # Run quantum attack
│   ├── classical_attack.py      # Run classical attack
│   ├── classical_bloom_attack.py # Run Bloom filter attack
│   └── compare_classical_vs_quantum.py  # Compare approaches
│
├── scripts/                      # Utility scripts
│   ├── redistribute_buckets.py  # Change qubit configuration
│   └── generate_covered_hashes.py # Generate test hashes
│
├── analysis/                     # Analysis tools
│   └── collision_analysis.py    # Collision analysis
│
├── tests/                        # Test suite (349 tests)
│   ├── test_bloom_filter.py
│   ├── test_grover_search.py
│   ├── test_bucket_organizer.py
│   └── ...
│
├── thesis/                       # Thesis documentation
│   ├── Chapter1_Introduction.md
│   ├── Chapter2_Literature_Survey.md
│   ├── Chapter3_System_Architecture.md
│   ├── Chapter4_Implementation.md
│   ├── Chapter5_Results_Analysis.md
│   ├── Chapter6_Conclusion.md
│   └── References.md
│
└── docs/                         # Additional documentation
    ├── ATTACK_PHASE_EXPLAINED.md
    ├── CLASSICAL_ATTACK_EXPLAINED.md
    └── TEST_RESULTS_SUMMARY.md
```

## Testing

```bash
# Run all tests (349 tests)
pytest tests/ -v

# Run specific test suite
pytest tests/test_grover_search.py -v

# With coverage
pytest tests/ --cov=rainbow_table_generator --cov=attack --cov-report=html
```

## Technical Details

### Hash-Reduction Chain

```python
def generate_chain(start_point, chain_length):
    current = start_point
    for i in range(chain_length):
        hash_value = sha1(current)
        current = reduce(hash_value, iteration=i, length=8)
    endpoint = sha1(current)
    return (start_point, endpoint)
```

### Reduction Function

```python
def reduce(hash_value: bytes, iteration: int, password_length: int) -> str:
    """Iteration-dependent reduction (Oechslin 2003)"""
    charset = "abcdefghijklmnopqrstuvwxyz0123456789"
    charset_len = len(charset)
    search_space = charset_len ** password_length
    
    hash_int = int.from_bytes(hash_value, byteorder='big')
    value = (hash_int + iteration) % search_space
    
    password = []
    for _ in range(password_length):
        char_index = value % charset_len
        password.append(charset[char_index])
        value //= charset_len
    
    return ''.join(password)
```

### Bucketing Strategy

```python
# SHA-1-based bucketing with fill factor
num_buckets = ceil(total_chains / (bucket_size * fill_factor))
bucket_key = int(endpoint[:8], 16) % num_buckets
```

## Research Contributions

**Novel Contributions:**

1. **First DEGA + Rainbow Table Integration**
   - Deterministic quantum search with constant circuit depth
   - 1.4-3.7× faster than standard Grover's algorithm
   - 10-22× shallower circuits (9 gates vs 96-400 gates)

2. **Bloom Filter + Quantum Search**
   - 99.9% workload reduction through pre-screening
   - Novel combination not found in prior work

3. **Production-Scale Implementation**
   - 38.3M chains (largest reported quantum rainbow table system)
   - Multiple qubit configurations (8, 10, 12, 14, 16)
   - Comprehensive experimental evaluation (1000 hashes × 10 test sets × 9 configs)

4. **Comprehensive Collision Analysis**
   - Disk-based sampling methodology (191K-382K chains)
   - 19-38× larger scale than traditional approaches
   - Validated reduction function design

5. **PCFG-Guided Generation**
   - 55% probability mass coverage with 38.3M chains
   - Systematic application to rainbow table generation

## Dependencies

```
pyyaml>=6.0          # Configuration
pytest>=7.0          # Testing
pytest-cov>=4.0      # Coverage
qiskit>=1.0          # Quantum simulation
mmh3>=4.0            # MurmurHash3 (Bloom filter)
bitarray>=2.8        # Bit arrays (Bloom filter)
```

## Known Limitations

1. **Quantum simulation overhead**: Real quantum hardware would be significantly faster
2. **Limited coverage**: 38.3M chains cover 1.36% of 8-char alphanumeric space
3. **Single hash function**: SHA-1 only (no SHA-256, MD5, etc.)
4. **Lowercase only**: No uppercase or special characters
5. **Endpoint collisions**: ~1% false negative rate due to structural limitation

## Future Work

- Deploy on real quantum hardware (IBM Quantum, IonQ)
- Scale to 100M+ chains for better coverage
- Extend to longer passwords (9-10 characters)
- Support multiple hash functions (SHA-256, MD5, bcrypt)
- GPU acceleration for classical chain walking
- Modern hash function support (Argon2, scrypt)

## References

- **DEGA**: Distributed Exact Grover's Algorithm - Deterministic quantum search
- **QIris**: Lee et al., "QIris: Quantum Implementation of Rainbow Table Attacks" (2024)
- **Oechslin**: "Making a faster cryptanalytic time-memory trade-off" (2003)
- **Grover**: "A fast quantum mechanical algorithm for database search" (1996)

## License

This project is for educational and research purposes only.

---

**Status**: Production-ready. 38.3M chains, 98.02% endpoint diversity, 1.98% collision rate, 95.8%-96.6% effective coverage. DEGA 8-qubit achieves best performance (0.449s/hash, 2.23 h/s) with 99% accuracy. All configurations achieve zero false positives and ~99% overall accuracy. Comprehensive testing completed (1000 hashes × 10 test sets × 9 configurations).
