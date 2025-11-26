from typing import List
import random

from ..entities import Player, PlayerPool
from ..game_logic import game_outcome_with_draws, elo_expected_score
from ..utils import weighted_sample
from .base import Tournament

class WorldCupSimulator(Tournament):
    """
    Simulate a knockout World Cup tournament.

    Attributes:
        field_size (int): Total number of players in the knockout.
        games_per_match (int): Number of games played per match (tiebreaks simplified).
    """

    def __init__(self,
                 players: PlayerPool,
                 num_qualifiers: int = 3,
                 field_size: int = 128,
                 games_per_match: int = 2):
        """
        Initialize the World Cup simulator.

        Args:
            players (PlayerPool): Pool of available players.
            num_qualifiers (int, optional): Number of qualification spots. Defaults to 3.
            field_size (int, optional): Size of the knockout field. Defaults to 128.
            games_per_match (int, optional): Games per match. Defaults to 2.
        """
        super().__init__(players, num_qualifiers)
        self.field_size = field_size
        self.games_per_match = games_per_match

    def simulate_match(self, a: Player, b: Player) -> Player:
        """
        Simulate a match between two players.

        Args:
            a (Player): First player.
            b (Player): Second player.

        Returns:
            Player: The winner of the match.
        """
        score_a = 0.0
        score_b = 0.0
        for _ in range(self.games_per_match):
            res = game_outcome_with_draws(a.elo, b.elo)
            if res == 1.0:
                score_a += 1.0
            elif res == 0.5:
                score_a += 0.5
                score_b += 0.5
            else:
                score_b += 1.0

        if score_a > score_b:
            return a
        elif score_b > score_a:
            return b
        
        # Tiebreak: assume higher Elo has slight edge
        ea = elo_expected_score(a.elo, b.elo)
        if random.random() < ea:
            return a
        else:
            return b

    def simulate_tournament(self) -> List[Player]:
        """
        Run the knockout tournament.

        Returns:
            List[Player]: Players sorted by finishing position (Winner, Runner-up, etc.)
        """
        # Choose field_size players, biased to include stronger players more often
        # In reality, WC spots are allocated by rating + continental qualifiers. 
        # We use a weighted sample to approximate "mostly strong players get in".
        field = weighted_sample(self.players,
                                min(self.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2500) / 100.0)

        # Random initial seeding by Elo (you can mimic FIDE seeding later)
        field = sorted(field, key=lambda p: p.elo, reverse=True)

        # Knockout bracket
        current = field[:]
        positions = []  # will store losers in reverse finishing order
        while len(current) > 1:
            next_round = []
            # pair top vs bottom etc.
            for i in range(len(current) // 2):
                a = current[i]
                b = current[-(i+1)]
                winner = self.simulate_match(a, b)
                loser = b if winner is a else a
                positions.append(loser)
                next_round.append(winner)
            current = next_round

        # Champion is remaining player
        champion = current[0]
        positions.append(champion)

        # positions now has [round1 losers, round2 losers, ..., champion]
        # Roughly interpret last elements as top finishers:
        positions_sorted = positions[::-1]  # champion first
        return positions_sorted

    def get_qualifiers(self) -> List[Player]:
        """
        Run the tournament and return the top `num_qualifiers` players.

        Returns:
            List[Player]: The qualified players.
        """
        standings = self.simulate_tournament()
        # Take top num_qualifiers distinct players
        return standings[:self.num_qualifiers]
