import json

from langchain_openai import AzureChatOpenAI
from app.models.Dashboard import DashboardModel
from app.models.Industries import IndustriesModel
from app.models.Topics import TopicsModel
from app.models.Locations import LocationsModel
from bson import ObjectId
from datetime import datetime, timedelta                        
from openai  import AzureOpenAI
import os
from app.models.DashboardCompliance import DashboardComplianceModel
from langchain.schema import HumanMessage, SystemMessage
from app.schemas.Dashboard import LawChangeListByLocation
from app.dependencies import get_vector_db, get_serp_helper, get_azure_openai_client, get_langchain_chat_client

class DashboardCompliance:
    def __init__(self):
        self.model = DashboardModel()
        # Use singleton instances instead of creating new ones
        self.vector_store = get_vector_db("source-hr-knowledge")
        self.industries_model = IndustriesModel()
        self.topics_model = TopicsModel()
        self.locations_model = LocationsModel()      
        self.dashboard_compliance_model = DashboardComplianceModel()
        self.serp_helper = get_serp_helper()
        self.azure_client = get_azure_openai_client()
        self.chat = get_langchain_chat_client()
    
    # Tool implementations
    def _tool_search_documents(self, query: str, filters: dict = None, top_k: int = 10):
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
        
    async def get_dashboard_choices(self, dashboard_id: str):
        dashboard = await self.model.get_dashboard({"_id": ObjectId(dashboard_id)})
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
        topic_slugs = []
        for category in topics:
            for topic in getattr(category, "topics", []):
                slug = getattr(topic, "slug", None)
                if slug:
                    topic_slugs.append(slug)

        location_names = [slug.replace('-', ' ').title() for slug in location_slugs] if location_slugs else []
        industry_names = [slug.replace('-', ' ').title() for slug in industry_slugs] if industry_slugs else []
        topic_names = [slug.replace('-', ' ').title() for slug in topic_slugs] if topic_slugs else []
        dashboard_choices = {
            "location_names": location_names,
            "industry_names": industry_names,
            "topic_names": topic_names
        }
        return dashboard_choices
        
    async def retrieve_law_changes(self, dashboard_id: str):
        try:
            dashboard_choices = await self.get_dashboard_choices(dashboard_id)
            # Prepare readable strings from choices
            location_str = ", ".join(dashboard_choices.get("location_names", [])) 
            industry_str = ", ".join(dashboard_choices.get("industry_names", [])) 
            topic_str = ", ".join(dashboard_choices.get("topic_names", [])) 
            tools = [
                        {
                            "type": "function",
                            "function": {
                                "name": "search_documents",
                                "description": "Search HR law documents in Pinecone with semantic query and metadata filters.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "filters": {
                                            "type": "object",
                                            "properties": {
                                                "location_slug": {"type": "string"},
                                                "primary_industry_slug": {"type": "string"},
                                                "secondary_industry_slug": {"type": "string"},
                                                "region_slug": {"type": "string"},
                                                "topic_slug": {"type": "string"},
                                                "sourceType": {"type": "string"},
                                                "discussedTimestamp_gt": {"type": "number"},
                                                "discussedTimestamp_lt": {"type": "number"}
                                            }
                                        },
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
                                "description": "Fetch latest HR/legal resources from the web via SERP API.",
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
                                "description": "Scrape and clean webpage content from one or more URLs in parallel. Use 'urls' for multiple URLs or 'url' for single URL.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "urls": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Array of URLs to scrape content from (preferred for multiple URLs)"
                                        },
                                        "url": {
                                            "type": "string",
                                            "description": "Single URL to scrape (alternative to urls array)"
                                        }
                                    }
                                }
                            }
                        }
                    ]
            messages = [
                    {
                        "role": "system",
                        "content": """You are a legal news analyst. Analyze the provided documents and extract at least 4 unique structured news items about
                    changes in employment law or HR regulations in the past 3 months.
                    You have the following tools to help you:
                    - search_documents: Search HR law documents in Pinecone with semantic query and metadata filters.
                    - fetch_serp_content: Fetch latest HR/legal resources from the web via SERP API.
                    - get_webpage_content: Scrape and clean webpage content from one or more URLs in parallel. Use 'urls' for multiple URLs or 'url' for single URL.

                    """
                    },
                    {
                        "role": "user",
                        "content": f"""Extract 4 unique structured news items about changes in employment law or HR regulations.
                        current date: {datetime.utcnow()}
                        past 3 months: {datetime.utcnow() - timedelta(days=90)}
                        Focus on the following dashboard context:
                        - Locations: {location_str}
                        - Industries: {industry_str}
                        - Topics: {topic_str}
                        """

                    }
                ]
            response = self.azure_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools
            )
            response_message = response.choices[0].message
            message_content = response.choices[0].message.content

            while not message_content and response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    if function_name == "search_documents":
                        result = self._tool_search_documents(**args)
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
                message_content = response.choices[0].message.content
                
                
            law_changes = self.format_law_changes(message_content)
                
                
                
            # Build a minimal valid payload structure (empty list placeholder)
            
    
            compliance_payload = {
                "dashboardId": dashboard_id,
                "data": law_changes,
                "status": "FETCHED",
                "createdAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }
            try:
                self.dashboard_compliance_model.create(compliance_payload)
            except Exception as e:
                # Do not fail the endpoint if persistence fails; return the computed data
                print(f"Persisting dashboard compliance failed: {e}")
            return {
                "success": True,
                "data": law_changes
            }

        except Exception as e:
            print(f"Error in retrieve_law_changes: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    def format_law_changes(self, raw_data: str):
        
        system_message = SystemMessage(
        content=f"""You are a legal compliance analyst. Analyze the provided documents and return the most relevant law changes in the past 3 months.
        """
        )
        messages = [
            system_message,
            HumanMessage(content=f"text: {raw_data}")
        ]
        structured_llm = self.chat.with_structured_output(LawChangeListByLocation)
        response = structured_llm.invoke(messages)
        return response.lawChangesByLocation