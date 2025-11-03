from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from bson import ObjectId
from datetime import datetime
from enum import Enum
from app.schemas.PyObjectId import PyObjectId
class VectorDatabaseSchema(BaseModel):
    index: str
    namespace: Optional[str] = None
class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    IN_PROGRESS = "IN_PROGRESS"

class DocumentsSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    vectorDatabase: VectorDatabaseSchema
    status: DocumentStatus
    type: str
    name: str
    originalSource: str
    sourceType: str
    vectorDocId: List[Dict] = []
    createdOn: datetime
    deletedOn: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        
class CreateTextDocumentsSchema(BaseModel):
    knowledgeText: str
    