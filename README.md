# Quantum-Enhanced Rainbow Table Attack System

**Last Updated:** April 7, 2026

## Project Overview

This project implements a hybrid classical-quantum password cracking system that combines rainbow table cryptanalysis with Grover's quantum search algorithm. The system generates pre-computed hash-reduction chains organized into buckets optimized for quantum search, enabling quantum speedup during the attack phase.

## System Architecture

### Two-Phase Design

```
Phase 1: Rainbow Table Generation (Classical)
    ↓
    38M+ passwords → Hash-Reduction Chains → Bucketed Storage (SQLite)
    ↓
Phase 2: Attack Phase (Hybrid Classical-Quantum) [NOT YET IMPLEMENTED]
    ↓
    Target Hash → Bucket Lookup → Classical Search → Grover Search → Password Recovery
```

## Phase 1: Rainbow Table Generation ✓ COMPLETED

### Current Implementation Status

**Generation Complete:**
- 38,285,439 chains generated from PCFG wordset
- 2.9 GB SQLite database with indexed storage
- Generation time: ~12.5 hours (single-threaded)
- Configuration: SHA-1, 1000-iteration chains, 4-qubit buckets

**Current Configuration:**
```json
{
  "hash_algorithm": "sha1",
  "chain_length": 1000,
  "qubit_count": 4,
  "bucket_size": 16,
  "num_buckets": 2392841,
  "total_chains": 38285439
}
```

### How It Works

1. **Input:** PCFG-generated 8-character passwords (38M+ entries)
   - Source: `PCFG/wordset_output/wordset_len8.txt`
   - Generated from RockYou dataset using Probabilistic Context-Free Grammar

2. **Chain Generation:**
   ```
   Start Password → Hash → Reduce(i=0) → Hash → Reduce(i=1) → ... → Final Hash (Endpoint)
   Store: (start_point, end_point, bucket_key, intra_value)
   ```

3. **Bucketing Strategy:**
   ```python
   # Use first 32 bits of SHA-1 endpoint hash
   hash_value = int(endpoint[:8], 16)
   
   # Dynamic bucket allocation
   num_buckets = ceil(total_entries / bucket_size)
   bucket_size = 2^qubit_count
   
   # Bucket assignment
   bucket_key = hash_value % num_buckets
   intra_value = hash_value % bucket_size
   ```

4. **Storage:** SQLite database with schema:
   ```sql
   CREATE TABLE chains (
       bucket_key INTEGER NOT NULL,
       intra_value INTEGER NOT NULL,
       start_point TEXT NOT NULL,
       end_point TEXT NOT NULL
   );
   CREATE INDEX idx_bucket_key ON chains(bucket_key);
   ```

### Key Components

- **`rainbow_table_generator/chain_generator.py`**: Hash-reduction chain generation
- **`rainbow_table_generator/bucket_organizer.py`**: SHA-1-based bucketing logic
- **`rainbow_table_generator/storage.py`**: SQLite database management
- **`rainbow_table_generator/hash_functions.py`**: SHA-1/MD5/SHA-256 support
- **`rainbow_table_generator/reduction.py`**: Deterministic hash-to-password mapping
- **`rainbow_table_generator/main.py`**: Orchestration and progress tracking

## Recent Major Changes

### Bucketing Strategy Migration (Completed)

**Problem Identified:**
- Old QIris-style 16-bit hash bucketing limited to 4,096 buckets maximum
- With 38M entries and 4-qubit requirement (bucket_size=16), needed 2.4M buckets
- System was fundamentally broken for large-scale quantum search

**Solution Implemented:**
- Switched from 16-bit custom hash to SHA-1-direct bucketing
- Uses first 32 bits of endpoint hash (4 billion possible values)
- Dynamic bucket calculation: `num_buckets = ceil(total_entries / bucket_size)`
- Modulo-based distribution ensures uniform bucket filling

