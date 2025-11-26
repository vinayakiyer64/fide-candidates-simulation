"""
Default tournament factory registry.

This module centralizes the mapping from string identifiers to concrete
Tournament classes so that the simulation code does not hard-code imports.
"""

from typing import Callable, Dict, Type

from src.entities import PlayerPool
from src.tournaments.base import Tournament
from src.tournaments.world_cup import WorldCupSimulator
from src.tournaments.grand_swiss import GrandSwissSimulator
from src.tournaments.circuit import FideCircuitSimulator

TournamentFactory = Callable[..., Tournament]


DEFAULT_TOURNAMENT_FACTORIES: Dict[str, TournamentFactory] = {
    "world_cup": WorldCupSimulator,
    "grand_swiss": GrandSwissSimulator,
    "fide_circuit": FideCircuitSimulator,
}

