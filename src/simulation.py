from typing import List, Dict, Optional, Set
from collections import Counter
import random
import math

from src.entities import Player, PlayerPool
from src.config import QualificationConfig
from src.tournaments.base import Tournament
from src.tournaments.world_cup import WorldCupSimulator
from src.tournaments.grand_swiss import GrandSwissSimulator
from src.tournaments.circuit import FideCircuitSimulator


class QualificationSimulator:
    """
    Simulates a full qualification cycle based on the provided configuration.
    """

    def __init__(self, players: PlayerPool, config: QualificationConfig):
        """
        Initialize the simulator.

        Args:
            players (PlayerPool): The pool of all players.
            config (QualificationConfig): The qualification rules.
        """
        self.players = players
        self.config = config

    def _create_tournament(self, tournament_type: str, **kwargs) -> Tournament:
        """
        Factory method to create tournament instances.
        """
        factory_map = {
            "world_cup": WorldCupSimulator,
            "grand_swiss": GrandSwissSimulator,
            "fide_circuit": FideCircuitSimulator,
        }
        
        if tournament_type not in factory_map:
            raise ValueError(f"Unknown tournament type: {tournament_type}")
            
        return factory_map[tournament_type](self.players, **kwargs)

    def _get_standings_for_slot(self, tournament_type: str, kwargs: dict) -> List[Player]:
        """
        Get standings for a tournament slot.
        
        For 'rating', returns players sorted by live Elo.
        For other types, runs the tournament simulation.
        """
        if tournament_type == "rating":
            # Return all players sorted by current (live) Elo
            return sorted(self.players, key=lambda p: p.elo, reverse=True)
        else:
            tournament = self._create_tournament(tournament_type, **kwargs)
            return tournament.get_standings(top_n=20)

    def simulate_one_season(self) -> List[Player]:
        """
        Simulate all qualification paths and return list of unique qualifiers.
        
        Returns:
            List[Player]: The final list of Candidates.
        """
        # 1. Collection Phase: Run all tournaments and collect standings
        standings_map: Dict[str, List[Player]] = {}
        
        for slot in self.config.slots:
            # Only run tournament once per type (cache results)
            if slot.tournament_type not in standings_map:
                standings_map[slot.tournament_type] = self._get_standings_for_slot(
                    slot.tournament_type, slot.kwargs
                )

        # 2. Allocation Phase: Apply each slot's strategy in order
        final_qualifiers: List[Player] = []
        qualified_ids: Set[int] = set()

        for slot in self.config.slots:
            standings = standings_map.get(slot.tournament_type, [])
            
            # Apply the slot's allocation strategy
            new_qualifiers = slot.strategy.allocate(
                standings=standings,
                max_spots=slot.max_spots,
                already_qualified=qualified_ids
            )
            
            # Add to final list
            for player in new_qualifiers:
                if player.id not in qualified_ids:
                    final_qualifiers.append(player)
                    qualified_ids.add(player.id)
                    
            # Early exit if we've reached target
            if len(final_qualifiers) >= self.config.target_candidates:
                break

        return final_qualifiers[:self.config.target_candidates]


def run_monte_carlo(players: PlayerPool,
                    config: QualificationConfig,
                    num_seasons: int = 1000,
                    seed: Optional[int] = None) -> Dict:
    """
    Run many simulated seasons and compute fairness metrics.

    Args:
        players (PlayerPool): List of players.
        config (QualificationConfig): Simulation configuration.
        num_seasons (int): Number of iterations.
        seed (int, optional): Random seed.

    Returns:
        Dict: Statistics including mean average Elo of qualifiers and fairness metrics.
    """
    if seed is not None:
        random.seed(seed)

    qual_counts = Counter()
    elo_sums = 0.0
    elo_sums_sq = 0.0
    total_valid_seasons = 0
    
    # Pre-compute original stats for fast lookup
    original_map = {p.id: p for p in players}
    original_ranks = {p.id: p.initial_rank for p in players}

    for _ in range(num_seasons):
        # Deep copy for isolation
        season_players = [p.clone() for p in players]
        
        qual_sim = QualificationSimulator(season_players, config)
        quals = qual_sim.simulate_one_season()
        
        if len(quals) < 1:
            continue
        
        total_valid_seasons += 1
        
        # Metrics based on ORIGINAL stats (True Strength)
        avg_elo = sum(original_map[p.id].elo for p in quals) / len(quals)
        elo_sums += avg_elo
        elo_sums_sq += avg_elo ** 2
        
        for p in quals:
            qual_counts[p.id] += 1

    if total_valid_seasons == 0:
        return {}

    # Statistics
    qual_probs = {
        pid: count / total_valid_seasons
        for pid, count in qual_counts.items()
    }

    mean_avg_elo = elo_sums / total_valid_seasons
    var_avg_elo = (elo_sums_sq / total_valid_seasons) - mean_avg_elo ** 2

    # Correlation: Initial Rank vs Qualification Prob
    xs = [original_ranks[p.id] for p in players]
    ys = [qual_probs.get(p.id, 0.0) for p in players]
    
    if len(xs) > 1:
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / len(xs)
        var_x = sum((x - mean_x) ** 2 for x in xs) / len(xs)
        var_y = sum((y - mean_y) ** 2 for y in ys) / len(ys)
        
        corr = cov / math.sqrt(var_x * var_y) if var_x > 0 and var_y > 0 else 0.0
    else:
        corr = 0.0

    return {
        "mean_avg_elo": mean_avg_elo,
        "var_avg_elo": var_avg_elo,
        "qual_probs": qual_probs,
        "corr_rank_prob": corr,
        "total_seasons": total_valid_seasons,
    }
