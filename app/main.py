from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from dotenv import load_dotenv
import os

from app.api import api_router

load_dotenv()

app = FastAPI(
    title="Blog2Tube - Asset Kit Generator",
    description="블로그 글을 Vrew/CapCut용 Asset Kit으로 변환",
    version="2.0.0"
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")

# Include routers
app.include_router(api_router, tags=["asset"])


@app.get("/", response_class=HTMLResponse)
async def home():
    """메인 페이지"""
    return FileResponse("static/index.html")


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}
