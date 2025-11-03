from typing import List, Optional,Dict
from bson import ObjectId
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime

from app.schemas.PyObjectId import PyObjectId


class LoginStepSchema(BaseModel):
    step: str
    selectorType: str


class CrawlableURL(BaseModel):
    url: str
    crawlStatus: str="PENDING"
    updatedOn: datetime
    ingestionStatus:str="PENDING"
    ingestedOn: Optional[datetime]=None
    vectorDocIds:List[Dict]=[]




class WebsiteCrawlSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    nameOfWebsite: str
    urlOfWebsite: str
    categoryOfWebsite: str
    sourceType: str
    maxDepth:int
    maxUrls:int
    crawlStatus: str = "PENDING"
    lastCrawled: Optional[datetime] =None
    listOfCrawlableUrls: List[CrawlableURL] = []
    username: Optional[str]=None
    password: Optional[str]=None
    loginButtonSelector: Optional[str] = None
    loginSteps: Optional[List[LoginStepSchema]] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        
        
class WebsiteCrawlCreate(BaseModel):
    nameOfWebsite: Optional[str]=None
    urlOfWebsite: Optional[str]=None
    categoryOfWebsite: Optional[str]=None
    sourceType: Optional[str]=None
    maxDepth: Optional[int]=None
    maxUrls: Optional[int]=None
    username: Optional[str]=None
    password: Optional[str]=None
    loginButtonSelector: Optional[str] = None
    loginSteps: Optional[List[LoginStepSchema]] = None
