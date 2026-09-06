from typing import Literal

from pydantic import BaseModel, Field


class TraceEvent(BaseModel):
    sequence: int
    phase: str
    message: str
    elapsed_ms: float


class Evidence(BaseModel):
    id: str
    title: str
    url: str
    publisher: str
    excerpt: str
    retrieved_at: str
    cited_quotes: list[str] = Field(default_factory=list)
    stances: list[Literal["supported", "refuted", "uncertain"]] = Field(default_factory=list)


class ClaimResult(BaseModel):
    id: str
    text: str
    verdict: Literal["supported", "refuted", "uncertain", "conflicting"]
    reasoning: str
    evidence: list[Evidence] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)


class Investigation(BaseModel):
    claims: list[ClaimResult] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    recommended_action: str
