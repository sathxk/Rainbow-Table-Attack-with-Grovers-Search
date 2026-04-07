"""
Reduction function module for rainbow table generation.

This module provides the reduction function that maps hash values back to
password candidates. The reduction function is a critical component of rainbow
table construction, enabling the creation of hash chains.
"""

# Character set for password generation: lowercase letters (a-z) and digits (0-9)
CHARSET = "abcdefghijklmnopqrstuvwxyz0123456789"

def reduce(hash_value: bytes, iteration: int, password_length: int) -> str:
    """
    Reduce a hash value to a password candidate.
    
    The reduction function maps hash values back to the password space. It is
    iteration-dependent to ensure different reduction functions at each step
    of the rainbow table chain, preventing chain merging.
    
    Args:
        hash_value: The hash digest as bytes
        iteration: The iteration index in the chain (0-based)
        password_length: The desired length of the output password
        
    Returns:
        A password string of the specified length using characters from CHARSET
        
    Example:
        >>> import hashlib
        >>> hash_val = hashlib.md5(b"password").digest()
        >>> pwd = reduce(hash_val, 0, 8)
        >>> len(pwd)
        8
        >>> all(c in CHARSET for c in pwd)
        True
    """
    # 4.2.1: Combine hash with iteration index
    # Convert iteration to bytes and concatenate with hash
    iteration_bytes = iteration.to_bytes(4, byteorder='big')
    combined = hash_value + iteration_bytes
    
    # 4.2.2: Convert to integer for modulo operations
    # Convert the combined bytes to a large integer
    combined_int = int.from_bytes(combined, byteorder='big')
    
    # 4.2.3: Generate password by selecting characters from charset
    # Use modulo operations to select characters from the charset
    password = []
    charset_len = len(CHARSET)
    
    for _ in range(password_length):
        # Select character based on current value
        char_index = combined_int % charset_len
        password.append(CHARSET[char_index])
        # Shift to next character position
        combined_int //= charset_len
    
    return ''.join(password)

def validate_password(password: str, expected_length: int) -> bool:
    """
    Validate that a password conforms to the required constraints.

    Checks that the password:
    1. Has the expected length
    2. Contains only characters from CHARSET

    Args:
        password: The password string to validate
        expected_length: The expected length of the password

    Returns:
        True if the password is valid, False otherwise

    Example:
        >>> validate_password("abc123", 6)
        True
        >>> validate_password("abc123", 8)
        False
        >>> validate_password("abc@123", 7)
        False
    """
    # Check password length
    if len(password) != expected_length:
        return False

    # Check all characters are in CHARSET
    if not all(c in CHARSET for c in password):
        return False

    return True

