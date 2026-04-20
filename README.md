# Quantum-Enhanced Rainbow Table Attack System

A hybrid classical-quantum password cracking system that combines rainbow table cryptanalysis with Grover's quantum search algorithm.

## Overview

This project implements a complete rainbow table attack system with two approaches:

1. **Quantum Attack**: Uses Grover's algorithm for O(√N) search within buckets
2. **Classical Attack**: Uses hash table lookups for O(1) endpoint matching

Both approaches achieve 100% success rate on the test dataset, with different performance characteristics.

## Performance Comparison

| Metric | Classical | Quantum | Notes |
|--------|-----------|---------|-------|
| **Speed** | 0.8s/hash | 4.1s/hash | Classical 5× faster (on simulator) |
| **Memory** | 3.6 GB | 65 MB | Quantum 57× more efficient |
| **Init Time** | 57s | 0.05s | Quantum 1,138× faster |
| **Success Rate** | 100% | 100% | Both perfect |

*Note: Quantum performance measured on classical simulator. Real quantum hardware would be significantly faster.*

## System Architecture

```
Phase 1: Rainbow Table Generation (Classical)
    ↓
    38M passwords → Hash-Reduction Chains → Bucketed Storage (SQLite)
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
# Quantum attack (Grover's search)
./venv/bin/python examples/quantum_attack.py

# Classical attack (hash table lookup)
./venv/bin/python examples/classical_attack.py

# Side-by-side comparison
./venv/bin/python examples/compare_classical_vs_quantum.py
```

All attacks read hashes from `hashes.txt` (one SHA-1 hash per line).

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
├── hashes.txt                    # Test hashes (input)
├── requirements.txt              # Python dependencies
│
├── attack/                       # Attack phase implementation
│   ├── bloom_filter.py          # Bloom filter pre-screening
│   ├── bucket_loader.py         # Database integration
│   ├── chain_verifier.py        # Classical verification
│   ├── classical_attack.py      # Classical attack (hash table)
│   ├── dummy_padding.py         # Bucket padding for quantum
│   ├── grover_search.py         # Grover's quantum search
│   ├── orchestrator.py          # Quantum attack orchestrator
│   ├── walk_forward.py          # Endpoint reconstruction
│   └── cli.py                   # Command-line interface
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
├── examples/                     # Example scripts
│   ├── quantum_attack.py        # Run quantum attack
│   ├── classical_attack.py      # Run classical attack
│   └── compare_classical_vs_quantum.py  # Compare both
│
├── tests/                        # Test suite (349 tests)
│   ├── test_bloom_filter.py
│   ├── test_grover_search.py
│   ├── test_bucket_organizer.py
│   └── ...
│
├── docs/                         # Documentation
│   ├── OPTIMIZATION_RESULTS.md
│   ├── TEST_RESULTS_SUMMARY.md
│   └── INTERMEDIATE_PASSWORD_RESULTS.md
│
└── rainbow_tables/output/        # Generated data (not in repo)
    ├── rainbow_table.db         # 2.9 GB SQLite database
    └── metadata.json            # Generation parameters
```

## Phase 1: Rainbow Table Generation

### Current Database

- **Total chains**: 38,285,441
- **Endpoint diversity**: 98.02% (37.5M unique endpoints)
- **Buckets**: 49,851 (10-qubit configuration)
- **Database size**: 2.9 GB
- **Generation time**: ~6 hours (4 workers)

### Configuration

```json
{
  "hash_algorithm": "sha1",
  "chain_length": 1000,
  "qubit_count": 10,
  "fill_factor": 0.75,
  "bucket_size": 1024,
  "num_buckets": 49851
}
```

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

### Quantum Attack (Grover's Search)

**How it works:**
1. Bloom filter pre-screens candidate endpoints (99.9% rejection rate)
2. Load matching bucket from database
3. Pad bucket to 2^n entries for quantum circuit
4. Run Grover's search (25 iterations for 10 qubits)
5. Verify result classically

**Performance:**
- Average: 4.1s per hash
- Throughput: 0.24 hashes/second
- Memory: 65.6 MB (Bloom filter)

### Classical Attack (Hash Table Lookup)

**How it works:**
1. Load all 37.5M endpoints into hash table (one-time, 57s)
2. For each position k, compute candidate endpoint
3. O(1) hash table lookup
4. Walk chain forward to verify

**Performance:**
- Average: 0.8s per hash
- Throughput: 1.21 hashes/second
- Memory: 3.6 GB (hash table)

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

**QIris (Lee et al., 2024):**
- Limited to 4,096 buckets, ~65K entries
- Custom 16-bit hash function
- Proof-of-concept only

**This Project:**
- Scales to 38M+ entries
- SHA-1-based bucketing (4 billion possible buckets)
- Production-ready implementation
- Comprehensive test coverage (349 tests)
- Both quantum and classical implementations

### Key Innovations

- **Hybrid approach**: Combines classical pre-screening with quantum search
- **Endpoint pre-filtering**: 99.94% reduction in chain walks
- **Fill factor over-provisioning**: Eliminates bucket overflow
- **Practical implementation**: Works on Qiskit simulator, ready for real quantum hardware

### Complexity Analysis

- **Classical search**: O(M) per bucket (linear scan)
- **Quantum search**: O(√M) per bucket (Grover's algorithm)
- **Bucket lookup**: O(1) (hash table or indexed SQL)
- **Overall**: O(N × √M) quantum vs O(N × M) classical, where N = chain length, M = bucket size

## Performance Logs

See `quantum_attack.log` and `classical_attack.log` for detailed performance data from the latest runs.

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

- **QIris Paper**: Lee et al., "QIris: Quantum Implementation of Rainbow Table Attacks" (2024)
- **Original Rainbow Tables**: Oechslin, "Making a faster cryptanalytic time-memory trade-off" (2003)
- **Grover's Algorithm**: Grover, "A fast quantum mechanical algorithm for database search" (1996)

## License

This project is for educational and research purposes only.

---

**Status**: Both phases complete. 38.3M chains, 98% endpoint diversity, 0% bucket overflow. Quantum and classical attacks both achieve 100% success rate on test dataset.
