import json

from src.entities import Player, PlayerPool
from src.config import QualificationConfig, TournamentSlot
from src.simulation import run_monte_carlo
from src.utils import augment_player_pool
from src.allocation import StrictTopNAllocation, CircuitAllocation, RatingAllocation


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


def main():
    players = load_players()
    if not players:
        print("No players loaded. Exiting.")
        return

    print(f"Top player: {players[0].name} ({players[0].elo})")

    # Define Scenarios using the Config Structure
    
    # Current System:
    # - Grand Swiss: 2 spots (Strict Top 2)
    # - World Cup: 3 spots (Strict Top 3)
    # - FIDE Circuit: Base 2, Max 3 (spillover if duplicates with GS/WC)
    # - Rating: 1 guaranteed + fill remainder to 8
    config_current = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=2, strategy=StrictTopNAllocation()),
            TournamentSlot("world_cup", max_spots=3, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=3, strategy=CircuitAllocation(base_spots=2, max_spots=3)),
            TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
        ]
    )
    
    # Scenario A: "Pure Meritocracy" (Top 8 by Rating)
    config_rating_only = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=8)),
        ]
    )
    
    # Scenario B: Re-allocate WC to Rating
    # Reduce WC from 3 to 1 spot
    config_more_rating = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=1, strategy=StrictTopNAllocation()),
            TournamentSlot("world_cup", max_spots=2, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=3, strategy=CircuitAllocation(base_spots=2, max_spots=3)),
            TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
        ]
    )
    
    # Scenario C: More Circuit Spots
    # Reduce WC from 3 to 2 and swiss from 2 to 1, increase Circuit max to 4
    config_more_circuit = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=1, strategy=StrictTopNAllocation()),
            TournamentSlot("world_cup", max_spots=2, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=4, strategy=CircuitAllocation(base_spots=2, max_spots=4)),
            TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
        ]
    )
    
    # Scenario D: Grand Slam (Swiss focused, no WC)
    config_grand_slam = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=4, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=3, strategy=CircuitAllocation(base_spots=2, max_spots=3)),
            TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
        ]
    )

    # Scenario E: Single Swiss Spot + 2 WC Spots + 3 Circuit Spots + Rating
    config_single_swiss_wc_circuit_rating = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=1, strategy=StrictTopNAllocation()),
            TournamentSlot("world_cup", max_spots=2, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=3, strategy=CircuitAllocation(base_spots=2, max_spots=3)),
            TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
        ]
    )

    # Scenario F: 2 independent Swiss Spots + 2 WC Spots + 2 Circuit Spots + Rating
    config_two_independent_swiss_wc_circuit_rating = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss_1", max_spots=1, strategy=StrictTopNAllocation()),
            TournamentSlot("grand_swiss_2", max_spots=1, strategy=StrictTopNAllocation()),
            TournamentSlot("world_cup", max_spots=2, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=2, strategy=CircuitAllocation(base_spots=2, max_spots=2)),
            TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
        ]
    )

    scenarios = [
        ("Current System", config_current),
        ("Pure Rating (Reference)", config_rating_only),
        ("More Rating Spots (-1 WC and -1 Swiss)", config_more_rating),
        ("More Circuit Spots (-1 WC and -1 Swiss)", config_more_circuit),
        ("Grand Slam (No WC)", config_grand_slam),
        ("Single Swiss + 2 WC + 2 Circuit + Rating", config_single_swiss_wc_circuit_rating),
        ("2 independent Swiss + 2 WC + 2 Circuit + Rating", config_two_independent_swiss_wc_circuit_rating),
    ]
    
    # Run simulations
    print("\nRunning Simulations (500 seasons each)...")
    print("-" * 95)
    print(f"{'Scenario':<35} | {'Orig Elo':<10} | {'Live Elo':<10} | {'Top 8 Qual%':<12} | {'Corr(Rank,Prob)':<15}")
    print("-" * 95)
    
    # Top 8 players by Elo (Target set)
    top_8_ids = {p.id for p in sorted(players, key=lambda x: x.elo, reverse=True)[:8]}
    
    for name, cfg in scenarios:
        res = run_monte_carlo(players, cfg, num_seasons=500, seed=42)
        
        if not res:
            print(f"{name:<35} | Error: No qualifiers produced.")
            continue

        # Metric: What % of the "True Top 8" qualified on average?
        avg_top8_qual = sum(res["qual_probs"].get(pid, 0) for pid in top_8_ids) / 8.0
        
        print(f"{name:<35} | {res['mean_avg_elo_original']:.1f}      | {res['mean_avg_elo_live']:.1f}      | {avg_top8_qual*100:.1f}%        | {res['corr_rank_prob']:.3f}")

    print("-" * 95)


if __name__ == "__main__":
    main()
