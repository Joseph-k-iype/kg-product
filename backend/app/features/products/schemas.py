import math

from pydantic import BaseModel, Field, field_validator

from app.domain.contracts import EmbeddingModelInput


def valid_config(value):
    if value is None:
        return value
    if "quality_gates" in value:
        gates = value["quality_gates"]
        if not isinstance(gates, dict):
            raise ValueError("Quality requirements must be a mapping of thresholds")
        for threshold in gates.values():
            if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
                raise ValueError("Quality thresholds must be finite numbers between 0 and 1")
    if "embedding_model" in value:
        value["embedding_model"] = EmbeddingModelInput.model_validate(value["embedding_model"]).model_dump()
    if "limit" in value:
        limit = value["limit"]
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("Choose between 1 and 50 matching results")
    return value


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    purpose: str = ""
    domain: str = "General"
    owner: str = "Demo author"
    tags: list[str] = []
    config: dict = {}

    _valid_config = field_validator("config")(valid_config)

    @field_validator("name")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Enter a product name")
        return value.strip()


class ProductUpdate(BaseModel):
    expected_generation: int
    name: str | None = Field(default=None, min_length=1, max_length=200)
    purpose: str | None = None
    domain: str | None = None
    owner: str | None = None
    tags: list[str] | None = None
    config: dict | None = None

    _valid_config = field_validator("config")(valid_config)

    @field_validator("name")
    @classmethod
    def not_blank(cls, value):
        return ProductCreate.not_blank(value) if value is not None else value
