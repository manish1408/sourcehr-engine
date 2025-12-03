import os
from datetime import date
from typing import List

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from app.helpers.SERP import SERPHelper
from app.models.GeneralNews import GeneralNewsModel
from app.schemas.GeneralNews import GeneralNewsDocument, GeneralNewsItem, GeneralNewsSummary


class GeneralNewsHelper:
    def __init__(self) -> None:
        self.model = GeneralNewsModel()
        self.serp_helper = SERPHelper()
        self.chat = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("gpt-4o-mini"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
        )

    def generate_daily_summary(self, summary_date: date | None = None) -> dict:
        target_date = summary_date or date.today()

        serp_results = self._fetch_serp_results()
        content_snippets = self._format_serp_context(serp_results)

        summary = self._generate_summary_from_context(content_snippets, target_date)
        summary.summaryDate = target_date.isoformat()

        document = GeneralNewsDocument(
            summaryDate=summary.summaryDate,
            articles=[GeneralNewsItem(**item.model_dump()) for item in summary.articles],
        )
        self.model.replace_summary(document)
        return {"success": True, "data": document}

    def _fetch_serp_results(self) -> List[dict]:
        query = 'latest US employment law news OR "court ruling" OR "workplace discrimination" OR "hiring bias" OR "wrongful termination" OR "labor law update" OR "EEOC lawsuit" OR "company sued" OR "employee rights case" site:news.google.com'
        try:
            results = self.serp_helper.serp_results(query)[:20]
           
            if not results:
                print("[GeneralNewsHelper] No SERP results returned for query")
            return results[:20]
        except Exception as exc:  # pylint: disable=broad-except
            print(f"[GeneralNewsHelper] SERP fetch failed: {exc}")
            return []

    @staticmethod
    def _format_serp_context(results: List[dict]) -> str:
        if not results:
            return ""
        formatted = []
        for idx, result in enumerate(results, start=1):
            title = result.get("title") or result.get("name") or ""
            snippet = result.get("description") or result.get("snippet") or ""
            link = result.get("link") or result.get("url") or ""
            formatted.append(f"Result {idx}:\nTitle: {title}\nSummary: {snippet}\nURL: {link}")
        return "\n\n".join(formatted)

    def _generate_summary_from_context(self, context: str, target_date: date) -> GeneralNewsSummary:
        system_prompt = SystemMessage(
            content=(
                "You are a legal news editor. Based on the provided context, produce up to five distinct "
                "employment-law news items relevant to employers in the United States."
            )
        )
        user_prompt = HumanMessage(
            content=(
                "Using the context below, generate a structured JSON object with these rules:\n"
                "- Produce exactly 15 articles. If the context is insufficient, rely on verified, recent public information to reach 15 items.\n"
                "- Each article must have a concise Title and a Description limited to 1-3 sentences.\n"
                "- Avoid duplication; each article should focus on a unique development.\n"
                f"Date: {target_date.isoformat()}\n"
                "Context:\n"
                f"{context if context else 'No SERP results were retrieved; rely on verified high-level knowledge of recent US employment law developments.'}"
            )
        )

        structured_llm = self.chat.with_structured_output(GeneralNewsSummary)
        response = structured_llm.invoke([system_prompt, user_prompt])
        # Ensure descriptions are within the requested length and limit to 15 articles
        trimmed_articles = []
        articles = response.articles
        if len(articles) < 15:
            missing = 15 - len(articles)
            for _ in range(missing):
                articles.append(
                    GeneralNewsItem(
                        title="General Employment Law Update",
                        description="Summary not provided. Please research recent employment law developments in the United States.",
                    )
                )
        for item in articles[:15]:
            sentences = item.description.split(".")
            trimmed_description = ".".join([s.strip() for s in sentences if s.strip()][:3])
            if trimmed_description and not trimmed_description.endswith("."):
                trimmed_description += "."
            trimmed_articles.append(
                GeneralNewsItem(
                    title=item.title.strip(),
                    description=trimmed_description.strip(),
                )
            )
        response.articles = trimmed_articles
        return response
