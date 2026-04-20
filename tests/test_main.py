"""
Integration tests for main orchestration module.
"""

import pytest
import tempfile
import json
from pathlib import Path

from rainbow_table_generator.main import RainbowTableGenerator
from rainbow_table_generator.hash_functions import MD5HashFunction
from rainbow_table_generator.bucket_organizer import BucketOrganizer
from rainbow_table_generator.storage import StorageManager


class TestRainbowTableGenerator:
    """Tests for RainbowTableGenerator class."""
    
    def test_init_with_valid_config(self, tmp_path):
        """Test initialization with valid configuration."""
        # Create a temporary config file
        config_data = {
            "hash_algorithm": "md5",
            "chain_length": 100,
            "qubit_count": 3,
            "bucket_size_threshold": 1000,
            "max_qubits": 10,
            "simulation_shots": 512,
            "input_wordset_path": "test_wordset.txt",
            "output_directory": str(tmp_path / "output"),
            "checkpoint_interval": 10000,
            "flush_interval": 500,
            "log_level": "INFO",
            "max_retries": 3
        }
        
        config_path = tmp_path / "test_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Create a dummy wordset file to satisfy validation
        wordset_path = tmp_path / "test_wordset.txt"
        wordset_path.write_text("password\n")
        config_data["input_wordset_path"] = str(wordset_path)
        
        # Update config file with valid wordset path
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Initialize generator
        generator = RainbowTableGenerator(str(config_path))
        
        # Verify configuration is loaded
        assert generator.config is not None
        assert generator.config.hash_algorithm == "md5"
        assert generator.config.chain_length == 100
        assert generator.config.qubit_count == 3
        
        # Verify hash function is initialized
        assert generator.hash_function is not None
        assert isinstance(generator.hash_function, MD5HashFunction)
        
        # Verify bucket organizer is deferred (initialized during generation)
        assert generator.bucket_organizer is None
        
        # Verify storage manager is initialized
        assert generator.storage_manager is not None
        assert isinstance(generator.storage_manager, StorageManager)
        
        # Verify output directory was created
        output_dir = Path(config_data["output_directory"])
        assert output_dir.exists()
        assert (output_dir / "checkpoints").exists()
        assert (output_dir / "logs").exists()
        
        # Verify chain generator and progress logger are None (deferred)
        assert generator.chain_generator is None
        assert generator.progress_logger is None
    
    def test_init_with_invalid_config_path(self):
        """Test initialization with non-existent config file."""
        with pytest.raises(FileNotFoundError):
            RainbowTableGenerator("nonexistent_config.json")
    
    def test_repr(self, tmp_path):
        """Test string representation of RainbowTableGenerator."""
        # Create a temporary config file
        config_data = {
            "hash_algorithm": "sha1",
            "chain_length": 50,
            "qubit_count": 2,
            "input_wordset_path": "test.txt",
            "output_directory": str(tmp_path / "output")
        }
        
        config_path = tmp_path / "test_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Create dummy wordset
        wordset_path = tmp_path / "test.txt"
        wordset_path.write_text("test\n")
        config_data["input_wordset_path"] = str(wordset_path)
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        generator = RainbowTableGenerator(str(config_path))
        repr_str = repr(generator)
        
        assert "RainbowTableGenerator" in repr_str
        assert "config=" in repr_str


