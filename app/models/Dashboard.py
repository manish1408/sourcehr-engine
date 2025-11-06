from copy import deepcopy
from dataclasses import fields
import os
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from app.helpers.Database import MongoDB

from app.schemas.PyObjectId import PyObjectId
from app.schemas.Dashboard import DashboardSchema



class DashboardModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Dashboards"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    def create_dashboard(self, data: dict) -> PyObjectId:
        result = self.collection.insert_one(data)
        return result.inserted_id
    
    def list_dashboards(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[DashboardSchema]:
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        return list(cursor)
    
   
    def get_dashboards_with_projection(self, filters: dict = {}, skip: int = 0, limit: int = 100, fields: List[str] = None) -> List[dict]:
        if fields is None:
            projection = {}
        else:
            projection = {field: 1 for field in fields}

        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        return list(cursor)

    def get_dashboard(self, filters: dict) -> Optional[DashboardSchema]:
        """
        Retrieve a single Dashboard data  matching the given filters.
        """
        document = self.collection.find_one(filters)
        if document:
            return DashboardSchema(**document)
        return None

    def update_dashboard(self, dashboard_id: str, data: dict) -> bool:
        data["updatedAt"] = datetime.utcnow()
        result = self.collection.update_one({"_id": ObjectId(dashboard_id)}, {"$set": data})
        return result.modified_count > 0

    def delete_dashboard(self, dashboard_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(dashboard_id)})
        return result.deleted_count > 0



    def duplicate_dashboard(self, dashboard_id: str, user_id: str) -> Optional[str]:
        dashboard = self.get_dashboard({"_id": ObjectId(dashboard_id)})
        if not dashboard:
            return None

        dashboard_data = deepcopy(dashboard.model_dump())  

        dashboard_data.pop("id", None)
        dashboard_data["name"] = f"{dashboard_data.get('name', 'Untitled')} (Copy)"
        dashboard_data["userId"] = user_id
        dashboard_data["createdAt"] = dashboard_data["updatedAt"] = datetime.utcnow()

        return self.create_dashboard(dashboard_data)
