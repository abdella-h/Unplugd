from fastapi import APIRouter

from . import datacenters

router = APIRouter()
router.include_router(datacenters.router, tags=["datacenters"])
