from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    candidate: str
    filename: str
    section: str
    chunk_index: int
    text: str
    score: float


class AnalysisResponse(BaseModel):
    answer: str
    skills_found: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    match_score: int | None = None
    summary: str = ""
    sources: list[SourceChunk] = Field(default_factory=list)
    mode: str = "local"


class RankedCandidate(BaseModel):
    candidate: str
    filename: str
    field: str = ""
    title: str = ""
    match_score: int
    skills_found: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    summary: str = ""
