from abc import ABC, abstractmethod
from typing import List
from ..entities import Player, PlayerPool

class Tournament(ABC):
    """
    Abstract base class for all tournament simulations.

    Attributes:
        players (PlayerPool): List of players eligible for the tournament.
        num_qualifiers (int): Number of players who qualify from this tournament.
    """

    def __init__(self, players: PlayerPool, num_qualifiers: int):
        """
        Initialize the tournament simulator.

        Args:
            players (PlayerPool): Pool of available players.
            num_qualifiers (int): Number of qualification spots available.
        """
        self.players = players
        self.num_qualifiers = num_qualifiers

    @abstractmethod
    def get_qualifiers(self) -> List[Player]:
        """
        Run the tournament simulation and return the qualifiers.

        Returns:
            List[Player]: The list of players who qualified.
        """
        pass

