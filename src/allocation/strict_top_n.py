from typing import List, Set
from src.entities import Player
from src.allocation.base import AllocationStrategy

class StrictTopNAllocation(AllocationStrategy):
    """
    Strict Top-N allocation strategy.
    
    Only considers the top `max_spots` players in the standings.
    If any of them are already qualified, that spot is LOST (not passed to the next player).
    """

    def allocate(self, 
                 standings: List[Player], 
                 max_spots: int,
                 already_qualified: Set[int]) -> List[Player]:
        """
        Allocate spots strictly from the Top N.

        Args:
            standings (List[Player]): Ordered list of players (best first).
            max_spots (int): Number of top positions to consider.
            already_qualified (Set[int]): IDs of players who have already qualified.

        Returns:
            List[Player]: Players who qualify (only those in Top N who aren't already qualified).
        """
        qualifiers = []
        
        # Only look at the top `max_spots` players
        top_n = standings[:max_spots]
        
        for player in top_n:
            if player.id not in already_qualified:
                qualifiers.append(player)
                
        return qualifiers

