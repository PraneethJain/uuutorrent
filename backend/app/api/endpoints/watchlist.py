from fastapi import APIRouter, HTTPException, status
from typing import List

from app.api.deps import DBSession, CurrentUser, CurrentAnilistToken
from app.schemas import anilist as anilist_schema
from app.schemas import msg as msg_schema
from app.services.anilist_service import anilist_service
from app.services.torrent_orchestration_service import torrent_orchestration_service

router = APIRouter()


@router.get("/", response_model=List[anilist_schema.AnilistEntry])
async def get_user_watchlist(
    current_user: CurrentUser,
    anilist_token: CurrentAnilistToken,
):
    """
    Get the current user's 'CURRENT' watching list from Anilist.
    """
    try:
        viewer_id = await anilist_service.get_viewer_id(anilist_token)
        watchlist = await anilist_service.get_user_list(
            user_token=anilist_token, user_id=viewer_id
        )
        return watchlist
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error fetching watchlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch watchlist.",
        )


@router.post(
    "/download", response_model=msg_schema.Msg, status_code=status.HTTP_202_ACCEPTED
)
async def download_watchlist_item(
    request: anilist_schema.WatchlistDownloadRequest,
    current_user: CurrentUser,
    anilist_token: CurrentAnilistToken,
    db: DBSession,
):
    """
    Trigger the download process for a specific unwatched episode from the watchlist.
    """
    print(f"Fetching details for Anilist media ID: {request.media_id}")
    media_details = await anilist_service.get_media_details(
        user_token=anilist_token, media_id=request.media_id
    )

    if not media_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find media details on Anilist for ID {request.media_id}.",
        )

    media_title = media_details.title.userPreferred or media_details.title.romaji
    if not media_title:
        media_title = media_details.title.english or f"AnilistMedia_{request.media_id}"
        print(
            f"Warning: Using fallback title '{media_title}' for media ID {request.media_id}"
        )

    print(f"Found title: '{media_title}' for media ID: {request.media_id}")

    try:
        torrent_hash = await torrent_orchestration_service.download_watchlist_episode(
            db=db,
            user=current_user,
            media_title=media_title,
            episode_number=request.episode,
            preferred_quality=request.preferred_quality,
        )
        return {
            "msg": f"Download initiated for episode {request.episode}. Torrent hash: {torrent_hash}"
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error orchestrating download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate download.",
        )


@router.post("/progress", response_model=msg_schema.Msg)
async def update_watchlist_progress(
    request: anilist_schema.WatchlistProgressUpdate, anilist_token: CurrentAnilistToken
):
    """
    Update the progress for a media item on the user's Anilist watchlist.
    """
    success = await anilist_service.set_progress(
        user_token=anilist_token, media_id=request.media_id, progress=request.progress
    )
    if success:
        return {
            "msg": f"Anilist progress updated successfully for media ID {request.media_id} to {request.progress}."
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update Anilist progress.",
        )
