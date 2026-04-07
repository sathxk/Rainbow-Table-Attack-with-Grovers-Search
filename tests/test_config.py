"""
Unit tests for configuration management module.
"""

import json
import pytest
import tempfile
import yaml
from pathlib import Path
from rainbow_table_generator.config import Config, load_config


class TestConfig:
    """Tests for Config class."""
    
    def test_config_default_initialization(self):
        """Test Config initialization with default values."""
        config = Config()
        
        assert config.hash_algorithm == "md5"
        assert config.chain_length == 1000
        assert config.qubit_count == 4
        assert config.bucket_size_threshold == 10000
        assert config.max_qubits == 20
        assert config.simulation_shots == 1024
        assert config.input_wordset_path == ""
        assert config.output_directory == "rainbow_tables/output"
        assert config.checkpoint_interval == 100000
        assert config.flush_interval == 1000
        assert config.log_level == "INFO"
        assert config.max_retries == 3
    
    def test_config_custom_initialization(self):
        """Test Config initialization with custom values."""
        config = Config(
            hash_algorithm="sha256",
            chain_length=500,
            qubit_count=8,
            bucket_size_threshold=5000,
            max_qubits=25,
            simulation_shots=2048,
            input_wordset_path="test_wordset.txt",
            output_directory="test_output",
            checkpoint_interval=50000,
            flush_interval=500,
            log_level="DEBUG",
            max_retries=5
        )
        
        assert config.hash_algorithm == "sha256"
        assert config.chain_length == 500
        assert config.qubit_count == 8
        assert config.bucket_size_threshold == 5000
        assert config.max_qubits == 25
        assert config.simulation_shots == 2048
        assert config.input_wordset_path == "test_wordset.txt"
        assert config.output_directory == "test_output"
        assert config.checkpoint_interval == 50000
        assert config.flush_interval == 500
        assert config.log_level == "DEBUG"
        assert config.max_retries == 5
    
    def test_config_repr(self):
        """Test Config string representation."""
        config = Config(hash_algorithm="sha1", chain_length=100)
        repr_str = repr(config)
        
        assert "Config(" in repr_str
        assert "hash_algorithm='sha1'" in repr_str
        assert "chain_length=100" in repr_str
    
    def test_config_to_dict(self):
        """Test Config conversion to dictionary."""
        config = Config(
            hash_algorithm="md5",
            chain_length=1000,
            input_wordset_path="wordset.txt"
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["hash_algorithm"] == "md5"
        assert config_dict["chain_length"] == 1000
        assert config_dict["input_wordset_path"] == "wordset.txt"
        assert "qubit_count" in config_dict
        assert "max_qubits" in config_dict


class TestLoadConfig:
    """Tests for load_config function."""
    
    def test_load_config_json_file(self):
        """Test loading configuration from a JSON file."""
        # Create a temporary JSON config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "hash_algorithm": "sha256",
                "chain_length": 500,
                "qubit_count": 8,
                "input_wordset_path": "test_wordset.txt",
                "output_directory": "test_output"
            }
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            
            assert config.hash_algorithm == "sha256"
            assert config.chain_length == 500
            assert config.qubit_count == 8
            assert config.input_wordset_path == "test_wordset.txt"
            assert config.output_directory == "test_output"
            # Check that defaults are used for missing keys
            assert config.bucket_size_threshold == 10000
            assert config.max_qubits == 20
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_yaml_file(self):
        """Test loading configuration from a YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                "hash_algorithm": "sha1",
                "chain_length": 2000,
                "qubit_count": 6,
                "log_level": "DEBUG"
            }
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            
            assert config.hash_algorithm == "sha1"
            assert config.chain_length == 2000
            assert config.qubit_count == 6
            assert config.log_level == "DEBUG"
            # Check that defaults are used for missing keys
            assert config.input_wordset_path == ""
            assert config.simulation_shots == 1024
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_yml_extension(self):
        """Test loading configuration from a .yml file."""
        # Create a temporary .yml config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            config_data = {
                "hash_algorithm": "md5",
                "chain_length": 1500
            }
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            
            assert config.hash_algorithm == "md5"
            assert config.chain_length == 1500
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_all_parameters(self):
        """Test loading configuration with all parameters specified."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_data = {
                "hash_algorithm": "sha256",
                "chain_length": 750,
                "qubit_count": 5,
                "bucket_size_threshold": 8000,
                "max_qubits": 25,
                "simulation_shots": 2048,
                "input_wordset_path": "wordset.txt",
                "output_directory": "output",
                "checkpoint_interval": 50000,
                "flush_interval": 500,
                "log_level": "WARNING",
                "max_retries": 5
            }
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            
            assert config.hash_algorithm == "sha256"
            assert config.chain_length == 750
            assert config.qubit_count == 5
            assert config.bucket_size_threshold == 8000
            assert config.max_qubits == 25
            assert config.simulation_shots == 2048
            assert config.input_wordset_path == "wordset.txt"
            assert config.output_directory == "output"
            assert config.checkpoint_interval == 50000
            assert config.flush_interval == 500
            assert config.log_level == "WARNING"
            assert config.max_retries == 5
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_empty_file_uses_defaults(self):
        """Test loading configuration from empty JSON file uses defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            
            # All values should be defaults
            assert config.hash_algorithm == "md5"
            assert config.chain_length == 1000
            assert config.qubit_count == 4
            assert config.bucket_size_threshold == 10000
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            load_config("nonexistent_config.json")
        
        assert "Configuration file not found" in str(exc_info.value)
        assert "nonexistent_config.json" in str(exc_info.value)
    
    def test_load_config_unsupported_format(self):
        """Test that ValueError is raised for unsupported file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("some config")
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                load_config(temp_path)
            
            assert "Unsupported configuration file format" in str(exc_info.value)
            assert ".txt" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_invalid_json(self):
        """Test that JSONDecodeError is raised for malformed JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_invalid_yaml(self):
        """Test that YAMLError is raised for malformed YAML."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                load_config(temp_path)
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_non_dict_content(self):
        """Test that ValueError is raised when file contains non-dict content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(["list", "instead", "of", "dict"], f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                load_config(temp_path)
            
            assert "must contain a dictionary" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_case_insensitive_extension(self):
        """Test that file extensions are case-insensitive."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.JSON', delete=False) as f:
            config_data = {"hash_algorithm": "md5"}
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_config(temp_path)
            assert config.hash_algorithm == "md5"
        finally:
            Path(temp_path).unlink()


