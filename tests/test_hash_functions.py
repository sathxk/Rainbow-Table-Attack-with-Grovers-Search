"""
Unit tests for hash function wrappers.
"""

import pytest


class TestHashFunction:
    """Tests for HashFunction abstract base class."""
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that HashFunction cannot be instantiated directly."""
        from rainbow_table_generator.hash_functions import HashFunction
        
        with pytest.raises(TypeError):
            HashFunction("test")


class TestMD5HashFunction:
    """Tests for MD5HashFunction class."""
    
    def test_md5_hash_returns_bytes(self):
        """Test that MD5 hash returns bytes."""
        from rainbow_table_generator.hash_functions import MD5HashFunction
        
        md5_func = MD5HashFunction()
        result = md5_func.hash("password")
        
        assert isinstance(result, bytes)
        assert len(result) == 16  # MD5 produces 16 bytes
    
    def test_md5_hash_known_value(self):
        """Test MD5 hash against a known value."""
        from rainbow_table_generator.hash_functions import MD5HashFunction
        
        md5_func = MD5HashFunction()
        # MD5 hash of "password" is 5f4dcc3b5aa765d61d8327deb882cf99
        result = md5_func.hash_hex("password")
        
        assert result == "5f4dcc3b5aa765d61d8327deb882cf99"
    
    def test_md5_algorithm_name(self):
        """Test that algorithm name is set correctly."""
        from rainbow_table_generator.hash_functions import MD5HashFunction
        
        md5_func = MD5HashFunction()
        assert md5_func.algorithm_name == "md5"
    
    def test_md5_empty_string(self):
        """Test MD5 hash of empty string."""
        from rainbow_table_generator.hash_functions import MD5HashFunction
        
        md5_func = MD5HashFunction()
        # MD5 hash of empty string is d41d8cd98f00b204e9800998ecf8427e
        result = md5_func.hash_hex("")
        
        assert result == "d41d8cd98f00b204e9800998ecf8427e"
    
    def test_md5_special_characters(self):
        """Test MD5 hash with special characters."""
        from rainbow_table_generator.hash_functions import MD5HashFunction
        
        md5_func = MD5HashFunction()
        result = md5_func.hash_hex("p@$$w0rd!")
        
        # Verify it produces a valid hex string of correct length
        assert len(result) == 32  # MD5 hex is 32 characters
        assert all(c in "0123456789abcdef" for c in result)
    
    def test_md5_repr(self):
        """Test string representation of MD5HashFunction."""
        from rainbow_table_generator.hash_functions import MD5HashFunction
        
        md5_func = MD5HashFunction()
        repr_str = repr(md5_func)
        
        assert "MD5HashFunction" in repr_str
        assert "md5" in repr_str


class TestSHA1HashFunction:
    """Tests for SHA1HashFunction class."""
    
    def test_sha1_hash_returns_bytes(self):
        """Test that SHA-1 hash returns bytes."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        
        sha1_func = SHA1HashFunction()
        result = sha1_func.hash("password")
        
        assert isinstance(result, bytes)
        assert len(result) == 20  # SHA-1 produces 20 bytes
    
    def test_sha1_hash_known_value(self):
        """Test SHA-1 hash against a known value."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        
        sha1_func = SHA1HashFunction()
        # SHA-1 hash of "password" is 5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8
        result = sha1_func.hash_hex("password")
        
        assert result == "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8"
    
    def test_sha1_algorithm_name(self):
        """Test that algorithm name is set correctly."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        
        sha1_func = SHA1HashFunction()
        assert sha1_func.algorithm_name == "sha1"
    
    def test_sha1_empty_string(self):
        """Test SHA-1 hash of empty string."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        
        sha1_func = SHA1HashFunction()
        # SHA-1 hash of empty string is da39a3ee5e6b4b0d3255bfef95601890afd80709
        result = sha1_func.hash_hex("")
        
        assert result == "da39a3ee5e6b4b0d3255bfef95601890afd80709"
    
    def test_sha1_special_characters(self):
        """Test SHA-1 hash with special characters."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        
        sha1_func = SHA1HashFunction()
        result = sha1_func.hash_hex("p@$$w0rd!")
        
        # Verify it produces a valid hex string of correct length
        assert len(result) == 40  # SHA-1 hex is 40 characters
        assert all(c in "0123456789abcdef" for c in result)
    
    def test_sha1_repr(self):
        """Test string representation of SHA1HashFunction."""
        from rainbow_table_generator.hash_functions import SHA1HashFunction
        
        sha1_func = SHA1HashFunction()
        repr_str = repr(sha1_func)
        
        assert "SHA1HashFunction" in repr_str
        assert "sha1" in repr_str


