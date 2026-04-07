"""
Unit tests for reduction function module.
"""

import pytest
import hashlib
from rainbow_table_generator.reduction import reduce, validate_password, CHARSET


class TestReduce:
    """Tests for reduce function."""
    
    # 4.4.1: Test deterministic behavior (same input → same output)
    def test_deterministic_behavior(self):
        """Test that same inputs produce same output."""
        hash_value = hashlib.md5(b"password").digest()
        iteration = 0
        password_length = 8
        
        # Call reduce multiple times with same inputs
        result1 = reduce(hash_value, iteration, password_length)
        result2 = reduce(hash_value, iteration, password_length)
        result3 = reduce(hash_value, iteration, password_length)
        
        # All results should be identical
        assert result1 == result2
        assert result2 == result3
    
    def test_deterministic_with_different_hash(self):
        """Test deterministic behavior with different hash values."""
        hash_value1 = hashlib.md5(b"password1").digest()
        hash_value2 = hashlib.md5(b"password2").digest()
        iteration = 5
        password_length = 6
        
        # Each hash should consistently produce the same output
        result1a = reduce(hash_value1, iteration, password_length)
        result1b = reduce(hash_value1, iteration, password_length)
        result2a = reduce(hash_value2, iteration, password_length)
        result2b = reduce(hash_value2, iteration, password_length)
        
        assert result1a == result1b
        assert result2a == result2b
    
    # 4.4.2: Test iteration-dependent behavior (different iterations → different outputs)
    def test_iteration_dependent_behavior(self):
        """Test that different iterations produce different outputs."""
        hash_value = hashlib.md5(b"password").digest()
        password_length = 8
        
        # Generate passwords with different iterations
        result_iter0 = reduce(hash_value, 0, password_length)
        result_iter1 = reduce(hash_value, 1, password_length)
        result_iter2 = reduce(hash_value, 2, password_length)
        
        # All results should be different
        assert result_iter0 != result_iter1
        assert result_iter1 != result_iter2
        assert result_iter0 != result_iter2
    
    def test_iteration_dependent_multiple_iterations(self):
        """Test iteration dependency across a range of iterations."""
        hash_value = hashlib.sha1(b"test").digest()
        password_length = 6
        
        # Generate passwords for iterations 0-9
        results = [reduce(hash_value, i, password_length) for i in range(10)]
        
        # All results should be unique
        assert len(results) == len(set(results))
    
    # 4.4.3: Test password length constraint
    def test_password_length_constraint(self):
        """Test that output password matches requested length."""
        hash_value = hashlib.md5(b"password").digest()
        iteration = 0
        
        # Test various password lengths
        for length in [4, 6, 8, 10, 12]:
            result = reduce(hash_value, iteration, length)
            assert len(result) == length
    
    def test_password_length_edge_cases(self):
        """Test password length with edge case values."""
        hash_value = hashlib.sha256(b"test").digest()
        iteration = 3
        
        # Test minimum length
        result_min = reduce(hash_value, iteration, 1)
        assert len(result_min) == 1
        
        # Test larger length
        result_large = reduce(hash_value, iteration, 20)
        assert len(result_large) == 20
    
    # 4.4.4: Test character set constraint
    def test_character_set_constraint(self):
        """Test that all characters in output are from CHARSET."""
        hash_value = hashlib.md5(b"password").digest()
        iteration = 0
        password_length = 8
        
        result = reduce(hash_value, iteration, password_length)
        
        # Verify all characters are in CHARSET
        assert all(c in CHARSET for c in result)
    
    def test_character_set_constraint_multiple_cases(self):
        """Test character set constraint across multiple test cases."""
        test_cases = [
            (hashlib.md5(b"test1").digest(), 0, 6),
            (hashlib.sha1(b"test2").digest(), 5, 8),
            (hashlib.sha256(b"test3").digest(), 10, 10),
            (hashlib.md5(b"").digest(), 0, 4),
        ]
        
        for hash_value, iteration, password_length in test_cases:
            result = reduce(hash_value, iteration, password_length)
            assert all(c in CHARSET for c in result)
    
    def test_charset_contains_expected_characters(self):
        """Test that CHARSET contains lowercase letters and digits."""
        # Verify CHARSET composition
        assert "abcdefghijklmnopqrstuvwxyz" in CHARSET
        assert "0123456789" in CHARSET
        assert len(CHARSET) == 36  # 26 letters + 10 digits


class TestValidatePassword:
    """Tests for validate_password function."""
    
    def test_valid_password(self):
        """Test validation of a valid password."""
        password = "abc123"
        expected_length = 6
        
        assert validate_password(password, expected_length) is True
    
    def test_valid_password_all_letters(self):
        """Test validation with all letters."""
        password = "abcdefgh"
        expected_length = 8
        
        assert validate_password(password, expected_length) is True
    
    def test_valid_password_all_digits(self):
        """Test validation with all digits."""
        password = "123456"
        expected_length = 6
        
        assert validate_password(password, expected_length) is True
    
    def test_invalid_password_wrong_length_too_short(self):
        """Test validation fails when password is too short."""
        password = "abc123"
        expected_length = 8
        
        assert validate_password(password, expected_length) is False
    
    def test_invalid_password_wrong_length_too_long(self):
        """Test validation fails when password is too long."""
        password = "abc12345"
        expected_length = 6
        
        assert validate_password(password, expected_length) is False
    
    def test_invalid_password_special_characters(self):
        """Test validation fails with special characters."""
        password = "abc@123"
        expected_length = 7
        
        assert validate_password(password, expected_length) is False
    
    def test_invalid_password_uppercase_letters(self):
        """Test validation fails with uppercase letters."""
        password = "Abc123"
        expected_length = 6
        
        assert validate_password(password, expected_length) is False
    
    def test_invalid_password_space(self):
        """Test validation fails with space character."""
        password = "abc 123"
        expected_length = 7
        
        assert validate_password(password, expected_length) is False
    
    def test_empty_password(self):
        """Test validation of empty password."""
        password = ""
        expected_length = 0
        
        assert validate_password(password, expected_length) is True
    
    def test_empty_password_wrong_length(self):
        """Test validation fails for empty password with non-zero expected length."""
        password = ""
        expected_length = 6
        
        assert validate_password(password, expected_length) is False
