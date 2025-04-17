from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Annotated

from app.api.deps import CurrentUser, CurrentAdminUser, TorrentRepoDep
from app.schemas import torrent as torrent_schema
from app.schemas import msg as msg_schema
from app.services.qbittorrent_service import qbittorrent_service

router = APIRouter()


@router.get("/", response_model=List[torrent_schema.TorrentInfo])
async def get_user_torrents(
    current_user: CurrentUser,
    torrent_repo: TorrentRepoDep,
):
    """
    Get list of torrents managed by qBittorrent associated with the current user.
    """
    user_torrent_hashes = await torrent_repo.get_user_torrent_hashes(
        user_id=current_user.id
    )
    if not user_torrent_hashes:
        return []

    try:
        all_torrents_raw = qbittorrent_service.get_all_torrents_raw()
        user_torrents_raw = [
            t for t in all_torrents_raw if t.hash in user_torrent_hashes
        ]
        return [qbittorrent_service.map_torrent_info(t) for t in user_torrents_raw]
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error processing torrent list for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve or process torrent list."
        )


@router.post("/", response_model=msg_schema.Msg, status_code=status.HTTP_202_ACCEPTED)
async def add_torrent_magnet(
    torrent_in: torrent_schema.TorrentAdd,
    current_user: CurrentUser,
    torrent_repo: TorrentRepoDep,
):
    """
    Add a new torrent via magnet link.
    """
    torrent_hash = qbittorrent_service.add_torrent_source(torrent_in.magnet_link)

    if not torrent_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add torrent or retrieve hash from qBittorrent.",
        )

    try:
        link = await torrent_repo.link_torrent(
            user_id=current_user.id, torrent_hash=torrent_hash
        )
        if link:
            print(
                f"Successfully linked torrent {torrent_hash} to user {current_user.id}"
            )
        else:
            print(
                f"Torrent link between user {current_user.id} and torrent {torrent_hash} already exists."
            )
            return {
                "msg": f"Torrent added successfully (Hash: {torrent_hash}). Link to user already existed."
            }

    except Exception as e:
        print(
            f"CRITICAL: Failed to link manually added torrent {torrent_hash} to user {current_user.id}: {e}"
        )
        return {
            "msg": f"Torrent added to qBittorrent (hash: {torrent_hash}), but failed to link to user in DB. Please check logs."
        }

    return {"msg": f"Torrent added successfully. Hash: {torrent_hash}"}


async def verify_torrent_ownership(
    info_hash: str, current_user: CurrentUser, torrent_repo: TorrentRepoDep
):
    is_owner = await torrent_repo.is_owner(
        user_id=current_user.id, torrent_hash=info_hash
    )
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not own this torrent.",
        )
    return info_hash


OwnedTorrentHash = Annotated[str, Depends(verify_torrent_ownership)]


@router.post("/{info_hash}/pause", response_model=msg_schema.Msg)
async def pause_user_torrent(
    info_hash: OwnedTorrentHash,
):
    """Pause a specific torrent owned by the user."""
    qbittorrent_service.pause_torrent(info_hash=info_hash)
    return {"msg": f"Torrent {info_hash} pause request sent."}


@router.post("/{info_hash}/resume", response_model=msg_schema.Msg)
async def resume_user_torrent(info_hash: OwnedTorrentHash):
    """Resume a specific torrent owned by the user."""
    qbittorrent_service.resume_torrent(info_hash=info_hash)
    return {"msg": f"Torrent {info_hash} resume request sent."}


@router.delete(
    "/{info_hash}", response_model=msg_schema.Msg, status_code=status.HTTP_200_OK
)
async def delete_user_torrent(
    info_hash: OwnedTorrentHash,
    current_user: CurrentUser,
    torrent_repo: TorrentRepoDep,
    delete_files: bool = Query(
        False, description="Set to true to also delete files from disk."
    ),
):
    """Delete a specific torrent owned by the user (and optionally its files)."""
    try:
        qbittorrent_service.delete_torrent(
            info_hash=info_hash, delete_files=delete_files
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error deleting torrent {info_hash} from qBit: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to delete torrent from qBittorrent."
        )

    try:
        deleted = await torrent_repo.unlink_torrent(
            user_id=current_user.id, torrent_hash=info_hash
        )
        if not deleted:
            print(
                f"WARN: Torrent {info_hash} deleted from qBit, but no link found in DB for user {current_user.id} to unlink."
            )
    except Exception as e:
        print(
            f"CRITICAL: Failed to unlink torrent {info_hash} from user {current_user.id} after successful qBit deletion: {e}"
        )
        return {
            "msg": f"Torrent {info_hash} deleted from qBittorrent, but failed to unlink from DB. Files deleted: {delete_files}. Please check logs."
        }

    return {
        "msg": f"Torrent {info_hash} deleted successfully. Files deleted: {delete_files}."
    }


@router.get(
    "/all",
    response_model=List[torrent_schema.TorrentInfo],
    dependencies=[Depends(CurrentAdminUser)],
)
async def get_all_torrents_admin():
    """(Admin) Get all torrents currently in qBittorrent."""
    all_torrents_raw = qbittorrent_service.get_all_torrents_raw()
    return [qbittorrent_service.map_torrent_info(t) for t in all_torrents_raw]
