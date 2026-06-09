#!/usr/bin/env python3
"""
Rainbow Table Collision Analysis

Analyzes the rainbow table for:
1. Endpoint collisions (multiple chains with same endpoint)
2. Chain distribution across buckets
3. Unique vs total chains
4. Collision rate and impact on coverage

Usage:
    python analysis/collision_analysis.py [--db rainbow_table.db]
"""

import argparse
import sqlite3
import sys
from collections import Counter, defaultdict
sys.path.insert(0, '.')

from rainbow_table_generator.config import load_config

def analyze_collisions(db_path):
    """Analyze collisions in the rainbow table"""
    
    print("=" * 90)
    print("  RAINBOW TABLE COLLISION ANALYSIS")
    print("=" * 90)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check schema
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n[*] Database: {db_path}")
    print(f"[*] Tables found: {', '.join(tables)}")
    
    # Get total chains stored
    cursor.execute("SELECT COUNT(*) FROM chains")
    total_chains_stored = cursor.fetchone()[0]
    
    # Get unique endpoints
    cursor.execute("SELECT COUNT(DISTINCT end_point) FROM chains")
    unique_endpoints = cursor.fetchone()[0]
    
    # Calculate collision rate
    collision_rate = (total_chains_stored - unique_endpoints) / total_chains_stored * 100 if total_chains_stored > 0 else 0
    
    print(f"\n{'='*90}")
    print(f"  OVERALL STATISTICS")
    print(f"{'='*90}")
    print(f"  Total chains stored:       {total_chains_stored:,}")
    print(f"  Unique endpoints:          {unique_endpoints:,}")
    print(f"  Duplicate endpoints:       {total_chains_stored - unique_endpoints:,}")
    print(f"  Collision rate:            {collision_rate:.2f}%")
    print(f"  Effective coverage:        {unique_endpoints / total_chains_stored * 100:.2f}%")
    
    # Analyze endpoint collision distribution
    print(f"\n[*] Analyzing endpoint collision distribution...")
    cursor.execute("""
        SELECT end_point, COUNT(*) as count 
        FROM chains 
        GROUP BY end_point 
        HAVING count > 1
        ORDER BY count DESC
        LIMIT 20
    """)
    
    collisions = cursor.fetchall()
    
    if collisions:
        print(f"\n{'='*90}")
        print(f"  TOP 20 ENDPOINT COLLISIONS")
        print(f"{'='*90}")
        print(f"  {'Endpoint':<42} {'Collision Count':<20}")
        print(f"  {'-'*42} {'-'*20}")
        
        for endpoint, count in collisions:
            print(f"  {endpoint:<42} {count:<20}")
    else:
        print(f"\n[+] No endpoint collisions found!")
    
    # Collision frequency distribution
    cursor.execute("""
        SELECT COUNT(*) as collision_count, COUNT(end_point) as num_endpoints
        FROM (
            SELECT end_point, COUNT(*) as collision_count
            FROM chains
            GROUP BY end_point
        )
        GROUP BY collision_count
        ORDER BY collision_count
    """)
    
    collision_dist = cursor.fetchall()
    
    print(f"\n{'='*90}")
    print(f"  COLLISION FREQUENCY DISTRIBUTION")
    print(f"{'='*90}")
    print(f"  {'Chains per Endpoint':<25} {'Number of Endpoints':<25} {'Percentage':<15}")
    print(f"  {'-'*25} {'-'*25} {'-'*15}")
    
    for collision_count, num_endpoints in collision_dist:
        percentage = num_endpoints / unique_endpoints * 100 if unique_endpoints > 0 else 0
        print(f"  {collision_count:<25} {num_endpoints:<25,} {percentage:>6.2f}%")
    
    # Bucket distribution analysis
    print(f"\n[*] Analyzing bucket distribution...")
    cursor.execute("""
        SELECT bucket_key, COUNT(*) as chain_count
        FROM chains
        GROUP BY bucket_key
        ORDER BY chain_count DESC
    """)
    
    bucket_counts = [count for _, count in cursor.fetchall()]
    
    if bucket_counts:
        avg_chains = sum(bucket_counts) / len(bucket_counts)
        min_chains = min(bucket_counts)
        max_chains = max(bucket_counts)
        
        print(f"\n{'='*90}")
        print(f"  BUCKET DISTRIBUTION")
        print(f"{'='*90}")
        print(f"  Total buckets:             {len(bucket_counts):,}")
        print(f"  Average chains/bucket:     {avg_chains:.2f}")
        print(f"  Min chains in bucket:      {min_chains:,}")
        print(f"  Max chains in bucket:      {max_chains:,}")
        print(f"  Std deviation:             {(sum((x - avg_chains)**2 for x in bucket_counts) / len(bucket_counts))**0.5:.2f}")
        
        # Bucket fill distribution (assuming 1024 for 10-qubit)
        bucket_size = 1024  # 2^10 for 10-qubit
        print(f"\n  Bucket Fill Analysis (target size: {bucket_size}):")
        
        under_filled = sum(1 for c in bucket_counts if c < bucket_size)
        exactly_filled = sum(1 for c in bucket_counts if c == bucket_size)
        over_filled = sum(1 for c in bucket_counts if c > bucket_size)
        
        print(f"    Under-filled (<{bucket_size}):  {under_filled:,} ({under_filled/len(bucket_counts)*100:.2f}%)")
        print(f"    Exactly filled (={bucket_size}): {exactly_filled:,} ({exactly_filled/len(bucket_counts)*100:.2f}%)")
        print(f"    Over-filled (>{bucket_size}):   {over_filled:,} ({over_filled/len(bucket_counts)*100:.2f}%)")
    
    # Startpoint analysis
    print(f"\n[*] Analyzing startpoint distribution...")
    cursor.execute("SELECT COUNT(DISTINCT start_point) FROM chains")
    unique_startpoints = cursor.fetchone()[0]
    
    print(f"\n{'='*90}")
    print(f"  STARTPOINT ANALYSIS")
    print(f"{'='*90}")
    print(f"  Unique startpoints:        {unique_startpoints:,}")
    print(f"  Startpoint reuse rate:     {(total_chains_stored - unique_startpoints) / total_chains_stored * 100:.2f}%")
    
    # Check for startpoint collisions
    cursor.execute("""
        SELECT start_point, COUNT(*) as count
        FROM chains
        GROUP BY start_point
        HAVING count > 1
        LIMIT 10
    """)
    
    sp_collisions = cursor.fetchall()
    if sp_collisions:
        print(f"\n  WARNING: Found {len(sp_collisions)} startpoint collisions (should be 0)!")
        print(f"  Top 10 startpoint collisions:")
        for sp, count in sp_collisions:
            print(f"    {sp}: {count} chains")
    else:
        print(f"\n  [+] No startpoint collisions (all startpoints unique)")
    
    conn.close()
    
    print(f"\n{'='*90}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze rainbow table collisions")
    parser.add_argument("--db", default="rainbow_tables/output/rainbow_table.db", 
                       help="Path to rainbow table database")
    args = parser.parse_args()
    
    analyze_collisions(args.db)
