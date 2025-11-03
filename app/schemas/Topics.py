from pydantic import BaseModel,Field
from typing import Optional, List
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId

class TopicItem(BaseModel):
    title: str
    slug: str

class TopicSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    category: str
    category_slug: str
    topics: List[TopicItem]

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
        use_enum_values = True
