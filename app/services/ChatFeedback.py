from app.models.ChatFeedback import ChatFeedbackModel
from app.models.ChatSession import ChatSessionModel
from app.schemas.ChatFeedback import ChatFeedbackSchema
from datetime import datetime


class ChatFeedbackService:
    def __init__(self):
        self.model=ChatFeedbackModel()
        self.chat_model=ChatSessionModel()
        
    async def create_chat_feedback(self, data, user_id, user_name):
        try:    
            data['UserId'] = user_id
            data['UserName'] = user_name
            data_resp = await self.model.create_chat_feedback(data)
            update = await self.chat_model.update_message_sentiment_with_message_id(data['ChatSessionId'],data['ChatMessageId'], data['Sentiment'])
            
            return {
                    "success": True,
                    "data": data_resp
                }
        except Exception as e:
            return{    
                "success": False,
                "data": None,
                "error":str(e)
            }
            
    async def get_chat_feedback_by_id(self, chat_feedback_id):
        try:
            data = await self.model.get_chat_feedback_by_id(chat_feedback_id)
            return {
                        "success": True,
                        "data": data
                    }
        except Exception as e:
            return{    
                "success": False,
                "data": None,
                "error":str(e)
            }
            
    async def get_all_chat_feedbacks(self, page, limit=10):
        total_docs = await self.model.get_documents_count({})
        limit = limit
        total_pages = (total_docs + limit - 1) // limit
        number_to_skip = (page - 1) * limit
        docs = await self.model.get_all_chat_feedbacks({}, number_to_skip, limit)
        
        if not docs:
                return {
                    "success": False,
                    "data": None,
                    "error": "No documents found"
                }

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
            
    async def update_chat_feedback(self, chat_feedback_id, sentiment, feedback):
        try:        
            data = {
            "Sentiment": sentiment,
            "Feedback": feedback,
            "UpdatedOn":datetime.utcnow()
            }
            data = await self.model.update_chat_feedback(chat_feedback_id, data)
            return {
                        "success": True,
                        "data": data
                    }
        except Exception as e:
            return{    
                "success": False,
                "data": None,
                "error":str(e)
            }
            
    async def delete_chat_feedback(self, chat_feedback_id):
        try:
            data = await self.model.delete_chat_feedback(chat_feedback_id)
            return {
                    "success": True,
                    "data": data
                }
        except Exception as e:
            return{    
                "success": False,
                "data": None,
                "error":str(e)
            }
            
        
        
            
            
            
            
        
        
