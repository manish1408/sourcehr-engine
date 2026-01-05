from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime

from app.schemas.PyObjectId import PyObjectId
from app.schemas.Industries import IndustrySchema
from app.schemas.Topics import TopicSchema
    

class LocationItem(BaseModel):
    name: str
    slug: str
class LocationSchema(BaseModel):
    region_name: str
    region_slug: str
    locations: List[LocationItem]

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
        use_enum_values = True
        
class SecondaryIndustrySchema(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    
class IndustrySchema(BaseModel):
    primary_industry: Optional[str] = None
    primary_industry_slug: Optional[str] = None
    secondary_industry: List[SecondaryIndustrySchema] = None
    
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        arbitrary_types_allowed = True

class TopicItem(BaseModel):
    title: str
    slug: str

class TopicSchema(BaseModel):
    category: str
    category_slug: str
    topics: List[TopicItem]

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        allow_population_by_field_name = True
        use_enum_values = True


        
        

class DisplayOptions(BaseModel):
    view: Literal["table", "chart", "matrix"]="table"
    notificationsEnabled: bool=True
    exportFormat: List[Literal["pdf", "csv"]]=['pdf']

class WidgetOptions(BaseModel):
    showNews: bool=True
    showLegalCalendar: bool=True
    showCourtOpinions: bool=False
    showJurisdictionSelector: bool=True
    showRecentAlerts: bool=True

class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    locations: List[LocationSchema]
    industries: List[IndustrySchema]
    topics: List[TopicSchema]
    region: Optional[List[str]] = None
    displayOptions: DisplayOptions = Field(default_factory=DisplayOptions)
    widgets: WidgetOptions = Field(default_factory=WidgetOptions)
    savedSearches: Optional[List[str]] = []
    alertsEnabled: Optional[bool]=True
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
    
class DashboardUpdate(BaseModel):
    name: Optional[str]=None
    description: Optional[str]=None
    locations: List[LocationSchema]=None
    industries: List[IndustrySchema]=None
    topics: List[TopicSchema]=None
    region: Optional[List[str]]=None
    displayOptions: Optional[DisplayOptions]=None
    widgets: Optional[WidgetOptions]=None
    savedSearches: Optional[List[str]]=None
    alertsEnabled: Optional[bool]=None

class DashboardSchema(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    userId: str
    name: str
    description: Optional[str]
    locations: List[LocationSchema]
    industries: List[IndustrySchema]
    topics: List[TopicSchema]
    region: Optional[List[str]] = None
    displayOptions: DisplayOptions
    widgets: WidgetOptions
    savedSearches: List[str]
    alertsEnabled: bool
    createdAt: datetime 
    updatedAt: datetime
    lastSessionId:Optional[str]=None
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        


class LinkModel(BaseModel):
    title: Optional[str] = Field(
        default=None,
        description="A human-readable title for the source link. Generate one if not explicitly available."
    )
    url: str = Field(
        description="The URL to the original source of the law change, such as a government or legal website provided in the text."
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
        description="The name or title of the law or regulation, if mentioned"
    )
    applicable: str = Field(
        description="A concise but detailed paragraph or bullet-point list explaining how the law applies."
    )
    links: List[LinkModel] = Field(
        description="A list of source links related to the law change, each with a title and URL provided in the text"
    )





class LawChangeGroupByLocation(BaseModel):
    jurisdiction: str = Field(
        description="The jurisdiction (location) where these law changes apply in Readable format"
    )
    lawChanges: List[LawChangeMetadata] = Field(
        description="A list of law change entries for this jurisdiction."
    )

class LawChangeListByLocation(BaseModel):
    lawChangesByLocation: List[LawChangeGroupByLocation] = Field(
        description="A list of law change groups, each grouped by jurisdiction (location)."
    )

class NewsSchema(BaseModel):
    title: str = Field(..., description="Title of the news")
    description: str = Field(..., description="Description of the news")
    detailedDescription: Optional[str] = Field(..., description="A detailed, rephrased, and expanded version of the news content generated from the raw news data. This should be comprehensive, containing approximately 50-100 sentences with extensive in-depth information, background context, implications, legal analysis, industry impact, and future considerations.")
    sourceUrl: str = Field(..., description="The URL to the original source of the news provided in the text.")
    imageUrl: Optional[str] = None
class NewsList(BaseModel):
    news:List[NewsSchema]
    


class CourtDecisionSchema(BaseModel):
    title: str = Field(..., description="Title of the court decision example: 'Bank of America v. DOL (2023)'")
    description: str = Field(..., description="Summary of the decision and relevance to employers example: 'The court ruled that Bank of America must pay $100 million to the Department of Labor (DOL) for violating the Fair Labor Standards Act (FLSA).'")
    sourceUrl: str = Field(..., description="The URL to the original source of the court decision provided in the text. example: 'https://www.dol.gov/news/press-releases/2023/08/bank-america-v-dol'")

class CourtDecisionList(BaseModel):
    courtDecisions: List[CourtDecisionSchema]

class LegalCalendarEvent(BaseModel):
    title: str = Field(..., description="Title of the legal event ")
    description: str = Field(..., description="Description of the legal event that highlights the key changes or impacts")
    effective_date: str = Field(..., description="Effective date in ISO format (YYYY-MM-DD)")
    sourceUrl: str = Field(..., description="The URL to the original source of the legal event provided in the text. example: 'https://www.dol.gov/news/press-releases/2023/08/bank-america-v-dol'")
class LegalCalendar(BaseModel):
    events: List[LegalCalendarEvent] = Field(..., description="List of structured legal calendar events")
