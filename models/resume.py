from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ResumeChunk(BaseModel):
    text: str
    filename: str
    candidate: str
    chunk_index: int
    section: str = "general"
    upload_date: str = ""


class Resume(BaseModel):
    id: str
    name: str
    filename: str
    upload_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    chunk_count: int = 0
    skills: list[str] = Field(default_factory=list)
    field: str = ""
    title: str = ""
    salary: str = ""
    ai_score: str = ""
