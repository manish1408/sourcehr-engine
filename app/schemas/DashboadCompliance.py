from datetime import datetime
from pydantic import BaseModel,Field
from typing import List, Literal, Optional
from app.schemas.Dashboard import LawChangeGroupByLocation

class LinkModel(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description="A human-readable title for the source link. Generate one if not explicitly available."
    )
    url: str = Field(
        description="The URL to the original source of the law change, such as a government or legal website."
    )


class LawChangeMetadata(BaseModel):
    topic: str = Field(
        description="The topic or subject area related to the law change, written in a human-readable format."
    )
    industry: str = Field(
        description="The specific industry affected by the law change, written in human-readable form"
    )
    jurisdiction: str = Field(
        description="The jurisdiction where the law change applies"
    )
    law: str = Field(
        description="The name or title of the law or regulation mentioned."
    )
    applicable: str = Field(
        description="A  detailed paragraph or bullet-point list explaining how the law applies."
    )
    links: List[LinkModel] = Field(
        description="A list of source links related to the law change, each with a title and URL."
    )

    
class DashboardCompliance(BaseModel):
    dashboardId: str
    data: List[LawChangeGroupByLocation]
    status: Literal['REFRESHED', 'FETCHED']
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
