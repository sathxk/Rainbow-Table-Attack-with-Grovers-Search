"""
Chain generator module for rainbow table generation.

This module provides the ChainGenerator class that implements hash-reduction
chain generation logic. Chains are sequences of alternating hash and reduction
operations that form the basis of rainbow table construction.
"""

from typing import Tuple, Callable
from rainbow_table_generator.hash_functions import HashFunction


class ChainGenerator:
    """
    Generator for hash-reduction chains in rainbow table construction.
    
    A chain is a sequence of alternating hash and reduction operations:
    password -> hash -> reduce -> password -> hash -> reduce -> ...
    
    The chain starts with a start_point (initial password) and ends with an
    end_point (final password after chain_length iterations). Only the
    start_point and end_point are stored in the rainbow table, allowing
    space-efficient storage while maintaining the ability to reconstruct
    intermediate values.
    
    Attributes:
        hash_function: HashFunction instance for computing password hashes
        chain_length: Number of hash-reduce iterations per chain
        password_length: Length of passwords in the chain
    """
    
    def __init__(
        self,
        hash_function: HashFunction,
        chain_length: int,
        password_length: int
    ):
        """
        Initialize the ChainGenerator with hash function and chain parameters.
        
        Args:
            hash_function: HashFunction instance for hashing passwords
            chain_length: Number of hash-reduce iterations per chain
            password_length: Length of passwords to generate in reduction step
            
        Raises:
            ValueError: If chain_length is not positive or password_length is invalid
        """
        if chain_length < 1:
            raise ValueError(
                f"chain_length must be positive, got {chain_length}"
            )
        
        if password_length < 1:
            raise ValueError(
                f"password_length must be positive, got {password_length}"
            )
        
        self.hash_function = hash_function
        self.chain_length = chain_length
        self.password_length = password_length
    
    def __repr__(self) -> str:
        """Return string representation of ChainGenerator."""
        return (
            f"ChainGenerator("
            f"hash_function={self.hash_function!r}, "
            f"chain_length={self.chain_length}, "
            f"password_length={self.password_length})"
        )


    def generate_chain(
        self,
        start_point: str,
        reduce_func: Callable[[bytes, int, int], str]
    ) -> Tuple[str, str]:
        """
        Generate a hash-reduction chain from a starting password.

        This method creates a chain by alternating hash and reduction operations:
        start_point -> hash -> reduce -> hash -> reduce -> ... -> end_point

        The chain performs chain_length iterations, where each iteration consists
        of hashing the current password and then reducing the hash to get the
        next password. Only the start_point and end_point are returned.

        Args:
            start_point: The initial password to start the chain
            reduce_func: Reduction function with signature (hash_bytes, iteration, length) -> password

        Returns:
            A tuple (start_point, end_point) where end_point is the final password
            after chain_length hash-reduce iterations

        Raises:
            ValueError: If start_point is empty or invalid
            TypeError: If reduce_func is not callable or returns invalid type
            RuntimeError: If chain generation fails due to hash or reduction errors

        Example:
            >>> from rainbow_table_generator.hash_functions import MD5HashFunction
            >>> from rainbow_table_generator.reduction import reduce
            >>> hash_func = MD5HashFunction()
            >>> gen = ChainGenerator(hash_func, chain_length=100, password_length=8)
            >>> start, end = gen.generate_chain("password", reduce)
            >>> len(end)
            8
        """
        # Validate start_point
        if not start_point:
            raise ValueError("start_point cannot be empty")
        
        if not isinstance(start_point, str):
            raise TypeError(
                f"start_point must be a string, got {type(start_point).__name__}"
            )
        
        # Validate reduce_func
        if not callable(reduce_func):
            raise TypeError("reduce_func must be callable")
        
        try:
            # Start with the initial password
            current_password = start_point

            # Iterate chain_length times: hash -> reduce
            for iteration in range(self.chain_length):
                try:
                    # Hash the current password
                    hash_value = self.hash_function.hash(current_password)
                    
                    # Validate hash output
                    if not isinstance(hash_value, bytes):
                        raise RuntimeError(
                            f"Hash function returned invalid type {type(hash_value).__name__}, "
                            f"expected bytes at iteration {iteration}"
                        )
                    
                    if len(hash_value) == 0:
                        raise RuntimeError(
                            f"Hash function returned empty bytes at iteration {iteration}"
                        )
                    
                except Exception as e:
                    raise RuntimeError(
                        f"Hash operation failed at iteration {iteration} "
                        f"with password '{current_password}': {str(e)}"
                    ) from e
                
                try:
                    # Reduce the hash to get the next password
                    current_password = reduce_func(hash_value, iteration, self.password_length)
                    
                    # Validate reduction output
                    if not isinstance(current_password, str):
                        raise RuntimeError(
                            f"Reduction function returned invalid type {type(current_password).__name__}, "
                            f"expected str at iteration {iteration}"
                        )
                    
                    if not current_password:
                        raise RuntimeError(
                            f"Reduction function returned empty string at iteration {iteration}"
                        )
                    
                    if len(current_password) != self.password_length:
                        raise RuntimeError(
                            f"Reduction function returned password of length {len(current_password)}, "
                            f"expected {self.password_length} at iteration {iteration}"
                        )
                    
                except RuntimeError:
                    # Re-raise RuntimeError from validation
                    raise
                except Exception as e:
                    raise RuntimeError(
                        f"Reduction operation failed at iteration {iteration}: {str(e)}"
                    ) from e

            # Return (start_point, end_point) tuple
            end_point = current_password
            return (start_point, end_point)
            
        except (ValueError, TypeError, RuntimeError):
            # Re-raise expected exceptions
            raise
        except Exception as e:
            # Catch any unexpected exceptions
            raise RuntimeError(
                f"Unexpected error during chain generation: {str(e)}"
            ) from e

