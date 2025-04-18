# --- FILE START: ./backend/app/workers.py ---
import asyncio
import logging
from typing import Callable

# No longer need pydantic for isinstance checks here
# import pydantic

from app.events import DownloadEpisodeRequested, TorrentFound
from app.services.anilist_service import AnilistService
from app.services.nyaa_service import NyaaService
from app.services.qbittorrent_service import QBittorrentService
from app.db.repository.torrent_repo import TorrentRepository
from app.db.base import AsyncSession

log = logging.getLogger(__name__)

# *** DEFINE SEPARATE QUEUES ***
download_request_queue: asyncio.Queue = asyncio.Queue()
torrent_found_queue: asyncio.Queue = asyncio.Queue()
# *** END QUEUE DEFINITION ***


# Worker to handle the initial download request: Find torrent
async def handle_download_request(
    # Takes the input queue for this stage
    request_queue: asyncio.Queue,
    # Takes the output queue for the next stage
    found_queue: asyncio.Queue,
    anilist_svc: AnilistService,
    nyaa_svc: NyaaService,
    session_factory: Callable[[], AsyncSession],  # Keep if needed
):
    log.info(
        f"Worker 'handle_download_request' started (Task: {asyncio.current_task().get_name()}). Listening on request_queue."
    )
    while True:
        event: DownloadEpisodeRequested = None  # Clearer scoping
        try:
            log.info(
                "Worker 'handle_download_request' waiting for event on request_queue..."
            )
            # *** GET FROM SPECIFIC QUEUE ***
            event = await request_queue.get()
            # *** END GET ***
            log.info(
                f"Worker 'handle_download_request' received event: Type=DownloadEpisodeRequested, Content={event}"
            )  # Type is guaranteed now

            # --- REMOVED TYPE CHECK ---
            # No longer needed as we only get from the correct queue

            # --- Processing Logic (remains the same inside) ---
            log.info(
                f"Worker 'handle_download_request': Processing DownloadEpisodeRequested for media_id {event.media_id}, ep {event.episode}"
            )
            media_details = None
            search_results = None
            selected_torrent = None

            # 1. Get Media Details
            # ... (logging and logic as before) ...
            log.info(f"--> Getting media details for {event.media_id} from Anilist...")
            media_details = await anilist_svc.get_media_details(
                user_token=event.anilist_token, media_id=event.media_id
            )
            if not media_details:
                log.error(
                    f"--> Anilist Error: Could not find media details for ID {event.media_id}. Skipping."
                )
                request_queue.task_done()
                continue
            # ... (title logic) ...
            media_title = (
                media_details.title.userPreferred
                or media_details.title.romaji
                or media_details.title.english
                or f"AnilistMedia_{event.media_id}"
            )
            log.info(f"--> Got media details: Title='{media_title}'")

            # 2. Search Nyaa
            # ... (logging and logic as before) ...
            query = f"{media_title} - {event.episode:02d}"
            log.info(f"--> Searching Nyaa for: '{query} {event.preferred_quality}'")
            search_results = await nyaa_svc.search(f"{query} {event.preferred_quality}")
            if not search_results:
                log.warning(
                    f"--> Nyaa: No results found with quality filter. Retrying without for: '{query}'"
                )
                search_results = await nyaa_svc.search(query)
            if not search_results:
                log.error(
                    f"--> Nyaa Error: No torrents found on Nyaa for '{query}'. Skipping."
                )
                request_queue.task_done()
                continue
            log.info(f"--> Nyaa: Found {len(search_results)} potential results.")

            # 3. Select Best Torrent
            # ... (logging and logic as before) ...
            log.info("--> Selecting best torrent...")
            valid_results = [r for r in search_results if r.info_hash]
            if not valid_results:
                log.error(
                    "--> Nyaa Error: No results found with a valid info_hash. Skipping."
                )
                request_queue.task_done()
                continue
            # ... (selection logic) ...
            quality_filtered = [
                r
                for r in valid_results
                if event.preferred_quality.lower() in r.title.lower()
            ]
            if quality_filtered:
                quality_filtered.sort(key=lambda r: r.seeders or 0, reverse=True)
                selected_torrent = quality_filtered[0]
                log.info(
                    f"--> Selected torrent matching quality: {selected_torrent.title} (Hash: {selected_torrent.info_hash})"
                )
            else:
                valid_results.sort(key=lambda r: r.seeders or 0, reverse=True)
                selected_torrent = valid_results[0]
                log.info(
                    f"--> Selected best torrent (no quality match): {selected_torrent.title} (Hash: {selected_torrent.info_hash})"
                )

            if not selected_torrent or not selected_torrent.info_hash:
                log.error(
                    "--> Internal Error: Could not select a suitable torrent after filtering. Skipping."
                )
                request_queue.task_done()
                continue

            # 4. Publish TorrentFound event to the *next* queue
            log.info(
                f"--> Publishing TorrentFound event for hash {selected_torrent.info_hash} to found_queue..."
            )
            found_event = TorrentFound(
                user_id=event.user_id,
                media_title=media_title,
                episode=event.episode,
                torrent_info_hash=selected_torrent.info_hash,
            )
            # *** PUT TO SPECIFIC QUEUE ***
            await found_queue.put(found_event)
            # *** END PUT ***
            log.info(f"--> Published TorrentFound event successfully.")
            # --- END Processing Logic ---

            # Mark original DownloadEpisodeRequested event as done
            request_queue.task_done()
            log.info(
                f"Worker 'handle_download_request': Finished processing event for media_id {event.media_id}, ep {event.episode}."
            )

        except asyncio.CancelledError:
            log.info(f"Worker 'handle_download_request' cancelled.")
            break
        except Exception as e:
            log.exception(
                f"Worker 'handle_download_request': Unhandled exception during processing event {event!r}."
            )
            if event is not None:
                try:
                    request_queue.task_done()  # Use correct queue instance
                    log.info(
                        f"Worker 'handle_download_request': Marked task done on request_queue after exception for event {event!r}."
                    )
                except ValueError:
                    pass
            await asyncio.sleep(5)


