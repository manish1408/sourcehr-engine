import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException,BackgroundTasks
from fastapi import Depends
from typing import List
from app.helpers.Utilities import Utils
from app.middleware.JWTVerification import jwt_validator
from app.schemas.ServerResponse import ServerResponse
from app.services.Evaluation import EvaluationService
from app.dependencies import get_evaluation_service


router = APIRouter(prefix="/api/v1/evaluation", tags=["Evaluation"])

@router.post("/upload-csv-dataset",response_model=ServerResponse)
async def upload_csv_dataset_api(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(...),
    input_keys: List[str] = Form(...),
    output_keys: List[str] = Form(...),
    service: EvaluationService = Depends(get_evaluation_service),
    jwt_payload: dict = Depends(jwt_validator)

):
    try:
        data = await service.upload_csv_dataset(
            file=file,
            name=name,
            description=description,
            input_keys=input_keys,
            output_keys=output_keys
        )
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})


@router.delete("/delete-dataset/{dataset_id}", response_model=ServerResponse)
async def delete_evaluation_dataset(
    dataset_id: str,
    service: EvaluationService = Depends(get_evaluation_service),jwt_payload: dict = Depends(jwt_validator)
):
    try:
        data = await service.delete_evaluation_dataset(dataset_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.get("/evaluate/{dataset_id}",response_model=ServerResponse)
async def evaluate_dataset_api(dataset_id: str,background_tasks: BackgroundTasks,service: EvaluationService = Depends(get_evaluation_service),jwt_payload: dict = Depends(jwt_validator)
):
    try:
        # Wrap the async method in a lambda for background task
        async def bg_task():
            await service.evaluate_langsmith_dataset(dataset_id)
        
        background_tasks.add_task(bg_task)
        return Utils.create_response(
            data="Evaluation started",
            success=True,
            error="",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})
    

@router.get("/get-evaluation/{evaluation_id}", response_model=ServerResponse)
async def get_evaluation_by_id(
    evaluation_id: str,
    service: EvaluationService = Depends(get_evaluation_service),jwt_payload: dict = Depends(jwt_validator)

):
    try:
        data = await service.get_evaluation(evaluation_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )


@router.get("/get-all-evaluations", response_model=ServerResponse)
async def get_all_evaluations(
    page: int = 1,
    limit: int = 10,
    service: EvaluationService = Depends(get_evaluation_service),jwt_payload: dict = Depends(jwt_validator)

):
    try:
        data = await service.get_all_evaluations(page, limit)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )
