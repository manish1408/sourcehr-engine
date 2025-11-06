from typing import List
from altair import Field
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from app.middleware.JWTVerification import jwt_validator
from app.services.Dashboard import DashboardService
from app.schemas.Dashboard import DashboardCreate, DashboardUpdate
from app.helpers.Utilities import Utils
from app.schemas.ServerResponse import ServerResponse
from app.helpers.AIImageGeneration import NewsImageGenerator



router = APIRouter(prefix="/api/v1/dashboards", tags=["Dashboards"])

@router.post("/create", response_model=ServerResponse)
def create_dashboard(
    body: DashboardCreate,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = service.create_dashboard(user_id, body)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})

@router.get("/list", response_model=ServerResponse)
def list_dashboards(
    page: int = 1,
    limit: int = 10,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = service.list_dashboards(user_id, page, limit)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})

@router.get("/get/{dashboard_id}", response_model=ServerResponse)
def get_dashboard(
    dashboard_id: str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.get_dashboard(dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})

@router.put("/update/{dashboard_id}", response_model=ServerResponse)
def update_dashboard(
    dashboard_id: str,
    body: DashboardUpdate,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.update_dashboard(dashboard_id, body)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})

@router.delete("/delete/{dashboard_id}", response_model=ServerResponse)
def delete_dashboard(
    dashboard_id: str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.delete_dashboard(dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail=Utils.create_response(None, False, str(e)).dict())

@router.post("/duplicate/{dashboard_id}", response_model=ServerResponse)
def duplicate_dashboard(
    dashboard_id: str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = service.duplicate_dashboard(dashboard_id, user_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail=Utils.create_response(None, False, str(e)).dict())
    

@router.get('/get_law_changes/{dashboard_id}', response_model=ServerResponse)
def retrieve_law_changes(
    dashboard_id: str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.retrieve_law_changes(dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get('/fetch-dashboard-compliance/{dashboard_id}', response_model=ServerResponse)
def fetch_dashboard_compliance(
    dashboard_id:str,
    service: DashboardService = Depends(DashboardService),jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.get_law_changes(dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get('/get_locations', response_model=ServerResponse)
def get_locations(
    service: DashboardService = Depends(DashboardService)):
    try:
        data = service.get_locations()
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    

@router.get('/get_industries', response_model=ServerResponse)
def get_industries(
    service: DashboardService = Depends(DashboardService)):
    try:
        data = service.get_industries()
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get('/get_topics', response_model=ServerResponse)
def get_topics(
    service: DashboardService = Depends(DashboardService)):
    try:
        data = service.get_topics()
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.get('/generate_news/{dashboard_id}', response_model=ServerResponse)
def generate_news(dashboard_id:str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator),
    background_tasks: BackgroundTasks = BackgroundTasks()
    ):
    try:
        background_tasks.add_task(service.generate_news, dashboard_id)
        return Utils.create_response("News generation started", True, "" )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get('/fetch-news/{dashboard_id}', response_model=ServerResponse)
def fetch_news(
    dashboard_id:str,
    service: DashboardService = Depends(DashboardService),jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.fetch_news(dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get('/generate_court_decisions/{dashboard_id}', response_model=ServerResponse)
def generate_court_decisions(
    dashboard_id: str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    try:
        background_tasks.add_task(service.generate_court_decisions, dashboard_id)
        return Utils.create_response("Court decisions generation started", True, "")
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.get('/fetch-court-decisions/{dashboard_id}', response_model=ServerResponse)
def fetch_court_decisions(
    dashboard_id: str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.fetch_court_decisions(dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.get('/generate_legal_calender/{dashboard_id}', response_model=ServerResponse)
def generate_legal_calender(   dashboard_id:str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator),
    background_tasks: BackgroundTasks = BackgroundTasks()
    ):
    try:
        background_tasks.add_task(service.create_legal_calender, dashboard_id)
        return Utils.create_response("Legal calender generation started", True, "" )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get('/get_legal_calender/{dashboard_id}', response_model=ServerResponse)
def get_legal_calender(
    dashboard_id:str,
    service: DashboardService = Depends(DashboardService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.get_legal_calender(dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
# @router.get('/generate_news_image', response_model=ServerResponse)
# def generate_news():
#     try:
#         news_image_generator=NewsImageGenerator()
#         data = news_image_generator.process_article()
#         return Utils.create_response(data["data"], data["success"], data.get("error", "") )
#     except Exception as e:
#         raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})    
    
    



