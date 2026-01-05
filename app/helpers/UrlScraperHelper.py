from typing import List, Optional
from app.models.ScrapedUrl import ScrapedUrlModel
from app.helpers.VectorDB import VectorDB
from app.helpers.Scraper import WebsiteScraper
from datetime import datetime


class UrlScraperHelper:
    """
    Helper class to scrape URLs and save them to vector database in dashboard-specific namespaces.
    Tracks scraped URLs in MongoDB to avoid re-scraping.
    """
    
    def __init__(self):
        self.scraped_url_model = ScrapedUrlModel()
        self.scraper = WebsiteScraper()
    
    def scrape_and_save_urls(
        self, 
        urls: List[str], 
        dashboard_id: str, 
        source: str
    ) -> dict:
        """
        Scrape URLs and save to vector DB if not already scraped.
        
        Args:
            urls: List of URLs to scrape
            dashboard_id: Dashboard ID for namespace and tracking
            source: Source type ("news", "calendar", or "compliance")
            
        Returns:
            dict with success status and details
        """
        if not urls:
            return {"success": True, "scraped_count": 0, "skipped_count": 0}
        
        scraped_count = 0
        skipped_count = 0
        errors = []
        
        # Create vector DB instance with dashboard-specific namespace
        namespace = f"{dashboard_id}-memory"
        vector_db = VectorDB(namespace)
        
        for url in urls:
            if not url or not url.strip():
                continue
                
            url = url.strip()
            
            try:
                # Check if URL is already scraped
                existing = self.scraped_url_model.get_by_dashboard_source_url(
                    dashboard_id, source, url
                )
                
                # Skip only if successfully scraped and has vector DB IDs
                if existing and existing.scraped and existing.vectorDbIds:
                    # URL already successfully scraped, skip
                    skipped_count += 1
                    continue
                
                # If existing entry has error or failed scraping, we'll retry and update
                
                # Scrape the URL
                scraped_content = self.scraper.scrape_url(url)
                
                if not scraped_content.get("success"):
                    # Scraping failed - create entry with error message
                    error_msg = f"Failed to scrape: {scraped_content.get('error', 'Unknown error')}"
                    errors.append(f"Failed to scrape {url}: {scraped_content.get('error', 'Unknown error')}")
                    self.scraped_url_model.create_or_update_with_error(
                        dashboard_id=dashboard_id,
                        source=source,
                        url=url,
                        error=error_msg,
                        scraped=False
                    )
                    continue
                
                markdown_content = scraped_content["data"]["markdown"]
                
                # Save to vector DB
                results = vector_db.enterWebsiteToKnowledge(
                    page_content=markdown_content,
                    url=url,
                    source_type=source
                )
                
                if results:
                    # Extract vector DB IDs from results
                    vector_db_ids = [r.get("uuid") for r in results if r.get("uuid")]
                    
                    # Save tracking info to MongoDB
                    if existing:
                        # Update existing record
                        self.scraped_url_model.update_scraped_url(
                            dashboard_id, source, url, vector_db_ids
                        )
                    else:
                        # Create new record
                        self.scraped_url_model.create({
                            "dashboardId": dashboard_id,
                            "source": source,
                            "url": url,
                            "scraped": True,
                            "vectorDbIds": vector_db_ids,
                            "error": None
                        })
                    
                    scraped_count += 1
                else:
                    # Vector DB save failed - create entry with error message
                    error_msg = "Failed to save to vector DB"
                    errors.append(f"Failed to save {url} to vector DB")
                    self.scraped_url_model.create_or_update_with_error(
                        dashboard_id=dashboard_id,
                        source=source,
                        url=url,
                        error=error_msg,
                        scraped=False
                    )
                    
            except Exception as e:
                # Exception occurred - create entry with error message
                error_msg = f"Error processing: {str(e)}"
                errors.append(f"Error processing {url}: {str(e)}")
                self.scraped_url_model.create_or_update_with_error(
                    dashboard_id=dashboard_id,
                    source=source,
                    url=url,
                    error=error_msg,
                    scraped=False
                )
        
        return {
            "success": True,
            "scraped_count": scraped_count,
            "skipped_count": skipped_count,
            "errors": errors if errors else None
        }



