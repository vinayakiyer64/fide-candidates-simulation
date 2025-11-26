# FIDE Candidates Simulation

Monte Carlo simulation of the FIDE World Championship qualification cycle to evaluate the fairness of different qualification systems.

## Overview

The simulation models four qualification paths to the Candidates Tournament:
- **Grand Swiss** (2 spots) - Swiss-system tournament
- **World Cup** (3 spots) - Knockout tournament  
- **FIDE Circuit** (2-3 spots) - Series of elite events with points
- **Rating** (1+ spots) - Highest-rated non-qualified players

Each qualification path has specific allocation rules (e.g., strict top-N, spillover for duplicates). The simulation runs 500+ seasons to measure how often the "true" top 8 players qualify under different systems.

## Project Structure

```
fide-candidates-simulation/
├── data/
│   └── players.json              # FIDE Top 100 players
├── src/
│   ├── entities.py               # Player dataclass
│   ├── game_logic.py             # Elo expected score, game simulation, rating updates
│   ├── utils.py                  # Weighted sampling, player pool augmentation
│   ├── config.py                 # QualificationConfig, TournamentSlot
│   ├── simulation.py             # QualificationSimulator, run_monte_carlo
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

Output:
```
Loaded 100 real players. Augmenting pool...
Total player pool size after augmentation: 328
Top player: Carlsen, Magnus (2839.0)

Running Simulations (500 seasons each)...
---------------------------------------------------------------------------
Scenario                            | Avg Elo    | Top 8 Qual%  | Corr(Rank,Prob)
---------------------------------------------------------------------------
Current System                      | 2747.1      | 44.7%        | -0.455
Pure Rating (Reference)             | 2785.0      | 100.0%        | -0.267
More Rating Spots (-2 WC)           | 2761.9      | 59.8%        | -0.365
More Circuit Spots (-2 WC)          | 2759.8      | 57.9%        | -0.373
Grand Slam (No WC)                  | 2750.8      | 49.2%        | -0.409
---------------------------------------------------------------------------
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

## Allocation Rules

The simulation implements FIDE's actual qualification rules:

1. **Grand Swiss / World Cup**: Strict Top-N. If a top finisher already qualified via a higher-priority path, that spot is **lost** (not passed down).

2. **FIDE Circuit**: Base 2 spots. Gets a 3rd spot **only if** there's a duplicate (a Circuit top finisher already qualified via GS/WC).

3. **Rating**: Guaranteed 1 spot for the highest-rated non-qualified player. Fills all remaining spots to reach 8 candidates.

Priority order: Grand Swiss → World Cup → Circuit → Rating

## Key Metrics

- **Avg Elo**: Mean Elo of the 8 qualifiers (higher = stronger field)
- **Top 8 Qual%**: How often the "true" top 8 by rating actually qualify
- **Corr(Rank, Prob)**: Correlation between initial rank and qualification probability (more negative = more meritocratic)

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
