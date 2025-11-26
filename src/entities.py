from dataclasses import dataclass
from typing import List
import copy

@dataclass
class Player:
    """
    Represents a chess player in the simulation.

    Attributes:
        id (int): Unique identifier for the player.
        name (str): Display name of the player.
        elo (float): Current FIDE Elo rating.
        initial_rank (int): Initial ranking based on Elo at the start of simulation.
    """
    id: int
    name: str
    elo: float
    initial_rank: int  # rank by Elo

    def clone(self) -> 'Player':
        """Create a deep copy of the player."""
        return copy.deepcopy(self)

# Helper type alias for a list of Players
PlayerPool = List[Player]
