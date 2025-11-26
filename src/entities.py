from dataclasses import dataclass
from typing import List

@dataclass
class Player:
    id: int
    name: str
    elo: float
    initial_rank: int  # rank by Elo
    # You can add federation, age, etc. if needed

# Helper type
PlayerPool = List[Player]

