"""
Tests for attack/grover_search.py (GroverSearch).

Uses n_qubits=2 (N=4) where 1 Grover iteration gives 100% success probability:
    P = sin²(3·arcsin(1/√4)) = sin²(3·π/6) = sin²(π/2) = 1.0
"""
import pytest

from rainbow_table_generator.hash_functions import SHA1HashFunction
from rainbow_table_generator.reduction import reduce
from attack.grover_search import GroverSearch
from attack.dummy_padding import DummyPadder, DUMMY_ENTRY

try:
    from qiskit import QuantumCircuit
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not QISKIT_AVAILABLE, reason="Qiskit not installed")


def build_chain(sp, chain_length=4, password_length=8):
    hf = SHA1HashFunction()
    current = sp
    hashes = []
    for i in range(chain_length):
        h = hf.hash(current)
        hashes.append(h.hex())
        current = reduce(h, i, password_length)
    ep = hf.hash(current).hex()
    return sp, ep, hashes


def make_padded(sps, n_qubits=2, chain_length=4):
    hf = SHA1HashFunction()
    entries = []
    all_hashes = []
    for sp in sps:
        _, ep, hashes = build_chain(sp, chain_length=chain_length)
        entries.append((sp, ep))
        all_hashes.append(hashes)
    padder = DummyPadder(n_qubits=n_qubits)
    return padder.pad(entries), all_hashes


def make_searcher(n_qubits=2, chain_length=4):
    return GroverSearch(n_qubits=n_qubits, chain_length=chain_length,
                        password_length=8, hash_func=SHA1HashFunction())


class TestGroverSearchInit:
    def test_n_iterations_n2(self):
        assert make_searcher(n_qubits=2).n_iterations == 1

    def test_n_iterations_n10(self):
        import math
        s = make_searcher(n_qubits=10, chain_length=1000)
        assert s.n_iterations == 25

    def test_invalid_n_qubits(self):
        with pytest.raises(ValueError):
            make_searcher(n_qubits=0)

    def test_repr(self):
        s = make_searcher(n_qubits=2)
        assert "GroverSearch" in repr(s)
        assert "n_qubits=2" in repr(s)


class TestClassicalOracle:
    def test_oracle_finds_correct_entry(self):
        s = make_searcher()
        sp, ep, hashes = build_chain("test0001")
        target_bytes = bytes.fromhex(hashes[0])
        assert s._oracle_evaluate(sp, target_bytes, 0) is True

    def test_oracle_rejects_wrong_entry(self):
        s = make_searcher()
        sp1, _, hashes1 = build_chain("chainaaa")
        sp2, _, _ = build_chain("chainbbb")
        target_bytes = bytes.fromhex(hashes1[0])
        assert s._oracle_evaluate(sp2, target_bytes, 0) is False


class TestGroverSearch:
    def test_finds_entry_at_index_0(self):
        s = make_searcher()
        padded, all_hashes = make_padded(["aaaa0001", "bbbb0002", "cccc0003"])
        result = s.search(padded, all_hashes[0][0], position_k=0)
        assert result == 0

    def test_finds_entry_at_index_1(self):
        s = make_searcher()
        padded, all_hashes = make_padded(["aaaa0001", "bbbb0002", "cccc0003"])
        result = s.search(padded, all_hashes[1][0], position_k=0)
        assert result == 1

    def test_returns_none_when_no_match(self):
        s = make_searcher()
        padded, _ = make_padded(["aaaa0001", "bbbb0002"])
        result = s.search(padded, "0" * 40, position_k=0)
        assert result is None

    def test_wrong_bucket_size_raises(self):
        s = make_searcher()
        with pytest.raises(ValueError, match="exactly 4 entries"):
            s.search([("sp", "ep")] * 3, "0" * 40, position_k=0)

    def test_finds_at_different_positions(self):
        s = make_searcher()
        padded, all_hashes = make_padded(["aaaa0001", "bbbb0002"])
        for k in range(4):
            result = s.search(padded, all_hashes[0][k], position_k=k)
            assert result == 0

    def test_dummy_entries_never_marked(self):
        s = make_searcher()
        dummy_bucket = [DUMMY_ENTRY] * 4
        assert s.search(dummy_bucket, "0" * 40, position_k=0) is None
