"""
Configuration management module for rainbow table generator.

This module provides the Config class to hold configuration parameters
and functions to load, validate, and manage configuration.
"""

import json
import yaml
from pathlib import Path
from typing import Optional


class Config:
    """
    Configuration class to hold all parameters for the rainbow table generator system.
    
    Attributes:
        hash_algorithm: Hash function to use (md5, sha1, sha256, ntlm)
        chain_length: Number of hash-reduce iterations per chain
        qubit_count: Number of qubits for bucket organization (2^N buckets)
        bucket_size_threshold: Maximum entries per bucket before splitting
        max_qubits: Maximum number of qubits allowed (1-30)
        simulation_shots: Number of shots for quantum circuit simulation
        input_wordset_path: Path to input wordset file
        output_directory: Directory for output files
        checkpoint_interval: Number of chains between checkpoints
        flush_interval: Number of chains between bucket flushes
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        max_retries: Maximum retry attempts for I/O operations
    """
    
    def __init__(
        self,
        hash_algorithm: str = "md5",
        chain_length: int = 1000,
        qubit_count: int = 10,
        bucket_size_threshold: int = 10000,
        max_qubits: int = 20,
        simulation_shots: int = 1024,
        input_wordset_path: str = "",
        output_directory: str = "rainbow_tables/output",
        checkpoint_interval: int = 100000,
        flush_interval: int = 1000,
        log_level: str = "INFO",
        max_retries: int = 3,
        fill_factor: float = 0.75,
    ):
        """
        Initialize Config with provided or default values.
        
        Args:
            hash_algorithm: Hash function name
            chain_length: Number of iterations per chain
            qubit_count: Number of qubits for bucketing
            bucket_size_threshold: Max entries per bucket
            max_qubits: Maximum qubits allowed
            simulation_shots: Quantum simulation shots
            input_wordset_path: Input file path
            output_directory: Output directory path
            checkpoint_interval: Chains between checkpoints
            flush_interval: Chains between flushes
            log_level: Logging level
            max_retries: Max I/O retry attempts
        """
        self.hash_algorithm = hash_algorithm
        self.chain_length = chain_length
        self.qubit_count = qubit_count
        self.bucket_size_threshold = bucket_size_threshold
        self.max_qubits = max_qubits
        self.simulation_shots = simulation_shots
        self.input_wordset_path = input_wordset_path
        self.output_directory = output_directory
        self.checkpoint_interval = checkpoint_interval
        self.flush_interval = flush_interval
        self.log_level = log_level
        self.max_retries = max_retries
        self.fill_factor = fill_factor  # bucket over-provisioning (0 < fill_factor <= 1)

        # Derived: num_buckets computed from fill_factor
        # formula: num_buckets = ceil(total / (bucket_size * fill_factor))
        # Stored in BucketOrganizer at runtime; exposed here for reference
        self.password_length = 8  # fixed for this project
    
    def __repr__(self) -> str:
        """Return string representation of Config."""
        return (
            f"Config(hash_algorithm={self.hash_algorithm!r}, "
            f"chain_length={self.chain_length}, "
            f"qubit_count={self.qubit_count}, "
            f"fill_factor={self.fill_factor}, "
            f"bucket_size_threshold={self.bucket_size_threshold}, "
            f"max_qubits={self.max_qubits}, "
            f"simulation_shots={self.simulation_shots}, "
            f"input_wordset_path={self.input_wordset_path!r}, "
            f"output_directory={self.output_directory!r}, "
            f"checkpoint_interval={self.checkpoint_interval}, "
            f"flush_interval={self.flush_interval}, "
            f"log_level={self.log_level!r}, "
            f"max_retries={self.max_retries})"
        )
    
    def to_dict(self) -> dict:
        """
        Convert Config to dictionary.
        
        Returns:
            Dictionary containing all configuration parameters
        """
        return {
            "hash_algorithm": self.hash_algorithm,
            "chain_length": self.chain_length,
            "qubit_count": self.qubit_count,
            "bucket_size_threshold": self.bucket_size_threshold,
            "max_qubits": self.max_qubits,
            "simulation_shots": self.simulation_shots,
            "input_wordset_path": self.input_wordset_path,
            "output_directory": self.output_directory,
            "checkpoint_interval": self.checkpoint_interval,
            "flush_interval": self.flush_interval,
            "log_level": self.log_level,
            "max_retries": self.max_retries,
            "fill_factor": self.fill_factor,
        }


