"""
Unit tests for bucket organizer module.
"""

import pytest
from rainbow_table_generator.bucket_organizer import BucketOrganizer


class TestBucketOrganizer:
    """Tests for BucketOrganizer class."""
    
    def test_initialization_valid_parameters(self):
        """Test BucketOrganizer initialization with valid parameters."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        assert organizer.qubit_count == 4
        assert organizer.bucket_size == 16
        assert organizer.num_buckets == 63  # ceil(1000 / 16)
        assert len(organizer.buckets) == 0  # Empty initially
    
    def test_initialization_different_qubit_counts(self):
        """Test BucketOrganizer with different qubit counts."""
        # Test qubit_count=3 -> bucket_size=8
        organizer3 = BucketOrganizer(qubit_count=3, total_entries=1000)
        assert organizer3.bucket_size == 8
        assert organizer3.num_buckets == 125  # ceil(1000 / 8)
        
        # Test qubit_count=5 -> bucket_size=32
        organizer5 = BucketOrganizer(qubit_count=5, total_entries=1000)
        assert organizer5.bucket_size == 32
        assert organizer5.num_buckets == 32  # ceil(1000 / 32)
        
        # Test qubit_count=6 -> bucket_size=64
        organizer6 = BucketOrganizer(qubit_count=6, total_entries=1000)
        assert organizer6.bucket_size == 64
        assert organizer6.num_buckets == 16  # ceil(1000 / 64)
    
    def test_initialization_large_dataset(self):
        """Test BucketOrganizer with large dataset (38M entries)."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=38285441)
        assert organizer.bucket_size == 16
        assert organizer.num_buckets == 2392841  # ceil(38285441 / 16)
    
    def test_initialization_invalid_qubit_count(self):
        """Test BucketOrganizer initialization with invalid qubit count."""
        with pytest.raises(ValueError, match="qubit_count must be positive"):
            BucketOrganizer(qubit_count=0, total_entries=1000)
        
        with pytest.raises(ValueError, match="qubit_count must be positive"):
            BucketOrganizer(qubit_count=-1, total_entries=1000)
    
    def test_initialization_invalid_total_entries(self):
        """Test BucketOrganizer initialization with invalid total_entries."""
        with pytest.raises(ValueError, match="total_entries must be positive"):
            BucketOrganizer(qubit_count=4, total_entries=0)
        
        with pytest.raises(ValueError, match="total_entries must be positive"):
            BucketOrganizer(qubit_count=4, total_entries=-1)
    
    def test_repr(self):
        """Test string representation of BucketOrganizer."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        repr_str = repr(organizer)
        assert "BucketOrganizer" in repr_str
        assert "qubit_count=4" in repr_str
        assert "bucket_size=16" in repr_str
        assert "num_buckets=63" in repr_str


class TestAssignBucket:
    """Tests for assign_bucket method."""
    
    def test_assign_bucket_valid_endpoint(self):
        """Test bucket assignment with valid MD5 endpoint."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Test with MD5 hash
        endpoint = "5f4dcc3b5aa765d61d8327deb882cf99"
        bucket_idx = organizer.assign_bucket(endpoint)
        assert 0 <= bucket_idx < organizer.num_buckets
    
    def test_assign_bucket_deterministic(self):
        """Test that bucket assignment is deterministic."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        endpoint = "5f4dcc3b5aa765d61d8327deb882cf99"
        bucket_idx1 = organizer.assign_bucket(endpoint)
        bucket_idx2 = organizer.assign_bucket(endpoint)
        
        assert bucket_idx1 == bucket_idx2
    
    def test_assign_bucket_uses_md5_directly(self):
        """Test that bucket assignment uses MD5 hash directly."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Test with known MD5 hash
        endpoint = "5f4dcc3b5aa765d61d8327deb882cf99"
        
        # Calculate expected bucket_key
        hash_value = int(endpoint[:8], 16)  # "5f4dcc3b" = 1598906427
        expected_bucket = hash_value % organizer.num_buckets
        
        actual_bucket = organizer.assign_bucket(endpoint)
        assert actual_bucket == expected_bucket
    
    def test_assign_bucket_distribution(self):
        """Test that bucket assignment distributes across buckets."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=10000)
        
        # Generate different MD5-like endpoints
        import hashlib
        endpoints = []
        for i in range(100):
            password = f"password{i}"
            hash_value = hashlib.md5(password.encode()).hexdigest()
            endpoints.append(hash_value)
        
        bucket_indices = [organizer.assign_bucket(ep) for ep in endpoints]
        
        # Check that we get different bucket indices
        unique_buckets = set(bucket_indices)
        assert len(unique_buckets) > 1  # Should distribute across multiple buckets
    
    def test_assign_bucket_empty_endpoint(self):
        """Test bucket assignment with empty endpoint."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        with pytest.raises(ValueError, match="end_point cannot be empty"):
            organizer.assign_bucket("")
    
    def test_assign_bucket_invalid_hex(self):
        """Test bucket assignment with invalid hex string."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        with pytest.raises(ValueError, match="valid hexadecimal string"):
            organizer.assign_bucket("not_a_hex_string")
    
    def test_assign_bucket_short_endpoint(self):
        """Test bucket assignment with short endpoint (< 8 chars)."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Should work with short hex strings (pads with zeros conceptually)
        endpoint = "abc123"
        bucket_idx = organizer.assign_bucket(endpoint)
        assert 0 <= bucket_idx < organizer.num_buckets


