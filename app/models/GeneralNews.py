import os
from datetime import date
from typing import Optional

from app.helpers.Database import MongoDB
from app.schemas.GeneralNews import GeneralNewsDocument


def _as_iso_string(target_date: date) -> str:
    return target_date.isoformat()


class GeneralNewsModel:
    def __init__(self, db_name: Optional[str] = None, collection_name: str = "GeneralNews") -> None:
        database_name = db_name or os.getenv("DB_NAME")
        if not database_name:
            raise ValueError("DB_NAME environment variable is not set")
        database = MongoDB.get_database(database_name)
        self.collection = database[collection_name]
        self.collection.create_index("summaryDate", unique=True)

    def replace_summary(self, document: GeneralNewsDocument) -> str:
        self.collection.delete_many({"summaryDate": document.summaryDate})
        payload = document.model_dump(by_alias=True)
        result = self.collection.insert_one(payload)
        return str(result.inserted_id)
