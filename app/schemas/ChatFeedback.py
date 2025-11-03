from typing import Literal, Optional
from pydantic import BaseModel, Field
from bson import ObjectId
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId

class ChatFeedbackSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    ChatSessionId: str
    UserId:str
    UserName:str
    ChatMessageId:str
    Question:str
    Answer:str
    Sentiment:Literal["POSITIVE", "NEGATIVE"]
    Feedback:Optional[str] = ""
    CreatedOn: datetime
    UpdatedOn:datetime=None
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }
        
class CreateChatFeedbackSchema(BaseModel):
    ChatMessageId:str
    Question:str
    Answer:str
    Sentiment:Literal["POSITIVE", "NEGATIVE"]
    Feedback:Optional[str] = ""
    ChatSessionId:str
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        
class UpdateChatFeedbackSchema(BaseModel):
    Sentiment:Literal["POSITIVE", "NEGATIVE"]
    Feedback:Optional[str] = ""
        