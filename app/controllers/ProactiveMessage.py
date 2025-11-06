import json
from fastapi import APIRouter, HTTPException, Depends, Response, UploadFile, File, Form, Query
from app.middleware.JWTVerification import jwt_validator
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils

from dotenv import load_dotenv

from app.services.ProactiveMessage import ProactiveMessageService
from typing import List
from bson import ObjectId

load_dotenv()


router = APIRouter(prefix="/api/v1/proactiveMessage", tags=["Proactive Message"])

def get_service():
    return ProactiveMessageService() 


@router.get("/generate-proactive-message/{dashboard_id}/{session_id}", response_model=ServerResponse)
def generate_followup_message(dashboard_id:str,session_id:str,service: ProactiveMessageService = Depends(get_service)):  
    try:
        data=service.generateProactiveFollowUpMessage(session_id,dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
