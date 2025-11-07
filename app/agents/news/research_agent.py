import itertools
from dataclasses import dataclass
from typing import Dict, List, Optional

from bson import ObjectId
from app.helpers.SERP import SERPHelper
from app.helpers.VectorDB import VectorDB
from app.models.Dashboard import DashboardModel


@dataclass
class ResearchSnippet:
    source: str
    title: str
    summary: str
    url: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None


class NewsResearchAgent:
    """Collects news context for a dashboard from SERP and vector sources."""

    def __init__(
        self,
        serp_helper: Optional[SERPHelper] = None,
        vector_store: Optional[VectorDB] = None,
        namespace: str = "source-hr-knowledge",
    ) -> None:
        self.serp_helper = serp_helper or SERPHelper()
        self.vector_store = vector_store or VectorDB(namespace)
        self.dashboard_model = DashboardModel()

    def gather(self, dashboard_id: str, per_source_limit: int = 5) -> Dict[str, List[ResearchSnippet]]:
        try:
            dashboard_object_id = ObjectId(dashboard_id)
        except Exception:
            return {"google_serp": [], "vector_store": []}

        dashboard = self.dashboard_model.get_dashboard({"_id": dashboard_object_id})
        if not dashboard:
            return {"google_serp": [], "vector_store": []}

        location_names, industry_names, topic_names = self._extract_dashboard_context(dashboard)
        location_slugs, industry_slugs, topic_slugs = self._extract_dashboard_slugs(dashboard)

        google_snippets = self._collect_google_snippets(
            location_names, industry_names, topic_names, per_source_limit
        )
        vector_snippets = self._collect_vector_snippets(
            location_slugs, industry_slugs, topic_slugs, topic_names, per_source_limit
        )

        print(
            f"[NewsResearchAgent] Google SERP snippets for dashboard {dashboard_id}: "
            f"{[snippet.title for snippet in google_snippets]}"
        )
        print(
            f"[NewsResearchAgent] Vector store snippets for dashboard {dashboard_id}: "
            f"{[snippet.title for snippet in vector_snippets]}"
        )

        return {
            "google_serp": google_snippets,
            "vector_store": vector_snippets,
        }

    def _collect_google_snippets(
        self,
        location_names: List[str],
        industry_names: List[str],
        topic_names: List[str],
        limit: int,
    ) -> List[ResearchSnippet]:
        keyword_chunks = self._compose_keyword_batches(location_names, industry_names, topic_names)
        results: List[ResearchSnippet] = []
        for keywords in keyword_chunks:
            query = f"{' '.join(keywords)} employment law news".strip()
            try:
                serp_items = self.serp_helper.serp_results(query)
            except Exception as exc:  # pragma: no cover - network failure path
                print(f"SERP lookup failed for query '{query}': {exc}")
                serp_items = []

            for item in serp_items:
                if len(results) >= limit:
                    break
                title = item.get("title") or item.get("name") or ""
                if not title:
                    continue
                summary = item.get("description") or item.get("snippet") or ""
                url = item.get("link") or item.get("url")
                snippet = ResearchSnippet(
                    source="google_serp",
                    title=title,
                    summary=summary,
                    url=url,
                    metadata={"query": query},
                )
                results.append(snippet)
            if len(results) >= limit:
                break
        return results

    def _collect_vector_snippets(
        self,
        location_slugs: List[str],
        industry_slugs: List[str],
        topic_slugs: List[str],
        topic_names: List[str],
        limit: int,
    ) -> List[ResearchSnippet]:
        filters: Dict[str, str] = {}
        if location_slugs:
            filters["location_slug"] = location_slugs[0]
        if industry_slugs:
            filters["primary_industry_slug"] = industry_slugs[0]
        if topic_slugs:
            filters["topic_slug"] = topic_slugs[0]

        query_terms = [topic_names[0]] if topic_names else []
        query_terms.extend(location_slugs[:1])
        query_terms.extend(industry_slugs[:1])
        query = " ".join(query_terms) or "employment law update"

        docs = self.vector_store.retrieve_by_metadata(query=query, metadata_filter=filters, k=limit)
        snippets: List[ResearchSnippet] = []
        for doc in docs:
            metadata = {key: str(value) for key, value in (doc.metadata or {}).items()}
            snippets.append(
                ResearchSnippet(
                    source="vector_store",
                    title=metadata.get("title", "Employment law update"),
                    summary=doc.page_content,
                    url=metadata.get("pageUrl") or metadata.get("file_url"),
                    metadata=metadata,
                )
            )
        return snippets[:limit]

    @staticmethod
    def _compose_keyword_batches(
        location_names: List[str],
        industry_names: List[str],
        topic_names: List[str],
        batch_size: int = 3,
    ) -> List[List[str]]:
        groups = [location_names[:batch_size], industry_names[:batch_size], topic_names[:batch_size]]
        flattened = [name for group in groups for name in group if name]
        if not flattened:
            return [["employment law"]]

        batches: List[List[str]] = []
        for size in range(1, min(batch_size, len(flattened)) + 1):
            for combo in itertools.combinations(flattened, size):
                batches.append(list(combo))
        return batches or [["employment law"]]

    @staticmethod
    def _extract_dashboard_context(dashboard) -> tuple[List[str], List[str], List[str]]:
        location_names: List[str] = []
        for region in getattr(dashboard, "locations", []) or []:
            for loc in getattr(region, "locations", []) or []:
                slug = getattr(loc, "slug", "")
                if slug:
                    location_names.append(slug.replace("-", " ").title())

        industry_names: List[str] = []
        for industry in getattr(dashboard, "industries", []) or []:
            slug = getattr(industry, "primary_industry_slug", "")
            if slug:
                industry_names.append(slug.replace("-", " ").title())

        topic_names: List[str] = []
        for category in getattr(dashboard, "topics", []) or []:
            for topic in getattr(category, "topics", []) or []:
                slug = getattr(topic, "slug", "")
                if slug:
                    topic_names.append(slug.replace("-", " ").title())

        return location_names, industry_names, topic_names

    @staticmethod
    def _extract_dashboard_slugs(dashboard) -> tuple[List[str], List[str], List[str]]:
        location_slugs: List[str] = []
        for region in getattr(dashboard, "locations", []) or []:
            for loc in getattr(region, "locations", []) or []:
                slug = getattr(loc, "slug", None)
                if slug:
                    location_slugs.append(slug)

        industry_slugs: List[str] = []
        for industry in getattr(dashboard, "industries", []) or []:
            primary_slug = getattr(industry, "primary_industry_slug", None)
            if primary_slug:
                industry_slugs.append(primary_slug)

        topic_slugs: List[str] = []
        for category in getattr(dashboard, "topics", []) or []:
            for topic in getattr(category, "topics", []) or []:
                slug = getattr(topic, "slug", None)
                if slug:
                    topic_slugs.append(slug)

        return location_slugs, industry_slugs, topic_slugs


