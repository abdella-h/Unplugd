import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.models
from app.api.endpoints import router
from app.core.broker import DashboardConsumer, hub
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer = DashboardConsumer(hub, asyncio.get_running_loop())
    consumer.start()
    yield
    consumer.stop()


app = FastAPI(lifespan=lifespan)
app.include_router(router)
