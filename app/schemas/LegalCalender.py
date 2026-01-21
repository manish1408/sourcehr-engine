from datetime import datetime
from pydantic import BaseModel,Field
from typing import List, Literal, Optional

class LegalCalendarEvent(BaseModel):
    title: str = Field(..., description="Title of the legal event")
    description: str = Field(..., description="Description of the legal event")
    effective_date: Optional[str] = Field(None, description="Effective date in ISO format (YYYY-MM-DD). Set to null if not explicitly stated in source.")
    sourceUrl: str = Field(..., description="The URL to the original source of the legal event provided in the text. example: 'https://www.dol.gov/news/press-releases/2023/08/bank-america-v-dol'")
    descriptionEvidence: Optional[str] = Field(None, description="Exact sentence(s) from source text supporting the description. Required if description is provided.")
    dateEvidence: Optional[str] = Field(None, description="Exact sentence(s) from source text supporting the effective date. Required if effective_date is provided.")

class LegalCalendar(BaseModel):
    events: List[LegalCalendarEvent] = Field(..., description="List of structured legal calendar events")



    
class LegalCalenderSchema(BaseModel):
    dashboardId: str
    data: List[LegalCalendar]
    status: Literal['REFRESHED', 'FETCHED']
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
