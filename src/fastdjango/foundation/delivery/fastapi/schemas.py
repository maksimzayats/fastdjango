from pydantic import BaseModel, ConfigDict


class BaseFastAPISchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
