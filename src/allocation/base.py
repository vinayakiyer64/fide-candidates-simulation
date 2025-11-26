from abc import ABC, abstractmethod
from typing import List, Set
from src.entities import Player

class AllocationStrategy(ABC):
    """
    Abstract base class for allocation strategies.
    
    An allocation strategy determines how spots are filled from a pool of 
    tournament standings, given which players have already qualified.
    """

    @abstractmethod
    def allocate(self, 
                 standings: List[Player], 
                 max_spots: int,
                 already_qualified: Set[int]) -> List[Player]:
        """
        Allocate qualification spots from the standings.

        Args:
            standings (List[Player]): Ordered list of players (best first).
            max_spots (int): Maximum number of spots this allocation can fill.
            already_qualified (Set[int]): IDs of players who have already qualified.

        Returns:
            List[Player]: Players who qualify via this allocation.
        """
        pass

