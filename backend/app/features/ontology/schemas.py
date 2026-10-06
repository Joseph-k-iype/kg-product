from typing import Literal

from pydantic import BaseModel, Field


class OntologyEdit(BaseModel):
    kind: Literal["class", "object", "datatype", "shape", "namespace", "delete"]
    iri: str
    label: str = ""
    description: str = ""
    parent: str | None = None
    domain: str | None = None
    range: str | None = None
    target: str = ""
    path: str = ""
    original_path: str | None = None
    min_count: int = Field(0, ge=0)
    max_count: int | None = Field(None, ge=0)
    datatype: str = ""
    prefix: str = ""
    expected_generation: int | None = None
    impact_token: str | None = None


class ImportInput(BaseModel):
    turtle: str
    mode: Literal["merge", "replace"] = "merge"
    impact_token: str | None = None
    expected_generation: int | None = None


class MappingInput(BaseModel):
    classes: list[dict] = []
    properties: list[dict] = []
    expected_generation: int | None = None


class SampleInput(BaseModel):
    turtle: str
