"""
Unit tests for chain generator module.
"""

import pytest
from rainbow_table_generator.chain_generator import ChainGenerator
from rainbow_table_generator.hash_functions import MD5HashFunction, SHA256HashFunction


class TestChainGenerator:
    """Tests for ChainGenerator class."""
    
    def test_initialization_with_valid_parameters(self):
        """Test ChainGenerator initialization with valid parameters."""
        hash_func = MD5HashFunction()
        chain_length = 1000
        password_length = 8
        
        generator = ChainGenerator(hash_func, chain_length, password_length)
        
        assert generator.hash_function == hash_func
        assert generator.chain_length == chain_length
        assert generator.password_length == password_length
    
    def test_initialization_with_different_hash_function(self):
        """Test initialization with different hash function."""
        hash_func = SHA256HashFunction()
        chain_length = 500
        password_length = 6
        
        generator = ChainGenerator(hash_func, chain_length, password_length)
        
        assert generator.hash_function == hash_func
        assert generator.chain_length == chain_length
        assert generator.password_length == password_length
    
    def test_initialization_with_invalid_chain_length_zero(self):
        """Test that initialization fails with chain_length of 0."""
        hash_func = MD5HashFunction()
        
        with pytest.raises(ValueError, match="chain_length must be positive"):
            ChainGenerator(hash_func, 0, 8)
    
    def test_initialization_with_invalid_chain_length_negative(self):
        """Test that initialization fails with negative chain_length."""
        hash_func = MD5HashFunction()
        
        with pytest.raises(ValueError, match="chain_length must be positive"):
            ChainGenerator(hash_func, -1, 8)
    
    def test_initialization_with_invalid_password_length_zero(self):
        """Test that initialization fails with password_length of 0."""
        hash_func = MD5HashFunction()
        
        with pytest.raises(ValueError, match="password_length must be positive"):
            ChainGenerator(hash_func, 1000, 0)
    
    def test_initialization_with_invalid_password_length_negative(self):
        """Test that initialization fails with negative password_length."""
        hash_func = MD5HashFunction()
        
        with pytest.raises(ValueError, match="password_length must be positive"):
            ChainGenerator(hash_func, 1000, -5)
    
    def test_repr(self):
        """Test string representation of ChainGenerator."""
        hash_func = MD5HashFunction()
        chain_length = 1000
        password_length = 8
        
        generator = ChainGenerator(hash_func, chain_length, password_length)
        repr_str = repr(generator)
        
        assert "ChainGenerator" in repr_str
        assert "chain_length=1000" in repr_str
        assert "password_length=8" in repr_str


