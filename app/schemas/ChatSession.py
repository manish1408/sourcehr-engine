from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId

class ChatMessageSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    message: str
    messageType: Literal["user", "assistant"]
    citations: Optional[List[Union[str, dict]]] = Field(default_factory=list)
    createdOn: datetime = Field(default_factory=datetime.utcnow)
    Sentiment: Optional[Literal["POSITIVE", "NEGATIVE", ""]] = Field(default="")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        arbitrary_types_allowed = True

class ChatSessionSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    userId: str
    dashboardId:str
    createdOn: datetime = Field(default_factory=datetime.utcnow)
    messages: List[ChatMessageSchema] = []
    name:str
    sessionTitle: Optional[str] = "New Chat"

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        arbitrary_types_allowed = True




class ChatSessionTitle(BaseModel):
    title: str = Field(..., description="short title 2 - 4 words of the chat session")

class RegenerateStreamRequestSchema(BaseModel):
    ai_message_id: str
    
    
