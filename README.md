# FIDE Candidates Simulation

Monte Carlo simulation of the FIDE World Championship qualification cycle to evaluate the fairness of different qualification systems.

## Overview

The simulator plays out the official qualification cycle **sequentially**:

1. Each configured tournament runs with the players who actually participate.
2. Elo is updated after every game, so later events use "live" ratings.
3. Allocation rules (strict top-N, FIDE Circuit spillover, rating fallback) are applied immediately.
4. Already-qualified players are removed from future events (or can skip with a probability).

The four qualification paths are:
- **Grand Swiss** – Swiss-system event (2 spots per slot)
- **World Cup** – Knockout event (3 spots per slot)
- **FIDE Circuit** – Series of events with spillover logic (base 2, +1 if duplicates)
- **Rating** – Highest-rated non-qualified players (fills the remainder)

Each season is simulated hundreds of times to measure fairness metrics such as the average Elo of qualifiers and the percentage of "true" top-8 players who qualify.

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

Sample output:

```
Loaded 100 real players. Augmenting pool...
Total player pool size after augmentation: 323
Top player: Carlsen, Magnus (2839.0)

Key players:
  Magnus: Carlsen, Magnus (ID: 1503014)
  Nakamura: Nakamura, Hikaru (ID: 2016192)
  Gukesh: Gukesh D (ID: 46616543)
  Caruana: Caruana, Fabiano (ID: 2020009)

Running Simulations (1000 seasons each)...
Scenario                            | Orig Elo | Live Elo | StdDev | Top8%  | <2700  | <2650  | MinElo
-----------------------------------------------------------------------------------------------------------------------------
Scenario 1: Base Structure          | 2754.9   | 2768.9   | 14.3   | 49.3%  | 0.82   | 0.180  | 2687
Scenario 2: Strategic Participation | 2741.0   | 2756.4   | 12.9   | 39.5%  | 0.98   | 0.175  | 2682
Scenario 3: Fewer GS/WC Slots       | 2752.9   | 2767.7   | 11.1   | 52.7%  | 0.63   | 0.101  | 2698
Scenario 4: Two Swiss Events        | 2741.8   | 2757.5   | 13.0   | 40.2%  | 0.97   | 0.189  | 2683
Scenario 5: Swiss Focus (Gukesh WC) | 2756.0   | 2771.2   | 14.0   | 50.1%  | 0.78   | 0.149  | 2691
Scenario 6: Pure Rating             | 2786.2   | 2786.2   | 0.0    | 100.0% | 0.00   | 0.000  | 2764

Top 15 Qualification Probabilities (Current System)
----------------------------------------------------------------------
Rank   | Player                         | Orig Elo   | Qual Prob 
----------------------------------------------------------------------
1      | Carlsen, Magnus                | 2839       | 95.6%
2      | Nakamura, Hikaru               | 2813       | 79.0%
3      | Caruana, Fabiano               | 2795       | 58.1%
4      | Keymer, Vincent                | 2773       | 35.0%
5      | Erigaisi Arjun                 | 2769       | 34.1%
6      | Giri, Anish                    | 2769       | 31.8%
7      | Praggnanandhaa R               | 2768       | 31.7%
8      | So, Wesley                     | 2764       | 29.1%
9      | Firouzja, Alireza              | 2762       | 26.7%
10     | Wei, Yi                        | 2752       | 20.6%
```

### Update Player Data

```bash
python3 scripts/scrape_fide.py
```

This fetches the current FIDE Top 100 from `ratings.fide.com`.

## Parameter Choices & Assumptions

- **Tournament order:** `base_slots()` schedules a small "direct" circuit slot (strict top‑N), then the Grand Swiss (2 spots), World Cup (3 spots), a larger circuit slot with spillover logic (base 1 + bonus spot if GS/WC duplicates), and finally the rating fallback. Scenarios tweak this list as needed.
- **Participant sampling:** Each event draws a weighted sample of the augmented player pool (weights grow with Elo) to mimic invite lists that favor top players while still allowing room for lower‑rated entrants.
- **Elo updates:** Every game/match calls `update_ratings`, so later events see "live" ratings that incorporate performance to date.
- **Skip probability:** Each `TournamentSlot` can assign `qualified_skip_prob`. A value of `0.5`, for example, causes already-qualified players to skip the next event 50 % of the time, modeling strategic rest.
- **Player modes:** `PlayerConfig` drives whether a player plays, is eligible, or is rating-only. Use `blocked_tournaments` for fine-grained exclusions.

## Scenarios

| Scenario | Description | GS slots | WC slots | Circuit slots | Rating policy |
|----------|-------------|----------|----------|---------------|---------------|
| 1. Base Structure | Everyone except Gukesh (plays but ineligible as reigning WC), skip prob = 0 | 2 | 3 | 1 direct + 2 spillover | fills remainder |
| 2. Strategic Participation | Magnus excluded, Gukesh WC, Hikaru rating-only, skip prob 0.5 | 2 | 3 | 1 + 2 | fills remainder |
| 3. Fewer GS/WC Slots | Scenario 2 but GS=1 and WC=2 (extra seats flow to rating) | 1 | 2 | 1 + 2 | fills remainder |
| 4. Two Swiss Events | Scenario 2 with two independent Swiss events (1 slot each) around WC | 1 + 1 | 3 | 1 + 2 | fills remainder |
| 5. Swiss Focus (Gukesh WC) | Scenario 4 but only Gukesh is WC; Magnus & Hikaru play | 1 + 1 | 3 | 1 + 2 | fills remainder |
| 6. Pure Rating | No tournaments – top 8 by current Elo | – | – | – | 8 rating spots |