class TestAddToBucket:
    """Tests for add_to_bucket method."""
    
    def test_add_to_bucket_single_entry(self):
        """Test adding a single SP-EP pair to bucket."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        start_point = "password"
        end_point = "5f4dcc3b5aa765d61d8327deb882cf99"
        
        organizer.add_to_bucket(start_point, end_point)
        
        # Check that total entries increased
        assert organizer.get_total_entries() == 1
        
        # Check that the pair was added to the correct bucket
        bucket_idx = organizer.assign_bucket(end_point)
        bucket_contents = organizer.get_bucket(bucket_idx)
        assert len(bucket_contents) == 1
        assert bucket_contents[0][0] == start_point
        assert bucket_contents[0][1] == end_point
    
    def test_add_to_bucket_multiple_entries(self):
        """Test adding multiple SP-EP pairs to buckets."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        pairs = [
            ("password1", "5f4dcc3b5aa765d61d8327deb882cf99"),
            ("password2", "6cb75f652a9b52798eb6cf2201057c73"),
            ("password3", "819b0643d6b89dc9b579fdfc9094f28e"),
        ]
        
        for sp, ep in pairs:
            organizer.add_to_bucket(sp, ep)
        
        assert organizer.get_total_entries() == 3
    
    def test_add_to_bucket_empty_start_point(self):
        """Test adding entry with empty start point."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        with pytest.raises(ValueError, match="start_point cannot be empty"):
            organizer.add_to_bucket("", "5f4dcc3b5aa765d61d8327deb882cf99")
    
    def test_add_to_bucket_invalid_end_point(self):
        """Test adding entry with invalid end point."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        with pytest.raises(ValueError):
            organizer.add_to_bucket("password", "")


class TestGetBucketCounts:
    """Tests for get_bucket_counts method."""
    
    def test_get_bucket_counts_empty(self):
        """Test getting bucket counts when all buckets are empty."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        counts = organizer.get_bucket_counts()
        
        assert len(counts) == 0  # No buckets have data yet
    
    def test_get_bucket_counts_with_entries(self):
        """Test getting bucket counts after adding entries."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Add entries
        organizer.add_to_bucket("password1", "5f4dcc3b5aa765d61d8327deb882cf99")
        organizer.add_to_bucket("password2", "6cb75f652a9b52798eb6cf2201057c73")
        organizer.add_to_bucket("password3", "5f4dcc3b5aa765d61d8327deb882cf99")  # Same bucket as password1
        
        counts = organizer.get_bucket_counts()
        
        # Should have entries in buckets
        assert sum(counts.values()) == 3


