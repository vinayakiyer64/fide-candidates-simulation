import json
import sys
import os

# Add current directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.entities import Player, PlayerPool
from src.simulation import QualificationConfig, run_monte_carlo
from src.utils import augment_player_pool

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
                initial_rank=p["initial_rank"] if "initial_rank" in p else p["id"]
            ))
        
        # Augment to ensure we have enough players for large tournaments (World Cup)
        # Real data might stop at rank 100 (~2640 Elo). We want down to 2400.
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

    # 1. Define Scenarios using the new Modular Config
    
    # Current System:
    # - 1 Rating Spot
    # - 3 World Cup Spots
    # - 2 Grand Swiss Spots
    # - 2 FIDE Circuit Spots
    config_current = QualificationConfig(
        num_rating_spots=1,
        tournament_configs=[
            {"type": "world_cup", "spots": 3},
            {"type": "grand_swiss", "spots": 2},
            {"type": "fide_circuit", "spots": 2}
        ]
    )
    
    # Scenario A: "Pure Meritocracy" (Top 8 by Rating)
    config_rating_only = QualificationConfig(
        num_rating_spots=8,
        tournament_configs=[]
    )
    
    # Scenario B: Re-allocate WC to Rating
    # Shift 2 spots from WC to Rating: Rating=3, WC=1
    config_more_rating = QualificationConfig(
        num_rating_spots=3,
        tournament_configs=[
            {"type": "world_cup", "spots": 1},
            {"type": "grand_swiss", "spots": 2},
            {"type": "fide_circuit", "spots": 2}
        ]
    )
    
    # Scenario C: Re-allocate WC to Circuit
    # Shift 2 spots from WC to Circuit: WC=1, Circuit=4
    config_more_circuit = QualificationConfig(
        num_rating_spots=1,
        tournament_configs=[
            {"type": "world_cup", "spots": 1},
            {"type": "grand_swiss", "spots": 2},
            {"type": "fide_circuit", "spots": 4}
        ]
    )
    
    # Custom Scenario: "Grand Slam" 
    # 4 Grand Swiss tournaments, 2 spots each. No Rating spots.
    config_grand_slam = QualificationConfig(
        num_rating_spots=0,
        tournament_configs=[
            {"type": "grand_swiss", "spots": 2, "kwargs": {"rounds": 11}},
            {"type": "grand_swiss", "spots": 2, "kwargs": {"rounds": 11}},
            {"type": "grand_swiss", "spots": 2, "kwargs": {"rounds": 11}},
            {"type": "grand_swiss", "spots": 2, "kwargs": {"rounds": 11}},
        ]
    )

    scenarios = [
        ("Current System", config_current),
        ("Pure Rating (Reference)", config_rating_only),
        ("More Rating Spots (+2 from WC)", config_more_rating),
        ("More Circuit Spots (+2 from WC)", config_more_circuit),
        ("Grand Slam (4x Swiss)", config_grand_slam),
    ]
    
    # Run simulations
    print("\nRunning Simulations (500 seasons each)...")
    print("-" * 75)
    print(f"{'Scenario':<35} | {'Avg Elo':<10} | {'Top 8 Qual%':<12} | {'Corr(Rank,Prob)':<15}")
    print("-" * 75)
    
    # Top 8 players by Elo (Target set)
    top_8_ids = {p.id for p in sorted(players, key=lambda x: x.elo, reverse=True)[:8]}
    
    for name, cfg in scenarios:
        res = run_monte_carlo(players, cfg, num_seasons=500, seed=42)
        
        if not res:
            print(f"{name:<35} | Error: No qualifiers produced.")
            continue

        # Metric: What % of the "True Top 8" qualified on average?
        avg_top8_qual = sum(res["qual_probs"].get(pid, 0) for pid in top_8_ids) / 8.0
        
        print(f"{name:<35} | {res['mean_avg_elo']:.1f}      | {avg_top8_qual*100:.1f}%        | {res['corr_rank_prob']:.3f}")

    print("-" * 75)

if __name__ == "__main__":
    main()
