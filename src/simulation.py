"""
Monte Carlo simulation for FIDE qualification cycles.

This module provides:
- QualificationSimulator: Simulates a single season
- run_monte_carlo: Runs many seasons and computes statistics
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import Counter
import random
import math

from src.entities import Player, PlayerPool
from src.config import QualificationConfig, TournamentSlot
from src.participation import ParticipationManager
from src.tournament_registry import (
    DEFAULT_TOURNAMENT_FACTORIES,
    TournamentFactory,
)


@dataclass
class SimulationStats:
    """Aggregated statistics from many simulated seasons."""

    mean_avg_elo_original: float
    mean_avg_elo_live: float
    var_avg_elo_live: float
    qual_probs: Dict[int, float]
    total_seasons: int

    @property
    def stddev_avg_elo_live(self) -> float:
        return math.sqrt(self.var_avg_elo_live) if self.var_avg_elo_live > 0 else 0.0


class QualificationSimulator:
    """
    Simulates a full qualification cycle based on the provided configuration.
    
    The simulation runs sequentially:
    1. For each tournament slot (in order):
       a. Determine participants (respecting modes and withdrawals)
       b. Run tournament (updates Elo for participants)
       c. Filter standings to eligible players
       d. Allocate qualification spots
       e. Mark qualifiers (affects future slots)
    """

    def __init__(
        self,
        players: PlayerPool,
        config: QualificationConfig,
        seed: Optional[int] = None,
        tournament_factories: Optional[Dict[str, TournamentFactory]] = None,
    ):
        """
        Initialize the simulator.

        Args:
            players: The pool of all players (will be modified during simulation)
            config: The qualification rules
            seed: Random seed for reproducible participation decisions
        """
        self.players = players
        self.config = config
        self.participation = ParticipationManager(players, config, seed=seed)
        merged_factories: Dict[str, TournamentFactory] = {
            **DEFAULT_TOURNAMENT_FACTORIES,
            **config.tournament_factories,
        }
        if tournament_factories:
            merged_factories.update(tournament_factories)
        self.tournament_factories = merged_factories

    def _create_tournament(self, tournament_type: str, participants: PlayerPool, **kwargs):
        """Factory method to create tournament instances."""
        factory = self.tournament_factories.get(tournament_type)
        if factory is None:
            raise ValueError(f"Unknown tournament type: {tournament_type}")
        return factory(participants, **kwargs)

    def _get_standings_for_slot(self, slot: TournamentSlot) -> List[Player]:
        """
        Get standings for a tournament slot.
        
        For rating: Returns ALL players sorted by current Elo
        For tournaments: Runs tournament with eligible participants
        
        Args:
            slot: The tournament slot
            
        Returns:
            Ordered list of players (best first)
        """
        if slot.tournament_type == "rating":
            # Rating uses ALL players sorted by current (live) Elo
            # Eligibility filtering happens at allocation time
            return sorted(self.players, key=lambda p: p.elo, reverse=True)
        
        # Get participants for this tournament
        participants = self.participation.get_participants(slot)
        
        if len(participants) < 2:
            return []
        
        tournament = self._create_tournament(
            slot.tournament_type, 
            participants, 
            **slot.kwargs
        )
        return tournament.get_standings(top_n=20)

    def simulate_one_season(self) -> List[Player]:
        """
        Simulate the full qualification cycle sequentially.
        
        For each slot:
        1. Determine participants (respecting modes and withdrawals)
        2. Run tournament (updates Elo for participants)
        3. Filter standings to eligible players only
        4. Allocate spots (strategy sees all qualified for spillover logic)
        5. Mark qualifiers (affects future slots)
        
        Returns:
            List of qualified players (up to target_candidates)
        """
        final_qualifiers: List[Player] = []
        
        for slot in self.config.slots:
            if len(final_qualifiers) >= self.config.target_candidates:
                break
            
            # 1-2. Run tournament with eligible participants
            standings = self._get_standings_for_slot(slot)
            
            if not standings:
                continue
            
            # 3. Filter to eligible players only
            eligible_standings = self.participation.get_eligible_standings(standings)
            
            if not eligible_standings:
                continue
            
            # 4. Allocate (strategy sees all qualified for spillover logic)
            new_qualifiers = slot.strategy.allocate(
                standings=eligible_standings,
                max_spots=slot.max_spots,
                already_qualified=self.participation.qualified_ids
            )
            
            # 5. Mark as qualified
            new_ids = {p.id for p in new_qualifiers}
            self.participation.mark_qualified(new_ids)
            final_qualifiers.extend(new_qualifiers)
        
        return final_qualifiers[:self.config.target_candidates]


def run_monte_carlo(
    players: PlayerPool,
    config: QualificationConfig,
    num_seasons: int = 1000,
    seed: Optional[int] = None,
    tournament_factories: Optional[Dict[str, TournamentFactory]] = None,
) -> SimulationStats:
    """
    Run many simulated seasons and compute fairness metrics.

    Args:
        players: List of players (original, will be cloned for each season)
        config: Simulation configuration
        num_seasons: Number of iterations
        seed: Random seed for reproducibility

    Returns:
        Dict containing:
            - mean_avg_elo_original: Mean Elo of qualifiers based on pre-season ratings
            - mean_avg_elo_live: Mean Elo of qualifiers based on post-season ratings
            - var_avg_elo_live: Variance of average live Elo across seasons
            - qual_probs: Qualification probability per player
            - total_seasons: Number of valid seasons simulated
    """
    if seed is not None:
        random.seed(seed)

    qual_counts = Counter()
    
    # Track both original and live Elo metrics
    original_elo_sums = 0.0
    live_elo_sums = 0.0
    live_elo_sums_sq = 0.0
    total_valid_seasons = 0
    
    # Pre-compute original stats for fast lookup
    original_map = {p.id: p for p in players}
    original_elos = {p.id: p.elo for p in players}

    for season_idx in range(num_seasons):
        # Deep copy for isolation - each season starts fresh
        season_players = [p.clone() for p in players]
        
        # Use season_idx as part of seed for reproducible participation decisions
        participation_seed = (seed + season_idx) if seed is not None else None
        
        qual_sim = QualificationSimulator(season_players, config, seed=participation_seed)
        quals = qual_sim.simulate_one_season()
        
        if len(quals) < 1:
            continue
        
        total_valid_seasons += 1
        
        # Metrics based on ORIGINAL Elo (true strength, pre-season)
        avg_elo_original = sum(original_elos[p.id] for p in quals) / len(quals)
        original_elo_sums += avg_elo_original
        
        # Metrics based on LIVE Elo (updated through season)
        avg_elo_live = sum(p.elo for p in quals) / len(quals)
        live_elo_sums += avg_elo_live
        live_elo_sums_sq += avg_elo_live ** 2
        
        for p in quals:
            qual_counts[p.id] += 1

    if total_valid_seasons == 0:
        return {}

    # Statistics
    qual_probs = {
        pid: count / total_valid_seasons
        for pid, count in qual_counts.items()
    }

    mean_avg_elo_original = original_elo_sums / total_valid_seasons
    mean_avg_elo_live = live_elo_sums / total_valid_seasons
    var_avg_elo_live = (live_elo_sums_sq / total_valid_seasons) - mean_avg_elo_live ** 2

    return SimulationStats(
        mean_avg_elo_original=mean_avg_elo_original,
        mean_avg_elo_live=mean_avg_elo_live,
        var_avg_elo_live=var_avg_elo_live,
        qual_probs=qual_probs,
        total_seasons=total_valid_seasons,
    )
