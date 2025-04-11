from fastapi import HTTPException, status
from typing import Optional
import asyncio

from app.db.models import User
from app.services.nyaa_service import nyaa_service, NyaaResult
from app.services.qbittorrent_service import qbittorrent_service
from app.db.repository.torrent_repo import TorrentRepository
from app.db.base import AsyncSession


class TorrentOrchestrationService:

    def _select_best_torrent(
        self, results: list[NyaaResult], preferred_quality: str
    ) -> Optional[NyaaResult]:
        """Selects the 'best' torrent, prioritizing those with an info_hash."""
        if not results:
            return None

        valid_results = [r for r in results if r.info_hash]
        if not valid_results:
            print("No Nyaa results found with a valid info_hash.")
            return None

        quality_filtered = [
            r for r in valid_results if preferred_quality.lower() in r.title.lower()
        ]

        if quality_filtered:
            quality_filtered.sort(key=lambda r: r.seeders or 0, reverse=True)
            print(
                f"Found {len(quality_filtered)} results matching quality '{preferred_quality}'. Best: {quality_filtered[0]}"
            )
            return quality_filtered[0]
        else:
            valid_results.sort(key=lambda r: r.seeders or 0, reverse=True)
            print(
                f"No results matching quality '{preferred_quality}'. Falling back to highest seeder: {valid_results[0]}"
            )
            return valid_results[0]

    async def download_watchlist_episode(
        self,
        db: AsyncSession,
        user: User,
        media_title: str,
        episode_number: int,
        preferred_quality: str,
    ) -> str:
        """Orchestrates the download: searches Nyaa, selects, adds via hash/URL."""

        query = f"{media_title} - {episode_number:02d}"
        print(f"Searching Nyaa for: '{query} {preferred_quality}'")
        search_results = await nyaa_service.search(f"{query} {preferred_quality}")

        if not search_results:
            print(f"Retrying Nyaa search without quality filter for: '{query}'")
            search_results = await nyaa_service.search(query)

        if not search_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No torrents found on Nyaa for '{query}'.",
            )

        selected_torrent = self._select_best_torrent(search_results, preferred_quality)

        if not selected_torrent or not selected_torrent.info_hash:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Could not find a suitable torrent with an info_hash on Nyaa.",
            )

        print(
            f"Selected torrent: {selected_torrent.title} (Hash: {selected_torrent.info_hash})"
        )

        source_to_add = selected_torrent.info_hash

        print(
            f"qbt-sync: Calling add_torrent_source in executor for hash {source_to_add}..."
        )
        try:
            loop = asyncio.get_running_loop()
            torrent_hash_from_qbit = await loop.run_in_executor(
                None,
                qbittorrent_service.add_torrent_source,
                source_to_add,
            )
        except (ValueError, HTTPException) as e:
            print(f"Error during add_torrent_source execution: {e}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(status_code=400, detail=f"Torrent source error: {e}")
        except Exception as e:
            print(f"Error executing qbittorrent add in executor: {e}")
            raise HTTPException(
                status_code=500, detail="Error during torrent addition process."
            )

        if not torrent_hash_from_qbit:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add torrent to qBittorrent or confirm its hash.",
            )

        if torrent_hash_from_qbit.lower() != selected_torrent.info_hash.lower():
            print(
                f"WARNING: Hash mismatch! Nyaa hash: {selected_torrent.info_hash}, qBit returned: {torrent_hash_from_qbit}. Using qBit hash."
            )

        final_hash = torrent_hash_from_qbit
        torrent_repo = TorrentRepository(db)
        try:
            link = await torrent_repo.link_torrent(
                user_id=user.id, torrent_hash=final_hash
            )
            if link:
                print(f"Successfully linked torrent {final_hash} to user {user.id}")
            else:
                print(
                    f"Torrent link for hash {final_hash} and user {user.id} already existed."
                )
        except Exception as e:
            print(
                f"CRITICAL: Failed to link torrent {final_hash} to user {user.id} in DB after adding to qBit: {e}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Torrent added to qBit (hash: {final_hash}), but DB linking failed.",
            )

        return final_hash


torrent_orchestration_service = TorrentOrchestrationService()