class TestGenerateChain:
    """Tests for generate_chain method."""

    def test_generate_chain_with_empty_start_point(self):
        """Test that generate_chain raises ValueError for empty start_point."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)

        def mock_reduce(hash_bytes, iteration, length):
            return "a" * length

        with pytest.raises(ValueError, match="start_point cannot be empty"):
            generator.generate_chain("", mock_reduce)

    def test_generate_chain_with_non_string_start_point(self):
        """Test that generate_chain raises TypeError for non-string start_point."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)

        def mock_reduce(hash_bytes, iteration, length):
            return "a" * length

        with pytest.raises(TypeError, match="start_point must be a string"):
            generator.generate_chain(12345, mock_reduce)

    def test_generate_chain_with_non_callable_reduce_func(self):
        """Test that generate_chain raises TypeError for non-callable reduce_func."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)

        with pytest.raises(TypeError, match="reduce_func must be callable"):
            generator.generate_chain("password", "not_a_function")

    def test_generate_chain_with_reduce_func_returning_wrong_type(self):
        """Test that generate_chain raises RuntimeError when reduce_func returns non-string."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)

        def bad_reduce(hash_bytes, iteration, length):
            return 12345  # Returns int instead of str

        with pytest.raises(RuntimeError, match="Reduction function returned invalid type"):
            generator.generate_chain("password", bad_reduce)

    def test_generate_chain_with_reduce_func_returning_empty_string(self):
        """Test that generate_chain raises RuntimeError when reduce_func returns empty string."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)

        def bad_reduce(hash_bytes, iteration, length):
            return ""  # Returns empty string

        with pytest.raises(RuntimeError, match="Reduction function returned empty string"):
            generator.generate_chain("password", bad_reduce)

    def test_generate_chain_with_reduce_func_returning_wrong_length(self):
        """Test that generate_chain raises RuntimeError when reduce_func returns wrong length."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)

        def bad_reduce(hash_bytes, iteration, length):
            return "abc"  # Returns length 3 instead of 8

        with pytest.raises(RuntimeError, match="Reduction function returned password of length 3, expected 8"):
            generator.generate_chain("password", bad_reduce)

    def test_generate_chain_with_reduce_func_raising_exception(self):
        """Test that generate_chain handles exceptions from reduce_func."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)

        def bad_reduce(hash_bytes, iteration, length):
            raise ValueError("Simulated reduction error")

        with pytest.raises(RuntimeError, match="Reduction operation failed at iteration 0"):
            generator.generate_chain("password", bad_reduce)

    def test_generate_chain_with_hash_function_error(self):
        """Test that generate_chain handles hash function errors."""
        # Create a mock hash function that raises an error
        class BadHashFunction:
            def hash(self, password):
                raise ValueError("Simulated hash error")

        bad_hash = BadHashFunction()
        generator = ChainGenerator(bad_hash, chain_length=10, password_length=8)

        def mock_reduce(hash_bytes, iteration, length):
            return "a" * length

        with pytest.raises(RuntimeError, match="Hash operation failed at iteration 0"):
            generator.generate_chain("password", mock_reduce)

    def test_generate_chain_error_at_specific_iteration(self):
        """Test that error messages include the correct iteration number."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)

        call_count = [0]

        def failing_reduce(hash_bytes, iteration, length):
            call_count[0] += 1
            if call_count[0] == 5:  # Fail on 5th call (iteration 4)
                raise ValueError("Simulated error at iteration 4")
            return "a" * length

        with pytest.raises(RuntimeError, match="Reduction operation failed at iteration 4"):
            generator.generate_chain("password", failing_reduce)

    def test_generate_chain_with_valid_inputs(self):
        """Test successful chain generation with valid inputs."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=5, password_length=8)

        def mock_reduce(hash_bytes, iteration, length):
            # Simple deterministic reduction for testing
            return "a" * length

        start, end = generator.generate_chain("password", mock_reduce)

        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8


class TestChainGenerationWithDifferentHashFunctions:
    """Tests for chain generation with different hash functions (Task 5.4.1)."""

    def test_chain_generation_with_md5(self):
        """Test chain generation using MD5 hash function."""
        from rainbow_table_generator.reduction import reduce
        
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8
        # Verify deterministic behavior
        start2, end2 = generator.generate_chain("password", reduce)
        assert end == end2

    def test_chain_generation_with_sha1(self):
        """Test chain generation using SHA-1 hash function."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        from rainbow_table_generator.reduction import reduce
        
        hash_func = SHA1HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8

    def test_chain_generation_with_sha256(self):
        """Test chain generation using SHA-256 hash function."""
        from rainbow_table_generator.reduction import reduce
        
        hash_func = SHA256HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8

    def test_different_hash_functions_produce_different_endpoints(self):
        """Test that different hash functions produce different chain endpoints."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        from rainbow_table_generator.reduction import reduce
        
        start_point = "password"
        chain_length = 100
        password_length = 8
        
        # Generate chain with MD5
        md5_gen = ChainGenerator(MD5HashFunction(), chain_length, password_length)
        _, md5_end = md5_gen.generate_chain(start_point, reduce)
        
        # Generate chain with SHA-1
        sha1_gen = ChainGenerator(SHA1HashFunction(), chain_length, password_length)
        _, sha1_end = sha1_gen.generate_chain(start_point, reduce)
        
        # Generate chain with SHA-256
        sha256_gen = ChainGenerator(SHA256HashFunction(), chain_length, password_length)
        _, sha256_end = sha256_gen.generate_chain(start_point, reduce)
        
        # Different hash functions should produce different endpoints
        assert md5_end != sha1_end
        assert md5_end != sha256_end
        assert sha1_end != sha256_end

    def test_chain_generation_deterministic_across_hash_functions(self):
        """Test that chain generation is deterministic for each hash function."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        from rainbow_table_generator.reduction import reduce
        
        start_point = "testpass"
        chain_length = 50
        password_length = 8
        
        # Test MD5 determinism
        md5_gen = ChainGenerator(MD5HashFunction(), chain_length, password_length)
        _, md5_end1 = md5_gen.generate_chain(start_point, reduce)
        _, md5_end2 = md5_gen.generate_chain(start_point, reduce)
        assert md5_end1 == md5_end2
        
        # Test SHA-1 determinism
        sha1_gen = ChainGenerator(SHA1HashFunction(), chain_length, password_length)
        _, sha1_end1 = sha1_gen.generate_chain(start_point, reduce)
        _, sha1_end2 = sha1_gen.generate_chain(start_point, reduce)
        assert sha1_end1 == sha1_end2
        
        # Test SHA-256 determinism
        sha256_gen = ChainGenerator(SHA256HashFunction(), chain_length, password_length)
        _, sha256_end1 = sha256_gen.generate_chain(start_point, reduce)
        _, sha256_end2 = sha256_gen.generate_chain(start_point, reduce)
        assert sha256_end1 == sha256_end2


