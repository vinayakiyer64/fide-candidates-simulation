import json
import sys
import os

# Add current directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.entities import Player, PlayerPool
from src.simulation import QualificationConfig, run_monte_carlo

def load_players(filename: str = "data/players.json") -> PlayerPool:
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
        return players
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using dummy data.")
        players = []
        base_elo = 2850
        for i in range(100):
            elo = base_elo - i * 2
            players.append(Player(
                id=i,
                name=f"Player_{i+1}",
                elo=elo,
                initial_rank=i+1
            ))
        return players

def main():
    players = load_players()
    print(f"Loaded {len(players)} players.")
    if players:
        print(f"Top player: {players[0].name} ({players[0].elo})")

    # 1. Define Scenarios
    
    # Baseline: As described by user
    # a. ELO (1), b. GS (2), c. WC (3), d. Circuit (2) -> Total 8
    config_current = QualificationConfig(
        num_rating=1,
        num_world_cup=3,
        num_grand_swiss=2,
        num_circuit=2
    )
    
    # Scenario A: "Pure Meritocracy" (Top 8 by Rating)
    config_rating_only = QualificationConfig(
        num_rating=8,
        num_world_cup=0,
        num_grand_swiss=0,
        num_circuit=0
    )
    
    # Scenario B: Re-allocate WC to Rating
    # Shift 2 spots from WC to Rating: Rating=3, WC=1, GS=2, Circuit=2
    config_more_rating = QualificationConfig(
        num_rating=3,
        num_world_cup=1,
        num_grand_swiss=2,
        num_circuit=2
    )
    
    # Scenario C: Re-allocate WC to Circuit
    # Shift 2 spots from WC to Circuit: Rating=1, WC=1, GS=2, Circuit=4
    config_more_circuit = QualificationConfig(
        num_rating=1,
        num_world_cup=1,
        num_grand_swiss=2,
        num_circuit=4
    )

    scenarios = [
        ("Current System", config_current),
        ("Pure Rating (Reference)", config_rating_only),
        ("More Rating Spots (+2 from WC)", config_more_rating),
        ("More Circuit Spots (+2 from WC)", config_more_circuit),
    ]
    
    # Run simulations
    print("\nRunning Simulations (500 seasons each)...")
    print("-" * 60)
    print(f"{'Scenario':<30} | {'Avg Elo':<10} | {'Top 8 Qual%':<12} | {'Corr(Rank,Prob)':<15}")
    print("-" * 60)
    
    # Top 8 players by Elo (Target set)
    top_8_ids = {p.id for p in sorted(players, key=lambda x: x.elo, reverse=True)[:8]}
    
    for name, cfg in scenarios:
        res = run_monte_carlo(players, cfg, num_seasons=500, seed=42)
        
        # Metric: What % of the "True Top 8" qualified on average?
        # sum(prob of qualification for p in top_8) / 8
        avg_top8_qual = sum(res["qual_probs"].get(pid, 0) for pid in top_8_ids) / 8.0
        
        print(f"{name:<30} | {res['mean_avg_elo']:.1f}      | {avg_top8_qual*100:.1f}%        | {res['corr_rank_prob']:.3f}")

    print("-" * 60)

if __name__ == "__main__":
    main()

