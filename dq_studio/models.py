from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    category: str
    scope: str
    severity: str
    column: str
    message: str
    count: int
    examples: tuple[str, ...]
    sql: str


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    logical_type: str
    nullable: bool
    domain: tuple[str, ...] = ()
    format_name: str | None = None
