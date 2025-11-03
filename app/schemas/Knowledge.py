from pydantic import BaseModel, Field
from typing import Optional,List
from bson import ObjectId
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId


class VectorDatabaseSchema(BaseModel):
    index: str
    namespace: Optional[str] = None
    
class KnowledgeSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    name: str
    description: Optional[str] = ''
    userId:str
    vectorDatabase: VectorDatabaseSchema
    isDeleted: bool = False
    createdOn: datetime
    deletedOn: Optional[datetime] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        
        
class CreateKnowledgeSchema(BaseModel):
    name: str
    description: Optional[str] = ''
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        
class ChatWithKnowledgeSchema(BaseModel):
    question: str