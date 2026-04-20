"""
Tests for attack/walk_forward.py and attack/chain_verifier.py.
These are tested together with real generated chains.
"""
import pytest
from rainbow_table_generator.hash_functions import SHA1HashFunction
from rainbow_table_generator.reduction import reduce
from attack.walk_forward import walk_forward
from attack.chain_verifier import ChainVerifier


def build_chain(sp: str, chain_length: int = 10, password_length: int = 8):
    """Generate chain; return (sp, ep_hex, hashes[k]=H(pwd_k) as hex)."""
    hf = SHA1HashFunction()
    current = sp
    hashes = []
    for i in range(chain_length):
        h = hf.hash(current)
        hashes.append(h.hex())
        current = reduce(h, i, password_length)
    ep = hf.hash(current).hex()
    return sp, ep, hashes


class TestWalkForward:
    def test_last_position_returns_ep(self):
        hf = SHA1HashFunction()
        sp, ep, hashes = build_chain("starting1", chain_length=5)
        result = walk_forward(hashes[4], 4, 5, 8, hf)
        assert result == ep

    def test_first_position_returns_ep(self):
        hf = SHA1HashFunction()
        sp, ep, hashes = build_chain("starting2", chain_length=5)
        result = walk_forward(hashes[0], 0, 5, 8, hf)
        assert result == ep

    def test_all_positions_return_same_ep(self):
        hf = SHA1HashFunction()
        sp, ep, hashes = build_chain("midtest00", chain_length=10)
        for k in range(10):
            assert walk_forward(hashes[k], k, 10, 8, hf) == ep

    def test_wrong_position_gives_different_ep(self):
        hf = SHA1HashFunction()
        sp, ep, hashes = build_chain("wrongpos0", chain_length=10)
        # Use hash from position 3 but claim it's position 7
        assert walk_forward(hashes[3], 7, 10, 8, hf) != ep

    def test_output_is_40_char_hex(self):
        hf = SHA1HashFunction()
        sp, ep, hashes = build_chain("hextest0", chain_length=5)
        result = walk_forward(hashes[0], 0, 5, 8, hf)
        assert len(result) == 40
        assert all(c in "0123456789abcdef" for c in result)

    def test_invalid_position_below_zero(self):
        hf = SHA1HashFunction()
        with pytest.raises(ValueError):
            walk_forward("a" * 40, -1, 10, 8, hf)

    def test_invalid_position_equals_chain_length(self):
        hf = SHA1HashFunction()
        with pytest.raises(ValueError):
            walk_forward("a" * 40, 10, 10, 8, hf)

    def test_deterministic_output(self):
        hf = SHA1HashFunction()
        sp, ep, hashes = build_chain("dettest00", chain_length=5)
        r1 = walk_forward(hashes[2], 2, 5, 8, hf)
        r2 = walk_forward(hashes[2], 2, 5, 8, hf)
        assert r1 == r2


class TestChainVerifier:
    def _make_verifier(self, chain_length=10):
        return ChainVerifier(
            chain_length=chain_length,
            password_length=8,
            hash_func=SHA1HashFunction(),
        )

    def test_finds_hash_at_position_0(self):
        sp, ep, hashes = build_chain("findtest0", chain_length=5)
        v = self._make_verifier(chain_length=5)
        result = v.find_password(sp, hashes[0])
        assert result == sp

    def test_finds_hash_at_all_positions(self):
        sp, ep, hashes = build_chain("findmid01", chain_length=10)
        v = self._make_verifier(chain_length=10)
        for k in range(10):
            pwd = v.find_password(sp, hashes[k])
            assert pwd is not None
            assert SHA1HashFunction().hash_hex(pwd) == hashes[k]

    def test_returns_none_for_unknown_hash(self):
        sp, ep, hashes = build_chain("notfound0", chain_length=5)
        v = self._make_verifier(chain_length=5)
        assert v.find_password(sp, "0" * 40) is None

    def test_dummy_sp_returns_none(self):
        v = self._make_verifier()
        assert v.find_password("__DUMMY_SP__", "a" * 40) is None

    def test_verify_at_position_correct(self):
        sp, ep, hashes = build_chain("verifypos", chain_length=10)
        v = self._make_verifier(chain_length=10)
        for k in range(10):
            assert v.verify_at_position(sp, hashes[k], k) is True

    def test_verify_at_position_wrong_k(self):
        sp, ep, hashes = build_chain("wrongk000", chain_length=10)
        v = self._make_verifier(chain_length=10)
        assert v.verify_at_position(sp, hashes[3], 7) is False

    def test_invalid_chain_length(self):
        with pytest.raises(ValueError):
            ChainVerifier(chain_length=0, password_length=8,
                          hash_func=SHA1HashFunction())

    def test_repr(self):
        v = self._make_verifier()
        assert "ChainVerifier" in repr(v)
