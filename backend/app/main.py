from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.api import api_router

from app.db.base import create_tables

# Define CORS origins allowed (adjust for your TUI's environment)
origins = [
    # Allow local development if TUI runs on different port/origin
    # "http://localhost",
    # "http://localhost:xxxx", # Port where TUI might make requests if web-based
    # Add specific origins for deployed TUI if applicable
    "*"  # Allow all for simplicity during dev - BE CAREFUL IN PRODUCTION
]


app = FastAPI(
    title="UUUTorrent Backend",
    description="API backend for managing torrents via qBittorrent, integrated with Anilist watchlist.",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",  # Standard OpenAPI path
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc",  # ReDoc UI
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Prometheus monitoring
Instrumentator().instrument(app).expose(
    app, endpoint="/api/metrics", tags=["Monitoring"]
)

# Include API routers under /api/v1 prefix
app.include_router(api_router, prefix="/api/v1")


@app.get("/api/health", tags=["Monitoring"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    print("Creating database tables (if they don't exist)...")
    await create_tables()
    print("Database tables checked/created.")


# Custom exception handler for validation errors for cleaner responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


# Add more global exception handlers if needed


# Example placeholder for root path
@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to UUUTorrent Backend API. See /api/docs for details."}


if __name__ == "__main__":
    import uvicorn

    # Run directly for simple development
    # Use gunicorn with uvicorn workers for production
    uvicorn.run(app, host="0.0.0.0", port=8000)
