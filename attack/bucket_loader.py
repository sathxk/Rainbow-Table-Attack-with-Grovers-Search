"""
Bucket Loader for the Quantum Rainbow Table Attack phase.

Wraps SQLite access for the attack loop.  Keeps a persistent connection
open for the duration of the attack session (context manager pattern) to
avoid per-query open/close overhead across 1000 chain positions.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

ChainEntry = Tuple[str, str]


class BucketLoader:
    """
    Loads chain entries from the rainbow table SQLite DB for a given bucket.

    Use as a context manager to keep the connection open across all chain
    position checks in a single crack() call.

    Example:
        >>> with BucketLoader("rainbow_tables/output/rainbow_table.db", 49851) as loader:
        ...     key = loader.compute_bucket_key("aabbccdd...")
        ...     entries = loader.load_bucket(key)
    """

    def __init__(self, db_path: str, num_buckets: int) -> None:
        if num_buckets < 1:
            raise ValueError(f"num_buckets must be >= 1, got {num_buckets}")
        self.db_path = Path(db_path)
        self.num_buckets = num_buckets
        self._conn: Optional[sqlite3.Connection] = None

    # --- Context manager ---

    def open(self) -> None:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "BucketLoader":
        self.open()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    # --- Core operations ---

    def compute_bucket_key(self, candidate_ep_hex: str) -> int:
        """
        Compute bucket_key for a candidate endpoint.

        Uses the same formula as BucketOrganizer.assign_bucket():
            int(ep[:8], 16) % num_buckets
        """
        if len(candidate_ep_hex) < 8:
            raise ValueError(
                f"candidate_ep_hex must be >= 8 chars, got {len(candidate_ep_hex)}"
            )
        return int(candidate_ep_hex[:8], 16) % self.num_buckets

    def load_bucket(self, bucket_key: int) -> List[ChainEntry]:
        """
        Fetch all (start_point, end_point) rows for bucket_key, ordered by intra_value.

        Raises:
            RuntimeError: If connection not open.
        """
        if self._conn is None:
            raise RuntimeError(
                "BucketLoader not open. Use as context manager: "
                "`with BucketLoader(...) as loader:`"
            )
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT start_point, end_point FROM chains "
            "WHERE bucket_key = ? ORDER BY intra_value",
            (bucket_key,),
        )
        return cursor.fetchall()

    def get_total_chains(self) -> int:
        """Return total number of chains in the database."""
        if self._conn is None:
            raise RuntimeError("BucketLoader not open.")
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chains")
        return cursor.fetchone()[0]

    def __repr__(self) -> str:
        status = "open" if self._conn else "closed"
        return (
            f"BucketLoader(db={self.db_path.name!r}, "
            f"num_buckets={self.num_buckets}, status={status!r})"
        )
