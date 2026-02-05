from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os

from app.routers import video
from app.api import api_router

load_dotenv()

app = FastAPI(
    title="Blog to YouTube Video Converter",
    description="블로그 글을 유튜브 동영상으로 변환하는 앱",
    version="1.0.0"
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/output", StaticFiles(directory="output"), name="output")
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(video.router, prefix="/api", tags=["video"])
app.include_router(api_router, tags=["script"])


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """메인 페이지"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}
