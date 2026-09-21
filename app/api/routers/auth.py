from fastapi import APIRouter, Depends, Response, HTTPException, Request
from pydantic import BaseModel
import jwt
import secrets
from datetime import datetime, timedelta
from passlib.hash import argon2

from app.api.dependencies import get_current_user, get_database
from app.core.config import JWT_SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, COOKIE_SECURE
from app.core.database import DatabaseManager

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
def login(req: LoginRequest, response: Response, db: DatabaseManager = Depends(get_database)):
    with db.connect() as conn:
        user = conn.execute("SELECT password_hash FROM users WHERE username = %s", (req.username,)).fetchone()
        
    if not user or not argon2.verify(req.password, user[0]):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu")
        
    # Generate CSRF token
    csrf_token = secrets.token_hex(32)
    
    # Generate JWT containing username and csrf_token
    token_data = {"sub": req.username, "csrf": csrf_token}
    token = create_access_token(token_data)
    
    # Set HttpOnly Cookie for JWT
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    # Return CSRF token in JSON so frontend can store in state or localStorage
    # to send back in X-CSRF-Token header
    return {"username": req.username, "csrf_token": csrf_token}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Đăng xuất thành công"}

@router.get("/me")
def get_me(request: Request, user: str = Depends(get_current_user), db: DatabaseManager = Depends(get_database)):
    token = request.cookies.get("access_token")
    csrf_token = ""
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
            csrf_token = payload.get("csrf", "")
        except Exception:
            pass
    with db.connect() as conn:
        row = conn.execute("SELECT role FROM users WHERE username = %s", (user,)).fetchone()
    return {"user": user, "username": user, "role": row[0] if row else "user", "csrf_token": csrf_token}
