from datetime import datetime
from pydantic import BaseModel,Field
from typing import List, Literal, Optional

class LegalCalendarEvent(BaseModel):
    title: str = Field(..., description="Title of the legal event")
    description: str = Field(..., description="Description of the legal event")
    effective_date: str = Field(..., description="Effective date in ISO format (YYYY-MM-DD)")
    sourceUrl: str = Field(..., description="The URL to the original source of the legal event provided in the text. example: 'https://www.dol.gov/news/press-releases/2023/08/bank-america-v-dol'")

class LegalCalendar(BaseModel):
    events: List[LegalCalendarEvent] = Field(..., description="List of structured legal calendar events")



    
class LegalCalenderSchema(BaseModel):
    dashboardId: str
    data: List[LegalCalendar]
    status: Literal['REFRESHED', 'FETCHED']
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
