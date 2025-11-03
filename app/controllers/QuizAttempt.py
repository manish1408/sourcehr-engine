from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.QuizAttempts import QuizAttemptService
from app.dependencies import get_quiz_attempt_service
from app.schemas.QuizAttempt import  AnswerSubmission
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import  jwt_validator
from app.schemas.ServerResponse import ServerResponse

router = APIRouter(prefix="/api/v1/quiz-attempts", tags=["QuizAttempts"])

@router.post("/create/{quiz_id}", response_model=ServerResponse)
async def create_quiz_attempt(
    quiz_id,
    service: QuizAttemptService = Depends(get_quiz_attempt_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = await service.create_attempt(quiz_id,user_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.get("/list", response_model=ServerResponse)
async def get_quiz_attempts(
    page: int = 1,
    limit: int = int,
    quiz_id: Optional[str] = None,
    user_id: Optional[str] = None,
    service: QuizAttemptService = Depends(get_quiz_attempt_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        filters = {}
        if quiz_id:
            filters["quizId"] = quiz_id
        if user_id:
            filters["userId"] = user_id

        data = await service.get_attempts(filters, page, limit)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.post("/submit-answer/{attempt_id}", response_model=ServerResponse)
async def submit_answer_to_attempt(
    attempt_id: str,
    answer: AnswerSubmission,
    service: QuizAttemptService = Depends(get_quiz_attempt_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.push_answer(attempt_id, answer)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.post("/submit-quiz/{attempt_id}/{quiz_id}", response_model=ServerResponse)
async def submit_quiz_attempt(
    attempt_id: str,
    quiz_id: str,
    service: QuizAttemptService = Depends(get_quiz_attempt_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.submit_quiz(attempt_id, quiz_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.patch("/update-answer/{attempt_id}", response_model=ServerResponse)
async def update_quiz_attempt_answer(
    attempt_id: str,
    body: AnswerSubmission,
    service: QuizAttemptService = Depends(get_quiz_attempt_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.update_selected_answers(attempt_id, body)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "data": None,
                "error": str(e),
                "success": False
            }
        )


@router.delete("/delete/{attempt_id}", response_model=ServerResponse)
async def delete_quiz_attempt(
    attempt_id: str,
    service: QuizAttemptService = Depends(get_quiz_attempt_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.delete_attempt(attempt_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get("/leaderboard", response_model=ServerResponse)
async def get_leaderboard(
    skip: int = 0,
    limit: int = 10,
    service: QuizAttemptService = Depends(get_quiz_attempt_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.get_leaderboard(skip=skip, limit=limit)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/user-submission{quiz_id}", response_model=ServerResponse)
async def get_user_submission(
    quiz_id: str,
    service: QuizAttemptService = Depends(get_quiz_attempt_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = await service.get_user_submission(user_id,quiz_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=404, detail={"data": None, "error": str(e), "success": False})