**Changes Made:**
- ✓ Removed `hash16bit()` function from `bucket_organizer.py`
- ✓ Added `total_entries` parameter to `BucketOrganizer.__init__()`
- ✓ Updated bucket assignment to use `int(endpoint[:8], 16) % num_buckets`
- ✓ Deferred `BucketOrganizer` initialization in `main.py` until entry count known
- ✓ Updated metadata to include `num_buckets` and `bucket_size`
- ✓ All 259 tests passing
- ✓ Documentation updated

**Migration from MD5 to SHA-1:**
- All documentation updated to use SHA-1 as primary hash algorithm
- System still supports MD5, SHA-1, and SHA-256
- SHA-1 chosen for balance of security and performance

## Current Issues & Work In Progress

### Issue 1: Bucketing Distribution Problem 🔴 CRITICAL

**Observed Behavior:**
- Expected: 2,392,841 buckets with ~16 entries each
- Actual: Only 84,370 unique buckets populated
- This means buckets are averaging ~454 entries each (way over the 16-entry limit)

**Impact:**
- Buckets too large for 4-qubit Grover's algorithm
- Quantum search requires buckets ≤16 entries for 4-qubit systems
- Current distribution defeats the purpose of quantum optimization

**Root Cause (Hypothesis):**
- Bucketing formula may not be distributing uniformly
- Possible collision in first 8 hex chars of SHA-1 endpoints
- Need to investigate actual endpoint distribution in database

**Action Required:**
1. Analyze endpoint distribution in current database
2. Verify bucketing formula is correctly implemented
3. Consider alternative bucketing strategies if needed
4. Regenerate rainbow table with fixed bucketing

### Issue 2: Qubit Count Optimization 🟡 ENHANCEMENT

**Current State:**
- System configured for 4 qubits (bucket_size = 16)
- Qiskit benchmark shows 12 qubits is optimal for this hardware

**Proposed Change:**
- Switch from 4 qubits to 12 qubits
- New bucket_size = 2^12 = 4,096 entries per bucket
- New num_buckets = ceil(38,285,439 / 4,096) = 9,347 buckets

**Benefits:**
- Fewer buckets to manage (9,347 vs 2.4M)
- Better demonstrates Grover's algorithm (50 iterations vs 3)
- Still fast: 0.14s per search vs 0.04s
- More practical for real-world quantum hardware

**Tradeoffs:**
- Larger buckets mean more memory per quantum circuit (12.6 MB vs 0.8 MB)
- Longer quantum simulation time per bucket
- But: Dramatically fewer buckets to search overall

**Qiskit Benchmark Results:**
| Qubits | Bucket Size | Grover Iters | Time/Search | Memory | Buckets (38M) |
|--------|-------------|--------------|-------------|--------|---------------|
| 4      | 16          | 3            | 0.04s       | 0.8 MB | 2,392,841     |
| 12     | 4,096       | 50           | 0.14s       | 12.6 MB| 9,347         |
| 16     | 65,536      | 201          | 5.07s       | 270 MB | 584           |

**Recommendation:** Switch to 12 qubits for optimal balance

## Immediate Next Steps

### Priority 1: Fix Bucketing Distribution
1. **Investigate current database:**
   ```bash
   # Analyze bucket distribution
   python3 -c "import sqlite3; conn = sqlite3.connect('rainbow_tables/output/rainbow_table.db'); 
   cursor = conn.cursor(); 
   cursor.execute('SELECT bucket_key, COUNT(*) as cnt FROM chains GROUP BY bucket_key ORDER BY cnt DESC LIMIT 20'); 
   print(cursor.fetchall())"
   ```

2. **Verify bucketing formula implementation:**
   - Check `bucket_organizer.py` logic
   - Test with sample endpoints
   - Ensure modulo operation is correct

3. **Fix and regenerate:**
   - Implement corrected bucketing strategy
   - Delete old rainbow table: `rm -rf rainbow_tables/output/`
   - Regenerate with fixed code

