from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId
class LocationItem(BaseModel):
    name: str
    slug: str

class LocationSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    region_name: str
    region_slug: str
    locations: List[LocationItem]

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
        use_enum_values = True
