import json

from langchain_openai import AzureChatOpenAI
from app.models.Dashboard import DashboardModel
from app.helpers.VectorDB import VectorDB
from app.models.Industries import IndustriesModel
from app.models.Topics import TopicsModel
from app.models.Locations import LocationsModel
from bson import ObjectId
from datetime import datetime, timedelta                        
from openai  import AzureOpenAI
import os
from app.models.CourtDecisions import CourtDecisionsModel
from app.helpers.SERP import SERPHelper
from langchain.schema import HumanMessage, SystemMessage
from app.schemas.Dashboard import CourtDecisionList

    
class CourtDecisions:
    def __init__(self):
        self.model = DashboardModel()
        self.vector_store = VectorDB("source-hr-knowledge")
        self.industries_model = IndustriesModel()
        self.topics_model = TopicsModel()
        self.locations_model=LocationsModel()      
        self.court_decisions_model = CourtDecisionsModel()
        self.serp_helper = SERPHelper()
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
        
    def retrieve_court_decisions(self, dashboard_id: str):
        try:
            dashboard_choices = self.get_dashboard_choices(dashboard_id)
            # Prepare readable strings from choices
            location_str = ", ".join(dashboard_choices.get("location_names", [])) or "all locations"
            industry_str = ", ".join(dashboard_choices.get("industry_names", [])) or "all industries"
            topic_str = ", ".join(dashboard_choices.get("topic_names", [])) or "all topics"
            region_str = ", ".join(dashboard_choices.get("region_names", [])) if dashboard_choices.get("region_names") else ""
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
                        "content": """You are a legal news analyst. Analyze the provided documents and extract at least 4 unique structured court decisions about
                    changes in employment law or HR regulations.
                    You have the following tools to help you:
                    - search_documents: Search HR law documents in Pinecone with semantic query and metadata filters.
                    - fetch_serp_content: Fetch latest HR/legal resources from the web via SERP API.
                    - get_webpage_content: Scrape and clean webpage content from one or more URLs in parallel. Use 'urls' for multiple URLs or 'url' for single URL.
                    """
                    },
                    {
                        "role": "user",
                        "content": f"""Extract 4 unique structured court decisions about changes in employment law or HR regulations.
                        current date: {datetime.utcnow()}
                        Focus on the following dashboard context:
                        - Locations: {location_str}
                        - Industries: {industry_str}
                        - Topics: {topic_str}
                        - Regions: {region_str if region_str else "all regions"}
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

                response = self.azure_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=tools
                    )
                response_message = response.choices[0].message
                message_content = response.choices[0].message.content
            court_decisons = self.format_court_decisions(message_content)
   
            existing_docs = self.court_decisions_model.get_court_decisions(dashboard_id)
            if existing_docs:
                doc = existing_docs[0]
                existing_list = doc.courtDecisions if hasattr(doc, 'courtDecisions') else []
                existing_keys = {(getattr(n, 'title', None), getattr(n, 'sourceUrl', None)) for n in existing_list}
                new_items = []
                for item in court_decisons:
                    key = (item.get('title'), item.get('sourceUrl'))
                    if key not in existing_keys:
                        new_items.append(item)
                doc.courtDecisions.extend(new_items)
                doc.updatedAt = datetime.utcnow()
                self.court_decisions_model.update_court_decisions(dashboard_id, doc.model_dump(by_alias=True))
                result = self.court_decisions_model.get_court_decisions(dashboard_id)
            else:
                payload = {
                    "dashboardId": dashboard_id,
                    "courtDecisions": court_decisons,
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }
                self.court_decisions_model.create(payload)
                result = self.court_decisions_model.get_court_decisions(dashboard_id)

            return {"success": True, "data": result}

        except Exception as e:
            print(f"Error in retrieve_court_decisions: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
            
    def format_court_decisions(self, raw_data: str):
        
        system_message = SystemMessage(
        content=f"""You are a legal court decisions analyst. Analyze the provided documents and return the most relevant court decisions.
        """
        )
        messages = [
            system_message,
            HumanMessage(content=f"text: {raw_data}")
        ]
        structured_llm = self.chat.with_structured_output(CourtDecisionList)
        response = structured_llm.invoke(messages)
        return [item.model_dump() for item in response.courtDecisions]