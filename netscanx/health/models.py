from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HealthCheck(BaseModel):
    name: str
    status: str  # "ok", "warning", "error", "skipped"
    message: str
    weight: int = 10  # points deducted from 100 on failure
    details: dict[str, Any] = Field(default_factory=dict)


class HealthReport(BaseModel):
    """Health score, 0-100. warning deducts half of a check's weight,
    error deducts the full weight, skipped deducts nothing. Each check
    runner (local vs. network) documents its own weight set, which is
    designed to sum to 100 across that runner's checks so a machine
    failing everything in that set bottoms out at 0."""

    target: str  # "local" or an IP/hostname
    checks: list[HealthCheck] = Field(default_factory=list)
    score: int = 100
    summary_ok: int = 0
    summary_warning: int = 0
    summary_error: int = 0
    timestamp: datetime = Field(default_factory=_now)

    def add(self, check: HealthCheck) -> None:
        self.checks.append(check)
        if check.status == "ok":
            self.summary_ok += 1
        elif check.status == "warning":
            self.summary_warning += 1
            self.score -= check.weight // 2
        elif check.status == "error":
            self.summary_error += 1
            self.score -= check.weight
        self.score = max(0, self.score)
