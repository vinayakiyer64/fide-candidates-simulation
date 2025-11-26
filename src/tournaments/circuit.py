from dataclasses import dataclass
from typing import List, Dict
from collections import defaultdict

from ..entities import Player, PlayerPool
from ..utils import weighted_sample
from .grand_swiss import GrandSwissSimulator

@dataclass
class CircuitTournament:
    name: str
    field_size: int
    rounds: int
    tar: float  # tournament average rating
    weight: float = 1.0  # classical=1.0, rapid<1, etc.


class FideCircuitSimulator:
    """
    Simulate an annual FIDE Circuit composed of several events.
    We simplify the points formula but keep the key structure.
    """

    def __init__(self,
                 players: PlayerPool,
                 num_qualifiers: int = 2,
                 tournaments: List[CircuitTournament] = None):
        self.players = players
        self.num_qualifiers = num_qualifiers
        if tournaments is None:
            # Some example events; replace with real data later
            self.tournaments = [
                CircuitTournament("SuperGM RR 1", 12, 11, 2750, 1.0),
                CircuitTournament("SuperGM RR 2", 10, 9, 2730, 1.0),
                CircuitTournament("Strong Open 1", 80, 9, 2650, 1.0),
                CircuitTournament("Strong Open 2", 80, 9, 2670, 1.0),
                CircuitTournament("SuperSwiss 1", 100, 11, 2700, 1.0),
            ]
        else:
            self.tournaments = tournaments

    def simulate_event(self, event: CircuitTournament) -> Dict[int, float]:
        """
        Simulate one event and return Circuit points per player id.
        Points formula:
            P = B * k * w
        with:
            B: basic points by rank
            k: (tar - 2500) / 100
            w: event.weight
        """
        # Choose participants: stronger players more likely
        field = weighted_sample(self.players,
                                min(event.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2600) / 200.0)

        # Run a Swiss-like tournament
        swiss = GrandSwissSimulator(field, num_qualifiers=0,
                                    field_size=len(field),
                                    rounds=event.rounds)
        standings = swiss.simulate_tournament()  # list of (player, score)

        # Basic points for top 8 in top half (approx)
        basic_points = [11, 8, 7, 6, 5, 4, 3, 2]  # winner gets 11
        k = max(0.0, (event.tar - 2500.0) / 100.0)
        w = event.weight

        points = defaultdict(float)
        top_half = standings[:len(standings) // 2]
        for i, (p, score) in enumerate(top_half[:8]):
            B = basic_points[i]
            P = B * k * w
            points[p.id] += P

        return points

    def simulate_circuit(self) -> List[Player]:
        """
        Return qualifiers by total circuit points over all events.
        """
        total_points = defaultdict(float)

        for event in self.tournaments:
            event_points = self.simulate_event(event)
            for pid, pts in event_points.items():
                total_points[pid] += pts

        # Sort players by points then Elo
        scored_players = [(p, total_points[p.id]) for p in self.players if total_points[p.id] > 0]
        if not scored_players:
            # If nobody scored (very small test), just return empty
            return []

        scored_players.sort(key=lambda x: (x[1], x[0].elo), reverse=True)

        qualifiers = []
        used_ids = set()
        for p, pts in scored_players:
            if p.id not in used_ids:
                qualifiers.append(p)
                used_ids.add(p.id)
            if len(qualifiers) >= self.num_qualifiers:
                break
        return qualifiers

