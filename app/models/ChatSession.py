from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv
from app.schemas.ChatSession import ChatSessionSchema,ChatMessageSchema
from app.helpers.Database import MongoDB
from app.schemas.PyObjectId import PyObjectId

load_dotenv()

class ChatSessionModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="ChatSessions"):
        self.collection = MongoDB.get_database(db_name)[collection_name]
    
    def create_session(self, data: dict) -> PyObjectId:
        """
        Create a new session in the database.
        """
        data["createdOn"] = datetime.utcnow()
        document = ChatSessionSchema(**data)
        result = self.collection.insert_one(document.dict(by_alias=True))
        return result.inserted_id

    def get_session(self, filters: dict) -> Optional[dict]:
        document = self.collection.find_one(filters)
        if document:
            session = ChatSessionSchema(**document)
            return session.dict(by_alias=True)
        return None
    
    
    def update_session(self, session_id: str, updates: dict) -> bool:
        """
        Update an existing session document by its ID.
        """
        filters = {"_id": ObjectId(session_id)}
        result = self.collection.update_one(filters, {"$set": updates})
        return result.modified_count > 0
    
    
    def get_session_with_projection(self, filters: dict = {}, skip: int = 0, limit: int = 5, fields: List[str] = None) -> List[dict]:
        """
        Retrieve a list of sessions matching the given filters with pagination and optional projection.
        """
        projection = {}
        if fields:
            for field in fields:
                projection[field] = 1  
        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        return list(cursor)


    def get_sessions(self, filters: dict = {}, skip: int = 0, limit: int = 10) -> List[ChatSessionSchema]:
        cursor = self.collection.find(filters).skip(skip).limit(limit).sort("createdOn",-1)
        return [ChatSessionSchema(**doc) for doc in cursor]
    
    def add_message(self, session_id: str, message_data: dict) -> bool:
        
        message = ChatMessageSchema(**message_data)
        # print(message)
        message_data = message.dict(by_alias=True) 
        message_data["createdOn"] = datetime.utcnow()
        result = self.collection.update_one(
            {"_id": ObjectId(session_id)},
            {"$push": {"messages": message_data}}
        )
        if result.modified_count > 0:
            return str(message.id)
        return None
    
    def update_message_with_message_id(self,session_id:str, message_id: str,message:str,citations:list):
        parent_id = ObjectId(session_id)
        message_id = ObjectId(message_id)
        result = self.collection.update_one(
            { "_id": parent_id, "messages._id": message_id },
            {
                "$set": {
                    "messages.$[msg].message":message,
                    "messages.$[msg].citations":citations,
                    "messages.$[msg].createdOn":datetime.utcnow()       
                }
            },
            array_filters=[{ "msg._id": message_id }]
        )
        return result.modified_count > 0

    def update_message_sentiment_with_message_id(self,session_id:str, message_id: str,sentiment:str):
        parent_id = ObjectId(session_id)
        message_id = ObjectId(message_id)
        result = self.collection.update_one(
            { "_id": parent_id, "messages._id": message_id },
            {
                "$set": {
                    "messages.$[msg].Sentiment":sentiment 
                }
            },
            array_filters=[{ "msg._id": message_id }]
        )
        return result.modified_count > 0
    def get_sessions_count(self, filters: dict) -> int:
        """
        Retrieve a count of sessions matching the given filters.
        """
        total_count = self.collection.count_documents(filters)
        if total_count:
            return total_count
        return 0


    def delete_session(self, session_id: str) -> bool:
        result = self.collection.delete_one({"_id": ObjectId(session_id)})
        return result.deleted_count > 0

