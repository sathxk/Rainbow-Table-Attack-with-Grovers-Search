"""
DEGA (Distributed Exact Grover's Algorithm) implementation for rainbow table attacks.

This module provides a deterministic quantum search algorithm with significantly
reduced circuit depth compared to standard Grover's algorithm.
"""

from DEGA.dega_search import DEGASearch

__all__ = ["DEGASearch"]
