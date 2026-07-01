from pydantic import BaseModel, ConfigDict


class BaseFastAPISchema(BaseModel):
    """Base Pydantic model for FastAPI request and response schemas."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)
