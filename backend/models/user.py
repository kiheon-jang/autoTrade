"""
사용자 관련 데이터베이스 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from datetime import datetime
from core.database import Base


class User(Base):
    """사용자 모델"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # 빗썸 API 키 (암호화 저장)
    bithumb_api_key = Column(String(255), nullable=True)
    bithumb_secret_key = Column(String(255), nullable=True)
    
    # 알림 설정
    telegram_chat_id = Column(String(50), nullable=True)
    email_notifications = Column(Boolean, default=True)
    telegram_notifications = Column(Boolean, default=False)
    
    # 거래 설정
    max_risk_per_trade = Column(String(10), default="2.0")  # 2%
    max_total_risk = Column(String(10), default="10.0")     # 10%
    max_positions = Column(Integer, default=5)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"


class UserSession(Base):
    """사용자 세션 모델"""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    refresh_token = Column(String(255), unique=True, index=True, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 지원
    user_agent = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, expires_at='{self.expires_at}')>"
