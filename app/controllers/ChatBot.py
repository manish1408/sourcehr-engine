import json
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile,BackgroundTasks
from fastapi.responses import StreamingResponse
from app.middleware.JWTVerification import jwt_validator
from app.services.Chat import ChatService
from app.schemas.ServerResponse import ServerResponse
from app.schemas.Knowledge import CreateKnowledgeSchema,ChatWithKnowledgeSchema
from app.helpers.Utilities import Utils
import shutil
import os
from pydantic import BaseModel, Field
from typing import Literal
from app.schemas.ChatSession import RegenerateStreamRequestSchema
import asyncio
from app.dependencies import get_chat_service

from dotenv import load_dotenv

load_dotenv()


router = APIRouter(prefix="/api/v1/chat", tags=["Chat"], dependencies=[Depends(jwt_validator)]) 

@router.post("/session/create/{dashboard_id}", response_model=ServerResponse)
async def create_session(dashboard_id: str,service: ChatService = Depends(get_chat_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        user_id = jwt_payload.get("id")
        result = await service.create_session(user_id,dashboard_id)
        return Utils.create_response(result["data"], result["success"], result.get("error", ""))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )
        
@router.post("/chat/stream/{session_id}")
async def chat_with_stream(
    session_id: str,
    # knowledge_id: str,
    body: ChatWithKnowledgeSchema,
    background_tasks: BackgroundTasks,
    service: ChatService = Depends(get_chat_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        user_id = jwt_payload.get("id")

        # Generator that yields token chunks
        async def stream_tokens():
            async for item in service.chat_stream(body.question, session_id):
                if "token" in item:
                    yield item["token"]
                elif "error" in item:
                    yield f"\n[Error]: {item['error']}\n"

        # Background task to update title, after stream is done
        async def wrap_with_title_generation():
            full_resp = ""
            async for item in service.chat_stream(body.question, session_id):
                if "token" in item:
                    full_resp += item["token"]
                    response = {
                        "message": item["token"],
                        "citations": item.get("citations", [])
                    }
                    if item.get("messageId"):
                        response["messageId"] = item["messageId"]
                    yield json.dumps(response)
                elif "error" in item:
                    response = {"error": item["error"]}
                    yield json.dumps(response)
                    return
            
            # Schedule the async background task
            async def bg_task():
                await service.generate_session_title(session_id, body.question, full_resp)
            
            background_tasks.add_task(bg_task)

        return StreamingResponse(
            wrap_with_title_generation(),
            media_type="text/plain"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    

@router.post("/chat-no-stream/{session_id}", response_model=ServerResponse)
async def chat_no_stream(session_id: str,body: ChatWithKnowledgeSchema, service: ChatService = Depends(get_chat_service)):  
    try:
        # Collect all chunks from the async generator
        full_response = ""
        citations = []
        message_id = None
        error = None
        
        async for chunk in service.chat_no_stream(body.question, session_id):
            if isinstance(chunk, dict):
                if "delta" in chunk:
                    full_response += chunk["delta"]
                elif "success" in chunk:
                    if chunk["success"]:
                        citations = chunk.get("data", {}).get("citations", [])
                        message_id = chunk.get("data", {}).get("_id")
                    else:
                        error = chunk.get("error", "Unknown error")
                elif "error" in chunk:
                    error = chunk["error"]
        
        if error:
            return Utils.create_response(None, False, error)
        
        return Utils.create_response({
            "response": full_response,
            "citations": citations,
            "_id": message_id
        }, True, "")
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})

@router.post("/chat-stream/{session_id}")
async def chat_stream(
    session_id: str,
    body: ChatWithKnowledgeSchema,
    service: ChatService = Depends(get_chat_service)
):
    try:
        async def stream_generator():
            # print(f"Starting stream generator for question: '{body.question}'")
            chunk_count = 0
            async for chunk in service.chat_no_stream(body.question, session_id):
                chunk_count += 1
                # print(f"Controller received chunk {chunk_count}: {type(chunk)} - {chunk}")
                
                # If chunk is a dict (final yield from service)
                if isinstance(chunk, dict):
                    if "delta" in chunk:
                        # Extract the actual text chunk and yield as JSON matching /chat/stream format
                        # print(f"Yielding delta: '{chunk['delta']}'")
                        response = {
                            "message": chunk["delta"],
                            "citations": []
                        }
                        yield json.dumps(response) + "\n"
                    elif "error" in chunk:
                        # print(f"Yielding error: {chunk['error']}")
                        response = {"error": chunk["error"]}
                        yield json.dumps(response) + "\n"
                    elif "success" in chunk and not chunk["success"]:
                        # print(f"Yielding success error: {chunk.get('error', 'Unknown error')}")
                        response = {"error": chunk.get('error', 'Unknown error')}
                        yield json.dumps(response) + "\n"
                    elif "success" in chunk and chunk["success"]:
                        # Final success response from service
                        # print(f"Yielding final success response")
                        # For final response, include messageId if available
                        final_response = {
                            "message": "",
                            "citations": chunk.get("data", {}).get("citations", []),
                            "messageId": chunk.get("data", {}).get("_id")
                        }
                        yield json.dumps(final_response) + "\n"
                    else:
                        # Skip other dict responses
                        # print(f"Skipping dict chunk: {chunk}")
                        continue
                else:
                    # Direct text chunk - yield as JSON matching /chat/stream format
                    # print(f"Yielding direct text: '{chunk}'")
                    response = {
                        "message": chunk,
                        "citations": []
                    }
                    yield json.dumps(response) + "\n"
            
            # print(f"Stream generator completed. Total chunks processed: {chunk_count}")
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/plain"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={"data": None, "error": str(e), "success": False}
        )

@router.get("/session/{dashboard_id}/{session_id}", response_model=ServerResponse)
async def get_session_by_id(dashboard_id: str,session_id: str,page:int=1,limit:int=5, service: ChatService = Depends(get_chat_service),jwt_payload: dict = Depends(jwt_validator)):  
    try:
        data = await service.get_session(dashboard_id,session_id) 
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.get("/get-all-sessions/{dashboard_id}", response_model=ServerResponse)
async def get_all_sessions(dashboard_id: str,page:int=1,limit:int=10, service: ChatService = Depends(get_chat_service),jwt_payload: dict = Depends(jwt_validator)):  
    try:
        data = await service.get_all_sessions(dashboard_id,page,limit) 
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
@router.delete("/session/delete/{session_id}", response_model=ServerResponse)
async def delete_session(session_id: str, service: ChatService = Depends(get_chat_service),jwt_payload: dict = Depends(jwt_validator)):
    try:
        data = await service.delete_session(session_id)
        return Utils.create_response(data["data"], data["success"], data.get("error", ""))
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    
    
@router.post("/chat/regenerate/stream/{session_id}")
async def regenerate_response_stream(
    session_id: str,
    body: RegenerateStreamRequestSchema,
    service: ChatService = Depends(get_chat_service),
    jwt_payload: dict = Depends(jwt_validator)
):
    try:
        async def stream():
            async for item in service.regenerate_response_stream(session_id,body.ai_message_id):
                yield json.dumps(item) + '\n'
        return StreamingResponse(stream(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=400, detail={"data": None, "error": str(e), "success": False})
    




