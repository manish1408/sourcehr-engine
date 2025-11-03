from pymongo import ReturnDocument
from app.helpers.AIChatNoStream import AIChatNoStream
from app.models.Document import DocumentModel
from app.models.Dashboard import DashboardModel
from app.models.User import UserModel
from app.helpers.Utilities import Utils
from app.helpers.VectorDB import VectorDB
from app.helpers.AzureStorage import AzureBlobUploader
from app.helpers.AIChat import AIChat
from pydantic import ValidationError
from bson import ObjectId
import os
from dotenv import load_dotenv
from app.models.ChatSession import ChatSessionModel
from datetime import datetime
import json

load_dotenv()

class ChatService:
    
    def __init__(self):
        self.document_model = DocumentModel()
        self.user_model = UserModel()
        self.azure_helper = AzureBlobUploader()
        self.model= ChatSessionModel()
        self.dashboard_model=DashboardModel()

            
            
    async def add_text_to_knowledge(self, knowledge_id, text):
            knowledge_base = await self.knowledge_model.get_knowledge({'_id':ObjectId(knowledge_id)})
            
            random_hex = Utils.generate_hex_string(6)
            file_name = f"{text[:15].replace(' ','-')}-{random_hex}"
            
            vector_db_helper = VectorDB(knowledge_base.vectorDatabase.namespace)
            vector_docs_ids = vector_db_helper.enterTextKnowledge(text,file_name)
            if vector_docs_ids == None:
                return {
                    "success": False,
                    "data": None,
                    "error":'Unable to add document to vector db'
                }
            
            data = await self.document_model.create_document({
                "knowledgeId": str(knowledge_id),
                "vectorDatabase": {
                    "index": os.getenv("PINECONE_INDEX"),
                    "namespace": knowledge_base.vectorDatabase.namespace
                },
                "status": 'SUCCESS',
                "type": 'text',
                "name": file_name,
                "originalSource": text,
                "vectorDocId": vector_docs_ids
            })
            
            if(data):
                return {
                    "success": True,
                    "data": 'Successfully added document'
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "error":'Unable to add document'
                }
          


    async def generate_session_title(self, session_id, question, response):
        
        try:
            session = await self.model.get_session({"_id": ObjectId(session_id)})
            if session.get("sessionTitle") == "New Chat":
                # knowledge_base = await self.knowledge_model.get_knowledge({'_id': ObjectId(knowledge_id)})
                ai_chat = AIChat(namespace="source-hr-knowledge")
                resp = ai_chat.get_chat_session_title(question, response)
                session = await self.model.update_session(session_id, {"sessionTitle":resp.title})
                return session
            return
        except Exception as e:
            return None
        
    async def chat_stream(self, question, session_id):
        sessions = await self.model.get_session_with_projection(
            filters={"_id": ObjectId(session_id)},
            fields=["messages"]
        )

        if not sessions:
            yield {"error": "Session not found"}
            return

        session = sessions[0]
        session["messages"] = session.get("messages", [])[-5:]

        ai_chat = AIChat("source-hr-knowledge")
        full_response = ""
        final_citations = []

        try:
            async for token in ai_chat.chat_with_knowledge_stream_openai_tools(question, session):
                if token is None:
                    yield {"error": "Unable to generate response"}
                    return

                content = token.get("content", "")
                citations = token.get("citations", [])
                full_response += content

                if citations:
                    final_citations = citations

                yield {
                    "token": content,
                    "citations": [],
                    "messageId": None
                }

            user_message = {
                "message": question,
                "messageType": "user",
                "citations": [],
                "createdAt": datetime.utcnow()
            }

            assistant_message = {
                "message": full_response,
                "messageType": "assistant",
                "citations": final_citations,
                "createdAt": datetime.utcnow()
            }

            success_user = await self.model.add_message(session_id, user_message)
            success_assistant = await self.model.add_message(session_id, assistant_message)

            if not success_user or not success_assistant:
                yield {"error": "Failed to save messages"}
                return

            yield {
                "token": "",
                "citations": final_citations,
                "messageId": success_assistant
            }

        except Exception as e:
            yield {"error": str(e)}

        
    async def chat_no_stream(self, question, session_id):

        sessions = await self.model.get_session_with_projection(
            filters={"_id": ObjectId(session_id)},
            fields=["messages","LLMHistory"]
        )

        if not sessions:
            yield {
                "success": False,
                "data": None,
                "error": "Session not found"
            }
            return

        session = sessions[0]
        session["Messages"] = session.get("messages", [])[-5:]
        llmHistory = session.get("LLMHistory", [])

        input_messages = {
            "messages": llmHistory
        }

        ai_chat = AIChatNoStream("source-hr-knowledge")

        # generator from helper
        generator = ai_chat.chat_with_tools(input_messages, question)

        full_response = ""
        citations = []

        for chunk in generator:
            # print("Chunk received:", chunk)  # Debugging line
            # If chunk is a dict (final yield from helper)
            if isinstance(chunk, dict):
                citations = chunk.get("citations", [])
                input_messages = chunk.get("history", input_messages)
                continue

            # Else it's a text delta
            full_response += chunk
            
            yield {"delta": chunk}  # 🔥 streaming to frontend

        # after streaming is done, save to DB
        updated_doc = await self.model.collection.find_one_and_update(
            {"_id": ObjectId(session_id)},
            {"$set": {"LLMHistory": input_messages.get("messages", [])}},
            return_document=ReturnDocument.AFTER,
            upsert=True
        )

        if not full_response:
            yield {
                "success": False,
                "data": None,
                "error": "Unable to generate response"
            }
            return

        user_message = {
            "message": question,
            "messageType": "user",
            "citations": [],
            "createdAt": datetime.utcnow()
        }

        assistant_message = {
            "message": full_response,
            "messageType": "assistant",
            "citations": citations,
            "createdAt": datetime.utcnow()
        }

        success_user_message = await self.model.add_message(session_id, user_message)
        success_assistant_message = await self.model.add_message(session_id, assistant_message)

        if not success_user_message or not success_assistant_message:
            yield {
                "success": False,
                "data": None,
                "error": "Failed to save chat messages"
            }
            return

        yield {
            "success": True,
            "data": {
                "response": full_response,
                "citations": citations,
                "_id": success_assistant_message
            }
        }

        
    async def create_session(self, user_id: str, dashboard_id: str) -> dict:
        try:
            user = await self.user_model.get_user({"_id": ObjectId(user_id)})

            session_data = {
                "userId": user_id,
                "dashboardId": dashboard_id,
                "messages": [],
                "name": user.fullName
            }

            # This returns the ObjectId
            inserted_id = await self.model.create_session(session_data)
            session_id = str(inserted_id)

            # Update last_session_id in the dashboard
            await self.dashboard_model.update_dashboard(dashboard_id,{"lastSessionId":session_id})

            return {"data": {"_id": session_id}, "success": True}  # 👈 wrap in a dict for consistency

        except Exception as e:
            return {"data": None, "success": False, "error": str(e)}


            
    async def get_all_sessions(self, dashboard_id, page, limit=10):
        
        # if role == 'admin':
        #     filter = {"knowledgeId": knowledge_id}
        # else:
        filter = {"dashboardId": dashboard_id}
        total_docs = await self.model.get_sessions_count(filter)
        limit = limit
        total_pages = (total_docs + limit - 1) // limit
        number_to_skip = (page - 1) * limit
        # docs = await self.model.get_sessions(filter, number_to_skip, limit)
        
        cursor = self.model.collection.find(filter,{"sessionTitle": 1, "userId":1, "name":1, "dashboardId":1, "createdOn": 1}).skip(number_to_skip).limit(limit).sort("createdOn",-1)
        docs = await cursor.to_list(length=limit)
         
        return {
                "success": True,
                "data": {
                    "docs": docs,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                    }
                }
            }

    async def get_session(self, dashboard_id: str, session_id: str):
        try:
            document = await self.model.get_session({"_id": ObjectId(session_id)})
            return {"data": document, "success": True}
        except Exception as e:
            return {"data": None, "success": False, "error": str(e)}


    async def delete_session(self, session_id: str) -> dict:
        success = await self.model.delete_session(session_id)
        if not success:
            return {"data": None, "success": False, "error": "Failed to delete session"}
        return {"data": "Session deleted", "success": True}

            
        
    async def get_file_by_file_name(self, knowledge_id, file_name):
        try:

            resp = await self.document_model.get_document({"knowledgeId":knowledge_id, "name":file_name })
                
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
            
    async def regenerate_response_stream(self, session_id: str, ai_message_id: str):
        session = await self.model.get_session({"_id": ObjectId(session_id)})
        if not session:
            yield {"error": "Session not found"}
            return

        user_message = None
        messages = session.get("messages", [])
        ai_index = None
        for idx, msg in enumerate(messages):
            if str(msg.get("_id")) == str(ai_message_id) and msg.get("messageType") == "assistant":
                ai_index = idx
                break
        if ai_index is not None and ai_index > 0:
            prev_msg = messages[ai_index - 1]
            if prev_msg.get("messageType") == "user":
                user_message = prev_msg
        if not user_message:
            yield {"error": "Previous user message not found"}
            return

        question = user_message["message"]
        session_context = session.copy()
        session_context["messages"] = messages[-5:]

        ai_chat = AIChat("source-hr-knowledge")
        full_response = ""
        citations = []

        try:
            async for token in ai_chat.chat_with_knowledge_stream_openai_tools(question, session_context):
                if token is None:
                    yield {"error": "Unable to generate response"}
                    return

                content = token.get("content", "")
                citations = token.get("citations", [])
                full_response += content

                yield {
                    "message": content,
                    "citations": []
                }
            await self.model.update_message_with_message_id(session_id, ai_message_id, full_response, citations)

            # Yield the messageId at the end
            yield {
                "message": "",
                "citations":citations,
                "messageId": ai_message_id
            }

        except Exception as e:
            yield {"error": str(e)}
            