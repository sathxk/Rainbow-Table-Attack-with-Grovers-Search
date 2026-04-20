"""
Tests for attack/bucket_loader.py (BucketLoader).
"""
import os
import sqlite3
import pytest
from attack.bucket_loader import BucketLoader


def make_temp_db(tmp_path, n_buckets=5, chains_per_bucket=3):
    db_path = str(tmp_path / "rainbow_table.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE chains (
            bucket_key   INTEGER NOT NULL,
            intra_value  INTEGER NOT NULL,
            start_point  TEXT    NOT NULL,
            end_point    TEXT    NOT NULL
        )
    """)
    conn.execute("CREATE INDEX idx_bk ON chains (bucket_key)")
    rows = []
    for bk in range(n_buckets):
        for iv in range(chains_per_bucket):
            rows.append((bk, iv, f"sp_{bk}_{iv}", f"ep_{bk}_{iv}"))
    conn.executemany("INSERT INTO chains VALUES (?,?,?,?)", rows)
    conn.commit(); conn.close()
    return db_path


class TestBucketLoaderInit:
    def test_valid_init(self, tmp_path):
        db = make_temp_db(tmp_path)
        loader = BucketLoader(db, num_buckets=1000)
        assert loader.num_buckets == 1000

    def test_invalid_num_buckets(self, tmp_path):
        db = make_temp_db(tmp_path)
        with pytest.raises(ValueError):
            BucketLoader(db, num_buckets=0)

    def test_repr_closed(self, tmp_path):
        loader = BucketLoader(str(tmp_path / "x.db"), num_buckets=100)
        assert "closed" in repr(loader)

    def test_repr_open(self, tmp_path):
        db = make_temp_db(tmp_path)
        with BucketLoader(db, num_buckets=100) as loader:
            assert "open" in repr(loader)


class TestComputeBucketKey:
    def test_known_value(self, tmp_path):
        db = make_temp_db(tmp_path)
        loader = BucketLoader(db, num_buckets=49876)
        ep = "aabbccdd" + "0" * 32
        expected = int("aabbccdd", 16) % 49876
        assert loader.compute_bucket_key(ep) == expected

    def test_output_in_range(self, tmp_path):
        import hashlib
        db = make_temp_db(tmp_path)
        loader = BucketLoader(db, num_buckets=49876)
        for i in range(100):
            ep = hashlib.sha1(f"test{i}".encode()).hexdigest()
            key = loader.compute_bucket_key(ep)
            assert 0 <= key < 49876

    def test_too_short_ep_raises(self, tmp_path):
        db = make_temp_db(tmp_path)
        loader = BucketLoader(db, num_buckets=100)
        with pytest.raises(ValueError):
            loader.compute_bucket_key("abc")


class TestLoadBucket:
    def test_load_existing_bucket(self, tmp_path):
        db = make_temp_db(tmp_path, n_buckets=5, chains_per_bucket=3)
        with BucketLoader(db, num_buckets=100) as loader:
            rows = loader.load_bucket(0)
            assert len(rows) == 3
            assert rows[0] == ("sp_0_0", "ep_0_0")

    def test_load_empty_bucket(self, tmp_path):
        db = make_temp_db(tmp_path, n_buckets=3, chains_per_bucket=2)
        with BucketLoader(db, num_buckets=100) as loader:
            assert loader.load_bucket(99) == []

    def test_ordered_by_intra_value(self, tmp_path):
        db = make_temp_db(tmp_path, n_buckets=1, chains_per_bucket=5)
        with BucketLoader(db, num_buckets=100) as loader:
            rows = loader.load_bucket(0)
            for i, (sp, ep) in enumerate(rows):
                assert sp == f"sp_0_{i}"

    def test_load_without_open_raises(self, tmp_path):
        db = make_temp_db(tmp_path)
        loader = BucketLoader(db, num_buckets=100)
        with pytest.raises(RuntimeError):
            loader.load_bucket(0)

    def test_open_raises_on_missing_db(self, tmp_path):
        loader = BucketLoader(str(tmp_path / "nope.db"), num_buckets=100)
        with pytest.raises(FileNotFoundError):
            loader.open()

    def test_get_total_chains(self, tmp_path):
        db = make_temp_db(tmp_path, n_buckets=4, chains_per_bucket=3)
        with BucketLoader(db, num_buckets=100) as loader:
            assert loader.get_total_chains() == 12

    def test_context_manager_closes_connection(self, tmp_path):
        db = make_temp_db(tmp_path)
        loader = BucketLoader(db, num_buckets=100)
        with loader:
            assert loader._conn is not None
        assert loader._conn is None
