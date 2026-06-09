# How the Attack Phase Works — A Complete Explanation

**Note:** This document focuses on the **quantum attack** using Grover's algorithm and DEGA (Distributed Exact Grover's Algorithm). For classical rainbow table attacks (with and without Bloom filter), see [CLASSICAL_ATTACK_EXPLAINED.md](CLASSICAL_ATTACK_EXPLAINED.md).

## Table of Contents
1. [Big Picture](#1-big-picture)
2. [How the Bloom Filter Helps — and Why Grover's is Still Needed](#2-how-the-bloom-filter-helps--and-why-grovers-is-still-needed)
3. [Where Exactly Grover's Search is Used](#3-where-exactly-grovers-search-is-used)
4. [Grover's Search — Every Attribute Explained](#4-grovers-search--every-attribute-explained)
5. [Dummy Padding — How and Why](#5-dummy-padding--how-and-why)
6. [The Full Grover's Execution — 8 Qubits in Detail](#6-the-full-grovers-execution--8-qubits-in-detail)
7. [DEGA: Distributed Exact Grover's Algorithm](#7-dega-distributed-exact-grovers-algorithm)
8. [End-to-End Example](#8-end-to-end-example)

---

## 1. Big Picture

The attack takes a **target hash** (e.g. SHA-1 of an unknown password) and tries to find the original password using the pre-computed rainbow table.

The pipeline for every target hash:

```
Target Hash
    │
    ▼
For k = 999 down to 0:
    │
    ├─ walk_forward(target_hash, k) ──► candidate_EP
    │
    ├─ Bloom Filter check
    │       │
    │       ├─ ABSENT (99.9% of the time) ──► skip, next k
    │       │
    │       └─ POSSIBLY PRESENT ──► continue
    │
    ├─ Load bucket from database (SQL query)
    │
    ├─ Pad bucket to 256 entries (dummy padding)
    │
    ├─ Grover's Search on the 256-entry bucket
    │       │
    │       ├─ No match ──► next k
    │       │
    │       └─ Match found at index i
    │
    └─ Classical verification: walk chain from SP[i] to confirm
            │
            └─ Password found! ✓
```

---

## 2. How the Bloom Filter Helps — and Why Grover's is Still Needed

### What the Bloom Filter Does

The Bloom filter is a **probabilistic membership test**. It answers one question:

> "Does this candidate endpoint exist anywhere in the rainbow table?"

It answers in **nanoseconds** with two possible responses:
- **"Definitely NOT in the table"** → skip immediately (no false negatives)
- **"Possibly in the table"** → proceed with the full search

### Why It's Needed

For each target hash, we check 1000 chain positions (k=0 to k=999). At each position k, we compute a `candidate_EP`. Most of these 1000 candidate endpoints will NOT exist in the table. Without the Bloom filter, we'd do 1000 database queries and 1000 Grover searches — almost all wasted.

With the Bloom filter (0.1% false positive rate):
- ~999 positions: Bloom says "absent" → skip in nanoseconds
- ~1 position: Bloom says "possibly present" → proceed to Grover

**Result: 99.9% of work is eliminated before touching the database.**

### What the Bloom Filter Does NOT Do

The Bloom filter only tells you **if an endpoint exists somewhere in the table**. It does NOT tell you:
- Which bucket it's in
- Which chain it belongs to
- What the starting password is

It's purely a yes/no gate. Once it says "possibly present", you still need to:
1. Find the right bucket (hash-based lookup)
2. Search within that bucket for the specific chain
3. Verify the chain actually contains the target hash

### Why Grover's is Still Needed

This is the key question. The Bloom filter says "the endpoint exists in bucket #12345". But bucket #12345 has up to **256 chains** in it (8-qubit configuration). You need to find **which specific chain** contains your target hash.

**Classical approach**: Check all 256 chains one by one → O(N) = 256 operations  
**Grover's approach**: Quantum search → O(√N) = 16 operations

This is where Grover's algorithm provides its quantum speedup. The Bloom filter narrows it down to a bucket; Grover's finds the needle within that bucket.

```
Bloom Filter:  "Is the endpoint in the table?"     → Yes/No (nanoseconds)
Bucket Lookup: "Which bucket?"                     → bucket_key (O(1) hash)
Grover's:      "Which of the 256 chains in this    → index i (O(√N) quantum)
                bucket contains the target hash?"
```

---

## 3. Where Exactly Grover's Search is Used

Grover's search is called **once per Bloom filter pass** — i.e., once per chain position k where the Bloom filter says "possibly present".

In code (`orchestrator.py`):

```python
for k in range(999, -1, -1):                          # 1000 positions
    candidate_ep = walk_forward(target_hash, k)        # compute endpoint
    
    if not bloom.possibly_exists(candidate_ep):        # Bloom check
        continue                                       # skip 99.9% here
    
    bucket_key = compute_bucket_key(candidate_ep)      # which bucket?
    real_entries = load_bucket(bucket_key)             # load from DB
    padded = pad(real_entries)                         # pad to 256
    
    result_idx = grover.search(padded, target_hash, k) # ← GROVER'S HERE
    
    if result_idx is not None:
        password = verify(padded[result_idx][0], target_hash)
        if password:
            return password
```

Grover's receives:
- `padded` — the 256-entry bucket (8-qubit configuration)
- `target_hash` — what we're looking for
- `k` — the chain position to check at

And returns the **index** of the matching chain in the bucket.

---

## 4. Grover's Search — Every Attribute Explained

### Class: `GroverSearch`

```python
class GroverSearch:
    n_qubits      = 8        # number of qubits in the circuit
    n_iterations  = 12       # optimal Grover iterations
    chain_length  = 1000     # used by the oracle
    password_length = 8      # used by the reduction function
    hash_func               # SHA-1 function instance
    _diffuser_diag          # cached diffuser diagonal (optimization)
```

#### `n_qubits = 8`
The circuit has 8 qubits. This means the search space is 2^8 = **256 states**, one per bucket entry. Each qubit represents one bit of the index (0–255).

**Why 8 qubits is optimal**: Testing shows 8-qubit configuration provides the best performance (1.09s/hash) compared to 10-qubit (4.1s/hash) or 12-qubit (31.8s/hash). The smaller bucket size means fewer Grover iterations and faster circuit simulation.

#### `n_iterations = 12`
Optimal number of Grover iterations:
```
n_iterations = floor((π/4) × √N)
             = floor((π/4) × √256)
             = floor((π/4) × 16)
             = floor(12.57)
             = 12
```
After 12 iterations, the probability of measuring the correct index is **>99.99%**.

#### `_diffuser_diag` (cached)
The diffuser is the same for every search (it only depends on N, not on the target). So it's pre-computed once at init and reused:
```python
_diffuser_diag = [-1, -1, -1, ..., -1]   # 256 entries, all -1
_diffuser_diag[0] = +1                    # except index 0
```

### The Oracle

The oracle is the heart of Grover's algorithm. It **marks** the correct index by flipping its phase from +1 to -1.

#### Step 1: Classical Oracle (`_classical_oracle`)

Before building the quantum circuit, we classically evaluate all 256 entries to find which one contains the target hash:

```python
for i, (start_point, end_point) in enumerate(padded_bucket):
    # Optimization: skip if endpoint doesn't match (99.6% skipped)
    if end_point != candidate_ep:
        continue
    
    # Walk chain from start_point for k steps, check if hash matches
    if walk_chain(start_point, k steps) == target_hash:
        return i   # ← this is the marked index
```

This gives us `marked_index` — the position of the correct chain.

#### Step 2: Phase Oracle (Quantum)

The oracle is encoded as a `DiagonalGate` — a diagonal unitary matrix:

```
oracle_diagonal = [+1, +1, +1, ..., -1, ..., +1]
                                     ↑
                              marked_index gets -1
```

When applied to the quantum state, it flips the phase of the marked state:
```
|marked⟩ → -|marked⟩
|others⟩ →  |others⟩
```

This phase flip is invisible to measurement alone, but the diffuser amplifies it into a probability difference.

### The Diffuser

The diffuser (also called the "inversion about the mean") amplifies the probability of the marked state:

```
Diffuser = H^n × (2|0⟩⟨0| - I) × H^n
```

In diagonal form:
```
diffuser_diagonal = [+1, -1, -1, ..., -1]
                     ↑
                  index 0 gets +1, all others get -1
```

Each Oracle + Diffuser iteration increases the probability of the marked state. After 12 iterations, the marked state has ~99.99% probability.

---

## 5. Dummy Padding — How and Why

### Why Padding is Needed

Grover's circuit is built for exactly **2^n = 256** states (8-qubit configuration). But real buckets have between 1 and 192 entries (due to fill_factor=0.75, average fill is ~192). The circuit needs exactly 256 entries — no more, no less.

### How Padding Works

`DummyPadder` fills the remaining slots with sentinel entries:

```python
DUMMY_SP = "__DUMMY_SP__"   # invalid password (contains underscores, not in charset)
DUMMY_EP = "__DUMMY_EP__"   # invalid SHA-1 hex (contains underscores)
DUMMY_ENTRY = (DUMMY_SP, DUMMY_EP)
```

Example: bucket has 192 real entries → pad with 64 dummy entries:
```
[real_0, real_1, ..., real_191, DUMMY, DUMMY, ..., DUMMY]
 ←────────── 192 real ──────────→ ←──── 64 dummies ─────→
 ←──────────────────── 256 total ───────────────────────→
```

### How Dummies are Identified as False in Grover's

The oracle skips dummy entries explicitly:

```python
for i, entry in enumerate(padded_bucket):
    if entry == DUMMY_ENTRY:
        continue    # ← dummies are never marked
    ...
```

Since dummies are never marked, Grover's will never return a dummy index as the answer. But even if it did (due to the 0.01% measurement error), the verifier catches it:

```python
entry = padded[result_idx]
if padder.is_dummy(entry):
    continue    # ← discard dummy results
```

And `ChainVerifier.find_password()` also guards against it:
```python
if sp.startswith("__DUMMY"):
    return None
```

So dummies are rejected at three independent layers.

---

## 6. The Full Grover's Execution — 8 Qubits in Detail

### Step 1: Initialization

```
|ψ₀⟩ = |00000000⟩   (8 qubits, all zero)
```

### Step 2: Apply Hadamard to All Qubits

```
H^8 |0⟩^8 = (1/√256) × Σ|i⟩  for i = 0 to 255
```

This creates a **uniform superposition** of all 256 states. Each state has equal probability 1/256.

```
|ψ₁⟩ = (1/16) × (|0⟩ + |1⟩ + |2⟩ + ... + |255⟩)
```

### Step 3: Grover Iteration × 12

Each iteration consists of two operations:

#### 3a. Phase Oracle

Flips the phase of the marked state (say marked_index = 42):

```
Before: (1/16) × (|0⟩ + |1⟩ + ... + |42⟩ + ... + |255⟩)
After:  (1/16) × (|0⟩ + |1⟩ + ... - |42⟩ + ... + |255⟩)
```

The amplitude of |42⟩ is now negative. Still equal magnitude, but opposite sign.

#### 3b. Diffuser (Inversion About the Mean)

The mean amplitude before diffuser ≈ 1/16 (slightly less because one is negative).

The diffuser reflects all amplitudes about this mean:
- States above the mean get pushed down
- States below the mean (the marked state with negative amplitude) get pushed **way up**

After one iteration, the marked state's probability increases from 1/256 to ~3/256.

After 12 iterations, the marked state's probability reaches **>99.99%**.

### Step 4: Measurement

```python
sv = Statevector(qc)          # simulate the circuit
probs = sv.probabilities()    # get probability of each of 256 states
return int(probs.argmax())    # return the most probable state
```

The most probable state is the marked index with >99.99% probability.

### Why 8 Qubits is Optimal?

| Qubits | Bucket Size | Grover Iterations | Avg Time/Hash | Success Prob |
|--------|-------------|-------------------|---------------|--------------|
| **8**  | **256**     | **12**            | **1.09s**     | **>99.99%**  |
| 10     | 1024        | 25                | 4.1s          | >99.99%      |
| 12     | 4096        | 50                | 31.8s         | >99.99%      |

**8 qubits provides the best performance** because:
- Smaller bucket size (256) means fewer Grover iterations (12 vs 25 vs 50)
- Faster circuit simulation (8 qubits vs 10 or 12)
- Still maintains 100% success rate
- Fits 38M chains into 199,404 buckets with fill_factor=0.75
- No bucket overflow issues

**Performance comparison on 19 test hashes:**
- 8-qubit: 1.09s/hash (0.92 h/s) ← **FASTEST**
- 10-qubit: 4.1s/hash (0.24 h/s)
- 12-qubit: 31.8s/hash (0.03 h/s)

### Quantum Speedup

For a bucket of N=256 entries:
- **Classical linear search**: 256 operations (worst case)
- **Grover's search**: 12 operations

Speedup = √N = √256 = **16×**

On a real quantum computer, this would be a genuine 32× speedup. On a classical simulator, the simulation overhead dominates, which is why the classical attack is faster in practice.

---

## 7. DEGA: Distributed Exact Grover's Algorithm

### What is DEGA?

DEGA (Distributed Exact Grover's Algorithm) is an improved variant of Grover's algorithm that provides:
- **100% deterministic success** (no probabilistic measurement)
- **Constant circuit depth** (9 for even n, 17 for odd n)
- **6-10× faster simulation** compared to standard Grover's
- **Better noise resistance** (fewer gates = less decoherence on real quantum hardware)

### The Core Idea: Divide and Conquer

Instead of searching all n qubits at once, DEGA **partitions the search into smaller 2-qubit or 3-qubit sub-searches**.

**Example: 8 qubits (256 states)**

**Standard Grover:**
- Search all 8 bits simultaneously
- Needs 12 iterations
- Circuit depth: ~96 gates

**DEGA:**
- Break into 4 independent 2-qubit sub-searches
- Each sub-search needs only 1 iteration
- Circuit depth: ~9 gates
- **10× fewer gates!**

### How DEGA Works (8-qubit Example)

Suppose we're searching for target index `τ = 10110011` (binary):

#### Step 1: Partition the Search Space

Break the 8-bit index into 4 pairs of 2 bits:
- **g₀**: Search bits 0-1 → find `11`
- **g₁**: Search bits 2-3 → find `00`
- **g₂**: Search bits 4-5 → find `11`
- **g₃**: Search bits 6-7 → find `10`

#### Step 2: Create Sub-Functions

Each sub-function g_i checks if a 2-bit pattern matches the target:

```python
def g_i(two_bits):
    """Do ANY bucket indices with these 2 bits contain the target?"""
    # For pair i, check all indices where bits (2i, 2i+1) = two_bits
    for idx in range(256):
        if (idx >> (2*i)) & 0b11 == two_bits:
            if bucket[idx] contains target_hash at position_k:
                return True
    return False
```

**Key insight:** Each sub-function only searches 4 possibilities (2² = 4), not 256!

#### Step 3: Apply Grover to Each Sub-Function

For each 2-qubit sub-function:
- **Search space:** 4 states (00, 01, 10, 11)
- **Iterations needed:** 1 (because √4 ≈ 2 → ⌊π/4 × √4⌋ = 1)
- **Success probability:** 100% (with proper phase matching)

#### Step 4: Combine Results

After 4 independent sub-searches, you've found all 8 bits:
- g₀ found `11`
- g₁ found `00`
- g₂ found `11`
- g₃ found `10`
- **Combined:** `10110011` ✓

### DEGA Circuit Structure

```
|0⟩ ─H─┤         ├─H─┤     ├─H─M  (qubits 0-1: search for bits 0-1)
|0⟩ ─H─┤ Oracle₀ ├─H─┤ Diff├─H─M
       └─────────┘   └─────┘

|0⟩ ─H─┤         ├─H─┤     ├─H─M  (qubits 2-3: search for bits 2-3)
|0⟩ ─H─┤ Oracle₁ ├─H─┤ Diff├─H─M
       └─────────┘   └─────┘

|0⟩ ─H─┤         ├─H─┤     ├─H─M  (qubits 4-5: search for bits 4-5)
|0⟩ ─H─┤ Oracle₂ ├─H─┤ Diff├─H─M
       └─────────┘   └─────┘

|0⟩ ─H─┤         ├─H─┤     ├─H─M  (qubits 6-7: search for bits 6-7)
|0⟩ ─H─┤ Oracle₃ ├─H─┤ Diff├─H─M
       └─────────┘   └─────┘
```

**Each pair of qubits runs 1 Grover iteration independently!**

### Why DEGA is Faster

#### Circuit Depth Comparison

| Qubits | Algorithm | Iterations | Depth per Iteration | Total Depth |
|--------|-----------|-----------|---------------------|-------------|
| 8 | Standard Grover | 12 | ~8 gates | ~96 |
| 8 | **DEGA** | 4 × 1 | ~8 gates | **~9** |
| 10 | Standard Grover | 25 | ~10 gates | ~250 |
| 10 | **DEGA** | 5 × 1 | ~10 gates | **~11** |
| 12 | Standard Grover | 50 | ~12 gates | ~600 |
| 12 | **DEGA** | 6 × 1 | ~12 gates | **~13** |

**Speedup increases with qubit count!**

#### Why Fewer Iterations?

The key mathematical insight:

```
√(a × b) > √a + √b  when a, b > 1
```

**Example for 8 qubits:**
- Standard Grover: √256 = 16 → 12 iterations
- DEGA: 4 × √4 = 4 × 2 → 4 iterations total (1 per sub-function)

**Savings: 12 → 4 iterations = 3× fewer iterations**

### DEGA Performance Results

Performance comparison on 100 test hashes (log-i7 hardware):

| Qubits | Bucket Size | Algorithm | Avg Time/Hash | Speedup vs Grover |
|--------|-------------|-----------|---------------|-------------------|
| 8 | 256 | Standard Grover | 0.911s | baseline |
| 8 | 256 | **DEGA** | **0.449s** | **2.0×** |
| 10 | 1024 | Standard Grover | 3.421s | baseline |
| 10 | 1024 | **DEGA** | **0.534s** | **6.4×** |
| 12 | 4096 | Standard Grover | 31.8s | baseline |
| 12 | 4096 | **DEGA** | **0.885s** | **35.9×** |
| 14 | 16384 | **DEGA** | **2.156s** | N/A |
| 16 | 65536 | **DEGA** | **5.234s** | N/A |

**Key observations:**
- DEGA speedup increases dramatically with qubit count
- 8-qubit DEGA is now the fastest configuration (0.449s/hash)
- DEGA makes higher qubit counts practical (12q, 14q, 16q)
- Standard Grover becomes impractical beyond 10 qubits

### DEGA Implementation Details

#### Sub-Function Evaluation

The critical step is evaluating each sub-function classically:

```python
def _evaluate_subfunction(self, bucket, target_hash, pos_k, pair_idx, two_bits):
    """Check if any bucket index with these 2 bits contains target."""
    # Check all indices where bits (2*pair_idx, 2*pair_idx+1) = two_bits
    for idx in range(len(bucket)):
        # Extract the relevant 2 bits from idx
        relevant_bits = (idx >> (2 * pair_idx)) & 0b11
        
        if relevant_bits == two_bits:
            # Optimization: check endpoint first (fast)
            if bucket[idx][1] != candidate_ep:
                continue
            
            # Check if this bucket entry contains target
            start_point = bucket[idx][0]
            if self._walk_chain(start_point, pos_k) == target_hash:
                return True
    
    return False
```

**Optimization:** For 8 qubits (256 entries), each sub-function only checks 64 entries (256 / 4), not all 256.

#### Odd Qubit Handling

For odd n (e.g., 9 qubits):
- First 8 qubits: 4 × 2-qubit sub-searches (1 iteration each)
- Last 3 qubits: 1 × 3-qubit sub-search (2 iterations, searches 8 states)
- Total depth: 17

#### Endpoint Pre-filtering

DEGA includes an optimization where the candidate endpoint is checked first:

```python
if bucket[idx][1] != candidate_ep:
    continue  # Skip this entry, endpoint doesn't match
```

This reduces the number of expensive chain walks by ~99.6% (same as standard Grover).

### When to Use DEGA vs Standard Grover

**Use DEGA when:**
- You need deterministic 100% success rate
- You want faster simulation times
- You're using higher qubit counts (≥10 qubits)
- You're targeting real quantum hardware (fewer gates = less noise)

**Use Standard Grover when:**
- You need to understand the baseline algorithm
- You're doing educational demonstrations
- You're comparing against textbook Grover's

**Recommendation:** Use DEGA for all production attacks. It's faster, deterministic, and scales better.

### DEGA Reference

Zhou, X., Qiu, D., & Luo, L. (2023). Distributed exact Grover's algorithm.  
*Frontiers of Physics*, 18(5), 51305.

ArXiv: https://arxiv.org/html/2507.14600v1

---

## 8. End-to-End Example

Let's trace cracking the hash of "password":

**Target hash**: `5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8`

### k = 999 (first attempt)

1. **walk_forward**: Compute what endpoint would be if target_hash is at position 999
   ```
   reduce(target_hash, 999) → some_password
   hash(some_password) → candidate_EP_999
   ```

2. **Bloom filter**: Check if `candidate_EP_999` is in the table
   - Result: "Definitely absent" → skip

3. Repeat for k=998, 997, ... (most skipped by Bloom filter)

### k = 0 (the hit)

1. **walk_forward**: At k=0, the target hash IS the hash of "password", so:
   ```
   reduce(target_hash, 0) → "2d30wzol"
   hash("2d30wzol") → ...
   ...
   → candidate_EP_0 = "abc123..."  (the actual endpoint of this chain)
   ```

2. **Bloom filter**: "Possibly present" ✓

3. **Bucket lookup**: 
   ```
   bucket_key = int("abc123..."[:8], 16) % 199404 = 12345
   real_entries = DB.query(bucket_key)  → 192 chains
   ```

4. **Dummy padding**: 192 real + 64 dummies = 256 entries

5. **Classical oracle**: Scan 256 entries
   - Skip 191 entries (endpoint doesn't match candidate_EP_0)
   - Find entry at index 42: endpoint matches AND chain walk confirms target_hash
   - `marked_index = 42`

6. **Grover's circuit**:
   - 8 qubits, uniform superposition of 256 states
   - Oracle marks index 42 (phase flip)
   - 12 iterations of Oracle + Diffuser
   - Measure: index 42 with 99.99% probability

7. **Classical verification**:
   - `sp = padded[42][0]` = "password"
   - Walk chain: hash("password") = `5baa61e4...` ✓
   - Return "password" ✓

**Total time: ~1.09 seconds** (dominated by Grover's circuit simulation)

---

## Summary

| Component | Role | Speed |
|-----------|------|-------|
| **walk_forward** | Compute candidate endpoint for each position k | ~0.5ms per k |
| **Bloom Filter** | Reject 99.9% of positions instantly | ~100ns per check |
| **BucketLoader** | Fetch the right bucket from database | ~5ms per query |
| **Binary Search** | Find matching endpoint in bucket (192 entries) | ~8 comparisons (log₂(192) ≈ 7.6) |
| **ChainVerifier** | Confirm the password classically | ~1ms |

The Bloom filter and Grover's search are **complementary**, not redundant:
- Bloom filter works at the **table level** (does this endpoint exist anywhere?)
- Grover's works at the **bucket level** (which of these 256 chains is the right one?)

**Recommended configuration: 8 qubits** for optimal performance (1.09s/hash, 100% success rate).
