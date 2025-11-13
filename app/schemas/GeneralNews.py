from datetime import date
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from app.schemas.PyObjectId import PyObjectId


class GeneralNewsItem(BaseModel):
    title: str
    description: str


class GeneralNewsSummary(BaseModel):
    summaryDate: str
    articles: List[GeneralNewsItem]


class GeneralNewsDocument(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    summaryDate: str
    articles: List[GeneralNewsItem]

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
