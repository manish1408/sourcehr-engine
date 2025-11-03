from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict
from bson import ObjectId
from datetime import datetime
from enum import Enum
from app.schemas.PyObjectId import PyObjectId

class UrlStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"

class SerpUrlSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    url: str
    rawContent: str
    status: UrlStatus = UrlStatus.PENDING
    createdOn: datetime = Field(default_factory=datetime.utcnow)
    vectorDocIds: List[Dict] = []

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
