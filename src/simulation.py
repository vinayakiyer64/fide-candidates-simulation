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
        num_rating_spots (int): Number of spots allocated purely by rating.
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

    def rating_qualifiers(self, already_qualified_ids: Set[int]) -> List[Player]:
        """
        Select qualifiers based on FINAL live rating, skipping those who already qualified.

        Args:
            already_qualified_ids (Set[int]): IDs of players who already qualified.

        Returns:
            List[Player]: List of players qualifying by rating.
        """
        # Sort by current (live) Elo
        sorted_by_live = sorted(self.players, key=lambda p: p.elo, reverse=True)
        
        qualifiers = []
        for p in sorted_by_live:
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
        # 1. Collection Phase: Gather potential qualifiers from each event
        # We need to store them separately before allocation to handle conflicts
        potential_qualifiers = {} # map "type" -> list of players
        
        # We run ALL configured tournaments first
        for t_cfg in self.config.tournament_configs:
            t_type = t_cfg["type"]
            spots = t_cfg["spots"]
            kwargs = t_cfg.get("kwargs", {})
            
            if spots <= 0:
                continue

            # For Circuit, we need to grab the full list (or at least top 3)
            # The base 'get_qualifiers' usually respects 'num_qualifiers', 
            # but for spillover logic (Circuit #3), we might need more depth.
            # Let's hack it: ask for more qualifiers than needed?
            # Or better: use the tournament instance to get full standings.
            
            tournament = self._create_tournament(t_type, spots, **kwargs)
            
            # Get a deeper list to handle spillover/conflicts
            # e.g. get top 10 from each event to be safe
            top_finishers = tournament.get_qualifiers(excluded_ids=set()) 
            # Note: get_qualifiers usually returns 'num_qualifiers'. 
            # We might need to expose 'simulate_tournament' or ask for more.
            
            # Update: base.py's get_qualifiers runs the sim and slices.
            # But we need the raw standings or a deeper slice.
            # Let's temporarily override 'num_qualifiers' to a safe high number (e.g. 10)
            # just for the retrieval, then reset? 
            # Actually, let's just refactor _create_tournament to accept overrides?
            # Or just assume get_qualifiers(excluded_ids=...) is not enough if we do 2-pass.
            
            # Strategy: Run sim, get full standings (or top N).
            # Since get_qualifiers is the public API, let's rely on it but
            # we need to modify the tournament instance to return MORE players.
            tournament.num_qualifiers = 10 # fetch top 10 to be safe for conflicts
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

        # A. Grand Swiss (Top 2)
        gs_pool = potential_qualifiers.get("grand_swiss", [])
        gs_spots = 2 # Hardcoded per requirement logic or fetch from config?
        # Fetch from config to match the user's setup
        gs_config_spots = next((c['spots'] for c in self.config.tournament_configs if c['type'] == 'grand_swiss'), 0)
        
        count = 0
        for p in gs_pool:
            if count >= gs_config_spots: break
            if add_qualifier(p):
                count += 1

        # B. World Cup (Top 3)
        wc_pool = potential_qualifiers.get("world_cup", [])
        wc_config_spots = next((c['spots'] for c in self.config.tournament_configs if c['type'] == 'world_cup'), 0)
        
        count = 0
        for p in wc_pool:
            if count >= wc_config_spots: break
            if add_qualifier(p):
                count += 1

        # C. FIDE Circuit (Top 2)
        circuit_pool = potential_qualifiers.get("fide_circuit", [])
        circuit_config_spots = next((c['spots'] for c in self.config.tournament_configs if c['type'] == 'fide_circuit'), 0)
        
        count = 0
        for p in circuit_pool:
            if count >= circuit_config_spots: break
            if add_qualifier(p):
                count += 1
                
        # D. Circuit Spillover (Spot #3) logic?
        # Requirement: "Allocate any additional spots to the 3rd Player on the circuit list"
        # This implies if we haven't filled the target (8?), we check Circuit #3.
        # But the logic says "Allocate *any* additional spots".
        # Let's assume this means ONE specific extra spot if available?
        # Or does it mean "If GS/WC winners were duplicates, priority goes to Circuit #3"?
        # Re-reading user query: "Allocate any additional spots to the 3rd Player on the circuit list"
        
        # Let's try to fill 1 spot from Circuit #3 if we are below capacity (typically 8).
        # But wait, 'circuit_config_spots' usually handles the base allocation.
        # If we assume target is 8, and we have gaps.
        
        # Actually, the "Circuit 3rd spot" rule is usually specific: 
        # If the World Cup spot is unused (e.g. winner -> World Champ), it goes to Rating.
        # If a logical spot is freed up, does it go to Circuit?
        # User said: "c. Allocate any additional spots to the 3rd Player on the circuit list"
        
        # Let's implement: If total < 8, try to add next Circuit player (up to 1 more?)
        if len(final_qualifiers) < 8:
            # Try to find the next best Circuit player (who isn't qualified)
            # We already took 'circuit_config_spots' (e.g. 2).
            # Let's check the rest of the pool.
            for p in circuit_pool:
                if p.id not in qualified_ids:
                    add_qualifier(p)
                    # Only one spot? "3rd Player". Implies just one specific reserve.
                    break 

        # E. Rating Spots (Fill remainder)
        # "Allocate additional slots to the player ratings."
        # This means fill until we hit 8.
        
        if len(final_qualifiers) < 8:
            # Sort by current (live) Elo
            sorted_by_live = sorted(self.players, key=lambda p: p.elo, reverse=True)
            for p in sorted_by_live:
                if len(final_qualifiers) >= 8:
                    break
                add_qualifier(p)

        return final_qualifiers[:8]


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
