from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_access_token,
    get_client_ip,
    get_current_user,
    hash_password,
    log_audit_event,
    verify_password,
)
from app.database import get_db
from app.models import Entry, User
from app.schemas import AccountDeleteRequest, Token, UserCreate, UserResponse

router = APIRouter(tags=["Auth"])


@router.get("/auth/setup")
def check_setup(db: Session = Depends(get_db)):
    setup_done = db.query(User).first() is not None
    return {"setup_done": setup_done}


@router.post("/auth/setup", status_code=201, response_model=UserResponse)
def setup_account(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    if db.query(User).first() is not None:
        raise HTTPException(status_code=409, detail="Account already exists")

    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log_audit_event("auth.setup", payload.username, get_client_ip(request), True)
    return UserResponse.model_validate(user)


@router.post("/auth/token", response_model=Token)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form.username, form.password)
    if not user:
        log_audit_event("auth.login.failure", form.username, get_client_ip(request), False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.username})
    log_audit_event("auth.login.success", user.username, get_client_ip(request), True)
    return Token(access_token=token)


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.delete("/auth/account", status_code=204)
def delete_account(
    payload: AccountDeleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.password, current_user.hashed_password):
        log_audit_event(
            "data.delete_account",
            current_user.username,
            get_client_ip(request),
            False,
        )
        raise HTTPException(status_code=401, detail="Password is incorrect")

    log_audit_event(
        "data.delete_account",
        current_user.username,
        get_client_ip(request),
        True,
    )
    db.query(Entry).delete()
    db.delete(current_user)
    db.commit()
    return Response(status_code=204)
