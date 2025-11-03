from fastapi import APIRouter, Depends, HTTPException
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from app.services.ChatFeedback import ChatFeedbackService
from app.schemas.ServerResponse import ServerResponse
from app.schemas.ChatFeedback import CreateChatFeedbackSchema,UpdateChatFeedbackSchema
from app.dependencies import get_chat_feedback_service



router = APIRouter(prefix="/api/v1/chat-feedback", tags=["ChatFeedback"], dependencies=[Depends(jwt_validator)])

@router.post("/create-chat-feedback", response_model=ServerResponse)
async def create_chat_feedback(body: CreateChatFeedbackSchema,  service: ChatFeedbackService = Depends(get_chat_feedback_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
            user_id = jwt_payload.get("id")
            user_name = jwt_payload.get("fullName")
            data = body.model_dump()
            data = await service.create_chat_feedback(data, user_id,user_name)
            return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
            raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})

@router.get("/chat-feedback/{chat_feedback_id}", response_model=ServerResponse)
async def get_chat_feedback_by_id(chat_feedback_id:str,service: ChatFeedbackService = Depends(get_chat_feedback_service),jwt_payload: dict = Depends(jwt_validator)):  
    try:
        data = await service.get_chat_feedback_by_id(chat_feedback_id) 
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get("/get-all-chat-feedbacks", response_model=ServerResponse)
async def get_all_chat_feedbacks(page:int = 1, limit:int = 100, service: ChatFeedbackService = Depends(get_chat_feedback_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = await service.get_all_chat_feedbacks(page,limit)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})
    
@router.put("/update-chat-feedback/{chat_feedback_id}", response_model=ServerResponse)
async def update_chat_feedback(chat_feedback_id:str,body:UpdateChatFeedbackSchema,service: ChatFeedbackService = Depends(get_chat_feedback_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = await service.update_chat_feedback(chat_feedback_id,body.Sentiment,body.Feedback)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})
    
@router.delete("/delete-chat-feedback/{chat_feedback_id}", response_model=ServerResponse)
async def delete_chat_feedback(chat_feedback_id:str, service: ChatFeedbackService = Depends(get_chat_feedback_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = await service.delete_chat_feedback(chat_feedback_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
      raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})




