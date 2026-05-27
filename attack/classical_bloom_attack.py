"""
Memory-Efficient Classical Rainbow Table Attack with Bloom Filter

Traditional rainbow table attack that uses a Bloom filter for pre-screening.
This reduces memory usage from 3.6 GB to 65.6 MB.

Key differences from standard classical attack:
- Uses Bloom filter for endpoint pre-screening (65.6 MB)
- Direct database query for specific endpoint (not bucketing)
- O(1) database lookup with indexed query
- Memory-efficient and nearly as fast as hash table approach

Comparison:
- Standard Classical: 3.6 GB RAM, 0.679s/hash, O(1) hash table lookup
- Classical + Bloom:  65.6 MB RAM, 0.627s/hash, O(1) indexed SQL query
- Quantum + Bloom:    65.6 MB RAM, 1.091s/hash, O(√N) Grover search

Note: Bucketing is NOT used in classical attacks - that's a quantum-specific
optimization. Classical attacks query the database directly by endpoint.
"""

import sqlite3
from typing import Optional
from rainbow_table_generator.config import Config
from rainbow_table_generator.hash_functions import hash_factory
from rainbow_table_generator.reduction import reduce
from attack.bloom_filter import BloomFilter


class ClassicalBloomAttack:
    """
    Memory-efficient classical rainbow table attack using Bloom filter.

    Traditional rainbow table approach with Bloom filter pre-screening.

    Workflow:
    1. Bloom filter pre-screens candidate endpoints (99.9% rejection)
    2. Direct SQL query for exact endpoint match
    3. Walk chain forward to verify and recover password
    """

    def __init__(
        self,
        config: Config,
        db_path: str,
        num_buckets: int,  # Kept for compatibility but not used
        bloom_filter: BloomFilter
    ):
        """
        Initialize memory-efficient classical attack.

        Args:
            config:       Configuration object
            db_path:      Path to rainbow table database
            num_buckets:  Not used (kept for API compatibility)
            bloom_filter: Pre-built Bloom filter for endpoint screening
        """
        self.config = config
        self.db_path = db_path
        self.bloom = bloom_filter
        self.hash_func = hash_factory(config.hash_algorithm)
        self.conn = None

    def _compute_candidate_endpoint(self, target_hash: str, position: int) -> str:
        """
        Compute the candidate endpoint assuming target_hash is at chain position k.
        """
        current = reduce(
            bytes.fromhex(target_hash),
            iteration=position,
            password_length=self.config.password_length
        )
        for k in range(position + 1, self.config.chain_length):
            current_hash = self.hash_func.hash_hex(current)
            current = reduce(
                bytes.fromhex(current_hash),
                iteration=k,
                password_length=self.config.password_length
            )
        return self.hash_func.hash_hex(current)

    def _walk_forward(self, start_point: str, target_hash: str, up_to: int) -> Optional[str]:
        """
        Walk a chain from start_point up to position up_to looking for target_hash.
        Returns the plaintext password if found, else None.
        """
        current = start_point
        for k in range(up_to + 1):
            current_hash = self.hash_func.hash_hex(current)
            if current_hash == target_hash:
                return current
            if k < self.config.chain_length - 1:
                current = reduce(
                    bytes.fromhex(current_hash),
                    iteration=k,
                    password_length=self.config.password_length
                )
        return None

    def _query_endpoint(self, candidate_ep: str) -> Optional[str]:
        """
        Query database directly for a specific endpoint.
        
        Traditional rainbow table approach: direct lookup by endpoint.
        No bucketing needed - that's quantum-specific.

        Args:
            candidate_ep: Endpoint to search for

        Returns:
            Start point if found, None otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT start_point FROM chains WHERE end_point = ? LIMIT 1",
            (candidate_ep,)
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def crack(self, target_hash: str, verbose: bool = False) -> Optional[str]:
        """
        Crack a hash using memory-efficient classical attack with Bloom filter.

        Args:
            target_hash: SHA-1 hex string to crack
            verbose:     Print progress per position

        Returns:
            Plaintext password, or None if not found
        """
        if verbose:
            print(f"[*] Classical+Bloom attack on: {target_hash}")

        # Open database connection
        self.conn = sqlite3.connect(self.db_path)
        
        try:
            for k in range(self.config.chain_length - 1, -1, -1):
                candidate_ep = self._compute_candidate_endpoint(target_hash, k)

                # Bloom filter pre-screening (99.9% rejection rate)
                if not self.bloom.possibly_exists(candidate_ep):
                    continue

                if verbose:
                    print(f"[k={k}] Bloom filter match → querying database...")

                # Direct database query for endpoint (O(1) with index)
                start_point = self._query_endpoint(candidate_ep)

                if not start_point:
                    continue

                if verbose:
                    print(f"[k={k}] Endpoint found → verifying chain...")

                # Verify chain
                password = self._walk_forward(start_point, target_hash, k)
                if password:
                    return password
        finally:
            if self.conn:
                self.conn.close()
                self.conn = None

        return None

    @property
    def memory_mb(self) -> float:
        """Return memory usage in MB (Bloom filter only)."""
        return self.bloom.memory_bytes / 1024 / 1024
