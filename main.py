# app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from piccolo.engine import engine_finder

from auth.endpoints.router import router as auth_router
from profiles.endpoints.router import router as profiles_router
from helper.endpoints.router import router as helper_router
from services.endpoints.router import router as services_router
from admin.endpoints.router import router as admin_router 

from fastapi import FastAPI

app = FastAPI()
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = engine_finder()
    await engine.start_connection_pool()
    try:
        yield
    finally:
        await engine.close_connection_pool()

app = FastAPI(
    title="gshbe API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/swagger",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow all origins
    allow_credentials=False,      # MUST be False when origins=["*"]
    allow_methods=["*"],          # allow all HTTP methods
    allow_headers=["*"],          # allow all headers
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
app.include_router(helper_router, prefix="/helper", tags=["helper"])
app.include_router(services_router, prefix="/services", tags=["Services"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
