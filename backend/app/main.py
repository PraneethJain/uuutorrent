# --- FILE START: ./backend/app/main.py ---
import asyncio
import logging  # Use logging module
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.api import api_router
from app.db.base import create_tables, AsyncSessionLocal  # Import AsyncSessionLocal
from app.core.config import settings

# Import services needed by workers
from app.services.anilist_service import anilist_service
from app.services.nyaa_service import nyaa_service
from app.services.qbittorrent_service import qbittorrent_service
from app.workers import (  # Import worker functions
    handle_download_request,
    handle_torrent_found,
    download_request_queue,
    torrent_found_queue,
)

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


# Define CORS origins allowed
origins = ["*"]

app = FastAPI(
    title="UUUTorrent Backend",
    description="API backend for managing torrents via qBittorrent, integrated with Anilist watchlist.",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

background_tasks = set()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(
    app, endpoint="/api/metrics", tags=["Monitoring"]
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/api/health", tags=["Monitoring"])
async def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    log.info("Application startup...")
    log.info("Creating database tables (if they don't exist)...")
    try:
        await create_tables()
        log.info("Database tables checked/created.")
    except Exception as e:
        log.exception("FATAL: Failed to create database tables.")

    log.info("Starting event queue workers...")
    try:
        # *** PASS SPECIFIC QUEUES TO WORKERS ***
        task1 = asyncio.create_task(
            handle_download_request(
                request_queue=download_request_queue,  # Input queue
                found_queue=torrent_found_queue,  # Output queue
                anilist_svc=anilist_service,
                nyaa_svc=nyaa_service,
                session_factory=AsyncSessionLocal,
            )
        )
        task2 = asyncio.create_task(
            handle_torrent_found(
                found_queue=torrent_found_queue,  # Input queue
                qbt_svc=qbittorrent_service,
                session_factory=AsyncSessionLocal,
            )
        )
        # *** END PASSING QUEUES ***
        background_tasks.add(task1)
        background_tasks.add(task2)
        task1.add_done_callback(background_tasks.discard)
        task2.add_done_callback(background_tasks.discard)
        log.info(
            f"Event queue workers scheduled (Tasks: {task1.get_name()}, {task2.get_name()})."
        )
    except Exception as e:
        log.exception("FATAL: Failed to start event queue workers.")

    # *** Pass the *initial* queue needed by endpoint to app state ***
    app.state.download_request_queue = download_request_queue
    # (torrent_found_queue is only needed between workers, not endpoint)
    log.info("Application startup complete.")


@app.on_event("shutdown")
async def on_shutdown():
    # ... (shutdown logic remains the same) ...
    log.info("Application shutdown...")
    log.info("Stopping event queue workers...")
    for task in list(background_tasks):
        if not task.done():
            task.cancel()
            log.info(f"Cancelled task {task.get_name()}")
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    log.info("Event queue workers stopped.")
    log.info("Application shutdown complete.")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to UUUTorrent Backend API. See /api/docs for details."}


# NOTE: uvicorn running logic is usually handled outside main.py
# Example: uvicorn app.main:app --host 0.0.0.0 --port 8000
# --- FILE END: ./backend/app/main.py ---