class TestSHA256HashFunction:
    """Tests for SHA256HashFunction class."""
    
    def test_sha256_hash_returns_bytes(self):
        """Test that SHA-256 hash returns bytes."""
        from rainbow_table_generator.hash_functions import SHA256HashFunction
        
        sha256_func = SHA256HashFunction()
        result = sha256_func.hash("password")
        
        assert isinstance(result, bytes)
        assert len(result) == 32  # SHA-256 produces 32 bytes
    
    def test_sha256_hash_known_value(self):
        """Test SHA-256 hash against a known value."""
        from rainbow_table_generator.hash_functions import SHA256HashFunction
        
        sha256_func = SHA256HashFunction()
        # SHA-256 hash of "password" is 5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8
        result = sha256_func.hash_hex("password")
        
        assert result == "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    
    def test_sha256_algorithm_name(self):
        """Test that algorithm name is set correctly."""
        from rainbow_table_generator.hash_functions import SHA256HashFunction
        
        sha256_func = SHA256HashFunction()
        assert sha256_func.algorithm_name == "sha256"
    
    def test_sha256_empty_string(self):
        """Test SHA-256 hash of empty string."""
        from rainbow_table_generator.hash_functions import SHA256HashFunction
        
        sha256_func = SHA256HashFunction()
        # SHA-256 hash of empty string is e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        result = sha256_func.hash_hex("")
        
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    
    def test_sha256_special_characters(self):
        """Test SHA-256 hash with special characters."""
        from rainbow_table_generator.hash_functions import SHA256HashFunction
        
        sha256_func = SHA256HashFunction()
        result = sha256_func.hash_hex("p@$$w0rd!")
        
        # Verify it produces a valid hex string of correct length
        assert len(result) == 64  # SHA-256 hex is 64 characters
        assert all(c in "0123456789abcdef" for c in result)
    
    def test_sha256_unicode_characters(self):
        """Test SHA-256 hash with Unicode characters."""
        from rainbow_table_generator.hash_functions import SHA256HashFunction
        
        sha256_func = SHA256HashFunction()
        result = sha256_func.hash_hex("пароль")  # Russian for "password"
        
        # Verify it produces a valid hex string of correct length
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)
    
    def test_sha256_repr(self):
        """Test string representation of SHA256HashFunction."""
        from rainbow_table_generator.hash_functions import SHA256HashFunction
        
        sha256_func = SHA256HashFunction()
        repr_str = repr(sha256_func)
        
        assert "SHA256HashFunction" in repr_str
        assert "sha256" in repr_str


class TestHashFactory:
    """Tests for hash_factory function."""
    
    def test_factory_creates_md5(self):
        """Test that factory creates MD5HashFunction."""
        from rainbow_table_generator.hash_functions import hash_factory, MD5HashFunction
        
        hash_func = hash_factory("md5")
        
        assert isinstance(hash_func, MD5HashFunction)
        assert hash_func.algorithm_name == "md5"
    
    def test_factory_creates_sha1(self):
        """Test that factory creates SHA1HashFunction."""
        from rainbow_table_generator.hash_functions import hash_factory, SHA1HashFunction
        
        hash_func = hash_factory("sha1")
        
        assert isinstance(hash_func, SHA1HashFunction)
        assert hash_func.algorithm_name == "sha1"
    
    def test_factory_creates_sha256(self):
        """Test that factory creates SHA256HashFunction."""
        from rainbow_table_generator.hash_functions import hash_factory, SHA256HashFunction
        
        hash_func = hash_factory("sha256")
        
        assert isinstance(hash_func, SHA256HashFunction)
        assert hash_func.algorithm_name == "sha256"
    
    def test_factory_case_insensitive(self):
        """Test that factory is case-insensitive."""
        from rainbow_table_generator.hash_functions import hash_factory, MD5HashFunction
        
        hash_func_upper = hash_factory("MD5")
        hash_func_mixed = hash_factory("Md5")
        
        assert isinstance(hash_func_upper, MD5HashFunction)
        assert isinstance(hash_func_mixed, MD5HashFunction)
    
    def test_factory_invalid_algorithm_raises_error(self):
        """Test that factory raises ValueError for invalid algorithm."""
        from rainbow_table_generator.hash_functions import hash_factory
        
        with pytest.raises(ValueError) as exc_info:
            hash_factory("invalid_algorithm")
        
        assert "Unsupported hash algorithm" in str(exc_info.value)
        assert "invalid_algorithm" in str(exc_info.value)
    
    def test_factory_empty_string_raises_error(self):
        """Test that factory raises ValueError for empty string."""
        from rainbow_table_generator.hash_functions import hash_factory
        
        with pytest.raises(ValueError) as exc_info:
            hash_factory("")
        
        assert "Unsupported hash algorithm" in str(exc_info.value)
    
    def test_factory_created_hash_functions_work(self):
        """Test that hash functions created by factory work correctly."""
        from rainbow_table_generator.hash_functions import hash_factory
        
        md5_func = hash_factory("md5")
        sha1_func = hash_factory("sha1")
        sha256_func = hash_factory("sha256")
        
        # Test that they can hash a password
        md5_result = md5_func.hash_hex("test")
        sha1_result = sha1_func.hash_hex("test")
        sha256_result = sha256_func.hash_hex("test")
        
        # Verify correct lengths
        assert len(md5_result) == 32  # MD5 hex is 32 characters
        assert len(sha1_result) == 40  # SHA-1 hex is 40 characters
        assert len(sha256_result) == 64  # SHA-256 hex is 64 characters
