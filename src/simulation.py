from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from collections import Counter
import random
import math

from .entities import Player, PlayerPool
from .tournaments.world_cup import WorldCupSimulator
from .tournaments.grand_swiss import GrandSwissSimulator
from .tournaments.circuit import FideCircuitSimulator

@dataclass
class QualificationConfig:
    num_rating: int
    num_world_cup: int
    num_grand_swiss: int
    num_circuit: int


class QualificationSimulator:
    def __init__(self,
                 players: PlayerPool,
                 config: QualificationConfig):
        # Players sorted by Elo descending
        self.players = sorted(players, key=lambda p: p.elo, reverse=True)
        self.config = config

    def rating_qualifiers(self, already_qualified_ids: Set[int]) -> List[Player]:
        qualifiers = []
        for p in self.players:
            if p.id in already_qualified_ids:
                continue
            qualifiers.append(p)
            already_qualified_ids.add(p.id)
            if len(qualifiers) >= self.config.num_rating:
                break
        return qualifiers

    def simulate_one_season(self) -> List[Player]:
        """
        Simulate all qualification paths and return list of unique qualifiers.
        """
        qualified_ids = set()
        qualifiers = []

        # World Cup
        if self.config.num_world_cup > 0:
            wc_sim = WorldCupSimulator(self.players, self.config.num_world_cup)
            wc_qualifiers = wc_sim.get_qualifiers()
            for p in wc_qualifiers:
                if p.id not in qualified_ids:
                    qualified_ids.add(p.id)
                    qualifiers.append(p)

        # Grand Swiss
        if self.config.num_grand_swiss > 0:
            gs_sim = GrandSwissSimulator(self.players, self.config.num_grand_swiss)
            gs_qualifiers = gs_sim.get_qualifiers()
            for p in gs_qualifiers:
                if p.id not in qualified_ids:
                    qualified_ids.add(p.id)
                    qualifiers.append(p)

        # FIDE Circuit
        if self.config.num_circuit > 0:
            circuit_sim = FideCircuitSimulator(self.players, self.config.num_circuit)
            circuit_qualifiers = circuit_sim.simulate_circuit()
            for p in circuit_qualifiers:
                if p.id not in qualified_ids:
                    qualified_ids.add(p.id)
                    qualifiers.append(p)

        # Rating
        if self.config.num_rating > 0:
            rating_qualifiers = self.rating_qualifiers(qualified_ids)
            qualifiers.extend(rating_qualifiers)

        # Ensure we have at most 8 for Candidates
        qualifiers = qualifiers[:8]
        return qualifiers


def run_monte_carlo(players: PlayerPool,
                    config: QualificationConfig,
                    num_seasons: int = 1000,
                    seed: Optional[int] = None) -> Dict:
    """
    Run many simulated seasons and compute fairness metrics.
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
        total_seasons_with_full_8 += 1
        avg_elo = sum(p.elo for p in quals) / len(quals)
        elo_sums += avg_elo
        elo_sums_sq += avg_elo ** 2
        for p in quals:
            qual_counts[p.id] += 1

    # per-player qualification probability
    qual_probs = {
        p.id: qual_counts[p.id] / total_seasons_with_full_8
        for p in players
    }

    # average & variance of average Elo of qualifiers
    mean_avg_elo = elo_sums / max(1, total_seasons_with_full_8)
    var_avg_elo = (elo_sums_sq / max(1, total_seasons_with_full_8)) - mean_avg_elo ** 2

    # Correlation between Elo rank and qualification probability (approx)
    ranks = [p.initial_rank for p in players]
    probs = [qual_probs[p.id] for p in players]
    rank_mean = sum(ranks) / len(ranks)
    prob_mean = sum(probs) / len(probs)
    cov = sum((r - rank_mean) * (q - prob_mean) for r, q in zip(ranks, probs)) / len(ranks)
    var_rank = sum((r - rank_mean) ** 2 for r in ranks) / len(ranks)
    var_prob = sum((q - prob_mean) ** 2 for q in probs) / len(probs)
    if var_rank > 0 and var_prob > 0:
        corr_rank_prob = cov / math.sqrt(var_rank * var_prob)
    else:
        corr_rank_prob = 0.0

    return {
        "mean_avg_elo": mean_avg_elo,
        "var_avg_elo": var_avg_elo,
        "qual_probs": qual_probs,
        "corr_rank_prob": corr_rank_prob,
        "total_seasons": total_seasons_with_full_8,
    }

