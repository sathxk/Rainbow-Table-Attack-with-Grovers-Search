"""
Unit tests for storage manager module (SQLite-based).
"""

import pytest
import sqlite3
from pathlib import Path
from rainbow_table_generator.storage import StorageManager


class TestStorageManager:
    """Tests for StorageManager class."""
    
    def test_init_creates_paths(self, tmp_path):
        """Test that initialization sets up correct paths."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir), max_retries=3)
        
        assert manager.output_directory == output_dir
        assert manager.db_path == output_dir / "rainbow_table.db"
        assert manager.checkpoint_dir == output_dir / "checkpoints"
        assert manager.logs_dir == output_dir / "logs"
        assert manager.max_retries == 3
    
    def test_init_validates_max_retries(self, tmp_path):
        """Test that initialization validates max_retries parameter."""
        with pytest.raises(ValueError, match="max_retries must be positive"):
            StorageManager(str(tmp_path), max_retries=0)
        
        with pytest.raises(ValueError, match="max_retries must be positive"):
            StorageManager(str(tmp_path), max_retries=-1)


class TestInitializeOutputDirectory:
    """Tests for initialize_output_directory method."""
    
    def test_creates_directory_structure(self, tmp_path):
        """Test that all required directories and database are created."""
        output_dir = tmp_path / "rainbow_tables"
        manager = StorageManager(str(output_dir))
        
        manager.initialize_output_directory()
        
        assert output_dir.exists()
        assert (output_dir / "rainbow_table.db").exists()
        assert (output_dir / "checkpoints").exists()
        assert (output_dir / "logs").exists()
    
    def test_creates_database_schema(self, tmp_path):
        """Test that SQLite database is created with correct schema."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        # Verify database exists and has correct schema
        conn = sqlite3.connect(str(manager.db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "chains" in tables
        
        # Verify index exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indices = [row[0] for row in cursor.fetchall()]
        assert "idx_bucket_key" in indices
        
        conn.close()


class TestWriteBucket:
    """Tests for write_bucket method."""
    
    def test_writes_entries_to_database(self, tmp_path):
        """Test that entries are written to SQLite database."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        entries = [
            ("password1", "abc123def456", 5),
            ("password2", "789012345678", 10),
            ("password3", "fedcba987654", 15)
        ]
        
        manager.write_bucket(0, entries)
        
        # Query database to verify
        cursor = manager.conn.execute("SELECT * FROM chains WHERE bucket_key = 0")
        rows = cursor.fetchall()
        
        assert len(rows) == 3
        assert rows[0] == (0, 5, "password1", "abc123def456")
        assert rows[1] == (0, 10, "password2", "789012345678")
        assert rows[2] == (0, 15, "password3", "fedcba987654")
    
    def test_handles_2tuple_format(self, tmp_path):
        """Test backward compatibility with 2-tuple format."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        # Use valid MD5-like hex endpoints
        entries = [
            ("password1", "5f4dcc3b5aa765d61d8327deb882cf99"),
            ("password2", "6cb75f652a9b52798eb6cf2201057c73")
        ]
        
        manager.write_bucket(0, entries)
        
        # Verify entries were written
        cursor = manager.conn.execute("SELECT COUNT(*) FROM chains WHERE bucket_key = 0")
        count = cursor.fetchone()[0]
        assert count == 2
    
    def test_appends_to_database(self, tmp_path):
        """Test that multiple writes accumulate in database."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        entries1 = [("password1", "ep1", 1)]
        entries2 = [("password2", "ep2", 2), ("password3", "ep3", 3)]
        
        manager.write_bucket(0, entries1)
        manager.write_bucket(0, entries2)
        
        cursor = manager.conn.execute("SELECT COUNT(*) FROM chains WHERE bucket_key = 0")
        count = cursor.fetchone()[0]
        assert count == 3
    
    def test_handles_multiple_buckets(self, tmp_path):
        """Test that different bucket keys are stored correctly."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        manager.write_bucket(0, [("pwd1", "ep1", 1)])
        manager.write_bucket(5, [("pwd2", "ep2", 2)])
        manager.write_bucket(10, [("pwd3", "ep3", 3)])
        
        cursor = manager.conn.execute("SELECT DISTINCT bucket_key FROM chains ORDER BY bucket_key")
        keys = [row[0] for row in cursor.fetchall()]
        assert keys == [0, 5, 10]


class TestMetadataAndIndex:
    """Tests for metadata and index writing."""
    
    def test_writes_metadata_json(self, tmp_path):
        """Test that metadata.json is written correctly."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        manager.write_metadata(
            hash_algorithm="md5",
            chain_length=1000,
            qubit_count=4,
            bucket_count=16,  # Legacy parameter (kept for compatibility)
            num_buckets=2392841,
            password_length=8,
            charset="abcdefghijklmnopqrstuvwxyz0123456789",
            reduction_function="iteration_dependent_v1",
            generation_timestamp="2026-03-31T10:30:00Z",
            total_chains=38285441,
            generation_time_seconds=12345.67
        )
        
        metadata_file = output_dir / "metadata.json"
        assert metadata_file.exists()
        
        import json
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata["hash_algorithm"] == "md5"
        assert metadata["total_chains"] == 38285441
        assert metadata["num_buckets"] == 2392841
        assert metadata["bucket_size"] == 16  # Calculated from qubit_count
    
    def test_writes_index_json(self, tmp_path):
        """Test that index.json is written correctly."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        bucket_info = [
            {"bucket_key": 0, "entry_count": 100},
            {"bucket_key": 5, "entry_count": 200}
        ]
        
        manager.write_index(bucket_info)
        
        index_file = output_dir / "index.json"
        assert index_file.exists()
        
        import json
        with open(index_file, 'r') as f:
            index_data = json.load(f)
        
        assert len(index_data["buckets"]) == 2
        assert index_data["buckets"][0]["bucket_key"] == 0


class TestCheckpoints:
    """Tests for checkpoint save/load."""
    
    def test_saves_checkpoint(self, tmp_path):
        """Test that checkpoint is saved correctly."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        manager.save_checkpoint(
            chains_processed=100000,
            last_start_point="password123",
            bucket_counts={0: 6250, 1: 6248}
        )
        
        checkpoint_file = output_dir / "checkpoints" / "checkpoint_100000.json"
        assert checkpoint_file.exists()
    
    def test_loads_checkpoint(self, tmp_path):
        """Test that checkpoint is loaded correctly."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        manager.save_checkpoint(
            chains_processed=100000,
            last_start_point="password123",
            bucket_counts={0: 6250, 1: 6248}
        )
        
        checkpoint = manager.load_checkpoint()
        
        assert checkpoint is not None
        assert checkpoint["chains_processed"] == 100000
        assert checkpoint["last_start_point"] == "password123"
        assert checkpoint["bucket_counts"][0] == 6250
    
    def test_loads_most_recent_checkpoint(self, tmp_path):
        """Test that most recent checkpoint is loaded."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        manager.save_checkpoint(100000, "pwd1", {})
        manager.save_checkpoint(200000, "pwd2", {})
        manager.save_checkpoint(150000, "pwd3", {})
        
        checkpoint = manager.load_checkpoint()
        assert checkpoint["chains_processed"] == 200000


class TestDatabaseQueries:
    """Tests for database query methods."""
    
    def test_get_bucket_count(self, tmp_path):
        """Test that bucket count is calculated correctly."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        manager.write_bucket(0, [("pwd1", "ep1", 1)])
        manager.write_bucket(5, [("pwd2", "ep2", 2)])
        manager.write_bucket(5, [("pwd3", "ep3", 3)])
        
        assert manager.get_bucket_count() == 2
    
    def test_get_total_chains(self, tmp_path):
        """Test that total chain count is calculated correctly."""
        output_dir = tmp_path / "output"
        manager = StorageManager(str(output_dir))
        manager.initialize_output_directory()
        
        manager.write_bucket(0, [("pwd1", "ep1", 1)])
        manager.write_bucket(5, [("pwd2", "ep2", 2), ("pwd3", "ep3", 3)])
        
        assert manager.get_total_chains() == 3
