from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from app.db.models import UserTorrentLink


class TorrentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def link_torrent(
        self, user_id: int, torrent_hash: str
    ) -> Optional[UserTorrentLink]:
        """
        Creates a link between a user and a torrent hash.
        Handles potential unique constraint violations gracefully.
        Returns the link object if created, None if it already existed or on error.
        """
        link = UserTorrentLink(user_id=user_id, torrent_hash=torrent_hash)
        self.db.add(link)
        try:
            await self.db.flush()
            await self.db.refresh(link)
            return link
        except IntegrityError as e:
            await self.db.rollback()
            print(
                f"IntegrityError linking torrent {torrent_hash} for user {user_id}: {e}. Link likely exists."
            )
            existing_link = await self.get_link(user_id, torrent_hash)
            return existing_link
        except Exception as e:
            await self.db.rollback()
            print(f"Error linking torrent {torrent_hash} for user {user_id}: {e}")
            raise

    async def get_link(
        self, user_id: int, torrent_hash: str
    ) -> Optional[UserTorrentLink]:
        """Gets a specific link object."""
        result = await self.db.execute(
            select(UserTorrentLink).filter_by(
                user_id=user_id, torrent_hash=torrent_hash
            )
        )
        return result.scalars().first()

    async def unlink_torrent(self, user_id: int, torrent_hash: str) -> bool:
        """
        Removes the link between a user and a torrent hash.
        Returns True if a link was found and deleted, False otherwise.
        """
        stmt = (
            delete(UserTorrentLink)
            .where(
                UserTorrentLink.user_id == user_id,
                UserTorrentLink.torrent_hash == torrent_hash,
            )
            .execution_options(synchronize_session=False)
        )

        result = await self.db.execute(stmt)
        deleted_count = result.rowcount
        return deleted_count > 0

    async def get_user_torrent_hashes(self, user_id: int) -> List[str]:
        """Retrieves a list of all torrent hashes linked to a specific user."""
        stmt = select(UserTorrentLink.torrent_hash).where(
            UserTorrentLink.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def is_owner(self, user_id: int, torrent_hash: str) -> bool:
        """Checks if a specific user is linked to a specific torrent hash."""
        stmt = (
            select(UserTorrentLink.id)
            .where(
                UserTorrentLink.user_id == user_id,
                UserTorrentLink.torrent_hash == torrent_hash,
            )
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_all_links_for_user(self, user_id: int) -> List[UserTorrentLink]:
        """Gets all link objects for a user."""
        result = await self.db.execute(
            select(UserTorrentLink).filter(UserTorrentLink.user_id == user_id)
        )
        return result.scalars().all()
