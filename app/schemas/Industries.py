from pydantic import BaseModel,Field
from typing import Optional, List
from bson import ObjectId

from app.schemas.PyObjectId import PyObjectId


class SecondaryIndustrySchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    
class IndustrySchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    primary_industry: Optional[str] = None
    primary_industry_slug: Optional[str] = None
    secondary_industry: List[SecondaryIndustrySchema] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

