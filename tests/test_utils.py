"""
Unit tests for utility functions module.
"""

import pytest
import tempfile
import os
from rainbow_table_generator.utils import stream_wordset, count_wordset_lines


class TestStreamWordset:
    """Tests for stream_wordset generator function."""
    
    def test_stream_valid_passwords(self):
        """Test streaming passwords with correct length."""
        # Create a temporary wordset file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("testpass\n")
            f.write("abcd1234\n")
            temp_path = f.name
        
        try:
            # Stream passwords with expected length 8
            passwords = list(stream_wordset(temp_path, expected_length=8))
            
            # Should yield all three passwords
            assert len(passwords) == 3
            assert "password" in passwords
            assert "testpass" in passwords
            assert "abcd1234" in passwords
        finally:
            os.unlink(temp_path)
    
    def test_filter_by_length(self):
        """Test that passwords with incorrect length are filtered out."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("short\n")      # length 5
            f.write("password\n")   # length 8
            f.write("toolong123\n") # length 10
            f.write("testpass\n")   # length 8
            temp_path = f.name
        
        try:
            # Stream passwords with expected length 8
            passwords = list(stream_wordset(temp_path, expected_length=8))
            
            # Should only yield passwords with length 8
            assert len(passwords) == 2
            assert "password" in passwords
            assert "testpass" in passwords
            assert "short" not in passwords
            assert "toolong123" not in passwords
        finally:
            os.unlink(temp_path)
    
    def test_strip_whitespace(self):
        """Test that whitespace is properly stripped from passwords."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("  password  \n")
            f.write("\ttestpass\t\n")
            f.write("abcd1234  \n")
            temp_path = f.name
        
        try:
            passwords = list(stream_wordset(temp_path, expected_length=8))
            
            # All passwords should be stripped of whitespace
            assert len(passwords) == 3
            assert "password" in passwords
            assert "testpass" in passwords
            assert "abcd1234" in passwords
            # Verify no whitespace in results
            for pwd in passwords:
                assert pwd == pwd.strip()
        finally:
            os.unlink(temp_path)
    
    def test_empty_file(self):
        """Test streaming from an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            passwords = list(stream_wordset(temp_path, expected_length=8))
            assert len(passwords) == 0
        finally:
            os.unlink(temp_path)
    
    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            list(stream_wordset("nonexistent_file.txt", expected_length=8))
    
    def test_generator_behavior(self):
        """Test that stream_wordset returns a generator."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            temp_path = f.name
        
        try:
            result = stream_wordset(temp_path, expected_length=8)
            # Should be a generator
            assert hasattr(result, '__iter__')
            assert hasattr(result, '__next__')
        finally:
            os.unlink(temp_path)
    
    def test_large_file_memory_efficiency(self):
        """Test that large files are processed line-by-line (memory efficient)."""
        # Create a file with many passwords
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for i in range(10000):
                f.write(f"pass{i:04d}\n")
            temp_path = f.name
        
        try:
            # Process using generator - should not load entire file into memory
            count = 0
            for password in stream_wordset(temp_path, expected_length=8):
                count += 1
                # Only passwords with exactly 8 characters
                assert len(password) == 8
            
            # Passwords from pass0000 to pass9999 all have length 8
            assert count == 10000
        finally:
            os.unlink(temp_path)
    
    def test_empty_lines_ignored(self):
        """Test that empty lines are filtered out."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("\n")
            f.write("testpass\n")
            f.write("   \n")
            f.write("abcd1234\n")
            temp_path = f.name
        
        try:
            passwords = list(stream_wordset(temp_path, expected_length=8))
            
            # Empty lines should be filtered out (length 0 != 8)
            assert len(passwords) == 3
            assert "" not in passwords
        finally:
            os.unlink(temp_path)


class TestCountWordsetLines:
    """Tests for count_wordset_lines function."""
    
    def test_count_basic_file(self):
        """Test counting lines in a basic file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("testpass\n")
            f.write("abcd1234\n")
            temp_path = f.name
        
        try:
            count = count_wordset_lines(temp_path)
            assert count == 3
        finally:
            os.unlink(temp_path)
    
    def test_count_empty_file(self):
        """Test counting lines in an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name
        
        try:
            count = count_wordset_lines(temp_path)
            assert count == 0
        finally:
            os.unlink(temp_path)
    
    def test_count_file_with_empty_lines(self):
        """Test counting lines including empty lines."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("\n")
            f.write("testpass\n")
            f.write("   \n")
            f.write("abcd1234\n")
            temp_path = f.name
        
        try:
            count = count_wordset_lines(temp_path)
            # Should count all lines including empty ones
            assert count == 5
        finally:
            os.unlink(temp_path)
    
    def test_count_large_file(self):
        """Test counting lines in a large file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for i in range(10000):
                f.write(f"password{i}\n")
            temp_path = f.name
        
        try:
            count = count_wordset_lines(temp_path)
            assert count == 10000
        finally:
            os.unlink(temp_path)
    
    def test_count_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        with pytest.raises(FileNotFoundError):
            count_wordset_lines("nonexistent_file.txt")
    
    def test_count_file_without_trailing_newline(self):
        """Test counting lines in a file without trailing newline."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("testpass\n")
            f.write("abcd1234")  # No trailing newline
            temp_path = f.name
        
        try:
            count = count_wordset_lines(temp_path)
            assert count == 3
        finally:
            os.unlink(temp_path)
    
    def test_count_single_line(self):
        """Test counting a file with a single line."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            temp_path = f.name
        
        try:
            count = count_wordset_lines(temp_path)
            assert count == 1
        finally:
            os.unlink(temp_path)


class TestResumeFromCheckpoint:
    """Tests for resume_from_checkpoint function."""

    def test_resume_from_middle(self):
        """Test resuming from a checkpoint in the middle of the file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("testpass\n")
            f.write("abcd1234\n")
            f.write("qwerty12\n")
            f.write("zxcvbnm0\n")
            temp_path = f.name

        try:
            from rainbow_table_generator.utils import resume_from_checkpoint

            # Resume from "testpass" - should yield passwords after it
            passwords = list(resume_from_checkpoint(temp_path, expected_length=8,
                                                   last_start_point="testpass"))

            assert len(passwords) == 3
            assert "abcd1234" in passwords
            assert "qwerty12" in passwords
            assert "zxcvbnm0" in passwords
            assert "password" not in passwords
            assert "testpass" not in passwords
        finally:
            os.unlink(temp_path)

    def test_resume_from_first(self):
        """Test resuming from the first password."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("testpass\n")
            f.write("abcd1234\n")
            temp_path = f.name

        try:
            from rainbow_table_generator.utils import resume_from_checkpoint

            # Resume from first password
            passwords = list(resume_from_checkpoint(temp_path, expected_length=8,
                                                   last_start_point="password"))

            assert len(passwords) == 2
            assert "testpass" in passwords
            assert "abcd1234" in passwords
            assert "password" not in passwords
        finally:
            os.unlink(temp_path)

    def test_resume_from_last(self):
        """Test resuming from the last password (should yield nothing)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("testpass\n")
            f.write("abcd1234\n")
            temp_path = f.name

        try:
            from rainbow_table_generator.utils import resume_from_checkpoint

            # Resume from last password - should yield nothing
            passwords = list(resume_from_checkpoint(temp_path, expected_length=8,
                                                   last_start_point="abcd1234"))

            assert len(passwords) == 0
        finally:
            os.unlink(temp_path)

    def test_resume_checkpoint_not_found(self):
        """Test resuming when checkpoint password is not in file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("testpass\n")
            f.write("abcd1234\n")
            temp_path = f.name

        try:
            from rainbow_table_generator.utils import resume_from_checkpoint

            # Resume from non-existent password - should yield nothing
            passwords = list(resume_from_checkpoint(temp_path, expected_length=8,
                                                   last_start_point="notfound"))

            assert len(passwords) == 0
        finally:
            os.unlink(temp_path)

    def test_resume_with_length_filtering(self):
        """Test that resume still filters by password length."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")   # length 8
            f.write("short\n")      # length 5
            f.write("testpass\n")   # length 8
            f.write("toolong123\n") # length 10
            f.write("abcd1234\n")   # length 8
            temp_path = f.name

        try:
            from rainbow_table_generator.utils import resume_from_checkpoint

            # Resume from "password" with length filter
            passwords = list(resume_from_checkpoint(temp_path, expected_length=8,
                                                   last_start_point="password"))

            # Should only yield valid length passwords after checkpoint
            assert len(passwords) == 2
            assert "testpass" in passwords
            assert "abcd1234" in passwords
            assert "short" not in passwords
            assert "toolong123" not in passwords
        finally:
            os.unlink(temp_path)

    def test_resume_with_whitespace(self):
        """Test that resume handles whitespace correctly."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("  password  \n")
            f.write("testpass\n")
            f.write("  abcd1234\n")
            temp_path = f.name

        try:
            from rainbow_table_generator.utils import resume_from_checkpoint

            # Resume from "password" (stripped)
            passwords = list(resume_from_checkpoint(temp_path, expected_length=8,
                                                   last_start_point="password"))

            assert len(passwords) == 2
            assert "testpass" in passwords
            assert "abcd1234" in passwords
        finally:
            os.unlink(temp_path)

    def test_resume_generator_behavior(self):
        """Test that resume_from_checkpoint returns a generator."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("password\n")
            f.write("testpass\n")
            temp_path = f.name

        try:
            from rainbow_table_generator.utils import resume_from_checkpoint

            result = resume_from_checkpoint(temp_path, expected_length=8,
                                          last_start_point="password")

            # Should be a generator
            assert hasattr(result, '__iter__')
            assert hasattr(result, '__next__')
        finally:
            os.unlink(temp_path)

    def test_resume_empty_file(self):
        """Test resuming from an empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name

        try:
            from rainbow_table_generator.utils import resume_from_checkpoint

            passwords = list(resume_from_checkpoint(temp_path, expected_length=8,
                                                   last_start_point="password"))

            assert len(passwords) == 0
        finally:
            os.unlink(temp_path)

    def test_resume_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        from rainbow_table_generator.utils import resume_from_checkpoint

        with pytest.raises(FileNotFoundError):
            list(resume_from_checkpoint("nonexistent_file.txt", expected_length=8,
                                       last_start_point="password"))

