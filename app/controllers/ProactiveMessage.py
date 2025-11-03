import json
from fastapi import APIRouter, HTTPException, Depends, Response, UploadFile, File, Form, Query
from app.middleware.JWTVerification import jwt_validator
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils

from dotenv import load_dotenv

from app.services.ProactiveMessage import ProactiveMessageService
from app.dependencies import get_proactive_message_service
from typing import List
from bson import ObjectId

load_dotenv()


router = APIRouter(prefix="/api/v1/proactiveMessage", tags=["Proactive Message"])



@router.get("/generate-proactive-message/{dashboard_id}/{session_id}", response_model=ServerResponse)
async def generate_followup_message(dashboard_id:str,session_id:str,service: ProactiveMessageService = Depends(get_proactive_message_service)):  
    try:
        data = await service.generateProactiveFollowUpMessage(session_id,dashboard_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
