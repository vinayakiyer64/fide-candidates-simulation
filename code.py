import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
from collections import defaultdict, Counter

# ==============================
# 1. Basic player representation
# ==============================

@dataclass
class Player:
    id: int
    name: str
    elo: float
    initial_rank: int  # rank by Elo
    # You can add federation, age, etc. if needed

# Helper type
PlayerPool = List[Player]


# =======================
# 2. Elo + draw model
# =======================

def elo_expected_score(ra: float, rb: float) -> float:
    """Expected score for player A vs player B."""
    return 1.0 / (1.0 + 10 ** (-(ra - rb) / 400.0))


def game_outcome_with_draws(ra: float,
                            rb: float,
                            d0: float = 0.40,
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
    p_loss = max(0.0, 1.0 - p_win - p_draw)

    # Sample outcome
    u = random.random()
    if u < p_win:
        return 1.0
    elif u < p_win + p_draw:
        return 0.5
    else:
        return 0.0


# ==================================================
# 3. Helpers for tournament sampling & random seeds
# ==================================================

def weighted_sample(players: PlayerPool,
                    k: int,
                    weight_fn: Optional[Callable[[Player], float]] = None) -> PlayerPool:
    """Sample k distinct players, optionally weighted by weight_fn."""
    if weight_fn is None:
        return random.sample(players, k)
    weights = [weight_fn(p) for p in players]
    total = sum(weights)
    probs = [w / total for w in weights]
    # naive algorithm for k << n
    chosen = []
    available = players[:]
    available_probs = probs[:]
    for _ in range(k):
        x = random.random()
        cum = 0.0
        for i, (p, pr) in enumerate(zip(available, available_probs)):
            cum += pr
            if x <= cum:
                chosen.append(p)
                # remove
                del available[i]
                del available_probs[i]
                s = sum(available_probs) or 1.0
                available_probs = [w / s for w in available_probs]
                break
    return chosen


# =====================================
# 4. World Cup (knockout) simulator
# =====================================

class WorldCupSimulator:
    """
    Simulate a knockout World Cup.
    We ignore color assignments and tiebreak time controls and approximate
    each match by a small number of classical-like games.
    """

    def __init__(self,
                 players: PlayerPool,
                 num_qualifiers: int = 3,
                 field_size: int = 128,
                 games_per_match: int = 2):
        self.players = players
        self.num_qualifiers = num_qualifiers
        self.field_size = field_size
        self.games_per_match = games_per_match

    def simulate_match(self, a: Player, b: Player) -> Player:
        """Return winner of a mini-match between players A and B."""
        score_a = 0.0
        score_b = 0.0
        for _ in range(self.games_per_match):
            res = game_outcome_with_draws(a.elo, b.elo)
            if res == 1.0:
                score_a += 1.0
            elif res == 0.5:
                score_a += 0.5
                score_b += 0.5
            else:
                score_b += 1.0

        if score_a > score_b:
            return a
        elif score_b > score_a:
            return b
        # Tiebreak: assume higher Elo has slight edge
        ea = elo_expected_score(a.elo, b.elo)
        if random.random() < ea:
            return a
        else:
            return b

    def simulate_tournament(self) -> List[Player]:
        """
        Return a list of players sorted by finishing position (1st, 2nd, 3rd, ...).
        """
        # Choose field_size players, biased to include stronger players more often
        field = weighted_sample(self.players,
                                min(self.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2600) / 200.0)

        # Random initial seeding by Elo (you can mimic FIDE seeding later)
        field = sorted(field, key=lambda p: p.elo, reverse=True)

        # Knockout bracket
        current = field[:]
        positions = []  # will store losers in reverse finishing order
        while len(current) > 1:
            next_round = []
            # pair top vs bottom etc.
            for i in range(len(current) // 2):
                a = current[i]
                b = current[-(i+1)]
                winner = self.simulate_match(a, b)
                loser = b if winner is a else a
                positions.append(loser)
                next_round.append(winner)
            current = next_round

        # Champion is remaining player
        champion = current[0]
        positions.append(champion)

        # positions now has [round1 losers, round2 losers, ..., champion]
        # Roughly interpret last elements as top finishers:
        positions_sorted = positions[::-1]  # champion first
        return positions_sorted

    def get_qualifiers(self) -> List[Player]:
        standings = self.simulate_tournament()
        # Take top num_qualifiers distinct players
        return standings[:self.num_qualifiers]


# =====================================
# 5. Grand Swiss simulator (Swiss)
# =====================================

class GrandSwissSimulator:
    """
    Approximate 11-round Swiss with N players.
    We group players by score and pair within groups.
    """

    def __init__(self,
                 players: PlayerPool,
                 num_qualifiers: int = 2,
                 field_size: int = 110,
                 rounds: int = 11):
        self.players = players
        self.num_qualifiers = num_qualifiers
        self.field_size = field_size
        self.rounds = rounds

    def simulate_tournament(self) -> List[Tuple[Player, float]]:
        field = weighted_sample(self.players,
                                min(self.field_size, len(self.players)),
                                weight_fn=lambda p: 1.0 + max(0, p.elo - 2600) / 200.0)

        scores = {p.id: 0.0 for p in field}

        for _ in range(self.rounds):
            # Group by score (approximate Swiss)
            groups = defaultdict(list)
            for p in field:
                groups[scores[p.id]].append(p)

            new_scores = scores.copy()

            for score_group, group_players in groups.items():
                random.shuffle(group_players)
                # pair them in order
                for i in range(0, len(group_players), 2):
                    if i + 1 >= len(group_players):
                        # bye: assign half point
                        new_scores[group_players[i].id] += 0.5
                        continue
                    a = group_players[i]
                    b = group_players[i+1]
                    res = game_outcome_with_draws(a.elo, b.elo)
                    if res == 1.0:
                        new_scores[a.id] += 1.0
                    elif res == 0.5:
                        new_scores[a.id] += 0.5
                        new_scores[b.id] += 0.5
                    else:
                        new_scores[b.id] += 1.0
            scores = new_scores

        # Final standings: score, then Elo as tiebreak
        standings = sorted(field,
                           key=lambda p: (scores[p.id], p.elo),
                           reverse=True)
        return [(p, scores[p.id]) for p in standings]

    def get_qualifiers(self) -> List[Player]:
        standings = self.simulate_tournament()
        return [p for p, s in standings[:self.num_qualifiers]]


# ==================================
# 6. FIDE Circuit simulator
# ==================================

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


# =========================================
# 7. Qualification system + Monte Carlo
# =========================================

@dataclass
class QualificationConfig:
    num_rating: int
    num_world_cup: int
    num_grand_swiss: int
    num_circuit: int


class QualificationSimulator:
    def __init__(self,
                 players: PlayerPool,
                 config: QualificationConfig):
        # Players sorted by Elo descending
        self.players = sorted(players, key=lambda p: p.elo, reverse=True)
        self.config = config

    def rating_qualifiers(self, already_qualified_ids: set) -> List[Player]:
        qualifiers = []
        for p in self.players:
            if p.id in already_qualified_ids:
                continue
            qualifiers.append(p)
            already_qualified_ids.add(p.id)
            if len(qualifiers) >= self.config.num_rating:
                break
        return qualifiers

    def simulate_one_season(self) -> List[Player]:
        """
        Simulate all qualification paths and return list of unique qualifiers.
        """
        qualified_ids = set()
        qualifiers = []

        # World Cup
        if self.config.num_world_cup > 0:
            wc_sim = WorldCupSimulator(self.players, self.config.num_world_cup)
            wc_qualifiers = wc_sim.get_qualifiers()
            for p in wc_qualifiers:
                if p.id not in qualified_ids:
                    qualified_ids.add(p.id)
                    qualifiers.append(p)

        # Grand Swiss
        if self.config.num_grand_swiss > 0:
            gs_sim = GrandSwissSimulator(self.players, self.config.num_grand_swiss)
            gs_qualifiers = gs_sim.get_qualifiers()
            for p in gs_qualifiers:
                if p.id not in qualified_ids:
                    qualified_ids.add(p.id)
                    qualifiers.append(p)

        # FIDE Circuit
        if self.config.num_circuit > 0:
            circuit_sim = FideCircuitSimulator(self.players, self.config.num_circuit)
            circuit_qualifiers = circuit_sim.simulate_circuit()
            for p in circuit_qualifiers:
                if p.id not in qualified_ids:
                    qualified_ids.add(p.id)
                    qualifiers.append(p)

        # Rating
        if self.config.num_rating > 0:
            rating_qualifiers = self.rating_qualifiers(qualified_ids)
            qualifiers.extend(rating_qualifiers)

        # Ensure we have at most 8 for Candidates
        qualifiers = qualifiers[:8]
        return qualifiers


def run_monte_carlo(players: PlayerPool,
                    config: QualificationConfig,
                    num_seasons: int = 1000,
                    seed: Optional[int] = None) -> Dict:
    """
    Run many simulated seasons and compute fairness metrics.
    """
    if seed is not None:
        random.seed(seed)

    qual_sim = QualificationSimulator(players, config)

    qual_counts = Counter()
    elo_sums = 0.0
    elo_sums_sq = 0.0
    total_seasons_with_full_8 = 0

    for _ in range(num_seasons):
        quals = qual_sim.simulate_one_season()
        if len(quals) < 1:
            continue
        total_seasons_with_full_8 += 1
        avg_elo = sum(p.elo for p in quals) / len(quals)
        elo_sums += avg_elo
        elo_sums_sq += avg_elo ** 2
        for p in quals:
            qual_counts[p.id] += 1

    # per-player qualification probability
    qual_probs = {
        p.id: qual_counts[p.id] / total_seasons_with_full_8
        for p in players
    }

    # average & variance of average Elo of qualifiers
    mean_avg_elo = elo_sums / max(1, total_seasons_with_full_8)
    var_avg_elo = (elo_sums_sq / max(1, total_seasons_with_full_8)) - mean_avg_elo ** 2

    # Correlation between Elo rank and qualification probability (approx)
    ranks = [p.initial_rank for p in players]
    probs = [qual_probs[p.id] for p in players]
    rank_mean = sum(ranks) / len(ranks)
    prob_mean = sum(probs) / len(probs)
    cov = sum((r - rank_mean) * (q - prob_mean) for r, q in zip(ranks, probs)) / len(ranks)
    var_rank = sum((r - rank_mean) ** 2 for r in ranks) / len(ranks)
    var_prob = sum((q - prob_mean) ** 2 for q in probs) / len(probs)
    if var_rank > 0 and var_prob > 0:
        corr_rank_prob = cov / math.sqrt(var_rank * var_prob)
    else:
        corr_rank_prob = 0.0

    return {
        "mean_avg_elo": mean_avg_elo,
        "var_avg_elo": var_avg_elo,
        "qual_probs": qual_probs,
        "corr_rank_prob": corr_rank_prob,
        "total_seasons": total_seasons_with_full_8,
    }


# ===================================
# 8. Example usage (with dummy data)
# ===================================

if __name__ == "__main__":
    # TODO: replace with real 2700chess/FIDE list
    # Here we create a toy pool: top 150 players with descending Elo
    players = []
    base_elo = 2850
    for i in range(150):
        elo = base_elo - i * 5  # simple gradient
        players.append(Player(
            id=i,
            name=f"Player_{i+1}",
            elo=elo,
            initial_rank=i+1
        ))

    # Current system config (example): 1 rating, 3 WC, 2 GS, 2 Circuit
    current_cfg = QualificationConfig(
        num_rating=1,
        num_world_cup=3,
        num_grand_swiss=2,
        num_circuit=2
    )

    res_current = run_monte_carlo(players, current_cfg, num_seasons=500, seed=42)
    print("Current system mean avg Elo of qualifiers:", res_current["mean_avg_elo"])
    print("Correlation between Elo rank and qualification prob:",
          res_current["corr_rank_prob"])

    # Alt 1: 2 rating, 2 WC, 2 GS, 2 Circuit
    alt1_cfg = QualificationConfig(
        num_rating=2,
        num_world_cup=2,
        num_grand_swiss=2,
        num_circuit=2
    )
    res_alt1 = run_monte_carlo(players, alt1_cfg, num_seasons=500, seed=43)
    print("Alt1 mean avg Elo:", res_alt1["mean_avg_elo"])

    # Alt 2: 3 rating, 2 WC, 3 Circuit, (e.g. 0 GS or adjust as you like)
    alt2_cfg = QualificationConfig(
        num_rating=3,
        num_world_cup=2,
        num_grand_swiss=0,
        num_circuit=3
    )
    res_alt2 = run_monte_carlo(players, alt2_cfg, num_seasons=500, seed=44)
    print("Alt2 mean avg Elo:", res_alt2["mean_avg_elo"])
