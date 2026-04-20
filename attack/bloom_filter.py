"""
Bloom Filter for the Quantum Rainbow Table Attack phase.

Purpose: Pre-screen candidate endpoints before expensive DB queries and
Grover's circuit simulations. For each candidate_EP, the Bloom filter
answers "definitely absent" (skip immediately) or "possibly present"
(proceed with DB lookup + quantum search). This eliminates ~99.9% of
work when the target hash does NOT appear at a given chain position.

False positive rate: 0.1% (configurable). A false positive means we
run a Grover search on a bucket that doesn't contain the target —
classical verification catches this immediately.
"""

import json
import math
import struct
from pathlib import Path
from typing import Optional

try:
    import mmh3
    from bitarray import bitarray
except ImportError as e:
    raise ImportError(
        "BloomFilter requires mmh3 and bitarray. "
        "Install with: pip install mmh3 bitarray"
    ) from e


class BloomFilter:
    """
    Space-efficient probabilistic set for endpoint pre-screening.

    Uses k independent MurmurHash3 hash functions over a bitarray of
    m bits. Parameters m and k are computed from n_items and fpr:
        m = -n * ln(fpr) / ln(2)^2
        k = (m / n) * ln(2)

    Attributes:
        n_items (int):  Expected number of items to insert.
        fpr (float):    Target false positive rate (e.g. 0.001 = 0.1%).
        m (int):        Bit array size.
        k (int):        Number of hash functions.
        count (int):    Number of items inserted so far.

    Example:
        >>> bf = BloomFilter(n_items=38_285_441, fpr=0.001)
        >>> bf.add("aabbccddeeff112233445566778899aabbccddee")
        >>> bf.possibly_exists("aabbccddeeff112233445566778899aabbccddee")
        True
    """

    def __init__(self, n_items: int, fpr: float = 0.001, seed: int = 42) -> None:
        if n_items <= 0:
            raise ValueError(f"n_items must be > 0, got {n_items}")
        if not (0 < fpr < 1):
            raise ValueError(f"fpr must be in (0, 1), got {fpr}")

        self.n_items = n_items
        self.fpr = fpr
        self.seed = seed
        self.count = 0

        # Optimal parameters
        self.m = math.ceil(-n_items * math.log(fpr) / (math.log(2) ** 2))
        self.k = max(1, round((self.m / n_items) * math.log(2)))

        self._bits = bitarray(self.m)
        self._bits.setall(0)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def _hashes(self, item: str):
        """Yield k bit positions for item using double-hashing with mmh3."""
        h1 = mmh3.hash(item, self.seed, signed=False)
        h2 = mmh3.hash(item, self.seed + 1, signed=False)
        for i in range(self.k):
            yield (h1 + i * h2) % self.m

    def add(self, item: str) -> None:
        """Insert an item into the filter."""
        for pos in self._hashes(item):
            self._bits[pos] = 1
        self.count += 1

    def possibly_exists(self, item: str) -> bool:
        """
        Return True if item MIGHT be in the set (no false negatives).
        Return False if item is DEFINITELY NOT in the set.
        """
        return all(self._bits[pos] for pos in self._hashes(item))

    # ------------------------------------------------------------------
    # Batch build from database
    # ------------------------------------------------------------------

    def build_from_db(self, db_path: str, batch_size: int = 100_000) -> int:
        """
        Populate the filter with all endpoint hashes from the SQLite DB.

        Streams in batches to keep memory usage constant regardless of
        table size.

        Args:
            db_path:    Path to the rainbow_table.db SQLite file.
            batch_size: Rows to fetch per DB round-trip.

        Returns:
            Number of endpoints inserted.

        Raises:
            FileNotFoundError: If db_path does not exist.
        """
        import sqlite3

        db = Path(db_path)
        if not db.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        conn = sqlite3.connect(str(db))
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT end_point FROM chains")
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                for (ep,) in rows:
                    self.add(ep)
        finally:
            conn.close()

        return self.count

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, bits_path: str, meta_path: str) -> None:
        """
        Save the Bloom filter to disk.

        Args:
            bits_path: Path for the binary bitarray file.
            meta_path: Path for the JSON metadata file.
        """
        Path(bits_path).parent.mkdir(parents=True, exist_ok=True)
        Path(meta_path).parent.mkdir(parents=True, exist_ok=True)

        with open(bits_path, "wb") as f:
            self._bits.tofile(f)

        with open(meta_path, "w") as f:
            json.dump({
                "n_items": self.n_items,
                "fpr": self.fpr,
                "seed": self.seed,
                "m": self.m,
                "k": self.k,
                "count": self.count,
            }, f)

    @classmethod
    def load(cls, bits_path: str, meta_path: str) -> "BloomFilter":
        """
        Load a previously saved Bloom filter from disk.

        Raises:
            FileNotFoundError: If either file is missing.
        """
        for p in (bits_path, meta_path):
            if not Path(p).exists():
                raise FileNotFoundError(f"Bloom filter file not found: {p}")

        with open(meta_path) as f:
            meta = json.load(f)

        instance = cls.__new__(cls)
        instance.n_items = meta["n_items"]
        instance.fpr = meta["fpr"]
        instance.seed = meta["seed"]
        instance.m = meta["m"]
        instance.k = meta["k"]
        instance.count = meta["count"]
        instance._bits = bitarray()
        with open(bits_path, "rb") as f:
            instance._bits.fromfile(f)
        # fromfile pads to byte boundary; truncate to exact m bits
        del instance._bits[instance.m:]

        return instance

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def fill_ratio(self) -> float:
        """Fraction of bits set to 1."""
        if self.m == 0:
            return 0.0
        return self._bits.count(1) / self.m

    @property
    def memory_bytes(self) -> int:
        """Approximate memory used by the bitarray in bytes."""
        return math.ceil(self.m / 8)

    def __repr__(self) -> str:
        return (
            f"BloomFilter("
            f"n_items={self.n_items}, "
            f"fpr={self.fpr}, "
            f"m={self.m}, "
            f"k={self.k}, "
            f"count={self.count}, "
            f"fill_ratio={self.fill_ratio:.4f}, "
            f"memory={self.memory_bytes / 1024:.1f} KB)"
        )
