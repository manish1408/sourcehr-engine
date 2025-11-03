from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class MetaDataSchema(BaseModel):
        chunkText: str = Field(..., description="The raw text excerpt describing the legal or regulatory event without pronouns or determiners.")
        region: str = Field(..., description="Geopolitical subregion, chosen from the predefined region enum.")
        region_slug: Optional[str] = Field(description="Slugified version of the region")
        location: Optional[str] = Field(None, description="The specific location")
        location_slug: Optional[str] = Field(None, description="Slugified version of the location")
        primary_industry: str = Field(..., description="Top-level industry affected, e.g., 'Finance & Insurance'.")
        primary_industry_slug: Optional[str] = Field(description="Slugified version of the primary industry")
        secondary_industry: str = Field(..., description="More specific sector within the primary industry, e.g., 'Fintech'.")   
        secondary_industry_slug: Optional[str] = Field(description="Slugified version of the secondary industry")
        topic: str = Field(..., description="Labor & employment-related topic of the event, e.g., 'Parental Leave'.")
        topic_slug: Optional[str] = Field(description="Slugified version of the topic")
        discussedTimestamp: str = Field(..., description="ISO 8601 timestamp when the event occurred or will occur, e.g., '2025-08-01T00:00:00Z'.")
        newsPublishTimestamp: str = Field(..., description="ISO 8601 timestamp when the article was published.")

class MetaDataSchemaList(BaseModel):
    metaData: List[MetaDataSchema]


