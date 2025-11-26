import random
import math

def elo_expected_score(ra: float, rb: float) -> float:
    """Expected score for player A vs player B."""
    return 1.0 / (1.0 + 10 ** (-(ra - rb) / 400.0))


def game_outcome_with_draws(ra: float,
                            rb: float,
                            d0: float = 0.55,
                            d_min: float = 0.15,
                            D: float = 400.0) -> float:
    """
    Simulate one game result for A vs B.

    Returns:
        1.0 for A win
        0.5 for draw
        0.0 for A loss
    """
    ea = elo_expected_score(ra, rb)
    delta = abs(ra - rb)

    # Draw probability decreases with rating gap
    p_draw = max(d_min, d0 * math.exp(-delta / D))

    # Compute win prob to match expected score
    p_win = ea - 0.5 * p_draw
    # Numerical safety
    p_win = max(0.0, min(1.0, p_win))
    
    # Sample outcome
    u = random.random()
    if u < p_win:
        return 1.0
    elif u < p_win + p_draw:
        return 0.5
    else:
        return 0.0

