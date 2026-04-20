"""
Grover's Search for the Quantum Rainbow Table Attack phase.

Architecture — Lookup-Table Oracle (Simulation Standard):
    On a real quantum computer the oracle would implement SHA-1 in reversible
    gates (millions of Toffoli gates — impractical today). For simulation we
    use the standard "lookup-table oracle" approach from quantum algorithm
    research:
        1. Classically evaluate all 2^n entries to find the marked index.
        2. Encode that index as a phase oracle (DiagonalGate: -1 at marked).
        3. Run the full Grover iteration loop (Hadamard + Oracle + Diffuser).
        4. Simulate with Qiskit Statevector and return argmax of probabilities.

Grover parameters for n=10 qubits, N=1024:
    iterations = floor((π/4)√N) = floor((π/4)×32) = 25
    Success probability ≈ 99.99%
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
        "GroverSearch requires Qiskit. Install with: pip install qiskit"
    ) from _e

ChainEntry = Tuple[str, str]


class GroverSearch:
    """
    Builds and runs a Grover's algorithm circuit to search within a padded bucket.

    Attributes:
        n_qubits (int):        Circuit width; bucket_size = 2^n_qubits.
        n_iterations (int):    Optimal Grover iterations = ⌊(π/4)√N⌋.
        chain_length (int):    For oracle evaluation.
        password_length (int): For reduction function.
        hash_func:             HashFunction instance.

    Example:
        >>> searcher = GroverSearch(n_qubits=10, chain_length=1000,
        ...                        password_length=8, hash_func=SHA1HashFunction())
        >>> idx = searcher.search(padded_bucket, target_hash_hex="abc...", position_k=888)
    """

    def __init__(
        self,
        n_qubits: int,
        chain_length: int,
        password_length: int,
        hash_func: HashFunction,
    ) -> None:
        if n_qubits < 1:
            raise ValueError(f"n_qubits must be >= 1, got {n_qubits}")
        self.n_qubits = n_qubits
        self.n_iterations = max(1, math.floor((math.pi / 4) * math.sqrt(2 ** n_qubits)))
        self.chain_length = chain_length
        self.password_length = password_length
        self.hash_func = hash_func
        
        # Optimization 3: Pre-compute and cache diffuser diagonal
        N = 2 ** n_qubits
        self._diffuser_diag = [-1.0 + 0j] * N
        self._diffuser_diag[0] = 1.0 + 0j

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
        Run Grover's search on a padded bucket for target_hash at position k.

        Args:
            padded_bucket:    List of (start_point, end_point) tuples, padded to 2^n.
            target_hash_hex:  40-char SHA-1 hex string to search for.
            position_k:       Chain position where target_hash should appear.
            candidate_ep_hex: Optional 40-char hex endpoint for pre-filtering.
                              If provided, only entries with matching endpoints
                              will be checked (massive speedup).

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

        # Step 1: Classical oracle — find marked index
        marked_index = self._classical_oracle(
            padded_bucket, target_hash_hex, position_k, candidate_ep_hex
        )
        if marked_index is None:
            return None

        # Step 2: Build + simulate Grover circuit
        qc = self._build_circuit(marked_index)
        return self._simulate(qc)

    # ------------------------------------------------------------------
    # Classical oracle
    # ------------------------------------------------------------------

    def _classical_oracle(
        self,
        padded_bucket: List[ChainEntry],
        target_hash_hex: str,
        position_k: int,
        candidate_ep_hex: Optional[str] = None,
    ) -> Optional[int]:
        """
        Find the first bucket index whose chain contains target_hash at position_k.
        
        Optimization: If candidate_ep_hex is provided, pre-filter by endpoint first.
        This eliminates ~99.9% of entries with a simple string comparison before
        doing expensive chain-walking.
        """
        target_bytes = bytes.fromhex(target_hash_hex)
        for i, entry in enumerate(padded_bucket):
            if entry == DUMMY_ENTRY:
                continue
            
            # Optimization 1: Endpoint pre-filtering
            # If we know the candidate endpoint, check it first (O(1) string compare)
            # Only walk the chain if the endpoint matches
            if candidate_ep_hex is not None and entry[1] != candidate_ep_hex:
                continue
            
            if self._oracle_evaluate(entry[0], target_bytes, position_k):
                return i
        return None

    def _oracle_evaluate(self, sp: str, target_bytes: bytes, position_k: int) -> bool:
        """Walk chain from SP for position_k steps; check if H(pwd_k) == target."""
        current = sp
        for i in range(position_k):
            hash_val = self.hash_func.hash(current)
            current = reduce(hash_val, i, self.password_length)
        return self.hash_func.hash(current) == target_bytes

    # ------------------------------------------------------------------
    # Quantum circuit
    # ------------------------------------------------------------------

    def _build_circuit(self, marked_index: int) -> QuantumCircuit:
        """
        Build Grover circuit: H^n → [Oracle + Diffuser] × n_iterations.
        
        Optimization 3: Reuse cached diffuser diagonal instead of rebuilding.
        """
        n = self.n_qubits
        N = 2 ** n
        qc = QuantumCircuit(n)
        qc.h(range(n))

        # Build oracle diagonal (must be fresh for each marked_index)
        oracle_diag = [1.0 + 0j] * N
        oracle_diag[marked_index] = -1.0 + 0j

        for _ in range(self.n_iterations):
            # Phase oracle
            qc.append(DiagonalGate(oracle_diag), range(n))
            # Diffuser: 2|s⟩⟨s| − I = H^n (2|0⟩⟨0| − I) H^n
            # Use cached diffuser diagonal
            qc.h(range(n))
            qc.append(DiagonalGate(self._diffuser_diag), range(n))
            qc.h(range(n))

        return qc

    def _simulate(self, qc: QuantumCircuit) -> int:
        """Simulate and return the most probable basis state (argmax of probs)."""
        sv = Statevector(qc)
        probs = sv.probabilities()
        return int(probs.argmax())

    def __repr__(self) -> str:
        return (
            f"GroverSearch("
            f"n_qubits={self.n_qubits}, "
            f"n_iterations={self.n_iterations}, "
            f"chain_length={self.chain_length})"
        )
