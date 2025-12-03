import os
from datetime import date
from typing import List, Optional

from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI

from app.helpers.AzureStorage import AzureBlobUploader
from app.helpers.SERP import SERPHelper
from app.models.GeneralNews import GeneralNewsModel
from app.schemas.GeneralNews import GeneralNewsDocument, GeneralNewsItem, GeneralNewsSummary


class GeneralNewsHelper:
    def __init__(self) -> None:
        self.model = GeneralNewsModel()
        self.serp_helper = SERPHelper()
        self.azure_blob = AzureBlobUploader()
        self.chat = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("gpt-4o-mini"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
        )

    def _fetch_logo_for_organization(self, organization_name: Optional[str]) -> Optional[str]:
        """Fetch logo URL for an organization using SERP API and upload to blob storage."""
        if not organization_name:
            return None
        
        try:
            query = f"{organization_name} logo"
            api_response = self.serp_helper.serp_image_results(query)
            original_logo_url = SERPHelper.extract_final_image_url(api_response)
            
            if not original_logo_url:
                return None
            
            # Upload image to Azure Blob Storage
            blob_url = self.azure_blob.copy_and_upload_to_azure_blob(
                image_url=original_logo_url,
                container_name=os.getenv("AZURE_STORAGE_CONTAINER", "temp"),
                folder_name="organization-logos",
                file_type=".png"
            )
            
            if blob_url:
                print(f"[GeneralNewsHelper] Uploaded logo for {organization_name} to blob storage")
                return blob_url
            else:
                print(f"[GeneralNewsHelper] Failed to upload logo for {organization_name} to blob storage")
                return None
        except Exception as exc:
            print(f"[GeneralNewsHelper] Failed to fetch/upload logo for {organization_name}: {exc}")
            return None

    def generate_daily_summary(self, summary_date: date | None = None) -> dict:
        target_date = summary_date or date.today()

        serp_results = self._fetch_serp_results()
        content_snippets = self._format_serp_context(serp_results)

        summary = self._generate_summary_from_context(content_snippets, target_date)
        summary.summaryDate = target_date.isoformat()

        # Fetch logos for each article
        articles_with_logos = []
        for article in summary.articles:
            logo_url = None
            if article.organizationName:
                logo_url = self._fetch_logo_for_organization(article.organizationName)
            
            article_with_logo = GeneralNewsItem(
                title=article.title,
                description=article.description,
                organizationName=article.organizationName,
                logoUrl=logo_url,
            )
            articles_with_logos.append(article_with_logo)

        # Delete all previous entries for this date before inserting new ones
        self.model.delete_by_date(target_date.isoformat())

        # Save each article at root level instead of as an array
        saved_articles = []
        for article in articles_with_logos:
            article_doc = self.model.create_article(
                summaryDate=target_date.isoformat(),
                article=article
            )
            saved_articles.append(article_doc)

        return {"success": True, "data": saved_articles}

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
                "employment-law news items relevant to employers in the United States. "
                "For each article, extract the organization name (company, court, agency, etc.) mentioned in the news."
            )
        )
        user_prompt = HumanMessage(
            content=(
                "Using the context below, generate a structured JSON object with these rules:\n"
                "- Produce exactly 15 articles. If the context is insufficient, rely on verified, recent public information to reach 15 items.\n"
                "- Each article must have a concise Title, a Description limited to 1-3 sentences, and an OrganizationName.\n"
                "- Extract the organization name (company, court, agency, etc.) from the content for each article.\n"
                "- If no organization is mentioned, set organizationName to null.\n"
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
                        organizationName=None,
                        logoUrl=None,
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
                    organizationName=item.organizationName.strip() if item.organizationName and isinstance(item.organizationName, str) else None,
                    logoUrl=None,  # Will be populated later
                )
            )
        response.articles = trimmed_articles
        return response
