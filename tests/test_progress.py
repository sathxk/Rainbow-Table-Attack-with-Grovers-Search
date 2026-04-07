"""
Unit tests for the progress logger module.

This module tests the ProgressLogger class that tracks and logs progress
during rainbow table generation.
"""

import pytest
import time
import logging
from pathlib import Path
from rainbow_table_generator.progress import ProgressLogger


class TestProgressLoggerInit:
    """Tests for ProgressLogger initialization."""
    
    def test_init_valid_parameters(self):
        """Test initialization with valid parameters."""
        logger = ProgressLogger(
            total_chains=100000,
            log_interval=10000,
            log_level="INFO"
        )
        
        assert logger.total_chains == 100000
        assert logger.log_interval == 10000
        assert logger.start_time is None
        assert logger.last_log_time is None
        assert logger.chains_at_last_log == 0
    
    def test_init_with_log_file(self, tmp_path):
        """Test initialization with log file."""
        log_file = tmp_path / "logs" / "test.log"
        
        logger = ProgressLogger(
            total_chains=100000,
            log_file=str(log_file)
        )
        
        assert logger.total_chains == 100000
        assert log_file.exists()
    
    def test_init_invalid_total_chains(self):
        """Test initialization with invalid total_chains."""
        with pytest.raises(ValueError, match="total_chains must be positive"):
            ProgressLogger(total_chains=0)
        
        with pytest.raises(ValueError, match="total_chains must be positive"):
            ProgressLogger(total_chains=-100)
    
    def test_init_invalid_log_interval(self):
        """Test initialization with invalid log_interval."""
        with pytest.raises(ValueError, match="log_interval must be positive"):
            ProgressLogger(total_chains=100000, log_interval=0)
        
        with pytest.raises(ValueError, match="log_interval must be positive"):
            ProgressLogger(total_chains=100000, log_interval=-1000)
    
    def test_repr(self):
        """Test string representation."""
        logger = ProgressLogger(total_chains=100000, log_interval=5000)
        repr_str = repr(logger)
        
        assert "ProgressLogger" in repr_str
        assert "total_chains=100000" in repr_str
        assert "log_interval=5000" in repr_str


class TestProgressLoggerStart:
    """Tests for starting progress tracking."""
    
    def test_start(self):
        """Test starting progress tracking."""
        logger = ProgressLogger(total_chains=100000)
        
        assert logger.start_time is None
        assert logger.last_log_time is None
        
        logger.start()
        
        assert logger.start_time is not None
        assert logger.last_log_time is not None
        assert logger.start_time == logger.last_log_time
        assert logger.chains_at_last_log == 0
    
    def test_start_multiple_times(self):
        """Test calling start() multiple times."""
        logger = ProgressLogger(total_chains=100000)
        
        logger.start()
        first_start_time = logger.start_time
        
        time.sleep(0.01)  # Small delay
        
        logger.start()
        second_start_time = logger.start_time
        
        # Second start should update the time
        assert second_start_time > first_start_time


