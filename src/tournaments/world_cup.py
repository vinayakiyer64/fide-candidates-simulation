from typing import List
import random

from src.entities import Player, PlayerPool
from src.game_logic import game_outcome_with_draws, elo_expected_score, update_ratings
from src.utils import weighted_sample
from src.tournaments.base import Tournament

class WorldCupSimulator(Tournament):
    """
    Simulate a knockout World Cup tournament.
    """

    def __init__(self,
                 players: PlayerPool,
                 field_size: int = 128,
                 games_per_match: int = 2):
        """
        Initialize the World Cup simulator.

        Args:
            players (PlayerPool): Pool of available players.
            field_size (int, optional): Size of the knockout field. Defaults to 128.
            games_per_match (int, optional): Games per match. Defaults to 2.
        """
        super().__init__(players)
        self.field_size = field_size
        self.games_per_match = games_per_match

    def _simulate_match(self, a: Player, b: Player) -> Player:
        """
        Simulate a match between two players, updating their Elos.
        """
        score_a = 0.0
        score_b = 0.0
        K = 10.0

        for _ in range(self.games_per_match):
            res = game_outcome_with_draws(a.elo, b.elo)
            a.elo, b.elo = update_ratings(a.elo, b.elo, res, k_factor=K)

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
        
        # Tiebreak
        ea = elo_expected_score(a.elo, b.elo)
        return a if random.random() < ea else b

    def get_standings(self, top_n: int = 10) -> List[Player]:
        """
        Run the knockout tournament and return top finishers.
        """
        # Select field
        field = weighted_sample(self.players,
                                min(self.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2500) / 100.0)

        # Seed by Elo
        field = sorted(field, key=lambda p: p.elo, reverse=True)

        # Knockout bracket
        current = field[:]
        positions = []
        
        while len(current) > 1:
            next_round = []
            for i in range(len(current) // 2):
                a = current[i]
                b = current[-(i+1)]
                winner = self._simulate_match(a, b)
                loser = b if winner is a else a
                positions.append(loser)
                next_round.append(winner)
            current = next_round

        # Champion
        if current:
            positions.append(current[0])

        # Reverse to get champion first
        standings = positions[::-1]
        return standings[:top_n]
