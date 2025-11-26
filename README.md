# FIDE Candidate Simulation

This project simulates the qualification cycle for the FIDE Candidates Tournament to evaluate the fairness of different qualification systems.

## Project Structure

```
fide-candidate-simulation/
├── data/
│   └── players.json           # Top 100 players data (real + extrapolated)
├── src/
│   ├── entities.py            # Domain models (Player class)
│   ├── game_logic.py          # Chess game simulation (Elo, draw rates)
│   ├── utils.py               # Helper functions (weighted sampling)
│   ├── simulation.py          # Main Monte Carlo simulation engine
│   └── tournaments/           # Tournament format implementations
│       ├── world_cup.py       # Knockout format
│       ├── grand_swiss.py     # Swiss format
│       └── circuit.py         # FIDE Circuit (series of events)
├── scripts/
│   └── parse_chesscom.py      # Scraper for player data
└── main.py                    # CLI entry point
```

## Usage

1.  **Install Dependencies** (if re-running scraper):
    ```bash
    pip install requests beautifulsoup4
    ```

2.  **Run the Simulation**:
    ```bash
    python3 main.py
    ```

## Scenarios

The simulation compares the **Current System** against three alternatives:
1.  **Pure Meritocracy**: Top 8 by Rating (Theoretical maximum fairness).
2.  **More Rating Spots**: Re-allocating 2 spots from the World Cup to the Rating list.
3.  **More Circuit Spots**: Re-allocating 2 spots from the World Cup to the FIDE Circuit.

## Key Findings

*   **World Cup Volatility**: The knockout format is highly volatile. Removing spots from it significantly increases the probability that the strongest players qualify.
*   **Rating is King**: Allocating more spots to the Rating list is the most effective way to ensure the "best" players qualify.

