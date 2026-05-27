"""
Test suite for DEGA implementation.

Verifies correctness and performance of Distributed Exact Grover's Algorithm.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DEGA.dega_search import DEGASearch
from attack.grover_search import GroverSearch
from rainbow_table_generator.hash_functions import SHA1HashFunction
from rainbow_table_generator.reduction import reduce
from attack.dummy_padding import DUMMY_ENTRY


def create_test_bucket(n_qubits: int, target_idx: int, target_hash: str, position_k: int):
    """
    Create a test bucket with one entry containing the target hash.

    Args:
        n_qubits:    Number of qubits (bucket size = 2^n_qubits).
        target_idx:  Index where target should be placed.
        target_hash: Target hash hex string.
        position_k:  Chain position where target appears.

    Returns:
        Padded bucket with target at target_idx.
    """
    bucket_size = 2 ** n_qubits
    bucket = [DUMMY_ENTRY] * bucket_size
    
    # Create a chain that contains target_hash at position_k
    # Work backwards from target_hash to find start_point
    hash_func = SHA1HashFunction()
    
    # For simplicity, use a dummy start point and endpoint
    # In real scenario, this would be computed properly
    start_point = "testpass"
    end_point = hash_func.hash_hex(start_point)
    
    bucket[target_idx] = (start_point, end_point)
    
    return bucket


def test_dega_basic():
    """Test basic DEGA functionality with 4 qubits."""
    print("=" * 70)
    print("TEST 1: Basic DEGA Search (4 qubits)")
    print("=" * 70)
    
    n_qubits = 4
    bucket_size = 2 ** n_qubits  # 16
    target_idx = 10
    
    # Create test data
    hash_func = SHA1HashFunction()
    target_password = "test1234"
    target_hash = hash_func.hash_hex(target_password)
    position_k = 0
    
    # Create bucket with target at index 10
    bucket = [DUMMY_ENTRY] * bucket_size
    bucket[target_idx] = (target_password, hash_func.hash_hex(target_password))
    
    # Initialize DEGA
    dega = DEGASearch(
        n_qubits=n_qubits,
        chain_length=1000,
        password_length=8,
        hash_func=hash_func
    )
    
    print(f"[*] Bucket size: {bucket_size}")
    print(f"[*] Target index: {target_idx} (binary: {bin(target_idx)})")
    print(f"[*] Target hash: {target_hash}")
    print(f"[*] DEGA config: {dega}")
    print()
    
    # Run search
    start = time.time()
    result = dega.search(bucket, target_hash, position_k)
    elapsed = time.time() - start
    
    print(f"[+] Result: {result}")
    print(f"[+] Time: {elapsed:.4f}s")
    
    if result == target_idx:
        print("[✓] TEST PASSED: Found correct index!")
    else:
        print(f"[✗] TEST FAILED: Expected {target_idx}, got {result}")
    
    print()


def test_dega_vs_grover():
    """Compare DEGA vs standard Grover on 8 qubits."""
    print("=" * 70)
    print("TEST 2: DEGA vs Standard Grover (8 qubits)")
    print("=" * 70)
    
    n_qubits = 8
    bucket_size = 2 ** n_qubits  # 256
    target_idx = 137
    
    # Create test data
    hash_func = SHA1HashFunction()
    target_password = "pass8888"
    target_hash = hash_func.hash_hex(target_password)
    position_k = 0
    
    # Create bucket
    bucket = [DUMMY_ENTRY] * bucket_size
    bucket[target_idx] = (target_password, hash_func.hash_hex(target_password))
    
    print(f"[*] Bucket size: {bucket_size}")
    print(f"[*] Target index: {target_idx}")
    print(f"[*] Target hash: {target_hash}")
    print()
    
    # Test Standard Grover
    print("[1] Standard Grover's Algorithm")
    grover = GroverSearch(
        n_qubits=n_qubits,
        chain_length=1000,
        password_length=8,
        hash_func=hash_func
    )
    print(f"    Config: {grover}")
    
    start = time.time()
    result_grover = grover.search(bucket, target_hash, position_k)
    time_grover = time.time() - start
    
    print(f"    Result: {result_grover}")
    print(f"    Time: {time_grover:.4f}s")
    print(f"    Status: {'✓ PASS' if result_grover == target_idx else '✗ FAIL'}")
    print()
    
    # Test DEGA
    print("[2] DEGA (Distributed Exact Grover)")
    dega = DEGASearch(
        n_qubits=n_qubits,
        chain_length=1000,
        password_length=8,
        hash_func=hash_func
    )
    print(f"    Config: {dega}")
    
    start = time.time()
    result_dega = dega.search(bucket, target_hash, position_k)
    time_dega = time.time() - start
    
    print(f"    Result: {result_dega}")
    print(f"    Time: {time_dega:.4f}s")
    print(f"    Status: {'✓ PASS' if result_dega == target_idx else '✗ FAIL'}")
    print()
    
    # Compare
    print("[3] Performance Comparison")
    print(f"    Grover time:  {time_grover:.4f}s")
    print(f"    DEGA time:    {time_dega:.4f}s")
    speedup = time_grover / time_dega if time_dega > 0 else 0
    print(f"    Speedup:      {speedup:.2f}×")
    print()
    
    if speedup > 1:
        print(f"[✓] DEGA is {speedup:.2f}× faster than standard Grover!")
    else:
        print(f"[!] DEGA is slower (speedup: {speedup:.2f}×)")
    
    print()


def test_dega_odd_qubits():
    """Test DEGA with odd number of qubits (9 qubits)."""
    print("=" * 70)
    print("TEST 3: DEGA with Odd Qubits (9 qubits)")
    print("=" * 70)
    
    n_qubits = 9
    bucket_size = 2 ** n_qubits  # 512
    target_idx = 333
    
    # Create test data
    hash_func = SHA1HashFunction()
    target_password = "oddtest9"
    target_hash = hash_func.hash_hex(target_password)
    position_k = 0
    
    # Create bucket
    bucket = [DUMMY_ENTRY] * bucket_size
    bucket[target_idx] = (target_password, hash_func.hash_hex(target_password))
    
    # Initialize DEGA
    dega = DEGASearch(
        n_qubits=n_qubits,
        chain_length=1000,
        password_length=8,
        hash_func=hash_func
    )
    
    print(f"[*] Bucket size: {bucket_size}")
    print(f"[*] Target index: {target_idx}")
    print(f"[*] DEGA config: {dega}")
    print(f"[*] Has odd qubit: {dega.has_odd_qubit}")
    print(f"[*] Circuit depth: {dega.circuit_depth}")
    print()
    
    # Run search
    start = time.time()
    result = dega.search(bucket, target_hash, position_k)
    elapsed = time.time() - start
    
    print(f"[+] Result: {result}")
    print(f"[+] Time: {elapsed:.4f}s")
    
    if result == target_idx:
        print("[✓] TEST PASSED: Odd qubit handling works!")
    else:
        print(f"[✗] TEST FAILED: Expected {target_idx}, got {result}")
    
    print()


def test_dega_not_found():
    """Test DEGA when target is not in bucket."""
    print("=" * 70)
    print("TEST 4: DEGA with Target Not Found")
    print("=" * 70)
    
    n_qubits = 6
    bucket_size = 2 ** n_qubits  # 64
    
    # Create test data
    hash_func = SHA1HashFunction()
    target_hash = hash_func.hash_hex("notinbucket")
    position_k = 0
    
    # Create bucket with different entries
    bucket = [DUMMY_ENTRY] * bucket_size
    bucket[10] = ("other1", hash_func.hash_hex("other1"))
    bucket[20] = ("other2", hash_func.hash_hex("other2"))
    
    # Initialize DEGA
    dega = DEGASearch(
        n_qubits=n_qubits,
        chain_length=1000,
        password_length=8,
        hash_func=hash_func
    )
    
    print(f"[*] Bucket size: {bucket_size}")
    print(f"[*] Target hash: {target_hash} (not in bucket)")
    print()
    
    # Run search
    start = time.time()
    result = dega.search(bucket, target_hash, position_k)
    elapsed = time.time() - start
    
    print(f"[+] Result: {result}")
    print(f"[+] Time: {elapsed:.4f}s")
    
    if result is None:
        print("[✓] TEST PASSED: Correctly returned None!")
    else:
        print(f"[✗] TEST FAILED: Expected None, got {result}")
    
    print()


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "DEGA TEST SUITE" + " " * 38 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    try:
        test_dega_basic()
        test_dega_vs_grover()
        test_dega_odd_qubits()
        test_dega_not_found()
        
        print("=" * 70)
        print("ALL TESTS COMPLETED")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[✗] ERROR: {e}")
        import traceback
        traceback.print_exc()