class TestChainGenerationWithDifferentChainLengths:
    """Tests for chain generation with different chain lengths (Task 5.4.2)."""

    def test_chain_generation_with_length_1(self):
        """Test chain generation with minimum chain length of 1."""
        from rainbow_table_generator.reduction import reduce
        
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=1, password_length=8)
        
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8
        # With chain length 1, endpoint should be different from start
        assert end != start

    def test_chain_generation_with_length_10(self):
        """Test chain generation with chain length of 10."""
        from rainbow_table_generator.reduction import reduce
        
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8

    def test_chain_generation_with_length_100(self):
        """Test chain generation with chain length of 100."""
        from rainbow_table_generator.reduction import reduce
        
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=100, password_length=8)
        
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8

    def test_chain_generation_with_length_1000(self):
        """Test chain generation with chain length of 1000."""
        from rainbow_table_generator.reduction import reduce
        
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=1000, password_length=8)
        
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8

    def test_chain_generation_with_length_10000(self):
        """Test chain generation with maximum chain length of 10000."""
        from rainbow_table_generator.reduction import reduce
        
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10000, password_length=8)
        
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8

    def test_different_chain_lengths_produce_different_endpoints(self):
        """Test that different chain lengths produce different endpoints."""
        from rainbow_table_generator.reduction import reduce
        
        hash_func = MD5HashFunction()
        start_point = "password"
        password_length = 8
        
        # Generate chains with different lengths
        gen1 = ChainGenerator(hash_func, chain_length=10, password_length=password_length)
        _, end1 = gen1.generate_chain(start_point, reduce)
        
        gen2 = ChainGenerator(hash_func, chain_length=100, password_length=password_length)
        _, end2 = gen2.generate_chain(start_point, reduce)
        
        gen3 = ChainGenerator(hash_func, chain_length=1000, password_length=password_length)
        _, end3 = gen3.generate_chain(start_point, reduce)
        
        # Different chain lengths should produce different endpoints
        assert end1 != end2
        assert end1 != end3
        assert end2 != end3

    def test_chain_length_affects_computation_time(self):
        """Test that longer chains take more time (basic performance check)."""
        import time
        from rainbow_table_generator.reduction import reduce
        
        hash_func = MD5HashFunction()
        start_point = "password"
        password_length = 8
        
        # Measure time for short chain
        gen_short = ChainGenerator(hash_func, chain_length=10, password_length=password_length)
        start_time = time.time()
        gen_short.generate_chain(start_point, reduce)
        time_short = time.time() - start_time
        
        # Measure time for long chain
        gen_long = ChainGenerator(hash_func, chain_length=1000, password_length=password_length)
        start_time = time.time()
        gen_long.generate_chain(start_point, reduce)
        time_long = time.time() - start_time
        
        # Longer chain should take more time (with some tolerance for measurement variance)
        # We expect at least 5x difference for 100x chain length increase
        assert time_long > time_short * 5


