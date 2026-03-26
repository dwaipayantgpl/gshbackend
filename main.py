# app/main.py
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from piccolo.engine import engine_finder

from admin.endpoints.router import router as admin_router

# from notifications.logic.socket import socket_app
from auth.endpoints.router import router as auth_router
from bookings.endpoints.router import router as bookings_router
from chat.endpoints.router import router as chat_router
from complaint.endpoints.router import router as complains_router
from faq.endpoints.router import router as faq_router
from helper.endpoints.router import router as helper_router
from notifications.endpoints.router import router as notifications_router
from profiles.endpoints.router import router as profiles_router
from ratings.endpoints.router import router as ratings_router
from seeker.endpoints.router import router as seeker_router
from services.endpoints.router import router as services_router

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent


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
    allow_origins=["*"],  # allow all origins
    allow_credentials=False,  # MUST be False when origins=["*"]
    allow_methods=["*"],  # allow all HTTP methods
    allow_headers=["*"],  # allow all headers
)
# app.mount("/ws", socket_app)
# app.mount("/", socket_app)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(profiles_router, prefix="/profiles", tags=["profiles"])
app.include_router(helper_router, prefix="/helper", tags=["helper"])
app.include_router(services_router, prefix="/services", tags=["Services"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(complains_router, prefix="/complaint", tags=["complaint"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(seeker_router, prefix="/seeker", tags=["seeker"])
app.include_router(bookings_router, prefix="/bookings", tags=["bookings"])
app.include_router(
    notifications_router, prefix="/notifications", tags=["notifications"]
)
app.include_router(ratings_router, prefix="/ratings", tags=["ratings"])
app.include_router(faq_router, prefix="/faq", tags=["faq"])
