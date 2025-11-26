from abc import ABC, abstractmethod
from typing import List, Set
from src.entities import Player, PlayerPool

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
    def get_qualifiers(self, excluded_ids: Set[int] = None) -> List[Player]:
        """
        Run the tournament simulation and return the qualifiers.

        Args:
            excluded_ids (Set[int], optional): IDs of players who are ineligible to qualify
                                               (e.g., already qualified). Defaults to None.

        Returns:
            List[Player]: The list of players who qualified.
        """
        pass
