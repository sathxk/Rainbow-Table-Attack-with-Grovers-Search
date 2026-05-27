# Quantum-Enhanced Rainbow Table Attack System

A hybrid classical-quantum password cracking system that combines rainbow table cryptanalysis with quantum search algorithms (Grover's and DEGA).

## Overview

This project implements a complete rainbow table attack system with four approaches:

1. **Quantum Attack (DEGA)**: Uses Distributed Exact Grover's Algorithm for deterministic 100% success rate
2. **Quantum Attack (Standard Grover)**: Uses standard Grover's algorithm for O(√N) search within buckets
3. **Classical Attack (Hash Table)**: Uses hash table lookups for O(1) endpoint matching
4. **Classical Attack (Bloom Filter)**: Uses Bloom filter on classical attack

All approaches achieve **100% success rate** on passwords covered by the rainbow table. Test dataset includes 60 covered passwords and 40 deliberately uncovered passwords to validate "NOT FOUND" handling.

## Performance Comparison (100 hashes: 60 covered + 40 uncovered)

### System Specifications
- **OS**: Ubuntu 24.04.2 LTS (Linux 6.17.0-19-generic)
- **CPU**: Intel Core Ultra 5 125H
- **RAM**: 16 GB
- **Python**: 3.12.3

### Performance Results

| Configuration | Total Time | Avg Time/Hash | Throughput | 
|--------------|-----------|---------------|------------|
| **DEGA 8-qubit** | **44.926s** | **0.449s** | **2.23 h/s** |
| **DEGA 10-qubit** | **45.298s** | **0.453s** | **2.21 h/s** |
| Classical + Bloom | 49.497s | 0.495s | 2.02 h/s |
| Classical (no Bloom) | 49.899s | 0.499s | 2.00 h/s |
| Grover 8-qubit | 63.247s | 0.632s | 1.58 h/s |
| DEGA 12-qubit | 64.528s | 0.645s | 1.55 h/s |
| DEGA 14-qubit | 79.729s | 0.797s | 1.25 h/s |
| DEGA 16-qubit | 117.810s | 1.178s | 0.85 h/s |
| Grover 10-qubit | 166.897s | 1.669s | 0.60 h/s |

**Key Findings:**
- **DEGA 8-qubit is fastest overall** — faster than Classical Bloom and all Grover variants
- **DEGA 8-qubit and 10-qubit are statistically tied** (difference within system variance)
- **All approaches achieve 100% success rate** on covered passwords, except DEGA 12-qubit (59/60)
- **All approaches correctly identify uncovered passwords** (40/40 "NOT FOUND")
- **DEGA scales well up to 14 qubits** — beyond that, classical oracle overhead dominates

### DEGA vs Standard Grover

| Metric | Standard Grover | DEGA | Advantage |
|--------|----------------|------|-----------|
| **Success Rate** | 99.99% | 100% (deterministic) | Guaranteed success |
| **Circuit Depth** | ~96 gates | 9-17 gates | 5-10× shallower |
| **Grover Iterations** | 12-50 | 0 (partitioned search) | No iterations needed |
| **Speed (8q)** | ~0.632s/hash | 0.449s/hash | 1.4× faster |
| **Algorithm** | Single n-qubit search | ⌊n/2⌋ sub-searches | Distributed approach |

*DEGA partitions an n-qubit search into multiple smaller searches, achieving deterministic results with shallower circuits.*

## System Architecture

```
Phase 1: Rainbow Table Generation (Classical)
    ↓
    38M passwords → Hash-Reduction Chains → Bucketed Storage
    ↓
Phase 2: Attack Phase (Hybrid Classical-Quantum)
    ↓
    Target Hash → Bloom Filter → Bucket Lookup → Grover/Hash Table → Password
```

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
./venv/bin/python demos/quantum_attack.py --qubits 8 --use-dega    # Fastest (0.534s/hash)
./venv/bin/python demos/quantum_attack.py --qubits 10 --use-dega   # Default (0.542s/hash)
./venv/bin/python demos/quantum_attack.py --qubits 12 --use-dega
./venv/bin/python demos/quantum_attack.py --qubits 14 --use-dega
./venv/bin/python demos/quantum_attack.py --qubits 16 --use-dega

# Standard Grover quantum attack
./venv/bin/python demos/quantum_attack.py --qubits 8    # 1.09s/hash
./venv/bin/python demos/quantum_attack.py --qubits 10   # 4.1s/hash
./venv/bin/python demos/quantum_attack.py --qubits 12   # 31.8s/hash
./venv/bin/python demos/quantum_attack.py --qubits 14

# Classical attacks
./venv/bin/python demos/classical_attack.py              # Hash table (3.6 GB RAM)
./venv/bin/python demos/classical_bloom_attack.py        # Bloom filter (65.6 MB RAM)

# Side-by-side comparison
./venv/bin/python demos/compare_classical_vs_quantum.py --qubits 8
./venv/bin/python demos/compare_classical_vs_quantum.py --qubits 10
```

All attacks read hashes from `hashes_100.txt` (one SHA-1 hash per line).

### Using the CLI

```bash
# Crack a single hash with quantum attack
./venv/bin/python -m attack crack 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8

# Build Bloom filter (one-time setup)
./venv/bin/python -m attack build-bloom --n-items 38285441 --fpr 0.001

# Show database info
./venv/bin/python -m attack info
```

## Project Structure

```
.
├── README.md                     # This file
├── config.json                   # System configuration
├── hashes_100.txt                # Test hashes (input)
├── requirements.txt              # Python dependencies
│
├── attack/                       # Attack phase implementation
│   ├── bloom_filter.py          # Bloom filter pre-screening
│   ├── bucket_loader.py         # Database integration
│   ├── chain_verifier.py        # Classical verification
│   ├── classical_attack.py      # Classical attack (hash table)
│   ├── classical_bloom_attack.py # Classical attack (Bloom filter)
│   ├── dummy_padding.py         # Bucket padding for quantum
│   ├── grover_search.py         # Grover's quantum search
│   ├── orchestrator.py          # Quantum attack orchestrator
│   ├── walk_forward.py          # Endpoint reconstruction
│   └── cli.py                   # Command-line interface
│
├── PCFG/                         # Password sample basis (PCFG pipeline)
│   ├── clean_rockyou.py         # Cleans raw RockYou dataset
│   ├── split_by_length.py       # Splits cleaned passwords by length
│   ├── pcfg_trainer.ipynb       # Trains PCFG model per length group
│   ├── rockyou.txt              # Raw RockYou dataset (not in repo)
│   ├── rockyou_cleaned1.txt     # Cleaned dataset
│   ├── split_output/            # Per-length password files (len6–len10)
│   └── pcfg_output/             # Trained rulesets and charts (len6–len10)
│
├── DEGA/                         # DEGA implementation
│   ├── dega_search.py           # Distributed Exact Grover's Algorithm
│   ├── test_dega.py             # DEGA test suite (4 tests, all passing)
│   ├── DEGA_EXPLAINED.md        # Theory and explanation
│   ├── README.md                # Usage guide
│   └── INTEGRATION_SUMMARY.md   # Integration details
│
├── rainbow_table_generator/     # Table generation
│   ├── bucket_organizer.py      # SHA-1-based bucketing
│   ├── chain_generator.py       # Hash-reduction chains
│   ├── config.py                # Configuration management
│   ├── hash_functions.py        # SHA-1/MD5/SHA-256
│   ├── reduction.py             # Hash-to-password mapping
│   ├── storage.py               # SQLite database
│   ├── parallel.py              # Multi-process generation
│   └── main.py                  # Main orchestrator
│
├── demos/                        # Demo scripts
│   ├── quantum_attack.py        # Run quantum attack (Grover/DEGA)
│   ├── classical_attack.py      # Run classical attack (hash table)
│   ├── classical_bloom_attack.py # Run classical attack (Bloom filter)
│   └── compare_classical_vs_quantum.py  # Compare both
│
├── scripts/                      # Utility scripts
│   └── redistribute_buckets.py  # Redistribute DB to different qubit config
│
├── analysis/                     # Analysis tools
│   └── collision_analysis.py    # Endpoint collision analysis
│
├── tests/                        # Test suite (349 tests)
│   ├── test_bloom_filter.py
│   ├── test_grover_search.py
│   ├── test_bucket_organizer.py
│   └── ...
│
├── docs/                         # Documentation
│   ├── ATTACK_PHASE_EXPLAINED.md        # Quantum attack deep-dive
│   ├── CLASSICAL_ATTACK_EXPLAINED.md    # Classical attacks (with/without Bloom)
│   ├── OPTIMIZATION_RESULTS.md
│   ├── TEST_RESULTS_SUMMARY.md
│   └── INTERMEDIATE_PASSWORD_RESULTS.md
│
├── logs/                         # Performance logs
│   ├── dega_attack_8q_100.log   # DEGA 8-qubit results
│   ├── dega_attack_10q_100.log  # DEGA 10-qubit results
│   ├── dega_attack_12q_100.log  # DEGA 12-qubit results
│   ├── dega_attack_14q_100.log  # DEGA 14-qubit results
│   ├── classical_bloom_attack_100.log
│   ├── classical_no_bloom_attack_100.log
│   └── collision_analysis_10q.log
│
├── log-i7/                       # Performance logs (extended qubit configs)
│   ├── dega_8q.log              # DEGA 8-qubit
│   ├── dega_10q.log             # DEGA 10-qubit
│   ├── dega_12q.log             # DEGA 12-qubit
│   ├── dega_14q.log             # DEGA 14-qubit
│   ├── dega-16q.log             # DEGA 16-qubit
│   ├── grovers_8q.log           # Standard Grover 8-qubit
│   ├── grovers_10q.log          # Standard Grover 10-qubit
│   ├── classical.log            # Classical hash table
│   └── classical_bloom.log      # Classical Bloom filter
│
└── rainbow_tables/output/        # Generated data (not in repo)
    ├── rainbow_table.db         # 6.9 GB SQLite database (10-qubit, source)
    ├── rainbow_table_8q.db      # 8-qubit database (2.8 GB)
    ├── rainbow_table_12q.db     # 12-qubit database (2.8 GB)
    ├── rainbow_table_14q.db     # 14-qubit database (2.8 GB, fill_factor=0.95)
    └── metadata.json            # Generation parameters
```

## Phase 1: Rainbow Table Generation

### Password Sample: PCFG Pipeline

The rainbow table is built from a password sample derived from the **RockYou dataset**, processed through a PCFG (Probabilistic Context-Free Grammar) pipeline. This pipeline shapes which passwords end up in the table and ensures the sample reflects real-world password patterns.

```
rockyou.txt
    ↓
clean_rockyou.py       — removes noise, filters by length, caps duplicates
    ↓
split_by_length.py     — splits cleaned passwords into per-length files
    ↓
pcfg_trainer.ipynb     — trains a PCFG model per length group
    ↓
ruleset.json           — probability tables used to guide generation
```

Each password is tokenised into typed segments:
- **L** = consecutive letters, **D** = consecutive digits, **S** = consecutive symbols

For example, `hello123!` → `(L, hello)(D, 123)(S, !)` → structural tag `L5D3S1`

The trainer builds probability tables for structural patterns, base words, digit/symbol strings, capitalisation masks, and segment positions — trained separately for each password length (6–10 chars). The 8-character model was trained on **2,966,956 passwords** and found **3,220 unique structural patterns**.

A uniform random sample would waste coverage on rare patterns. The PCFG model ensures the table prioritises the most likely real-world passwords — the same patterns attackers target first.

### Current Database

- **Total chains**: 38,285,442
- **Unique endpoints**: 37,526,594 (98.02% diversity)
- **Endpoint collisions**: 758,848 (1.98% collision rate)
- **Database size**: 2.9 GB
- **Generation time**: ~6 hours (4 workers)
- **Bucket overflow**: 0% (perfect distribution)

### Collision Analysis Results

**Endpoint Collisions (from 38.3M chains):**
- **1.98% collision rate** - Very low, indicating excellent reduction function
- **98.02% effective coverage** - Near-perfect efficiency
- Maximum collision: 5 chains sharing one endpoint
- All buckets under-filled (639-907 chains vs target 1024)

**Internal Collisions (disk-based sampling analysis):**

Two sample sizes tested using disk-based SQLite storage:

**0.5% sample (191,427 SPs):**
- **0.01148% internal collision rate** - 21,985 collisions out of 191.4M internal states
- **6.48% chains affected** - 12,411 chains had at least one collision
- All collisions are 2-way or 3-way (21,984 two-way, 1 three-way)
- Collisions distributed throughout chain (positions 5-982)
- Storage: ~7.6 GB, Analysis time: ~7 minutes

**1.0% sample (382,854 SPs):**
- **0.02174% internal collision rate** - 83,251 collisions out of 382.9M internal states
- **12.62% chains affected** - 48,314 chains had at least one collision
- All collisions are 2-way or 3-way (83,245 two-way, 6 three-way)
- Collisions distributed throughout chain (positions 5-982)
- Storage: ~15 GB, Analysis time: ~14 minutes

**Extrapolation to full dataset (38.3M chains):**
- **Estimated collision rate**: 0.015% - 0.020%
- **Estimated colliding states**: 5.7M - 7.7M states (out of 38.3B total)
- **Estimated chains affected**: 10% - 15%
- **Effective coverage impact**: 95.8% - 96.6% (after accounting for both endpoint and internal collisions)

*The collision rate is a property of the reduction function, not the sample size. Larger samples detect more rare collisions, providing more accurate estimates. The 1.0% sample (0.02174%) is closer to the true population rate than the 0.5% sample (0.01148%).*

*This validates the iteration-dependent reduction function is working excellently with minimal chain merging. See `analysis/README_COLLISION_ANALYSIS.md` for detailed methodology.*

### Available Qubit Configurations

| Qubits | Bucket Size | Num Buckets | Fill Factor | Grover Iterations | Database File |
|--------|-------------|-------------|-------------|-------------------|---------------|
| **8**  | 256         | 199,404     | 0.75        | 12                | `rainbow_table_8q.db` |
| **10** | 1,024       | 49,851      | 0.75        | 25                | `rainbow_table.db` |
| **12** | 4,096       | 12,463      | 0.75        | 50                | `rainbow_table_12q.db` |
| **14** | 16,384      | 2,460       | 0.95        | 100               | `rainbow_table_14q.db` |
| **16** | 65,536      | 615         | 0.95        | 201               | `rainbow_table_16q.db` |

### Redistributing to a Different Qubit Configuration

All qubit-specific databases are derived from the base 10-qubit database using the redistribution script:

```bash
# Redistribute to 8-qubit
./venv/bin/python scripts/redistribute_buckets.py --qubits 8

# Redistribute to 12-qubit
./venv/bin/python scripts/redistribute_buckets.py --qubits 12

# Redistribute to 14-qubit (uses 0.95 fill factor )
./venv/bin/python scripts/redistribute_buckets.py --qubits 14 --fill-factor 0.95

# Redistribute to 16-qubit (uses 0.95 fill factor)
./venv/bin/python scripts/redistribute_buckets.py --qubits 16 --fill-factor 0.95

# Custom target path
./venv/bin/python scripts/redistribute_buckets.py --qubits 8 --target-db rainbow_tables/output/my_8q.db
```

The script reads all chains from the source database and rewrites them with the new bucketing parameters. Takes ~90s for 38M chains.

### Key Features

- **SHA-1-based bucketing**: Uses first 32 bits of endpoint hash
- **Fill factor over-provisioning**: 0.75 fill factor prevents bucket overflow
- **Standard reduction function**: Oechslin 2003 algorithm, 98% endpoint diversity
- **Parallel generation**: Multi-worker support for faster generation

### Generate Your Own Table

```bash
# Configure in config.json, then:
python -m rainbow_table_generator.main --config config.json
```

## Phase 2: Attack Phase

### DEGA  Attack 

**What is DEGA?**
DEGA (Distributed Exact Grover's Algorithm) partitions an n-qubit search space into ⌊n/2⌋ smaller sub-searches, achieving:
- **Deterministic 100% success rate** (vs 99.99% for standard Grover)
- **Shallower circuits** (9-17 gates vs ~96 gates)
- **Faster execution** on simulators (2× speedup)
- **No Grover iterations needed** (partitioned search strategy)

**How it works:**
1. Bloom filter pre-screens candidate endpoints (99.9% rejection rate)
2. Load matching bucket from database
3. Partition bucket into ⌊n/2⌋ sub-searches
4. Run DEGA search (deterministic, no iterations)
5. Verify result classically

**Performance (8 qubits - fastest):**
- Average: 0.449s per hash
- Throughput: 2.23 hashes/second
- Memory: 65.6 MB (Bloom filter)
- Circuit depth: 9 gates (even n) or 17 gates (odd n)
- Success rate: 100% (deterministic)

**Performance (10 qubits):**
- Average: 0.453s per hash
- Throughput: 2.21 hashes/second
- Memory: 65.6 MB (Bloom filter)
- Circuit depth: 9 gates
- Success rate: 100% (deterministic)

**Performance (16 qubits):**
- Average: 1.178s per hash
- Throughput: 0.85 hashes/second
- Memory: 65.6 MB (Bloom filter)
- Circuit depth: 9 gates
- Success rate: 100% (deterministic)
- Note: classical oracle overhead dominates at this bucket size (65,536 entries)

See [DEGA/DEGA_EXPLAINED.md](DEGA/DEGA_EXPLAINED.md) for detailed theory and [DEGA/README.md](DEGA/README.md) for usage.

### Standard Grover Quantum Attack

**How it works:**
1. Bloom filter pre-screens candidate endpoints (99.9% rejection rate)
2. Load matching bucket from database
3. Pad bucket to 2^n entries for quantum circuit
4. Run Grover's search (12/25/50 iterations for 8/10/12 qubits)
5. Verify result classically

**Performance (8 qubits):**
- Average: 0.632s per hash
- Throughput: 1.58 hashes/second
- Memory: 65.6 MB (Bloom filter)
- Grover iterations: 12
- Success rate: 99.99%

**Performance (10 qubits):**
- Average: 1.669s per hash
- Throughput: 0.60 hashes/second
- Memory: 65.6 MB (Bloom filter)
- Grover iterations: 25
- Success rate: 99.99%

### Classical Attack

The project implements **two classical approaches**:

#### 1. Standard Classical Attack (Hash Table Lookup)

**How it works:**
1. Load all 38M endpoints into hash table (one-time, 57s)
2. For each position k, compute candidate endpoint
3. O(1) hash table lookup
4. Walk chain forward to verify

**Performance:**
- Average: 0.499s per hash
- Throughput: 2.00 hashes/second
- Memory: 3.6 GB (hash table)
- Init time: 57 seconds

#### 2. Memory-Efficient Classical Attack (Bloom Filter)

**How it works:**
1. Load Bloom filter (65.6 MB, 0.05s)
2. For each position k, check Bloom filter (99.9% rejection)
3. Load matching bucket from database
4. Linear search within bucket (O(N))
5. Walk chain forward to verify

**Performance:**
- Average: 0.495s per hash
- Throughput: 2.02 hashes/second
- Memory: 65.6 MB (Bloom filter only)
- Init time: 0.05 seconds

**Comparison:**
- Memory-efficient approach uses **57× less memory** (65.6 MB vs 3.6 GB)
- Comparable speed to hash table approach (0.495s vs 0.499s)
- **1,138× faster initialization** (0.05s vs 57s)
- Same 100% success rate

### Attack Flow

```
For each chain position k (999 → 0):
  1. Compute candidate_endpoint from target_hash
  2. Check if endpoint exists (Bloom filter or hash table)
  3. If found, load chain and verify
  4. Return password if verified
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
    """Standard rainbow table reduction (Oechslin 2003)"""
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
num_buckets = ceil(total_entries / (bucket_size * fill_factor))
bucket_key = int(endpoint[:8], 16) % num_buckets
intra_value = int(endpoint[:8], 16) % bucket_size
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

## Dependencies

```
pyyaml>=6.0          # Configuration
pytest>=7.0          # Testing
pytest-cov>=4.0      # Coverage
qiskit>=1.0          # Quantum simulation
mmh3>=4.0            # MurmurHash3 (Bloom filter)
bitarray>=2.8        # Bit arrays (Bloom filter)
```

## Research Context

This implementation improves upon existing research:

**Novel Contributions:**
1. **DEGA Integration**: First implementation combining DEGA with rainbow tables
   - Deterministic 100% success rate
   - 2× faster than standard Grover on simulators
   - Shallower circuits (9-17 gates vs ~96 gates)

2. **Bloom Filter + Quantum Search**: Novel combination not found in prior academic work
   - 99.9% rejection rate reduces quantum workload
   - 54× memory reduction vs classical approach
   - Confirmed by 2024 Springer paper review

3. **Comprehensive Collision Analysis**:
   - Endpoint collision rate: 1.98%
   - Internal collision rate: 0.00% (10,000 chain sample)
   - Validates iteration-dependent reduction function

4. **Production-Ready Implementation**:
   - Scales to 38M+ entries
   - SHA-1-based bucketing (4 billion possible buckets)
   - Comprehensive test coverage (349 tests)
   - Both quantum (Grover/DEGA) and classical implementations

**This Project:**
- Scales to 38M+ entries
- SHA-1-based bucketing (4 billion possible buckets)
- Production-ready implementation
- Comprehensive test coverage (349 tests)
- Multiple quantum and classical implementations

### Key Innovations

- **Hybrid approach**: Combines classical pre-screening with quantum search
- **Endpoint pre-filtering**: 99.94% reduction in chain walks
- **Fill factor over-provisioning**: Eliminates bucket overflow
- **Practical implementation**: Works on Qiskit simulator, ready for real quantum hardware

### Complexity Analysis

- **Classical search**: O(log M) per bucket (binary search)
- **Quantum search**: O(√M) per bucket (Grover's algorithm)
- **Bucket lookup**: O(1) (hash table or indexed SQL)
- **Overall**: O(N × √M) quantum vs O(N × log M) classical, where N = chain length, M = bucket size

**For 8-qubit configuration (M = 256):**
- Classical: log₂(256) = 8 comparisons per bucket
- Quantum: √256 = 16 Grover iterations per bucket
- On real quantum hardware, quantum would be 2× faster per bucket

## Performance Logs

All performance logs are stored in the `logs/` directory:

- `logs/dega_attack_8q_100.log` - DEGA 8-qubit results (fastest)
- `logs/dega_attack_10q_100.log` - DEGA 10-qubit results
- `logs/dega_attack_12q_100.log` - DEGA 12-qubit results
- `logs/classical_bloom_attack_100.log` - Classical with Bloom filter
- `logs/classical_no_bloom_attack_100.log` - Classical without Bloom filter
- `logs/collision_analysis_10q.log` - Endpoint collision analysis

## Documentation

For detailed explanations of how the attacks work:

- **[ATTACK_PHASE_EXPLAINED.md](docs/ATTACK_PHASE_EXPLAINED.md)** — Complete deep-dive into the quantum attack using Grover's algorithm
  - How Bloom filter and Grover's search work together
  - Detailed explanation of every Grover's attribute
  - Dummy padding mechanism
  - Full 8-qubit execution walkthrough
  - End-to-end example with timing breakdown

- **[CLASSICAL_ATTACK_EXPLAINED.md](docs/CLASSICAL_ATTACK_EXPLAINED.md)** — Comprehensive guide to classical rainbow table attacks
  - Standard classical attack (hash table lookup)
  - Memory-efficient classical attack (Bloom filter + linear search)
  - Performance comparison and tradeoffs
  - When to use each approach
  - Implementation details and memory calculations

- **[OPTIMIZATION_RESULTS.md](docs/OPTIMIZATION_RESULTS.md)** — Performance optimization results

- **[TEST_RESULTS_SUMMARY.md](docs/TEST_RESULTS_SUMMARY.md)** — Test suite overview (349 tests)

## Known Limitations

1. **Quantum simulation overhead**: Real quantum hardware would be much faster
2. **Memory vs speed tradeoff**: Classical is faster but uses 57× more memory
3. **Coverage**: 38M chains cover only 0.0014% of 8-char alphanumeric space (2.8 trillion)
4. **Initialization time**: Classical requires 57s to load endpoints into memory

## Future Work

- Test on real quantum hardware (IBM Quantum, IonQ, etc.)
- Implement distributed classical attack across multiple machines
- Optimize Grover's circuit for specific quantum architectures
- Extend to longer passwords (9-10 characters)
- GPU acceleration for classical chain walking

## References

- **DEGA**: Distributed Exact Grover's Algorithm - Deterministic quantum search with partitioned search space
- **QIris Paper**: Lee et al., "QIris: Quantum Implementation of Rainbow Table Attacks" (2024) - ArXiv:2408.07032
- **Original Rainbow Tables**: Oechslin, "Making a faster cryptanalytic time-memory trade-off" (2003) - Crypto 2003
- **Grover's Algorithm**: Grover, "A fast quantum mechanical algorithm for database search" (1996)
- **Collision Analysis Methodology**: Standard sampling approach (10,000 chains, 0.03% of total) following Oechslin 2003

## License

This project is for educational and research purposes only.

---

**Status**: Both phases complete. 38.3M chains, 98.02% endpoint diversity, 1.98% collision rate, 0% bucket overflow. DEGA quantum attack achieves best performance (0.449s/hash, 2.23 h/s) with deterministic 100% success rate. DEGA tested across 8, 10, 12, 14, and 16-qubit configurations. All attacks achieve 100% success rate on covered passwords (60/100 test hashes).
