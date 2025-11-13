import os
from datetime import datetime
from typing import Optional

from bson import ObjectId
from pymongo import ReturnDocument

from app.helpers.Database import MongoDB
from app.schemas.Queue import QueueEntry, QueueStatus, QueueType


class QueueModel:
    def __init__(self, db_name: Optional[str] = None, collection_name: str = "Queue") -> None:
        database_name = db_name or os.getenv("DB_NAME")
        if not database_name:
            raise ValueError("DB_NAME environment variable is not set")
        database = MongoDB.get_database(database_name)
        self.collection = database[collection_name]
        self.collection.create_index([("status", 1), ("createdAt", 1)])

    def enqueue(self, dashboard_id: str, queue_type: QueueType) -> QueueEntry:
        entry = QueueEntry(dashboardId=dashboard_id, type=queue_type)
        result = self.collection.insert_one(entry.model_dump(by_alias=True))
        entry.id = result.inserted_id
        return entry

    def claim_next(self) -> Optional[QueueEntry]:
        doc = self.collection.find_one_and_update(
            {"status": QueueStatus.PENDING.value},
            {
                "$set": {
                    "status": QueueStatus.PROCESSING.value,
                    "updatedAt": datetime.utcnow(),
                }
            },
            sort=[("createdAt", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if doc:
            return QueueEntry(**doc)
        return None

    def mark_status(self, entry_id: ObjectId, status: QueueStatus, error: Optional[str] = None) -> None:
        update_set = {
            "status": status.value,
            "updatedAt": datetime.utcnow(),
        }
        if error is not None:
            update_set["error"] = error
            update = {"$set": update_set}
        else:
            update = {"$set": update_set, "$unset": {"error": ""}}
        self.collection.update_one({"_id": ObjectId(entry_id)}, update, upsert=False)
