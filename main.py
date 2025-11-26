"""
FIDE Candidates Qualification Simulation

This script runs Monte Carlo simulations comparing different qualification systems.
"""

import json
from typing import Dict, List, Optional

from src.entities import Player, PlayerPool
from src.config import (
    QualificationConfig,
    TournamentSlot,
    PlayerConfig,
    ParticipationMode,
)
from src.scenario_builder import ScenarioBuilder
from src.simulation import SimulationStats, run_monte_carlo
from src.utils import augment_player_pool
from src.allocation import StrictTopNAllocation, CircuitAllocation, RatingAllocation


# Known player IDs (from FIDE)
MAGNUS_ID = 1503014
NAKAMURA_ID = 2016192
CARUANA_ID = 2020009
GUKESH_ID = 46616543


def load_players(filename: str = "data/players.json") -> PlayerPool:
    """
    Load players from JSON file and augment the pool to ensure depth.
    """
    try:
        with open(filename, "r") as f:
            data = json.load(f)
        players = []
        for p in data:
            players.append(Player(
                id=p["id"],
                name=p["name"],
                elo=p["elo"],
                initial_rank=p.get("initial_rank", p["id"])
            ))
        
        print(f"Loaded {len(players)} real players. Augmenting pool...")
        players = augment_player_pool(players, target_min_elo=2400.0)
        print(f"Total player pool size after augmentation: {len(players)}")
        
        return players
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using dummy data.")
        return []


def base_slots(qualified_skip_prob: float = 0.0) -> List[TournamentSlot]:
    """Return the default ordered slot list."""
    return [
        TournamentSlot(
            "fide_circuit",
            max_spots=1,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=qualified_skip_prob,
        ),
        TournamentSlot(
            "grand_swiss",
            max_spots=2,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=qualified_skip_prob,
        ),
        TournamentSlot(
            "world_cup",
            max_spots=3,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=qualified_skip_prob,
        ),
        TournamentSlot(
            "fide_circuit",
            max_spots=2,
            strategy=CircuitAllocation(base_spots=1, max_spots=2),
            qualified_skip_prob=qualified_skip_prob,
        ),
        TournamentSlot(
            "rating",
            max_spots=8,
            strategy=RatingAllocation(guaranteed_spots=1),
        ),
    ]


