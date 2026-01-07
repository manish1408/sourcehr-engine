 
import os
from typing import List
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.News import CreateNewsSchema

class NewsModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="News"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    def create(self, data: dict):
        """
        Create a new news document in the database.
        """
        from bson import ObjectId
        
        data["created_at"] = datetime.utcnow()
        news = CreateNewsSchema(**data)
        news_dict = news.model_dump(by_alias=True, mode='python')
        
        # Ensure all news items have _id ObjectIds
        if "news" in news_dict and isinstance(news_dict["news"], list):
            for news_item in news_dict["news"]:
                if "_id" not in news_item or news_item.get("_id") is None:
                    news_item["_id"] = ObjectId()
        
        result = self.collection.insert_one(news_dict)
        return result.inserted_id
    
    
    def get_news(self, dashboard_id: str) -> List[CreateNewsSchema]:
        """
        Retrieve news for a specific dashboard from the database.
        """
        cursor = self.collection.find({"dashboardId": dashboard_id})
        news_list = []
        for doc in cursor:
            # Ensure detailedDescription exists for backward compatibility
            if "news" in doc:
                for news_item in doc["news"]:
                    if "detailedDescription" not in news_item or not news_item.get("detailedDescription"):
                        # Use description as fallback for existing items
                        news_item["detailedDescription"] = news_item.get("description", "")
            news_list.append(CreateNewsSchema(**doc))
        return news_list
    
    def update_news(self, dashboard_id: str, data: dict):
        """
        Update a news document in the database.
        Validates data and ensures all news items have proper ObjectIds.
        """
        from bson import ObjectId
        
        # Validate the data using the schema
        try:
            validated_data = CreateNewsSchema(**data)
        except Exception as e:
            print(f"Error validating news data: {e}")
            raise
        
        # Get the validated dict with python mode to preserve ObjectId types
        validated_dict = validated_data.model_dump(by_alias=True, mode='python')
        
        # Ensure all news items have _id ObjectIds
        if "news" in validated_dict and isinstance(validated_dict["news"], list):
            for news_item in validated_dict["news"]:
                if "_id" not in news_item or news_item.get("_id") is None:
                    news_item["_id"] = ObjectId()
        
        result = self.collection.update_one({"dashboardId": dashboard_id}, {"$set": validated_dict})
        return result.modified_count

