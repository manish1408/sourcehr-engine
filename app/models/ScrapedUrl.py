import os
from typing import Optional, List
from app.helpers.Database import MongoDB
from datetime import datetime
from app.schemas.ScrapedUrl import ScrapedUrlSchema
from bson import ObjectId


class ScrapedUrlModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="ScrapedUrls"):
        self.collection = MongoDB.get_database(db_name)[collection_name]
        # Create compound index on dashboardId, source, and url for fast lookups
        self.collection.create_index([("dashboardId", 1), ("source", 1), ("url", 1)], unique=True)

    def create(self, data: dict) -> ObjectId:
        """
        Create a new scraped URL document in the database.
        """
        data["createdAt"] = datetime.utcnow()
        data["updatedAt"] = datetime.utcnow()
        scraped_url = ScrapedUrlSchema(**data)
        result = self.collection.insert_one(scraped_url.model_dump(by_alias=True))
        return result.inserted_id
    
    def get_by_dashboard_source_url(self, dashboard_id: str, source: str, url: str) -> Optional[ScrapedUrlSchema]:
        """
        Check if a URL has already been scraped for a specific dashboard and source.
        """
        document = self.collection.find_one({
            "dashboardId": dashboard_id,
            "source": source,
            "url": url
        })
        if document:
            return ScrapedUrlSchema(**document)
        return None
    
    def update_scraped_url(self, dashboard_id: str, source: str, url: str, vector_db_ids: List[str]) -> bool:
        """
        Update a scraped URL document with vector DB IDs.
        """
        result = self.collection.update_one(
            {
                "dashboardId": dashboard_id,
                "source": source,
                "url": url
            },
            {
                "$set": {
                    "scraped": True,
                    "vectorDbIds": vector_db_ids,
                    "error": None,
                    "updatedAt": datetime.utcnow()
                },
                "$unset": {"error": ""}
            }
        )
        return result.modified_count > 0
    
    def create_or_update_with_error(self, dashboard_id: str, source: str, url: str, error: str, scraped: bool = False) -> ObjectId:
        """
        Create or update a scraped URL entry with an error message.
        Used when scraping fails but we still want to track the attempt.
        """
        existing = self.get_by_dashboard_source_url(dashboard_id, source, url)
        
        if existing:
            # Update existing record with error
            self.collection.update_one(
                {
                    "dashboardId": dashboard_id,
                    "source": source,
                    "url": url
                },
                {
                    "$set": {
                        "scraped": scraped,
                        "error": error,
                        "updatedAt": datetime.utcnow()
                    }
                }
            )
            return existing.id
        else:
            # Create new record with error
            data = {
                "dashboardId": dashboard_id,
                "source": source,
                "url": url,
                "scraped": scraped,
                "error": error,
                "vectorDbIds": None
            }
            return self.create(data)



