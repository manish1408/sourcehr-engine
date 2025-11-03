from typing import List, Optional
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from app.schemas.SerpUrl import SerpUrlSchema
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId

from dotenv import load_dotenv

load_dotenv()

class SerpUrlModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="SerpUrls"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def ensure_index(self):
        """Create unique index on URL to prevent duplicates"""
        await self.collection.create_index("url", unique=True)

    async def create_serp_url(self, data: dict) -> PyObjectId:
        """
        Create a new SERP URL document in the database.
        Checks for duplicates before inserting.
        """
        # Check if URL already exists
        existing_url = await self.collection.find_one({"url": data["url"]})
        if existing_url:
            return existing_url["_id"]
        
        data["createdOn"] = datetime.utcnow()
        serp_url = SerpUrlSchema(**data)
        result = await self.collection.insert_one(serp_url.dict(by_alias=True))
        return result.inserted_id



    async def get_serp_url(self, filters: dict) -> Optional[SerpUrlSchema]:
        """
        Retrieve a single SERP URL matching the given filters.
        """
        document = await self.collection.find_one(filters)
        if document:
            return SerpUrlSchema(**document)
        return None


    async def update_serp_url(self, url_id: str, update_data: dict) -> bool:
        """
        Update a SERP URL document by its ID.
        """
        filters = {"_id": ObjectId(url_id)}
        result = await self.collection.update_one(filters, {"$set": update_data})
        return result.modified_count > 0


