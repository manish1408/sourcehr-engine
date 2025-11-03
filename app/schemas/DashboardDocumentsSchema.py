from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.PyObjectId import PyObjectId
from bson import ObjectId

class RelatedDocument(BaseModel):
    title: str
    link: str


class LawDetails(BaseModel):
    title: str
    jurisdiction: str
    industry: str
    topic: str
    relatedDocuments: List[RelatedDocument]


class LawDocumentItem(BaseModel):
    summary: str
    lawDetails: LawDetails


class FinalDocSchema(BaseModel):
    id: Optional[str] = Field(..., alias="_id")
    jurisdiction: str
    topic: str
    lawChangesCount: int
    lawDocument: List[LawDocumentItem]
    class Config:
        populate_by_name = True
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Response(BaseModel):
    id: str = Field(..., alias="_id")
    jurisdiction: str
    topic: str
    lawChangesCount: int
    lawDocument: List[LawDocumentItem]
    class Config:
        allow_population_by_field_name = True

class GetDocResponse(BaseModel):
    data:List[Response]
    success:bool