### Priority 2: Migrate to 12-Qubit Configuration
1. **Update configuration:**
   ```json
   {
     "qubit_count": 12,
     "bucket_size": 4096
   }
   ```

2. **Regenerate rainbow table:**
   - Expected: 9,347 buckets with ≤4,096 entries each
   - Generation time: ~12-15 hours

3. **Validate new table:**
   - Verify bucket count matches expectation
   - Verify no bucket exceeds 4,096 entries
   - Check bucket distribution uniformity

## Phase 2: Attack Phase (Future Work)

### Planned Implementation

**Attack Flow:**
1. Input: Target SHA-1 hash
2. Calculate bucket_key using same formula as generation
3. Retrieve bucket from database (≤4,096 chains for 12-qubit)
4. Classical chain walking (try all chains sequentially)
5. If classical fails, apply Grover's quantum search
6. Return recovered password or "not found"

**Components to Build:**
- Hash lookup module (bucket calculation + database query)
- Chain walker (backward chain traversal)
- Password reconstructor (forward chain reconstruction)
- Grover search module (Qiskit quantum circuit)
- Attack orchestrator (main entry point)

**Requirements:** See `.kiro/specs/quantum-grover-attack-phase/requirements.md`

## Project Structure

```
.
├── rainbow_table_generator/       # Phase 1: Generation (COMPLETE)
│   ├── bucket_organizer.py        # Bucketing logic
│   ├── chain_generator.py         # Hash-reduction chains
│   ├── config.py                  # Configuration management
│   ├── hash_functions.py          # SHA-1/MD5/SHA-256
│   ├── reduction.py               # Hash-to-password mapping
│   ├── storage.py                 # SQLite database I/O
│   ├── progress.py                # Progress tracking
│   ├── parallel.py                # Multi-process generation
│   ├── main.py                    # Main orchestrator
│   └── utils.py                   # Utilities
│
├── tests/                         # Test suite (259 tests, all passing)
│   ├── test_bucket_organizer.py
│   ├── test_chain_generator.py
│   ├── test_storage.py
│   └── ...
│
├── PCFG/                          # Password generation
│   ├── wordset_output/
│   │   └── wordset_len8.txt       # 38M passwords
│   └── ...
│
├── rainbow_tables/output/         # Generated rainbow table
│   ├── rainbow_table.db           # 2.9 GB SQLite database
│   ├── metadata.json              # Generation parameters
│   ├── index.json                 # Bucket statistics
│   └── logs/
│
├── .kiro/specs/                   # Specifications
│   ├── quantum-grover-rainbow-table/
│   └── quantum-grover-attack-phase/
│
├── config.json                    # Runtime configuration
├── requirements.txt               # Python dependencies
│
└── Documentation:
    ├── BUCKETING_CHANGES_SUMMARY.md
    ├── BUCKETING_STRATEGY_COMPARISON.md
    ├── CONVERSATION_SUMMARY.md
    ├── MD5_TO_SHA1_MIGRATION.md
    └── qiskit_simulation_benchmark.md
```

## Running the System

### Generate Rainbow Table
```bash
# Current configuration (4 qubits)
python -m rainbow_table_generator.main --config config.json

# After fixing bucketing and switching to 12 qubits
# 1. Update config.json: "qubit_count": 12
# 2. Delete old table: rm -rf rainbow_tables/output/
# 3. Regenerate: python -m rainbow_table_generator.main --config config.json
```

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific component
pytest tests/test_bucket_organizer.py -v

