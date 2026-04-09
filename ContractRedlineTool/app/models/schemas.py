from pydantic import BaseModel, Field
from enum import Enum


class RiskLevel(str, Enum):
    major = "major"
    moderate = "moderate"
    minor = "minor"


class Recommendation(BaseModel):
    """A single recommended change to apply to the contract."""

    original_text: str = Field(
        ...,
        description="The exact text in the contract to find and replace",
        min_length=1,
    )
    replacement_text: str = Field(
        default="",
        description="The new text to insert (tracked as insertion). Leave empty string to only delete.",
    )
    rationale: str = Field(
        ...,
        description="Explanation for the change, added as a Word comment",
        min_length=1,
    )
    risk_level: RiskLevel = Field(
        default=RiskLevel.moderate,
        description="Risk severity: major, moderate, or minor",
    )
    section: str = Field(
        default="",
        description="Optional: the contract section where this change applies",
    )


class RedlineRequest(BaseModel):
    """Request to redline a SharePoint Word document with tracked changes."""

    document_url: str = Field(
        ..., description="Full URL to the Word document in SharePoint"
    )
    recommendations: list[Recommendation] = Field(
        ..., description="List of changes to apply", min_length=1
    )
    author: str = Field(
        default="Contract Review Agent",
        description="Author name for tracked changes and comments",
    )
    output_filename: str = Field(
        default="",
        description="Optional output filename. If empty, appends '_redlined' to original name.",
    )
    output_folder_url: str = Field(
        default="",
        description="Optional SharePoint folder URL for the redlined document. If empty, uploads to the same folder as the source document.",
    )


class ChangeResult(BaseModel):
    """Result of applying a single change."""

    original_text: str
    replacement_text: str
    applied: bool
    comment_added: bool
    error: str = ""


class RedlineResponse(BaseModel):
    """Response after redlining a document."""

    status: str = Field(description="'success' or 'partial' or 'error'")
    output_url: str = Field(
        default="", description="URL to the redlined document in SharePoint"
    )
    changes_applied: int = Field(
        description="Number of tracked changes successfully applied"
    )
    changes_failed: int = Field(
        default=0, description="Number of changes that could not be applied"
    )
    comments_added: int = Field(description="Number of rationale comments added")
    results: list[ChangeResult] = Field(
        default_factory=list, description="Per-change results"
    )
    summary: str = Field(
        default="", description="Human-readable summary of the redline operation"
    )
    error: str = Field(
        default="", description="Error message if status is 'error'"
    )


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    service: str = "Contract Redline Tool"
