from datetime import datetime
import os

from bson import ObjectId
from app.helpers.AIChat import AIChat
from app.models.ChatSession import ChatSessionModel
from app.services.Dashboard import DashboardModel


class ProactiveMessageService:
    
    def __init__(self):
        self.ai_chat=AIChat("source-hr-knowledge")
        self.chat_session_model=ChatSessionModel()
        self.dashboard_model=DashboardModel()
        
        
    def generateProactiveFollowUpMessage(self, session_id, dashboard_id):
        try:
            conversationHistory = self.chat_session_model.get_session({'_id': ObjectId(session_id)})
            dashboard = self.dashboard_model.get_dashboard({'_id': ObjectId(dashboard_id)})
            locations = getattr(dashboard, "locations", [])
            industries = getattr(dashboard, "industries", [])
            topics = getattr(dashboard, "topics", [])

            location_slugs = []
            for region in locations:
                for loc in getattr(region, "locations", []):
                    slug = getattr(loc, "slug", None)
                    if slug:
                        location_slugs.append(slug)

            industry_slugs = []
            for industry in industries:
                primary_slug = getattr(industry, "primary_industry_slug", None)
                if primary_slug:
                    industry_slugs.append(primary_slug)
                for secondary in getattr(industry, "secondary_industry", []):
                    secondary_slug = getattr(secondary, "slug", None)
                    if secondary_slug:
                        industry_slugs.append(secondary_slug)

            # Flatten all topic slugs
            topic_slugs = []
            for category in topics:
                for topic in getattr(category, "topics", []):
                    slug = getattr(topic, "slug", None)
                    if slug:
                        topic_slugs.append(slug)
            # Only use the last 15 messages and only 'message' and 'messageType' fields
            
            dashboard_info={
                "locations":location_slugs,
                "industries":industry_slugs,
                "topics":topic_slugs
            }
            messages = conversationHistory.get("messages", [])
            last_15_messages = messages[-15:]
            filtered_messages = [
                {"message": m.get("message", ""), "messageType": m.get("messageType", "")}
                for m in last_15_messages
            ]
            conversationHistory["messages"] = filtered_messages

            proactiveMessages = self.ai_chat.generateProactiveMessages(conversationHistory, dashboard_info).proactiveMessages
            return {
                "success": True,
                "data": proactiveMessages
            }
        
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "error": str(e)
            }