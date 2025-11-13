import os
from typing import List
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.DashboadCompliance import DashboardCompliance

class DashboardComplianceModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Dashboard Compliance"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    def create(self, data: dict):
        """
        Create a new dashboard compliance document in the database.
        """
        data["createdAt"] = datetime.utcnow()
        data = DashboardCompliance(**data)
        result = self.collection.insert_one(data.model_dump(by_alias=True))
        return result.inserted_id
    
    def get_law_changes(self, dashboard_id: str) -> List[DashboardCompliance]:
        """
        Retrieve law changes for a specific dashboard from the database.
        """
        cursor = self.collection.find({"dashboardId": dashboard_id})
        return [DashboardCompliance(**doc) for doc in cursor]

    def delete_by_dashboard(self, dashboard_id: str) -> int:
        """Delete all compliance records for the given dashboard."""
        result = self.collection.delete_many({"dashboardId": dashboard_id})
        return result.deleted_count
