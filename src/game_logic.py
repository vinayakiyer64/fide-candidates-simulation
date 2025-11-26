import random
import math
from typing import Tuple

def elo_expected_score(ra: float, rb: float) -> float:
    """
    Calculate the expected score for player A vs player B using the Elo formula.

    Args:
        ra (float): Rating of player A.
        rb (float): Rating of player B.

    Returns:
        float: Expected score for player A (between 0.0 and 1.0).
    """
    return 1.0 / (1.0 + 10 ** (-(ra - rb) / 400.0))


def game_outcome_with_draws(ra: float,
                            rb: float,
                            d0: float = 0.55,
                            d_min: float = 0.15,
                            D: float = 400.0) -> float:
    """
    Simulate one game result for A vs B, accounting for draw probabilities.

    The draw probability is modeled to decrease as the rating difference increases.

    Args:
        ra (float): Rating of player A.
        rb (float): Rating of player B.
        d0 (float, optional): Maximum draw probability (equal ratings). Defaults to 0.55.
        d_min (float, optional): Minimum draw probability. Defaults to 0.15.
        D (float, optional): Scaling factor for rating difference. Defaults to 400.0.

    Returns:
        float: 1.0 for A win, 0.5 for draw, 0.0 for A loss.
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

def update_ratings(ra: float, rb: float, result: float, k_factor: float = 10.0) -> Tuple[float, float]:
    """
    Update ratings for two players after a game.

    Args:
        ra (float): Rating of player A.
        rb (float): Rating of player B.
        result (float): Actual score for player A (1.0, 0.5, or 0.0).
        k_factor (float, optional): K-factor for rating updates. Defaults to 10.0.

    Returns:
        Tuple[float, float]: New ratings (ra_new, rb_new).
    """
    expected_a = elo_expected_score(ra, rb)
    change = k_factor * (result - expected_a)
    return ra + change, rb - change
