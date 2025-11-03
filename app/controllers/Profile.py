from fastapi import APIRouter, Form, HTTPException, UploadFile, File, Depends,Header
from fastapi.responses import JSONResponse
from app.middleware.JWTVerification import jwt_validator
from app.services.Profile import ProfileService
from app.dependencies import get_profile_service
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
from app.schemas.User import UpdateUserSchema

router = APIRouter(prefix="/api/v1/profile", tags=["Profile"])

    
@router.put("/update-user-info", response_model=ServerResponse)
async def update_user_info(
    body: UpdateUserSchema,
    service: ProfileService = Depends(get_profile_service),
    jwt_payload: dict = Depends(jwt_validator)

):
    try:
        user_id = jwt_payload.get("id")
        data = await service.update_user_info(user_id,body.model_dump(exclude_unset=True))
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False}) 
    
@router.get("/me", response_model=ServerResponse)
async def get_me(
    authorization: str = Header(..., description="Bearer <token>"),
    profile_service: ProfileService = Depends(get_profile_service)
):
    try:
        if not authorization.startswith("Bearer "):
            raise Exception("Invalid Authorization header format")
        
        token = authorization.split(" ")[1]
        result = await profile_service.get_current_user(token)
        return Utils.create_response(result["data"], result["success"], result.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False}) 
    

@router.post("/save-onboarding/{onboardingStep}",response_model=ServerResponse)
async def save_onboarding(onboardingStep:int,profile_service: ProfileService = Depends(get_profile_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        user_id = jwt_payload.get("id")
        data = await profile_service.save_onboarding(user_id,onboardingStep)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False}) 
