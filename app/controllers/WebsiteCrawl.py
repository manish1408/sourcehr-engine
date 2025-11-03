from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from app.services.WebsiteCrawl import WebsiteCrawlService
from app.dependencies import get_website_crawl_service
from app.schemas.WebsiteCrawl import WebsiteCrawlCreate
from app.helpers.Utilities import Utils, ServerResponse
from app.middleware.JWTVerification import jwt_validator

router = APIRouter(prefix="/api/v1/website-crawl", tags=["Website Crawl"])

@router.post("/create", response_model=ServerResponse)
async def create_website_crawl(
    body: WebsiteCrawlCreate,
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.create_website_crawl(body)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/list", response_model=ServerResponse)
async def list_website_crawls(
    page: int = 1,
    limit: int = 10,
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.list_website_crawls(page, limit)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/get-crawl-by-id/{crawl_id}", response_model=ServerResponse)
async def get_website_crawl(
    crawl_id: str,
    page: int = 1,
    limit: int = 10,
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.get_website_crawl_by_id(crawl_id, page, limit)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=404, detail={"data": None, "error": str(e), "success": False})


@router.put("/update/{crawl_id}", response_model=ServerResponse)
async def update_website_crawl(
    crawl_id: str,
    body: WebsiteCrawlCreate,
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.update_website_crawl(crawl_id, body.model_dump(exclude_unset=True,exclude_none=True))
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.delete("/delete/{crawl_id}", response_model=ServerResponse)
async def delete_website_crawl(
    crawl_id: str,
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.delete_website_crawl(crawl_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=404, detail={"data": None, "error": str(e), "success": False})
    


@router.get("/get-jobs", response_model=ServerResponse)
async def get_jobs(
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.list_jobs()
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=404, detail={"data": None, "error": str(e), "success": False})

@router.get("/fetch-crawlable-urls/{crawl_id}", response_model=ServerResponse)
async def fetch_crawlable_urls(
    crawl_id: str,
    background_tasks: BackgroundTasks,
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        # Wrap the async method for background task
        async def bg_task():
            await service.fetch_crawlable_urls(crawl_id)
        
        background_tasks.add_task(bg_task)
        return Utils.create_response(
            data="Crawlable URLs fetching started",
            success=True,
            error="",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    


@router.get("/start/scraping", response_model=ServerResponse)
async def start_website_crawl(
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.schedule_scraper()
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/get-scraper-status/{crawl_id}", response_model=ServerResponse)
async def get_scraper_status(
    crawl_id: str,
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.get_scraper_status(crawl_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.delete("/clear-crawlable-urls/{crawl_id}", response_model=ServerResponse)
async def clear_crawlable_urls(
    crawl_id: str,
    service: WebsiteCrawlService = Depends(get_website_crawl_service)
):
    try:
        data = await service.clear_crawlable_urls(crawl_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
