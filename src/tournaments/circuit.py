from dataclasses import dataclass
from typing import List, Dict
from collections import defaultdict

from src.entities import Player, PlayerPool
from src.utils import weighted_sample
from src.tournaments.base import Tournament
from src.tournaments.grand_swiss import GrandSwissSimulator

@dataclass
class CircuitEvent:
    """
    Configuration for a single event within the FIDE Circuit.
    """
    name: str
    field_size: int
    rounds: int
    tar: float  # Tournament Average Rating
    weight: float = 1.0


class FideCircuitSimulator(Tournament):
    """
    Simulate the FIDE Circuit, a series of tournaments where players earn points.
    """

    def __init__(self,
                 players: PlayerPool,
                 events: List[CircuitEvent] = None):
        """
        Initialize the FIDE Circuit simulator.

        Args:
            players (PlayerPool): Pool of available players.
            events (List[CircuitEvent], optional): List of events. Defaults to standard set.
        """
        super().__init__(players)
        if events is None:
            self.events = [
                CircuitEvent("SuperGM RR 1", 12, 11, 2750, 1.0),
                CircuitEvent("SuperGM RR 2", 10, 9, 2730, 1.0),
                CircuitEvent("Strong Open 1", 80, 9, 2650, 1.0),
                CircuitEvent("Strong Open 2", 80, 9, 2670, 1.0),
                CircuitEvent("SuperSwiss 1", 100, 11, 2700, 1.0),
            ]
        else:
            self.events = events

    def _simulate_event(self, event: CircuitEvent) -> Dict[int, float]:
        """
        Simulate one circuit event and calculate points.
        """
        field = weighted_sample(self.players,
                                min(event.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2600) / 200.0)

        swiss = GrandSwissSimulator(field, field_size=len(field), rounds=event.rounds)
        standings = swiss.get_standings(top_n=len(field))

        basic_points = [11, 8, 7, 6, 5, 4, 3, 2]
        k = max(0.0, (event.tar - 2500.0) / 100.0)
        w = event.weight

        points = defaultdict(float)
        top_half = standings[:len(standings) // 2]
        
        for i, p in enumerate(top_half[:8]):
            B = basic_points[i]
            P = B * k * w
            points[p.id] += P

        return points

    def get_standings(self, top_n: int = 10) -> List[Player]:
        """
        Simulate the full circuit and return standings by total points.
        """
        total_points = defaultdict(float)

        for event in self.events:
            event_points = self._simulate_event(event)
            for pid, pts in event_points.items():
                total_points[pid] += pts

        # Create list of (player, points) for players who scored
        player_map = {p.id: p for p in self.players}
        scored = [(player_map[pid], pts) for pid, pts in total_points.items() if pts > 0]
        
        # Sort by points, then Elo
        scored.sort(key=lambda x: (x[1], x[0].elo), reverse=True)
        
        standings = [p for p, pts in scored]
        return standings[:top_n]
