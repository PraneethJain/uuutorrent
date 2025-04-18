# --- FILE START: ./backend/app/api/endpoints/watchlist.py ---
import asyncio
import logging  # Import logging
from fastapi import APIRouter, HTTPException, status, Request
from typing import List

from app.api.deps import DBSession, CurrentUser, CurrentAnilistToken
from app.schemas import anilist as anilist_schema
from app.schemas import msg as msg_schema
from app.services.anilist_service import anilist_service
from app.events import DownloadEpisodeRequested

log = logging.getLogger(__name__)  # Use logger
router = APIRouter()


@router.get("/", response_model=List[anilist_schema.AnilistEntry])
async def get_user_watchlist(
    current_user: CurrentUser,
    anilist_token: CurrentAnilistToken,
):
    """
    Get the current user's 'CURRENT' watching list from Anilist.
    """
    log.info(f"API: Received request to get watchlist for user {current_user.id}")
    try:
        viewer_id = await anilist_service.get_viewer_id(anilist_token)
        watchlist = await anilist_service.get_user_list(
            user_token=anilist_token, user_id=viewer_id
        )
        log.info(
            f"API: Successfully fetched watchlist for user {current_user.id}, found {len(watchlist)} items."
        )
        return watchlist
    except HTTPException as e:
        log.warning(
            f"API: HTTPException fetching watchlist for user {current_user.id}: {e.detail}"
        )
        raise e
    except Exception as e:
        log.exception(
            f"API: Unhandled exception fetching watchlist for user {current_user.id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch watchlist.",
        )


@router.post(
    "/download", response_model=msg_schema.Msg, status_code=status.HTTP_202_ACCEPTED
)
async def download_watchlist_item(
    request_payload: anilist_schema.WatchlistDownloadRequest,
    fastapi_request: Request,  # Inject request to get app state
    current_user: CurrentUser,
    anilist_token: CurrentAnilistToken,
):
    """
    [EVENT-DRIVEN] Trigger the download process by publishing an event
    to the download_request_queue. Returns immediately.
    """
    log.info(
        f"API: Received download request from user {current_user.id} for media {request_payload.media_id}, ep {request_payload.episode}"
    )
    try:
        # *** GET CORRECT QUEUE FROM STATE ***
        request_queue = fastapi_request.app.state.download_request_queue
        if not request_queue:
            log.error("API Error: download_request_queue not found in app state.")
            raise HTTPException(status_code=500, detail="Event queue not initialized")
        # *** END GET QUEUE ***

        event = DownloadEpisodeRequested(
            user_id=current_user.id,
            media_id=request_payload.media_id,
            episode=request_payload.episode,
            preferred_quality=request_payload.preferred_quality,
            anilist_token=anilist_token,
        )

        # *** PUT TO CORRECT QUEUE ***
        await request_queue.put(event)
        log.info(
            f"API: Published DownloadEpisodeRequested event to download_request_queue for user {current_user.id}, media {request_payload.media_id}, ep {request_payload.episode}"
        )
        # *** END PUT ***
        return {
            "msg": f"Download request accepted for episode {request_payload.episode}. Processing initiated."
        }

    except Exception as e:
        log.exception(
            f"API Error: Failed to publish download event for user {current_user.id}, media {request_payload.media_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue download request.",
        )


@router.post("/progress", response_model=msg_schema.Msg)
async def update_watchlist_progress(
    request: anilist_schema.WatchlistProgressUpdate,
    anilist_token: CurrentAnilistToken,
    current_user: CurrentUser,  # Added user for logging
):
    """
    Update the progress for a media item on the user's Anilist watchlist.
    """
    log.info(
        f"API: Received request to update progress for user {current_user.id}, media {request.media_id} to {request.progress}"
    )
    try:
        success = await anilist_service.set_progress(
            user_token=anilist_token,
            media_id=request.media_id,
            progress=request.progress,
        )
        if success:
            log.info(
                f"API: Successfully updated Anilist progress for user {current_user.id}, media {request.media_id}"
            )
            return {
                "msg": f"Anilist progress updated successfully for media ID {request.media_id} to {request.progress}."
            }
        else:
            log.error(
                f"API Error: Failed to update Anilist progress for user {current_user.id}, media {request.media_id} (service returned False)."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update Anilist progress.",
            )
    except HTTPException as e:
        log.warning(
            f"API: HTTPException updating progress for user {current_user.id}, media {request.media_id}: {e.detail}"
        )
        raise e
    except Exception as e:
        log.exception(
            f"API: Unhandled exception updating progress for user {current_user.id}, media {request.media_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating progress.",
        )


# --- FILE END: ./backend/app/api/endpoints/watchlist.py ---
