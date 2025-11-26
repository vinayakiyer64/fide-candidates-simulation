from dataclasses import dataclass
from typing import List, Tuple, Dict
from collections import defaultdict
import random

from ..entities import Player, PlayerPool
from ..game_logic import game_outcome_with_draws, elo_expected_score
from ..utils import weighted_sample

class WorldCupSimulator:
    """
    Simulate a knockout World Cup.
    We ignore color assignments and tiebreak time controls and approximate
    each match by a small number of classical-like games.
    """

    def __init__(self,
                 players: PlayerPool,
                 num_qualifiers: int = 3,
                 field_size: int = 128,
                 games_per_match: int = 2):
        self.players = players
        self.num_qualifiers = num_qualifiers
        self.field_size = field_size
        self.games_per_match = games_per_match

    def simulate_match(self, a: Player, b: Player) -> Player:
        """Return winner of a mini-match between players A and B."""
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
        Return a list of players sorted by finishing position (1st, 2nd, 3rd, ...).
        """
        # Choose field_size players, biased to include stronger players more often
        field = weighted_sample(self.players,
                                min(self.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2600) / 200.0)

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
        standings = self.simulate_tournament()
        # Take top num_qualifiers distinct players
        return standings[:self.num_qualifiers]

