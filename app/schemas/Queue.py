from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field
from bson import ObjectId

from app.schemas.PyObjectId import PyObjectId


class QueueType(str, Enum):
    NEWS = "NEWS"
    CALENDAR = "CALENDAR"
    COMPLIANCE = "COMPLIANCE"
    LAW_CHANGE = "LAW_CHANGE"

class QueueStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class QueueEntry(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=ObjectId, alias="_id")
    dashboardId: str
    type: QueueType
    status: QueueStatus = QueueStatus.PENDING
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class QueueCreateRequest(BaseModel):
    dashboardId: str
    type: QueueType


class QueueResponse(BaseModel):
    id: str
    status: QueueStatus
    type: QueueType
    dashboardId: str
    createdAt: datetime
    updatedAt: datetime
    error: Optional[str] = None
