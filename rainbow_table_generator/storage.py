"""
Storage manager module for rainbow table generation.

This module provides the StorageManager class that handles all file I/O
operations using SQLite for efficient storage and retrieval of rainbow table
chains. It manages writing SP-EP pairs to a database, creating metadata files,
and checkpoint files for recovery.
"""

import json
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, UTC


class StorageManager:
    """
    Manager for all storage operations in rainbow table generation.
    
    Uses SQLite to store SP-EP pairs with bucket organization. The database
    schema includes:
    - chains table: (bucket_key, intra_value, start_point, end_point)
    - Index on bucket_key for fast lookups
    
    Directory structure:
    - output_directory/
      - rainbow_table.db (SQLite database)
      - checkpoints/
      - logs/
      - metadata.json
    
    Attributes:
        output_directory: Root directory for all output files
        max_retries: Maximum number of retry attempts for I/O operations
        db_path: Path to the SQLite database file
        checkpoint_dir: Path to the checkpoints subdirectory
        logs_dir: Path to the logs subdirectory
        conn: SQLite connection (None until initialized)
    """
    
    def __init__(self, output_directory: str, max_retries: int = 3):
        """
        Initialize the StorageManager with output directory and retry settings.
        
        Args:
            output_directory: Root directory for all output files
            max_retries: Maximum number of retry attempts for I/O operations
            
        Raises:
            ValueError: If max_retries is not positive
        """
        if max_retries < 1:
            raise ValueError(f"max_retries must be positive, got {max_retries}")
        
        self.output_directory = Path(output_directory)
        self.max_retries = max_retries
        
        # Define file paths
        self.db_path = self.output_directory / "rainbow_table.db"
        self.checkpoint_dir = self.output_directory / "checkpoints"
        self.logs_dir = self.output_directory / "logs"
        
        # SQLite connection (initialized in initialize_output_directory)
        self.conn: Optional[sqlite3.Connection] = None
    
    def __repr__(self) -> str:
        return (
            f"StorageManager("
            f"output_directory={str(self.output_directory)!r}, "
            f"max_retries={self.max_retries})"
        )
    
    def initialize_output_directory(self, min_free_space_gb: float = 1.0) -> None:
        """
        Initialize the output directory structure and SQLite database.

        Creates:
        - output_directory/
        - checkpoints/
        - logs/
        - rainbow_table.db with schema

        Args:
            min_free_space_gb: Minimum required free disk space in GB

        Raises:
            OSError: If directories cannot be created
            RuntimeError: If insufficient disk space
        """
        # Create main output directory
        try:
            self.output_directory.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create output directory {self.output_directory}: {e}") from e

        # Create subdirectories
        for subdir in [self.checkpoint_dir, self.logs_dir]:
            try:
                subdir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise OSError(f"Failed to create subdirectory {subdir}: {e}") from e

        # Check disk space
        try:
            stat = shutil.disk_usage(self.output_directory)
            free_space_gb = stat.free / (1024 ** 3)
            if free_space_gb < min_free_space_gb:
                raise RuntimeError(
                    f"Insufficient disk space: {free_space_gb:.2f} GB available, "
                    f"{min_free_space_gb:.2f} GB required"
                )
        except OSError as e:
            raise RuntimeError(f"Failed to check disk space: {e}") from e

        # Initialize SQLite database
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chains (
                bucket_key   INTEGER NOT NULL,
                intra_value  INTEGER NOT NULL,
                start_point  TEXT    NOT NULL,
                end_point    TEXT    NOT NULL
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bucket_key ON chains (bucket_key)")
        self.conn.commit()
    
    def write_bucket(self, bucket_key: int, entries: List[Tuple], mode: str = 'a', commit: bool = False) -> None:
        """
        Write entries to the SQLite database.

        Args:
            bucket_key: Bucket key (for compatibility, but all entries go into one table)
            entries: List of (start_point, end_point, intra_value) tuples
                     OR (start_point, end_point) tuples (intra_value computed automatically)
            mode: Ignored (kept for API compatibility)
            commit: Whether to commit immediately (default False for batching)

        Raises:
            IOError: If writing fails after retries
        """
        if not self.conn:
            raise RuntimeError("Database not initialized. Call initialize_output_directory() first.")

        if not entries:
            return

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                # Prepare rows: handle both 2-tuple and 3-tuple formats
                rows = []
                for entry in entries:
                    if len(entry) == 3:
                        sp, ep, intra = entry
                    elif len(entry) == 2:
                        sp, ep = entry
                        # Compute intra_value from endpoint using first 8 hex chars
                        hash_value = int(ep[:8], 16)
                        intra = hash_value % (2 ** 4)  # Assume 4 qubits for backward compatibility
                    else:
                        raise ValueError(f"Entry must be 2-tuple or 3-tuple, got {len(entry)}-tuple")
                    
                    rows.append((bucket_key, intra, sp, ep))
                
                self.conn.executemany(
                    "INSERT INTO chains (bucket_key, intra_value, start_point, end_point) VALUES (?, ?, ?, ?)",
                    rows
                )
                
                # Only commit if requested (for batching performance)
                if commit:
                    self.conn.commit()
                
                return

            except sqlite3.Error as e:
                last_error = e
                if attempt >= self.max_retries:
                    raise IOError(f"Failed to write bucket {bucket_key} after {self.max_retries} attempts: {e}") from e
    
    def commit(self) -> None:
        """Commit pending database transactions."""
        if self.conn:
            self.conn.commit()
    
    def write_metadata(
        self,
        hash_algorithm: str,
        chain_length: int,
        qubit_count: int,
        bucket_count: int,
        num_buckets: int,
        password_length: int,
        charset: str,
        reduction_function: str,
        generation_timestamp: str,
        total_chains: int,
        generation_time_seconds: float
    ) -> None:
        """Write metadata.json file."""
        metadata = {
            "hash_algorithm": hash_algorithm,
            "chain_length": chain_length,
            "qubit_count": qubit_count,
            "bucket_size": 2 ** qubit_count,
            "bucket_count": bucket_count,
            "num_buckets": num_buckets,
            "password_length": password_length,
            "charset": charset,
            "reduction_function": reduction_function,
            "generation_timestamp": generation_timestamp,
            "total_chains": total_chains,
            "generation_time_seconds": generation_time_seconds
        }

        metadata_path = self.output_directory / "metadata.json"
        
        for attempt in range(1, self.max_retries + 1):
            try:
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                    f.write('\n')
                return
            except (OSError, IOError) as e:
                if attempt >= self.max_retries:
                    raise IOError(f"Failed to write metadata.json after {self.max_retries} attempts: {e}") from e
    
    def write_index(self, bucket_info: List[Dict]) -> None:
        """Write index.json file with bucket statistics."""
        index_data = {"buckets": bucket_info}
        index_path = self.output_directory / "index.json"
        
        for attempt in range(1, self.max_retries + 1):
            try:
                with open(index_path, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, indent=2, ensure_ascii=False)
                    f.write('\n')
                return
            except (OSError, IOError) as e:
                if attempt >= self.max_retries:
                    raise IOError(f"Failed to write index.json after {self.max_retries} attempts: {e}") from e
    
    def save_checkpoint(
        self,
        chains_processed: int,
        last_start_point: str,
        bucket_counts: Dict[int, int]
    ) -> None:
        """Save a checkpoint file for recovery."""
        if chains_processed < 0:
            raise ValueError(f"chains_processed must be non-negative, got {chains_processed}")

        checkpoint_data = {
            "chains_processed": chains_processed,
            "last_start_point": last_start_point,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "bucket_counts": bucket_counts
        }

        checkpoint_filename = f"checkpoint_{chains_processed}.json"
        checkpoint_path = self.checkpoint_dir / checkpoint_filename

        for attempt in range(1, self.max_retries + 1):
            try:
                with open(checkpoint_path, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
                    f.write('\n')
                return
            except (OSError, IOError) as e:
                if attempt >= self.max_retries:
                    raise IOError(f"Failed to save checkpoint after {self.max_retries} attempts: {e}") from e
    
    def load_checkpoint(self, chains_processed: Optional[int] = None) -> Optional[Dict]:
        """Load the most recent checkpoint file."""
        if chains_processed is not None and chains_processed < 0:
            raise ValueError(f"chains_processed must be non-negative, got {chains_processed}")

        if chains_processed is not None:
            checkpoint_filename = f"checkpoint_{chains_processed}.json"
            checkpoint_path = self.checkpoint_dir / checkpoint_filename
            if not checkpoint_path.exists():
                return None
            checkpoint_files = [checkpoint_path]
        else:
            if not self.checkpoint_dir.exists():
                return None
            checkpoint_files = sorted(
                self.checkpoint_dir.glob("checkpoint_*.json"),
                key=lambda p: int(p.stem.split("_")[1]),
                reverse=True
            )
            if not checkpoint_files:
                return None

        checkpoint_path = checkpoint_files[0]
        
        try:
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            required_fields = ["chains_processed", "last_start_point", "timestamp", "bucket_counts"]
            for field in required_fields:
                if field not in checkpoint_data:
                    raise IOError(f"Checkpoint corrupted: missing field '{field}'")
            
            # Convert bucket_counts keys from strings to integers
            bucket_counts = {int(k): v for k, v in checkpoint_data["bucket_counts"].items()}
            
            return {
                "chains_processed": checkpoint_data["chains_processed"],
                "last_start_point": checkpoint_data["last_start_point"],
                "timestamp": checkpoint_data["timestamp"],
                "bucket_counts": bucket_counts
            }
            
        except json.JSONDecodeError as e:
            raise IOError(f"Checkpoint corrupted: invalid JSON: {e}") from e
        except (OSError, IOError) as e:
            raise IOError(f"Failed to read checkpoint: {e}") from e
    
    def get_bucket_count(self) -> int:
        """Return the number of distinct bucket_keys in the database."""
        if not self.conn:
            raise RuntimeError("Database not initialized")
        cursor = self.conn.execute("SELECT COUNT(DISTINCT bucket_key) FROM chains")
        return cursor.fetchone()[0]
    
    def get_total_chains(self) -> int:
        """Return the total number of chains in the database."""
        if not self.conn:
            raise RuntimeError("Database not initialized")
        cursor = self.conn.execute("SELECT COUNT(*) FROM chains")
        return cursor.fetchone()[0]
    
    def close(self) -> None:
        """Close the SQLite connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
