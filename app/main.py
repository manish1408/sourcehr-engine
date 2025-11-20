import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI

from app.helpers.Calendar import Calendar as CalendarHelper
from app.helpers.CourtDecisions import CourtDecisions
from app.helpers.DashboardCompliance import DashboardCompliance
from app.helpers.Database import MongoDB
from app.helpers.GeneralNews import GeneralNewsHelper
from app.helpers.News import News as NewsHelper
from app.helpers.SERP import SERPHelper
from app.middleware.Cors import add_cors_middleware
from app.middleware.GlobalErrorHandling import GlobalErrorHandlingMiddleware
from app.models.Dashboard import DashboardModel
from app.models.Queue import QueueModel
from app.schemas.Queue import QueueEntry, QueueStatus, QueueType
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
    court_decisions_helper = CourtDecisions()
    for dashboard in _iter_dashboards(limit):
        dashboard_id = str(dashboard.get("_id")) if isinstance(dashboard, dict) else str(getattr(dashboard, "id", ""))
        if not dashboard_id:
            continue
        result = court_decisions_helper.retrieve_court_decisions(dashboard_id)
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


def run_general_news_job() -> None:
    helper = GeneralNewsHelper()
    result = helper.generate_daily_summary()
    summary = result.get("data")
    success = result.get("success")
    if summary and summary.articles:
        print(
            f"[GeneralNews] date={summary.summaryDate} success={success} "
            f"articles={len(summary.articles)}"
        )
        for article in summary.articles:
            print(f"  - {article.title}: {article.description}")
    else:
        print(f"[GeneralNews] success={success}, no articles generated")


def _process_queue_entry(entry: QueueEntry) -> tuple[str, bool, Optional[str]]:
    """Process a single queue entry. Returns (entry_id, success, error_message)."""
    queue_model = QueueModel()
    dashboard_id = entry.dashboardId
    entry_id = entry.id
    print(f"[Queue] Processing entry {entry_id} type={entry.type} dashboard={dashboard_id}")

    try:
        if entry.type == QueueType.NEWS:
            NewsHelper().retrieve_news(dashboard_id)
        elif entry.type == QueueType.CALENDAR:
            CalendarHelper().retrieve_calendar(dashboard_id)
        elif entry.type == QueueType.COMPLIANCE:
            CourtDecisions().retrieve_court_decisions(dashboard_id)
        elif entry.type == QueueType.LAW_CHANGE:
            DashboardCompliance().retrieve_law_changes(dashboard_id)
        else:
            raise ValueError(f"Unsupported queue type: {entry.type}")

        queue_model.mark_status(entry_id, QueueStatus.COMPLETED)
        print(f"[Queue] Completed entry {entry_id}")
        return (str(entry_id), True, None)
    except Exception as exc:  # pylint: disable=broad-except
        queue_model.mark_status(entry_id, QueueStatus.FAILED, str(exc))
        print(f"[Queue] Failed entry {entry_id}: {exc}")
        return (str(entry_id), False, str(exc))


def run_queue_job() -> None:
    """Process all pending queue entries in parallel without blocking the main thread."""
    queue_model = QueueModel()
    entries = queue_model.claim_all_pending()
    
    if not entries:
        print("[Queue] No pending entries")
        return

    print(f"[Queue] Found {len(entries)} pending entries, processing in parallel...")
    
    # Process entries in parallel using ThreadPoolExecutor
    # Using max_workers to limit concurrent processing (adjust as needed)
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        future_to_entry = {
            executor.submit(_process_queue_entry, entry): entry 
            for entry in entries
        }
        
        # Wait for all tasks to complete and collect results
        completed = 0
        failed = 0
        for future in as_completed(future_to_entry):
            entry = future_to_entry[future]
            try:
                entry_id, success, error = future.result()
                if success:
                    completed += 1
                else:
                    failed += 1
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[Queue] Unexpected error processing entry {entry.id}: {exc}")
                failed += 1
    
    print(f"[Queue] Batch processed {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}: "
          f"{completed} completed, {failed} failed")


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

    scheduler.add_job(
        run_news_job,
        trigger="interval",
        hours=23.5,
        id="news_job",
        replace_existing=True,
    )
    scheduler.add_job(
        run_compliance_job,
        trigger="interval",
        hours=23.5,
        id="compliance_job",
        replace_existing=True,
    )
    scheduler.add_job(
        run_calendar_job,
        trigger="interval",
        hours=23.5,
        id="calendar_job",
        replace_existing=True,
    )
    scheduler.add_job(
        run_general_news_job,
        trigger="interval",
        hours=24,
        id="general_news_job",
        replace_existing=True,
    )
    scheduler.add_job(
        run_queue_job,
        trigger="interval",
        minutes=1,
        id="queue_job",
        replace_existing=True,
    )
    
    print("General news job scheduled to run every 24 hours")
    print("Queue job scheduled to run every minute")

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