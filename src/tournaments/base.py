from abc import ABC, abstractmethod
from typing import List
from src.entities import Player, PlayerPool

class Tournament(ABC):
    """
    Abstract base class for all tournament simulations.

    Attributes:
        players (PlayerPool): List of players eligible for the tournament.
    """

    def __init__(self, players: PlayerPool):
        """
        Initialize the tournament simulator.

        Args:
            players (PlayerPool): Pool of available players.
        """
        self.players = players

    @abstractmethod
    def get_standings(self, top_n: int = 10) -> List[Player]:
        """
        Run the tournament simulation and return the top N finishers.

        Args:
            top_n (int): Number of top finishers to return.

        Returns:
            List[Player]: Ordered list of players (winner first).
        """
        pass
