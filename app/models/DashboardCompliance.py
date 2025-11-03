import os
from typing import List
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.DashboadCompliance import DashboardCompliance

class DashboardComplianceModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Dashboard Compliance"):
        self.collection = MongoDB.get_async_database(db_name)[collection_name]

    async def create(self, data: dict):
        """
        Create a new dashboard compliance document in the database.
        """
        data["createdAt"] = datetime.utcnow()
        data = DashboardCompliance(**data)
        result = await self.collection.insert_one(data.model_dump(by_alias=True))
        return result.inserted_id
    
    async def get_law_changes(self, dashboard_id: str) -> List[DashboardCompliance]:
        """
        Retrieve law changes for a specific dashboard from the database.
        """
        cursor = self.collection.find({"dashboardId": dashboard_id})
        docs = await cursor.to_list(length=None)
        return [DashboardCompliance(**doc) for doc in docs]
