from typing import List, Set
from src.entities import Player, PlayerPool
from src.allocation.base import AllocationStrategy

class RatingFallbackAllocation(AllocationStrategy):
    """
    Rating fallback allocation strategy.
    
    Fills remaining spots from the player pool sorted by current (live) Elo.
    This is typically used as the final fallback to reach the target candidate count.
    """

    def __init__(self, player_pool: PlayerPool):
        """
        Initialize with the full player pool.

        Args:
            player_pool (PlayerPool): All players in the simulation.
        """
        self.player_pool = player_pool

    def allocate(self, 
                 standings: List[Player], 
                 max_spots: int,
                 already_qualified: Set[int]) -> List[Player]:
        """
        Allocate spots from the rating list.

        Args:
            standings (List[Player]): Ignored for this strategy (uses player_pool instead).
            max_spots (int): Number of spots to fill.
            already_qualified (Set[int]): IDs of players who have already qualified.

        Returns:
            List[Player]: Players who qualify by rating.
        """
        # Sort by current (live) Elo
        sorted_players = sorted(self.player_pool, key=lambda p: p.elo, reverse=True)
        
        qualifiers = []
        for player in sorted_players:
            if len(qualifiers) >= max_spots:
                break
            if player.id not in already_qualified:
                qualifiers.append(player)
                
        return qualifiers

