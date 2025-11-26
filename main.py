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
    
    scenarios: list[tuple[str, QualificationConfig]] = []

    # Scenario 1: Base tournament order with Gukesh ineligible (World Champion)
    baseline_builder = ScenarioBuilder(base_slots()).with_player_configs(
        {GUKESH_ID: PlayerConfig(mode=ParticipationMode.PLAYS_NOT_ELIGIBLE)}
    )
    scenarios.append(("Scenario 1: Base Structure", baseline_builder.build()))

    strategic_configs = {
        MAGNUS_ID: PlayerConfig(mode=ParticipationMode.EXCLUDED),
        GUKESH_ID: PlayerConfig(mode=ParticipationMode.PLAYS_NOT_ELIGIBLE),
        NAKAMURA_ID: PlayerConfig(mode=ParticipationMode.RATING_ONLY),
    }

    # Scenario 2: Strategic participation with skip probability 0.5
    scenario2_builder = ScenarioBuilder(base_slots(qualified_skip_prob=0.5)).with_player_configs(
        strategic_configs
    )
    scenarios.append(("Scenario 2: Strategic Participation", scenario2_builder.build()))

    # Scenario 3: Scenario 2 but with fewer GS/WC spots (extra spill to rating)
    scenario3_slots = [
        TournamentSlot(
            "fide_circuit",
            max_spots=1,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot(
            "grand_swiss",
            max_spots=1,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot(
            "world_cup",
            max_spots=2,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot(
            "fide_circuit",
            max_spots=2,
            strategy=CircuitAllocation(base_spots=1, max_spots=2),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
    ]
    scenarios.append(
        (
            "Scenario 3: Fewer GS/WC Slots",
            ScenarioBuilder(scenario3_slots).with_player_configs(strategic_configs).build(),
        )
    )

    # Scenario 4: Scenario 2 but with two independent Swiss events (before/after WC)
    scenario4_slots = [
        TournamentSlot(
            "fide_circuit",
            max_spots=1,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot(
            "grand_swiss",
            max_spots=1,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot(
            "world_cup",
            max_spots=3,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot(
            "grand_swiss",
            max_spots=1,
            strategy=StrictTopNAllocation(),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot(
            "fide_circuit",
            max_spots=2,
            strategy=CircuitAllocation(base_spots=1, max_spots=2),
            qualified_skip_prob=0.5,
        ),
        TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
    ]
    scenarios.append(
        (
            "Scenario 4: Two Swiss Events",
            ScenarioBuilder(scenario4_slots).with_player_configs(strategic_configs).build(),
        )
    )

    # Scenario 5: Scenario 4 but only Gukesh is WC (Magnus/Hikaru play)
    scenarios.append(
        (
            "Scenario 5: Swiss Focus (Gukesh WC)",
            ScenarioBuilder(scenario4_slots)
            .with_player_configs({GUKESH_ID: PlayerConfig(mode=ParticipationMode.PLAYS_NOT_ELIGIBLE)})
            .build(),
        )
    )

    # Scenario 6: Ratings only (top 8 by Elo)
    rating_only_builder = ScenarioBuilder(
        [
            TournamentSlot(
                "rating",
                max_spots=8,
                strategy=RatingAllocation(guaranteed_spots=8),
            )
        ]
    )
    scenarios.append(("Scenario 6: Pure Rating", rating_only_builder.build()))

    # =========================================================================
    # RUN SIMULATIONS
    # =========================================================================
    
    print("\n" + "=" * 125)
    print("Running Simulations (1000 seasons each)...")
    print("=" * 125)
    print(f"{'Scenario':<35} | {'Orig Elo':<8} | {'Live Elo':<8} | {'StdDev':<6} | {'Top8%':<6} | {'<2700':<6} | {'<2650':<6} | {'MinElo':<6}")
    print("-" * 125)
    
    # Top 8 players by Elo (Target set for fairness metric)
    top_8_ids = {p.id for p in sorted(players, key=lambda x: x.elo, reverse=True)[:8]}
    
    results: dict[str, SimulationStats] = {}

    for name, cfg in scenarios:
        stats = run_monte_carlo(players, cfg, num_seasons=1000, seed=42)
        results[name] = stats
        
        if stats.total_seasons == 0:
            print(f"{name:<35} | Error: No qualifiers produced.")
            continue

        # Metric: What % of the "True Top 8" qualified on average?
        avg_top8_qual = sum(stats.qual_probs.get(pid, 0) for pid in top_8_ids) / 8.0
        
        print(
            f"{name:<35} | "
            f"{stats.mean_avg_elo_original:.1f}    | "
            f"{stats.mean_avg_elo_live:.1f}    | "
            f"{stats.stddev_avg_elo_live:.1f}   | "
            f"{avg_top8_qual*100:.1f}%  | "
            f"{stats.avg_qualifiers_below_2700:.2f}   | "
            f"{stats.avg_qualifiers_below_2650:.3f}  | "
            f"{stats.avg_min_qualifier_elo:.0f}"
        )

    print("-" * 125)
    
    # =========================================================================
    # DETAILED QUALIFICATION PROBABILITIES
    # =========================================================================
    
    print("\n" + "=" * 100)
    print("Top 15 Qualification Probabilities (Current System)")
    print("=" * 100)
    
    baseline_name = "Scenario 1: Base Structure"
    stats = results.get(baseline_name)

    if stats and stats.total_seasons > 0:
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
