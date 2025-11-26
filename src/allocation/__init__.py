"""
Allocation strategies for qualification spots.

Each strategy implements the AllocationStrategy interface and determines
how spots are filled from tournament standings.
"""

from src.allocation.base import AllocationStrategy
from src.allocation.strict_top_n import StrictTopNAllocation
from src.allocation.circuit import CircuitAllocation
from src.allocation.rating import RatingAllocation

__all__ = [
    "AllocationStrategy",
    "StrictTopNAllocation", 
    "CircuitAllocation",
    "RatingAllocation",
]

