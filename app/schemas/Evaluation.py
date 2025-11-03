from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId

from pydantic import BaseModel, Field

class EvaluationScores(BaseModel):
    rag_groundedness: float = Field(..., description="Score for groundedness to retrieved context")
    hallucination: float = Field(..., description="Score for presence of hallucinated content")
    rag_retrieval_relevance: float = Field(..., description="Score for relevance of retrieved context to the query")
    correctness: float = Field(..., description="Score for factual correctness against the reference")
    conciseness: float = Field(..., description="Score for how concise the output is")


class EvaluationSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    userQuery: str
    output:str
    scores: EvaluationScores
    citations: Optional[List[str]]=None
    referenceOutput: Optional[str]=None
    datasetId:str
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
