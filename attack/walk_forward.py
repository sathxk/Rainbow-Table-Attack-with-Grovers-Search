"""
Walk-forward engine for the Quantum Rainbow Table Attack phase.

For each candidate chain position k (from chain_length-1 down to 0),
we "walk forward" from the target hash to reconstruct the endpoint that
would exist in the table IF the target hash appeared at position k.

Chain structure:
    pwd_0(SP) →[H,R_0]→ pwd_1 →[H,R_1]→ ... →[H,R_{t-1}]→ pwd_t → H → EP(stored)

If target_hash = H(pwd_k), walking forward from position k:
    R_k(target_hash) → pwd_{k+1}
    H(pwd_{k+1})      → ...
    R_{t-1}(...)      → pwd_t
    H(pwd_t)          → candidate_EP  ← should match a stored EP
"""

from rainbow_table_generator.hash_functions import HashFunction
from rainbow_table_generator.reduction import reduce


def walk_forward(
    target_hash_hex: str,
    position_k: int,
    chain_length: int,
    password_length: int,
    hash_func: HashFunction,
) -> str:
    """
    Walk a chain forward from position k to produce a candidate endpoint.

    Args:
        target_hash_hex: 40-char SHA-1 hex — the hash to crack.
        position_k:      Chain position assumed for target_hash [0, chain_length-1].
        chain_length:    Total hash-reduce iterations per chain (e.g. 1000).
        password_length: Password length produced by reduction (e.g. 8).
        hash_func:       HashFunction instance (e.g. SHA1HashFunction()).

    Returns:
        candidate_EP as a 40-char hex string.

    Raises:
        ValueError: If position_k is outside [0, chain_length - 1].
    """
    if not (0 <= position_k < chain_length):
        raise ValueError(
            f"position_k must be in [0, {chain_length - 1}], got {position_k}"
        )

    current_hash_bytes = bytes.fromhex(target_hash_hex)

    # Apply (Reduce at j, Hash) for j = position_k .. chain_length-1
    for j in range(position_k, chain_length):
        password = reduce(current_hash_bytes, j, password_length)
        current_hash_bytes = hash_func.hash(password)

    return current_hash_bytes.hex()
