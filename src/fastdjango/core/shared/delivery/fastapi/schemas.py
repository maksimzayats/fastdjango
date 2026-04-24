from pydantic import BaseModel, ConfigDict


class FastAPISchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
