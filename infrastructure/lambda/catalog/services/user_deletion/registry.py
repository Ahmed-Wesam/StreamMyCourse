"""Registry of ordered user-deletion steps (DSQL-2 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List


@dataclass(frozen=True)
class DeletionStep:
    name: str
    order: int
    run: Callable[[str], None]


class UserDeletionRegistry:
    def __init__(self) -> None:
        self._steps: List[DeletionStep] = []

    def register(self, *, name: str, order: int, run: Callable[[str], None]) -> None:
        self._steps.append(DeletionStep(name=name, order=order, run=run))
        self._steps.sort(key=lambda s: s.order)

    def ordered_steps(self) -> List[DeletionStep]:
        return list(self._steps)
