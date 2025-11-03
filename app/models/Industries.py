import os
from typing import List
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.Industries import IndustrySchema

class IndustriesModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Industries"):
        self.collection = MongoDB.get_async_database(db_name)[collection_name]

    async def create(self, data: dict):
        """
        Create a new industry document in the database.
        """
        data["created_at"] = datetime.utcnow()
        industry = IndustrySchema(**data)
        result = await self.collection.insert_one(industry.model_dump(by_alias=True))
        return result.inserted_id
    
    async def get_industries(self) -> List[IndustrySchema]:
        """
        Retrieve all industries from the database.
        """
        cursor = self.collection.find({})
        docs = await cursor.to_list(length=None)
        return [IndustrySchema(**doc) for doc in docs]