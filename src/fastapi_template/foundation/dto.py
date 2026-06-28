from pydantic import BaseModel, ConfigDict


class BaseDTO(BaseModel):
    """Define BaseDTO."""

    model_config = ConfigDict(from_attributes=True)
