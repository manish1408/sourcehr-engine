import json
from urllib.parse import urlencode
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field
import requests
import os
from dotenv import load_dotenv
from app.helpers.Crawler import hybrid_crawl_logic_async
import markdown
from bs4 import BeautifulSoup
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
import asyncio
import concurrent.futures
from typing import List, Dict, Any
from datetime import datetime
from app.helpers.VectorDB import VectorDB
from app.helpers.Scraper import WebsiteScraper
from app.models.SerpUrl import SerpUrlModel
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re
from threading import Event

scheduler = BackgroundScheduler(job_defaults={
    'coalesce': True,
    'max_instances': 1,
    'misfire_grace_time': 30,
})
scheduler.start()
stop_event = Event()
load_dotenv()

class WebPageSummary(BaseModel):
    summary: str = Field(..., description="Detailed summary with all key information from the webpage")

class SERPHelper:
    def __init__(self):
        self.scraper=WebsiteScraper()
        self.serp_url_model = SerpUrlModel()
        self.chat = AzureChatOpenAI(
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            azure_deployment=os.getenv('gpt-4o-mini'),
            api_key=os.getenv('AZURE_OPENAI_KEY'),
            api_version="2024-12-01-preview",
            model_name="gpt-4o-mini",
            openai_api_type="azure",
            streaming=False,
        )
        self.vector_db = VectorDB("source-hr-knowledge")
        

    def markdown_to_text(self,md: str) -> str:
        html = markdown.markdown(md)
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()
    
    

    def get_webpage(self, pageUrl):
        
        scraped_content = self.scraper.scrape_url(pageUrl)
        if scraped_content["success"]:
            markdown_content = scraped_content["data"]["markdown"]
            raw_content =  self.markdown_to_text(markdown_content)
            
            structured_llm = self.chat.with_structured_output(WebPageSummary)
            final_resp = structured_llm.invoke(
                f" Summaries the below content in detail \n\n\n {raw_content}"
            )
            return final_resp.summary
        
        else:
            return ""

    def _process_single_url(self, url: str) -> Dict[str, Any]:
        """Process a single URL and return structured result"""
        try:
            scraped_content = self.scraper.scrape_url(url)
            if scraped_content["success"]:
                markdown_content = scraped_content["data"]["markdown"]
                raw_content = self.markdown_to_text(markdown_content)
                self.serp_url_model.create_serp_url({
                    "url": url,
                    "rawContent": raw_content,
                })
                
                structured_llm = self.chat.with_structured_output(WebPageSummary)
                final_resp = structured_llm.invoke(
                    f" Summaries the below content in detail \n\n\n {raw_content}"
                )
                return {
                    "url": url,
                    "success": True,
                    "content": final_resp.summary,
                    "error": None
                }
            else:
                return {
                    "url": url,
                    "success": False,
                    "content": "",
                    "error": scraped_content.get("error", "Unknown scraping error")
                }
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "content": "",
                "error": str(e)
            }

    def get_webpages_parallel(self, urls: List[str], max_workers: int = 5) -> List[Dict[str, Any]]:
        """
        Process multiple URLs in parallel using ThreadPoolExecutor
        
        Args:
            urls: List of URLs to process
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of dictionaries with url, success, content, and error fields
        """
        if not urls:
            return []
        
        # Limit the number of workers to avoid overwhelming the system
        max_workers = 5
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_url = {executor.submit(self._process_single_url, url): url for url in urls}
            
            # Collect results as they complete
            results = []
            for future in concurrent.futures.as_completed(future_to_url):
                result = future.result()
                results.append(result)
        
        return results
            

    
    def serp_results(self, query: str):
        """
        Calls BrightData SERP API synchronously with a *properly encoded* Google URL.
        """
        key = os.getenv("BRIGHTDATA_SERP_KEY")
        if not key:
            raise ValueError("Missing BRIGHTDATA_SERP_KEY in environment variables")

        # Build a valid Google Search URL: https://www.google.com/search?q=<encoded>
        qs = urlencode({"q": query})
        google_url = f"https://www.google.com/search?{qs}&brd_json=1"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        }

        payload = {
            "zone": "source_hr_serp",
            "url": google_url,
            "format": "json"
        }

        r = requests.post("https://api.brightdata.com/request", headers=headers, json=payload)

        if r.status_code != 200:
            raise RuntimeError(
                f"BrightData SERP API failed: {r.status_code}, {r.text}\n"
                f"Payload url={google_url}"
            )

        data = r.json()

        if "body" in data:
            try:
                result =  json.loads(data["body"])
                
                return result.get("organic", [])
            except json.JSONDecodeError:
                raise ValueError("Failed to parse BrightData 'body' JSON")
        else:
            return data
        
        
    def scrape_pending_serp_url(self):
        try:
            pending_url=self.serp_url_model.collection.find_one({"status": "PENDING"})
            if pending_url:
                print(f"Scraping pending SERP URL: {pending_url.get('url', '')}")
                results=self.vector_db.enterWebsiteToKnowledge(
                    page_content=pending_url.get("rawContent", ""),
                    url=pending_url.get("url", ""),
                    source_type="HR Resource"
                )
                self.serp_url_model.collection.update_one({"_id": pending_url.get("_id", "")}, {"$set": {"status": "SUCCESS", "vectorDocIds": results}})
                self.serp_url_model.collection.update_one({"_id": pending_url.get("_id", "")}, {"$unset": {"rawContent": ""}})
                print(f"Scraped pending SERP URL: {pending_url.get('url', '')}")
                
            else:
                print("No pending SERP URL found")
                
        except Exception as e:
            self.serp_url_model.collection.update_one({"_id": pending_url.get("_id", "")}, {"$set": {"status": "ERROR"}})
            print(f"Error scraping pending SERP URL: {e}")
            

            
    def schedule_scrape_pending_serp_url(self):
        try:
            scheduler.add_job(
                self.scrape_pending_serp_url,
                'interval',
                minutes=1,
                id='scrape_pending_serp_url',
            )
            return {
                "success": True,
                "data": "Scrape pending SERP URL scheduled successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }

# if __name__ == "__main__":
#     helper = SERPHelper()
    
#     # Example: get Google SERP
#     serp_data = helper.serp_results("North Dakota HR law updates")
#     print(serp_data)

#     # Example: get a webpage via hybrid_crawl
#     page_data = helper.get_webpage("https://www.ndcourts.gov/news")
#     print(page_data)
