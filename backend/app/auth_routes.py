from fastapi import APIRouter, Depends, HTTPException, Request, Response

from . import media, storage
from .schemas import AccountResponse, ChangePasswordRequest, LoginRequest, RegisterRequest
from .settings import SESSION_COOKIE, SESSION_COOKIE_SECURE


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def account_response(user: dict[str, object]) -> AccountResponse:
    is_guest = bool(user.get("is_guest", False))
    return AccountResponse(
        username="Guest" if is_guest else str(user["username"]),
        must_change_password=bool(user.get("must_change_password", False)),
        is_guest=is_guest,
    )


def set_session_cookie(
    response: Response, token: str, *, guest: bool = False
) -> None:
    options: dict[str, object] = {
        "httponly": True,
        "secure": SESSION_COOKIE_SECURE,
        "samesite": "strict",
        "path": "/api",
    }
    if not guest:
        options["max_age"] = int(storage.SESSION_TTL.total_seconds())
    response.set_cookie(SESSION_COOKIE, token, **options)


def get_current_user(request: Request) -> dict[str, object]:
    token = request.cookies.get(SESSION_COOKIE)
    user = storage.get_user_for_session(token) if token else None
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in or continue as guest.")
    return user


def require_ready_user(
    user: dict[str, object] = Depends(get_current_user),
) -> dict[str, object]:
    if user.get("must_change_password"):
        raise HTTPException(
            status_code=403,
            detail="Change the temporary password before using the song library.",
        )
    return user


@router.post("/guest", response_model=AccountResponse, status_code=201)
def continue_as_guest(response: Response) -> AccountResponse:
    expired_users, expired_songs = storage.purge_expired_guests()
    media.delete_song_files(expired_songs)
    for user_id in expired_users:
        media.delete_user_uploads(user_id)
    user, token = storage.create_guest()
    set_session_cookie(response, token, guest=True)
    return account_response(user)


@router.post("/register", response_model=AccountResponse, status_code=201)
def register(payload: RegisterRequest, response: Response) -> AccountResponse:
    try:
        user = storage.create_user(payload.username, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    token = storage.create_session(user["id"])
    set_session_cookie(response, token)
    return account_response(user)


@router.post("/login", response_model=AccountResponse)
def login(payload: LoginRequest, response: Response) -> AccountResponse:
    user = storage.get_user_by_username(payload.username)
    if (
        user is None
        or user.get("is_guest")
        or not storage.verify_password(payload.password, str(user["password_hash"]))
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    token = storage.create_session(str(user["id"]))
    set_session_cookie(response, token)
    return account_response(user)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    user: dict[str, object] = Depends(get_current_user),
) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        storage.delete_session(token)
    if user.get("is_guest"):
        media.delete_song_files(storage.delete_guest(str(user["id"])))
        media.delete_user_uploads(str(user["id"]))
    response.delete_cookie(SESSION_COOKIE, path="/api", samesite="strict")
    response.status_code = 204
    return response


@router.get("/me", response_model=AccountResponse)
def current_account(
    user: dict[str, object] = Depends(get_current_user),
) -> AccountResponse:
    return account_response(user)


@router.post("/ping", response_model=AccountResponse)
def keep_guest_session(
    user: dict[str, object] = Depends(get_current_user),
) -> AccountResponse:
    return account_response(user)


@router.post("/change-password", response_model=AccountResponse)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    user: dict[str, object] = Depends(get_current_user),
) -> AccountResponse:
    if user.get("is_guest"):
        raise HTTPException(status_code=403, detail="Guest sessions do not use passwords.")
    stored = storage.get_user_by_username(str(user["username"]))
    if stored is None or not storage.verify_password(
        payload.current_password, str(stored["password_hash"])
    ):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=422,
            detail="Choose a new password different from the current one.",
        )
    user_id = str(user["id"])
    storage.update_password(user_id, payload.new_password)
    user["must_change_password"] = False
    token = storage.create_session(user_id)
    set_session_cookie(response, token)
    return account_response(user)
