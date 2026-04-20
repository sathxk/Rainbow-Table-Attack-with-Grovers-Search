"""
Attack phase package for the Quantum Rainbow Table Attack system.

Components:
    BloomFilter:    EP pre-screening (skips ~99.9% of candidate positions).
    DummyPadder:    Pads buckets to exactly 2^n for fixed-width quantum circuits.
    walk_forward:   Rebuild candidate_EP from target_hash at chain position k.
    BucketLoader:   SQLite wrapper to load chain entries by bucket_key.
    ChainVerifier:  Classical chain walk to extract the cracked plaintext password.
    GroverSearch:   Qiskit Grover's algorithm circuit on a padded bucket.
    RainbowAttack:  Main orchestrator wiring all components together.

Usage:
    from attack import RainbowAttack, BloomFilter
    from attack.walk_forward import walk_forward
"""

from attack.bloom_filter import BloomFilter
from attack.dummy_padding import DummyPadder
from attack.walk_forward import walk_forward
from attack.bucket_loader import BucketLoader
from attack.chain_verifier import ChainVerifier
from attack.grover_search import GroverSearch
from attack.orchestrator import RainbowAttack

__all__ = [
    "BloomFilter",
    "DummyPadder",
    "walk_forward",
    "BucketLoader",
    "ChainVerifier",
    "GroverSearch",
    "RainbowAttack",
]
