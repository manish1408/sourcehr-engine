from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.schemas.PyObjectId import PyObjectId

class News(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    title:str
    description:str
    sourceUrl:str
    imageUrl: Optional[str] = None 
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}



    


class CreateNewsSchema(BaseModel):
    dashboardId:str
    news:List[News]
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}



    
