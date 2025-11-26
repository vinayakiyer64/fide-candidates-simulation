"""
Utilities for assembling QualificationConfig instances.
"""

from copy import deepcopy
from typing import Dict, Iterable, Optional

from src.config import QualificationConfig, TournamentSlot, PlayerConfig


class ScenarioBuilder:
    """
    Immutable helper for constructing QualificationConfig objects.
    """

    def __init__(
        self,
        slots: Iterable[TournamentSlot],
        target_candidates: int = 8,
        player_configs: Optional[Dict[int, PlayerConfig]] = None,
    ):
        self._slots = deepcopy(list(slots))
        self._target_candidates = target_candidates
        self._player_configs = player_configs or {}

    def clone(self) -> "ScenarioBuilder":
        return ScenarioBuilder(
            slots=deepcopy(self._slots),
            target_candidates=self._target_candidates,
            player_configs=self._player_configs.copy(),
        )

    def with_slots(self, slots: Iterable[TournamentSlot]) -> "ScenarioBuilder":
        builder = self.clone()
        builder._slots = deepcopy(list(slots))
        return builder

    def with_target_candidates(self, count: int) -> "ScenarioBuilder":
        builder = self.clone()
        builder._target_candidates = count
        return builder

    def with_player_configs(self, configs: Dict[int, PlayerConfig]) -> "ScenarioBuilder":
        builder = self.clone()
        builder._player_configs.update(configs)
        return builder

    def with_skip_probability(self, probability: float) -> "ScenarioBuilder":
        builder = self.clone()
        for slot in builder._slots:
            slot.qualified_skip_prob = probability
        return builder

    def build(self) -> QualificationConfig:
        return QualificationConfig(
            target_candidates=self._target_candidates,
            slots=deepcopy(self._slots),
            player_configs=self._player_configs.copy(),
        )

