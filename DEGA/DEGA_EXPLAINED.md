# What is DEGA (Distributed Exact Grover's Algorithm)?

## The Core Problem with Standard Grover's

Standard Grover's algorithm has two issues:
1. **Probabilistic** - Success probability ≈ 99.99% but not 100%
2. **Deep circuits** - For n qubits, needs ~√(2^n) iterations, each adding gates

## DEGA's Solution: Divide and Conquer

Instead of searching all n qubits at once, DEGA **breaks the search into smaller 2-qubit or 3-qubit sub-searches**.

---

## How DEGA Works (8-qubit Example)

### Step 1: Partition the Search Space

For 8 qubits searching for target `τ = 10110011`:

**Standard Grover:** Search all 8 bits at once (256 possibilities)

**DEGA:** Break into 4 sub-searches of 2 bits each:
- **g₀**: Search bits 0-1 → find `10`
- **g₁**: Search bits 2-3 → find `11`
- **g₂**: Search bits 4-5 → find `00`
- **g₃**: Search bits 6-7 → find `11`

### Step 2: Create Sub-Functions

Each sub-function g_i checks if a 2-bit pattern matches the target:

```
g₀(x₀x₁) = 1 if (x₀x₁ matches first 2 bits of τ) else 0
g₁(x₂x₃) = 1 if (x₂x₃ matches next 2 bits of τ) else 0
g₂(x₄x₅) = 1 if (x₄x₅ matches next 2 bits of τ) else 0
g₃(x₆x₇) = 1 if (x₆x₇ matches last 2 bits of τ) else 0
```

**Key insight:** Each sub-function only searches 4 possibilities (2² = 4), not 256!

### Step 3: Apply Grover to Each Sub-Function

For each 2-qubit sub-function:
- **Iterations needed:** 1 (because √4 ≈ 1.57 → ⌊π/4 × √4⌋ = 1)
- **Success probability:** 100% (with phase matching)

### Step 4: Combine Results

After 4 sub-searches, you've found all 8 bits:
- g₀ found `10`
- g₁ found `11`
- g₂ found `00`
- g₃ found `11`
- **Combined:** `10110011` ✓

---

## Why DEGA is Faster

### Circuit Depth Comparison (8 qubits)

| Algorithm | Iterations | Depth per Iteration | Total Depth |
|-----------|-----------|---------------------|-------------|
| **Standard Grover** | 12 | ~8 gates | ~96 |
| **DEGA** | 4 × 1 | ~8 gates | **~9** |

**Speedup:** 96 → 9 = **10.7× fewer gates**

### Why Fewer Iterations?

- Standard Grover: √256 = 16 → 12 iterations
- DEGA: 4 × √4 = 4 × 2 → 4 iterations (one per sub-function)

**Key:** √(a×b) > √a + √b when a,b > 1

Example: √256 = 16, but √4 + √4 + √4 + √4 = 8

---

## The Math Behind DEGA

### Partitioning Strategy

For n qubits, create ⌊n/2⌋ sub-functions:

**For n=8 (even):**
- 4 sub-functions, each 2 qubits
- Each searches 2² = 4 states
- Total: 4 iterations

**For n=9 (odd):**
- 4 sub-functions: three 2-qubit + one 3-qubit
- Last one searches 2³ = 8 states (needs 2 iterations)
- Total: 3×1 + 1×2 = 5 iterations

### Sub-Function Construction

For sub-function g_i at position i:

```python
# Fix all bits except positions (2i, 2i+1)
# Check all 4 combinations of those 2 bits
# Return 1 if any combination makes f(x) = 1

g_i(m_i) = OR(
    f(y_0...y_{2i-1}, m_i, y_{2i}...y_{n-1})
    for all possible y values
)
```

**Example for g₁ (bits 2-3) with target τ=10110011:**

```
g₁(00) = OR(f(10,00,0011), f(10,00,1011), f(10,00,0111), f(10,00,1111)) = 0
g₁(01) = OR(f(10,01,0011), f(10,01,1011), f(10,01,0111), f(10,01,1111)) = 0
g₁(10) = OR(f(10,10,0011), f(10,10,1011), f(10,10,0111), f(10,10,1111)) = 0
g₁(11) = OR(f(10,11,0011), f(10,11,1011), f(10,11,0111), f(10,11,1111)) = 1 ✓
```

---

## DEGA Circuit Structure

