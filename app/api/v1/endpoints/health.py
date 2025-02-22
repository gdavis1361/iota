"""
Health check endpoint to verify API is running.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    Returns a 200 OK response if the API is running.
    """
    return {"status": "ok"}
