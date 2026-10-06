from pydantic import BaseModel, Field, field_validator

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    purpose: str = ''
    domain: str = 'General'
    owner: str = 'Demo author'
    tags: list[str] = []
    config: dict = {}
    @field_validator('name')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('Enter a product name')
        return value.strip()

class ProductUpdate(BaseModel):
    expected_generation: int
    name: str | None = Field(default=None, min_length=1, max_length=200)
    purpose: str | None = None
    domain: str | None = None
    owner: str | None = None
    tags: list[str] | None = None
    config: dict | None = None
