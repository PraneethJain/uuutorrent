from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated

from app.core import security
from app.schemas import user as user_schema
from app.schemas import token as token_schema
from app.schemas import msg as msg_schema
from app.api.deps import (
    UserRepoDep,
    TokenRepoDep,
    CurrentUser,
    CurrentAnilistToken,
)

router = APIRouter()


@router.post(
    "/signup", response_model=user_schema.User, status_code=status.HTTP_201_CREATED
)
async def create_user_signup(
    *, user_in: user_schema.UserCreate, user_repo: UserRepoDep
):
    """
    Create new user.
    """
    existing_user = await user_repo.get_user_by_username(username=user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered.",
        )
    existing_user = await user_repo.get_user_by_email(email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered."
        )

    hashed_password = security.get_password_hash(user_in.password)
    user = await user_repo.create_user(user_in=user_in, hashed_password=hashed_password)
    return user


@router.post("/token", response_model=token_schema.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_repo: UserRepoDep,
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = await user_repo.get_user_by_username(username=form_data.username)
    if (
        not user
        or not security.verify_password(form_data.password, user.hashed_password)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(
        data={"sub": user.username, "id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=user_schema.User)
async def read_users_me(current_user: CurrentUser):
    """
    Get current user.
    """
    return current_user


@router.post("/anilist/link", response_model=msg_schema.Msg)
async def link_anilist_account(
    token_data: token_schema.AnilistTokenCreate,
    current_user: CurrentUser,
    token_repo: TokenRepoDep,
):
    """
    Store the user's manually obtained Anilist access token.
    (Requires user to paste token after authorizing on Anilist website)
    """
    # TODO: Add validation to check if the token is actually valid? (e.g., make a viewer query)
    await token_repo.save_token(
        user_id=current_user.id, access_token=token_data.access_token
    )
    return {"msg": "Anilist token saved successfully."}


@router.get("/anilist/test", response_model=msg_schema.Msg)
async def test_anilist_token(
    anilist_token: CurrentAnilistToken,
):
    """Tests if the stored Anilist token works by fetching viewer ID."""
    from app.services.anilist_service import anilist_service

    try:
        viewer_id = await anilist_service.get_viewer_id(anilist_token)
        return {"msg": f"Anilist token is valid. Viewer ID: {viewer_id}"}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Anilist test error: {e}")
        raise HTTPException(status_code=500, detail="Failed to test Anilist token.")
