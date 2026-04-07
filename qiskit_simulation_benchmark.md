# Qiskit Statevector Simulation Benchmark

**Machine**: 16.2 GB RAM, 18 cores  
**Simulator**: `qiskit.primitives.StatevectorSampler`  
**Shots**: 1024  
**Circuit**: Hadamard + Oracle placeholder + Diffuser placeholder (realistic Grover structure)  
**Grover iterations**: `floor(π/4 * √(2^n))`

## Results

| Qubits (N) | Bucket size (2^N) | Grover iters | Time per search | Peak memory | Buckets (38M entries) | Status |
|:---:|---:|---:|---:|---:|---:|:---:|
| 4  | 16          | 3   | 0.04s  | 0.8 MB    | 2,392,841 | OK |
| 8  | 256         | 12  | 0.03s  | 0.9 MB    | 149,552   | OK |
| 10 | 1,024       | 25  | 0.06s  | 2.6 MB    | 37,388    | OK |
| 12 | 4,096       | 50  | 0.14s  | 12.6 MB   | 9,347     | OK |
| 14 | 16,384      | 100 | 0.52s  | 58.8 MB   | 2,336     | OK |
| 16 | 65,536      | 201 | 5.07s  | 269.6 MB  | 584       | Heavy |
| 18 | 262,144     | 402 | 43.09s | 1,213 MB  | 146       | Too slow |
| 20 | 1,048,576   | ~800| >5 min | >10 GB    | 36        | Timed out |

## Recommendation

**12 qubits** is the practical sweet spot on this machine:
- Fast enough per search (0.14s)
- Memory stays manageable (12.6 MB per circuit run)
- Reasonable number of buckets (9,347)
- Demonstrates Grover's algorithm meaningfully (50 iterations)

**10 qubits** is a lighter alternative if speed is the priority.

**16 qubits** is the hard ceiling — technically works but 5s per search and 270 MB is heavy for repeated lookups.
