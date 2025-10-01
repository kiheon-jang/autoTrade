"""
애플리케이션 설정 관리
"""
from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    APP_NAME: str = "Bithumb Auto Trading System"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8008
    
    # 데이터베이스 설정 (SQLite 사용)
    DATABASE_URL: str = "sqlite:///./trading.db"
    REDIS_URL: str = "redis://localhost:6379"
    TIMESCALE_URL: str = "sqlite:///./timescale.db"
    
    # 빗썸 API 설정
    BITHUMB_API_KEY: Optional[str] = None
    BITHUMB_SECRET_KEY: Optional[str] = None
    BITHUMB_BASE_URL: str = "https://api.bithumb.com"
    BITHUMB_WS_URL: str = "wss://pubwss.bithumb.com/pub/ws"
    
    # 보안 설정
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS 설정
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # 리스크 관리 설정
    MAX_RISK_PER_TRADE: float = 0.02  # 2%
    MAX_TOTAL_RISK: float = 0.10      # 10%
    MAX_POSITIONS: int = 5
    
    # 알림 설정
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    
    # 모니터링 설정
    PROMETHEUS_PORT: int = 9090
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()