class TestValidateConfig:
    """Tests for validate_config function."""
    
    def test_validate_config_valid_configuration(self, tmp_path):
        """Test that valid configuration passes validation."""
        from rainbow_table_generator.config import validate_config
        
        # Create a test wordset file
        wordset_file = tmp_path / "wordset.txt"
        wordset_file.write_text("password1\npassword2\n")
        
        # Create output directory
        output_dir = tmp_path / "output"
        
        config = Config(
            hash_algorithm="md5",
            chain_length=1000,
            qubit_count=4,
            input_wordset_path=str(wordset_file),
            output_directory=str(output_dir)
        )
        
        # Should not raise any exception
        validate_config(config)
        
        # Verify output directory was created
        assert output_dir.exists()
        assert output_dir.is_dir()
    
    def test_validate_config_invalid_hash_algorithm(self):
        """Test that invalid hash algorithm raises ValueError."""
        from rainbow_table_generator.config import validate_config
        
        config = Config(hash_algorithm="invalid_hash")
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        
        assert "Invalid hash_algorithm" in str(exc_info.value)
        assert "invalid_hash" in str(exc_info.value)
        assert "md5, sha1, sha256" in str(exc_info.value)
    
    def test_validate_config_valid_hash_algorithms(self, tmp_path):
        """Test that all valid hash algorithms pass validation."""
        from rainbow_table_generator.config import validate_config
        
        output_dir = tmp_path / "output"
        
        for hash_algo in ["md5", "sha1", "sha256"]:
            config = Config(
                hash_algorithm=hash_algo,
                output_directory=str(output_dir)
            )
            # Should not raise any exception
            validate_config(config)
    
    def test_validate_config_chain_length_too_small(self):
        """Test that chain_length < 1 raises ValueError."""
        from rainbow_table_generator.config import validate_config
        
        config = Config(chain_length=0)
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        
        assert "Invalid chain_length" in str(exc_info.value)
        assert "between 1 and 10,000" in str(exc_info.value)
    
    def test_validate_config_chain_length_too_large(self):
        """Test that chain_length > 10,000 raises ValueError."""
        from rainbow_table_generator.config import validate_config
        
        config = Config(chain_length=10001)
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        
        assert "Invalid chain_length" in str(exc_info.value)
        assert "between 1 and 10,000" in str(exc_info.value)
    
    def test_validate_config_chain_length_boundary_values(self, tmp_path):
        """Test that chain_length boundary values (1 and 10,000) are valid."""
        from rainbow_table_generator.config import validate_config
        
        output_dir = tmp_path / "output"
        
        # Test minimum boundary
        config = Config(chain_length=1, output_directory=str(output_dir))
        validate_config(config)
        
        # Test maximum boundary
        config = Config(chain_length=10000, output_directory=str(output_dir))
        validate_config(config)
    
    def test_validate_config_chain_length_not_integer(self):
        """Test that non-integer chain_length raises ValueError."""
        from rainbow_table_generator.config import validate_config
        
        config = Config()
        config.chain_length = 100.5
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        
        assert "chain_length must be an integer" in str(exc_info.value)
    
    def test_validate_config_qubit_count_zero(self):
        """Test that qubit_count = 0 raises ValueError."""
        from rainbow_table_generator.config import validate_config
        
        config = Config(qubit_count=0)
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        
        assert "Invalid qubit_count" in str(exc_info.value)
        assert "positive integer" in str(exc_info.value)
    
    def test_validate_config_qubit_count_negative(self):
        """Test that negative qubit_count raises ValueError."""
        from rainbow_table_generator.config import validate_config
        
        config = Config(qubit_count=-5)
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        
        assert "Invalid qubit_count" in str(exc_info.value)
        assert "positive integer" in str(exc_info.value)
    
    def test_validate_config_qubit_count_not_integer(self):
        """Test that non-integer qubit_count raises ValueError."""
        from rainbow_table_generator.config import validate_config
        
        config = Config()
        config.qubit_count = 4.5
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        
        assert "qubit_count must be an integer" in str(exc_info.value)
    
    def test_validate_config_input_wordset_path_not_exists(self):
        """Test that non-existent input_wordset_path raises FileNotFoundError."""
        from rainbow_table_generator.config import validate_config
        
        config = Config(input_wordset_path="/nonexistent/path/wordset.txt")
        
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_config(config)
        
        assert "Input wordset file not found" in str(exc_info.value)
        assert "/nonexistent/path/wordset.txt" in str(exc_info.value)
    
    def test_validate_config_input_wordset_path_empty(self, tmp_path):
        """Test that empty input_wordset_path is allowed."""
        from rainbow_table_generator.config import validate_config
        
        output_dir = tmp_path / "output"
        config = Config(input_wordset_path="", output_directory=str(output_dir))
        
        # Should not raise any exception
        validate_config(config)
    
    def test_validate_config_input_wordset_path_exists(self, tmp_path):
        """Test that existing input_wordset_path passes validation."""
        from rainbow_table_generator.config import validate_config
        
        wordset_file = tmp_path / "wordset.txt"
        wordset_file.write_text("password1\npassword2\n")
        output_dir = tmp_path / "output"
        
        config = Config(
            input_wordset_path=str(wordset_file),
            output_directory=str(output_dir)
        )
        
        # Should not raise any exception
        validate_config(config)
    
    def test_validate_config_output_directory_created(self, tmp_path):
        """Test that output_directory is created if it doesn't exist."""
        from rainbow_table_generator.config import validate_config
        
        output_dir = tmp_path / "new_output_dir"
        assert not output_dir.exists()
        
        config = Config(output_directory=str(output_dir))
        validate_config(config)
        
        # Directory should now exist
        assert output_dir.exists()
        assert output_dir.is_dir()
    
    def test_validate_config_output_directory_writable(self, tmp_path):
        """Test that writable output_directory passes validation."""
        from rainbow_table_generator.config import validate_config
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        config = Config(output_directory=str(output_dir))
        
        # Should not raise any exception
        validate_config(config)
    
    def test_validate_config_output_directory_not_writable(self, tmp_path):
        """Test that non-writable output_directory raises PermissionError."""
        from rainbow_table_generator.config import validate_config
        import os
        import sys
        
        # Skip this test on Windows as permission handling is different
        if sys.platform == "win32":
            pytest.skip("Permission test not reliable on Windows")
        
        output_dir = tmp_path / "readonly_output"
        output_dir.mkdir()
        
        # Make directory read-only
        os.chmod(output_dir, 0o444)
        
        config = Config(output_directory=str(output_dir))
        
        try:
            with pytest.raises(PermissionError) as exc_info:
                validate_config(config)
            
            assert "not writable" in str(exc_info.value).lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(output_dir, 0o755)
    
    def test_validate_config_output_directory_is_file(self, tmp_path):
        """Test that output_directory being a file raises ValueError."""
        from rainbow_table_generator.config import validate_config
        
        output_file = tmp_path / "output_file.txt"
        output_file.write_text("not a directory")
        
        config = Config(output_directory=str(output_file))
        
        with pytest.raises(ValueError) as exc_info:
            validate_config(config)
        
        assert "not a directory" in str(exc_info.value)
    
    def test_validate_config_all_parameters_valid(self, tmp_path):
        """Test validation with all parameters set to valid values."""
        from rainbow_table_generator.config import validate_config
        
        wordset_file = tmp_path / "wordset.txt"
        wordset_file.write_text("password1\npassword2\n")
        output_dir = tmp_path / "output"
        
        config = Config(
            hash_algorithm="sha256",
            chain_length=5000,
            qubit_count=10,
            bucket_size_threshold=8000,
            max_qubits=25,
            simulation_shots=2048,
            input_wordset_path=str(wordset_file),
            output_directory=str(output_dir),
            checkpoint_interval=50000,
            flush_interval=500,
            log_level="DEBUG",
            max_retries=5
        )
        
        # Should not raise any exception
        validate_config(config)
        
        # Verify output directory was created
        assert output_dir.exists()
        assert output_dir.is_dir()


