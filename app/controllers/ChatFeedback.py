from fastapi import APIRouter, Depends, HTTPException
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from app.services.ChatFeedback import ChatFeedbackService
from app.schemas.ServerResponse import ServerResponse
from app.schemas.ChatFeedback import CreateChatFeedbackSchema,UpdateChatFeedbackSchema



router = APIRouter(prefix="/api/v1/chat-feedback", tags=["ChatFeedback"], dependencies=[Depends(jwt_validator)])

def get_service():
    return ChatFeedbackService()

@router.post("/create-chat-feedback", response_model=ServerResponse)
def create_chat_feedback(body: CreateChatFeedbackSchema,  service: ChatFeedbackService = Depends(get_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
            user_id = jwt_payload.get("id")
            user_name = jwt_payload.get("fullName")
            data = body.model_dump()
            data = service.create_chat_feedback(data, user_id,user_name)
            return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
            raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})

@router.get("/chat-feedback/{chat_feedback_id}", response_model=ServerResponse)
def get_chat_feedback_by_id(chat_feedback_id:str,service: ChatFeedbackService = Depends(get_service),jwt_payload: dict = Depends(jwt_validator)):  
    try:
        data=service.get_chat_feedback_by_id(chat_feedback_id) 
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get("/get-all-chat-feedbacks", response_model=ServerResponse)
def get_all_chat_feedbacks(page:int = 1, limit:int = 100, service: ChatFeedbackService = Depends(get_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = service.get_all_chat_feedbacks(page,limit)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})
    
@router.put("/update-chat-feedback/{chat_feedback_id}", response_model=ServerResponse)
def update_chat_feedback(chat_feedback_id:str,body:UpdateChatFeedbackSchema,service: ChatFeedbackService = Depends(get_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = service.update_chat_feedback(chat_feedback_id,body.Sentiment,body.Feedback)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})
    
@router.delete("/delete-chat-feedback/{chat_feedback_id}", response_model=ServerResponse)
def delete_chat_feedback(chat_feedback_id:str, service: ChatFeedbackService = Depends(get_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = service.delete_chat_feedback(chat_feedback_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
      raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})




