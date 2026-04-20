"""
Dummy Padding for the Quantum Rainbow Table Attack phase.

Grover's algorithm requires a fixed-size search space: exactly 2^n entries
for an n-qubit circuit. Real buckets have between 1 and bucket_size
entries (and at most bucket_size = 2^n due to fill_factor). DummyPadder
fills the gap with sentinel entries that are mathematically distinguishable
from real entries and can never be mistaken for valid passwords or hashes.

Sentinel design:
    DUMMY_SP: "__DUMMY_SP__"  — never a valid charset[a-z0-9] × 8 password
    DUMMY_EP: "__DUMMY_EP__"  — never a valid 40-char SHA-1 hex string

After Grover's measures an index, the verifier calls is_dummy() before
relying on the result. A dummy result means the oracle had no marked items
(shouldn't happen if Bloom filter is working correctly) or Grover's made a
measurement error (< 0.01% probability for n=10).
"""

from typing import List, Tuple

# Sentinels — chosen to be invalid passwords AND invalid SHA-1 hex strings
DUMMY_SP: str = "__DUMMY_SP__"
DUMMY_EP: str = "__DUMMY_EP__"
DUMMY_ENTRY: Tuple[str, str] = (DUMMY_SP, DUMMY_EP)

_MAX_QUBITS = 20  # sanity cap: 2^20 = 1,048,576 entries


class DummyPadder:
    """
    Pads a bucket to exactly 2^n_qubits entries for quantum circuit compatibility.

    Appends DUMMY_ENTRY sentinels until len(bucket) == bucket_size.
    Real entries are preserved in their original order; dummies come last.

    Attributes:
        n_qubits (int):    Number of qubits (circuit width).
        bucket_size (int): Fixed target size = 2^n_qubits.

    Example:
        >>> padder = DummyPadder(n_qubits=10)
        >>> padded = padder.pad(real_entries)   # len == 1024
        >>> padder.count_real(padded)           # original count
        >>> padder.strip(padded)                # back to real entries
    """

    def __init__(self, n_qubits: int) -> None:
        """
        Args:
            n_qubits: Number of qubits; bucket_size = 2^n_qubits.
        Raises:
            ValueError: If n_qubits is outside [1, 20].
        """
        if not (1 <= n_qubits <= _MAX_QUBITS):
            raise ValueError(
                f"n_qubits must be in [1, {_MAX_QUBITS}], got {n_qubits}"
            )
        self.n_qubits = n_qubits
        self.bucket_size = 2 ** n_qubits

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def pad(self, entries: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Return a new list of exactly bucket_size (SP, EP) tuples.

        Real entries are placed first (preserving order); DUMMY_ENTRYs fill
        the remaining slots.

        Args:
            entries: List of real (start_point, end_point) tuples.

        Returns:
            New list of exactly self.bucket_size tuples.

        Raises:
            ValueError: If len(entries) > bucket_size (bucket overflow).
        """
        n = len(entries)
        if n > self.bucket_size:
            raise ValueError(
                f"Bucket overflow: {n} entries exceed bucket_size={self.bucket_size}. "
                f"Check fill_factor in config."
            )
        padding_needed = self.bucket_size - n
        return list(entries) + [DUMMY_ENTRY] * padding_needed

    def is_dummy(self, entry: Tuple[str, str]) -> bool:
        """Return True if entry is a dummy sentinel."""
        return entry == DUMMY_ENTRY

    def strip(self, padded: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Return only the real (non-dummy) entries from a padded list."""
        return [e for e in padded if not self.is_dummy(e)]

    # ------------------------------------------------------------------
    # Count helpers
    # ------------------------------------------------------------------

    def count_real(self, padded: List[Tuple[str, str]]) -> int:
        """Number of real (non-dummy) entries in padded bucket."""
        return sum(1 for e in padded if not self.is_dummy(e))

    def count_dummies(self, padded: List[Tuple[str, str]]) -> int:
        """Number of dummy entries in padded bucket."""
        return sum(1 for e in padded if self.is_dummy(e))

    def __repr__(self) -> str:
        return f"DummyPadder(n_qubits={self.n_qubits}, bucket_size={self.bucket_size})"