def load_config(config_path: str) -> Config:
    """
    Load configuration from a JSON or YAML file.
    
    This function reads a configuration file (JSON or YAML format) and returns
    a Config object with the parameters specified in the file. The file format
    is determined by the file extension (.json, .yaml, or .yml).
    
    Args:
        config_path: Path to the configuration file (JSON or YAML)
        
    Returns:
        Config object populated with values from the file
        
    Raises:
        FileNotFoundError: If the config file does not exist
        ValueError: If the file format is not supported or file is invalid
        json.JSONDecodeError: If JSON file is malformed
        yaml.YAMLError: If YAML file is malformed
    """
    config_file = Path(config_path)
    
    # Check if file exists
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Determine file format from extension
    file_extension = config_file.suffix.lower()
    
    try:
        with open(config_file, 'r') as f:
            if file_extension == '.json':
                config_data = json.load(f)
            elif file_extension in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            else:
                raise ValueError(
                    f"Unsupported configuration file format: {file_extension}. "
                    "Supported formats: .json, .yaml, .yml"
                )
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"Invalid JSON in configuration file: {e.msg}",
            e.doc,
            e.pos
        )
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in configuration file: {e}")
    
    # Validate that config_data is a dictionary
    if not isinstance(config_data, dict):
        raise ValueError(
            f"Configuration file must contain a dictionary/object, got {type(config_data).__name__}"
        )
    
    # Create Config object with values from file
    # Use .get() with None to allow Config defaults to be used for missing keys
    return Config(
        hash_algorithm=config_data.get('hash_algorithm', 'md5'),
        chain_length=config_data.get('chain_length', 1000),
        qubit_count=config_data.get('qubit_count', 10),
        bucket_size_threshold=config_data.get('bucket_size_threshold', 10000),
        max_qubits=config_data.get('max_qubits', 20),
        simulation_shots=config_data.get('simulation_shots', 1024),
        input_wordset_path=config_data.get('input_wordset_path', ''),
        output_directory=config_data.get('output_directory', 'rainbow_tables/output'),
        checkpoint_interval=config_data.get('checkpoint_interval', 100000),
        flush_interval=config_data.get('flush_interval', 1000),
        log_level=config_data.get('log_level', 'INFO'),
        max_retries=config_data.get('max_retries', 3),
        fill_factor=config_data.get('fill_factor', 0.75),
    )


def validate_config(config: Config) -> None:
    """
    Validate configuration parameters for correctness.

    This function checks all configuration parameters to ensure they meet
    the system requirements. It validates hash algorithms, numeric ranges,
    file paths, and directory permissions.

    Args:
        config: Config object to validate

    Raises:
        ValueError: If any configuration parameter is invalid
        FileNotFoundError: If input_wordset_path does not exist
        PermissionError: If output_directory is not writable
    """
    # Validate hash_algorithm is one of: md5, sha1, sha256
    valid_hash_algorithms = ['md5', 'sha1', 'sha256']
    if config.hash_algorithm not in valid_hash_algorithms:
        raise ValueError(
            f"Invalid hash_algorithm: {config.hash_algorithm!r}. "
            f"Must be one of: {', '.join(valid_hash_algorithms)}"
        )

    # Validate chain_length is between 1 and 10,000
    if not isinstance(config.chain_length, int):
        raise ValueError(
            f"chain_length must be an integer, got {type(config.chain_length).__name__}"
        )
    if config.chain_length < 1 or config.chain_length > 10000:
        raise ValueError(
            f"Invalid chain_length: {config.chain_length}. "
            f"Must be between 1 and 10,000"
        )

    # Validate qubit_count is positive integer
    if not isinstance(config.qubit_count, int):
        raise ValueError(
            f"qubit_count must be an integer, got {type(config.qubit_count).__name__}"
        )
    if config.qubit_count < 1:
        raise ValueError(
            f"Invalid qubit_count: {config.qubit_count}. "
            f"Must be a positive integer"
        )

    # Validate input_wordset_path exists
    if config.input_wordset_path:
        input_path = Path(config.input_wordset_path)
        if not input_path.exists():
            raise FileNotFoundError(
                f"Input wordset file not found: {config.input_wordset_path}"
            )

    # Validate output_directory is writable
    output_dir = Path(config.output_directory)

    # Check if path exists and is not a directory
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(
            f"output_directory is not a directory: {config.output_directory}"
        )

    # Create directory if it doesn't exist
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        raise PermissionError(
            f"Cannot create output directory: {config.output_directory}. {e}"
        )

    # Test write permission by creating a temporary file
    test_file = output_dir / '.write_test'
    try:
        test_file.touch()
        test_file.unlink()
    except (OSError, PermissionError) as e:
        raise PermissionError(
            f"Output directory is not writable: {config.output_directory}. {e}"
        )
def get_default_config() -> Config:
    """
    Get a Config object with all default parameters.

    This function returns a Config object initialized with default values
    for all parameters. Useful for testing or when no config file is provided.

    Returns:
        Config object with default values
    """
    return Config()





