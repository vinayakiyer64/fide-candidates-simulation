from typing import List, Tuple, Set
from collections import defaultdict
import random

from src.entities import Player, PlayerPool
from src.game_logic import game_outcome_with_draws, update_ratings
from src.utils import weighted_sample
from src.tournaments.base import Tournament

class GrandSwissSimulator(Tournament):
    """
    Simulate a Swiss-system tournament (e.g., FIDE Grand Swiss).

    Attributes:
        field_size (int): Number of participants.
        rounds (int): Number of rounds played.
    """

    def __init__(self,
                 players: PlayerPool,
                 num_qualifiers: int = 2,
                 field_size: int = 110,
                 rounds: int = 11):
        """
        Initialize the Grand Swiss simulator.

        Args:
            players (PlayerPool): Pool of available players.
            num_qualifiers (int, optional): Number of qualification spots. Defaults to 2.
            field_size (int, optional): Total players in the tournament. Defaults to 110.
            rounds (int, optional): Number of swiss rounds. Defaults to 11.
        """
        super().__init__(players, num_qualifiers)
        self.field_size = field_size
        self.rounds = rounds

    def simulate_tournament(self) -> List[Tuple[Player, float]]:
        """
        Run the Swiss tournament.

        Returns:
            List[Tuple[Player, float]]: List of (Player, Score), sorted by score descending.
        """
        # Selection: Strong players + wildcards. Modeled by weighted sample.
        field = weighted_sample(self.players,
                                min(self.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2500) / 100.0)

        scores = {p.id: 0.0 for p in field}
        
        K = 10.0 # K-factor for Swiss

        for _ in range(self.rounds):
            # Group by score (approximate Swiss pairings)
            groups = defaultdict(list)
            for p in field:
                groups[scores[p.id]].append(p)

            new_scores = scores.copy()

            for score_group, group_players in groups.items():
                random.shuffle(group_players)
                # Pair them in random order within score group
                # (Simplified pairing: ignores colors and past opponents)
                for i in range(0, len(group_players), 2):
                    if i + 1 >= len(group_players):
                        # Bye: assign half point, no rating change
                        new_scores[group_players[i].id] += 0.5
                        continue
                    a = group_players[i]
                    b = group_players[i+1]
                    res = game_outcome_with_draws(a.elo, b.elo)
                    
                    # Update Ratings
                    a.elo, b.elo = update_ratings(a.elo, b.elo, res, k_factor=K)
                    
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

    def get_qualifiers(self, excluded_ids: Set[int] = None) -> List[Player]:
        """
        Run the tournament and return the top eligible players.

        Args:
            excluded_ids (Set[int], optional): Players ineligible to qualify.

        Returns:
            List[Player]: The qualified players.
        """
        if excluded_ids is None:
            excluded_ids = set()
            
        standings = self.simulate_tournament()
        
        qualifiers = []
        for p, score in standings:
            if p.id not in excluded_ids:
                qualifiers.append(p)
                if len(qualifiers) >= self.num_qualifiers:
                    break
                    
        return qualifiers
