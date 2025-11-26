import random
from typing import List, Callable, Optional, TypeVar

T = TypeVar('T')

def weighted_sample(population: List[T],
                    k: int,
                    weight_fn: Optional[Callable[[T], float]] = None) -> List[T]:
    """Sample k distinct items, optionally weighted by weight_fn."""
    if weight_fn is None:
        return random.sample(population, k)
    
    weights = [weight_fn(x) for x in population]
    total = sum(weights)
    probs = [w / total for w in weights]
    
    # naive algorithm for k << n
    chosen = []
    available = population[:]
    available_probs = probs[:]
    
    for _ in range(k):
        x = random.random()
        cum = 0.0
        for i, (item, pr) in enumerate(zip(available, available_probs)):
            cum += pr
            if x <= cum:
                chosen.append(item)
                # remove
                del available[i]
                del available_probs[i]
                s = sum(available_probs) or 1.0
                available_probs = [w / s for w in available_probs]
                break
                
    return chosen