```
|0⟩ ─H─┤         ├─H─┤     ├─H─  (qubits 0-1: search for bits 0-1)
|0⟩ ─H─┤ Oracle₀ ├─H─┤ Diff├─H─
       └─────────┘   └─────┘

|0⟩ ─H─┤         ├─H─┤     ├─H─  (qubits 2-3: search for bits 2-3)
|0⟩ ─H─┤ Oracle₁ ├─H─┤ Diff├─H─
       └─────────┘   └─────┘

|0⟩ ─H─┤         ├─H─┤     ├─H─  (qubits 4-5: search for bits 4-5)
|0⟩ ─H─┤ Oracle₂ ├─H─┤ Diff├─H─
       └─────────┘   └─────┘

|0⟩ ─H─┤         ├─H─┤     ├─H─  (qubits 6-7: search for bits 6-7)
|0⟩ ─H─┤ Oracle₃ ├─H─┤ Diff├─H─
       └─────────┘   └─────┘
```

**Each pair of qubits runs 1 Grover iteration independently!**

---

## Key Advantages

1. **Deterministic:** 100% success rate (with proper phase matching)
2. **Shallow circuits:** Constant depth (9 for even n, 17 for odd n)
3. **Noise resistant:** Fewer gates = less decoherence
4. **Parallelizable:** Sub-searches are independent

---

## Implementation Challenges

### 1. Oracle Construction

For each sub-function, you need to:
- Evaluate f(x) for all 2^(n-2) fixed bit patterns
- OR the results to create g_i
- Build a phase oracle for g_i

### 2. Your Rainbow Table Context

In your case, f(x) checks if bucket entry x contains the target hash:

```python
def f(bucket_index):
    """Does bucket[index] contain target_hash at position_k?"""
    start_point = bucket[bucket_index][0]
    return walk_chain(start_point, position_k) == target_hash
```

For DEGA, you need:

```python
def g_i(two_bits):
    """Do ANY bucket indices with these 2 bits contain target?"""
    # For 8 qubits, bucket has 256 entries
    # If searching bits 2-3, check all indices where bits 2-3 = two_bits
    # That's 64 indices (256 / 4)
    for index in range(256):
        if (index >> (2*i)) & 0b11 == two_bits:
            if f(index):
                return True
    return False
```

---

## Pseudocode for Your Implementation

```python
class DEGASearch:
    def __init__(self, n_qubits, ...):
        self.n_qubits = n_qubits
        self.n_pairs = n_qubits // 2
        
    def search(self, bucket, target_hash, position_k):
        # Step 1: Find marked indices for each sub-function
        marked_bits = []
        for i in range(self.n_pairs):
            marked_2bits = self._find_marked_pair(
                bucket, target_hash, position_k, pair_index=i
            )
            marked_bits.append(marked_2bits)
        
        # Step 2: Build DEGA circuit
        qc = self._build_dega_circuit(marked_bits)
        
        # Step 3: Simulate and extract result
        result_bits = self._simulate(qc)
        
        # Step 4: Combine to get bucket index
        bucket_index = self._combine_bits(result_bits)
        return bucket_index
    
    def _find_marked_pair(self, bucket, target, pos_k, pair_index):
        """Find which 2-bit pattern is marked for this pair."""
        for two_bits in range(4):  # 00, 01, 10, 11
            if self._evaluate_subfunction(bucket, target, pos_k, 
                                         pair_index, two_bits):
                return two_bits
        return None
    
    def _evaluate_subfunction(self, bucket, target, pos_k, 
                             pair_idx, two_bits):
        """Check if any bucket index with these 2 bits contains target."""
        # Check all indices where bits (2*pair_idx, 2*pair_idx+1) = two_bits
        for idx in range(len(bucket)):
            # Extract the relevant 2 bits from idx
            relevant_bits = (idx >> (2 * pair_idx)) & 0b11
            if relevant_bits == two_bits:
                # Check if this bucket entry contains target
                if self._oracle_evaluate(bucket[idx][0], target, pos_k):
                    return True
        return False
```

---

## Expected Performance in Your Project

### Current (Standard Grover, 8 qubits):
- Circuit depth: ~96
- Simulation time: 0.911s/hash

### With DEGA (8 qubits):
- Circuit depth: ~9
- Simulation time: **~0.09-0.15s/hash** (estimated)
- **Speedup: 6-10×**

---

## Reference

Zhou, X., Qiu, D., & Luo, L. (2023). Distributed exact Grover's algorithm. 
Frontiers of Physics, 18(5), 51305.

ArXiv: https://arxiv.org/html/2507.14600v1