class TestChainGenerationErrorHandling:
    """Tests for error handling in chain generation (Task 5.4.3)."""

    def test_error_handling_with_hash_returning_non_bytes(self):
        """Test error handling when hash function returns non-bytes."""
        class BadHashFunction:
            algorithm_name = "bad"
            def hash(self, password):
                return "not bytes"  # Returns string instead of bytes
        
        bad_hash = BadHashFunction()
        generator = ChainGenerator(bad_hash, chain_length=10, password_length=8)
        
        def mock_reduce(hash_bytes, iteration, length):
            return "a" * length
        
        with pytest.raises(RuntimeError, match="Hash function returned invalid type"):
            generator.generate_chain("password", mock_reduce)

    def test_error_handling_with_hash_returning_empty_bytes(self):
        """Test error handling when hash function returns empty bytes."""
        class BadHashFunction:
            algorithm_name = "bad"
            def hash(self, password):
                return b""  # Returns empty bytes
        
        bad_hash = BadHashFunction()
        generator = ChainGenerator(bad_hash, chain_length=10, password_length=8)
        
        def mock_reduce(hash_bytes, iteration, length):
            return "a" * length
        
        with pytest.raises(RuntimeError, match="Hash function returned empty bytes"):
            generator.generate_chain("password", mock_reduce)

    def test_error_handling_with_hash_raising_exception(self):
        """Test error handling when hash function raises an exception."""
        class BadHashFunction:
            algorithm_name = "bad"
            def hash(self, password):
                raise ValueError("Simulated hash error")
        
        bad_hash = BadHashFunction()
        generator = ChainGenerator(bad_hash, chain_length=10, password_length=8)
        
        def mock_reduce(hash_bytes, iteration, length):
            return "a" * length
        
        with pytest.raises(RuntimeError, match="Hash operation failed at iteration 0"):
            generator.generate_chain("password", mock_reduce)

    def test_error_handling_with_reduce_returning_non_string(self):
        """Test error handling when reduce function returns non-string."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        def bad_reduce(hash_bytes, iteration, length):
            return 12345  # Returns int instead of str
        
        with pytest.raises(RuntimeError, match="Reduction function returned invalid type"):
            generator.generate_chain("password", bad_reduce)

    def test_error_handling_with_reduce_returning_empty_string(self):
        """Test error handling when reduce function returns empty string."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        def bad_reduce(hash_bytes, iteration, length):
            return ""
        
        with pytest.raises(RuntimeError, match="Reduction function returned empty string"):
            generator.generate_chain("password", bad_reduce)

    def test_error_handling_with_reduce_returning_wrong_length(self):
        """Test error handling when reduce function returns wrong length password."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        def bad_reduce(hash_bytes, iteration, length):
            return "abc"  # Returns length 3 instead of 8
        
        with pytest.raises(RuntimeError, match="Reduction function returned password of length 3, expected 8"):
            generator.generate_chain("password", bad_reduce)

    def test_error_handling_with_reduce_raising_exception(self):
        """Test error handling when reduce function raises an exception."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        def bad_reduce(hash_bytes, iteration, length):
            raise ValueError("Simulated reduction error")
        
        with pytest.raises(RuntimeError, match="Reduction operation failed at iteration 0"):
            generator.generate_chain("password", bad_reduce)

    def test_error_handling_preserves_iteration_context(self):
        """Test that error messages include correct iteration number."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=20, password_length=8)
        
        call_count = [0]
        
        def failing_reduce(hash_bytes, iteration, length):
            call_count[0] += 1
            if call_count[0] == 7:  # Fail on 7th call (iteration 6)
                raise ValueError("Simulated error at iteration 6")
            return "a" * length
        
        with pytest.raises(RuntimeError, match="Reduction operation failed at iteration 6"):
            generator.generate_chain("password", failing_reduce)

    def test_error_handling_with_empty_start_point(self):
        """Test error handling with empty start point."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        def mock_reduce(hash_bytes, iteration, length):
            return "a" * length
        
        with pytest.raises(ValueError, match="start_point cannot be empty"):
            generator.generate_chain("", mock_reduce)

    def test_error_handling_with_non_string_start_point(self):
        """Test error handling with non-string start point."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        def mock_reduce(hash_bytes, iteration, length):
            return "a" * length
        
        with pytest.raises(TypeError, match="start_point must be a string"):
            generator.generate_chain(12345, mock_reduce)

    def test_error_handling_with_non_callable_reduce_func(self):
        """Test error handling with non-callable reduce function."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        with pytest.raises(TypeError, match="reduce_func must be callable"):
            generator.generate_chain("password", "not_a_function")

    def test_error_recovery_after_failed_chain(self):
        """Test that generator can recover and generate valid chains after an error."""
        hash_func = MD5HashFunction()
        generator = ChainGenerator(hash_func, chain_length=10, password_length=8)
        
        # First attempt with bad reduce function
        def bad_reduce(hash_bytes, iteration, length):
            raise ValueError("Simulated error")
        
        with pytest.raises(RuntimeError):
            generator.generate_chain("password", bad_reduce)
        
        # Second attempt with good reduce function should work
        from rainbow_table_generator.reduction import reduce
        start, end = generator.generate_chain("password", reduce)
        
        assert start == "password"
        assert isinstance(end, str)
        assert len(end) == 8
