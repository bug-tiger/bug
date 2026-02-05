from fastapi import APIRouter

from app.api import script

api_router = APIRouter()
api_router.include_router(script.router, tags=["script"])

__all__ = ["api_router"]
