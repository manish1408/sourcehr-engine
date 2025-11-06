from datetime import datetime, timedelta
import re
import unicodedata

from bson import ObjectId
from app.models.Dashboard import DashboardModel
from app.schemas.Dashboard import DashboardCreate, DashboardUpdate
from app.helpers.VectorDB import VectorDB
from app.models.Industries import IndustriesModel
from app.models.Topics import TopicsModel
from app.helpers.AIChat import AIChat
from app.models.Locations import LocationsModel
from app.models.DashboardCompliance import DashboardComplianceModel
from app.models.News import NewsModel
from app.helpers.AIImageGeneration import NewsImageGenerator
from app.models.LegalCalender import LegalCalenderModel
from app.models.CourtDecisions import CourtDecisionsModel
from app.helpers.Calendar import Calendar
from app.helpers.CourtDecisions import CourtDecisions
from app.helpers.DashboardCompliance import DashboardCompliance
from app.helpers.News import News
class DashboardService:
    def __init__(self):
        self.model = DashboardModel()
        self.vector_store = VectorDB("source-hr-knowledge")
        self.industries_model = IndustriesModel()
        self.topics_model = TopicsModel()
        self.locations_model=LocationsModel()
        self.news_model=NewsModel()
        self.dashboard_compliance_model=DashboardComplianceModel()
        self.news_image_generation=NewsImageGenerator(temp_dir="temp_images")
        self.legal_calender_model=LegalCalenderModel()
        self.court_decisions_model=CourtDecisionsModel()
        self.dashboard_compliance_helper=DashboardCompliance()
        self.calendar_helper=Calendar()
        self.court_decisions_helper=CourtDecisions()
        self.news_helper=News()
    def create_dashboard(self, user_id: str, body: DashboardCreate):
        try:
            existing_dashboard = self.model.get_dashboard({"name":body.name,"userId":user_id})
            if existing_dashboard:
                return {  
                    "success": False,
                    "data": None,
                    "error": "A dashboard with this name already exists. Please choose a different name."
                    }
            data = body.model_dump(exclude_none=True)
            data.update({
            "userId": user_id,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            })

            data=self.model.create_dashboard(data=data)
            return {
                        "success": True,
                        "data": {"_id": data}
                    }
        except Exception as e:
            return {
                    "success": False,
                    "data": None,
                    "error":e
                }
            
    def list_dashboards(self, user_id: str, page: int = 1, limit: int = 10):
        try:
            limit=limit
            total = self.model.collection.count_documents({"userId": user_id})
            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            data = self.model.list_dashboards({"userId": user_id}, number_to_skip, limit)
            return {
                "success": True,
                "data": {
                    "dashboards": data,
                     "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                    "success": False,
                    "data": None,
                    "error": e
                }

            
                    
        
    def get_dashboard(self, dashboard_id: str):
        try:
            
            data= self.model.get_dashboard({"_id":ObjectId(dashboard_id)})
            return {
                "success": True,
                "data": data
            }
        except Exception as e:
            return {
                    "success": False,
                    "data": None,
                    "error":e
                }

    def update_dashboard(self, dashboard_id: str, body: DashboardUpdate):
        try:
            data= self.model.update_dashboard(dashboard_id, body.model_dump(exclude_unset=True,exclude_none=True))
            return {
            "success": True,
            "data": data
            }
        except Exception as e:
            return {
                    "success": False,
                    "data": None,
                    "error":e
                }
        

    def delete_dashboard(self, dashboard_id: str):
        try:
            data= self.model.delete_dashboard(dashboard_id)
            return {
            "success": True,
            "data": data
            }
        except Exception as e:
            return {
                    "success": False,
                    "data": None,
                    "error":e
                }
        

    def duplicate_dashboard(self, dashboard_id: str, user_id: str):
        try:
            dashboard = self.model.get_dashboard({"_id": ObjectId(dashboard_id)})
            dashboard_data=dashboard.model_dump()
            dashboard_data['name'] = dashboard_data['name'] + " (duplicate)"
            dashboard_data.pop("id", None)
            dashboard_data.pop("lastSessionId",None)
            dashboard_data["userId"] = user_id
            dashboard_data["createdAt"] = dashboard_data["updatedAt"] = datetime.utcnow()
            data=self.model.create_dashboard(dashboard_data)
            new_dashboard_id = str(data)  # or data["_id"] depending on your return

            # 2. Duplicate compliance data
            compliance_data = self.dashboard_compliance_model.get_law_changes(dashboard_id)
            if compliance_data:
                for compliance in compliance_data:
                    compliance_dict = compliance.model_dump() if hasattr(compliance, "model_dump") else dict(compliance)
                    compliance_dict.pop("id", None)
                    compliance_dict["dashboardId"] = new_dashboard_id
                    compliance_dict["createdAt"] = compliance_dict["updatedAt"] = datetime.utcnow()
                    self.dashboard_compliance_model.create(compliance_dict)

            # 3. Duplicate news data
            news_data = self.news_model.get_news(dashboard_id)
            if news_data:
                for news_doc in news_data:
                    news_dict = news_doc.model_dump() if hasattr(news_doc, "model_dump") else dict(news_doc)
                    news_dict.pop("id", None)
                    news_dict["dashboardId"] = new_dashboard_id
                    news_dict["createdAt"] = news_dict["updatedAt"] = datetime.utcnow()
                    self.news_model.create(news_dict)
            # 4. Duplicate legal calendar data
            legal_calendar_data = self.legal_calender_model.get_legal_calender(dashboard_id)
            if legal_calendar_data:
                for legal_calendar in legal_calendar_data:
                    legal_calendar_dict = legal_calendar.model_dump() if hasattr(legal_calendar, "model_dump") else dict(legal_calendar)
                    legal_calendar_dict.pop("id", None)
                    legal_calendar_dict["dashboardId"] = new_dashboard_id
                    legal_calendar_dict["createdAt"] = legal_calendar_dict["updatedAt"] = datetime.utcnow()
                    self.legal_calender_model.create(legal_calendar_dict)
            return{
                "success":True,
                "data":new_dashboard_id
            }

        except Exception as e:
            return {
                    "success": False,
                    "data": None,
                    "error":e
                }
            
            
    def get_locations(self):
        try:
            locations = self.locations_model.get_locations()
            return {
                "success": True,
                "data": locations
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    def get_industries(self):
        try:
            industries = self.industries_model.get_industries()
            return {
                "success": True,
                "data": industries
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    def get_topics(self):
        try:
            topics = self.topics_model.get_topics()
            return {
                "success": True,
                "data": topics
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
            
    def retrieve_law_changes(self, dashboard_id: str):
        try:
            law_changes = self.dashboard_compliance_helper.retrieve_law_changes(dashboard_id)
            return {
                "success": True,
                "data": law_changes
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

        
            

    def create_legal_calender(self, dashboard_id:str):
        try:
            legal_calendar = self.calendar_helper.retrieve_calendar(dashboard_id)
            return {
                "success": True,
                "data": legal_calendar
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def generate_news(self,dashboard_id:str):
        try:
            news = self.news_helper.retrieve_news(dashboard_id)
            return {
                "success": True,
                "data": news
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
        
         

    def generate_court_decisions(self, dashboard_id: str):
        try:
            court_decisions = self.court_decisions_helper.retrieve_court_decisions(dashboard_id)
            return {
                "success": True,
                "data": court_decisions
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

    def fetch_court_decisions(self, dashboard_id: str) -> dict:
        try:
            opinions = self.court_decisions_model.get_court_decisions(dashboard_id)
            return {"success": True, "data": opinions}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
            
    
    def get_law_changes(self, dashboard_id: str) -> dict:
        """
        Fetch all law changes for a specific dashboardId.
        """
        try:
            law_changes = self.dashboard_compliance_model.get_law_changes(dashboard_id)
            return {
                "success": True,
                "data": law_changes
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
        
    def fetch_news(self, dashboard_id: str) -> dict:
        """
        Fetch all news law  for a specific dashboardId.
        """
        try:
            news = self.news_model.get_news(dashboard_id)
            return {
                "success": True,
                "data": news
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    def get_legal_calender(self, dashboard_id: str) -> dict:
        """
        Fetch all legal calendar events for a specific dashboardId.
        """
        try:
            legal_calender = self.legal_calender_model.get_legal_calender(dashboard_id)
            return {
                "success": True,
                "data": legal_calender
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    