class TestProgressLoggerLogging:
    """Tests for logging methods."""
    
    def test_log_start(self, caplog):
        """Test logging start message."""
        logger = ProgressLogger(total_chains=100000)
        
        with caplog.at_level(logging.INFO):
            logger.log_start(
                hash_algorithm="md5",
                chain_length=1000,
                qubit_count=4,
                input_file="wordset.txt",
                output_directory="output/"
            )
        
        assert "Starting rainbow table generation" in caplog.text
        assert "hash=md5" in caplog.text
        assert "chain_length=1000" in caplog.text
        assert "qubits=4" in caplog.text
        assert "wordset.txt" in caplog.text
        assert "100,000 passwords" in caplog.text
        assert "output/" in caplog.text
    
    def test_should_log(self):
        """Test should_log method."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        assert logger.should_log(10000) is True
        assert logger.should_log(20000) is True
        assert logger.should_log(10001) is False
        assert logger.should_log(9999) is False
        assert logger.should_log(0) is True  # 0 % 10000 == 0
    
    def test_log_progress(self, caplog):
        """Test logging progress."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        time.sleep(0.01)  # Small delay to ensure rate calculation
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        assert "Progress:" in caplog.text
        assert "10,000 chains" in caplog.text
        assert "10.00%" in caplog.text
        assert "Rate:" in caplog.text
        assert "chains/s" in caplog.text
        assert "ETA:" in caplog.text
    
    def test_log_progress_without_start(self):
        """Test logging progress without calling start()."""
        logger = ProgressLogger(total_chains=100000)
        
        with pytest.raises(RuntimeError, match="start\\(\\) must be called"):
            logger.log_progress(10000)
    
    def test_log_checkpoint(self, caplog):
        """Test logging checkpoint."""
        logger = ProgressLogger(total_chains=100000)
        
        with caplog.at_level(logging.INFO):
            logger.log_checkpoint(100000)
        
        assert "Checkpoint saved" in caplog.text
        assert "100,000 chains processed" in caplog.text
    
    def test_log_summary(self, caplog):
        """Test logging summary."""
        logger = ProgressLogger(total_chains=100000)
        
        with caplog.at_level(logging.INFO):
            logger.log_summary(
                total_chains=100000,
                total_buckets=16,
                generation_time_seconds=100.5,
                average_rate=995.0
            )
        
        assert "Generation complete!" in caplog.text
        assert "Total chains: 100,000" in caplog.text
        assert "Total buckets: 16" in caplog.text
        assert "Generation time:" in caplog.text
        assert "Average rate: 995 chains/s" in caplog.text
    
    def test_log_error(self, caplog):
        """Test logging error message."""
        logger = ProgressLogger(total_chains=100000)
        
        with caplog.at_level(logging.ERROR):
            logger.log_error("Test error message")
        
        assert "Test error message" in caplog.text
    
    def test_log_warning(self, caplog):
        """Test logging warning message."""
        logger = ProgressLogger(total_chains=100000)
        
        with caplog.at_level(logging.WARNING):
            logger.log_warning("Test warning message")
        
        assert "Test warning message" in caplog.text
    
    def test_log_info(self, caplog):
        """Test logging info message."""
        logger = ProgressLogger(total_chains=100000)
        
        with caplog.at_level(logging.INFO):
            logger.log_info("Test info message")
        
        assert "Test info message" in caplog.text


class TestProgressLoggerTimeFormatting:
    """Tests for time formatting."""
    
    def test_format_time_seconds(self):
        """Test formatting time in seconds."""
        logger = ProgressLogger(total_chains=100000)
        
        assert logger._format_time(0) == "0s"
        assert logger._format_time(30) == "30s"
        assert logger._format_time(59) == "59s"
    
    def test_format_time_minutes(self):
        """Test formatting time in minutes."""
        logger = ProgressLogger(total_chains=100000)
        
        assert logger._format_time(60) == "1m 0s"
        assert logger._format_time(65) == "1m 5s"
        assert logger._format_time(125) == "2m 5s"
        assert logger._format_time(3599) == "59m 59s"
    
    def test_format_time_hours(self):
        """Test formatting time in hours."""
        logger = ProgressLogger(total_chains=100000)
        
        assert logger._format_time(3600) == "1h 0m"
        assert logger._format_time(3665) == "1h 1m"
        assert logger._format_time(7325) == "2h 2m"
        assert logger._format_time(86399) == "23h 59m"
    
    def test_format_time_days(self):
        """Test formatting time in days."""
        logger = ProgressLogger(total_chains=100000)
        
        assert logger._format_time(86400) == "1d 0h 0m"
        assert logger._format_time(90000) == "1d 1h 0m"
        assert logger._format_time(176400) == "2d 1h 0m"


class TestProgressLoggerRateCalculation:
    """Tests for processing rate calculation (subtask 9.3.1)."""
    
    def test_calculate_processing_rate_basic(self, caplog):
        """Test basic processing rate calculation."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        # Simulate processing 10,000 chains in 0.1 seconds
        time.sleep(0.1)
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        # Rate should be approximately 10,000 / 0.1 = 100,000 chains/s
        # (allowing for some variance due to timing)
        assert "Rate:" in caplog.text
        assert "chains/s" in caplog.text
    
    def test_calculate_processing_rate_multiple_intervals(self, caplog):
        """Test processing rate calculation across multiple intervals."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        # First interval
        time.sleep(0.05)
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        first_log = caplog.text
        
        # Second interval
        caplog.clear()
        time.sleep(0.05)
        with caplog.at_level(logging.INFO):
            logger.log_progress(20000)
        
        second_log = caplog.text
        
        # Both logs should contain rate information
        assert "Rate:" in first_log
        assert "Rate:" in second_log
    
    def test_processing_rate_zero_elapsed_time(self, caplog):
        """Test processing rate when elapsed time is zero."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        # Immediately log progress (no time elapsed)
        # Should handle division by zero gracefully
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        # Should not raise an exception and should show rate
        assert "Rate:" in caplog.text
        assert "ETA:" in caplog.text
    
    def test_processing_rate_with_zero_chains_since_last(self, caplog):
        """Test processing rate when no chains processed since last log."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        # Manually set times to create zero elapsed time scenario
        current_time = time.time()
        logger.start_time = current_time
        logger.last_log_time = current_time + 0.1  # Set future time to trigger else branch
        logger.chains_at_last_log = 0
        
        # Log progress - elapsed_since_last will be negative
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        # Should handle zero/negative elapsed time gracefully and show 0 rate
        assert "Rate: 0 chains/s" in caplog.text
        assert "ETA: unknown" in caplog.text


