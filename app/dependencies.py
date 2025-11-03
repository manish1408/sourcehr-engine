"""
Singleton dependencies for resource management.
Prevents creating multiple heavy resources on every API request.
"""
from functools import lru_cache
from typing import Optional, TYPE_CHECKING
from app.helpers.VectorDB import VectorDB
from app.helpers.SERP import SERPHelper
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI
import os

# Avoid circular imports
if TYPE_CHECKING:
    from app.services.Dashboard import DashboardService

# Global singletons - Core Resources
_vector_db_instances = {}
_serp_helper: Optional[SERPHelper] = None
_azure_openai_client: Optional[AzureOpenAI] = None
_langchain_chat_client: Optional[AzureChatOpenAI] = None

# Global singletons - Helpers
_dashboard_compliance_helper = None
_calendar_helper = None
_news_helper = None
_court_decisions_helper = None

# Global singletons - Services
_auth_service = None
_chat_service = None
_chat_feedback_service = None
_common_service = None
_dashboard_service: Optional['DashboardService'] = None
_dashboard_documents_service = None
_document_service = None
_evaluation_service = None
_proactive_message_service = None
_profile_service = None
_quiz_attempt_service = None
_quiz_service = None
_website_crawl_service = None


def get_vector_db(namespace: str) -> VectorDB:
    """
    Get or create a VectorDB instance for the given namespace.
    Reuses existing instances to avoid creating multiple connections.
    """
    global _vector_db_instances
    if namespace not in _vector_db_instances:
        _vector_db_instances[namespace] = VectorDB(namespace)
    return _vector_db_instances[namespace]


def get_serp_helper() -> SERPHelper:
    """
    Get the singleton SERPHelper instance.
    """
    global _serp_helper
    if _serp_helper is None:
        _serp_helper = SERPHelper()
    return _serp_helper


def get_azure_openai_client() -> AzureOpenAI:
    """
    Get the singleton Azure OpenAI client for function calling.
    """
    global _azure_openai_client
    if _azure_openai_client is None:
        _azure_openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-12-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
    return _azure_openai_client


def get_langchain_chat_client() -> AzureChatOpenAI:
    """
    Get the singleton LangChain Azure Chat client for structured output.
    """
    global _langchain_chat_client
    if _langchain_chat_client is None:
        _langchain_chat_client = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_deployment=os.getenv('gpt-4o-mini'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
        )
    return _langchain_chat_client


def get_dashboard_compliance_helper():
    """Get singleton DashboardCompliance helper"""
    global _dashboard_compliance_helper
    if _dashboard_compliance_helper is None:
        from app.helpers.DashboardCompliance import DashboardCompliance
        _dashboard_compliance_helper = DashboardCompliance()
    return _dashboard_compliance_helper


def get_calendar_helper():
    """Get singleton Calendar helper"""
    global _calendar_helper
    if _calendar_helper is None:
        from app.helpers.Calendar import Calendar
        _calendar_helper = Calendar()
    return _calendar_helper


def get_news_helper():
    """Get singleton News helper"""
    global _news_helper
    if _news_helper is None:
        from app.helpers.News import News
        _news_helper = News()
    return _news_helper


def get_court_decisions_helper():
    """Get singleton CourtDecisions helper"""
    global _court_decisions_helper
    if _court_decisions_helper is None:
        from app.helpers.CourtDecisions import CourtDecisions
        _court_decisions_helper = CourtDecisions()
    return _court_decisions_helper


def get_dashboard_service():
    """Get singleton DashboardService instance"""
    global _dashboard_service
    if _dashboard_service is None:
        from app.services.Dashboard import DashboardService
        _dashboard_service = DashboardService()
    return _dashboard_service


def get_auth_service():
    """Get singleton AuthService instance"""
    global _auth_service
    if _auth_service is None:
        from app.services.Auth import AuthService
        _auth_service = AuthService()
    return _auth_service


