from typing import List, Set
from src.entities import Player
from src.allocation.base import AllocationStrategy

class SpilloverAllocation(AllocationStrategy):
    """
    Spillover allocation strategy.
    
    Fills up to `max_spots` from the standings, skipping already qualified players.
    Unlike StrictTopN, this DOES pass spots to the next available player.
    """

    def allocate(self, 
                 standings: List[Player], 
                 max_spots: int,
                 already_qualified: Set[int]) -> List[Player]:
        """
        Allocate spots by filling from the top, skipping qualified players.

        Args:
            standings (List[Player]): Ordered list of players (best first).
            max_spots (int): Maximum number of spots to fill.
            already_qualified (Set[int]): IDs of players who have already qualified.

        Returns:
            List[Player]: Players who qualify.
        """
        qualifiers = []
        
        for player in standings:
            if len(qualifiers) >= max_spots:
                break
            if player.id not in already_qualified:
                qualifiers.append(player)
                
        return qualifiers

