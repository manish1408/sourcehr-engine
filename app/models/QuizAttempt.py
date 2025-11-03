from datetime import datetime
import os
from app.helpers.Database import MongoDB
from app.schemas import PyObjectId
from app.schemas.QuizAttempt import QuizAttempt,AnswerSubmission
from bson import ObjectId
from typing import List, Optional

class QuizAttemptModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="quizAttempts"):
        self.collection = MongoDB.get_database(db_name)[collection_name]


    async def create_attempt(self, data: dict) -> PyObjectId:
        """
        Create a new user document in the database.
        """
        data["createdOn"] = datetime.utcnow()
        data = QuizAttempt(**data)
        result = await self.collection.insert_one(data.dict(by_alias=True))
        return result.inserted_id

    async def get_attempt_by_id(self, filters: dict) -> QuizAttempt:
        """
        Retrieve a quiz attempt by its ID.
        """
        attempt = await self.collection.find_one(filters)
        return QuizAttempt(**attempt)
    
    async def get_attempts(self, filters: dict = {}, skip: int = 0, limit: int = 100) -> List[dict]:
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("createdOn", -1)
        return await cursor.to_list(length=limit)
    
    async def update_attempt(self, attempt_id: str, data: dict) -> bool:
        data["updatedOn"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"_id": ObjectId(attempt_id)},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def push_answer(self, attempt_id: str, answer: AnswerSubmission) -> bool:
        result = await self.collection.update_one(
            {"_id": ObjectId(attempt_id)},
            {"$push": {"answers": answer.model_dump()}}
        )
        return result.modified_count > 0
        
        
    async def update_selected_answers(self, attempt_id: str, updates: AnswerSubmission) -> bool:
        result = await self.collection.update_one(
            {
                "_id": ObjectId(attempt_id),
                "answers.questionId": updates.questionId
            },
            {
                "$set": {
                    "answers.$.selectedOptions": updates.selectedOptions
                }
            }
        )
        return result.modified_count > 0

    
    async def delete_attempt(self, attempt_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(attempt_id)})
        return result.deleted_count > 0

    async def get_leaderboard(self, skip: int = 0, limit: int = 10):
        pipeline = [
            {"$match": {"status": "SUBMITTED"}},  # Exact match
            {"$group": {
                "_id": "$userId",
                "totalScore": {"$sum": "$score"},
                "quizzesAttempted": {"$sum": 1},
                "averagePercentage": {"$avg": "$percentage"},
                "lastAttemptedOn": {"$max": "$createdOn"}
            }},
            {"$sort": {"averagePercentage": -1, "totalScore": -1}}  # Tie-breaker
        ]

        cursor = self.collection.aggregate(pipeline)
        all_results = await cursor.to_list(length=None)

        for i, doc in enumerate(all_results, start=1):
            doc["rank"] = i

        paginated_results = all_results[skip: skip + limit]

        return [{
            "userId": doc["_id"],
            "rank": doc["rank"],
            "totalScore": doc["totalScore"],
            "quizzesAttempted": doc["quizzesAttempted"],
            "averagePercentage": round(doc["averagePercentage"], 2),
            "lastAttemptedOn": doc.get("lastAttemptedOn")
        } for doc in paginated_results]