import os
from typing import Iterable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI

from app.helpers.Calendar import Calendar as CalendarHelper
from app.helpers.DashboardCompliance import DashboardCompliance
from app.helpers.Database import MongoDB
from app.helpers.News import News as NewsHelper
from app.helpers.SERP import SERPHelper
from app.middleware.Cors import add_cors_middleware
from app.middleware.GlobalErrorHandling import GlobalErrorHandlingMiddleware
from app.models.Dashboard import DashboardModel
from app.services.Documents import DocumentService
from app.services.WebsiteCrawl import WebsiteCrawlService

load_dotenv()

app = FastAPI(
    title="Source HR Engine",
    description="Source HR Engine - Long Running Scheduled Tasks",
    version="1.0.0",
    docs_url="/api-docs",
    redoc_url="/api-redoc",
)

# Middleware
app.add_middleware(GlobalErrorHandlingMiddleware)
add_cors_middleware(app)

scheduler = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1})


def _iter_dashboards(limit: Optional[int] = None) -> Iterable[dict]:
    model = DashboardModel()
    return model.list_dashboards({}, 0, limit) if limit else model.list_dashboards()


def run_news_job(limit: Optional[int] = None) -> None:
    news_helper = NewsHelper()
    for dashboard in _iter_dashboards(limit):
        dashboard_id = str(dashboard.get("_id")) if isinstance(dashboard, dict) else str(getattr(dashboard, "id", ""))
        if not dashboard_id:
            continue
        result = news_helper.retrieve_news(dashboard_id)
        success = result.get("success")
        items = len(result.get("data", []) or []) if success else 0
        print(f"[News] dashboard={dashboard_id} success={success} items={items}")


def run_compliance_job(limit: Optional[int] = None) -> None:
    compliance_helper = DashboardCompliance()
    for dashboard in _iter_dashboards(limit):
        dashboard_id = str(dashboard.get("_id")) if isinstance(dashboard, dict) else str(getattr(dashboard, "id", ""))
        if not dashboard_id:
            continue
        result = compliance_helper.retrieve_law_changes(dashboard_id)
        success = result.get("success")
        entries = len(result.get("data", []) or []) if success else 0
        print(f"[Compliance] dashboard={dashboard_id} success={success} entries={entries}")


def run_calendar_job(limit: Optional[int] = None) -> None:
    calendar_helper = CalendarHelper()
    for dashboard in _iter_dashboards(limit):
        dashboard_id = str(dashboard.get("_id")) if isinstance(dashboard, dict) else str(getattr(dashboard, "id", ""))
        if not dashboard_id:
            continue
        result = calendar_helper.retrieve_calendar(dashboard_id)
        success = result.get("success")
        events = len(result.get("data", []) or []) if success else 0
        print(f"[Calendar] dashboard={dashboard_id} success={success} events={events}")


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

    # Kick off initial runs
    run_news_job()
    run_compliance_job()
    run_calendar_job()

    # Schedule recurring jobs every 23 hours 30 minutes
    scheduler.add_job(run_news_job, "interval", hours=23, minutes=30, id="news_job", replace_existing=True)
    scheduler.add_job(run_compliance_job, "interval", hours=23, minutes=30, id="compliance_job", replace_existing=True)
    scheduler.add_job(run_calendar_job, "interval", hours=23, minutes=30, id="calendar_job", replace_existing=True)
    scheduler.start()

    print("All scheduled tasks initialized successfully")


@app.on_event("shutdown")
def shutdown_event():
    print("Shutting down Source HR Engine...")
    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass


@app.get("/")
def root():
    return {
        "service": "Source HR Engine",
        "status": "running",
        "description": "Long running scheduled tasks engine",
    }


@app.get("/health")
def health_check():
    """Health check endpoint to verify the server is running"""
    db_status = MongoDB.connection_status()
    return {
        "status": "healthy",
        "database": db_status,
        "service": "Source HR Engine",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=3003, reload=True)