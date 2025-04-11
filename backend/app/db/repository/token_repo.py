from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from typing import Optional

from app.db.models import AnilistToken


class AnilistTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_token(self, user_id: int) -> Optional[AnilistToken]:
        """Fetches the Anilist token object for a given user ID."""
        result = await self.db.execute(
            select(AnilistToken).filter(AnilistToken.user_id == user_id)
        )
        return result.scalars().first()

    async def save_token(self, user_id: int, access_token: str) -> AnilistToken:
        """
        Saves (creates or updates) the Anilist access token for a user.
        Uses PostgreSQL's ON CONFLICT DO UPDATE for atomic upsert.
        """
        stmt = insert(AnilistToken).values(user_id=user_id, access_token=access_token)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_=dict(access_token=stmt.excluded.access_token),
        ).returning(AnilistToken)

        try:
            result = await self.db.execute(stmt)
            saved_token = result.scalars().one()
            return saved_token
        except IntegrityError as e:
            print(f"Integrity error saving token for user {user_id}: {e}")
            raise
        except Exception as e:
            print(f"Error saving token for user {user_id}: {e}")
            raise

    async def delete_token(self, user_id: int) -> bool:
        """Deletes the Anilist token for a given user ID. Returns True if deleted."""
        token = await self.get_token(user_id)
        if token:
            await self.db.delete(token)
            await self.db.flush()
            return True
        return False
