import os
from pymongo.collection import Collection
from bson import ObjectId
from typing import Optional, List
from datetime import datetime
from app.schemas.WebsiteCrawl import WebsiteCrawlSchema

from app.helpers.Database import MongoDB


class WebsiteCrawlModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Crawler"):
        self.collection = MongoDB.get_database(db_name)[collection_name]
        
    def create_website_crawl(self, data: dict) -> str:
        
        """
        Insert a new website crawl document.
        """
        data = WebsiteCrawlSchema(**data)

        result = self.collection.insert_one(data.dict(by_alias=True))
        return str(result.inserted_id)


    def get_website_crawl(self, filters: dict) -> Optional[WebsiteCrawlSchema]:
            """
            Retrieve a single website crawl entry matching the given filters.
            """
            document = self.collection.find_one(filters)
            if document:
                document["_id"] = str(document["_id"])
                return WebsiteCrawlSchema(**document)
            return None

    def get_website_crawls(self, filters: dict = {}, skip: int = 0, limit: int = 10) -> List[WebsiteCrawlSchema]:
        """
        Retrieve a list of website crawl entries matching the given filters with pagination,
        excluding the 'listOfCrawlableUrls' field.
        """
        cursor = self.collection.find(filters, {"listOfCrawlableUrls": 0}).skip(skip).limit(limit)
        return [
            WebsiteCrawlSchema(**{**doc, "_id": str(doc["_id"])}).dict(exclude={"listOfCrawlableUrls"})
            for doc in cursor
        ]

    def get_website_crawl_with_paginated_urls(self, filters: dict, url_skip: int = 0, url_limit: int = 10) -> Optional[dict]:
        """
        Retrieve a single website crawl entry matching the given filters,
        with paginated listOfCrawlableUrls and total count.
        """
        document = self.collection.find_one(filters)
        if document:
            document["_id"] = str(document["_id"])
            urls = document.get("listOfCrawlableUrls", [])
            paginated_urls = urls[url_skip:url_skip + url_limit]
            document["listOfCrawlableUrls"] = paginated_urls
            result = WebsiteCrawlSchema(**document).dict()
            return result
        return None

    def update_website_crawl(self, filters: dict, update_data: dict) -> bool:
        """
        Update a website crawl document by filters.
        """
        result = self.collection.update_one(filters, {"$set": update_data})
        return result.modified_count > 0

    def delete_website_crawl(self, website_crawl_id: str) -> bool:
        """
        Delete a website crawl document
        """
        result = self.collection.delete_one({"_id": ObjectId(website_crawl_id)})
        return result.deleted_count>0