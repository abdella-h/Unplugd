from fastapi import APIRouter

from app.api.endpoints import alerts, stream

router = APIRouter()
router.include_router(stream.router)
router.include_router(alerts.router)
