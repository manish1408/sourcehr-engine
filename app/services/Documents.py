from app.models.Knowledge import KnowledgeModel
from app.models.Document import DocumentModel
from app.models.User import UserModel
from app.helpers.Utilities import Utils
from app.helpers.VectorDB import VectorDB
from app.helpers.AzureStorage import AzureBlobUploader
from app.helpers.AIChat import AIChat
from pydantic import ValidationError
from bson import ObjectId
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler(job_defaults={
    'coalesce': True,
    'max_instances': 1,
    'misfire_grace_time': 30,
})
scheduler.start()


load_dotenv()

class DocumentService:
    
    def __init__(self):
        self.document_model = DocumentModel()
        self.user_model = UserModel()
        self.azure_helper = AzureBlobUploader()

            
    async def delete_document(self, document_id):
        try:
            document = await self.document_model.get_document({'_id':ObjectId(document_id)})
            vector_db_helper = VectorDB("source-hr-knowledge")
            resp = vector_db_helper.deleteDocument(document.vectorDocId)
            data = False
            if resp:
                data = await self.document_model.delete_document(document_id)
            else:
                return {
                    "success": False,
                    "data": None,
                    "error":'Unable to delete document'
                }
            if(data):
                return {
                    "success": True,
                    "data": 'Successfully deleted document'
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "error":'Unable to delete document'
                }

        except ValidationError as e:
            error_details = e.errors()
            raise ValueError(f"Invalid data: {error_details}")
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error":str(e)
            }
    
    async def upload_and_add_document(self, file_path, file_name, source_type):
        ext = os.path.splitext(file_name)[1].lower()
        folder_by_ext = {
            '.pdf': ('pdf-knowledge', 'pdf'),
            '.docx': ('docx-knowledge', 'docx'),
            '.txt': ('txt-knowledge', 'txt')
        }
        folder_name, doc_type = folder_by_ext.get(ext, ('other-knowledge', ext.lstrip('.')))        
        file_url = self.azure_helper.upload_file_to_azure_blob(file_path, folder_name, ext)
        # Use correct field name to prevent duplicates
        existing_doc = await self.document_model.get_document({"name": file_name})
        if existing_doc:
            return {
                "success": False,
                "data": None,
                "error": 'A document with this name already exists.'
            }
        data = await self.document_model.create_document({
            "vectorDatabase": {
                "index": os.getenv("PINECONE_INDEX"),
                "namespace": "source-hr-knowledge"
            },
            "status": 'PENDING',
            "type": doc_type,
            "name": file_name,
            "originalSource": file_url,
            "sourceType": source_type,
            "vectorDocId": []
        })
        if data:
            return {
                "success": True,
                "data": "Document uploaded and queued for processing.",
            }
        else:
            return {
                "success": False,
                "data": None,
                "error": 'Unable to add document'
            }

    async def get_all_documents(self, page, limit=10):
        total_docs = await self.document_model.get_documents_count({})
        limit = limit
        total_pages = (total_docs + limit - 1) // limit
        number_to_skip = (page - 1) * limit
        docs = await self.document_model.get_documents({}, number_to_skip, limit)
        
        if not docs:
                return {
                    "success": False,
                    "data": None,
                    "error": "No documents found"
                }

        return {
                "success": True,
                "data": {
                    "documents": docs,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                    }
                }
            }
        
        

    
        
    async def get_document_by_id(self, document_id):
        try:

            resp = await self.document_model.get_document({ "_id":ObjectId(document_id) })
                
            if(resp):
                return {
                    "success": True,
                    "data": resp
                }
                
            else:
                return {
                    "success": False,
                    "data": None,
                    "error":'Unable to retrieve the file'
                }

        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error":str(e)
            }
            
    async def process_pending_documents(self):
        try:
            # Atomically find and claim a pending document
            pending_doc = await self.document_model.collection.find_one_and_update(
                {"status": "PENDING"},
                {"$set": {"status": "IN_PROGRESS"}},
                projection={"_id": 1, "originalSource": 1, "name": 1, "sourceType": 1}
            )
            if not pending_doc:
                return {"success": False, "error": "No pending documents left", "data": None}

            doc_id = pending_doc["_id"]
            file_path = pending_doc["originalSource"]
            file_name = pending_doc["name"]
            vector_db_helper = VectorDB("source-hr-knowledge")
            try:
                source_type = pending_doc.get("sourceType", "")
                vector_docs_results = vector_db_helper.enterDocumentToKnowledge(file_path, file_name, source_type)
                await self.document_model.update_document(
                    str(doc_id),
                    {"status": "SUCCESS", "vectorDocId": vector_docs_results}
                )
                return {"success": True, "error": None, "data": str(doc_id)}
            except Exception as e:
                # Align with DocumentStatus enum
                await self.document_model.update_document(str(doc_id), {"status": "ERROR"})
                return {"success": False, "error": str(e), "data": str(doc_id)}
        except Exception as e:
            return {"success": False, "error": str(e), "data": None}
            
    def schedule_processor(self):
        try:
            # Schedule the document processor to run every 10 seconds (adjust as needed)
            scheduler.add_job(
                self.process_pending_documents,
                'interval',
                seconds=10,
                id='document_processor_job',
                max_instances=1,
                coalesce=True,
                misfire_grace_time=30,
                replace_existing=True,
            )
            return {"success": True, "data": "Document processor scheduled successfully"}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
            