class TestGetDefaultConfig:
    """Tests for get_default_config function."""
    
    def test_get_default_config_returns_config_with_defaults(self):
        """Test that get_default_config returns a Config object with all default values."""
        from rainbow_table_generator.config import get_default_config
        
        config = get_default_config()
        
        # Verify it returns a Config object
        assert isinstance(config, Config)
        
        # Verify all default values
        assert config.hash_algorithm == "md5"
        assert config.chain_length == 1000
        assert config.qubit_count == 4
        assert config.bucket_size_threshold == 10000
        assert config.max_qubits == 20
        assert config.simulation_shots == 1024
        assert config.input_wordset_path == ""
        assert config.output_directory == "rainbow_tables/output"
        assert config.checkpoint_interval == 100000
        assert config.flush_interval == 1000
        assert config.log_level == "INFO"
        assert config.max_retries == 3
    
    def test_get_default_config_equivalent_to_config_no_args(self):
        """Test that get_default_config() is equivalent to Config()."""
        from rainbow_table_generator.config import get_default_config
        
        default_config = get_default_config()
        direct_config = Config()
        
        # Compare all attributes
        assert default_config.hash_algorithm == direct_config.hash_algorithm
        assert default_config.chain_length == direct_config.chain_length
        assert default_config.qubit_count == direct_config.qubit_count
        assert default_config.bucket_size_threshold == direct_config.bucket_size_threshold
        assert default_config.max_qubits == direct_config.max_qubits
        assert default_config.simulation_shots == direct_config.simulation_shots
        assert default_config.input_wordset_path == direct_config.input_wordset_path
        assert default_config.output_directory == direct_config.output_directory
        assert default_config.checkpoint_interval == direct_config.checkpoint_interval
        assert default_config.flush_interval == direct_config.flush_interval
        assert default_config.log_level == direct_config.log_level
        assert default_config.max_retries == direct_config.max_retries
