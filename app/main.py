import os
from dotenv import load_dotenv
from fastapi import FastAPI
from app.helpers.Database import MongoDB
from app.middleware.Cors import add_cors_middleware
from app.middleware.GlobalErrorHandling import GlobalErrorHandlingMiddleware
from app.helpers.SERP import SERPHelper
from app.services.WebsiteCrawl import WebsiteCrawlService
from app.services.Documents import DocumentService


load_dotenv()

app = FastAPI(
    title="Source HR Engine",
    description="Source HR Engine - Long Running Scheduled Tasks",
    version='1.0.0',
    docs_url="/api-docs",
    redoc_url="/api-redoc"
)

# Middleware
app.add_middleware(GlobalErrorHandlingMiddleware)
add_cors_middleware(app)

@app.on_event("startup")
def startup_event():
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    MongoDB.connect(connection_string)
    print("MongoDB connected")
    
    # Initialize and schedule all background tasks
    print("Initializing scheduled tasks...")
    
    # Schedule SERP URL scraper
    serp_helper = SERPHelper()
    serp_result = serp_helper.schedule_scrape_pending_serp_url()
    print(f"SERP scraper: {serp_result.get('data', 'scheduled')}")
    
    # Schedule Website Crawl tasks
    website_crawl = WebsiteCrawlService()
    crawler_result = website_crawl.schedule_crawler()
    print(f"Website crawler: {crawler_result.get('data', 'scheduled')}")
    scraper_result = website_crawl.schedule_scraper()
    print(f"Website scraper: {scraper_result.get('data', 'scheduled')}")
    
    # Schedule Document processor
    document_service = DocumentService()
    doc_result = document_service.schedule_processor()
    print(f"Document processor: {doc_result.get('data', 'scheduled')}")
    
    print("All scheduled tasks initialized successfully")

@app.on_event("shutdown") 
def shutdown_event():
    print("Shutting down Source HR Engine...")

@app.get("/")
def root():
    return {
        "service": "Source HR Engine",
        "status": "running",
        "description": "Long running scheduled tasks engine"
    }

@app.get("/health")
def health_check():
    """Health check endpoint to verify the server is running"""
    db_status = MongoDB.connection_status()
    return {
        "status": "healthy",
        "database": db_status,
        "service": "Source HR Engine"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3003, reload=True)