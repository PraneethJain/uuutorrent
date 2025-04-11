from fastapi import APIRouter

from app.api.endpoints import auth, torrents, watchlist

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(
    watchlist.router, prefix="/watchlist", tags=["Watchlist & Anilist"]
)
api_router.include_router(
    torrents.router, prefix="/torrents", tags=["Torrents & qBittorrent"]
)