# Worker to handle adding the found torrent to qBit and DB
async def handle_torrent_found(
    # Takes the input queue for this stage
    found_queue: asyncio.Queue,
    qbt_svc: QBittorrentService,
    session_factory: Callable[[], AsyncSession],
):
    log.info(
        f"Worker 'handle_torrent_found' started (Task: {asyncio.current_task().get_name()}). Listening on found_queue."
    )
    while True:
        event: TorrentFound = None
        final_hash = None
        try:
            log.info(
                "Worker 'handle_torrent_found' waiting for event on found_queue..."
            )
            # *** GET FROM SPECIFIC QUEUE ***
            event = await found_queue.get()
            # *** END GET ***
            log.info(
                f"Worker 'handle_torrent_found' received event: Type=TorrentFound, Content={event}"
            )  # Type is guaranteed

            # --- REMOVED TYPE CHECK ---

            # --- Processing Logic (remains the same inside) ---
            log.info(
                f"Worker 'handle_torrent_found': Processing TorrentFound for hash {event.torrent_info_hash}, user {event.user_id}"
            )

            # 1. Add to qBittorrent
            # ... (logging and logic as before) ...
            log.info(f"--> Adding torrent {event.torrent_info_hash} to qBittorrent...")
            loop = asyncio.get_running_loop()
            torrent_hash_from_qbit = await loop.run_in_executor(
                None,
                qbt_svc.add_torrent_source,
                event.torrent_info_hash,
            )
            if not torrent_hash_from_qbit:
                log.error(
                    f"--> qBittorrent Error: Failed to add torrent {event.torrent_info_hash} or confirm hash. Skipping."
                )
                found_queue.task_done()
                continue
            # ... (hash handling) ...
            final_hash = torrent_hash_from_qbit.lower()
            if final_hash != event.torrent_info_hash.lower():
                log.warning(
                    f"--> Hash mismatch! Nyaa hash: {event.torrent_info_hash}, qBit returned: {final_hash}. Using qBit hash."
                )
            log.info(f"--> qBittorrent: Torrent added/found with hash {final_hash}")

            # 2. Link in Database
            # ... (logging and logic as before) ...
            log.info(
                f"--> Linking torrent {final_hash} to user {event.user_id} in database..."
            )
            async with session_factory() as session:
                async with session.begin():
                    log.info(f"--> DB Session acquired.")
                    torrent_repo = TorrentRepository(session)
                    link = await torrent_repo.link_torrent(
                        user_id=event.user_id, torrent_hash=final_hash
                    )
                    if link:
                        log.info(
                            f"--> DB: Successfully linked torrent {final_hash} to user {event.user_id}"
                        )
                    else:
                        log.warning(
                            f"--> DB: Torrent link for hash {final_hash} and user {event.user_id} already existed or failed silently."
                        )
                log.info(f"--> DB Session closed.")
            log.info(f"--> DB link step completed.")
            # --- END Processing Logic ---

            found_queue.task_done()
            log.info(
                f"Worker 'handle_torrent_found': Finished processing event for hash {final_hash}, user {event.user_id}."
            )

        except asyncio.CancelledError:
            log.info(f"Worker 'handle_torrent_found' cancelled.")
            break
        except Exception as e:
            log.exception(
                f"Worker 'handle_torrent_found': Unhandled exception during processing event {event!r}."
            )
            if final_hash:
                log.critical(
                    f"CRITICAL: Failure occurred after torrent {final_hash} was likely added to qBit but possibly before DB link for user {event.user_id}!"
                )
            if event is not None:
                try:
                    found_queue.task_done()  # Use correct queue instance
                    log.info(
                        f"Worker 'handle_torrent_found': Marked task done on found_queue after exception for event {event!r}."
                    )
                except ValueError:
                    pass
            await asyncio.sleep(5)


# --- FILE END: ./backend/app/workers.py ---
