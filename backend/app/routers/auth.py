import logging
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, MessageResponse, RegisterRequest
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_OPTS = dict(httponly=True, samesite="lax", secure=False, path="/")


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie("humanizer_access_token", access_token, max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, **_COOKIE_OPTS)
    response.set_cookie("humanizer_refresh_token", refresh_token, max_age=REFRESH_TOKEN_EXPIRE_DAYS * 86400, **_COOKIE_OPTS)


@router.post("/register", status_code=201, response_model=MessageResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=req.email, hashed_password=hash_password(req.password))
    db.add(user)
    db.commit()
    logger.info("New user registered: %s", req.email)
    return {"message": "User registered successfully"}


@router.post("/login", response_model=MessageResponse)
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    user.hashed_refresh_token = hash_password(refresh_token)
    db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    logger.info("User logged in: %s", user.email)
    return {"message": "Login successful"}


@router.post("/refresh", response_model=MessageResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(alias="humanizer_refresh_token", default=None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError()
        user_id = payload["sub"]
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.hashed_refresh_token:
        raise HTTPException(status_code=401, detail="Session expired")
    if not verify_password(refresh_token, user.hashed_refresh_token):
        raise HTTPException(status_code=401, detail="Refresh token mismatch")

    new_access = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)
    user.hashed_refresh_token = hash_password(new_refresh)
    db.commit()

    _set_auth_cookies(response, new_access, new_refresh)
    return {"message": "Token refreshed"}


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    db: Session = Depends(get_db),
):
    # We make current_user optional or just omit it to allow clearing cookies even if the token is expired
    response.delete_cookie("humanizer_access_token", path="/")
    response.delete_cookie("humanizer_refresh_token", path="/")
    return {"message": "Logged out"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}
