from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
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
    
    Attributes:
        tournament_configs (List[Dict]): List of tournament configs (type, spots, kwargs).
        num_rating_spots (int): Minimum number of spots allocated purely by rating (used as fallback).
    """
    tournament_configs: List[Dict] = field(default_factory=list)
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
        self.players = players
        self.config = config

    def _create_tournament(self, type_name: str, num_spots: int, **kwargs) -> Tournament:
        """
        Factory method to create tournament instances.
        """
        # Initialize with dummy num_qualifiers, we fetch full standings anyway
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
            List[Player]: The final list of Candidates (typically 8).
        """
        potential_qualifiers = {} # map "type" -> list of players (standings)
        
        # 1. Collection Phase: Run ALL configured tournaments first
        for t_cfg in self.config.tournament_configs:
            t_type = t_cfg["type"]
            spots = t_cfg["spots"]
            kwargs = t_cfg.get("kwargs", {})
            
            if spots <= 0:
                continue

            tournament = self._create_tournament(t_type, spots, **kwargs)
            
            # Fetch DEEP standings (e.g., top 20) to ensure we have enough
            # candidates for conflict resolution/spillover.
            # We rely on 'simulate_tournament' or 'get_qualifiers' with large N.
            # Since 'get_qualifiers' uses 'num_qualifiers', we override it temporarily.
            tournament.num_qualifiers = 20 
            standings = tournament.get_qualifiers(excluded_ids=set())
            
            potential_qualifiers[t_type] = standings

        # 2. Allocation Phase
        final_qualifiers = []
        qualified_ids = set()

        def add_qualifier(player):
            if player.id not in qualified_ids:
                final_qualifiers.append(player)
                qualified_ids.add(player.id)
                return True
            return False

        # A. Grand Swiss (Strict Top 2)
        # If #1 is already qualified (unlikely as first), skip.
        # If #1 is qualified, does it go to #3? 
        # User requirement: "Grand Swiss (at most 2)..."
        # Usually GS spots DO pass down to #3, #4 if Top 2 are World Champ/Runner-up.
        # Assuming standard logic: Fill 2 spots from the best available in GS standings.
        gs_pool = potential_qualifiers.get("grand_swiss", [])
        gs_spots = next((c['spots'] for c in self.config.tournament_configs if c['type'] == 'grand_swiss'), 0)
        
        gs_count = 0
        for p in gs_pool:
            if gs_count >= gs_spots: break
            if add_qualifier(p):
                gs_count += 1

        # B. World Cup (Strict Top 3)
        # User requirement: "The world cup should only have 3 players at most. 
        # If of the top 3 players... 2 are qualified... only 1 spot goes to WC. 
        # No slot will go to the 4th player."
        wc_pool = potential_qualifiers.get("world_cup", [])
        wc_spots = next((c['spots'] for c in self.config.tournament_configs if c['type'] == 'world_cup'), 0)
        
        # Check strictly the top 'wc_spots' players (e.g., Top 3)
        wc_candidates = wc_pool[:wc_spots] 
        
        for p in wc_candidates:
            # If p is already qualified (via GS), they are skipped.
            # The spot is NOT filled by #4. It effectively "disappears" from WC quota.
            add_qualifier(p)

        # C. FIDE Circuit (Base + Spillover, Max 3 Total)
        # User requirement: "circuit spillover for up to 3 spots overall"
        circuit_pool = potential_qualifiers.get("fide_circuit", [])
        circuit_base_spots = next((c['spots'] for c in self.config.tournament_configs if c['type'] == 'fide_circuit'), 0)
        
        # Calculate how many spots are still open (Target 8)
        # But specific rule: Circuit can take "up to 3".
        # Base is usually 2. So 1 extra spillover allowed.
        circuit_max_total = 3 
        
        circuit_count = 0
        for p in circuit_pool:
            if circuit_count >= circuit_max_total: break
            
            # Add if not qualified
            if add_qualifier(p):
                circuit_count += 1
                
            # Note: This logic fills as many as possible up to 3.
            # This naturally covers "Base 2" + "Spillover 1" logic 
            # if spots are available and players aren't dupes.

        # D. Rating Spots (Fill Remainder)
        # "All the remaining go to rating."
        target_total = 8
        if len(final_qualifiers) < target_total:
            # Sort by current (live) Elo
            sorted_by_live = sorted(self.players, key=lambda p: p.elo, reverse=True)
            for p in sorted_by_live:
                if len(final_qualifiers) >= target_total:
                    break
                add_qualifier(p)

        return final_qualifiers[:target_total]


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
    total_seasons_with_full_8 = 0

    for _ in range(num_seasons):
        # CRITICAL: Deep copy players for each season so Elo updates don't persist
        # across seasons. We want each season to start fresh.
        season_players = [p.clone() for p in players]
        
        qual_sim = QualificationSimulator(season_players, config)
        quals = qual_sim.simulate_one_season()
        
        if len(quals) < 1:
            continue
        
        total_seasons_with_full_8 += 1
        
        # Use initial_rank or initial_elo to evaluate "True Strength" of qualifiers?
        # Usually fairness is measured against "True Strength" (Start of season Elo).
        # So we should probably sum the INITIAL Elo of qualifiers to measure quality.
        # But 'quals' contains Modified Player objects.
        # We need to look up their initial stats.
        
        # Wait, p.elo in 'quals' is the END of season Elo.
        # Fairness is: "Did the best players (at start) qualify?"
        # We should track based on ID.
        
        # Let's use the ID to lookup the ORIGINAL player for stats.
        # Creating a map for fast lookup
        original_map = {p.id: p for p in players}
        
        avg_elo = sum(original_map[p.id].elo for p in quals) / len(quals)
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

    # Correlation between Elo rank and qualification probability
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
