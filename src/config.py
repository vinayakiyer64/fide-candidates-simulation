from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from src.allocation.base import AllocationStrategy
from src.allocation.strict_top_n import StrictTopNAllocation
from src.allocation.spillover import SpilloverAllocation

@dataclass
class TournamentSlot:
    """
    Configuration for a single tournament slot in the qualification cycle.

    Attributes:
        tournament_type (str): Type of tournament ('grand_swiss', 'world_cup', 'fide_circuit').
        max_spots (int): Maximum number of qualification spots from this tournament.
        strategy (AllocationStrategy): How spots are allocated from standings.
        kwargs (Dict): Additional arguments passed to the tournament constructor.
    """
    tournament_type: str
    max_spots: int
    strategy: AllocationStrategy = field(default_factory=StrictTopNAllocation)
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class QualificationConfig:
    """
    Configuration for a full qualification cycle.

    Attributes:
        target_candidates (int): Total number of candidates to qualify (default 8).
        slots (List[TournamentSlot]): Ordered list of tournament slots.
                                      Order determines priority.
    """
    target_candidates: int = 8
    slots: List[TournamentSlot] = field(default_factory=list)