class TestGenerate:
    """Tests for generate method."""
    
    def test_generate_basic_workflow(self, tmp_path):
        """Test basic generate workflow with small wordset."""
        # Create a temporary config file
        config_data = {
            "hash_algorithm": "md5",
            "chain_length": 10,
            "qubit_count": 2,  # 4 buckets
            "input_wordset_path": str(tmp_path / "wordset.txt"),
            "output_directory": str(tmp_path / "output"),
            "checkpoint_interval": 5,
            "flush_interval": 3,
            "log_level": "INFO",
            "max_retries": 3
        }
        
        config_path = tmp_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Create a small wordset file with 10 passwords
        wordset_path = tmp_path / "wordset.txt"
        passwords = [f"pass{i:04d}" for i in range(10)]
        wordset_path.write_text('\n'.join(passwords) + '\n')
        
        # Initialize generator
        generator = RainbowTableGenerator(str(config_path))
        
        # Run generation
        generator.generate()
        
        # Verify output directory structure
        output_dir = Path(config_data["output_directory"])
        assert output_dir.exists()
        assert (output_dir / "checkpoints").exists()
        assert (output_dir / "logs").exists()
        
        # Verify SQLite database was created
        assert (output_dir / "rainbow_table.db").exists()
        
        # Verify metadata.json was created
        metadata_path = output_dir / "metadata.json"
        assert metadata_path.exists()
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        assert metadata["hash_algorithm"] == "md5"
        assert metadata["chain_length"] == 10
        assert metadata["qubit_count"] == 2
        assert metadata["num_buckets"] == 4  # ceil(10 / (4 * 0.75)) = 4 buckets
        assert metadata["bucket_size"] == 4  # 2^2 = 4
        assert metadata["password_length"] == 8
        assert metadata["total_chains"] == 10
        
        # Verify index.json was created
        index_path = output_dir / "index.json"
        assert index_path.exists()
        
        with open(index_path, 'r') as f:
            index = json.load(f)
        
        assert "buckets" in index
        # With 10 entries and bucket_size=4, we have 3 buckets
        assert len(index["buckets"]) >= 1
        
        # Verify total entries across all buckets equals total chains
        total_entries = sum(bucket["entry_count"] for bucket in index["buckets"])
        assert total_entries == 10
        
        # Verify SQLite database has entries
        import sqlite3
        conn = sqlite3.connect(str(output_dir / "rainbow_table.db"))
        cursor = conn.execute("SELECT COUNT(*) FROM chains")
        db_count = cursor.fetchone()[0]
        assert db_count == 10
        conn.close()
        
        # Verify checkpoint was created (at chains_processed=5)
        checkpoint_files = list((output_dir / "checkpoints").glob("checkpoint_*.json"))
        assert len(checkpoint_files) > 0
        
        # Verify log file was created
        log_files = list((output_dir / "logs").glob("*.log"))
        assert len(log_files) > 0
    
    def test_generate_with_checkpoint_resume(self, tmp_path):
        """Test generation resumption from checkpoint."""
        # Create a temporary config file
        config_data = {
            "hash_algorithm": "md5",
            "chain_length": 10,
            "qubit_count": 2,
            "input_wordset_path": str(tmp_path / "wordset.txt"),
            "output_directory": str(tmp_path / "output"),
            "checkpoint_interval": 3,
            "flush_interval": 2,
            "log_level": "INFO",
            "max_retries": 3
        }
        
        config_path = tmp_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Create a wordset file with 10 passwords
        wordset_path = tmp_path / "wordset.txt"
        passwords = [f"test{i:04d}" for i in range(10)]
        wordset_path.write_text('\n'.join(passwords) + '\n')
        
        # Initialize generator and create output directory
        generator = RainbowTableGenerator(str(config_path))
        
        # Manually create a checkpoint to simulate partial completion
        checkpoint_data = {
            "chains_processed": 5,
            "last_start_point": "test0004",
            "timestamp": "2026-03-31T10:00:00Z",
            "bucket_counts": {0: 1, 1: 2, 2: 1, 3: 1}
        }
        
        checkpoint_path = generator.storage_manager.checkpoint_dir / "checkpoint_5.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f)
        
        # Run generation (should resume from checkpoint)
        generator.generate()
        
        # Verify metadata shows all 10 chains were processed
        metadata_path = Path(config_data["output_directory"]) / "metadata.json"
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Should have processed all 10 chains (5 from checkpoint + 5 new)
        assert metadata["total_chains"] == 10
    
    def test_generate_empty_wordset(self, tmp_path):
        """Test generation with empty wordset file."""
        # Create a temporary config file
        config_data = {
            "hash_algorithm": "md5",
            "chain_length": 10,
            "qubit_count": 2,
            "input_wordset_path": str(tmp_path / "wordset.txt"),
            "output_directory": str(tmp_path / "output"),
            "checkpoint_interval": 100,
            "flush_interval": 10,
            "log_level": "INFO",
            "max_retries": 3
        }
        
        config_path = tmp_path / "config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)
        
        # Create an empty wordset file
        wordset_path = tmp_path / "wordset.txt"
        wordset_path.write_text('')
        
        # Initialize generator
        generator = RainbowTableGenerator(str(config_path))
        
        # Should raise RuntimeError for empty wordset
        with pytest.raises(RuntimeError, match="empty or contains no valid passwords"):
            generator.generate()


class TestCommandLineInterface:
    """Tests for command-line interface."""
    
    def test_placeholder(self):
        """Placeholder test."""
        pass
