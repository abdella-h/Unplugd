from fastapi import APIRouter

from . import login, logout, me, operators, refresh, setup, setup_status

router = APIRouter()

router.include_router(setup_status.router, tags=["setup"])
router.include_router(setup.router, tags=["setup"])
router.include_router(operators.router, tags=["operators"])
router.include_router(login.router, tags=["auth"])
router.include_router(me.router, tags=["auth"])
router.include_router(refresh.router, tags=["auth"])
router.include_router(logout.router, tags=["auth"])
