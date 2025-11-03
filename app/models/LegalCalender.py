import os
from typing import List
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.LegalCalender import LegalCalenderSchema

class LegalCalenderModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Legal Calender"):
        self.collection = MongoDB.get_async_database(db_name)[collection_name]

    async def create(self, data: dict):
        """
        Create a new dashboard compliance document in the database.
        """
        data["createdAt"] = datetime.utcnow()
        data = LegalCalenderSchema(**data)
        result = await self.collection.insert_one(data.model_dump(by_alias=True))
        return result.inserted_id
    
    async def get_legal_calender(self, dashboard_id: str) -> List[LegalCalenderSchema]:
        """
        Retrieve law changes for a specific dashboard from the database.
        """
        cursor = self.collection.find({"dashboardId": dashboard_id})
        docs = await cursor.to_list(length=None)
        return [LegalCalenderSchema(**doc) for doc in docs]

    async def update_legal_calender(self, dashboard_id: str, data: dict):
        """
        Update legal calendar document for a dashboard.
        """
        result = await self.collection.update_one({"dashboardId": dashboard_id}, {"$set": data})
        return result.modified_count
