"""
Attack Orchestrator for the Quantum Rainbow Table Attack phase.

Wires together all attack components into a single crack() call:
  - BloomFilter:    Skip ~99.9% of candidate positions in nanoseconds.
  - walk_forward:   Reconstruct candidate_EP from target_hash + position k.
  - BucketLoader:   Fetch real entries from SQLite for that bucket.
  - DummyPadder:    Pad to exactly 2^n entries for Grover's circuit.
  - GroverSearch:   Quantum search for the matching chain in the bucket.
  - ChainVerifier:  Classical walk from SP to extract the plaintext password.

Attack pipeline (per target hash):
    for k = chain_length-1 down to 0:
        candidate_EP = walk_forward(target_hash, k)
        if NOT bloom.possibly_exists(candidate_EP): continue     # nanoseconds
        bucket_key = int(candidate_EP[:8], 16) % num_buckets
        real_entries = DB.query(bucket_key)
        padded       = DummyPadder.pad(real_entries)             # to 2^n
        idx          = GroverSearch.search(padded, target_hash, k)  # quantum
        if idx is None: continue
        sp = padded[idx][0]
        password = ChainVerifier.find_password(sp, target_hash)
        if password: return password                              # CRACKED!
    return None                                                   # not in table
"""

from typing import Optional

from rainbow_table_generator.config import Config
from rainbow_table_generator.hash_functions import hash_factory

from attack.bloom_filter import BloomFilter
from attack.bucket_loader import BucketLoader
from attack.chain_verifier import ChainVerifier
from attack.dummy_padding import DummyPadder
from attack.grover_search import GroverSearch
from attack.walk_forward import walk_forward


class RainbowAttack:
    """
    Main orchestrator for the hybrid classical-quantum rainbow table attack.

    Example:
        >>> config = load_config("config.json")
        >>> bloom = BloomFilter(n_items=38_285_441, fpr=0.001)
        >>> bloom.build_from_db("rainbow_tables/output/rainbow_table.db")
        >>> attack = RainbowAttack(config, "rainbow_tables/output/rainbow_table.db",
        ...                       bloom_filter=bloom)
        >>> password = attack.crack("5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8")
    """

    def __init__(
        self,
        config: Config,
        db_path: str,
        num_buckets: int,
        bloom_filter: Optional[BloomFilter] = None,
        use_dega: bool = False,
    ) -> None:
        """
        Args:
            config:       Config loaded from config.json.
            db_path:      Path to rainbow_table.db.
            num_buckets:  Total buckets in the table (from fix_buckets output,
                          known to be 49851 for the current 10-qubit table).
            bloom_filter: Pre-built BloomFilter (None = disable pre-screening).
            use_dega:     Use DEGA instead of standard Grover (default: False).
        """
        self.config = config
        self.db_path = db_path
        self.bloom = bloom_filter
        self.use_dega = use_dega

        hash_func = hash_factory(config.hash_algorithm)
        self.padder = DummyPadder(n_qubits=config.qubit_count)
        self.verifier = ChainVerifier(
            chain_length=config.chain_length,
            password_length=config.password_length,
            hash_func=hash_func,
        )
        self.loader = BucketLoader(
            db_path=db_path,
            num_buckets=num_buckets,
        )
        
        # Choose quantum search algorithm
        if use_dega:
            from DEGA import DEGASearch
            self.searcher = DEGASearch(
                n_qubits=config.qubit_count,
                chain_length=config.chain_length,
                password_length=config.password_length,
                hash_func=hash_func,
            )
        else:
            self.searcher = GroverSearch(
                n_qubits=config.qubit_count,
                chain_length=config.chain_length,
                password_length=config.password_length,
                hash_func=hash_func,
            )
        
        self._hash_func = hash_func


    def crack(
        self,
        target_hash_hex: str,
        verbose: bool = False,
    ) -> Optional[str]:
        """
        Attempt to crack a hash using the quantum rainbow table attack.

        Args:
            target_hash_hex: 40-char SHA-1 hex string to crack.
            verbose:         Print progress for each position tried.

        Returns:
            Plaintext password, or None if not found in the table.
        """
        with self.loader:
            for k in range(self.config.chain_length - 1, -1, -1):

                # Step 1: Walk forward
                candidate_ep = walk_forward(
                    target_hash_hex=target_hash_hex,
                    position_k=k,
                    chain_length=self.config.chain_length,
                    password_length=self.config.password_length,
                    hash_func=self._hash_func,
                )

                # Step 2: Bloom filter pre-screen
                if self.bloom and not self.bloom.possibly_exists(candidate_ep):
                    continue

                if verbose:
                    print(f"[k={k}] Bloom passed → bucket lookup...")

                # Step 3: Load bucket from DB
                bucket_key = self.loader.compute_bucket_key(candidate_ep)
                real_entries = self.loader.load_bucket(bucket_key)
                if not real_entries:
                    continue

                # Step 4: Pad to 2^n
                padded = self.padder.pad(real_entries)

                # Step 5: Grover's search (with endpoint pre-filtering optimization)
                result_idx = self.searcher.search(
                    padded, target_hash_hex, k, candidate_ep_hex=candidate_ep
                )
                if result_idx is None:
                    continue

                # Step 6: Classical verification
                entry = padded[result_idx]
                if self.padder.is_dummy(entry):
                    continue

                password = self.verifier.find_password(entry[0], target_hash_hex)
                if password:
                    if verbose:
                        print(f"[k={k}] CRACKED! Password = {password!r}")
                    return password

        return None

    def __repr__(self) -> str:
        algorithm = "DEGA" if self.use_dega else "Grover"
        return (
            f"RainbowAttack("
            f"algorithm={algorithm}, "
            f"chain_length={self.config.chain_length}, "
            f"n_qubits={self.config.qubit_count}, "
            f"bloom={'enabled' if self.bloom else 'disabled'})"
        )