def get_chat_service():
    """Get singleton ChatService instance"""
    global _chat_service
    if _chat_service is None:
        from app.services.Chat import ChatService
        _chat_service = ChatService()
    return _chat_service


def get_chat_feedback_service():
    """Get singleton ChatFeedbackService instance"""
    global _chat_feedback_service
    if _chat_feedback_service is None:
        from app.services.ChatFeedback import ChatFeedbackService
        _chat_feedback_service = ChatFeedbackService()
    return _chat_feedback_service


def get_common_service():
    """Get singleton CommonService instance"""
    global _common_service
    if _common_service is None:
        from app.services.Common import CommonService
        _common_service = CommonService()
    return _common_service


def get_dashboard_documents_service():
    """Get singleton DashboardDocumentsService instance"""
    global _dashboard_documents_service
    if _dashboard_documents_service is None:
        from app.services.DashboardDocuments import DDService
        _dashboard_documents_service = DDService()
    return _dashboard_documents_service


def get_document_service():
    """Get singleton DocumentService instance"""
    global _document_service
    if _document_service is None:
        from app.services.Documents import DocumentService
        _document_service = DocumentService()
    return _document_service


def get_evaluation_service():
    """Get singleton EvaluationService instance"""
    global _evaluation_service
    if _evaluation_service is None:
        from app.services.Evaluation import EvaluationService
        _evaluation_service = EvaluationService()
    return _evaluation_service


def get_proactive_message_service():
    """Get singleton ProactiveMessageService instance"""
    global _proactive_message_service
    if _proactive_message_service is None:
        from app.services.ProactiveMessage import ProactiveMessageService
        _proactive_message_service = ProactiveMessageService()
    return _proactive_message_service


def get_profile_service():
    """Get singleton ProfileService instance"""
    global _profile_service
    if _profile_service is None:
        from app.services.Profile import ProfileService
        _profile_service = ProfileService()
    return _profile_service


def get_quiz_attempt_service():
    """Get singleton QuizAttemptService instance"""
    global _quiz_attempt_service
    if _quiz_attempt_service is None:
        from app.services.QuizAttempts import QuizAttemptService
        _quiz_attempt_service = QuizAttemptService()
    return _quiz_attempt_service


def get_quiz_service():
    """Get singleton QuizService instance"""
    global _quiz_service
    if _quiz_service is None:
        from app.services.Quizzes import QuizService
        _quiz_service = QuizService()
    return _quiz_service


def get_website_crawl_service():
    """Get singleton WebsiteCrawlService instance"""
    global _website_crawl_service
    if _website_crawl_service is None:
        from app.services.WebsiteCrawl import WebsiteCrawlService
        _website_crawl_service = WebsiteCrawlService()
    return _website_crawl_service


def cleanup_resources():
    """
    Cleanup all singleton resources. Call this on application shutdown.
    """
    global _vector_db_instances, _serp_helper, _azure_openai_client, _langchain_chat_client
    global _dashboard_compliance_helper, _calendar_helper, _news_helper, _court_decisions_helper
    global _auth_service, _chat_service, _chat_feedback_service, _common_service
    global _dashboard_service, _dashboard_documents_service, _document_service, _evaluation_service
    global _proactive_message_service, _profile_service, _quiz_attempt_service, _quiz_service, _website_crawl_service
    
    # Clear vector DB instances
    _vector_db_instances.clear()
    
    # Reset core resources
    _serp_helper = None
    _azure_openai_client = None
    _langchain_chat_client = None
    
    # Reset helpers
    _dashboard_compliance_helper = None
    _calendar_helper = None
    _news_helper = None
    _court_decisions_helper = None
    
    # Reset services
    _auth_service = None
    _chat_service = None
    _chat_feedback_service = None
    _common_service = None
    _dashboard_service = None
    _dashboard_documents_service = None
    _document_service = None
    _evaluation_service = None
    _proactive_message_service = None
    _profile_service = None
    _quiz_attempt_service = None
    _quiz_service = None
    _website_crawl_service = None

