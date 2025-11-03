from typing import List
from datetime import datetime
import os
from app.helpers.Database import MongoDB
from app.schemas.CourtDecisions import CreateCourtDecisionsSchema


class CourtDecisionsModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Court Decisions"):
        self.collection = MongoDB.get_async_database(db_name)[collection_name]

    async def create(self, data: dict):
        data["created_at"] = datetime.utcnow()
        doc = CreateCourtDecisionsSchema(**data)
        result = await self.collection.insert_one(doc.model_dump(by_alias=True))
        return result.inserted_id

    async def get_court_decisions(self, dashboard_id: str) -> List[CreateCourtDecisionsSchema]:
        cursor = self.collection.find({"dashboardId": dashboard_id})
        docs = await cursor.to_list(length=None)
        return [CreateCourtDecisionsSchema(**doc) for doc in docs]

    async def update_court_decisions(self, dashboard_id: str, data: dict):
        result = await self.collection.update_one({"dashboardId": dashboard_id}, {"$set": data})
        return result.modified_count
