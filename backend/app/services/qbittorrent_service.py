import qbittorrentapi
import urllib.parse
import time
from typing import Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.torrent import TorrentInfo

_qbt_client: Optional[qbittorrentapi.Client] = None
_qbt_connection_error = None

try:
    _qbt_client = qbittorrentapi.Client(
        host=settings.QBITTORRENT_HOST,
        username=settings.QBITTORRENT_USER,
        password=settings.QBITTORRENT_PASS,
        REQUESTS_ARGS={"timeout": (10, 30)},
    )
    _qbt_client.auth_log_in()
    print(
        f"Successfully connected to qBittorrent v{_qbt_client.app.version} at {settings.QBITTORRENT_HOST}"
    )
except (qbittorrentapi.LoginFailed, qbittorrentapi.APIError, Exception) as e:
    print(f"FATAL: Failed to connect/login to qBittorrent on startup: {e}")
    _qbt_connection_error = e
    _qbt_client = None


def _get_client() -> qbittorrentapi.Client:
    """Gets the connected client instance or raises an error if unavailable."""
    if _qbt_client:
        return _qbt_client
    else:
        detail = f"qBittorrent client not available. Connection failed on startup: {_qbt_connection_error}"
        print(detail)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail
        )


class QBittorrentService:
    """
    Service to interact with qBittorrent using the SYNCHRONOUS 'python-qbittorrentapi' library.
    Methods here are synchronous and should be called via 'run_in_executor' from async code.
    """

    def add_torrent_source(
        self,
        source: str,
        save_path: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[list[str]] = None,
        paused: bool = False,
    ) -> Optional[str]:
        """
        Adds a torrent from various sources. SYNCHRONOUS.
        Returns the info_hash if successfully added/found. Hash retrieval is unreliable for URL adds.
        """
        client = _get_client()
        known_hash = None
        urls_to_add = []
        kwargs = {}

        if save_path:
            kwargs["save_path"] = save_path
        if category:
            kwargs["category"] = category
        if tags:
            kwargs["tags"] = tags
        if paused:
            kwargs["is_paused"] = True

        if source.startswith("magnet:?"):
            urls_to_add.append(source)
            print(f"qbt-sync: Adding magnet link: {source[:50]}...")
            try:
                if "xt=urn:btih:" in source:
                    start = source.find("xt=urn:btih:") + len("xt=urn:btih:")
                    end = source.find("&", start)
                    known_hash = source[start : end if end != -1 else None].lower()
            except Exception:
                pass
        elif source.startswith(("http://", "https://")) and source.endswith(".torrent"):
            urls_to_add.append(source)
            print(f"qbt-sync: Adding .torrent URL: {source}")
        elif len(source) == 40 and all(c in "0123456789abcdefABCDEF" for c in source):
            known_hash = source.lower()
            magnet_from_hash = f"magnet:?xt=urn:btih:{known_hash}"
            trackers = [
                "udp://tracker.openbittorrent.com:6969/announce",
                "udp://tracker.opentrackr.org:1337/announce",
            ]
            for tr in trackers:
                magnet_from_hash += f"&tr={urllib.parse.quote(tr)}"
            urls_to_add.append(magnet_from_hash)
            print(f"qbt-sync: Adding info_hash {known_hash} via constructed magnet...")
        else:
            raise ValueError("Invalid torrent source provided.")
        if not urls_to_add:
            raise ValueError("Could not determine URL or magnet to add.")

        try:
            result = client.torrents_add(urls=urls_to_add, **kwargs)

            if result == "Ok.":
                if known_hash:
                    print(
                        f"qbt-sync: Torrent addition initiated for known hash: {known_hash}"
                    )
                    return known_hash
                else:
                    print(
                        "qbt-sync: Added by URL, attempting unreliable hash retrieval..."
                    )
                    time.sleep(0.75)
                    torrents = self.get_all_torrents_raw()
                    if torrents:
                        latest_torrent = max(torrents, key=lambda t: t.added_on)
                        print(
                            f"qbt-sync: Assumed newest torrent hash (unreliable): {latest_torrent.hash}"
                        )
                        return latest_torrent.hash
                    else:
                        print(
                            "qbt-sync: Could not retrieve torrent list after adding by URL."
                        )
                        return None
            else:
                print(f"qbt-sync: Failed to add torrent, API response: {result}")
                if known_hash:
                    existing = self.get_torrent_details_raw(known_hash)
                    if existing:
                        print(
                            f"qbt-sync: Torrent with hash {known_hash} appears to already exist."
                        )
                        return known_hash
                return None

        except qbittorrentapi.Conflict409Error:
            print(f"qbt-sync: Torrent already exists (Conflict 409): {source[:60]}...")
            if known_hash:
                return known_hash
            return None
        except qbittorrentapi.APIError as e:
            print(f"qbt-sync: API error adding torrent: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"qBittorrent API error: {e}",
            )
        except Exception as e:
            print(f"qbt-sync: Unexpected error adding torrent: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error interacting with qBittorrent: {e}",
            )

    def get_all_torrents_raw(self) -> list[qbittorrentapi.TorrentDictionary]:
        """Gets raw torrent data from qBittorrent. SYNCHRONOUS."""
        client = _get_client()
        try:
            return client.torrents_info()
        except qbittorrentapi.APIError as e:
            print(f"qbt-sync: API error getting torrents: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_gateway,
                detail=f"qBittorrent API error: {e}",
            )
        except Exception as e:
            print(f"qbt-sync: Unexpected error getting torrents: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error interacting with qBittorrent: {e}",
            )

    def get_torrent_details_raw(
        self, info_hash: str
    ) -> Optional[qbittorrentapi.TorrentDictionary]:
        """Gets raw details for a single torrent by hash. SYNCHRONOUS."""
        client = _get_client()
        try:
            results = client.torrents_info(torrent_hashes=info_hash)
            return results[0] if results else None
        except qbittorrentapi.NotFound404Error:
            print(f"qbt-sync: Torrent {info_hash} not found (404).")
            return None
        except qbittorrentapi.APIError as e:
            print(f"qbt-sync: API error getting torrent {info_hash}: {e}")
            return None
        except Exception as e:
            print(f"qbt-sync: Unexpected error getting torrent {info_hash}: {e}")
            return None

    def map_torrent_info(
        self, torrent_dict: qbittorrentapi.TorrentDictionary
    ) -> TorrentInfo:
        """Maps qbittorrentapi TorrentDictionary to our Pydantic schema."""
        try:
            state_raw = getattr(torrent_dict, "state", "unknown")
            state_str = str(state_raw)
            status_map = {
                "error": "Error",
                "missingFiles": "Missing Files",
                "uploading": "Seeding",
                "pausedUP": "Paused Upload",
                "queuedUP": "Queued Upload",
                "stalledUP": "Stalled Upload",
                "checkingUP": "Checking Upload",
                "forcedUP": "Forced Upload",
                "allocating": "Allocating",
                "downloading": "Downloading",
                "metaDL": "Fetching Metadata",
                "pausedDL": "Paused Download",
                "queuedDL": "Queued Download",
                "stalledDL": "Stalled Download",
                "checkingDL": "Checking Download",
                "forcedDL": "Forced Download",
                "checkingResumeData": "Checking Resume Data",
                "moving": "Moving",
                "unknown": "Unknown",
            }
            mapped_status = status_map.get(state_str, state_str.capitalize())
            progress_val = getattr(torrent_dict, "progress", 0.0) * 100

            return TorrentInfo(
                hash=getattr(torrent_dict, "hash", "N/A"),
                name=getattr(torrent_dict, "name", "N/A"),
                size=getattr(torrent_dict, "size", 0),
                progress=round(progress_val, 2),
                status=mapped_status,
                num_seeds=getattr(torrent_dict, "num_seeds", 0),
                num_leechs=getattr(torrent_dict, "num_leechs", 0),
                added_on=getattr(torrent_dict, "added_on", 0),
            )
        except Exception as e:
            print(
                f"Error mapping qbt TorrentDictionary to schema: {e} - Data: {torrent_dict}"
            )
            raise ValueError(f"Failed to map torrent info: {e}")

    def _manage_torrents(self, action_method_name: str, info_hashes: str | list[str]):
        """Helper for pause, resume actions. SYNCHRONOUS."""
        client = _get_client()
        try:
            method = getattr(client.torrents, action_method_name)
            method(torrent_hashes=info_hashes)  # Use torrent_hashes parameter
        except qbittorrentapi.APIError as e:
            print(f"qbt-sync: API error during {action_method_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"qBittorrent API error: {e}",
            )
        except Exception as e:
            print(f"qbt-sync: Unexpected error during {action_method_name}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error interacting with qBittorrent: {e}",
            )

    def pause_torrent(self, info_hash: str):
        """Pauses a specific torrent. SYNCHRONOUS."""
        self._manage_torrents("pause", info_hashes=info_hash)

    def resume_torrent(self, info_hash: str):
        """Resumes a specific torrent. SYNCHRONOUS."""
        self._manage_torrents("resume", info_hashes=info_hash)

    def delete_torrent(self, info_hash: str, delete_files: bool = False):
        """Deletes torrent. SYNCHRONOUS."""
        client = _get_client()
        try:
            client.torrents_delete(torrent_hashes=info_hash, delete_files=delete_files)
        except qbittorrentapi.NotFound404Error:
            print(f"qbt-sync: Torrent {info_hash} not found for deletion (404).")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Torrent {info_hash} not found for deletion.",
            )
        except qbittorrentapi.APIError as e:
            print(f"qbt-sync: API error deleting torrent: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"qBittorrent API error: {e}",
            )
        except Exception as e:
            print(f"qbt-sync: Unexpected error deleting torrent: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error interacting with qBittorrent: {e}",
            )


qbittorrent_service = QBittorrentService()
