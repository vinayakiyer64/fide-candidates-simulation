import random
from typing import List, Callable, Optional, TypeVar
from .entities import Player, PlayerPool

T = TypeVar('T')

def weighted_sample(population: List[T],
                    k: int,
                    weight_fn: Optional[Callable[[T], float]] = None) -> List[T]:
    """
    Sample k distinct items, optionally weighted by weight_fn.

    Args:
        population (List[T]): The list of items to sample from.
        k (int): Number of items to sample.
        weight_fn (Callable[[T], float], optional): Function returning the weight of an item.

    Returns:
        List[T]: The sampled items.
    """
    if weight_fn is None:
        return random.sample(population, k)
    
    weights = [weight_fn(x) for x in population]
    total = sum(weights)
    if total == 0:
        # Fallback if all weights are 0
        return random.sample(population, k)
        
    probs = [w / total for w in weights]
    
    # naive algorithm for k << n
    chosen = []
    available = population[:]
    available_probs = probs[:]
    
    for _ in range(k):
        if not available:
            break
        x = random.random()
        cum = 0.0
        selected_idx = -1
        
        # Standard roulette wheel selection
        for i, pr in enumerate(available_probs):
            cum += pr
            if x <= cum:
                selected_idx = i
                break
        
        # Fallback for floating point errors
        if selected_idx == -1:
            selected_idx = len(available) - 1
            
        chosen.append(available[selected_idx])
        
        # Remove selected
        del available[selected_idx]
        del available_probs[selected_idx]
        
        # Renormalize
        if not available:
            break
            
        s = sum(available_probs)
        if s > 0:
            available_probs = [w / s for w in available_probs]
        else:
            # If remaining prob is 0, uniform distribution
            available_probs = [1.0 / len(available)] * len(available)
                
    return chosen

def augment_player_pool(players: PlayerPool, target_min_elo: float = 2400.0) -> PlayerPool:
    """
    Augment the player pool by generating filler players down to a target minimum Elo.
    
    This ensures that tournaments with large fields (like World Cup, 128 players)
    have enough participants even if we only scraped the top 100.

    Args:
        players (PlayerPool): Existing real players (Top N).
        target_min_elo (float): The lower bound Elo to simulate down to.

    Returns:
        PlayerPool: The expanded list of players.
    """
    if not players:
        return players

    sorted_players = sorted(players, key=lambda p: p.elo, reverse=True)
    last_real_player = sorted_players[-1]
    last_elo = last_real_player.elo
    last_rank = last_real_player.initial_rank

    # If we already cover down to target, do nothing
    if last_elo <= target_min_elo:
        return players

    # Estimate how many players we need.
    # FIDE ratings follow roughly a normal distribution or logistic tail.
    # For top players, the density increases as rating drops.
    # Simple linear approximation for simulation purposes:
    # Assume density increases linearly? Or just fill a fixed number?
    
    # Let's assume we want a pool large enough for a 128-player tournament
    # plus some extras to make the selection interesting.
    # 200-300 players total is usually enough for "Top Level" sim context.
    
    # Let's create a simple ramp down to 2400.
    # Step size: e.g. 1 point per player?
    # 2640 - 2400 = 240 points. At 1 pt/player -> 240 extra players.
    
    new_players = list(sorted_players)
    current_elo = last_elo
    current_rank = last_rank
    
    while current_elo > target_min_elo:
        current_rank += 1
        # Decrease Elo slightly. 
        # Random decrement between 0.5 and 1.5 to create noise
        decrement = random.uniform(0.5, 1.5)
        current_elo -= decrement
        
        if current_elo < target_min_elo:
            break
            
        new_players.append(Player(
            id=current_rank, # Assuming IDs roughly map to rank for new ones
            name=f"Simulated_Player_{current_rank}",
            elo=round(current_elo, 1),
            initial_rank=current_rank
        ))
        
    return new_players
