import json
from app.models.Dashboard import DashboardModel
from app.helpers.VectorDB import VectorDB
from app.models.Industries import IndustriesModel
from app.models.Topics import TopicsModel
from app.models.Locations import LocationsModel
from bson import ObjectId
from datetime import datetime, timedelta                        
from openai  import AzureOpenAI
import os
from app.models.News import NewsModel
from app.helpers.AIImageGeneration import NewsImageGenerator
from app.helpers.SERP import SERPHelper
from langchain_openai import AzureChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from app.schemas.Dashboard import NewsList
from app.helpers.UrlScraperHelper import UrlScraperHelper
    
class  News:
    def __init__(self):
        self.model = DashboardModel()
        self.vector_store = VectorDB("source-hr-knowledge")
        self.industries_model = IndustriesModel()
        self.topics_model = TopicsModel()
        self.locations_model=LocationsModel()      
        self.news_model = NewsModel()
        self.news_image_generation = NewsImageGenerator()
        self.serp_helper = SERPHelper()
        self.url_scraper_helper = UrlScraperHelper()
        self.azure_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-12-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.chat = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_deployment=os.getenv('gpt-4o-mini'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
        )
    
    
    # Tool implementations
    def _tool_search_documents(self, query: str, filters: dict = None, top_k: int = 10, region_slugs: list = None):
        try:
            filters = filters or {}
            # Pinecone filter operators where applicable
            pinecone_filter = {}
            for key in [
                "location_slug",
                "primary_industry_slug",
                "secondary_industry_slug",
                "region_slug",
                "topic_slug",
                "sourceType"
            ]:
                value = filters.get(key)
                if value:
                    pinecone_filter[key] = value

            # Add region_slug filter if regions are provided and not already in filters
            if region_slugs and "region_slug" not in pinecone_filter:
                if len(region_slugs) == 1:
                    pinecone_filter["region_slug"] = region_slugs[0]
                elif len(region_slugs) > 1:
                    # Pinecone supports "$in" for multiple values
                    pinecone_filter["region_slug"] = {"$in": region_slugs}

            # time range
            gt = filters.get("discussedTimestamp_gt")
            lt = filters.get("discussedTimestamp_lt")
            if gt or lt:
                pinecone_filter["discussedTimestamp"] = {}
                if gt:
                    pinecone_filter["discussedTimestamp"]["$gt"] = gt
                if lt:
                    pinecone_filter["discussedTimestamp"]["$lt"] = lt

            docs = self.vector_store.retrieve_by_metadata(query=query, metadata_filter=pinecone_filter, k=top_k)
            # Return simplified structure
            return {
                "success": True,
                "matches": [
                    {
                        "text": getattr(d, "page_content", ""),
                        "metadata": getattr(d, "metadata", {})
                    } for d in docs
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_fetch_serp_content(self, query: str, num_results: int = 5):
        try:
            results = self.serp_helper.serp_results(query)
            results = results[: max(num_results, 0)] if isinstance(results, list) else []
            return {"success": True, "results": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_get_webpage_content(self, urls: list = None, url: str = None):
        try:
            targets = urls or ([url] if url else [])
            if not targets:
                return {"success": True, "pages": []}
            pages = self.serp_helper.get_webpages_parallel(targets)
            return {"success": True, "pages": pages}
        except Exception as e:
            return {"success": False, "error": str(e)}
        
    def get_dashboard_choices(self, dashboard_id: str):
        dashboard = self.model.get_dashboard({"_id": ObjectId(dashboard_id)})
        locations = getattr(dashboard, "locations", [])
        industries = getattr(dashboard, "industries", [])
        topics = getattr(dashboard, "topics", [])
        regions = getattr(dashboard, "region", []) or []
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
        topic_slugs = []
        for category in topics:
            for topic in getattr(category, "topics", []):
                slug = getattr(topic, "slug", None)
                if slug:
                    topic_slugs.append(slug)

        location_names = [slug.replace('-', ' ').title() for slug in location_slugs] if location_slugs else []
        industry_names = [slug.replace('-', ' ').title() for slug in industry_slugs] if industry_slugs else []
        topic_names = [slug.replace('-', ' ').title() for slug in topic_slugs] if topic_slugs else []
        region_names = [region.replace('-', ' ').title() if isinstance(region, str) else str(region).replace('-', ' ').title() for region in regions] if regions else []
        dashboard_choices = {
            "location_names": location_names,
            "industry_names": industry_names,
            "topic_names": topic_names,
            "region_names": region_names,
            "regions": regions
        }
        return dashboard_choices
        
    def retrieve_news(self, dashboard_id: str):
        """Main method to extract news items related to dashboard filters."""
        print(f"Processing news for dashboard: {dashboard_id}")
        try:
            dashboard_choices = self.get_dashboard_choices(dashboard_id)
            location_str = ", ".join(dashboard_choices.get("location_names", [])) or "all locations"
            industry_str = ", ".join(dashboard_choices.get("industry_names", [])) or "all industries"
            topic_str = ", ".join(dashboard_choices.get("topic_names", [])) or "all topics"
            region_str = ", ".join(dashboard_choices.get("region_names", [])) if dashboard_choices.get("region_names") else ""

            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_documents",
                        "description": "Search HR news documents with semantic query and metadata filters.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "filters": {"type": "object"},
                                "top_k": {"type": "integer", "default": 10}
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "fetch_serp_content",
                        "description": "Fetch latest HR/legal news from SERP API.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "num_results": {"type": "integer", "default": 5}
                            },
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_webpage_content",
                        "description": "Scrape webpage content from URLs in parallel.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "urls": {"type": "array", "items": {"type": "string"}},
                                "url": {"type": "string"}
                            }
                        }
                    }
                }
            ]

            messages = [
                {
                    "role": "system",
                    "content": f"""You are a legal news analyst. Extract at least 4 unique structured news items about
                        changes in employment law or HR regulations.
                        Focus on the following dashboard context:
                        - Locations: {location_str}
                        - Industries: {industry_str}
                        - Topics: {topic_str}
                        - Regions: {region_str if region_str else "all regions"}
                        Use the available tools if needed. Output must be a JSON object only.
                        
                        IMPORTANT: For each news item, ensure the detailedDescription field contains approximately 50-100 sentences with comprehensive, in-depth information including background context, implications, legal analysis, industry impact, and future considerations."""
                },
                {
                    "role": "user",
                    "content": f"Provide 4 unique structured news items based on the above context. current date: {datetime.utcnow()}"
                }
            ]

            response = self.azure_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
            )
            response_message = response.choices[0].message
            message_content = response_message.content
            while not message_content and response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    if function_name == "search_documents":
                        # Add region filtering if regions exist in dashboard
                        region_slugs = dashboard_choices.get("regions", [])
                        result = self._tool_search_documents(**args, region_slugs=region_slugs)
                    elif function_name == "fetch_serp_content":
                        result = self._tool_fetch_serp_content(**args)
                    elif function_name == "get_webpage_content":
                        result = self._tool_get_webpage_content(**args)
                        
                    messages.append({
                        "role": "assistant",
                        "tool_calls": [tool_call.model_dump()]
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(result)
                    })

                # Get new response after processing tool calls
                response = self.azure_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tools                )
                response_message = response.choices[0].message
                message_content = response_message.content
                
            raw_data = message_content
            news = self.format_news(raw_data)

            # Extract URLs from news items and scrape/save to vector DB
            news_urls = [item.sourceUrl for item in news.news if hasattr(item, 'sourceUrl') and item.sourceUrl]
            if news_urls:
                try:
                    scrape_result = self.url_scraper_helper.scrape_and_save_urls(
                        urls=news_urls,
                        dashboard_id=dashboard_id,
                        source="news"
                    )
                    print(f"[News] Scraped {scrape_result.get('scraped_count', 0)} URLs, skipped {scrape_result.get('skipped_count', 0)} URLs")
                    if scrape_result.get('errors'):
                        print(f"[News] Errors: {scrape_result.get('errors')}")
                except Exception as e:
                    print(f"[News] Error scraping URLs: {e}")

            # 2. Check if news already exists for this dashboard
            existing_news_docs = self.news_model.get_news(dashboard_id)
            if existing_news_docs:
                news_doc = existing_news_docs[0]
                existing_news_list = news_doc.news if hasattr(news_doc, 'news') else []

                # 2a. Deduplicate using (title, sourceUrl)
                existing_keys = {(getattr(n, 'title', None), getattr(n, 'sourceUrl', None)) for n in existing_news_list}
                new_news_items = []
                for item in news.news:
                    if not hasattr(item, 'id') or getattr(item, 'id', None) is None:
                        try:
                            item.id = str(ObjectId())
                        except Exception:
                            pass
                    # Ensure detailedDescription exists (should be generated by LLM, but add fallback)
                    if not hasattr(item, 'detailedDescription') or not getattr(item, 'detailedDescription', ''):
                        item.detailedDescription = getattr(item, 'description', '')
                    key = (getattr(item, 'title', None), getattr(item, 'sourceUrl', None))
                    if key not in existing_keys:
                        new_news_items.append(item)

                # 2b. Add new items to existing doc
                news_doc.news.extend(new_news_items)
                news_doc.updatedAt = datetime.utcnow()

                # 2c. Generate images for new items
                for news_item in new_news_items:
                    image_id = getattr(news_item, 'id', None) or f"{getattr(news_item, 'title', '')}_{getattr(news_item, 'sourceUrl', '')}"
                    image_url = self.news_image_generation.process_article(news_item.description, image_id)
                    news_item.imageUrl = image_url

                self.news_model.update_news(dashboard_id, news_doc.model_dump(by_alias=True))
                news = self.news_model.get_news(dashboard_id)

            else:
                # 3. No news exists, create new document
                for item in news.news:
                    if not hasattr(item, 'id') or getattr(item, 'id', None) is None:
                        try:
                            item.id = str(ObjectId())
                        except Exception:
                            pass
                    # Ensure detailedDescription exists (should be generated by LLM, but add fallback)
                    if not hasattr(item, 'detailedDescription') or not getattr(item, 'detailedDescription', ''):
                        item.detailedDescription = getattr(item, 'description', '')

                news_payload = {
                    "dashboardId": dashboard_id,
                    "news": [item.model_dump(by_alias=True) for item in news.news],
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }
                self.news_model.create(news_payload)

                news_generated = self.news_model.get_news(dashboard_id)
                for news_doc in news_generated:
                    for news_item in news_doc.news:
                        image_id = getattr(news_item, 'id', None) or f"{getattr(news_item, 'title', '')}_{getattr(news_item, 'sourceUrl', '')}"
                        image_url = self.news_image_generation.process_article(news_item.description, image_id)
                        news_item.imageUrl = image_url
                    self.news_model.update_news(dashboard_id, news_doc.model_dump(by_alias=True))
                news = self.news_model.get_news(dashboard_id)

            return {"success": True, "data": news}

        except Exception as e:
            print(f"Error in generating news: {e}")
            return {"success": False, "data": None, "error": str(e)}
        
    def format_news(self, raw_data: str):
        
        system_message = SystemMessage(
        content=f"""You are a legal news analyst. Analyze the provided documents and return the most relevant news items.
        
        For each news item, you must provide:
        1. title: A concise title for the news
        2. description: A brief summary of the news
        3. detailedDescription: A comprehensive, rephrased, and expanded version of the news content. This MUST be a very detailed explanation containing approximately 50-100 sentences (minimum 50 sentences). The detailedDescription should:
           - Provide extensive in-depth information about the news item
           - Rephrase and expand upon the raw news data comprehensively
           - Include background context, implications, and detailed analysis
           - Cover all relevant aspects, legal implications, industry impact, and future considerations
           - Be well-written, informative, and provide thorough understanding of the topic
           - Ensure it is substantial and detailed enough to give readers a complete understanding
        4. sourceUrl: The URL to the original source
        
        CRITICAL: The detailedDescription must be substantial - aim for 50-100 sentences. Do not provide a brief summary. Make it comprehensive and detailed.
        """
        )
        messages = [
            system_message,
            HumanMessage(content=f"text: {raw_data}")
        ]
        structured_llm = self.chat.with_structured_output(NewsList)
        response = structured_llm.invoke(messages)
        return response