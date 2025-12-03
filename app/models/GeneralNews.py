import os
from datetime import date
from typing import Optional

from bson import ObjectId

from app.helpers.AzureStorage import AzureBlobUploader
from app.helpers.Database import MongoDB
from app.schemas.GeneralNews import GeneralNewsDocument, GeneralNewsItem


def _as_iso_string(target_date: date) -> str:
    return target_date.isoformat()


class GeneralNewsModel:
    def __init__(self, db_name: Optional[str] = None, collection_name: str = "GeneralNews") -> None:
        database_name = db_name or os.getenv("DB_NAME")
        if not database_name:
            raise ValueError("DB_NAME environment variable is not set")
        database = MongoDB.get_database(database_name)
        self.collection = database[collection_name]
        self.azure_blob = AzureBlobUploader()
        
        # Drop existing unique index on summaryDate if it exists (needed for multiple articles per date)
        try:
            self.collection.drop_index("summaryDate_1")
        except Exception:
            # Index doesn't exist or has different name, ignore
            pass

    def replace_summary(self, document: GeneralNewsDocument) -> str:
        """Legacy method - kept for backward compatibility."""
        self.collection.delete_many({"summaryDate": document.summaryDate})
        payload = document.model_dump(by_alias=True)
        result = self.collection.insert_one(payload)
        return str(result.inserted_id)

    def delete_by_date(self, summary_date: str) -> int:
        """Delete all entries for a specific date and their associated blob images."""
        # First, fetch all entries to get their logo URLs
        entries = list(self.collection.find({"summaryDate": summary_date}))
        
        # Delete blob images if they exist
        for entry in entries:
            logo_url = entry.get("logoUrl")
            if logo_url:
                try:
                    self.azure_blob.delete_file(logo_url)
                    print(f"[GeneralNewsModel] Deleted blob image: {logo_url}")
                except Exception as e:
                    print(f"[GeneralNewsModel] Failed to delete blob image {logo_url}: {e}")
        
        # Delete database entries
        result = self.collection.delete_many({"summaryDate": summary_date})
        return result.deleted_count

    def create_article(self, summaryDate: str, article: GeneralNewsItem) -> dict:
        """Create a single article entry at root level."""
        payload = {
            "_id": ObjectId(),
            "summaryDate": summaryDate,
            "title": article.title,
            "description": article.description,
            "organizationName": article.organizationName,
            "logoUrl": article.logoUrl,
        }
        result = self.collection.insert_one(payload)
        payload["_id"] = result.inserted_id
        return payload
