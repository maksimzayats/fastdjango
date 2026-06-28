from pydantic import BaseModel, ConfigDict


class BaseFastAPISchema(BaseModel):
    """Define BaseFastAPISchema."""

    model_config = ConfigDict(from_attributes=True)
