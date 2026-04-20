"""Tests for attack/dummy_padding.py (DummyPadder)."""
import pytest
from attack.dummy_padding import DummyPadder, DUMMY_ENTRY, DUMMY_SP, DUMMY_EP


class TestDummyPadderInit:
    def test_bucket_size_for_10_qubits(self):
        p = DummyPadder(n_qubits=10)
        assert p.bucket_size == 1024

    def test_bucket_size_for_4_qubits(self):
        p = DummyPadder(n_qubits=4)
        assert p.bucket_size == 16

    def test_bucket_size_is_power_of_two(self):
        for n in range(1, 11):
            p = DummyPadder(n_qubits=n)
            assert p.bucket_size == 2 ** n

    def test_invalid_zero_qubits(self):
        with pytest.raises(ValueError):
            DummyPadder(n_qubits=0)

    def test_invalid_negative_qubits(self):
        with pytest.raises(ValueError):
            DummyPadder(n_qubits=-1)

    def test_invalid_above_20_qubits(self):
        with pytest.raises(ValueError):
            DummyPadder(n_qubits=21)

    def test_repr(self):
        p = DummyPadder(n_qubits=10)
        assert "DummyPadder" in repr(p)
        assert "1024" in repr(p)


class TestDummyEntry:
    def test_dummy_sp_not_valid_password(self):
        assert not DUMMY_SP.isalnum() or not all(c.islower() or c.isdigit() for c in DUMMY_SP)

    def test_dummy_ep_not_valid_sha1_hex(self):
        assert len(DUMMY_EP) != 40 or not all(c in "0123456789abcdef" for c in DUMMY_EP)


class TestPad:
    def test_pad_empty_bucket(self):
        p = DummyPadder(n_qubits=2)
        result = p.pad([])
        assert len(result) == 4
        assert all(e == DUMMY_ENTRY for e in result)

    def test_pad_exactly_full_bucket(self):
        p = DummyPadder(n_qubits=2)
        entries = [("sp", "ep")] * 4
        result = p.pad(entries)
        assert len(result) == 4
        assert result == entries

    def test_pad_partial_bucket(self):
        p = DummyPadder(n_qubits=2)
        entries = [("sp1", "ep1"), ("sp2", "ep2")]
        result = p.pad(entries)
        assert len(result) == 4
        assert result[:2] == entries
        assert result[2] == DUMMY_ENTRY
        assert result[3] == DUMMY_ENTRY

    def test_real_entries_preserved_in_order(self):
        p = DummyPadder(n_qubits=3)
        entries = [(f"sp{i}", f"ep{i}") for i in range(5)]
        result = p.pad(entries)
        assert result[:5] == entries

    def test_dummies_at_end(self):
        p = DummyPadder(n_qubits=3)
        result = p.pad([("sp", "ep")])
        assert all(e == DUMMY_ENTRY for e in result[1:])

    def test_overflow_raises(self):
        p = DummyPadder(n_qubits=2)
        with pytest.raises(ValueError, match="overflow"):
            p.pad([("sp", "ep")] * 5)

    def test_output_length_always_bucket_size(self):
        p = DummyPadder(n_qubits=4)
        for n in range(p.bucket_size + 1):
            result = p.pad([("sp", "ep")] * n)
            assert len(result) == p.bucket_size

    def test_realistic_10_qubit_bucket(self):
        p = DummyPadder(n_qubits=10)
        entries = [("sp", "ep")] * 768  # typical at fill_factor=0.75
        result = p.pad(entries)
        assert len(result) == 1024
        assert p.count_real(result) == 768
        assert p.count_dummies(result) == 256


class TestIsDummy:
    def test_dummy_entry_is_recognised(self):
        p = DummyPadder(n_qubits=4)
        assert p.is_dummy(DUMMY_ENTRY) is True

    def test_real_entry_not_dummy(self):
        p = DummyPadder(n_qubits=4)
        assert p.is_dummy(("realsp", "realep")) is False

    def test_partial_match_not_dummy(self):
        p = DummyPadder(n_qubits=4)
        assert p.is_dummy((DUMMY_SP, "different_ep")) is False


class TestStrip:
    def test_strip_removes_all_dummies(self):
        p = DummyPadder(n_qubits=2)
        entries = [("sp", "ep")]
        padded = p.pad(entries)
        assert p.strip(padded) == entries

    def test_strip_empty_bucket(self):
        p = DummyPadder(n_qubits=2)
        padded = p.pad([])
        assert p.strip(padded) == []

    def test_strip_preserves_order(self):
        p = DummyPadder(n_qubits=3)
        entries = [(f"sp{i}", f"ep{i}") for i in range(5)]
        padded = p.pad(entries)
        assert p.strip(padded) == entries


class TestCountMethods:
    def test_count_real(self):
        p = DummyPadder(n_qubits=3)
        padded = p.pad([("sp", "ep")] * 3)
        assert p.count_real(padded) == 3

    def test_count_dummies(self):
        p = DummyPadder(n_qubits=3)
        padded = p.pad([("sp", "ep")] * 3)
        assert p.count_dummies(padded) == 5  # 8 - 3

    def test_count_real_plus_dummies_equals_bucket_size(self):
        p = DummyPadder(n_qubits=10)
        padded = p.pad([("sp", "ep")] * 400)
        assert p.count_real(padded) + p.count_dummies(padded) == 1024
