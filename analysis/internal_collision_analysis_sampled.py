#!/usr/bin/env python3
"""
Internal Collision Analysis - Sampled Approach
Analyzes internal collisions by sampling a percentage of chains.

Usage:
    python internal_collision_analysis_sampled.py [--sample-rate 0.005] [--db-path path/to/db]
"""

import sqlite3
import hashlib
import random
import time
import argparse
import os
import sys

def reduce(hash_value, iteration, length):
    """
    Standard rainbow table reduction function.
    Maps hash value to password string.
    """
    charset = "abcdefghijklmnopqrstuvwxyz0123456789"
    charset_len = 36
    search_space = charset_len ** length
    
    hash_int = int.from_bytes(hash_value, byteorder='big')
    value = (hash_int + iteration) % search_space
    
    password = []
    for _ in range(length):
        char_index = value % charset_len
        password.append(charset[char_index])
        value //= charset_len
    
    return ''.join(password)


def analyze_collisions_sampled(db_path, sample_rate=0.005, output_db='collision_analysis.db'):
    """
    Analyze internal collisions by sampling chains.
    
    Args:
        db_path: Path to rainbow table database
        sample_rate: Fraction of chains to sample (default 0.005 = 0.5%)
        output_db: Path to output collision database
    
    Returns:
        tuple: (num_collisions, total_states)
    """
    
    # Check if input database exists
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    # Create database for intermediate states
    print("="*70)
    print("INTERNAL COLLISION ANALYSIS - SAMPLED APPROACH")
    print("="*70)
    print(f"\nCreating collision analysis database: {output_db}")
    
    # Remove existing output database if it exists
    if os.path.exists(output_db):
        print(f"Warning: {output_db} already exists. Removing...")
        os.remove(output_db)
    
    conn = sqlite3.connect(output_db)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE intermediate_states (
            chain_id INTEGER,
            position INTEGER,
            state TEXT
        )
    ''')
    
    # Load total chain count
    print("\nLoading chain information from main database...")
    main_conn = sqlite3.connect(db_path)
    main_cursor = main_conn.cursor()
    
    total_chains = main_cursor.execute('SELECT COUNT(*) FROM chains').fetchone()[0]
    sample_size = int(total_chains * sample_rate)
    
    print(f"\nDatabase: {db_path}")
    print(f"Total chains in database: {total_chains:,}")
    print(f"Sample rate: {sample_rate*100}%")
    print(f"Chains to analyze: {sample_size:,}")
    print(f"Expected storage: ~{sample_size * 1000 * 40 / (1024**3):.1f} GB")
    print(f"Estimated time: ~{sample_size / 38_285_442 * 360:.0f} minutes")
    
    # Random sampling of chain IDs
    print("\nSampling chain IDs...")
    random.seed(42)  # For reproducibility
    sample_ids = random.sample(range(1, total_chains + 1), sample_size)
    sample_ids.sort()  # Sort for efficient database access
    print(f"✓ Sampled {len(sample_ids):,} chain IDs")
    
    # Generate and store intermediate states
    print("\n" + "="*70)
    print("GENERATING INTERMEDIATE STATES")
    print("="*70)
    
    batch = []
    batch_size = 1000
    start_time = time.time()
    last_update = start_time
    
    for idx, chain_id in enumerate(sample_ids):
        # Get start point
        result = main_cursor.execute(
            'SELECT start_point FROM chains WHERE rowid = ?',
            (chain_id,)
        ).fetchone()
        
        if result is None:
            print(f"Warning: Chain {chain_id} not found, skipping...")
            continue
        
        start_point = result[0]
        
        # Generate chain and collect states
        current = start_point
        for position in range(1000):
            hash_value = hashlib.sha1(current.encode()).digest()
            state_hash = hash_value.hex()
            
            batch.append((chain_id, position, state_hash))
            
            current = reduce(hash_value, position, 8)
        
        # Insert batch
        if len(batch) >= batch_size * 1000:
            cursor.executemany(
                'INSERT INTO intermediate_states VALUES (?, ?, ?)',
                batch
            )
            conn.commit()
            batch = []
        
        # Progress update every 1000 chains or every 30 seconds
        current_time = time.time()
        if (idx + 1) % 1000 == 0 or (current_time - last_update) >= 30:
            elapsed = current_time - start_time
            progress = (idx + 1) / sample_size
            eta = (elapsed / progress - elapsed) if progress > 0 else 0
            
            print(f"  Progress: {idx + 1:,}/{sample_size:,} chains "
                  f"({progress*100:.1f}%) | "
                  f"Elapsed: {elapsed/60:.1f}m | "
                  f"ETA: {eta/60:.1f}m")
            last_update = current_time
    
    # Insert remaining
    if batch:
        cursor.executemany('INSERT INTO intermediate_states VALUES (?, ?, ?)', batch)
        conn.commit()
    
    generation_time = time.time() - start_time
    print(f"\n✓ Generation complete in {generation_time/60:.1f} minutes")
    
    # Create index
    print("\n" + "="*70)
    print("CREATING INDEX")
    print("="*70)
    print("Creating index on states (this may take a few minutes)...")
    index_start = time.time()
    cursor.execute('CREATE INDEX idx_state ON intermediate_states(state)')
    conn.commit()
    index_time = time.time() - index_start
    print(f"✓ Index created in {index_time/60:.1f} minutes")
    
    # Find collisions
    print("\n" + "="*70)
    print("FINDING COLLISIONS")
    print("="*70)
    print("Analyzing collisions...")
    collision_start = time.time()
    
    collisions = cursor.execute('''
        SELECT state, COUNT(*) as collision_count
        FROM intermediate_states
        GROUP BY state
        HAVING collision_count > 1
        ORDER BY collision_count DESC
    ''').fetchall()
    
    collision_time = time.time() - collision_start
    print(f"✓ Collision analysis complete in {collision_time:.1f} seconds")
    
    # Calculate statistics
    total_states = sample_size * 1000
    unique_states = total_states - sum(count - 1 for _, count in collisions)
    
    affected_chains_count = cursor.execute('''
        SELECT COUNT(DISTINCT chain_id)
        FROM intermediate_states
        WHERE state IN (
            SELECT state FROM intermediate_states
            GROUP BY state HAVING COUNT(*) > 1
        )
    ''').fetchone()[0]
    
    # Print results
    print("\n" + "="*70)
    print(f"COLLISION ANALYSIS RESULTS ({sample_rate*100}% Sample)")
    print("="*70)
    print(f"Chains analyzed:           {sample_size:,}")
    print(f"Total states tracked:      {total_states:,}")
    print(f"Unique states:             {unique_states:,}")
    print(f"Colliding states:          {len(collisions):,}")
    print(f"Chains affected:           {affected_chains_count:,} ({affected_chains_count/sample_size*100:.2f}%)")
    print(f"Internal collision rate:   {len(collisions) / total_states * 100:.5f}%")
    print("="*70)
    print(f"\nExtrapolated to full dataset ({total_chains:,} chains):")
    print(f"  Estimated colliding states: {len(collisions) / sample_rate:,.0f}")
    print(f"  Estimated collision rate:   {len(collisions) / total_states * 100:.5f}%")
    print("="*70)
    
    # Show top collisions
    if collisions:
        print("\nTop 10 collisions:")
        for i, (state, count) in enumerate(collisions[:10], 1):
            print(f"\n{i}. State {state[:16]}... appears in {count} chains:")
            details = cursor.execute(
                'SELECT chain_id, position FROM intermediate_states WHERE state = ? LIMIT 5',
                (state,)
            ).fetchall()
            for chain_id, pos in details:
                print(f"     Chain {chain_id}, position {pos}")
            if count > 5:
                print(f"     ... and {count - 5} more")
    else:
        print("\n✓ No collisions found in sample!")
    
    # Distribution of collision counts
    print("\nCollision frequency distribution:")
    distribution = cursor.execute('''
        SELECT collision_count, COUNT(*) as num_states
        FROM (
            SELECT COUNT(*) as collision_count
            FROM intermediate_states
            GROUP BY state
        )
        GROUP BY collision_count
        ORDER BY collision_count
    ''').fetchall()
    
    for collision_count, num_states in distribution:
        if collision_count == 1:
            print(f"  {collision_count} chain (unique):        {num_states:,} states")
        else:
            print(f"  {collision_count} chains share state:    {num_states:,} states")
    
    # Save summary to file
    summary_file = 'collision_analysis_summary.txt'
    print(f"\nSaving summary to {summary_file}...")
    with open(summary_file, 'w') as f:
        f.write(f"Internal Collision Analysis Summary ({sample_rate*100}% Sample)\n")
        f.write(f"{'='*70}\n\n")
        f.write(f"Database: {db_path}\n")
        f.write(f"Output database: {output_db}\n\n")
        f.write(f"Sample size: {sample_size:,} chains\n")
        f.write(f"Total states: {total_states:,}\n")
        f.write(f"Unique states: {unique_states:,}\n")
        f.write(f"Colliding states: {len(collisions):,}\n")
        f.write(f"Collision rate: {len(collisions) / total_states * 100:.5f}%\n")
        f.write(f"Chains affected: {affected_chains_count:,} ({affected_chains_count/sample_size*100:.2f}%)\n\n")
        f.write(f"Generation time: {generation_time/60:.1f} minutes\n")
        f.write(f"Index creation time: {index_time/60:.1f} minutes\n")
        f.write(f"Analysis time: {collision_time:.1f} seconds\n")
        f.write(f"Total time: {(generation_time + index_time + collision_time)/60:.1f} minutes\n\n")
        f.write(f"Extrapolated to full dataset:\n")
        f.write(f"  Estimated colliding states: {len(collisions) / sample_rate:,.0f}\n")
        f.write(f"  Estimated collision rate: {len(collisions) / total_states * 100:.5f}%\n")
    
    print(f"✓ Summary saved to {summary_file}")
    
    conn.close()
    main_conn.close()
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    print(f"Output database: {output_db}")
    print(f"Summary file: {summary_file}")
    print("="*70)
    
    return len(collisions), total_states


def main():
    parser = argparse.ArgumentParser(
        description='Analyze internal collisions in rainbow table by sampling chains'
    )
    parser.add_argument(
        '--db-path',
        default='rainbow_tables/output/rainbow_table.db',
        help='Path to rainbow table database (default: rainbow_tables/output/rainbow_table.db)'
    )
    parser.add_argument(
        '--sample-rate',
        type=float,
        default=0.005,
        help='Fraction of chains to sample (default: 0.005 = 0.5%%)'
    )
    parser.add_argument(
        '--output-db',
        default='collision_analysis.db',
        help='Path to output collision database (default: collision_analysis.db)'
    )
    
    args = parser.parse_args()
    
    # Validate sample rate
    if args.sample_rate <= 0 or args.sample_rate > 1:
        print("Error: Sample rate must be between 0 and 1")
        sys.exit(1)
    
    print(f"\nStarting collision analysis...")
    print(f"Sample rate: {args.sample_rate*100}%")
    print(f"Input database: {args.db_path}")
    print(f"Output database: {args.output_db}\n")
    
    start_time = time.time()
    
    try:
        collisions, total_states = analyze_collisions_sampled(
            args.db_path,
            sample_rate=args.sample_rate,
            output_db=args.output_db
        )
        
        total_time = time.time() - start_time
        print(f"\nTotal execution time: {total_time/60:.1f} minutes")
        
    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
