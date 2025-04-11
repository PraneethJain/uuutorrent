from pydantic import BaseModel, EmailStr
import datetime


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True  # Pydantic V2 (orm_mode in V1)
