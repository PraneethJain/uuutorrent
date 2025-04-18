# --- FILE START: ./backend/app/events.py ---
from pydantic import BaseModel


# Event indicating a user requested a download via the watchlist
class DownloadEpisodeRequested(BaseModel):
    user_id: int
    media_id: int
    episode: int
    preferred_quality: str
    # Include Anilist token directly to avoid DB lookup in the first worker
    anilist_token: str


# Event indicating a suitable torrent was found after searching
class TorrentFound(BaseModel):
    user_id: int
    media_title: str  # For logging/context
    episode: int  # For logging/context
    torrent_info_hash: str


# (Optional: Add failure events like SearchFailed, TorrentAddFailed etc. for robust error handling)

# --- FILE END: ./backend/app/events.py ---
