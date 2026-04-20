"""
Bucket organizer module for rainbow table generation.

This module provides the BucketOrganizer class that manages the distribution
of SP-EP pairs into buckets for quantum search. Each bucket holds at most
bucket_size (2^N) entries, which is the search space size that Grover's
algorithm will operate on.

The bucketing strategy uses the hash endpoint directly to assign
entries to buckets, ensuring uniform distribution across millions of buckets.
"""

import math
from typing import Dict, List, Tuple


class BucketOrganizer:
    """
    Organizer for distributing SP-EP pairs into buckets for quantum search.

    Uses hash values (endpoints) directly for bucket assignment:
      - bucket_key  = int(endpoint[:8], 16) % num_buckets
      - intra_value = int(endpoint[:8], 16) % bucket_size

    Each bucket contains at most bucket_size (2^N) entries, which is the
    search-space size that Grover's algorithm will operate on.

    Attributes:
        qubit_count:  Number of qubits N
        bucket_size:  Entries per bucket (2^N)
        num_buckets:  Total number of buckets needed
        buckets:      Dict mapping bucket_key -> list of (SP, EP, intra_value)
    """

    def __init__(self, qubit_count: int, total_entries: int, fill_factor: float = 0.75):
        """
        Initialize the BucketOrganizer.

        Args:
            qubit_count:   Number of qubits N (must be >= 1)
            total_entries: Total number of entries to be stored
            fill_factor:   Target occupancy per bucket (0 < fill_factor <= 1).
                           Over-provisioning (< 1.0) prevents modulo-bias collisions
                           from pushing any bucket above bucket_size (2^N) entries.
                           At fill_factor=0.75 the average bucket uses 75% capacity,
                           leaving a 25% headroom for uneven distribution.

        Raises:
            ValueError: If qubit_count < 1, total_entries < 1, or fill_factor invalid
        """
        if qubit_count < 1:
            raise ValueError(f"qubit_count must be positive, got {qubit_count}")
        if total_entries < 1:
            raise ValueError(f"total_entries must be positive, got {total_entries}")
        if not (0 < fill_factor <= 1.0):
            raise ValueError(f"fill_factor must be in (0, 1], got {fill_factor}")

        self.qubit_count = qubit_count
        self.bucket_size = 2 ** qubit_count  # entries per bucket (Grover's search space)
        self.fill_factor = fill_factor

        # Over-provision: effective_capacity per bucket = bucket_size * fill_factor
        # num_buckets = ceil(total / effective_capacity)
        import math as _math
        effective_capacity = self.bucket_size * fill_factor
        self.num_buckets = _math.ceil(total_entries / effective_capacity)

        # Dynamic dict: bucket_key -> [(start_point, end_point, intra_value)]
        self.buckets: Dict[int, List[Tuple[str, str, int]]] = {}

    def __repr__(self) -> str:
        return (
            f"BucketOrganizer("
            f"qubit_count={self.qubit_count}, "
            f"bucket_size={self.bucket_size}, "
            f"num_buckets={self.num_buckets}, "
            f"active_buckets={len(self.buckets)})"
        )

    def assign_bucket(self, end_point: str) -> int:
        """
        Return the bucket_key for a given endpoint hash.

        Uses the first 8 hex characters (32 bits) of the hash to
        calculate the bucket assignment.

        Args:
            end_point: Endpoint value (hash as hex string)

        Returns:
            bucket_key in range [0, num_buckets)
            
        Raises:
            ValueError: If end_point is empty or not a valid hex string
        """
        if not end_point:
            raise ValueError("end_point cannot be empty")
        
        # Validate it's a hex string
        if not all(c in '0123456789abcdefABCDEF' for c in end_point[:8]):
            raise ValueError("end_point must be a valid hexadecimal string")
        
        # Use first 8 hex chars (32 bits) of hash
        hash_value = int(end_point[:8], 16)
        
        # Distribute across buckets using modulo
        return hash_value % self.num_buckets

    def intra_bucket_value(self, end_point: str) -> int:
        """
        Return the intra-bucket value for a given endpoint.

        Uses the first 8 hex characters (32 bits) of the hash to
        calculate the position within the bucket.

        Args:
            end_point: Endpoint value (hash as hex string)

        Returns:
            intra_value in range [0, bucket_size)
        """
        # Use first 8 hex chars (32 bits) of hash
        hash_value = int(end_point[:8], 16)
        
        # Position within bucket
        return hash_value % self.bucket_size

    def add_to_bucket(self, start_point: str, end_point: str) -> None:
        """
        Add an SP-EP pair to the appropriate bucket buffer.

        Args:
            start_point: Start point (initial password)
            end_point:   End point value

        Raises:
            ValueError: If either argument is empty
        """
        if not start_point:
            raise ValueError("start_point cannot be empty")
        if not end_point:
            raise ValueError("end_point cannot be empty")

        bucket_key = self.assign_bucket(end_point)
        intra = self.intra_bucket_value(end_point)

        if bucket_key not in self.buckets:
            self.buckets[bucket_key] = []

        self.buckets[bucket_key].append((start_point, end_point, intra))

    def get_bucket_counts(self) -> Dict[int, int]:
        """Return a dict of bucket_key -> current buffer size."""
        return {k: len(v) for k, v in self.buckets.items()}

    def get_bucket(self, bucket_key: int) -> List[Tuple[str, str, int]]:
        """
        Return buffered entries for a bucket_key.

        Args:
            bucket_key: Key returned by assign_bucket()

        Returns:
            List of (start_point, end_point, intra_value) tuples
        """
        return self.buckets.get(bucket_key, [])

    def all_bucket_keys(self) -> List[int]:
        """Return all bucket keys that currently have buffered data."""
        return list(self.buckets.keys())

    def clear_bucket(self, bucket_key: int) -> None:
        """Clear the in-memory buffer for a bucket_key."""
        if bucket_key in self.buckets:
            self.buckets[bucket_key] = []

    def clear_all_buckets(self) -> None:
        """Clear all in-memory bucket buffers."""
        self.buckets.clear()

    def get_total_entries(self) -> int:
        """Return total buffered entries across all buckets."""
        return sum(len(v) for v in self.buckets.values())
