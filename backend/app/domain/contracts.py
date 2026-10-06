from dataclasses import dataclass
from uuid import UUID


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
