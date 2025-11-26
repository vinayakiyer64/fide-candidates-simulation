from typing import List, Set
from src.entities import Player
from src.allocation.base import AllocationStrategy

class RatingAllocation(AllocationStrategy):
    """
    Rating allocation strategy.
    
    - Guaranteed: Minimum spots (default 1)
    - Fills up to max_spots from the rating list
    
    Note: This strategy uses the 'standings' parameter as the player pool
    (sorted by live Elo), unlike tournament strategies which use tournament results.
    """

    def __init__(self, guaranteed_spots: int = 1):
        """
        Initialize the Rating allocation strategy.

        Args:
            guaranteed_spots (int): Minimum guaranteed spots (default 1).
        """
        self.guaranteed_spots = guaranteed_spots

    def allocate(self, 
                 standings: List[Player],
                 max_spots: int,
                 already_qualified: Set[int]) -> List[Player]:
        """
        Allocate spots from the rating list.

        Args:
            standings (List[Player]): Player pool sorted by live Elo (passed by simulator).
            max_spots (int): Maximum number of spots to fill.
            already_qualified (Set[int]): IDs of players already qualified.

        Returns:
            List[Player]: Players who qualify by rating.
        """
        # Ensure we fill at least guaranteed_spots, up to max_spots
        spots_to_fill = max(self.guaranteed_spots, max_spots)
        
        qualifiers = []
        for player in standings:
            if len(qualifiers) >= spots_to_fill:
                break
            if player.id not in already_qualified:
                qualifiers.append(player)
                
        return qualifiers
