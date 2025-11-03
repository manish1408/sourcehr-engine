import json
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from app.middleware.JWTVerification import jwt_validator
from app.services.Documents import DocumentService
from app.dependencies import get_document_service
from app.schemas.ServerResponse import ServerResponse
from app.helpers.Utilities import Utils
import shutil
import os


from dotenv import load_dotenv

load_dotenv()


router = APIRouter(prefix="/api/v1/documents", tags=["Documents"], dependencies=[Depends(jwt_validator)])


@router.post("/upload-to-knowledge", response_model=ServerResponse)
async def upload_to_knowledge(
    files: list[UploadFile] = File(...),
    sourceType: str = Form(...),
    service: DocumentService = Depends(get_document_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    results = []
    errors = []
    for file in files:
        pdf_path = None
        try:
            pdf_path = Utils.generate_hex_string() + file.filename
            pdf_path = pdf_path.replace(" ", "_")
            with open(pdf_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            data = await service.upload_and_add_document(pdf_path, file.filename, sourceType)
            results.append({
                "filename": file.filename,
                "data": data["data"],
                "success": data["success"],
                "error": data.get("error", "")
            })
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
        finally:
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
    # Mixed file-type support with partial success handling
    overall_success = any(r["success"] for r in results)
    error_message = "" if overall_success else "; ".join([e.get("error", "Unknown error") for e in errors]) or "All uploads failed"
    return Utils.create_response({
        "results": results,
        "errors": errors
    }, overall_success, error_message)
    
    
@router.get("/get-document{document_id}", response_model=ServerResponse)
async def get_document(document_id:str, service: DocumentService = Depends(get_document_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = await service.get_document_by_id(document_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})
    

    
@router.get("/get-all-documents", response_model=ServerResponse)
async def get_all_document_from_knowledge(page:int = 1, limit:int = 100, service:DocumentService = Depends(get_document_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = await service.get_all_documents(page,limit)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})
    
@router.delete("/delete-document/{document_id}", response_model=ServerResponse)
async def delete_document_from_knowledge(document_id:str, service: DocumentService = Depends(get_document_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = await service.delete_document(document_id)
        return Utils.create_response(data["data"],data["success"],data.get("error", "") )
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error":str(e),"success": False})

