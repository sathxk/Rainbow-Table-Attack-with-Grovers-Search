"""
Hash function wrappers for rainbow table generation.

This module provides an abstract base class for hash functions and concrete
implementations for MD5, SHA-1, SHA-256, and NTLM hash algorithms.
"""

from abc import ABC, abstractmethod


class HashFunction(ABC):
    """
    Abstract base class for hash functions used in rainbow table generation.
    
    This class defines the interface that all hash function implementations
    must follow. Concrete implementations should override the hash() method
    to provide specific hash algorithm functionality.
    
    The hash function is used in two main contexts:
    1. Rainbow table construction: Computing hashes of candidate passwords
    2. Grover Oracle construction: Supporting quantum search operations
    
    Attributes:
        algorithm_name: String identifier for the hash algorithm (e.g., 'md5', 'sha1')
    """
    
    def __init__(self, algorithm_name: str):
        """
        Initialize the hash function with an algorithm name.
        
        Args:
            algorithm_name: String identifier for the hash algorithm
        """
        self.algorithm_name = algorithm_name
    
    @abstractmethod
    def hash(self, password: str) -> bytes:
        """
        Compute the hash of a password string.
        
        This method must be implemented by concrete hash function classes.
        It takes a password string as input and returns the hash digest as bytes.
        
        Args:
            password: The password string to hash
            
        Returns:
            The hash digest as bytes
            
        Raises:
            NotImplementedError: If called on the abstract base class
        """
        pass
    
    def hash_hex(self, password: str) -> str:
        """
        Compute the hash of a password and return as hexadecimal string.
        
        This is a convenience method that calls hash() and converts the
        result to a hexadecimal string representation.
        
        Args:
            password: The password string to hash
            
        Returns:
            The hash digest as a lowercase hexadecimal string
        """
        return self.hash(password).hex()
    
    def __repr__(self) -> str:
        """Return string representation of the hash function."""
        return f"{self.__class__.__name__}(algorithm_name={self.algorithm_name!r})"


class MD5HashFunction(HashFunction):
    """
    MD5 hash function implementation.
    
    This class provides MD5 hashing functionality for rainbow table generation.
    MD5 produces a 128-bit (16-byte) hash value.
    
    Note: MD5 is cryptographically broken and should not be used for security
    purposes. It is included here for educational and legacy system compatibility.
    """
    
    def __init__(self):
        """Initialize the MD5 hash function."""
        super().__init__(algorithm_name='md5')
    
    def hash(self, password: str) -> bytes:
        """
        Compute the MD5 hash of a password string.
        
        Args:
            password: The password string to hash
            
        Returns:
            The MD5 hash digest as bytes (16 bytes)
        """
        import hashlib
        return hashlib.md5(password.encode('utf-8')).digest()


class SHA1HashFunction(HashFunction):
    """
    SHA-1 hash function implementation.
    
    This class provides SHA-1 hashing functionality for rainbow table generation.
    SHA-1 produces a 160-bit (20-byte) hash value.
    
    Note: SHA-1 is cryptographically broken and should not be used for security
    purposes. It is included here for educational and legacy system compatibility.
    """
    
    def __init__(self):
        """Initialize the SHA-1 hash function."""
        super().__init__(algorithm_name='sha1')
    
    def hash(self, password: str) -> bytes:
        """
        Compute the SHA-1 hash of a password string.
        
        Args:
            password: The password string to hash
            
        Returns:
            The SHA-1 hash digest as bytes (20 bytes)
        """
        import hashlib
        return hashlib.sha1(password.encode('utf-8')).digest()


class SHA256HashFunction(HashFunction):
    """
    SHA-256 hash function implementation.
    
    This class provides SHA-256 hashing functionality for rainbow table generation.
    SHA-256 produces a 256-bit (32-byte) hash value.
    
    SHA-256 is part of the SHA-2 family and is currently considered
    cryptographically secure for most applications.
    """
    
    def __init__(self):
        """Initialize the SHA-256 hash function."""
        super().__init__(algorithm_name='sha256')
    
    def hash(self, password: str) -> bytes:
        """
        Compute the SHA-256 hash of a password string.
        
        Args:
            password: The password string to hash
            
        Returns:
            The SHA-256 hash digest as bytes (32 bytes)
        """
        import hashlib
        return hashlib.sha256(password.encode('utf-8')).digest()



def hash_factory(algorithm_name: str) -> HashFunction:
    """
    Factory function to instantiate hash functions by name.
    
    This function provides a convenient way to create hash function instances
    based on a string identifier. It supports all hash algorithms implemented
    in this module.
    
    Args:
        algorithm_name: String identifier for the hash algorithm.
                       Supported values: 'md5', 'sha1', 'sha256'
                       (case-insensitive)
    
    Returns:
        An instance of the appropriate HashFunction subclass
    
    Raises:
        ValueError: If the algorithm_name is not supported
    
    Example:
        >>> hash_func = hash_factory('md5')
        >>> hash_func.hash_hex('password')
        '5f4dcc3b5aa765d61d8327deb882cf99'
    """
    algorithm_name_lower = algorithm_name.lower()
    
    if algorithm_name_lower == 'md5':
        return MD5HashFunction()
    elif algorithm_name_lower == 'sha1':
        return SHA1HashFunction()
    elif algorithm_name_lower == 'sha256':
        return SHA256HashFunction()
    else:
        raise ValueError(
            f"Unsupported hash algorithm: {algorithm_name}. "
            f"Supported algorithms: md5, sha1, sha256"
        )