class TestBucketManagement:
    """Tests for bucket management methods."""
    
    def test_get_bucket_valid_key(self):
        """Test getting bucket contents with valid key."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        endpoint = "10000000"  # Will map to some bucket
        organizer.add_to_bucket("password", endpoint)
        
        bucket_key = organizer.assign_bucket(endpoint)
        bucket_contents = organizer.get_bucket(bucket_key)
        assert len(bucket_contents) == 1
        assert bucket_contents[0][0] == "password"
        assert bucket_contents[0][1] == endpoint
        assert isinstance(bucket_contents[0][2], int)  # intra_value
    
    def test_get_bucket_nonexistent_key(self):
        """Test getting bucket with nonexistent key returns empty list."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Get a bucket that has no entries
        bucket_contents = organizer.get_bucket(999)
        assert bucket_contents == []
    
    def test_clear_bucket(self):
        """Test clearing a specific bucket."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        ep1 = "10000000"
        ep2 = "20000000"
        organizer.add_to_bucket("password1", ep1)
        organizer.add_to_bucket("password2", ep2)
        
        bucket_key1 = organizer.assign_bucket(ep1)
        bucket_key2 = organizer.assign_bucket(ep2)
        
        assert len(organizer.get_bucket(bucket_key1)) >= 1
        
        organizer.clear_bucket(bucket_key1)
        
        assert len(organizer.get_bucket(bucket_key1)) == 0
        # Other bucket should be unaffected if different
        if bucket_key1 != bucket_key2:
            assert len(organizer.get_bucket(bucket_key2)) == 1
    
    def test_clear_all_buckets(self):
        """Test clearing all buckets."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Add entries to multiple buckets
        organizer.add_to_bucket("password1", "10000000")
        organizer.add_to_bucket("password2", "20000000")
        organizer.add_to_bucket("password3", "30000000")
        
        assert organizer.get_total_entries() == 3
        
        organizer.clear_all_buckets()
        
        assert organizer.get_total_entries() == 0
        assert len(organizer.buckets) == 0
    
    def test_get_total_entries(self):
        """Test getting total entries across all buckets."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        assert organizer.get_total_entries() == 0
        
        organizer.add_to_bucket("password1", "10000000")
        assert organizer.get_total_entries() == 1
        
        organizer.add_to_bucket("password2", "20000000")
        assert organizer.get_total_entries() == 2
        
        organizer.add_to_bucket("password3", "30000000")
        assert organizer.get_total_entries() == 3
    
    def test_all_bucket_keys(self):
        """Test getting all active bucket keys."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Initially no buckets
        assert organizer.all_bucket_keys() == []
        
        # Add entries
        organizer.add_to_bucket("password1", "10000000")
        organizer.add_to_bucket("password2", "20000000")
        
        # Should have bucket keys now
        keys = organizer.all_bucket_keys()
        assert len(keys) >= 1
        assert all(isinstance(k, int) for k in keys)


