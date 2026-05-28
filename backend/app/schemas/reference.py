import uuid

from pydantic import BaseModel


class SfiaLevelResponse(BaseModel):
    id: uuid.UUID
    level: int
    label: str
    description: str

    model_config = {"from_attributes": True}
