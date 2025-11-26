import json
import sys
import os

# Add current directory to path so we can import src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.entities import Player, PlayerPool
from src.config import QualificationConfig, TournamentSlot
from src.simulation import run_monte_carlo
from src.utils import augment_player_pool
from src.allocation.strict_top_n import StrictTopNAllocation
from src.allocation.spillover import SpilloverAllocation

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

    # Define Scenarios using the new Config Structure
    
    # Current System:
    # - Grand Swiss: 2 spots (Strict Top 2)
    # - World Cup: 3 spots (Strict Top 3)
    # - FIDE Circuit: Up to 3 spots (Spillover, fills gaps)
    # - Rating: Fills remainder to 8
    config_current = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=2, strategy=StrictTopNAllocation()),
            TournamentSlot("world_cup", max_spots=3, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=3, strategy=SpilloverAllocation()),
        ]
    )
    
    # Scenario A: "Pure Meritocracy" (Top 8 by Rating)
    config_rating_only = QualificationConfig(
        target_candidates=8,
        slots=[]  # No tournaments, all 8 spots go to Rating
    )
    
    # Scenario B: Re-allocate WC to Rating
    # Reduce WC from 3 to 1 spot
    config_more_rating = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=2, strategy=StrictTopNAllocation()),
            TournamentSlot("world_cup", max_spots=1, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=3, strategy=SpilloverAllocation()),
        ]
    )
    
    # Scenario C: Re-allocate WC to Circuit
    # Reduce WC from 3 to 1, increase Circuit spillover potential
    config_more_circuit = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=2, strategy=StrictTopNAllocation()),
            TournamentSlot("world_cup", max_spots=1, strategy=StrictTopNAllocation()),
            TournamentSlot("fide_circuit", max_spots=5, strategy=SpilloverAllocation()),
        ]
    )
    
    # Custom Scenario: "Grand Slam" (4x Grand Swiss, 2 spots each)
    # Note: This runs 4 separate GS tournaments. 
    # With current design, we'd need to handle multiple tournaments of same type.
    # For simplicity, we simulate this as one large GS with more spots.
    config_grand_slam = QualificationConfig(
        target_candidates=8,
        slots=[
            TournamentSlot("grand_swiss", max_spots=8, strategy=SpilloverAllocation()),
        ]
    )

    scenarios = [
        ("Current System", config_current),
        ("Pure Rating (Reference)", config_rating_only),
        ("More Rating Spots (-2 WC)", config_more_rating),
        ("More Circuit Spots (-2 WC)", config_more_circuit),
        ("Grand Slam (Swiss Only)", config_grand_slam),
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
