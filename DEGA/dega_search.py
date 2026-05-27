"""
DEGA (Distributed Exact Grover's Algorithm) for Rainbow Table Attack.

Key differences from standard Grover's:
- Deterministic (100% success rate)
- Constant circuit depth: 9 for even n, 17 for odd n
- Partitions search into ⌊n/2⌋ independent 2-qubit or 3-qubit sub-searches
- 6-10× faster simulation time

Reference:
    Zhou, X., Qiu, D., & Luo, L. (2023). Distributed exact Grover's algorithm.
    Frontiers of Physics, 18(5), 51305.
"""

import math
from typing import List, Optional, Tuple

from rainbow_table_generator.hash_functions import HashFunction
from rainbow_table_generator.reduction import reduce
from attack.dummy_padding import DUMMY_ENTRY

try:
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    from qiskit.circuit.library import DiagonalGate
except ImportError as _e:
    raise ImportError(
        "DEGASearch requires Qiskit. Install with: pip install qiskit"
    ) from _e

ChainEntry = Tuple[str, str]


class DEGASearch:
    """
    Distributed Exact Grover's Algorithm for searching within a padded bucket.

    DEGA partitions the n-qubit search into ⌊n/2⌋ independent sub-searches,
    each operating on 2 or 3 qubits. This dramatically reduces circuit depth
    and provides deterministic success.

    Attributes:
        n_qubits (int):        Circuit width; bucket_size = 2^n_qubits.
        n_pairs (int):         Number of 2-qubit sub-searches.
        has_odd_qubit (bool):  Whether there's a final 3-qubit sub-search.
        chain_length (int):    For oracle evaluation.
        password_length (int): For reduction function.
        hash_func:             HashFunction instance.

    Example:
        >>> searcher = DEGASearch(n_qubits=8, chain_length=1000,
        ...                       password_length=8, hash_func=SHA1HashFunction())
        >>> idx = searcher.search(padded_bucket, target_hash_hex="abc...", position_k=888)
    """

    def __init__(
        self,
        n_qubits: int,
        chain_length: int,
        password_length: int,
        hash_func: HashFunction,
    ) -> None:
        if n_qubits < 2:
            raise ValueError(f"n_qubits must be >= 2 for DEGA, got {n_qubits}")
        
        self.n_qubits = n_qubits
        self.chain_length = chain_length
        self.password_length = password_length
        self.hash_func = hash_func
        
        # Partitioning strategy from DEGA paper:
        # For even n: n/2 pairs of 2 qubits
        # For odd n: (n-3)/2 pairs of 2 qubits + 1 group of 3 qubits
        if n_qubits % 2 == 0:
            self.n_pairs = n_qubits // 2
            self.has_odd_qubit = False
        else:
            self.n_pairs = (n_qubits - 3) // 2
            self.has_odd_qubit = True
        
        # Pre-compute diffuser diagonals for 2-qubit and 3-qubit cases
        self._diffuser_2q = self._build_diffuser_diagonal(2)
        if self.has_odd_qubit:
            self._diffuser_3q = self._build_diffuser_diagonal(3)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        padded_bucket: List[ChainEntry],
        target_hash_hex: str,
        position_k: int,
        candidate_ep_hex: Optional[str] = None,
    ) -> Optional[int]:
        """
        Run DEGA search on a padded bucket for target_hash at position k.

        Args:
            padded_bucket:    List of (start_point, end_point) tuples, padded to 2^n.
            target_hash_hex:  40-char SHA-1 hex string to search for.
            position_k:       Chain position where target_hash should appear.
            candidate_ep_hex: Optional 40-char hex endpoint for pre-filtering.

        Returns:
            Index of the matching entry in padded_bucket, or None if no match.

        Raises:
            ValueError: If len(padded_bucket) != 2^n_qubits.
        """
        expected = 2 ** self.n_qubits
        if len(padded_bucket) != expected:
            raise ValueError(
                f"padded_bucket must have exactly {expected} entries "
                f"(got {len(padded_bucket)})"
            )

        # Step 1: Find marked 2-bit patterns for each sub-function
        marked_patterns = []
        for pair_idx in range(self.n_pairs):
            pattern = self._find_marked_pattern(
                padded_bucket, target_hash_hex, position_k, 
                pair_idx, candidate_ep_hex, bits=2
            )
            if pattern is None:
                return None  # No match found in this sub-search
            marked_patterns.append(pattern)

        # Step 2: Handle odd qubit if present (3-qubit sub-search)
        if self.has_odd_qubit:
            pattern = self._find_marked_pattern(
                padded_bucket, target_hash_hex, position_k,
                self.n_pairs, candidate_ep_hex, bits=3
            )
            if pattern is None:
                return None
            marked_patterns.append(pattern)

        # Step 3: Build DEGA circuit
        qc = self._build_dega_circuit(marked_patterns)

        # Step 4: Simulate and extract bucket index
        return self._simulate(qc)

    # ------------------------------------------------------------------
    # Classical oracle - Sub-function evaluation
    # ------------------------------------------------------------------

    def _find_marked_pattern(
        self,
        padded_bucket: List[ChainEntry],
        target_hash_hex: str,
        position_k: int,
        sub_idx: int,
        candidate_ep_hex: Optional[str],
        bits: int,
    ) -> Optional[int]:
        """
        Find which bit pattern (0-3 for 2 bits, 0-7 for 3 bits) is marked
        for sub-function sub_idx.

        This evaluates the sub-function g_i for all possible patterns and
        returns the marked one.

        Args:
            padded_bucket:    The bucket to search.
            target_hash_hex:  Target hash.
            position_k:       Chain position.
            sub_idx:          Sub-function index (0 to n_pairs or n_pairs for odd).
            candidate_ep_hex: Optional endpoint pre-filter.
            bits:             2 or 3 (size of sub-function).

        Returns:
            The marked bit pattern (0-3 or 0-7), or None if no match.
        """
        target_bytes = bytes.fromhex(target_hash_hex)
        num_patterns = 2 ** bits
        
        for pattern in range(num_patterns):
            if self._evaluate_subfunction(
                padded_bucket, target_bytes, position_k,
                sub_idx, pattern, bits, candidate_ep_hex
            ):
                return pattern
        
        return None

    def _evaluate_subfunction(
        self,
        padded_bucket: List[ChainEntry],
        target_bytes: bytes,
        position_k: int,
        sub_idx: int,
        pattern: int,
        bits: int,
        candidate_ep_hex: Optional[str],
    ) -> bool:
        """
        Evaluate sub-function g_i(pattern).

        Returns True if ANY bucket index with the specified bit pattern
        at the sub-function's position contains the target hash.

        For example, if sub_idx=1 (bits 2-3) and pattern=0b11:
        - Check all bucket indices where bits 2-3 are 0b11
        - That's indices: ..00110000, ..00110001, ..00110010, etc.
        - Return True if any of them contain the target

        Args:
            padded_bucket:    The bucket to search.
            target_bytes:     Target hash as bytes.
            position_k:       Chain position.
            sub_idx:          Sub-function index.
            pattern:          Bit pattern to check (0-3 or 0-7).
            bits:             2 or 3.
            candidate_ep_hex: Optional endpoint pre-filter.

        Returns:
            True if this pattern is marked (contains target), False otherwise.
        """
        # Calculate bit positions for this sub-function
        bit_start = sub_idx * 2
        
        # Iterate through all bucket indices
        for idx in range(len(padded_bucket)):
            # Extract the relevant bits from the index
            if bits == 2:
                relevant_bits = (idx >> bit_start) & 0b11
            else:  # bits == 3
                relevant_bits = (idx >> bit_start) & 0b111
            
            # Skip if this index doesn't match the pattern we're checking
            if relevant_bits != pattern:
                continue
            
            # Skip dummy entries
            entry = padded_bucket[idx]
            if entry == DUMMY_ENTRY:
                continue
            
            # Endpoint pre-filtering optimization
            if candidate_ep_hex is not None and entry[1] != candidate_ep_hex:
                continue
            
            # Check if this entry contains the target
            if self._oracle_evaluate(entry[0], target_bytes, position_k):
                return True
        
        return False

    def _oracle_evaluate(self, sp: str, target_bytes: bytes, position_k: int) -> bool:
        """Walk chain from SP for position_k steps; check if H(pwd_k) == target."""
        current = sp
        for i in range(position_k):
            hash_val = self.hash_func.hash(current)
            current = reduce(hash_val, i, self.password_length)
        return self.hash_func.hash(current) == target_bytes

    # ------------------------------------------------------------------
    # Quantum circuit construction
    # ------------------------------------------------------------------

    def _build_dega_circuit(self, marked_patterns: List[int]) -> QuantumCircuit:
        """
        Build DEGA circuit with independent Grover iterations for each sub-function.

        For n=8 (even): 4 pairs of 2 qubits, each runs 1 Grover iteration
        For n=9 (odd):  4 pairs of 2 qubits + 1 group of 3 qubits (2 iterations)

        Args:
            marked_patterns: List of marked bit patterns for each sub-function.

        Returns:
            Complete DEGA quantum circuit.
        """
        qc = QuantumCircuit(self.n_qubits)
        
        # Initialize all qubits to superposition
        qc.h(range(self.n_qubits))
        
        # Apply Grover iteration to each 2-qubit pair
        for pair_idx in range(self.n_pairs):
            qubit_start = pair_idx * 2
            qubits = [qubit_start, qubit_start + 1]
            marked = marked_patterns[pair_idx]
            
            # Single Grover iteration for 2 qubits
            self._apply_grover_iteration_2q(qc, qubits, marked)
        
        # Handle odd qubit (3-qubit sub-search with 2 iterations)
        if self.has_odd_qubit:
            # For n=9: first 3 pairs cover qubits 0-5, last 3 qubits are 6-8
            qubit_start = self.n_pairs * 2
            qubits = [qubit_start, qubit_start + 1, qubit_start + 2]
            marked = marked_patterns[self.n_pairs]
            
            # Two Grover iterations for 3 qubits (for deterministic success)
            for _ in range(2):
                self._apply_grover_iteration_3q(qc, qubits, marked)
        
        return qc

    def _apply_grover_iteration_2q(
        self, 
        qc: QuantumCircuit, 
        qubits: List[int], 
        marked: int
    ) -> None:
        """
        Apply one Grover iteration to a 2-qubit sub-function.

        Args:
            qc:     Quantum circuit to modify.
            qubits: List of 2 qubit indices.
            marked: Marked state (0-3).
        """
        # Oracle: mark the target state
        oracle_diag = [1.0 + 0j] * 4
        oracle_diag[marked] = -1.0 + 0j
        qc.append(DiagonalGate(oracle_diag), qubits)
        
        # Diffuser: 2|s⟩⟨s| - I
        qc.h(qubits)
        qc.append(DiagonalGate(self._diffuser_2q), qubits)
        qc.h(qubits)

    def _apply_grover_iteration_3q(
        self,
        qc: QuantumCircuit,
        qubits: List[int],
        marked: int
    ) -> None:
        """
        Apply one Grover iteration to a 3-qubit sub-function.

        Args:
            qc:     Quantum circuit to modify.
            qubits: List of 3 qubit indices.
            marked: Marked state (0-7).
        """
        # Oracle: mark the target state
        oracle_diag = [1.0 + 0j] * 8
        oracle_diag[marked] = -1.0 + 0j
        qc.append(DiagonalGate(oracle_diag), qubits)
        
        # Diffuser: 2|s⟩⟨s| - I
        qc.h(qubits)
        qc.append(DiagonalGate(self._diffuser_3q), qubits)
        qc.h(qubits)

    def _build_diffuser_diagonal(self, n: int) -> List[complex]:
        """
        Build diffuser diagonal for n qubits: 2|0⟩⟨0| - I.

        Args:
            n: Number of qubits (2 or 3).

        Returns:
            Diagonal elements for DiagonalGate.
        """
        N = 2 ** n
        diag = [-1.0 + 0j] * N
        diag[0] = 1.0 + 0j
        return diag

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def _simulate(self, qc: QuantumCircuit) -> int:
        """
        Simulate DEGA circuit and return the most probable basis state.

        Returns:
            Bucket index (0 to 2^n_qubits - 1).
        """
        sv = Statevector(qc)
        probs = sv.probabilities()
        return int(probs.argmax())

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def circuit_depth(self) -> int:
        """
        Theoretical circuit depth for DEGA.

        Returns:
            9 for even n_qubits, 17 for odd n_qubits.
        """
        if self.has_odd_qubit:
            return 17
        return 9

    def __repr__(self) -> str:
        return (
            f"DEGASearch("
            f"n_qubits={self.n_qubits}, "
            f"n_pairs={self.n_pairs}, "
            f"has_odd={self.has_odd_qubit}, "
            f"depth={self.circuit_depth}, "
            f"chain_length={self.chain_length})"
        )