class TestProgressLoggerETACalculation:
    """Tests for estimated time remaining calculation (subtask 9.3.2)."""
    
    def test_calculate_eta_helper_basic(self):
        """Test calculate_eta() helper function with basic inputs."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        # Test with 25,000 chains processed at 1,000 chains/s
        # Remaining: 75,000 chains / 1,000 chains/s = 75 seconds = 1m 15s
        eta = logger.calculate_eta(chains_processed=25000, current_rate=1000.0)
        assert eta == "1m 15s"
    
    def test_calculate_eta_helper_zero_rate(self):
        """Test calculate_eta() with zero processing rate."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        # Zero rate should return "unknown"
        eta = logger.calculate_eta(chains_processed=10000, current_rate=0.0)
        assert eta == "unknown"
    
    def test_calculate_eta_helper_negative_rate(self):
        """Test calculate_eta() with negative processing rate."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        # Negative rate should return "unknown"
        eta = logger.calculate_eta(chains_processed=10000, current_rate=-100.0)
        assert eta == "unknown"
    
    def test_calculate_eta_helper_near_completion(self):
        """Test calculate_eta() near completion."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        # Test with 99,000 chains processed at 1,000 chains/s
        # Remaining: 1,000 chains / 1,000 chains/s = 1 second
        eta = logger.calculate_eta(chains_processed=99000, current_rate=1000.0)
        assert eta == "1s"
    
    def test_calculate_eta_helper_slow_rate(self):
        """Test calculate_eta() with slow processing rate."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        # Test with 10,000 chains processed at 10 chains/s
        # Remaining: 90,000 chains / 10 chains/s = 9,000 seconds = 2h 30m
        eta = logger.calculate_eta(chains_processed=10000, current_rate=10.0)
        assert eta == "2h 30m"
    
    def test_calculate_eta_helper_fast_rate(self):
        """Test calculate_eta() with fast processing rate."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        # Test with 50,000 chains processed at 10,000 chains/s
        # Remaining: 50,000 chains / 10,000 chains/s = 5 seconds
        eta = logger.calculate_eta(chains_processed=50000, current_rate=10000.0)
        assert eta == "5s"
    
    def test_calculate_eta_helper_long_duration(self):
        """Test calculate_eta() with long duration (days)."""
        logger = ProgressLogger(total_chains=10000000, log_interval=10000)
        
        # Test with 1,000,000 chains processed at 100 chains/s
        # Remaining: 9,000,000 chains / 100 chains/s = 90,000 seconds = 1d 1h 0m
        eta = logger.calculate_eta(chains_processed=1000000, current_rate=100.0)
        assert eta == "1d 1h 0m"
    
    def test_calculate_eta_helper_fractional_rate(self):
        """Test calculate_eta() with fractional processing rate."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        
        # Test with 10,000 chains processed at 123.45 chains/s
        # Remaining: 90,000 chains / 123.45 chains/s ≈ 729 seconds ≈ 12m 9s
        eta = logger.calculate_eta(chains_processed=10000, current_rate=123.45)
        assert eta == "12m 9s"
    
    def test_calculate_eta_basic(self, caplog):
        """Test basic ETA calculation."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        time.sleep(0.1)
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        # ETA should be present in the log
        assert "ETA:" in caplog.text
    
    def test_calculate_eta_zero_rate(self, caplog):
        """Test ETA calculation when processing rate is zero."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        # Immediately log progress (rate will be very high or zero)
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        # Should handle zero rate gracefully
        assert "ETA:" in caplog.text
    
    def test_calculate_eta_near_completion(self, caplog):
        """Test ETA calculation near completion."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        time.sleep(0.1)
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(90000)
        
        # ETA should be present and relatively short
        assert "ETA:" in caplog.text
    
    def test_eta_format_consistency(self, caplog):
        """Test that ETA is formatted consistently."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        time.sleep(0.1)
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        log_text = caplog.text
        
        # ETA should be in a readable format (using _format_time)
        assert "ETA:" in log_text
        # Should contain time units (s, m, h, or d)
        assert any(unit in log_text for unit in ["s", "m", "h", "d", "unknown"])


class TestProgressLoggerMessageFormatting:
    """Tests for progress message formatting (subtask 9.3.3)."""
    
    def test_format_progress_message_structure(self, caplog):
        """Test that progress message has correct structure."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        time.sleep(0.1)
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        log_text = caplog.text
        
        # Message should contain all required components
        assert "Progress:" in log_text
        assert "chains" in log_text
        assert "%" in log_text
        assert "Rate:" in log_text
        assert "chains/s" in log_text
        assert "ETA:" in log_text
    
    def test_format_chains_with_commas(self, caplog):
        """Test that chain counts are formatted with commas."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        time.sleep(0.1)
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        # Should format as "10,000" not "10000"
        assert "10,000 chains" in caplog.text
    
    def test_format_percentage_with_decimals(self, caplog):
        """Test that percentage is formatted with two decimal places."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        time.sleep(0.1)
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(10000)
        
        # Should format as "10.00%" with two decimal places
        assert "10.00%" in caplog.text
    
    def test_format_rate_with_commas(self, caplog):
        """Test that processing rate is formatted with commas."""
        logger = ProgressLogger(total_chains=1000000, log_interval=100000)
        logger.start()
        
        time.sleep(0.1)
        
        with caplog.at_level(logging.INFO):
            logger.log_progress(100000)
        
        log_text = caplog.text
        
        # Rate should be formatted with commas for large numbers
        assert "chains/s" in log_text
        # Should contain comma separator for thousands
        assert "," in log_text or "Rate: " in log_text
    
    def test_progress_message_at_different_percentages(self, caplog):
        """Test progress message formatting at different completion percentages."""
        logger = ProgressLogger(total_chains=100000, log_interval=10000)
        logger.start()
        
        percentages = []
        
        for chains in [10000, 25000, 50000, 75000, 90000]:
            time.sleep(0.01)
            caplog.clear()
            
            with caplog.at_level(logging.INFO):
                logger.log_progress(chains)
            
            log_text = caplog.text
            
            # Extract percentage from log
            if "%" in log_text:
                # Find the percentage value
                import re
                match = re.search(r'(\d+\.\d+)%', log_text)
                if match:
                    percentages.append(float(match.group(1)))
        
        # Percentages should be increasing
        assert len(percentages) > 0
        for i in range(1, len(percentages)):
            assert percentages[i] > percentages[i-1]