## Participation Modes

Player behavior is configured via `PlayerConfig`:

| Mode | Plays Tournaments? | Eligible for Spots? | Example Use |
|------|-------------------|---------------------|-------------|
| `FULL` (default) | ✅ Yes | ✅ Yes | Most players |
| `PLAYS_NOT_ELIGIBLE` | ✅ Yes | ❌ No | Reigning World Champion (plays to keep form, already qualified) |
| `EXCLUDED` | ❌ No | ❌ No | Retired or withdrawn players |
| `RATING_ONLY` | ❌ No | ✅ Rating fallback only | High-rated players preserving Elo (e.g., Nakamura) |

Additional controls:

- `blocked_tournaments`: blacklist specific events at the player level (e.g., "never plays World Cup").
- `qualified_skip_prob` (per `TournamentSlot`): once qualified, a player skips later events with this probability (models strategic rest).

All participation/eligibility logic lives in `src/participation.py`, keeping behavior isolated while scenarios remain declarative.

## Allocation Rules

The simulation implements FIDE's actual qualification rules:

1. **Grand Swiss / World Cup**: Strict Top-N. If a top finisher already qualified via a higher-priority path, that spot is **lost** (not passed down).

2. **FIDE Circuit**: Base 2 spots. Gets a 3rd spot **only if** there's a duplicate (a Circuit top finisher already qualified via GS/WC).

3. **Rating**: Guaranteed 1 spot for the highest-rated non-qualified player. Fills all remaining spots to reach 8 candidates.

Priority order: Grand Swiss → World Cup → Circuit → Rating

## Key Metrics

- **Orig Elo**: Average pre-season Elo of the qualifiers (true strength baseline)
- **Live Elo**: Average post-season Elo after all games (who actually performed)
- **StdDev**: Standard deviation of the average live Elo across seasons (volatility of the format)
- **Top8%**: How often the "true" top 8 by Elo qualified (fairness measure)
- **<2700**: Average number of qualifiers per season with live Elo below 2700 (outlier risk)
- **<2650**: Average number of qualifiers per season with live Elo below 2650 (extreme outlier risk)
- **MinElo**: Average minimum Elo among the 8 qualifiers (floor quality)

## Key Findings

- **Participation drives most variance.** Scenario 2 (Magnus out, Hikaru rating-only, skip = 0.5) drops the top‑8 hit rate to ~40% even though the event structure is unchanged. When those players return (Scenario 5), metrics rebound to the base case (~50%).
- **Structural tweaks still matter.** Reclaiming GS/WC seats for the rating list (Scenario 3) raises the top‑8 hit rate from ~49% to ~53% and reduces both Elo volatility (StdDev ~11 vs ~14) and outlier risk (<2700 drops from 0.82 to 0.63).
- **Extra Swiss events alone don't fix strategic behavior.** Scenario 4 still underperforms because the strongest players are absent; format changes can only do so much if participation is low.
- **Pure rating (Scenario 6)** guarantees the strongest possible field (Orig/Live Elo ~2786, StdDev 0, no outliers) but removes competitive variance entirely.
- **Outlier risk is real.** The baseline (Scenario 1) averages ~0.8 qualifiers below 2700 Elo per season, with the minimum qualifier averaging around 2687. Scenario 3 (fewer GS/WC slots) improves this floor to ~2698.

Overall, the model suggests that randomness in Candidate qualification is more sensitive to who plays (or skips) than to the exact arrangement of GS/WC/Circuit slots. 

## Extending the Simulation

### Add a New Tournament Type

1. Implement a subclass of `src.tournaments.base.Tournament` (e.g., `MyOpenEvent`) with a `get_standings(top_n: int)` method that mutates Elo as needed.
2. Register it in `src/tournament_registry.DEFAULT_TOURNAMENT_FACTORIES` so scenarios can reference it by string (e.g., `"my_open"`).
3. Optionally provide a custom `tournament_factories` dict via `QualificationConfig` if a scenario needs a one-off variant.

### Add a New Allocation Strategy

1. Create a class in `src/allocation/` inheriting from `AllocationStrategy`.
2. Implement `allocate(self, standings, max_spots, already_qualified) -> list[Player]`.
3. Use it inside a `TournamentSlot(strategy=YourStrategy(...))` when building scenarios.

### Define a New Scenario

Use `ScenarioBuilder` to keep configurations modular:

```python
from src.scenario_builder import ScenarioBuilder
from src.config import PlayerConfig, ParticipationMode
from src.allocation.strict_top_n import StrictTopNAllocation

custom_slots = [
    TournamentSlot("grand_swiss", max_spots=1, strategy=StrictTopNAllocation(), qualified_skip_prob=0.2),
    TournamentSlot("world_cup", max_spots=2, strategy=StrictTopNAllocation(), qualified_skip_prob=0.2),
    TournamentSlot("rating", max_spots=8, strategy=RatingAllocation(guaranteed_spots=1)),
]

custom_config = (
    ScenarioBuilder(custom_slots)
    .with_player_configs({123456: PlayerConfig(mode=ParticipationMode.RATING_ONLY)})
    .build()
)
```

Append `(name, custom_config)` to the `scenarios` list in `main.py` to include it in the Monte Carlo run.

## License

MIT
