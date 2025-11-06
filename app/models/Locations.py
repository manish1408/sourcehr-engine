import os
from typing import List
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.Locations import LocationSchema

class LocationsModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Locations"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    def create(self, data: dict):
        """
        Create a new location document in the database.
        """
        data["created_at"] = datetime.utcnow()
        location = LocationSchema(**data)
        result = self.collection.insert_one(location.model_dump(by_alias=True))
        return result.inserted_id
    
    def get_locations(self) -> List[LocationSchema]:
        """
        Retrieve all industries from the database.
        """
        cursor = self.collection.find({})
        return [LocationSchema(**doc) for doc in cursor]
    