class TestBucketAssignmentDistribution:
    """Tests for bucket assignment distribution."""
    
    def test_distribution_uniform_across_buckets(self):
        """Test that endpoints are distributed uniformly across buckets."""
        # With 1000 entries and 4 qubits (bucket_size=16), need 63 buckets
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Generate diverse hex values as endpoints using hash function
        import hashlib
        num_endpoints = 1000
        endpoints = []
        for i in range(num_endpoints):
            password = f"password{i}"
            hash_value = hashlib.md5(password.encode()).hexdigest()
            endpoints.append(hash_value)
        
        # Assign all endpoints to buckets
        bucket_assignments = [organizer.assign_bucket(ep) for ep in endpoints]
        
        # Count assignments per bucket
        bucket_counts = {}
        for bucket_key in bucket_assignments:
            bucket_counts[bucket_key] = bucket_counts.get(bucket_key, 0) + 1
        
        # Verify multiple buckets are used
        assert len(bucket_counts) >= 10, "Should use multiple buckets"
        
        # Verify all assignments are within valid range
        assert all(0 <= key < organizer.num_buckets for key in bucket_assignments)
    
    def test_distribution_with_realistic_hashes(self):
        """Test distribution with realistic MD5 hash values."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Simulate realistic hash values (32 hex chars)
        import hashlib
        num_passwords = 500
        endpoints = []
        for i in range(num_passwords):
            password = f"password{i}"
            hash_value = hashlib.md5(password.encode()).hexdigest()
            endpoints.append(hash_value)
        
        # Assign to buckets
        bucket_assignments = [organizer.assign_bucket(ep) for ep in endpoints]
        
        # Verify all bucket keys are valid
        assert all(0 <= key < organizer.num_buckets for key in bucket_assignments)
        
        # Verify multiple buckets are used
        unique_buckets = set(bucket_assignments)
        assert len(unique_buckets) >= 10, \
            f"Expected at least 10 buckets used, got {len(unique_buckets)}"
    
    def test_distribution_modulo_operation_correctness(self):
        """Test that modulo operation correctly distributes endpoints."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Test specific values where we can verify the calculation
        test_cases = [
            "00000000",  # 0
            "0000000f",  # 15
            "00000010",  # 16
            "000000ff",  # 255
        ]
        
        for endpoint in test_cases:
            hash_value = int(endpoint[:8], 16)
            expected_bucket = hash_value % organizer.num_buckets
            actual_bucket = organizer.assign_bucket(endpoint)
            assert actual_bucket == expected_bucket, \
                f"Endpoint {endpoint} should map to bucket {expected_bucket}, got {actual_bucket}"
    
    def test_distribution_different_qubit_counts(self):
        """Test distribution with different qubit counts."""
        # Test with 3 qubits (bucket_size=8, 100 entries -> 13 buckets)
        organizer3 = BucketOrganizer(qubit_count=3, total_entries=100)
        endpoints = [hex(i)[2:].zfill(8) for i in range(100)]
        assignments3 = [organizer3.assign_bucket(ep) for ep in endpoints]
        assert all(0 <= key < organizer3.num_buckets for key in assignments3)
        
        # Test with 5 qubits (bucket_size=32, 100 entries -> 4 buckets)
        organizer5 = BucketOrganizer(qubit_count=5, total_entries=100)
        assignments5 = [organizer5.assign_bucket(ep) for ep in endpoints]
        assert all(0 <= key < organizer5.num_buckets for key in assignments5)
    
    def test_distribution_consistency_across_calls(self):
        """Test that distribution is consistent across multiple organizer instances."""
        organizer1 = BucketOrganizer(qubit_count=4, total_entries=1000)
        organizer2 = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        endpoints = [hex(i)[2:].zfill(32) for i in range(100)]
        
        assignments1 = [organizer1.assign_bucket(ep) for ep in endpoints]
        assignments2 = [organizer2.assign_bucket(ep) for ep in endpoints]
        
        # Both organizers should produce identical assignments
        assert assignments1 == assignments2
    
    def test_distribution_large_dataset(self):
        """Test distribution with large dataset (38M entries)."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=38285441)
        
        # With 38M entries and bucket_size=16, should have ~2.4M buckets
        assert organizer.num_buckets == 2392841
        
        # Test a few assignments
        import hashlib
        for i in range(100):
            password = f"testpass{i}"
            endpoint = hashlib.md5(password.encode()).hexdigest()
            bucket_key = organizer.assign_bucket(endpoint)
            assert 0 <= bucket_key < organizer.num_buckets


class TestBucketBufferManagement:
    """Tests for bucket buffer management."""
    
    def test_buffer_initialization(self):
        """Test that bucket buffers are properly initialized."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Buckets dict should be empty initially (dynamic allocation)
        assert len(organizer.buckets) == 0
        assert organizer.get_total_entries() == 0
    
    def test_buffer_add_single_pair(self):
        """Test adding a single SP-EP pair to buffer."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        sp = "password123"
        ep = "5f4dcc3b5aa765d61d8327deb882cf99"
        
        organizer.add_to_bucket(sp, ep)
        
        # Verify the pair is in the correct bucket
        bucket_key = organizer.assign_bucket(ep)
        bucket_contents = organizer.get_bucket(bucket_key)
        
        assert len(bucket_contents) == 1
        assert bucket_contents[0][0] == sp
        assert bucket_contents[0][1] == ep
        assert isinstance(bucket_contents[0][2], int)  # intra_value
    
    def test_buffer_add_multiple_pairs_same_bucket(self):
        """Test adding multiple SP-EP pairs to the same bucket."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Find endpoints that actually map to the same bucket
        import hashlib
        same_bucket_endpoints = []
        target_bucket = None
        
        # Generate endpoints until we find 3 that map to the same bucket
        i = 0
        while len(same_bucket_endpoints) < 3:
            password = f"testpass{i}"
            ep = hashlib.md5(password.encode()).hexdigest()
            bucket_key = organizer.assign_bucket(ep)
            
            if target_bucket is None:
                target_bucket = bucket_key
                same_bucket_endpoints.append((password, ep))
            elif bucket_key == target_bucket:
                same_bucket_endpoints.append((password, ep))
            
            i += 1
            if i > 10000:  # Safety limit
                break
        
        # Should have found at least 3 endpoints for the same bucket
        assert len(same_bucket_endpoints) >= 3
        
        pairs = same_bucket_endpoints[:3]
        
        for sp, ep in pairs:
            organizer.add_to_bucket(sp, ep)
        
        # All should be in the same bucket
        bucket_contents = organizer.get_bucket(target_bucket)
        assert len(bucket_contents) == 3
        
        # Verify all pairs are present
        for i, (sp, ep) in enumerate(pairs):
            assert bucket_contents[i][0] == sp
            assert bucket_contents[i][1] == ep
    
    def test_buffer_add_multiple_pairs_different_buckets(self):
        """Test adding SP-EP pairs to different buckets."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        pairs = [
            ("password1", "10000000"),
            ("password2", "20000000"),
            ("password3", "30000000"),
            ("password4", "40000000"),
        ]
        
        for sp, ep in pairs:
            organizer.add_to_bucket(sp, ep)
        
        # Verify each pair is in its correct bucket
        for sp, ep in pairs:
            bucket_key = organizer.assign_bucket(ep)
            bucket_contents = organizer.get_bucket(bucket_key)
            # Check that this pair exists in the bucket
            found = any(entry[0] == sp and entry[1] == ep for entry in bucket_contents)
            assert found, f"Pair ({sp}, {ep}) not found in bucket {bucket_key}"
    
    def test_buffer_count_tracking(self):
        """Test that bucket counts are accurately tracked."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Initially all counts should be 0
        counts = organizer.get_bucket_counts()
        assert len(counts) == 0
        
        # Add pairs
        organizer.add_to_bucket("pw1", "10000000")
        organizer.add_to_bucket("pw2", "10000001")  # Same bucket as pw1
        organizer.add_to_bucket("pw3", "20000000")  # Different bucket
        
        counts = organizer.get_bucket_counts()
        assert sum(counts.values()) == 3
        assert organizer.get_total_entries() == 3
    
    def test_buffer_large_volume(self):
        """Test buffer management with large number of entries."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=10000)
        
        # Add 1,000 SP-EP pairs
        num_pairs = 1000
        for i in range(num_pairs):
            sp = f"password{i}"
            ep = hex(i)[2:].zfill(32)
            organizer.add_to_bucket(sp, ep)
        
        # Verify total count
        assert organizer.get_total_entries() == num_pairs
        
        # Verify buckets have entries
        counts = organizer.get_bucket_counts()
        assert len(counts) > 0
        
        # Verify sum of bucket counts equals total
        assert sum(counts.values()) == num_pairs
    
    def test_buffer_clear_and_refill(self):
        """Test clearing buffers and refilling them."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Fill buckets
        for i in range(100):
            organizer.add_to_bucket(f"pw{i}", hex(i)[2:].zfill(8))
        
        initial_total = organizer.get_total_entries()
        assert initial_total == 100
        
        # Clear all buckets
        organizer.clear_all_buckets()
        assert organizer.get_total_entries() == 0
        
        # Refill buckets
        for i in range(50):
            organizer.add_to_bucket(f"newpw{i}", hex(i + 1000)[2:].zfill(8))
        
        assert organizer.get_total_entries() == 50
    
    def test_buffer_selective_clear(self):
        """Test clearing individual buckets while preserving others."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Add entries to different buckets
        ep1 = "10000000"
        ep2 = "20000000"
        ep3 = "30000000"
        
        organizer.add_to_bucket("pw1", ep1)
        organizer.add_to_bucket("pw2", ep2)
        organizer.add_to_bucket("pw3", ep3)
        
        bucket_key1 = organizer.assign_bucket(ep1)
        bucket_key2 = organizer.assign_bucket(ep2)
        
        initial_total = organizer.get_total_entries()
        
        # Clear bucket 1
        organizer.clear_bucket(bucket_key1)
        
        assert len(organizer.get_bucket(bucket_key1)) == 0
        # Other buckets should be preserved
        assert organizer.get_total_entries() < initial_total
    
    def test_buffer_preserves_order(self):
        """Test that buffer preserves insertion order of SP-EP pairs."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Find endpoints that actually map to the same bucket
        import hashlib
        same_bucket_endpoints = []
        target_bucket = None
        
        # Generate endpoints until we find 4 that map to the same bucket
        i = 0
        while len(same_bucket_endpoints) < 4:
            password = f"pass{i}"
            ep = hashlib.md5(password.encode()).hexdigest()
            bucket_key = organizer.assign_bucket(ep)
            
            if target_bucket is None:
                target_bucket = bucket_key
                same_bucket_endpoints.append((password, ep))
            elif bucket_key == target_bucket:
                same_bucket_endpoints.append((password, ep))
            
            i += 1
            if i > 10000:  # Safety limit
                break
        
        # Should have found at least 4 endpoints for the same bucket
        assert len(same_bucket_endpoints) >= 4
        
        pairs = same_bucket_endpoints[:4]
        
        for sp, ep in pairs:
            organizer.add_to_bucket(sp, ep)
        
        # Retrieve bucket contents
        bucket_contents = organizer.get_bucket(target_bucket)
        
        # Verify order is preserved
        assert len(bucket_contents) == 4
        for i, (sp, ep) in enumerate(pairs):
            assert bucket_contents[i][0] == sp
            assert bucket_contents[i][1] == ep
    
    def test_intra_bucket_value(self):
        """Test that intra_bucket_value is correctly calculated and stored."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        ep = "5f4dcc3b5aa765d61d8327deb882cf99"
        sp = "password"
        
        # Calculate expected intra_value
        expected_intra = int(ep[:8], 16) % organizer.bucket_size
        
        organizer.add_to_bucket(sp, ep)
        
        bucket_key = organizer.assign_bucket(ep)
        bucket_contents = organizer.get_bucket(bucket_key)
        
        # Check that intra_value matches
        assert bucket_contents[0][2] == expected_intra
    
    def test_all_bucket_keys(self):
        """Test getting all active bucket keys."""
        organizer = BucketOrganizer(qubit_count=4, total_entries=1000)
        
        # Initially no buckets
        assert organizer.all_bucket_keys() == []
        
        # Add entries to different buckets
        organizer.add_to_bucket("pw1", "10000000")
        organizer.add_to_bucket("pw2", "20000000")
        organizer.add_to_bucket("pw3", "30000000")
        
        # Should have multiple bucket keys
        keys = organizer.all_bucket_keys()
        assert len(keys) >= 1
        assert all(isinstance(k, int) for k in keys)
        assert all(0 <= k < organizer.num_buckets for k in keys)
