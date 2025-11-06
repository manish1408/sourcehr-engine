from typing import List, Optional
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from datetime import datetime
from app.schemas.Evaluation import EvaluationSchema  # Make sure this exists!
from app.schemas.PyObjectId import PyObjectId

from dotenv import load_dotenv

load_dotenv()

class EvaluationModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Evaluation"):
        self.collection = MongoDB.get_database(db_name)[collection_name]
        
    def create_evaluation(self, data: dict) -> PyObjectId:
        """
        Create a new evaluation document in the database.
        """
        data["createdAt"] = datetime.utcnow()
        evaluation = EvaluationSchema(**data)
        result = self.collection.insert_one(evaluation.model_dump(exclude="id",by_alias=True))
        return result.inserted_id

    def get_documents_count(self, filters: dict) -> int:
        """
        Retrieve a count of documents matching the given filters.
        """
        total_count = self.collection.count_documents(filters)
        return total_count if total_count else 0
    
    def get_evaluation_by_id(self, evaluation_id: str) -> Optional[EvaluationSchema]:
        """
        Retrieve an evaluation entry by its ID.
        """
        doc = self.collection.find_one({"_id": ObjectId(evaluation_id)})
        return EvaluationSchema(**doc) if doc else None

    def get_all_evaluations(self, filters: dict = {}, skip: int = 0, limit: int = 100):
        """
        Retrieve a list of evaluation entries matching the given filters with pagination.
        """
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        return [EvaluationSchema(**doc) for doc in cursor]
        
    def update_evaluation(self, evaluation_id: str, data: dict) -> bool:
        """
        Update an evaluation entry by its ID.
        """
        data["updated_at"] = datetime.utcnow()
        update_result = self.collection.update_one(
            {"_id": ObjectId(evaluation_id)},
            {"$set": data}
        )
        return update_result.modified_count > 0
        
    def delete_evaluation(self, evaluation_id: str) -> bool:
        """
        Permanently delete an evaluation from the database.
        """
        result = self.collection.delete_one({"_id": ObjectId(evaluation_id)})
        return result.deleted_count > 0