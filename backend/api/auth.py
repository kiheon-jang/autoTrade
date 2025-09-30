"""
인증 관련 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from models.user import User, UserSession
from core.database import get_db
from datetime import datetime, timedelta
import secrets

router = APIRouter()
security = HTTPBearer()


class UserRegister(BaseModel):
    """사용자 등록 요청"""
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """사용자 로그인 요청"""
    username: str
    password: str


class APIKeyRegister(BaseModel):
    """빗썸 API 키 등록 요청"""
    api_key: str
    secret_key: str


@router.post("/register")
async def register_user(user: UserRegister, db: Session = Depends(get_db)):
    """사용자 등록"""
    try:
        # 중복 사용자 확인
        existing_user = db.query(User).filter(
            (User.username == user.username) | 
            (User.email == user.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="Username or email already exists"
            )
        
        # 새 사용자 생성
        new_user = User(
            username=user.username,
            email=user.email,
            hashed_password=user.password,  # 실제로는 해시화 필요
            is_active=True,
            is_verified=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": new_user.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login")
async def login_user(user: UserLogin, db: Session = Depends(get_db)):
    """사용자 로그인"""
    try:
        # 사용자 확인
        user_obj = db.query(User).filter(User.username == user.username).first()
        
        if not user_obj or not user_obj.is_active:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        # 비밀번호 확인 (실제로는 해시 비교 필요)
        if user_obj.hashed_password != user.password:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )
        
        # 세션 토큰 생성
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        # 세션 저장
        session = UserSession(
            user_id=user_obj.id,
            session_token=session_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        
        db.add(session)
        user_obj.last_login = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": "Login successful",
            "access_token": session_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/api-keys")
async def register_api_keys(api_keys: APIKeyRegister, db: Session = Depends(get_db)):
    """빗썸 API 키 등록"""
    try:
        # 실제로는 인증된 사용자만 접근 가능해야 함
        # 여기서는 간단히 첫 번째 사용자를 찾아서 업데이트
        user = db.query(User).first()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # API 키 업데이트
        user.bithumb_api_key = api_keys.api_key
        user.bithumb_secret_key = api_keys.secret_key
        
        db.commit()
        
        return {
            "success": True,
            "message": "Bithumb API keys registered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API key registration failed: {str(e)}")


@router.get("/me")
async def get_current_user(token: str = Depends(security), db: Session = Depends(get_db)):
    """현재 사용자 정보 조회"""
    try:
        # 세션 토큰으로 사용자 조회
        session = db.query(UserSession).filter(
            UserSession.session_token == token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )
        
        user = db.query(User).filter(User.id == session.user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        return {
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")
