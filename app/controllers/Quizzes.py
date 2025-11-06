from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.Quizzes import QuizService
from app.schemas.Quizzes import QuestionCreate, QuestionUpdate, QuizCreate, Quiz,QuizUpdate
from app.helpers.Utilities import Utils,ServerResponse
from app.middleware.JWTVerification import jwt_validator
from app.services.Quizzes import QuizService

router = APIRouter(prefix="/api/v1/quiz", tags=["Quizzes"])


@router.post("/create", response_model=ServerResponse)
def create_quiz(
    body: QuizCreate,
    service: QuizService = Depends(QuizService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = service.create_quiz(body,user_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/list", response_model=ServerResponse)
def list_quizzes(
    page: int=1,
    limit: int = 10,
    service: QuizService = Depends(QuizService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload["id"]
        data = service.list_quizzes(page, limit,user_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.get("/{quiz_id}", response_model=ServerResponse)
def get_quiz(
    quiz_id: str,
    service: QuizService = Depends(QuizService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.get_quiz_by_id(quiz_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=404, detail={"data": None, "error": str(e), "success": False})


@router.put("/update/{quiz_id}", response_model=ServerResponse)
def update_quiz(
    quiz_id: str,
    body: QuizUpdate,
    service: QuizService = Depends(QuizService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data=service.update_quiz(quiz_id, body.model_dump(exclude_unset=True))
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})


@router.delete("/delete/{quiz_id}", response_model=ServerResponse)
def delete_quiz(
    quiz_id: str,
    service: QuizService = Depends(QuizService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        service.delete_quiz(quiz_id)
        return Utils.create_response({"quiz_id": quiz_id}, True, "Quiz deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=404, detail={"data": None, "error": str(e), "success": False})
    
    
@router.post("/add/{quiz_id}", response_model=ServerResponse)
def add_question(
    quiz_id: str,
    body: QuestionCreate,
    service: QuizService = Depends(QuizService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.add_question(quiz_id, body)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.put("/update/{quiz_id}/{question_id}", response_model=ServerResponse)
def update_question(
    quiz_id: str,
    question_id: str,
    body: QuestionUpdate,
    service: QuizService = Depends(QuizService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.update_question(quiz_id, question_id, body)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.delete("/remove/{quiz_id}/{question_id}", response_model=ServerResponse)
def remove_question(
    quiz_id: str,
    question_id: str,
    service: QuizService = Depends(QuizService),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = service.remove_question(quiz_id, question_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )