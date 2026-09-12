from fastapi import APIRouter

from . import datacenters, devices

router = APIRouter()
router.include_router(datacenters.router, tags=["datacenters"])
router.include_router(devices.router, tags=["devices"])
