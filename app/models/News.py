 
import os
from typing import List
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.News import CreateNewsSchema

class NewsModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="News"):
        self.collection = MongoDB.get_async_database(db_name)[collection_name]

    async def create(self, data: dict):
        """
        Create a new news document in the database.
        """
        data["created_at"] = datetime.utcnow()
        news = CreateNewsSchema(**data)
        result = await self.collection.insert_one(news.model_dump(by_alias=True))
        return result.inserted_id
    
    
    async def get_news(self, dashboard_id: str) -> List[CreateNewsSchema]:
        """
        Retrieve news for a specific dashboard from the database.
        """
        cursor = self.collection.find({"dashboardId": dashboard_id})
        docs = await cursor.to_list(length=None)
        return [CreateNewsSchema(**doc) for doc in docs]
    
    async def update_news(self, dashboard_id: str, data: dict):
        """
        Update a news document in the database.
        """
        result = await self.collection.update_one({"dashboardId": dashboard_id}, {"$set": data})
        return result.modified_count

