from fastapi import APIRouter

from app.api import script
from app.api import asset

api_router = APIRouter()
api_router.include_router(script.router, tags=["script"])
api_router.include_router(asset.router, tags=["asset"])

__all__ = ["api_router"]
