from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from bson import ObjectId
from app.schemas.PyObjectId import PyObjectId


class ScrapedUrlSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    dashboardId: str = Field(..., description="Dashboard ID this URL belongs to")
    source: Literal["news", "calendar", "court_decisions"] = Field(..., description="Source type: news, calendar, or court_decisions")
    url: str = Field(..., description="The URL that was scraped")
    scraped: bool = Field(default=True, description="Whether the URL has been scraped")
    vectorDbIds: Optional[List[str]] = Field(default=None, description="List of vector DB document IDs")
    error: Optional[str] = Field(default=None, description="Error message if scraping failed")
    createdAt: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updatedAt: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
