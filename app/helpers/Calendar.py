import json
import re
import markdown
from bs4 import BeautifulSoup

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
from app.models.LegalCalender import LegalCalenderModel
from app.helpers.SERP import SERPHelper
from langchain.schema import HumanMessage, SystemMessage
from app.schemas.Dashboard import LegalCalendar
from app.helpers.UrlScraperHelper import UrlScraperHelper
from app.helpers.Scraper import WebsiteScraper
from typing import List, Dict, Any, Optional
    
class Calendar:
    def __init__(self):
        self.model = DashboardModel()
        self.vector_store = VectorDB("source-hr-knowledge")
        self.industries_model = IndustriesModel()
        self.topics_model = TopicsModel()
        self.locations_model=LocationsModel()      
        self.calendar_model = LegalCalenderModel()
        self.serp_helper = SERPHelper()
        self.url_scraper_helper = UrlScraperHelper()
        self.scraper = WebsiteScraper()
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
    
    def _markdown_to_text(self, md: str) -> str:
        """Convert markdown to clean text."""
        html = markdown.markdown(md)
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()
    
    def _is_authoritative_source(self, url: str) -> bool:
        """
        Filter URLs to only authoritative sources (gov, law firms, agencies).
        Prevents hallucinations from non-authoritative sources.
        """
        url_lower = url.lower()
        authoritative_domains = [
            '.gov', '.edu', 
            'dol.gov', 'eeoc.gov', 'nlrb.gov', 'osha.gov',
            'law.com', 'lexisnexis.com', 'westlaw.com',
            'court', 'judicial', 'legislature', 'congress',
            'bar.org', 'americanbar.org'
        ]
        return any(domain in url_lower for domain in authoritative_domains)
    
    def discover_candidate_urls(self, dashboard_choices: dict) -> List[Dict[str, str]]:
        """
        STEP 1: SERP-ONLY DISCOVERY (NO LLM)
        Discover candidate URLs using SERP API in Python.
        Filter to authoritative sources only.
        Returns: [{ url, title }]
        """
        location_str = ", ".join(dashboard_choices.get("location_names", [])) or "all locations"
        industry_str = ", ".join(dashboard_choices.get("industry_names", [])) or "all industries"
        topic_str = ", ".join(dashboard_choices.get("topic_names", [])) or "all topics"
        region_str = ", ".join(dashboard_choices.get("region_names", [])) if dashboard_choices.get("region_names") else ""
        
        # Build search queries for legal calendar events
        queries = []
        base_query = "employment law changes HR regulation effective date"
        
        if location_str != "all locations":
            queries.append(f"{base_query} {location_str}")
        if industry_str != "all industries":
            queries.append(f"{base_query} {industry_str}")
        if topic_str != "all topics":
            queries.append(f"{base_query} {topic_str}")
        if region_str:
            queries.append(f"{base_query} {region_str}")
        
        # If no specific filters, use general query
        if not queries:
            queries = [base_query]
        
        candidate_urls = []
        seen_urls = set()
        
        for query in queries[:3]:  # Limit to 3 queries to avoid rate limits
            try:
                serp_results = self.serp_helper.serp_results(query)
                if isinstance(serp_results, list):
                    for result in serp_results[:10]:  # Top 10 per query
                        url = result.get('link') or result.get('url')
                        title = result.get('title', '')
                        
                        if url and url not in seen_urls:
                            # Filter to authoritative sources only
                            if self._is_authoritative_source(url):
                                candidate_urls.append({
                                    "url": url,
                                    "title": title
                                })
                                seen_urls.add(url)
            except Exception as e:
                print(f"[Calendar] Error in SERP discovery for query '{query}': {e}")
                continue
        
        print(f"[Calendar] Discovered {len(candidate_urls)} candidate URLs from SERP")
        return candidate_urls
    
    def _scrape_source_text(self, url: str) -> Optional[str]:
        """
        STEP 2: SOURCE SCRAPING (NO LLM)
        Scrape a single URL and return clean page text.
        """
        try:
            scraped_content = self.scraper.scrape_url(url)
            if scraped_content.get("success"):
                markdown_content = scraped_content["data"]["markdown"]
                clean_text = self._markdown_to_text(markdown_content)
                return clean_text
            else:
                print(f"[Calendar] Failed to scrape {url}: {scraped_content.get('error', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"[Calendar] Error scraping {url}: {e}")
            return None
    
    def _extract_events_from_source(self, source_url: str, source_text: str, dashboard_choices: dict) -> List[Dict[str, Any]]:
        """
        STEP 3: SOURCE-BOUND EXTRACTION (LLM)
        The LLM may ONLY see sourceUrl and scraped sourceText.
        The LLM must generate title, shortDescription, effectiveDate ONLY if explicitly stated.
        """
        location_str = ", ".join(dashboard_choices.get("location_names", [])) or "all locations"
        industry_str = ", ".join(dashboard_choices.get("industry_names", [])) or "all industries"
        topic_str = ", ".join(dashboard_choices.get("topic_names", [])) or "all topics"
        
        # Truncate source text to avoid token limits (keep first 8000 chars)
        truncated_text = source_text[:8000] if len(source_text) > 8000 else source_text
        
        system_message = SystemMessage(
            content=f"""You are a legal calendar extraction specialist. Your task is EXTRACTIVE ONLY - you must extract facts that are EXPLICITLY stated in the provided source text.

CRITICAL RULES:
1. DO NOT infer, improve, or generalize legal meaning beyond what is explicitly stated.
2. DO NOT use legal knowledge outside the provided sourceText.
3. If effective date is NOT explicitly stated in the source, set effective_date = null.
4. If description cannot be FULLY supported by explicit statements in the source, do NOT generate it.
5. You MUST provide descriptionEvidence - the exact sentence(s) from sourceText supporting the description.
6. If effective_date is provided, you MUST provide dateEvidence - the exact sentence(s) from sourceText supporting the date.

Dashboard context (for relevance filtering only):
- Locations: {location_str}
- Industries: {industry_str}
- Topics: {topic_str}

Extract legal calendar events ONLY if they are explicitly mentioned in the source text.
If no calendar events are found, return an empty events list.
"""
        )
        
        user_message = HumanMessage(
            content=f"""Source URL: {source_url}

Source Text:
{truncated_text}

Extract legal calendar events from this source. Only extract events that are EXPLICITLY stated in the source text above.
For each event, provide:
- title: Extract or infer a concise title from the source
- description: Extract the description ONLY if it can be fully supported by explicit text
- effective_date: Extract ONLY if explicitly stated (format: YYYY-MM-DD), otherwise null
- descriptionEvidence: The exact sentence(s) from sourceText that support the description
- dateEvidence: The exact sentence(s) from sourceText that support the effective_date (if provided)
- sourceUrl: {source_url}
"""
        )
        
        try:
            structured_llm = self.chat.with_structured_output(LegalCalendar)
            response = structured_llm.invoke([system_message, user_message])
            return [event.model_dump() for event in response.events]
        except Exception as e:
            print(f"[Calendar] Error extracting events from {source_url}: {e}")
            return []
    
    def _enforce_evidence_guardrails(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        STEP 5: PROGRAMMATIC GUARDRAILS
        Remove unsupported facts:
        - If effectiveDate exists but no dateEvidence → remove effectiveDate
        - If description exists but no descriptionEvidence → discard the event
        """
        validated_events = []
        
        for event in events:
            # Guardrail 1: If effective_date exists but no dateEvidence → remove effective_date
            if event.get('effective_date') and not event.get('dateEvidence'):
                print(f"[Calendar] Removing effective_date from event '{event.get('title')}' - no dateEvidence")
                event['effective_date'] = None
                event['dateEvidence'] = None
            
            # Guardrail 2: If description exists but no descriptionEvidence → discard the event
            if event.get('description') and not event.get('descriptionEvidence'):
                print(f"[Calendar] Discarding event '{event.get('title')}' - description without evidence")
                continue
            
            # Guardrail 3: If effective_date is provided, ensure dateEvidence exists
            if event.get('effective_date') and not event.get('dateEvidence'):
                # This should not happen after guardrail 1, but double-check
                event['effective_date'] = None
            
            validated_events.append(event)
        
        return validated_events
    
    
    # ============================================================================
    # DEPRECATED: Tool implementations (no longer used in source-first pipeline)
    # These methods are kept for backward compatibility but are NOT used in
    # the new retrieve_calendar() method which follows the SOURCE-FIRST architecture.
    # ============================================================================
    def _tool_search_documents(self, query: str, filters: dict = None, top_k: int = 10,region_slugs: list = None):
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
        
    def retrieve_calendar(self, dashboard_id: str):
        """
        SOURCE-FIRST, NON-HALLUCINATING Legal Calendar Generation Pipeline
        
        STEP 1: SERP-ONLY DISCOVERY (NO LLM)
        STEP 2: SOURCE SCRAPING (NO LLM)
        STEP 3: SOURCE-BOUND EXTRACTION (LLM - extractive only)
        STEP 4: EVIDENCE ENFORCEMENT (built into extraction)
        STEP 5: PROGRAMMATIC GUARDRAILS
        """
        try:
            dashboard_choices = self.get_dashboard_choices(dashboard_id)
            
            # STEP 1: SERP-ONLY DISCOVERY (NO LLM)
            print("[Calendar] STEP 1: Discovering candidate URLs via SERP...")
            candidate_urls = self.discover_candidate_urls(dashboard_choices)
            
            if not candidate_urls:
                print("[Calendar] No candidate URLs found, returning existing calendar")
                existing_docs = self.calendar_model.get_legal_calender(dashboard_id)
                return {"success": True, "data": existing_docs if existing_docs else []}
            
            # STEP 2: SOURCE SCRAPING (NO LLM)
            print(f"[Calendar] STEP 2: Scraping {len(candidate_urls)} URLs...")
            scraped_sources = []
            for candidate in candidate_urls:
                url = candidate["url"]
                source_text = self._scrape_source_text(url)
                if source_text:
                    scraped_sources.append({
                        "url": url,
                        "title": candidate.get("title", ""),
                        "text": source_text
                    })
            
            if not scraped_sources:
                print("[Calendar] No sources successfully scraped, returning existing calendar")
                existing_docs = self.calendar_model.get_legal_calender(dashboard_id)
                return {"success": True, "data": existing_docs if existing_docs else []}
            
            print(f"[Calendar] Successfully scraped {len(scraped_sources)} sources")
            
            # STEP 3: SOURCE-BOUND EXTRACTION (LLM - extractive only, no RAG, no web fetching)
            print("[Calendar] STEP 3: Extracting events from sources (LLM extractive only)...")
            all_events = []
            for source in scraped_sources:
                events = self._extract_events_from_source(
                    source["url"],
                    source["text"],
                    dashboard_choices
                )
                all_events.extend(events)
            
            if not all_events:
                print("[Calendar] No events extracted from sources, returning existing calendar")
                existing_docs = self.calendar_model.get_legal_calender(dashboard_id)
                return {"success": True, "data": existing_docs if existing_docs else []}
            
            print(f"[Calendar] Extracted {len(all_events)} events from sources")
            
            # STEP 5: PROGRAMMATIC GUARDRAILS
            print("[Calendar] STEP 5: Enforcing evidence guardrails...")
            validated_events = self._enforce_evidence_guardrails(all_events)
            
            # Filter to only include events with valid sourceUrl
            legal_events_dict = []
            for event in validated_events:
                if event.get('sourceUrl') and event.get('sourceUrl').strip():
                    legal_events_dict.append(event)
            
            if not legal_events_dict:
                print("[Calendar] No validated events with sourceUrl found, skipping save")
                existing_docs = self.calendar_model.get_legal_calender(dashboard_id)
                return {"success": True, "data": existing_docs if existing_docs else []}
            
            print(f"[Calendar] {len(legal_events_dict)} events passed validation")
            
            # Save scraped URLs to vector DB for future reference (optional, for other features)
            calendar_urls = [item.get('sourceUrl') for item in legal_events_dict if item.get('sourceUrl')]
            if calendar_urls:
                try:
                    scrape_result = self.url_scraper_helper.scrape_and_save_urls(
                        urls=calendar_urls,
                        dashboard_id=dashboard_id,
                        source="calendar"
                    )
                    print(f"[Calendar] Saved {scrape_result.get('scraped_count', 0)} URLs to vector DB")
                except Exception as e:
                    print(f"[Calendar] Error saving URLs to vector DB: {e}")

            # Merge into existing document if present, else create new
            existing_docs = self.calendar_model.get_legal_calender(dashboard_id)
            if existing_docs:
                doc = existing_docs[0]
                # Gather existing keys for duplicate detection across all calendars in data
                existing_events = []
                for cal in getattr(doc, 'data', []) or []:
                    existing_events.extend(getattr(cal, 'events', []) or [])
                existing_keys = {(getattr(e, 'title', None), getattr(e, 'sourceUrl', None)) for e in existing_events}

                # Append only new events into the first calendar entry (create one if missing)
                new_items = []
                for item in legal_events_dict:
                    key = (item.get('title'), item.get('sourceUrl'))
                    if key not in existing_keys:
                        new_items.append(item)

                if getattr(doc, 'data', None):
                    target_calendar = doc.data[0]
                else:
                    # Create a new calendar container if none exists
                    from app.schemas.LegalCalender import LegalCalendar as LegalCalendarSchema, LegalCalendarEvent
                    target_calendar = LegalCalendarSchema(events=[])
                    doc.data = [target_calendar]

                # Convert dicts into model instances and extend
                from app.schemas.LegalCalender import LegalCalendarEvent
                target_calendar.events.extend([LegalCalendarEvent(**ni) for ni in new_items])
                doc.updatedAt = datetime.utcnow()
                # Keep status as FETCHED when new data arrives
                doc.status = 'FETCHED'
                self.calendar_model.update_legal_calender(dashboard_id, doc.model_dump(by_alias=True))
            else:
                legal_calender_payload = {
                    "dashboardId": dashboard_id,
                    "data": [{"events": legal_events_dict}],
                    "status": "FETCHED",
                    "createdAt": datetime.utcnow(),
                    "updatedAt": datetime.utcnow()
                }
                self.calendar_model.create(legal_calender_payload)

            # Return the up-to-date legal calendar documents
            saved_legal_calendar = self.calendar_model.get_legal_calender(dashboard_id)
            return {"success": True, "data": saved_legal_calendar}

        except Exception as e:
            print(f"Error in retrieve_legal_calendar: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            