"""
Utility functions for the Rainbow Table Generator.
"""

from typing import Generator


def stream_wordset(filepath: str, expected_length: int) -> Generator[str, None, None]:
    """
    Stream passwords from a PCFG wordset file.
    
    This function reads passwords line-by-line from a wordset file, validates
    each password's length, and yields valid passwords as a generator. This
    approach is memory-efficient for large wordset files.
    
    Args:
        filepath: Path to the wordset file
        expected_length: Expected password length for validation
        
    Yields:
        Valid password strings that match the expected length
        
    Raises:
        FileNotFoundError: If the wordset file doesn't exist
        IOError: If there's an error reading the file
    """
    # Sub-task 6.1.1: Open file and read line-by-line
    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            # Sub-task 6.1.2: Strip whitespace from each line
            password = line.strip()
            
            # Sub-task 6.1.3: Validate password length matches expected
            if len(password) == expected_length:
                # Sub-task 6.1.4: Yield valid passwords
                yield password


def count_wordset_lines(filepath: str) -> int:
    """
    Count the total number of lines in a wordset file.
    
    This function efficiently counts lines in a wordset file without loading
    the entire file into memory. It's used for progress tracking and ETA
    calculations during rainbow table generation.
    
    Args:
        filepath: Path to the wordset file
        
    Returns:
        Total number of lines in the file
        
    Raises:
        FileNotFoundError: If the wordset file doesn't exist
        IOError: If there's an error reading the file
    """
    count = 0
    with open(filepath, 'r', encoding='utf-8') as file:
        for _ in file:
            count += 1
    return count


def resume_from_checkpoint(filepath: str, expected_length: int,
                          last_start_point: str) -> Generator[str, None, None]:
    """
    Stream passwords from a wordset file, skipping already processed passwords.

    This function resumes password streaming from a checkpoint by skipping all
    passwords up to and including the last processed start point. This enables
    resumption of rainbow table generation after interruption.

    Args:
        filepath: Path to the wordset file
        expected_length: Expected password length for validation
        last_start_point: Last password that was processed (from checkpoint)

    Yields:
        Valid password strings that match the expected length, starting after
        the last_start_point

    Raises:
        FileNotFoundError: If the wordset file doesn't exist
        IOError: If there's an error reading the file
    """
    found_checkpoint = False

    with open(filepath, 'r', encoding='utf-8') as file:
        for line in file:
            password = line.strip()

            # Validate password length
            if len(password) != expected_length:
                continue

            # Skip until we find the checkpoint
            if not found_checkpoint:
                if password == last_start_point:
                    found_checkpoint = True
                continue

            # Yield passwords after checkpoint
            yield password

