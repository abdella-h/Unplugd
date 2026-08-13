from fastapi import FastAPI

import app.models.users
from app.api.endpoints import router
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(router)
