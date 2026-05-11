"""Internal data models used inside the Foundry agent's Code Interpreter sandbox.

Kept intentionally small and dependency-light so the same module can be
uploaded as an agent file and imported at run time.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class _CamelModel(BaseModel):
    """Base model that emits camelCase JSON while accepting snake_case fields."""

    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)


class RiskLevel(str, Enum):
    major = "major"
    moderate = "moderate"
    minor = "minor"


RISK_EMOJI = {
    RiskLevel.major: "🔴",
    RiskLevel.moderate: "🟡",
    RiskLevel.minor: "🟢",
}


class Recommendation(_CamelModel):
    """A single recommended change to apply to the contract.

    The free-form payload from Copilot Studio / Fabric is normalized by the
    agent into a list of these before any document work happens.
    """

    original_text: str = Field(..., min_length=1)
    replacement_text: str = ""
    rationale: str = Field(..., min_length=1)
    risk_level: RiskLevel = RiskLevel.moderate
    section: str = ""


class CoherenceVerdict(_CamelModel):
    """Result of the LLM coherence check for a single recommendation."""

    accepted: bool = True
    adjusted: bool = False
    adjusted_replacement_text: Optional[str] = None
    note: str = ""


class ChangeResult(_CamelModel):
    """Per-recommendation outcome surfaced back to Copilot Studio."""

    original_text: str
    replacement_text: str
    final_replacement_text: str = ""
    applied: bool = False
    adjusted: bool = False
    comment_added: bool = False
    risk_level: RiskLevel = RiskLevel.moderate
    error: str = ""


class RedlineResult(_CamelModel):
    """Overall redline outcome."""

    status: str
    output_filename: str = ""
    output_url: str = ""
    changes_applied: int = 0
    changes_adjusted: int = 0
    changes_failed: int = 0
    comments_added: int = 0
    results: list[ChangeResult] = Field(default_factory=list)
    summary: str = ""
    error: str = ""
