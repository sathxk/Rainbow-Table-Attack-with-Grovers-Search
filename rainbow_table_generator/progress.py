"""
Progress logger module for rainbow table generation.

This module provides the ProgressLogger class that tracks and logs progress
during rainbow table generation. It calculates processing rates, estimates
time remaining, and writes logs to both console and file.
"""

import logging
import time
from typing import Optional, Dict
from pathlib import Path


class ProgressLogger:
    """
    Logger for tracking and reporting rainbow table generation progress.
    
    The ProgressLogger tracks the progress of chain generation, calculates
    processing rates and estimated time remaining, and writes logs to both
    console and a log file. It provides periodic progress updates and final
    summary statistics.
    
    Progress is logged at configurable intervals (default: every 10,000 chains)
    and includes:
    - Chains completed
    - Percentage complete
    - Current processing rate (chains/second)
    - Estimated time remaining
    
    Attributes:
        total_chains: Total number of chains to generate
        log_interval: Number of chains between progress logs
        start_time: Timestamp when generation started
        last_log_time: Timestamp of last progress log
        chains_at_last_log: Number of chains at last progress log
        logger: Python logging.Logger instance
    """
    
    def __init__(
        self,
        total_chains: int,
        log_interval: int = 10000,
        log_file: Optional[str] = None,
        log_level: str = "INFO"
    ):
        """
        Initialize the ProgressLogger with total chains and logging settings.

        Args:
            total_chains: Total number of chains to generate
            log_interval: Number of chains between progress logs (default: 10,000)
            log_file: Path to log file (optional, logs to console only if None)
            log_level: Logging level (INFO, WARNING, ERROR)

        Raises:
            ValueError: If total_chains or log_interval is not positive
        """
        if total_chains < 1:
            raise ValueError(
                f"total_chains must be positive, got {total_chains}"
            )

        if log_interval < 1:
            raise ValueError(
                f"log_interval must be positive, got {log_interval}"
            )

        self.total_chains = total_chains
        self.log_interval = log_interval
        self.start_time: Optional[float] = None
        self.last_log_time: Optional[float] = None
        self.chains_at_last_log: int = 0

        # Setup logging
        self.setup_logging(log_file, log_level)

    def setup_logging(
        self,
        log_file: Optional[str] = None,
        log_level: str = "INFO"
    ) -> None:
        """
        Configure console and file logging with consistent formatting.

        This method sets up the Python logging system with:
        - Console handler (stdout) for real-time monitoring
        - File handler (optional) for persistent log storage
        - Consistent timestamp format: [YYYY-MM-DD HH:MM:SS]
        - Support for INFO, WARNING, and ERROR log levels

        The log file is created in the specified path, with parent directories
        created automatically if they don't exist. Both handlers use the same
        format for consistency.

        Args:
            log_file: Path to log file (optional, logs to console only if None)
            log_level: Logging level (INFO, WARNING, ERROR)

        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.setup_logging(
            ...     log_file="rainbow_tables/len8/logs/generation.log",
            ...     log_level="INFO"
            ... )
        """
        # Initialize logger
        self.logger = logging.getLogger("RainbowTableGenerator")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

        # Clear any existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Create formatter with timestamp format: [YYYY-MM-DD HH:MM:SS]
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Create and configure console handler (stdout)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Create and configure file handler if log_file is specified
        if log_file:
            # Create parent directories if they don't exist
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Create file handler with append mode and UTF-8 encoding
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    
    def __repr__(self) -> str:
        """Return string representation of ProgressLogger."""
        return (
            f"ProgressLogger("
            f"total_chains={self.total_chains}, "
            f"log_interval={self.log_interval})"
        )
    
    def start(self) -> None:
        """
        Mark the start of generation and initialize timing.
        
        This method should be called when chain generation begins. It records
        the start time for calculating elapsed time and processing rates.
        
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.start()
            >>> # ... generate chains ...
        """
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.chains_at_last_log = 0
    
    def log_start(
        self,
        hash_algorithm: str,
        chain_length: int,
        qubit_count: int,
        input_file: str,
        output_directory: str
    ) -> None:
        """
        Log the start of rainbow table generation with configuration details.
        
        Args:
            hash_algorithm: Hash algorithm being used (md5, sha1, sha256)
            chain_length: Number of hash-reduction iterations per chain
            qubit_count: Number of qubits for quantum search
            input_file: Path to input wordset file
            output_directory: Path to output directory
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.log_start(
            ...     hash_algorithm="md5",
            ...     chain_length=1000,
            ...     qubit_count=4,
            ...     input_file="wordset.txt",
            ...     output_directory="output/"
            ... )
        """
        self.logger.info("Starting rainbow table generation")
        self.logger.info(
            f"Configuration: hash={hash_algorithm}, "
            f"chain_length={chain_length}, qubits={qubit_count}"
        )
        self.logger.info(
            f"Input: {input_file} ({self.total_chains:,} passwords)"
        )
        self.logger.info(f"Output: {output_directory}")
    
    def should_log(self, chains_processed: int) -> bool:
        """
        Determine if progress should be logged based on chains processed.
        
        Args:
            chains_processed: Number of chains processed so far
            
        Returns:
            True if progress should be logged, False otherwise
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000, log_interval=10000)
            >>> logger.should_log(10000)
            True
            >>> logger.should_log(10001)
            False
        """
        return chains_processed % self.log_interval == 0
    
    def log_progress(self, chains_processed: int) -> None:
        """
        Log current progress with rate and ETA calculations.
        
        This method logs the current progress including:
        - Number of chains completed
        - Percentage complete
        - Current processing rate (chains/second)
        - Estimated time remaining
        
        Args:
            chains_processed: Number of chains processed so far
            
        Raises:
            RuntimeError: If start() has not been called
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.start()
            >>> logger.log_progress(10000)
        """
        if self.start_time is None:
            raise RuntimeError(
                "start() must be called before log_progress()"
            )
        
        current_time = time.time()
        
        # Calculate percentage complete
        percentage = (chains_processed / self.total_chains) * 100
        
        # Calculate current processing rate
        elapsed_since_last = current_time - self.last_log_time
        chains_since_last = chains_processed - self.chains_at_last_log
        
        if elapsed_since_last > 0:
            current_rate = chains_since_last / elapsed_since_last
        else:
            current_rate = 0
        
        # Calculate ETA using helper function
        eta_str = self.calculate_eta(chains_processed, current_rate)
        
        # Log progress
        self.logger.info(
            f"Progress: {chains_processed:,} chains ({percentage:.2f}%) | "
            f"Rate: {current_rate:,.0f} chains/s | ETA: {eta_str}"
        )
        
        # Update tracking variables
        self.last_log_time = current_time
        self.chains_at_last_log = chains_processed
    
    def log_checkpoint(self, chains_processed: int) -> None:
        """
        Log that a checkpoint has been saved.
        
        Args:
            chains_processed: Number of chains processed at checkpoint
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.log_checkpoint(100000)
        """
        self.logger.info(f"Checkpoint saved: {chains_processed:,} chains processed")
    def calculate_eta(
        self,
        chains_processed: int,
        current_rate: float
    ) -> str:
        """
        Calculate estimated time remaining based on processing rate.

        This helper function calculates the estimated time remaining (ETA)
        for completing the rainbow table generation. It uses the current
        processing rate and the number of remaining chains to estimate
        how long the generation will take to complete.

        Args:
            chains_processed: Number of chains processed so far
            current_rate: Current processing rate in chains/second

        Returns:
            Formatted ETA string (e.g., "1h 30m", "45m 20s", "unknown")
            Returns "unknown" if the rate is zero or negative

        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> eta = logger.calculate_eta(chains_processed=25000, current_rate=1000.0)
            >>> # eta would be approximately "1m 15s" (75000 chains / 1000 chains/s = 75s)
        """
        chains_remaining = self.total_chains - chains_processed

        if current_rate > 0:
            eta_seconds = chains_remaining / current_rate
            return self._format_time(eta_seconds)
        else:
            return "unknown"

    
    def log_summary(
        self,
        total_chains: int,
        total_buckets: int,
        generation_time_seconds: float,
        average_rate: float
    ) -> None:
        """
        Log final summary statistics after generation completes.
        
        Args:
            total_chains: Total number of chains generated
            total_buckets: Total number of buckets created
            generation_time_seconds: Total time taken for generation
            average_rate: Average processing rate (chains/second)
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.log_summary(
            ...     total_chains=100000,
            ...     total_buckets=16,
            ...     generation_time_seconds=100.5,
            ...     average_rate=995.0
            ... )
        """
        self.logger.info("Generation complete!")
        self.logger.info(f"Total chains: {total_chains:,}")
        self.logger.info(f"Total buckets: {total_buckets}")
        self.logger.info(
            f"Generation time: {self._format_time(generation_time_seconds)}"
        )
        self.logger.info(f"Average rate: {average_rate:,.0f} chains/s")
    
    def log_error(self, message: str) -> None:
        """
        Log an error message.
        
        Args:
            message: Error message to log
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.log_error("Failed to write bucket file")
        """
        self.logger.error(message)
    
    def log_warning(self, message: str) -> None:
        """
        Log a warning message.
        
        Args:
            message: Warning message to log
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.log_warning("Disk space running low")
        """
        self.logger.warning(message)
    
    def log_info(self, message: str) -> None:
        """
        Log an informational message.
        
        Args:
            message: Info message to log
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger.log_info("Initializing output directory")
        """
        self.logger.info(message)
    
    def _format_time(self, seconds: float) -> str:
        """
        Format time duration in seconds to human-readable string.
        
        Formats time as:
        - "Xs" for durations under 1 minute
        - "Xm Ys" for durations under 1 hour
        - "Xh Ym" for durations under 1 day
        - "Xd Yh Zm" for longer durations
        
        Args:
            seconds: Time duration in seconds
            
        Returns:
            Formatted time string
            
        Example:
            >>> logger = ProgressLogger(total_chains=100000)
            >>> logger._format_time(65)
            '1m 5s'
            >>> logger._format_time(3665)
            '1h 1m'
        """
        if seconds < 60:
            return f"{int(seconds)}s"
        
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        
        if minutes < 60:
            return f"{minutes}m {remaining_seconds}s"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if hours < 24:
            return f"{hours}h {remaining_minutes}m"
        
        days = hours // 24
        remaining_hours = hours % 24
        remaining_minutes = remaining_minutes
        
        return f"{days}d {remaining_hours}h {remaining_minutes}m"
