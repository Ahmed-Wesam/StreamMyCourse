"""Registry of ordered course-deletion steps by scope (DSQL-3 skeleton)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Literal

DeletionScope = Literal["lesson", "module", "course"]
_VALID_SCOPES = frozenset({"lesson", "module", "course"})


@dataclass(frozen=True)
class DeletionStep:
    name: str
    order: int
    scope: DeletionScope
    run: Callable[[str], None]


class CourseDeletionRegistry:
    def __init__(self) -> None:
        self._steps: List[DeletionStep] = []

    def register(
        self,
        *,
        name: str,
        order: int,
        scope: DeletionScope,
        run: Callable[[str], None],
    ) -> None:
        if scope not in _VALID_SCOPES:
            raise ValueError(f"invalid scope: {scope!r}; expected one of lesson, module, course")
        self._steps.append(DeletionStep(name=name, order=order, scope=scope, run=run))
        self._steps.sort(key=lambda s: s.order)

    def ordered_steps(self, scope: DeletionScope) -> List[DeletionStep]:
        return [s for s in self._steps if s.scope == scope]
