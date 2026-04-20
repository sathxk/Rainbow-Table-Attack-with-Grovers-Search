"""Tests for attack/bloom_filter.py (BloomFilter)."""
import os
import pytest

from attack.bloom_filter import BloomFilter


class TestBloomFilterInit:
    def test_default_fpr(self):
        bf = BloomFilter(n_items=1000)
        assert bf.fpr == 0.001

    def test_m_computed_correctly(self):
        import math
        bf = BloomFilter(n_items=1000, fpr=0.01)
        expected_m = math.ceil(-1000 * math.log(0.01) / (math.log(2) ** 2))
        assert bf.m == expected_m

    def test_k_computed_correctly(self):
        import math
        bf = BloomFilter(n_items=1000, fpr=0.01)
        expected_k = max(1, round((bf.m / 1000) * math.log(2)))
        assert bf.k == expected_k

    def test_count_starts_at_zero(self):
        bf = BloomFilter(n_items=1000)
        assert bf.count == 0

    def test_bits_all_zero_at_start(self):
        bf = BloomFilter(n_items=100)
        assert bf._bits.count(1) == 0

    def test_invalid_n_items_zero(self):
        with pytest.raises(ValueError):
            BloomFilter(n_items=0)

    def test_invalid_n_items_negative(self):
        with pytest.raises(ValueError):
            BloomFilter(n_items=-1)

    def test_invalid_fpr_zero(self):
        with pytest.raises(ValueError):
            BloomFilter(n_items=100, fpr=0.0)

    def test_invalid_fpr_one(self):
        with pytest.raises(ValueError):
            BloomFilter(n_items=100, fpr=1.0)


class TestBloomFilterAddQuery:
    def test_added_item_is_found(self):
        bf = BloomFilter(n_items=1000)
        bf.add("abc123")
        assert bf.possibly_exists("abc123") is True

    def test_no_false_negatives(self):
        bf = BloomFilter(n_items=1000, fpr=0.001)
        items = [f"sha1hex{i:040d}" for i in range(500)]
        for item in items:
            bf.add(item)
        for item in items:
            assert bf.possibly_exists(item) is True

    def test_count_increments(self):
        bf = BloomFilter(n_items=1000)
        for i in range(10):
            bf.add(f"item{i}")
        assert bf.count == 10

    def test_false_positive_rate_within_tolerance(self):
        n = 5000
        bf = BloomFilter(n_items=n, fpr=0.01)
        for i in range(n):
            bf.add(f"real_item_{i}")
        fp = sum(
            1 for i in range(n)
            if bf.possibly_exists(f"fake_item_{i}_9999")
        )
        assert fp / n <= 0.02  # allow 2× tolerance

    def test_empty_string_item(self):
        bf = BloomFilter(n_items=100)
        bf.add("")
        assert bf.possibly_exists("") is True

    def test_fill_ratio_increases_with_adds(self):
        bf = BloomFilter(n_items=1000)
        r0 = bf.fill_ratio
        bf.add("hello")
        assert bf.fill_ratio > r0


class TestBloomFilterBuildFromDb:
    def test_build_inserts_all_eps(self, tmp_path):
        import sqlite3
        db = str(tmp_path / "rt.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE chains (end_point TEXT)")
        eps = [f"ep{i:040d}" for i in range(50)]
        conn.executemany("INSERT INTO chains VALUES (?)", [(e,) for e in eps])
        conn.commit(); conn.close()

        bf = BloomFilter(n_items=100)
        bf.build_from_db(db)
        for ep in eps:
            assert bf.possibly_exists(ep) is True

    def test_build_returns_correct_count(self, tmp_path):
        import sqlite3
        db = str(tmp_path / "rt.db")
        conn = sqlite3.connect(db)
        conn.execute("CREATE TABLE chains (end_point TEXT)")
        conn.executemany("INSERT INTO chains VALUES (?)", [("x",)] * 30)
        conn.commit(); conn.close()

        bf = BloomFilter(n_items=100)
        count = bf.build_from_db(db)
        assert count == 30

    def test_build_raises_on_missing_db(self):
        bf = BloomFilter(n_items=100)
        with pytest.raises(FileNotFoundError):
            bf.build_from_db("/nonexistent/path.db")


class TestBloomFilterSaveLoad:
    def test_save_creates_files(self, tmp_path):
        bf = BloomFilter(n_items=100)
        bf.add("test")
        bits = str(tmp_path / "bf.bin")
        meta = str(tmp_path / "bf.json")
        bf.save(bits, meta)
        assert os.path.exists(bits)
        assert os.path.exists(meta)

    def test_load_restores_membership(self, tmp_path):
        bf = BloomFilter(n_items=1000, fpr=0.01)
        items = [f"item{i}" for i in range(100)]
        for item in items:
            bf.add(item)
        bits = str(tmp_path / "bf.bin")
        meta = str(tmp_path / "bf.json")
        bf.save(bits, meta)

        bf2 = BloomFilter.load(bits, meta)
        for item in items:
            assert bf2.possibly_exists(item) is True

    def test_load_raises_on_missing_meta(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            BloomFilter.load(str(tmp_path / "bits.bin"), str(tmp_path / "meta.json"))

    def test_repr_contains_key_info(self):
        bf = BloomFilter(n_items=100)
        r = repr(bf)
        assert "BloomFilter" in r
        assert "n_items=100" in r
