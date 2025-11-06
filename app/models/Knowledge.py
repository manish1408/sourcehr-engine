from typing import List, Optional
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from app.schemas.Knowledge import KnowledgeSchema
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId

from dotenv import load_dotenv

load_dotenv()

class KnowledgeModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Knowledges"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    def get_knowledge(self, filters: dict) -> Optional[KnowledgeSchema]:
        """
        Retrieve a single knowledge entry matching the given filters.
        """
        filters["isDeleted"] = False
        document = self.collection.find_one(filters)
        if document:
            return KnowledgeSchema(**document)
        return None

    def get_knowledges(self, filters: dict = {}, skip: int = 0, limit: int = 10) -> List[KnowledgeSchema]:
        """
        Retrieve a list of knowledge entries matching the given filters with pagination.
        """
        filters["isDeleted"] = False
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        return [KnowledgeSchema(**doc) for doc in cursor]
    
    def get_knowledges_with_projection(self, filters: dict = {}, skip: int = 0, limit: int = 10, fields: List[str] = None) -> List[dict]:
        """
        Retrieve a list of knowledge entries matching the given filters with pagination and projection.
        """
        if fields is None:
            projection = {}
        else:
            projection = {field: 1 for field in fields}

        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        return list(cursor)

    def create_knowledge(self, data: dict) -> PyObjectId:
        """
        Create a new knowledge document in the database.
        """
        data["createdOn"] = datetime.utcnow()
        knowledge = KnowledgeSchema(**data)
        result = self.collection.insert_one(knowledge.dict(by_alias=True))
        return result.inserted_id

    def update_knowledge(self, knowledge_id: str, updates: dict) -> bool:
        """
        Update an existing knowledge entry by its ID.
        """
        filters = {"_id": ObjectId(knowledge_id), "isDeleted": False}
        result = self.collection.update_one(filters, {"$set": updates})
        return result.modified_count > 0
    
    def push_vector_namespace(self, knowledge_id: str, namespace: str) -> bool:
        """
        Push a new namespace to the knowledge entry's VectorDatabase field.
        """
        filters = {"_id": ObjectId(knowledge_id), "isDeleted": False}
        result = self.collection.update_one(filters, {"$set": {"vectorDatabase.namespace": namespace}})
        return result.modified_count > 0

    def soft_delete_knowledge(self, knowledge_id: str) -> bool:
        """
        Soft delete a knowledge entry by marking it as deleted and setting DeletedOn.
        """
        result = self.collection.update_one(
            {"_id": ObjectId(knowledge_id), "isDeleted": False},
            {"$set": {"isDeleted": True, "deletedOn": datetime.utcnow()}}
        )
        return result.modified_count > 0

    def delete_knowledge(self, knowledge_id: str) -> bool:
        """
        Permanently delete a knowledge document from the database.
        """
        result = self.collection.delete_one({"_id": ObjectId(knowledge_id), "isDeleted": False})
        return result.deleted_count > 0
