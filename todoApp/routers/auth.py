"""
Authentication router for the Todo FastAPI application.
Provides endpoints for user registration, login, and Google OAuth integration.
"""
from datetime import timedelta, datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from todoApp.database import SessionLocal
from todoApp.models import Users
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import os
import json
import secrets
from urllib import parse, request as urlrequest
from dotenv import load_dotenv

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

SECRET_KEY = '197b2c37c391bed93fe80344fe73b806947a65e36206e05a1a23c2fa12702fe3'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl='auth/token')


class CreateUserRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    role: str
    phone_number: str
    address: str


class Token(BaseModel):
    access_token: str
    token_type: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]

templates = Jinja2Templates(directory="todoApp/templates")

# Load env once module imports
load_dotenv()

##pages##
@router.get("/login-page")
def render_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register-page")
def render_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

##Endpoints##
def authenticate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id, 'role': role}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')
        user_role: str = payload.get('role')  
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Could not validate user.')
        return {'username': username, 'id': user_id, 'user_role': user_role} 
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user.')


# --- Google OAuth 2.0 ---
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:8000/auth/google/callback')


@router.get("/google/login")
def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent"
    }
    return RedirectResponse(url=f"{auth_url}?{parse.urlencode(params)}")


def _post_form(url: str, data: dict):
    encoded = parse.urlencode(data).encode()
    req = urlrequest.Request(url, data=encoded)
    req.add_header('Content-Type', 'application/x-www-form-urlencoded')
    with urlrequest.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _get_json(url: str, bearer: str):
    req = urlrequest.Request(url)
    req.add_header('Authorization', f'Bearer {bearer}')
    with urlrequest.urlopen(req) as resp:
        return json.loads(resp.read().decode())


@router.get("/google/callback")
def google_callback(code: str | None = None, error: str | None = None, db: Annotated[Session, Depends(get_db)] = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for tokens
    token_resp = _post_form(
        "https://oauth2.googleapis.com/token",
        {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )

    access_token = token_resp.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to obtain access token from Google")

    # Get user info
    userinfo = _get_json("https://www.googleapis.com/oauth2/v3/userinfo", access_token)
    email = userinfo.get("email")
    given_name = userinfo.get("given_name") or ""
    family_name = userinfo.get("family_name") or ""
    name = userinfo.get("name") or email or "user"

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # Find or create user
    user_model = db.query(Users).filter(Users.email == email).first()
    if user_model is None:
        base_username = (email.split('@')[0] or name.replace(' ', '').lower())[:30]
        username = base_username
        suffix = 1
        while db.query(Users).filter(Users.username == username).first() is not None:
            username = f"{base_username}{suffix}"
            suffix += 1

        user_model = Users(
            email=email,
            username=username,
            first_name=given_name,
            last_name=family_name,
            role='user',
            hashed_password=bcrypt_context.hash(secrets.token_urlsafe(16)),
            is_active=True,
            address='',
            phone_number=''
        )
        db.add(user_model)
        db.commit()
        db.refresh(user_model)

    # Issue our JWT and redirect with cookie set
    token = create_access_token(user_model.username, user_model.id, user_model.role, timedelta(minutes=20))
    redirect = RedirectResponse(url='/todos/todo-page', status_code=302)
    redirect.set_cookie(key='access_token', value=token, path='/', secure=False, httponly=False, samesite='lax')
    return redirect

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency,
                      create_user_request: CreateUserRequest):
    create_user_model = Users(
        email=create_user_request.email,
        username=create_user_request.username,
        first_name=create_user_request.first_name,
        last_name=create_user_request.last_name,
        role=create_user_request.role,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        is_active=True,
        address = create_user_request.address,
        phone_number=create_user_request.phone_number
        
    )

    db.add(create_user_model)
    db.commit()


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Could not validate user.')
    token = create_access_token(user.username, user.id, user.role, timedelta(minutes=20))

    return {'access_token': token, 'token_type': 'bearer'}