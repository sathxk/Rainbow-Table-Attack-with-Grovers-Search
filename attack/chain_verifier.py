"""
Classical chain verifier for the Quantum Rainbow Table Attack phase.

After Grover's measures an index, we retrieve the SP and classically
walk the full chain to confirm the target hash appears in it and to
extract the plaintext password that produces it.

Why classical verification is needed:
  1. Grover's has ~0.01% failure probability (wrong index measured).
  2. Bloom filter false positives trigger Grover on buckets without match.
  3. Dummy indices are silently discarded here.
"""

from typing import Optional

from rainbow_table_generator.hash_functions import HashFunction
from rainbow_table_generator.reduction import reduce


class ChainVerifier:
    """
    Walks a chain from an SP to find the password that hashes to target_hash.

    Example:
        >>> verifier = ChainVerifier(chain_length=1000, password_length=8,
        ...                         hash_func=SHA1HashFunction())
        >>> pwd = verifier.find_password("startpwd", "abc123...")
        >>> if pwd:
        ...     print(f"Cracked: {pwd}")
    """

    def __init__(
        self,
        chain_length: int,
        password_length: int,
        hash_func: HashFunction,
    ) -> None:
        if chain_length < 1:
            raise ValueError(f"chain_length must be >= 1, got {chain_length}")
        if password_length < 1:
            raise ValueError(f"password_length must be >= 1, got {password_length}")
        self.chain_length = chain_length
        self.password_length = password_length
        self.hash_func = hash_func

    def find_password(self, sp: str, target_hash_hex: str) -> Optional[str]:
        """
        Walk chain from SP; return the password P such that H(P) == target_hash.

        Returns None if target_hash doesn't appear in this chain.
        """
        if sp.startswith("__DUMMY"):
            return None

        target_bytes = bytes.fromhex(target_hash_hex)
        current = sp

        for i in range(self.chain_length):
            hash_val = self.hash_func.hash(current)
            if hash_val == target_bytes:
                return current  # ← cracked!
            current = reduce(hash_val, i, self.password_length)

        return None

    def verify_at_position(self, sp: str, target_hash_hex: str, position_k: int) -> bool:
        """
        Return True if H(pwd at position k in chain starting at SP) == target_hash.
        More efficient than find_password when the position is already known.
        """
        if sp.startswith("__DUMMY"):
            return False
        target_bytes = bytes.fromhex(target_hash_hex)
        current = sp
        for i in range(position_k):
            hash_val = self.hash_func.hash(current)
            current = reduce(hash_val, i, self.password_length)
        return self.hash_func.hash(current) == target_bytes

    def __repr__(self) -> str:
        return (
            f"ChainVerifier("
            f"chain_length={self.chain_length}, "
            f"password_length={self.password_length})"
        )
