from typing import List, Optional
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from app.schemas.ChatFeedback import ChatFeedbackSchema
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId

from dotenv import load_dotenv

load_dotenv()
class ChatFeedbackModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="ChatFeedback"):
        self.collection = MongoDB.get_database(db_name)[collection_name]
        
            
    def create_chat_feedback(self, data: dict) -> PyObjectId:
        """
        Create a new chat_feedback document in the database.
        """
        data["CreatedOn"] = datetime.utcnow()
        chat_feedback = ChatFeedbackSchema(**data)
        result = self.collection.insert_one(chat_feedback.dict(by_alias=True))
        return result.inserted_id

    def get_documents_count(self, filters: dict) -> int:
        """
        Retrieve a count of documents matching the given filters.
        """
        total_count = self.collection.count_documents(filters)
        if total_count:
            return total_count
        return 0
    
    def get_chat_feedback_by_id(self, chat_feedback_id: str) -> Optional[ChatFeedbackSchema]:
        """
        Retrieve a chat_feedback entry by its ID.
        """
        return self.collection.find_one({"_id": ObjectId(chat_feedback_id)})

    def get_all_chat_feedbacks(self, filters: dict = {}, skip: int = 0, limit: int = 100):
        """
        Retrieve a list of chat_feedbacks entries matching the given filters with pagination.
        """
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        return list(cursor)
        
    def update_chat_feedback(self,chat_feedback_id,data):
        try:
            update_result = self.collection.update_one(
            {"_id": ObjectId(chat_feedback_id)},
            {"$set": data}
            )
            return update_result.modified_count > 0
        except Exception as e:
            return e
        
    def delete_chat_feedback(self,chat_feedback_id:str) ->bool :
        """
        Permanently delete chat_feedback from the database
        """
        result = self.collection.delete_one({"_id": ObjectId(chat_feedback_id)})
        return result.deleted_count > 0
            
