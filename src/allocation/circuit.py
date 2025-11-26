from typing import List, Set
from src.entities import Player
from src.allocation.base import AllocationStrategy

class CircuitAllocation(AllocationStrategy):
    """
    FIDE Circuit allocation strategy.
    
    - Base: 2 spots (configurable)
    - Spillover: Up to 1 additional spot (max 3 total) if there are duplicates
      (players in Circuit standings who are already qualified via GS/WC).
    
    The logic:
    1. Scan the top of Circuit standings to count duplicates (already qualified).
    2. available_spots = min(base_spots + duplicates_found, max_spots)
    3. Fill available_spots from standings, skipping already qualified players.
    """

    def __init__(self, base_spots: int = 2, max_spots: int = 3):
        """
        Initialize the Circuit allocation strategy.

        Args:
            base_spots (int): Base number of spots (default 2).
            max_spots (int): Maximum total spots including spillover (default 3).
        """
        self.base_spots = base_spots
        self._max_spots = max_spots

    def allocate(self, 
                 standings: List[Player], 
                 max_spots: int,
                 already_qualified: Set[int]) -> List[Player]:
        """
        Allocate Circuit spots based on the spillover rule.

        Args:
            standings (List[Player]): Ordered list of Circuit finishers.
            max_spots (int): Slot's max_spots (uses min of this and self._max_spots).
            already_qualified (Set[int]): IDs of players already qualified.

        Returns:
            List[Player]: Players who qualify via Circuit.
        """
        # Use the more restrictive of the two max_spots values
        effective_max = min(max_spots, self._max_spots)
        
        # First pass: count duplicates among top finishers
        # We need to look at enough players to find base_spots + potential duplicates
        scan_depth = effective_max + 5  # Look a bit deeper to find eligible players
        duplicates_found = 0
        eligible_players = []
        
        for player in standings[:scan_depth]:
            if player.id in already_qualified:
                duplicates_found += 1
            else:
                eligible_players.append(player)
        
        # Calculate available spots: base + spillover from duplicates, capped at max
        available_spots = min(self.base_spots + duplicates_found, effective_max)
        
        # Fill the available spots from eligible players
        return eligible_players[:available_spots]
