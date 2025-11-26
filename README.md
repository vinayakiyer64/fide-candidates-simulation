# FIDE Candidates Simulation

Monte Carlo simulation of the FIDE World Championship qualification cycle to evaluate the fairness of different qualification systems.

## Overview

The simulator plays out the official qualification cycle **sequentially**:

1. Each configured tournament runs with the players who actually participate.
2. Elo is updated after every game, so later events use “live” ratings.
3. Allocation rules (strict top-N, FIDE Circuit spillover, rating fallback) are applied immediately.
4. Already-qualified players are removed from future events (or can skip with a probability).

The four qualification paths are:
- **Grand Swiss** – Swiss-system event (2 spots per slot)
- **World Cup** – Knockout event (3 spots per slot)
- **FIDE Circuit** – Series of events with spillover logic (base 2, +1 if duplicates)
- **Rating** – Highest-rated non-qualified players (fills the remainder)

Each season is simulated hundreds of times to measure fairness metrics such as the average Elo of qualifiers and the percentage of “true” top-8 players who qualify.

## Project Structure

```
fide-candidates-simulation/
├── data/
│   └── players.json              # FIDE Top 100 players
├── src/
│   ├── entities.py               # Player dataclass
│   ├── game_logic.py             # Elo expected score, game simulation, rating updates
│   ├── utils.py                  # Weighted sampling, player pool augmentation
│   ├── config.py                 # QualificationConfig, TournamentSlot, PlayerConfig
│   ├── participation.py          # ParticipationManager (eligibility, withdrawals)
│   ├── scenario_builder.py       # Fluent helpers for assembling scenarios
│   ├── simulation.py             # Sequential QualificationSimulator + run_monte_carlo
│   ├── tournament_registry.py    # Default tournament factory mapping
│   ├── tournaments/
│   │   ├── base.py               # Abstract Tournament class
│   │   ├── world_cup.py          # Knockout format (128 players)
│   │   ├── grand_swiss.py        # Swiss format (110 players, 11 rounds)
│   │   └── circuit.py            # FIDE Circuit (series of events)
│   └── allocation/
│       ├── base.py               # Abstract AllocationStrategy class
│       ├── strict_top_n.py       # Top N only (spots lost if player already qualified)
│       ├── circuit.py            # Base 2, +1 spillover if duplicates, max 3
│       └── rating.py             # Guaranteed 1 + fill remainder
├── scripts/
│   └── scrape_fide.py            # Scraper for FIDE Top 100
├── main.py                       # Entry point with scenario definitions
└── requirements.txt
```

## Installation

```bash
# Clone the repository
git clone https://github.com/vinayakiyer64/fide-candidates-simulation.git
cd fide-candidates-simulation

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (only needed for scraping)
pip install -r requirements.txt
```

## Usage

### Run the Simulation

```bash
python3 main.py
```

Sample output (truncated):

```
Loaded 100 real players. Augmenting pool...
Total player pool size after augmentation: 334
Top player: Carlsen, Magnus (2839.0)

Running Simulations (1000 seasons each)...
Scenario                                 | Orig Elo | Live Elo | StdDev(Elo) | Top8 Qual%
------------------------------------------------------------------------------------------
Current System                           | 2755.8   | 2769.8   | 13.7        | 48.0%
Pure Rating (Reference)                  | 2786.2   | 2786.2   | 0.0         | 100.0%
More Rating Spots (-2 WC)                | 2766.8   | 2777.4   | 11.4        | 62.1%
...
```

### Update Player Data

```bash
python3 scripts/scrape_fide.py
```

This fetches the current FIDE Top 100 from `ratings.fide.com`.

## Scenarios

| Scenario | Grand Swiss | World Cup | Circuit | Rating |
|----------|-------------|-----------|---------|--------|
| Current System | 2 | 3 | 2-3 | 1+ |
| Pure Rating | - | - | - | 8 |
| More Rating (-2 WC) | 2 | 1 | 2-3 | 1+ |
| More Circuit (-2 WC) | 2 | 1 | 2-4 | 1+ |
| Grand Slam (No WC) | 4 | - | 2-3 | 1+ |

## Participation Modes

Player behavior is configured via `PlayerConfig`:

| Mode | Plays Tournaments? | Eligible for Spots? | Example Use |
|------|-------------------|---------------------|-------------|
| `FULL` (default) | ✅ Yes | ✅ Yes | Most players |
| `PLAYS_NOT_ELIGIBLE` | ✅ Yes | ❌ No | Reigning World Champion (plays to keep form, already qualified) |
| `EXCLUDED` | ❌ No | ❌ No | Retired or withdrawn players |
| `RATING_ONLY` | ❌ No | ✅ Rating fallback only | High-rated players preserving Elo (e.g., Nakamura) |

Additional controls:
- `blocked_tournaments`: Blacklist specific tournaments (player will skip only those events).
- `qualified_skip_prob` (per TournamentSlot): already-qualified players skip later events with this probability to model strategic rest.

All participation/eligibility logic lives in `ParticipationManager`, keeping responsibilities isolated (SRP) while letting scenarios stay declarative.

## Allocation Rules

The simulation implements FIDE's actual qualification rules:

1. **Grand Swiss / World Cup**: Strict Top-N. If a top finisher already qualified via a higher-priority path, that spot is **lost** (not passed down).

2. **FIDE Circuit**: Base 2 spots. Gets a 3rd spot **only if** there's a duplicate (a Circuit top finisher already qualified via GS/WC).

3. **Rating**: Guaranteed 1 spot for the highest-rated non-qualified player. Fills all remaining spots to reach 8 candidates.

Priority order: Grand Swiss → World Cup → Circuit → Rating

## Key Metrics

- **Orig Elo**: Average pre-season Elo of the qualifiers (true strength baseline)
- **Live Elo**: Average post-season Elo after all games (who actually performed)
- **StdDev(Elo)**: Standard deviation of the average live Elo across seasons (volatility of the format)
- **Top 8 Qual%**: How often the “true” top 8 by Elo qualified

## Key Findings

- **World Cup volatility**: The knockout format introduces significant randomness. Reducing WC spots increases the probability that the strongest players qualify.
- **Rating is most meritocratic**: Pure rating selection guarantees 100% of the true top 8 qualify.
- **Current system trade-off**: Balances competitive excitement (tournaments) with meritocracy (rating spots).

## Extending the Simulation

### Add a New Tournament Type

1. Create a new class in `src/tournaments/` inheriting from `Tournament`
2. Implement `get_standings(top_n: int) -> List[Player]`
3. Register it in `QualificationSimulator._create_tournament()`

### Add a New Allocation Strategy

1. Create a new class in `src/allocation/` inheriting from `AllocationStrategy`
2. Implement `allocate(standings, max_spots, already_qualified) -> List[Player]`
3. Use it in a `TournamentSlot` in `main.py`

### Define a New Scenario

```python
config_custom = QualificationConfig(
    target_candidates=8,
    slots=[
        TournamentSlot("grand_swiss", max_spots=3, strategy=StrictTopNAllocation()),
        TournamentSlot("world_cup", max_spots=2, strategy=StrictTopNAllocation()),
        TournamentSlot("fide_circuit", max_spots=2, strategy=CircuitAllocation(base_spots=2, max_spots=2)),
        TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
    ]
)
```

## License

MIT
