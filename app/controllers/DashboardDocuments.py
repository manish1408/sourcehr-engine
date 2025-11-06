from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.schemas.DashboardDocumentsSchema import FinalDocSchema, GetDocResponse
from app.services.DashboardDocuments import DDService
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils

router = APIRouter(prefix="/api/v1/DashboardDocuments", tags=["Dashboard Documents"])


def get_dd_service():
    return DDService()

# response_model=GetDocResponse
@router.get("/all-docs", response_model=GetDocResponse)
def get_all_documents(service: DDService = Depends(get_dd_service)):
    try:
        data = service.get_all_laws()
        return Utils.create_response(data=data["data"],success=data["success"],error=data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400,detail={"data": None, "error": str(e), "success": False})
