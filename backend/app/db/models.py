from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Boolean,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    anilist_token = relationship(
        "AnilistToken",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    torrents = relationship(
        "UserTorrentLink", back_populates="user", cascade="all, delete-orphan"
    )


class AnilistToken(Base):
    __tablename__ = "anilist_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    access_token = Column(String, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), default=func.now()
    )

    user = relationship("User", back_populates="anilist_token")


class UserTorrentLink(Base):
    __tablename__ = "user_torrent_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    torrent_hash = Column(String, nullable=False, index=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="torrents")

    __table_args__ = (
        UniqueConstraint("user_id", "torrent_hash", name="_user_torrent_uc"),
    )
