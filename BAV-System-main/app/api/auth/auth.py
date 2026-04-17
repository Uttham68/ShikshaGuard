"""
app/auth/auth.py
─────────────────
JWT authentication + role-based access control.
Roles: admin | principal

Admin  → full access: all schools, all proposals, dashboard, planning
Principal → own school only: submit/view proposals for their UDISE code
"""

import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.database.db import get_db
from app.database.models import User

log = logging.getLogger(__name__)

# ── Config
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from config import JWT_SECRET_KEY, JWT_EXPIRE_HOURS

SECRET_KEY         = JWT_SECRET_KEY
ALGORITHM          = "HS256"
TOKEN_EXPIRE_HOURS = JWT_EXPIRE_HOURS

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Pydantic models
class Token(BaseModel):
    access_token: str
    token_type:   str
    role:         str
    username:     str
    school_pseudocode: Optional[str] = None


class TokenData(BaseModel):
    username:          str
    role:              str
    school_pseudocode: Optional[str] = None


import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


# ── JWT helpers
def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(
            username          = payload["sub"],
            role              = payload["role"],
            school_pseudocode = payload.get("school_pseudocode"),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Current user dependency
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db:    Session = Depends(get_db),
) -> "User":
    token_data = decode_token(token)
    user = db.query(User).filter(User.username == token_data.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_admin(current_user: "User" = Depends(get_current_user)) -> "User":
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def require_principal(current_user: "User" = Depends(get_current_user)) -> "User":
    if current_user.role not in ("principal", "admin"):
        raise HTTPException(status_code=403, detail="Principal or admin access required")
    return current_user


def get_current_user_optional(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)),
    db:    Session = Depends(get_db),
) -> Optional["User"]:
    """Non-blocking auth — returns None if no token (for public endpoints)."""
    if not token:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None