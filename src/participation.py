"""
Participation logic for the qualification cycle.

This module handles:
- Determining which players participate in each tournament
- Determining which players are eligible for qualification
- Handling withdrawal of already-qualified players

Follows Single Responsibility Principle: Only handles participation/eligibility logic.
"""

from typing import Set, List, Optional
import random

from src.entities import Player, PlayerPool
from src.config import QualificationConfig, PlayerConfig, ParticipationMode, TournamentSlot


class ParticipationManager:
    """
    Manages player participation and eligibility throughout a season.
    
    Responsibilities:
    - Track which players have qualified
    - Determine tournament participants (who plays)
    - Determine allocation eligibility (who can receive spots)
    
    Thread Safety: Not thread-safe. Create one instance per season simulation.
    """
    
    def __init__(self, players: PlayerPool, config: QualificationConfig, seed: Optional[int] = None):
        """
        Initialize the participation manager.
        
        Args:
            players: Full player pool for the season
            config: Qualification configuration with player configs
            seed: Random seed for reproducible withdrawal decisions
        """
        self.players = players
        self.config = config
        self.qualified_ids: Set[int] = set()
        self._player_map = {p.id: p for p in players}
        self._rng = random.Random(seed)
    
    def _get_player_config(self, player_id: int) -> PlayerConfig:
        """
        Get configuration for a player, defaulting to FULL mode.
        
        Args:
            player_id: The player's ID
            
        Returns:
            PlayerConfig for this player
        """
        return self.config.player_configs.get(player_id, PlayerConfig())
    
    def can_participate(self, player: Player, slot: TournamentSlot) -> bool:
        """
        Determine if a player can participate in a tournament.
        
        Rules (in order):
        1. Rating slot is not a tournament - no participation
        2. EXCLUDED players never participate
        3. If the tournament is explicitly blocked for this player, skip it
        4. RATING_ONLY players don't participate in tournaments
        5. Already-qualified players may skip (based on qualified_skip_prob)
        6. FULL and PLAYS_NOT_ELIGIBLE players participate
        
        Args:
            player: The player to check
            slot: The tournament slot
            
        Returns:
            True if player participates in this tournament
        """
        cfg = self._get_player_config(player.id)
        tournament_type = slot.tournament_type
        
        # Rating is not a "tournament" - no participation concept
        if tournament_type == "rating":
            return False
        
        # EXCLUDED players never participate
        if cfg.mode == ParticipationMode.EXCLUDED:
            return False
        
        # Blocked tournaments override
        if cfg.blocked_tournaments and tournament_type in cfg.blocked_tournaments:
            return False

        # RATING_ONLY players skip all tournaments
        if cfg.mode == ParticipationMode.RATING_ONLY:
            return False
        
        # Already qualified? May skip with probability
        if player.id in self.qualified_ids:
            if self._rng.random() < slot.qualified_skip_prob:
                return False
        
        return True
    
    def is_eligible(self, player: Player) -> bool:
        """
        Determine if a player is eligible for qualification.
        
        Rules:
        1. Already-qualified players are not eligible (can't qualify twice)
        2. EXCLUDED players are not eligible
        3. PLAYS_NOT_ELIGIBLE players are not eligible
        4. FULL and RATING_ONLY players are eligible
        
        Args:
            player: The player to check
            
        Returns:
            True if player can receive a qualification spot
        """
        # Can't qualify twice
        if player.id in self.qualified_ids:
            return False
        
        cfg = self._get_player_config(player.id)
        
        # These modes are not eligible for qualification
        if cfg.mode in (ParticipationMode.EXCLUDED, ParticipationMode.PLAYS_NOT_ELIGIBLE):
            return False
        
        return True
    
    def get_participants(self, slot: TournamentSlot) -> PlayerPool:
        """
        Get list of players who will participate in this tournament.
        
        Args:
            slot: The tournament slot
            
        Returns:
            List of players participating in this tournament
        """
        return [p for p in self.players if self.can_participate(p, slot)]
    
    def get_eligible_standings(self, standings: List[Player]) -> List[Player]:
        """
        Filter standings to only eligible players.
        
        Args:
            standings: Full standings from tournament
            
        Returns:
            Standings filtered to only qualification-eligible players
        """
        return [p for p in standings if self.is_eligible(p)]
    
    def mark_qualified(self, player_ids: Set[int]) -> None:
        """
        Mark players as qualified.
        
        Args:
            player_ids: Set of player IDs who qualified
        """
        self.qualified_ids.update(player_ids)
    
    def get_qualified_ids(self) -> Set[int]:
        """
        Get the set of currently qualified player IDs.
        
        Returns:
            Set of qualified player IDs
        """
        return self.qualified_ids.copy()

