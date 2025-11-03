import os
import time
# from apscheduler.triggers.cron import CronTrigger
# from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from starlette.responses import RedirectResponse
from app.helpers.Database import MongoDB
from app.middleware.Cors import add_cors_middleware
from app.middleware.GlobalErrorHandling import GlobalErrorHandlingMiddleware
from app.controllers import Auth, Evaluation, Profile, ChatBot, Dashboard, Common, Quizzes, QuizAttempt, WebsiteCrawl, ChatFeedback, ProactiveMessage, DashboardDocuments
from app.middleware.JWTVerification import jwt_validator
from app.helpers.SERP import SERPHelper
# from app.services.WebsiteCrawl import WebsiteCrawlService
# from app.services.Documents import DocumentService
# from app.DataEnrichment import (
#     fetch_crawlable_urls_from_url,
#     scrape_urls_to_text_files,
#     enrich_textfile_and_store_in_pinecone
# )


load_dotenv()

app = FastAPI(
    title="Source HR Engine",
    description="Source HR Engine API's",
    version='1.0.0',
    docs_url="/api-docs",
    redoc_url="/api-redoc"
)

# Middleware
app.add_middleware(GlobalErrorHandlingMiddleware)
add_cors_middleware(app)

# Routes
app.include_router(Auth.router)
app.include_router(Profile.router,dependencies=[Depends(jwt_validator)])
app.include_router(ChatBot.router,dependencies=[Depends(jwt_validator)])
app.include_router(ProactiveMessage.router,dependencies=[Depends(jwt_validator)])
# app.include_router(Documents.router,dependencies=[Depends(jwt_validator)])
app.include_router(Dashboard.router)
app.include_router(Common.router,dependencies=[Depends(jwt_validator)])
app.include_router(Quizzes.router,dependencies=[Depends(jwt_validator)])
app.include_router(QuizAttempt.router,dependencies=[Depends(jwt_validator)])
app.include_router(WebsiteCrawl.router,dependencies=[Depends(jwt_validator)])
app.include_router(ChatFeedback.router,dependencies=[Depends(jwt_validator)])
app.include_router(DashboardDocuments.router)
app.include_router(Evaluation.router)

@app.on_event("startup")
async def startup_event():
    connection_string = os.getenv("MONGODB_CONNECTION_STRING")
    MongoDB.connect(connection_string)
    # website_crawl=WebsiteCrawlService()
    # website_crawl.schedule_crawler()
    # website_crawl.schedule_scraper()
    serp_helper=SERPHelper()
    serp_helper.schedule_scrape_pending_serp_url()
    # document_service=DocumentService()
    # document_service.schedule_processor()

    print("mongodb connected")
    # --- Optional: Run enrichment pipeline on startup ---
    # from app.DataEnrichment import (
    #     fetch_crawlable_urls_from_url,
    #     scrape_urls_to_text_files,
    #     enrich_textfile_and_store_in_pinecone,
    #     process_all_text_files_and_save_metadata
    # )
    # process_all_text_files_and_save_metadata()
    # crawl_result = fetch_crawlable_urls_from_url("https://www.hrdive.com/", max_depth=2, max_urls=10)
    # if crawl_result["success"]:
    #     file_infos = scrape_urls_to_text_files(crawl_result["data"])
    #     print(file_infos)
    # #     for file_info in file_infos:
    # #         enrich_textfile_and_store_in_pinecone(
    # #             file_info["file_path"],
    # #             file_info["url"],
    # #             pinecone_namespace="my-namespace"
    # #         )
    # else:
    #     print("Crawling failed:", crawl_result["error"])
    # # --- End enrichment pipeline ---

@app.on_event("shutdown") 
async def shutdown_event():
    print("app shutdown")

@app.get("/")
def api_docs():
    return RedirectResponse(url="/api-docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3003, reload=True)