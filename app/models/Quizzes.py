import os
from typing import List, Optional
from bson import ObjectId
from datetime import datetime

from app.helpers.Database import MongoDB
from app.schemas.Quizzes import Quiz
from app.schemas.PyObjectId import PyObjectId


class QuizModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Quizzes"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def create_quiz(self, data: dict) -> PyObjectId:
        data["createdOn"] = datetime.utcnow()
        data["updatedOn"] = datetime.utcnow()
        data["questions"] = []
        result = await self.collection.insert_one(data)
        return result.inserted_id

    async def list_quizzes(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[dict]:
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("createdOn", -1)
        return await cursor.to_list(length=limit)

    async def get_quizzes_with_projection(
        self, filters: dict = {}, skip: int = 0, limit: int = 100, fields: List[str] = None
    ) -> List[dict]:
        projection = {field: 1 for field in fields} if fields else {}
        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_quiz(self, filters: dict) -> Optional[Quiz]:
        document = await self.collection.find_one(filters)
        if document:
            return Quiz(**document)
        return None

    async def update_quiz(self, quiz_id: str, data: dict) -> bool:
        data["updatedOn"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(quiz_id)},
            {"$set": data}
        )
        return result.modified_count > 0

    async def delete_quiz(self, quiz_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(quiz_id)})
        return result.deleted_count > 0

    async def add_question(self, quiz_id: str, question_data: dict) -> bool:
        question_data["_id"] = ObjectId()
        result = await self.collection.update_one(
            {"_id": ObjectId(quiz_id)},
            {"$push": {"questions": question_data}, "$set": {"updatedOn": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    
    async def update_question(self, quiz_id: str, question_id: str, updates: dict) -> bool:  
        """
        Update a specific question inside a quiz using dot notation.
        """
        set_updates = {f"questions.$.{key}": value for key, value in updates.items()}
        set_updates["updatedOn"] = datetime.utcnow()

        result = await self.collection.update_one(
            {
                "_id": ObjectId(quiz_id),
                "questions._id": ObjectId(question_id)
            },
            {
                "$set": set_updates
            }
        )
        return result.modified_count > 0


    async def remove_question(self, quiz_id: str, question_id: str) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(quiz_id)},
            {"$pull": {"questions": {"_id": ObjectId(question_id)}}, "$set": {"updatedOn": datetime.utcnow()}}
        )
        return result.modified_count > 0