class TestProgressLoggerIntegration:
    """Integration tests for ProgressLogger."""
    
    def test_full_progress_tracking(self, tmp_path, caplog):
        """Test complete progress tracking workflow."""
        log_file = tmp_path / "logs" / "test.log"
        logger = ProgressLogger(
            total_chains=50000,
            log_interval=10000,
            log_file=str(log_file)
        )
        
        # Start generation
        logger.start()
        logger.log_start(
            hash_algorithm="md5",
            chain_length=1000,
            qubit_count=4,
            input_file="test_wordset.txt",
            output_directory=str(tmp_path / "output")
        )
        
        # Simulate progress
        with caplog.at_level(logging.INFO):
            for chains in [10000, 20000, 30000, 40000, 50000]:
                time.sleep(0.01)  # Small delay
                if logger.should_log(chains):
                    logger.log_progress(chains)
        
        # Log summary
        logger.log_summary(
            total_chains=50000,
            total_buckets=16,
            generation_time_seconds=50.0,
            average_rate=1000.0
        )
        
        # Verify log file was created and contains content
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "Starting rainbow table generation" in log_content
        assert "Progress:" in log_content
        assert "Generation complete!" in log_content
    
    def test_progress_with_checkpoints(self, caplog):
        """Test progress tracking with checkpoint logging."""
        logger = ProgressLogger(total_chains=200000, log_interval=10000)
        logger.start()
        
        with caplog.at_level(logging.INFO):
            # Simulate progress with checkpoints every 100,000 chains
            for chains in range(10000, 200001, 10000):
                if logger.should_log(chains):
                    logger.log_progress(chains)
                
                if chains % 100000 == 0:
                    logger.log_checkpoint(chains)
        
        assert "Checkpoint saved: 100,000 chains processed" in caplog.text
        assert "Checkpoint saved: 200,000 chains processed" in caplog.text
