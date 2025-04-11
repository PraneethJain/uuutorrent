from pydantic import BaseModel
from typing import Optional


class AnilistMediaTitle(BaseModel):
    romaji: Optional[str] = None
    english: Optional[str] = None
    native: Optional[str] = None
    userPreferred: Optional[str] = None


class AnilistMediaListEntry(BaseModel):
    progress: int


class AnilistNextAiringEpisode(BaseModel):
    airingAt: int
    timeUntilAiring: int
    episode: int


class AnilistMedia(BaseModel):
    id: int
    title: AnilistMediaTitle
    episodes: Optional[int] = None
    format: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    mediaListEntry: Optional[AnilistMediaListEntry] = None
    nextAiringEpisode: Optional[AnilistNextAiringEpisode] = None

    def get_unwatched_episodes(self) -> list[int]:
        if not self.episodes or self.episodes == 0 or self.status == "RELEASING":
            return []
        current_progress = self.mediaListEntry.progress if self.mediaListEntry else 0
        return list(range(current_progress + 1, self.episodes + 1))


class AnilistEntry(BaseModel):
    media: AnilistMedia


class WatchlistDownloadRequest(BaseModel):
    media_id: int
    episode: int
    preferred_quality: str = "1080p"


class WatchlistProgressUpdate(BaseModel):
    media_id: int
    progress: int