# With coverage
pytest tests/ --cov=rainbow_table_generator --cov-report=html
```

### Validate Generated Table
```bash
# Check database statistics
python3 -c "
import sqlite3
conn = sqlite3.connect('rainbow_tables/output/rainbow_table.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM chains')
print(f'Total entries: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(DISTINCT bucket_key) FROM chains')
print(f'Unique buckets: {cursor.fetchone()[0]}')
cursor.execute('SELECT MAX(cnt) FROM (SELECT COUNT(*) as cnt FROM chains GROUP BY bucket_key)')
print(f'Max bucket size: {cursor.fetchone()[0]}')
conn.close()
"
```

## Technical Details

### Hash-Reduction Chain Algorithm
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
    charset = "abcdefghijklmnopqrstuvwxyz0123456789"
    seed = hash_value.hex() + str(iteration)
    hash_int = int(seed, 16)
    
    password = []
    for i in range(password_length):
        char_index = (hash_int >> (i * 8)) % len(charset)
        password.append(charset[char_index])
    
    return ''.join(password)
```

### Bucketing Formula (Current Implementation)
```python
def assign_bucket(endpoint: str, num_buckets: int) -> int:
    hash_value = int(endpoint[:8], 16)  # First 32 bits
    return hash_value % num_buckets

def intra_bucket_value(endpoint: str, bucket_size: int) -> int:
    hash_value = int(endpoint[:8], 16)
    return hash_value % bucket_size
```

## Dependencies

```
pyyaml>=6.0          # Configuration parsing
pytest>=7.0          # Testing
pytest-cov>=4.0      # Coverage
qiskit>=1.0          # Quantum simulation (for attack phase)
```

## Performance Metrics

### Generation Phase (Current)
- Input: 38,285,439 passwords
- Chain length: 1000 iterations
- Generation time: 44,918 seconds (~12.5 hours)
- Processing rate: ~852 chains/second
- Database size: 2.9 GB
- Index size: 5.4 MB

### Expected Attack Phase Performance (12-qubit)
- Bucket lookup: <100ms (indexed SQLite query)
- Classical chain walking: ~1000 iterations/second per chain
- Quantum search: 0.14s per bucket (Qiskit statevector)
- Total attack time: <1 minute per target hash (estimated)

## Research Context

This implementation improves upon existing research:

**QIris (Lee et al., 2024):**
- Limited to 4,096 buckets, ~65K entries max
- Custom 16-bit hash function
- Proof-of-concept only

**Khajeian (2025):**
- Theoretical k-bit hash approach
- No production implementation

**This Project:**
- Scales to millions of entries
- Dynamic bucket allocation
- Production-ready SQLite storage
- Supports 4-16 qubit configurations
- Comprehensive test coverage

## Known Issues & Limitations

1. **Bucketing distribution broken** - Only 84K buckets used instead of 2.4M
2. **Single-threaded generation** - Parallel mode exists but not optimized
3. **No attack phase yet** - Phase 2 not implemented
4. **4-qubit configuration suboptimal** - Should migrate to 12 qubits
5. **No checkpoint resume** - Checkpoints saved but resume not implemented
6. **Memory usage during generation** - Buckets held in memory before flush

## Contributing & Development

### Before Making Changes
1. Read relevant specification in `.kiro/specs/`
2. Run existing tests: `pytest tests/ -v`
3. Check documentation for context

### After Making Changes
1. Update tests to match new behavior
2. Run full test suite
3. Update this README.md with changes
4. Update relevant documentation files
5. Regenerate rainbow table if bucketing/hashing changed

### Testing Philosophy
- All 259 tests must pass before committing
- Test coverage should remain >80%
- Integration tests validate end-to-end workflows

## References

- **QIris Paper:** Lee et al., "QIris: Quantum Implementation of Rainbow Table Attacks" (2024)
- **Hybrid Approach:** Khajeian, "Hybrid Classical-Quantum Rainbow Table Attack" (2025)
- **Original Rainbow Tables:** Oechslin, "Making a faster cryptanalytic time-memory trade-off" (2003)
- **Grover's Algorithm:** Grover, "A fast quantum mechanical algorithm for database search" (1996)

---

**Status:** Phase 1 complete with critical bucketing bug. Fixing distribution and migrating to 12 qubits before implementing Phase 2.
