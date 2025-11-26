from dataclasses import dataclass
from typing import List, Dict
from collections import defaultdict

from src.entities import Player, PlayerPool
from src.utils import weighted_sample
from src.tournaments.base import Tournament
from src.tournaments.grand_swiss import GrandSwissSimulator

@dataclass
class CircuitTournament:
    """
    Configuration for a single event within the FIDE Circuit.

    Attributes:
        name (str): Name of the event.
        field_size (int): Number of players.
        rounds (int): Number of rounds.
        tar (float): Tournament Average Rating (approximate).
        weight (float): Event weight (1.0 for classical, less for rapid/blitz).
    """
    name: str
    field_size: int
    rounds: int
    tar: float  # tournament average rating
    weight: float = 1.0  # classical=1.0, rapid<1, etc.


class FideCircuitSimulator(Tournament):
    """
    Simulate the FIDE Circuit, a series of tournaments where players earn points.
    """

    def __init__(self,
                 players: PlayerPool,
                 num_qualifiers: int = 2,
                 tournaments: List[CircuitTournament] = None):
        """
        Initialize the FIDE Circuit simulator.

        Args:
            players (PlayerPool): Pool of available players.
            num_qualifiers (int, optional): Number of qualification spots. Defaults to 2.
            tournaments (List[CircuitTournament], optional): List of events. Defaults to standard set.
        """
        super().__init__(players, num_qualifiers)
        if tournaments is None:
            # Standard example events
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
        Simulate one circuit event and calculate points.

        Args:
            event (CircuitTournament): The event to simulate.

        Returns:
            Dict[int, float]: Map of player_id -> points earned.
        """
        # Choose participants: stronger players more likely
        field = weighted_sample(self.players,
                                min(event.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2600) / 200.0)

        # Run a Swiss-like tournament (or Round Robin approximated as Swiss)
        swiss = GrandSwissSimulator(field, num_qualifiers=0,
                                    field_size=len(field),
                                    rounds=event.rounds)
        standings = swiss.simulate_tournament()  # list of (player, score)

        # Basic points for top 8 in top half (approx)
        # FIDE rules are complex; this is a simplified model.
        basic_points = [11, 8, 7, 6, 5, 4, 3, 2]  # winner gets 11
        
        # K factor depends on tournament strength (TAR)
        k = max(0.0, (event.tar - 2500.0) / 100.0)
        w = event.weight

        points = defaultdict(float)
        top_half = standings[:len(standings) // 2]
        
        # Assign points to top 8 finishers
        for i, (p, score) in enumerate(top_half[:8]):
            B = basic_points[i]
            P = B * k * w
            points[p.id] += P

        return points

    def get_qualifiers(self) -> List[Player]:
        """
        Simulate the full circuit and return qualifiers.

        Returns:
            List[Player]: The qualified players based on total circuit points.
        """
        total_points = defaultdict(float)

        for event in self.tournaments:
            event_points = self.simulate_event(event)
            for pid, pts in event_points.items():
                total_points[pid] += pts

        # Sort players by points then Elo
        scored_players = [(p, total_points[p.id]) for p in self.players if total_points[p.id] > 0]
        if not scored_players:
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
