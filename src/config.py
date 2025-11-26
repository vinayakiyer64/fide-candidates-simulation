from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from src.allocation.base import AllocationStrategy
from src.allocation.strict_top_n import StrictTopNAllocation


class ParticipationMode(Enum):
    """
    How a player participates in the qualification cycle.

    FULL: Plays all tournaments, eligible for all qualification paths
    RATING_ONLY: Skips tournaments, eligible via rating only (preserves rating)
    EXCLUDED: Completely excluded (doesn't play, can't qualify)
    PLAYS_NOT_ELIGIBLE: Plays tournaments (affects Elo), but can't qualify (e.g., World Champion)
    """

    FULL = "full"
    RATING_ONLY = "rating_only"
    EXCLUDED = "excluded"
    PLAYS_NOT_ELIGIBLE = "plays_not_eligible"


@dataclass
class PlayerConfig:
    """
    Configuration for a specific player's participation in the cycle.

    Attributes:
        mode: Overall participation mode
        blocked_tournaments: Optional blacklist of tournaments the player will *not* enter.
                             None means no additional blocks (participate in all tournaments).
    """

    mode: ParticipationMode = ParticipationMode.FULL
    blocked_tournaments: Optional[Set[str]] = None


@dataclass
class TournamentSlot:
    """
    Configuration for a single tournament slot in the qualification cycle.

    Attributes:
        tournament_type: Type of tournament ('grand_swiss', 'world_cup', 'fide_circuit', 'rating').
        max_spots: Maximum number of qualification spots from this tournament.
        strategy: How spots are allocated from standings.
        kwargs: Additional arguments passed to the tournament constructor.
        qualified_skip_prob: Probability that already-qualified players skip this tournament.
                            0.0 = always play, 1.0 = always skip.
    """
    tournament_type: str
    max_spots: int
    strategy: AllocationStrategy = field(default_factory=StrictTopNAllocation)
    qualified_skip_prob: float = 0.0    
    kwargs: Dict[str, Any] = field(default_factory=dict)



@dataclass 
class QualificationConfig:
    """
    Configuration for a full qualification cycle.

    Attributes:
        target_candidates: Total number of candidates to qualify (default 8).
        slots: Ordered list of tournament slots. Order determines priority.
        player_configs: Per-player configuration overrides. Key is player ID.
    """
    target_candidates: int = 8
    slots: List[TournamentSlot] = field(default_factory=list)
    player_configs: Dict[int, PlayerConfig] = field(default_factory=dict)
    tournament_factories: Dict[str, Callable[..., Any]] = field(default_factory=dict)
