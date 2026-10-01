from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class Evidence:
    source_id: str
    title: str
    text: str
    provenance: str


@dataclass(frozen=True)
class RouteDecision:
    route: Literal["memory", "faq", "search", "status", "finale"]
    engine: str
    reason: str


@dataclass(frozen=True)
class TraceStep:
    component: str
    mode: str
    detail: str


@dataclass
class Answer:
    text: str
    route: str
    route_engine: str
    evidence: list[Evidence] = field(default_factory=list)
    trace: list[TraceStep] = field(default_factory=list)
    cache_hit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrackedPerson:
    track_id: int
    box: tuple[int, int, int, int]
    aim: tuple[int, int]
    confidence: float
    seen_at: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