def main():
    players = load_players()
    if not players:
        print("No players loaded. Exiting.")
        return

    print(f"Top player: {players[0].name} ({players[0].elo})")
    
    # Find player names for display
    player_map = {p.id: p.name for p in players}
    print(f"\nKey players:")
    for pid, label in [(MAGNUS_ID, "Magnus"), (NAKAMURA_ID, "Nakamura"), 
                       (GUKESH_ID, "Gukesh"), (CARUANA_ID, "Caruana")]:
        if pid in player_map:
            print(f"  {label}: {player_map[pid]} (ID: {pid})")

    # =========================================================================
    # SCENARIO DEFINITIONS
    # =========================================================================
    
    base_builder = ScenarioBuilder(base_slots())
    scenarios = []
    
    # 1. Current System (baseline)
    scenarios.append(("Current System", base_builder.build()))
    
    # 2. Pure Rating (reference - maximum meritocracy)
    scenarios.append((
        "Pure Rating (Reference)",
        ScenarioBuilder(
            [
                TournamentSlot(
                    "rating",
                    max_spots=8,
                    strategy=RatingAllocation(guaranteed_spots=8),
                )
            ]
        ).build()
    ))
    
    # 3. Current System with Gukesh as World Champion (plays but can't qualify)
    scenarios.append((
        "Current + Gukesh (Champion)",
        base_builder.with_player_configs(
            {
                GUKESH_ID: PlayerConfig(mode=ParticipationMode.PLAYS_NOT_ELIGIBLE),
            }
        ).build()
    ))
    
    # 4. Current System with Magnus excluded (retired from cycle)
    scenarios.append((
        "Current + Magnus Excluded",
        base_builder.with_player_configs(
            {
                MAGNUS_ID: PlayerConfig(mode=ParticipationMode.EXCLUDED),
            }
        ).build()
    ))
    
    # 5. Current System with Nakamura rating-only (preserves rating)
    scenarios.append((
        "Current + Nakamura Rating-Only",
        base_builder.with_player_configs(
            {
                NAKAMURA_ID: PlayerConfig(mode=ParticipationMode.RATING_ONLY),
            }
        ).build()
    ))
    
    # 6. Current System with strategic withdrawals (75% skip after qualifying)
    scenarios.append((
        "Current + 75% Skip After Qual",
        ScenarioBuilder(base_slots(qualified_skip_prob=0.75)).build()
    ))
    
    # 7. Realistic scenario: Gukesh champion, Magnus excluded, strategic play
    scenarios.append((
        "Realistic (Gukesh WC, Magnus Out)",
        ScenarioBuilder(
            base_slots(qualified_skip_prob=0.75)
        )
        .with_player_configs(
            {
                GUKESH_ID: PlayerConfig(mode=ParticipationMode.PLAYS_NOT_ELIGIBLE),
                MAGNUS_ID: PlayerConfig(mode=ParticipationMode.EXCLUDED),
            }
        )
        .build()
    ))
    
    # 8. More Rating Spots (reduce WC from 3 to 1)
    more_rating_slots = [
        TournamentSlot("grand_swiss", max_spots=2, strategy=StrictTopNAllocation()),
        TournamentSlot("world_cup", max_spots=1, strategy=StrictTopNAllocation()),
        TournamentSlot(
            "fide_circuit",
            max_spots=3,
            strategy=CircuitAllocation(base_spots=2, max_spots=3),
        ),
        TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
    ]
    scenarios.append(
        (
            "More Rating Spots (-2 WC)",
            base_builder.with_slots(more_rating_slots).build(),
        )
    )

    # =========================================================================
    # RUN SIMULATIONS
    # =========================================================================
    
    print("\n" + "=" * 100)
    print("Running Simulations (1000 seasons each)...")
    print("=" * 100)
    print(f"{'Scenario':<40} | {'Orig Elo':<10} | {'Live Elo':<10} | {'StdDev(Elo)':<12} | {'Top8 Qual%':<10}")
    print("-" * 100)
    
    # Top 8 players by Elo (Target set for fairness metric)
    top_8_ids = {p.id for p in sorted(players, key=lambda x: x.elo, reverse=True)[:8]}
    
    for name, cfg in scenarios:
        stats = run_monte_carlo(players, cfg, num_seasons=1000, seed=42)
        
        if stats.total_seasons == 0:
            print(f"{name:<40} | Error: No qualifiers produced.")
            continue

        # Metric: What % of the "True Top 8" qualified on average?
        avg_top8_qual = sum(stats.qual_probs.get(pid, 0) for pid in top_8_ids) / 8.0
        
        print(
            f"{name:<40} | {stats.mean_avg_elo_original:.1f}      | "
            f"{stats.mean_avg_elo_live:.1f}      | {stats.stddev_avg_elo_live:.1f}         | "
            f"{avg_top8_qual*100:.1f}%"
        )

    print("-" * 100)
    
    # =========================================================================
    # DETAILED QUALIFICATION PROBABILITIES
    # =========================================================================
    
    print("\n" + "=" * 100)
    print("Top 15 Qualification Probabilities (Current System)")
    print("=" * 100)
    
    # Run current system once more for detailed stats
    stats = run_monte_carlo(players, base_builder.build(), num_seasons=1000, seed=42)

    if stats.total_seasons > 0:
        # Sort by qualification probability
        sorted_probs = sorted(stats.qual_probs.items(), key=lambda x: x[1], reverse=True)
        
        print(f"{'Rank':<6} | {'Player':<30} | {'Orig Elo':<10} | {'Qual Prob':<10}")
        print("-" * 70)
        
        for i, (pid, prob) in enumerate(sorted_probs[:15], 1):
            if pid in player_map:
                orig_elo = next((p.elo for p in players if p.id == pid), 0)
                print(f"{i:<6} | {player_map[pid]:<30} | {orig_elo:.0f}       | {prob*100:.1f}%")


if __name__ == "__main__":
    main()
