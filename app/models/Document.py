from typing import List, Optional
from app.helpers.Database import MongoDB
from bson import ObjectId
import os
from app.schemas.Documents import DocumentsSchema
from datetime import datetime
from app.schemas.PyObjectId import PyObjectId

from dotenv import load_dotenv

load_dotenv()

class DocumentModel:
    def __init__(self, db_name=os.getenv('DB_NAME'), collection_name="Documents"):
        self.collection = MongoDB.get_database(db_name)[collection_name]

    async def get_document(self, filters: dict) -> Optional[DocumentsSchema]:
        """
        Retrieve a single document matching the given filters.
        """
        document = await self.collection.find_one(filters)
        if document:
            return DocumentsSchema(**document)
        return None

    async def get_documents(self, filters: dict = {}, skip: int = 0, limit: int = 10) -> List[DocumentsSchema]:
        """
        Retrieve a list of documents matching the given filters with pagination.
        """
        cursor = self.collection.find(filters).skip(skip).limit(limit)
        results = await cursor.to_list(length=limit)
        return [DocumentsSchema(**doc) for doc in results]
    
    async def get_documents_count(self, filters: dict) -> int:
        """
        Retrieve a count of documents matching the given filters.
        """
        total_count = await self.collection.count_documents(filters)
        if total_count:
            return total_count
        return 0
    
    async def get_documents_with_projection(self, filters: dict = {}, skip: int = 0, limit: int = 10, fields: List[str] = None) -> List[dict]:
        """
        Retrieve a list of documents matching the given filters with pagination and projection.
        """
        if fields is None:
            projection = {}
        else:
            projection = {field: 1 for field in fields}

        cursor = self.collection.find(filters, projection).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def create_document(self, data: dict) -> PyObjectId:
        """
        Create a new document in the database.
        """
        data["createdOn"] = datetime.utcnow()
        document = DocumentsSchema(**data)
        result = await self.collection.insert_one(document.dict(by_alias=True))
        return result.inserted_id

    async def update_document(self, document_id: str, updates: dict) -> bool:
        """
        Update an existing document by its ID.
        """
        filters = {"_id": ObjectId(document_id)}
        result = await self.collection.update_one(filters, {"$set": updates})
        return result.modified_count > 0
    
    async def push_vector_id(self, document_id: str, vector_id: str) -> bool:
        """
        Push a new vector ID to the document's VectorDocId array.
        """
        filters = {"_id": ObjectId(document_id)}
        result = await self.collection.update_one(filters, {"$push": {"vectorDocId": vector_id}})
        return result.modified_count > 0


    async def delete_document(self, document_id: str) -> bool:
        """
        Permanently delete a document from the database.
        """
        result = await self.collection.delete_one({"_id": ObjectId(document_id)})
        return result.deleted_count > 0
    
    async def delete_many_document(self, filter: dict) -> bool:
        """
        Permanently delete a document from the database.
        """
        result = await self.collection.delete_many(filter)
        return result.deleted_count > 0