from dataclasses import asdict
from datetime import datetime
from typing import Dict, List

from bson import ObjectId

from app.helpers.AIImageGeneration import NewsImageGenerator
from app.models.Dashboard import DashboardModel
from app.models.News import NewsModel
from app.schemas.Dashboard import NewsList
from app.schemas.News import News as NewsDocument

from .research_agent import NewsResearchAgent
from .writer_agent import NewsWriterAgent


class NewsGenerationCoordinator:
    """Coordinates researcher and writer agents and persists results."""

    def __init__(self) -> None:
        self.dashboard_model = DashboardModel()
        self.news_model = NewsModel(collection_name="AIGenNews")
        self.research_agent = NewsResearchAgent()
        self.writer_agent = NewsWriterAgent()
        self.image_generator = NewsImageGenerator()

    def generate_for_dashboard(self, dashboard_id: str, max_items: int = 5) -> Dict:
        try:
            dashboard_object_id = ObjectId(dashboard_id)
        except Exception:
            return {"success": False, "error": "Invalid dashboard id", "data": None}

        dashboard = self.dashboard_model.get_dashboard({"_id": dashboard_object_id})
        if not dashboard:
            return {"success": False, "error": "Dashboard not found", "data": None}

        context = self._build_dashboard_context(dashboard)
        research = self.research_agent.gather(dashboard_id=dashboard_id, per_source_limit=max_items)
        research_dict = {
            source: [asdict(snippet) for snippet in snippets]
            for source, snippets in research.items()
        }

        news_list = self.writer_agent.compose_news(context, research_dict, max_items=max_items)
        self._persist_news(dashboard_id, news_list)

        return {"success": True, "data": news_list}

    def generate_for_all_dashboards(self, max_items: int = 5, limit: int = 1) -> Dict[str, Dict]:
        dashboards = self.dashboard_model.list_dashboards({}, 0, limit)
        results: Dict[str, Dict] = {}
        for dashboard in dashboards:
            dashboard_id = str(dashboard.get("_id")) if isinstance(dashboard, dict) else str(getattr(dashboard, "id", ""))
            if not dashboard_id:
                continue
            results[dashboard_id] = self.generate_for_dashboard(dashboard_id, max_items=max_items)
        return results

    def _persist_news(self, dashboard_id: str, news_list: NewsList) -> None:
        existing_docs = self.news_model.get_news(dashboard_id)
        if existing_docs:
            news_doc = existing_docs[0]
            existing_keys = {
                (getattr(item, "title", None), getattr(item, "sourceUrl", None))
                for item in getattr(news_doc, "news", []) or []
            }
            new_items = []
            for item in news_list.news:
                key = (item.title, item.sourceUrl)
                if key not in existing_keys:
                    new_items.append(item)

            formatted_items = []
            for news_item in new_items:
                payload = news_item.model_dump()
                payload["_id"] = ObjectId()
                payload["imageUrl"] = self.image_generator.process_article(
                    news_item.description,
                    str(payload["_id"]),
                )
                formatted_items.append(NewsDocument(**payload))

            news_doc.news.extend(formatted_items)
            news_doc.updatedAt = datetime.utcnow()
            self.news_model.update_news(dashboard_id, news_doc.model_dump(by_alias=True))
        else:
            news_payload = {
                "dashboardId": dashboard_id,
                "news": [],
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow(),
            }
            for news_item in news_list.news:
                payload = news_item.model_dump()
                payload["_id"] = ObjectId()
                payload["imageUrl"] = self.image_generator.process_article(
                    news_item.description,
                    str(payload["_id"]),
                )
                news_payload["news"].append(payload)
            self.news_model.create(news_payload)

    @staticmethod
    def _build_dashboard_context(dashboard) -> Dict[str, List[str]]:
        context: Dict[str, List[str]] = {"locations": [], "industries": [], "topics": []}
        for region in getattr(dashboard, "locations", []) or []:
            for loc in getattr(region, "locations", []) or []:
                slug = getattr(loc, "slug", "")
                if slug:
                    context["locations"].append(slug.replace("-", " ").title())

        for industry in getattr(dashboard, "industries", []) or []:
            slug = getattr(industry, "primary_industry_slug", "")
            if slug:
                context["industries"].append(slug.replace("-", " ").title())

        for category in getattr(dashboard, "topics", []) or []:
            for topic in getattr(category, "topics", []) or []:
                slug = getattr(topic, "slug", "")
                if slug:
                    context["topics"].append(slug.replace("-", " ").title())

        return context


