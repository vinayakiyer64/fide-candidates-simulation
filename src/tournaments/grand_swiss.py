from typing import List, Tuple
from collections import defaultdict
import random

from ..entities import Player, PlayerPool
from ..game_logic import game_outcome_with_draws
from ..utils import weighted_sample

class GrandSwissSimulator:
    """
    Approximate 11-round Swiss with N players.
    We group players by score and pair within groups.
    """

    def __init__(self,
                 players: PlayerPool,
                 num_qualifiers: int = 2,
                 field_size: int = 110,
                 rounds: int = 11):
        self.players = players
        self.num_qualifiers = num_qualifiers
        self.field_size = field_size
        self.rounds = rounds

    def simulate_tournament(self) -> List[Tuple[Player, float]]:
        field = weighted_sample(self.players,
                                min(self.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2600) / 200.0)

        scores = {p.id: 0.0 for p in field}

        for _ in range(self.rounds):
            # Group by score (approximate Swiss)
            groups = defaultdict(list)
            for p in field:
                groups[scores[p.id]].append(p)

            new_scores = scores.copy()

            for score_group, group_players in groups.items():
                random.shuffle(group_players)
                # pair them in order
                for i in range(0, len(group_players), 2):
                    if i + 1 >= len(group_players):
                        # bye: assign half point
                        new_scores[group_players[i].id] += 0.5
                        continue
                    a = group_players[i]
                    b = group_players[i+1]
                    res = game_outcome_with_draws(a.elo, b.elo)
                    if res == 1.0:
                        new_scores[a.id] += 1.0
                    elif res == 0.5:
                        new_scores[a.id] += 0.5
                        new_scores[b.id] += 0.5
                    else:
                        new_scores[b.id] += 1.0
            scores = new_scores

        # Final standings: score, then Elo as tiebreak
        standings = sorted(field,
                           key=lambda p: (scores[p.id], p.elo),
                           reverse=True)
        return [(p, scores[p.id]) for p in standings]

    def get_qualifiers(self) -> List[Player]:
        standings = self.simulate_tournament()
        return [p for p, s in standings[:self.num_qualifiers]]

