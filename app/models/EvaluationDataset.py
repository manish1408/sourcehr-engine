from typing import List, Optional
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from datetime import datetime
from app.schemas.EvaluationDataset import EvaluationDataset  # Make sure this exists!
from app.schemas.PyObjectId import PyObjectId

from dotenv import load_dotenv

load_dotenv()

class EvaluationDatasetModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Evaluation Dataset"):
        self.collection = MongoDB.get_database(db_name)[collection_name]
        
    async def create_evaluation_dataset(self, data: dict) -> PyObjectId:
        """
        Create a new evaluation document in the database.
        """
        data["created_at"] = datetime.utcnow()
        evaluation = EvaluationDataset(**data)
        result = await self.collection.insert_one(evaluation.model_dump(exclude="id",by_alias=True))
        return result.inserted_id

    async def get_documents_count(self, filters: dict) -> int:
        """
        Retrieve a count of documents matching the given filters.
        """
        total_count = await self.collection.count_documents(filters)
        return total_count if total_count else 0
    
    async def get_evaluation_dataset_by_id(self, dataset_id: str) -> Optional[EvaluationDataset]:
        """
        Retrieve an evaluation entry by its ID.
        """
        doc = await self.collection.find_one({"_id": "dataset_id"})
        return EvaluationDataset(**doc) if doc else None

    async def get_all_evaluation_datasets(self, filters: dict = {}, skip: int = 0, limit: int = 100):
        """
        Retrieve a list of evaluation entries matching the given filters with pagination.
        """
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        results = await cursor.to_list(length=limit)
        return [EvaluationDataset(**doc) for doc in results]
        
    async def update_evaluation_dataset(self, dataset_id: str, data: dict) -> bool:
        """
        Update an evaluation entry by its ID.
        """
        data["updated_at"] = datetime.utcnow()
        update_result = await self.collection.update_one(
            {"_id":"dataset_id"},
            {"$set": data}
        )
        return update_result.modified_count > 0
        
    async def delete_evaluation_dataset(self, dataset_id: str) -> bool:
        """
        Permanently delete an evaluation from the database.
        """
        result = await self.collection.delete_one({"datasetId":dataset_id})
        return result.deleted_count > 0