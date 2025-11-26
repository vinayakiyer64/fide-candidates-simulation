from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Type
from collections import Counter
import random
import math

from src.entities import Player, PlayerPool
from src.tournaments.base import Tournament
from src.tournaments.world_cup import WorldCupSimulator
from src.tournaments.grand_swiss import GrandSwissSimulator
from src.tournaments.circuit import FideCircuitSimulator

@dataclass
class QualificationConfig:
    """
    Configuration for a qualification season.
    
    Now modular: allows specifying a list of tournament classes/factories to run.
    
    Attributes:
        tournaments (List[Type[Tournament]]): List of tournament classes or instances to run.
        rating_spots (int): Number of spots allocated purely by rating.
    """
    # Dictionary mapping a unique key (e.g. 'world_cup') to a tuple of (TournamentClass, kwargs)
    # This allows generic instantiation.
    # For simplicity in this iteration, we can stick to a structured list of "Tournament definitions"
    
    # New design: A list of (TournamentFactory, num_spots) tuples?
    # Or keep it simple: The config object holds the counts, but the Simulator class is generic.
    
    # Let's make it data-driven.
    # The simulator will iterate over a list of configured tournaments.
    
    tournament_configs: List[Dict] = field(default_factory=list)
    # Example: [{"type": "world_cup", "spots": 3, "kwargs": {...}}, ...]
    
    num_rating_spots: int = 1


class QualificationSimulator:
    """
    Simulates a full qualification cycle based on the provided configuration.
    """

    def __init__(self,
                 players: PlayerPool,
                 config: QualificationConfig):
        """
        Initialize the simulator.

        Args:
            players (PlayerPool): The pool of all players.
            config (QualificationConfig): The qualification rules.
        """
        # Players sorted by Elo descending (needed for rating spots)
        self.players = sorted(players, key=lambda p: p.elo, reverse=True)
        self.config = config

    def rating_qualifiers(self, already_qualified_ids: Set[int]) -> List[Player]:
        """
        Select qualifiers based on Rating, skipping those who already qualified.

        Args:
            already_qualified_ids (Set[int]): IDs of players who already qualified.

        Returns:
            List[Player]: List of players qualifying by rating.
        """
        qualifiers = []
        for p in self.players:
            if p.id in already_qualified_ids:
                continue
            qualifiers.append(p)
            already_qualified_ids.add(p.id)
            if len(qualifiers) >= self.config.num_rating_spots:
                break
        return qualifiers

    def _create_tournament(self, type_name: str, num_spots: int, **kwargs) -> Tournament:
        """
        Factory method to create tournament instances.
        """
        if type_name == "world_cup":
            return WorldCupSimulator(self.players, num_qualifiers=num_spots, **kwargs)
        elif type_name == "grand_swiss":
            return GrandSwissSimulator(self.players, num_qualifiers=num_spots, **kwargs)
        elif type_name == "fide_circuit":
            return FideCircuitSimulator(self.players, num_qualifiers=num_spots, **kwargs)
        else:
            raise ValueError(f"Unknown tournament type: {type_name}")

    def simulate_one_season(self) -> List[Player]:
        """
        Simulate all qualification paths and return list of unique qualifiers.
        
        Returns:
            List[Player]: The final list of Candidates.
        """
        qualified_ids = set()
        qualifiers = []

        # Run configured tournaments
        for t_cfg in self.config.tournament_configs:
            t_type = t_cfg["type"]
            spots = t_cfg["spots"]
            kwargs = t_cfg.get("kwargs", {})
            
            if spots <= 0:
                continue

            tournament = self._create_tournament(t_type, spots, **kwargs)
            t_qualifiers = tournament.get_qualifiers()
            
            for p in t_qualifiers:
                if p.id not in qualified_ids:
                    qualified_ids.add(p.id)
                    qualifiers.append(p)

        # Rating Spots (always last to fill gaps)
        if self.config.num_rating_spots > 0:
            rating_qualifiers = self.rating_qualifiers(qualified_ids)
            qualifiers.extend(rating_qualifiers)

        # Ensure we have at most 8 for Candidates (or whatever the target is)
        # In a real scenario, if a spot is unused, it goes to rating.
        # Our logic effectively handles this by checking 'already_qualified_ids'
        # inside rating_qualifiers, but we should clamp to 8 explicitly if required.
        return qualifiers[:8]


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

    qual_sim = QualificationSimulator(players, config)

    qual_counts = Counter()
    elo_sums = 0.0
    elo_sums_sq = 0.0
    total_seasons_with_full_8 = 0

    for _ in range(num_seasons):
        quals = qual_sim.simulate_one_season()
        if len(quals) < 1:
            continue
        
        # Only count statistics if we actually filled the spots (mostly relevant for small pools)
        # But for robust stats we count all valid seasons.
        total_seasons_with_full_8 += 1
        
        avg_elo = sum(p.elo for p in quals) / len(quals)
        elo_sums += avg_elo
        elo_sums_sq += avg_elo ** 2
        for p in quals:
            qual_counts[p.id] += 1

    if total_seasons_with_full_8 == 0:
        return {}

    # per-player qualification probability
    qual_probs = {
        p.id: qual_counts[p.id] / total_seasons_with_full_8
        for p in players
    }

    # average & variance of average Elo of qualifiers
    mean_avg_elo = elo_sums / total_seasons_with_full_8
    var_avg_elo = (elo_sums_sq / total_seasons_with_full_8) - mean_avg_elo ** 2

    # Correlation between Elo rank and qualification probability (approx)
    ranks = [p.initial_rank for p in players]
    probs = [qual_probs[p.id] for p in players]
    
    if len(ranks) > 1:
        rank_mean = sum(ranks) / len(ranks)
        prob_mean = sum(probs) / len(probs)
        cov = sum((r - rank_mean) * (q - prob_mean) for r, q in zip(ranks, probs)) / len(ranks)
        var_rank = sum((r - rank_mean) ** 2 for r in ranks) / len(ranks)
        var_prob = sum((q - prob_mean) ** 2 for q in probs) / len(probs)
        
        if var_rank > 0 and var_prob > 0:
            corr_rank_prob = cov / math.sqrt(var_rank * var_prob)
        else:
            corr_rank_prob = 0.0
    else:
        corr_rank_prob = 0.0

    return {
        "mean_avg_elo": mean_avg_elo,
        "var_avg_elo": var_avg_elo,
        "qual_probs": qual_probs,
        "corr_rank_prob": corr_rank_prob,
        "total_seasons": total_seasons_with_full_8,
    }
