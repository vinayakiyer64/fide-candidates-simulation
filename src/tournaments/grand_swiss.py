from typing import List, Tuple
from collections import defaultdict
import random

from src.entities import Player, PlayerPool
from src.game_logic import game_outcome_with_draws, update_ratings
from src.utils import weighted_sample
from src.tournaments.base import Tournament

class GrandSwissSimulator(Tournament):
    """
    Simulate a Swiss-system tournament (e.g., FIDE Grand Swiss).
    """

    def __init__(self,
                 players: PlayerPool,
                 field_size: int = 110,
                 rounds: int = 11):
        """
        Initialize the Grand Swiss simulator.

        Args:
            players (PlayerPool): Pool of available players.
            field_size (int, optional): Total players in the tournament. Defaults to 110.
            rounds (int, optional): Number of swiss rounds. Defaults to 11.
        """
        super().__init__(players)
        self.field_size = field_size
        self.rounds = rounds

    def get_standings(self, top_n: int = 10) -> List[Player]:
        """
        Run the Swiss tournament and return top finishers.
        """
        # Select field
        field = weighted_sample(self.players,
                                min(self.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2500) / 100.0)

        scores = {p.id: 0.0 for p in field}
        K = 10.0

        for _ in range(self.rounds):
            # Group by score
            groups = defaultdict(list)
            for p in field:
                groups[scores[p.id]].append(p)

            new_scores = scores.copy()

            for score_group, group_players in groups.items():
                random.shuffle(group_players)
                for i in range(0, len(group_players), 2):
                    if i + 1 >= len(group_players):
                        # Bye
                        new_scores[group_players[i].id] += 0.5
                        continue
                    a = group_players[i]
                    b = group_players[i+1]
                    res = game_outcome_with_draws(a.elo, b.elo)
                    a.elo, b.elo = update_ratings(a.elo, b.elo, res, k_factor=K)
                    
                    if res == 1.0:
                        new_scores[a.id] += 1.0
                    elif res == 0.5:
                        new_scores[a.id] += 0.5
                        new_scores[b.id] += 0.5
                    else:
                        new_scores[b.id] += 1.0
            scores = new_scores

        # Sort by score, then Elo
        standings = sorted(field, key=lambda p: (scores[p.id], p.elo), reverse=True)
        return standings[:top_n]
