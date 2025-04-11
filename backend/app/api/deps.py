from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.core import security
from app.db.base import get_db
from app.db.repository.user_repo import UserRepository
from app.db.repository.token_repo import AnilistTokenRepository
from app.db.repository.torrent_repo import TorrentRepository
from app.db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

DBSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(db: DBSession) -> UserRepository:
    """Dependency function that provides a UserRepository instance."""
    return UserRepository(db)


def get_token_repository(db: DBSession) -> AnilistTokenRepository:
    """Dependency function that provides an AnilistTokenRepository instance."""
    return AnilistTokenRepository(db)


def get_torrent_repository(db: DBSession) -> TorrentRepository:
    """Dependency function that provides a TorrentRepository instance."""
    return TorrentRepository(db)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
TokenRepoDep = Annotated[AnilistTokenRepository, Depends(get_token_repository)]
TorrentRepoDep = Annotated[TorrentRepository, Depends(get_torrent_repository)]


async def get_current_user(
    db: DBSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = security.decode_access_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception

    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(user_id=token_data.user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_anilist_token(
    current_user: CurrentUser, token_repo: TokenRepoDep
) -> str:
    anilist_token_obj = await token_repo.get_token(user_id=current_user.id)
    if not anilist_token_obj or not anilist_token_obj.access_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anilist token not found or is invalid for this user. Please link your account via POST /api/v1/auth/anilist/link.",
        )
    return anilist_token_obj.access_token


CurrentAnilistToken = Annotated[str, Depends(get_current_anilist_token)]


async def get_current_active_admin(
    current_user: CurrentUser,
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user


CurrentAdminUser = Annotated[User, Depends(get_current_active_admin)]


async def verify_torrent_ownership(
    info_hash: str,
    current_user: CurrentUser,
    torrent_repo: TorrentRepoDep,
) -> str:
    is_owner = await torrent_repo.is_owner(
        user_id=current_user.id, torrent_hash=info_hash
    )
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Torrent not found or user does not have permission.",
        )
    return info_hash


OwnedTorrentHash = Annotated[str, Depends(verify_torrent_ownership)]
