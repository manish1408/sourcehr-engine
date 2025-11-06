import asyncio
from datetime import datetime
import json
from fastapi import HTTPException
from bson import ObjectId
from typing import Optional
from app.models.WebsiteCrawl import WebsiteCrawlModel
from app.schemas.WebsiteCrawl import WebsiteCrawlSchema, WebsiteCrawlCreate
from app.helpers.Scraper import WebsiteScraper
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re
from threading import Event
from app.helpers.VectorDB import VectorDB 
scheduler = BackgroundScheduler(job_defaults={
    'coalesce': True,
    'max_instances': 1,
    'misfire_grace_time': 30,
})
scheduler.start()
stop_event = Event()
from app.helpers.Crawler import hybrid_crawl_logic_async
from app.schemas.WebsiteCrawl import CrawlableURL
from datetime import datetime




class WebsiteCrawlService:
    def __init__(self):
        self.model = WebsiteCrawlModel()
        # self.crawler=WebsiteCrawler()
        self.scraper=WebsiteScraper()
        self.vector_db=VectorDB("source-hr-knowledge")

    def create_website_crawl(self, data: WebsiteCrawlCreate) -> dict:
        try:
            crawl_data = data.model_dump()
            inserted_id = self.model.create_website_crawl(crawl_data)
            return {
                "success": True,
                "data": inserted_id
            }
        except Exception as e:
            return {
                "success": False,
                "data": str(e),
                "error": "Unable to create website crawl"
            }

    def list_website_crawls(self, page: int = 1, limit: int = 10, filters: dict = {}) -> dict:
        try:
            # Get scheduled jobs and map by job ID for quick lookup
            jobs = scheduler.get_jobs()
            job_map = {job.id: str(job.next_run_time) for job in jobs}

            # Fetch paginated crawls from DB
            total = self.model.collection.count_documents(filters)
            total_pages = (total + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            crawls = self.model.get_website_crawls(filters, number_to_skip, limit)

            # Attach only next_run_time to each crawl
            for crawl in crawls:
                job_id = str(crawl.get("id"))  # Assuming crawl has job_id
                crawl["next_run_time"] = job_map.get(job_id)

            return {
                "success": True,
                "data": {
                    "crawls": crawls,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentPage": page,
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to list website crawls: {str(e)}"
            }


    def get_website_crawl_by_id(self, crawl_id: str, page: int = 1, limit: int = 10) -> dict:
        try:
            if not ObjectId.is_valid(crawl_id):
                raise HTTPException(status_code=400, detail="Invalid Crawl ID")
            # Fetch the full document to count total URLs
            full_doc = self.model.collection.find_one({"_id": ObjectId(crawl_id)})
            if not full_doc:
                raise HTTPException(status_code=404, detail="Website crawl not found")
            total_urls = len(full_doc.get("listOfCrawlableUrls", []))
            total_pages = (total_urls + limit - 1) // limit
            number_to_skip = (page - 1) * limit
            # Fetch the paginated URLs
            crawl = self.model.get_website_crawl_with_paginated_urls({"_id": ObjectId(crawl_id)}, number_to_skip, limit)
            if not crawl:
                raise HTTPException(status_code=404, detail="Website crawl not found")
            return {
                "success": True,
                "data": {
                    "crawl": crawl,
                    "pagination": {
                        "totalPages": total_pages,
                        "currentpage": page,    
                        "limit": limit
                    }
                }
            }
        except Exception as e:
            return {    
                "success": False,
                "data": None,
                "error": f"Unable to get website crawl: {str(e)}"
            }

    def update_website_crawl(self, crawl_id: str, update_data: dict) -> dict:
        try:
            if not ObjectId.is_valid(crawl_id):
                raise HTTPException(status_code=400, detail="Invalid Crawl ID")
            updated = self.model.update_website_crawl({"_id": ObjectId(crawl_id)}, update_data)
            if not updated:
                raise HTTPException(status_code=404, detail="Website crawl not found or not updated")
            return {
                "success": True,
                "data": "Website crawl updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to update website crawl: {str(e)}"
            }

    def delete_website_crawl(self, crawl_id: str) -> dict:
        try:
            deleted = self.model.delete_website_crawl(crawl_id)
            return {
                "success": True,
                "data": "Website crawl deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "error": f"Unable to delete website crawl: {str(e)}"
            }

    # def schedule_crawl(self, crawl_id: str, max_depth: int = 1, max_urls: int = None):
    #     try:
    #         website = self.model.collection.find_one({"_id": ObjectId(crawl_id)})
    #         duration_str = website.get("crawlDuration", "1H")
    #         hours, minutes = self.parse_duration(duration_str)
    #         scheduler.add_job(
    #             self._run_crawl,
    #             'interval',
    #             hours=hours,
    #             minutes=minutes,
    #             id=crawl_id,
    #             kwargs={"website_id": crawl_id, "max_depth": max_depth, "max_urls": max_urls}
    #         )
    #         # Update the crawlStatus to SCHEDULED after scheduling the job
    #         self.model.collection.update_one(
    #             {"_id": ObjectId(crawl_id)},
    #             {"$set": {"crawlStatus": "SCHEDULED"}}
    #         )
    #         return {
    #             "success": True,
    #             "data": "Crawl scheduled successfully"
    #         }
    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "data": None,
    #             "error": f"Unable to schedule crawl: {str(e)}"
    #         }

    # def parse_duration(self, duration_str):
    #     # Example: "10H20M", "12H", "45M"
    #     hours = 0
    #     minutes = 0
    #     match = re.match(r'(?:(\d+)H)?(?:(\d+)M)?', duration_str)
    #     if match:
    #         if match.group(1):
    #             hours = int(match.group(1))
    #         if match.group(2):
    #             minutes = int(match.group(2))
    #     return hours, minutes

    # def stop_crawl(self, crawl_id: str):
    #     try:
    #         stop_event.set()
    #         print(scheduler.get_jobs())
    #         scheduler.remove_job(job_id=crawl_id)
    #         return {"data": f"Crawl {crawl_id} stopped", "success": True}
    #     except JobLookupError:
    #         return {"data": None, "success": False, "error": "Crawl job not found or already stopped"}
    #     except Exception as e:
    #         return {"data": None, "success": False, "error": str(e)}

    def list_jobs(self):
        try:
            print("asjdasjdahsj")
            jobs = scheduler.get_jobs()
            job_list = []
            for job in jobs:
                job_list.append({
                    "id": job.id,
                    "next_run_time": str(job.next_run_time),
                    "trigger": str(job.trigger),
                    "func": str(job.func_ref),
                    "args": job.args,
                    "kwargs": job.kwargs,
                })
            return {"success": True, "data": job_list}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}

    async def fetch_crawlable_urls(self, crawl_id: str) -> dict:

        try:
            website = self.model.collection.find_one({"_id": ObjectId(crawl_id)})
            if not website:
                return {"success": False, "data": None, "error": "Crawl entry not found"}
            # Check if crawlable URLs already exist
            if website.get("listOfCrawlableUrls") and len(website["listOfCrawlableUrls"]) > 0:
                return {"success": False, "data": website["listOfCrawlableUrls"], "error": "Already crawlable urls present"}
            self.model.collection.update_one(
                {"_id": ObjectId(crawl_id)},
                {
                    "$set": {
                        "crawlStatus": "IN_PROGRESS"
                    }
                }
            )
            url = website.get("urlOfWebsite")
            max_depth = website.get("maxDepth", 1)
            max_urls = website.get("maxUrls", 50)

            discovered_urls = await hybrid_crawl_logic_async(url, max_depth, max_urls)

            crawlable_urls = [
                CrawlableURL(
                    url=u,
                    crawlStatus="PENDING",
                    updatedOn=datetime.utcnow(),
                    ingestionStatus="PENDING",
                    ingestedOn=None,
                    vectorDocIds=[]
                ).dict() for u in discovered_urls
            ]

            self.model.update_website_crawl(
                {"_id": ObjectId(crawl_id)},
                {
                    "listOfCrawlableUrls": crawlable_urls,
                    "crawlStatus": "SUCCESS",
                    "lastCrawled": datetime.utcnow()
                }
            )
            print(f"Successfully crawled all urls from {url}")

            return {"success": True, "data": crawlable_urls}
        except Exception as e:    
            return {"success": False, "data": str(e), "error": "Unable to fetch crawlable URLs"}
        
        
    def scrape_website_and_ingest_data(self,url:str,crawl_id):
        try:
            print(f"scrapping url: {url} from crawler {crawl_id}")
            scraped_content = self.scraper.scrape_url(url)
            website_doc = self.model.collection.find_one({"_id": ObjectId(crawl_id)}, {"sourceType": 1})
            source_type = website_doc.get("sourceType", "") if website_doc else ""
            if scraped_content["success"]:
                markdown_content = scraped_content["data"]["markdown"]
                results=self.vector_db.enterWebsiteToKnowledge(
                    page_content=markdown_content,
                    url=url,
                    source_type=source_type
                )
                if results:
                    self.model.collection.update_one(
                        {"_id":ObjectId(crawl_id),"listOfCrawlableUrls.url": url},
                        {
                            "$set": {
                                "listOfCrawlableUrls.$.ingestionStatus": "SUCCESS",
                                "listOfCrawlableUrls.$.ingestedOn": datetime.utcnow(),
                                "listOfCrawlableUrls.$.crawlStatus": "SUCCESS",
                                "listOfCrawlableUrls.$.vectorDocIds": results
                            }
                        }
                    )
                    print(f"scrapped {url} from crawler {crawl_id} sucessfully")
                else:
                    self.model.collection.update_one(
                        {"_id":ObjectId(crawl_id),"listOfCrawlableUrls.url": url},
                        {
                            "$set": {
                                "listOfCrawlableUrls.$.ingestionStatus": "FAILED",
                                "listOfCrawlableUrls.$.ingestedOn": None,
                                "listOfCrawlableUrls.$.crawlStatus": "SUCCESS",
                                "listOfCrawlableUrls.$.vectorDocIds": []
                            }
                        }
                    )

            else:
                    self.model.collection.update_one(
                        {"_id":ObjectId(crawl_id),"listOfCrawlableUrls.url": url},
                        {
                            "$set": {
                                "listOfCrawlableUrls.$.ingestionStatus": "FAILED",
                                "listOfCrawlableUrls.$.ingestedOn": None,
                                "listOfCrawlableUrls.$.crawlStatus": "FAILED",
                                "listOfCrawlableUrls.$.vectorDocIds": []
                            }
                        }
                    )
                    
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        
        
    def fetch_and_scrape_pending_urls(self):
        try:
            # Atomically find and claim a pending URL
            pending_url_doc = self.model.collection.find_one_and_update(
                {"listOfCrawlableUrls.crawlStatus": "PENDING"},
                {"$set": {"listOfCrawlableUrls.$.crawlStatus": "IN_PROGRESS"}},
                projection={"urlOfWebsite": 1, "listOfCrawlableUrls.$": 1}
            )
            crawl_id=pending_url_doc["_id"]
            if not pending_url_doc or "listOfCrawlableUrls" not in pending_url_doc:
                return  # No pending URLs left

            url = pending_url_doc["listOfCrawlableUrls"][0]["url"]
            self.scrape_website_and_ingest_data(url,crawl_id)
        except Exception as e:
            return {"success": False, "error": str(e), "data": None}
        
    def schedule_scraper(self):
        try:
            # Schedule the scraper to run every 5 minutes
            scheduler.add_job(
                self.fetch_and_scrape_pending_urls,
                'interval',
                seconds=10,
                id='scraper_job',
                max_instances=1,
                coalesce=True,
                misfire_grace_time=30,
                replace_existing=True,
            )

            return {"success": True, "data": "Scraper scheduled successfully"}
        except Exception as e:
            return {"success": False, "data": None, "error": str(e)}
        
    def get_scraper_status(self, crawl_id):
        try:
            if not ObjectId.is_valid(crawl_id):
                return {"success": False, "error": "Invalid Crawl ID", "data": None}
            doc = self.model.collection.find_one({"_id": ObjectId(crawl_id)})
            if not doc:
                return {"success": False, "error": "Crawl not found", "data": None}
            urls = doc.get("listOfCrawlableUrls", [])
            total = len(urls)
            pending = sum(1 for u in urls if u.get("crawlStatus") == "PENDING")
            completed = sum(1 for u in urls if u.get("crawlStatus") == "SUCCESS")
            error = sum(1 for u in urls if u.get("crawlStatus") == "FAILED")
            return {
                "success": True,
                "data": {
                    "total": total,
                    "pending": pending,
                    "completed": completed,
                    "error": error,
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e), "data": None}
        
    def clear_crawlable_urls(self, crawl_id: str) -> dict:
            if not ObjectId.is_valid(crawl_id):
                return {"success": False, "data": None, "error": "Invalid Crawl ID"}
            updated = self.model.update_website_crawl({"_id": ObjectId(crawl_id)}, {"listOfCrawlableUrls": []})
            if not updated:
                return {"success": False, "data": None, "error": "Website crawl not found or not updated"}
            return {"success": True, "data": "listOfCrawlableUrls cleared successfully"}
        
    def fetch_crawlable_urls_from_url(
        url: str,
        max_depth: int = 1,
        max_urls: int = 50
    ) -> dict:
        """
        Crawls the given URL up to max_depth and max_urls, and returns discovered URLs.
        """
        from datetime import datetime

        try:
            discovered_urls = hybrid_crawl_logic(url, max_depth, max_urls)
            if not discovered_urls:
                return {"success": False, "data": [], "error": "No crawlable URLs found"}
            # # Optionally, wrap in your CrawlableURL schema if you want
            # crawlable_urls = [
            #     {
            #         "url": u,
            #         "crawlStatus": "PENDING",
            #         "updatedOn": datetime.utcnow(),
            #         "ingestionStatus": "PENDING",
            #         "ingestedOn": None,
            #         "vectorDocIds": []
            #     }
            #     for u in discovered_urls
            # ]
            return {"success": True, "data": discovered_urls}
        except Exception as e:
            return {"success": False, "data": [], "error": str(e)}
    
    def schedule_crawler(self):
            try:
                scheduler.add_job(
                    lambda: asyncio.run(self.fetch_pending_crawlable_urls()),
                    "interval",
                    seconds=10,
                    id="crawler_job",
                    max_instances=1,
                    coalesce=True,
                    misfire_grace_time=30,
                    replace_existing=True,
                )
                return {"success": True, "data": "Crawler scheduled successfully"}
            except Exception as e:
                return {"success": False, "data": [], "error": str(e)}
        
    async def fetch_pending_crawlable_urls(self):
        try:
            # Fetch documents with crawlStatus = "PENDING"
            pending_doc = self.model.collection.find_one({"crawlStatus": "PENDING"}, {"_id": 1})
            if pending_doc:
                crawl_id = str(pending_doc["_id"])
                await self.fetch_crawlable_urls(crawl_id)
            else:
                print("No pending crawlable URLs found")
            
        except Exception as e:
            print(f"❌ Error fetching crawlable URLs: {e}")