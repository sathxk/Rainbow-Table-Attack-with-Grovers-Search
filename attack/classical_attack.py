"""
Classical Rainbow Table Attack

Traditional rainbow table attack using hash table lookups for endpoint matching.
This serves as a baseline for comparison with the quantum-enhanced attack.

Key differences from quantum attack:
- Uses hash table (dict) for O(1) endpoint lookups instead of Grover's search
- No bucketing needed - direct endpoint lookup
- No Bloom filter needed - hash table provides instant membership test
- Simpler implementation, purely classical
"""

import sqlite3
import time
from typing import Optional, Dict
from rainbow_table_generator.config import Config
from rainbow_table_generator.hash_functions import hash_factory
from rainbow_table_generator.reduction import reduce


def load_hashes(path: str) -> list[str]:
    """
    Load hashes from a text file, one per line.
    Lines starting with '#' are treated as comments and ignored.
    Inline comments after the hash (separated by whitespace) are stripped.
    """
    hashes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            hashes.append(line.split()[0])
    return hashes


class ClassicalRainbowAttack:
    """
    Classical rainbow table attack using hash table lookups.

    This implementation uses the traditional approach:
    1. Load all endpoints into a hash table (dict) once at init
    2. For each position k, compute candidate endpoint
    3. O(1) hash table lookup to find matching chain
    4. Walk chain forward to verify and recover password

    Note:
        Endpoints are loaded into memory once during __init__.
        Subsequent crack() calls use the in-memory hash table with no DB access.
    """

    def __init__(self, config: Config, db_path: str):
        self.config = config
        self.db_path = db_path
        self.endpoint_map: Dict[str, str] = {}
        self.hash_func = hash_factory(config.hash_algorithm)
        self._load_endpoints()

    def _load_endpoints(self):
        """Load all (end_point → start_point) pairs into memory."""
        print(f"[*] Loading endpoints into hash table...")
        start_time = time.time()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT end_point, start_point FROM chains")

        count = 0
        for end_point, start_point in cursor:
            self.endpoint_map[end_point] = start_point
            count += 1
            if count % 1_000_000 == 0:
                print(f"    Loaded {count:,} endpoints...")

        conn.close()
        elapsed = time.time() - start_time
        print(f"[+] Loaded {len(self.endpoint_map):,} unique endpoints in {elapsed:.2f}s")
        print(f"[+] Hash table memory: ~{len(self.endpoint_map) * 100 / 1024 / 1024:.1f} MB")

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

    def crack(self, target_hash: str, verbose: bool = False) -> Optional[str]:
        """
        Crack a hash using the classical rainbow table attack.

        Args:
            target_hash: SHA-1 hex string to crack.
            verbose:     Print progress per position.

        Returns:
            Plaintext password, or None if not found.
        """
        if verbose:
            print(f"[*] Classical attack on: {target_hash}")

        for k in range(self.config.chain_length - 1, -1, -1):
            candidate_ep = self._compute_candidate_endpoint(target_hash, k)

            if candidate_ep in self.endpoint_map:
                if verbose:
                    print(f"[k={k}] Endpoint match → verifying chain...")
                start_point = self.endpoint_map[candidate_ep]
                password = self._walk_forward(start_point, target_hash, k)
                if password:
                    return password

        return None
