from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class RevisionRef:
    product_id: UUID
    revision_id: UUID
    generation: int


@dataclass(frozen=True)
class ArtifactRef:
    key: str
    sha256: str
    version: str


@dataclass(frozen=True)
class ModelRef:
    name: str
    revision: str
    dimension: int


@dataclass(frozen=True)
class Evidence:
    chunk_id: UUID
    document_id: UUID
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class RetrievalHit:
    evidence: Evidence
    score: float


class EmbeddingModelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    dimension: int = Field(strict=True, ge=1)
