from datetime import datetime
from typing import List, Literal, Optional
from bson import ObjectId
from pydantic import BaseModel, Field
from app.schemas import PyObjectId


class AnswerSubmission(BaseModel):
    questionId: str
    selectedOptions: List[str]



class QuizAttempt(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    userId: str
    quizId: str
    answers: List[AnswerSubmission] = []
    score: Optional[int] = None
    total: Optional[int] = None
    percentage: Optional[float] = None
    createdOn: Optional[datetime] = Field(default_factory=datetime.utcnow)
    status:Literal["PENDING", "SUBMITTED"]="PENDING"


    class Config:
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        populate_by_name = True