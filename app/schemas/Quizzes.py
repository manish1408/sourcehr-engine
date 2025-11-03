from datetime import datetime
from typing import List, Literal, Optional
from bson import ObjectId
from pydantic import BaseModel, Field

from app.schemas import PyObjectId


class Option(BaseModel):
    optionId: str
    text: str

class Question(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    question_text: str
    options: List[Option]
    correctAnswers: List[str] = Field(alias="correctOptions")  # MongoDB's correctOptions -> correctAnswers
    rewardPoint: int = Field(alias="reward_point")  # MongoDB's reward_point -> rewardPoint
    type: Literal["SINGLE", "MULTIPLE"]
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class QuestionCreate(BaseModel):
    question_text: str
    options: List[Option]
    correctOptions: List[str]  
    rewardPoint: int
    type: Literal["SINGLE", "MULTIPLE"]


class QuestionUpdate(BaseModel):
    question_text: Optional[str]=None
    options: Optional[List[Option]]=None
    rewardPoint: Optional[int]=None
    type: Optional[Literal["SINGLE", "MULTIPLE"]]=None




class Quiz(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId,alias="_id")
    title: str
    description: Optional[str]
    questions: List[Question]=[]
    createdOn: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updatedOn: Optional[datetime] = Field(default_factory=datetime.utcnow)
    quizDuration:int
    createdBy:str

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True



class QuizCreate(BaseModel):
    title: str
    description: Optional[str] = None
    quizDuration: int
    
class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    quizDuration: Optional[int] = None  
    


        

        
