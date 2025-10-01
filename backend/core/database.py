"""
데이터베이스 연결 및 설정
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator, Optional
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# 데이터베이스 엔진 (선택적)
engine = None
timescale_engine = None
SessionLocal = None
TimescaleSessionLocal = None
redis_client = None
Base = declarative_base()
TimescaleBase = declarative_base()

# 데이터베이스 초기화 시도 (실패해도 계속 진행)
try:
    # SQLite 데이터베이스 엔진
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    
    # 시계열 데이터용 엔진
    timescale_engine = create_engine(
        settings.TIMESCALE_URL,
        echo=settings.DEBUG,
        connect_args={"check_same_thread": False} if "sqlite" in settings.TIMESCALE_URL else {}
    )
    
    # 세션 팩토리
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    TimescaleSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=timescale_engine)
    
    logger.info("데이터베이스 연결 성공")
except Exception as e:
    logger.warning(f"데이터베이스 연결 실패 (메모리 모드로 계속): {e}")
    SessionLocal = lambda: None
    TimescaleSessionLocal = lambda: None


def get_db() -> Generator:
    """데이터베이스 세션 의존성 (optional)"""
    if SessionLocal is None:
        yield None
        return
    
    db = SessionLocal()
    try:
        yield db
    finally:
        if db:
            db.close()


def get_timescale_db() -> Generator:
    """시계열 데이터베이스 세션 의존성 (optional)"""
    if TimescaleSessionLocal is None:
        yield None
        return
        
    db = TimescaleSessionLocal()
    try:
        yield db
    finally:
        if db:
            db.close()


def get_redis():
    """Redis 클라이언트 반환 (로컬 개발용으로 None 반환)"""
    return redis_client


def create_tables():
    """데이터베이스 테이블 생성 (optional)"""
    if not engine or not timescale_engine:
        logger.info("데이터베이스 미사용 - 테이블 생성 건너뜀")
        return
        
    try:
        # 모든 모델 임포트
        from models.user import User, UserSession
        from models.strategy import Strategy, StrategyExecution, BacktestResult
        from models.order import Order, Trade, Position, Portfolio
        from models.market_data import Ticker, OrderBook, Transaction, Candle, TechnicalIndicator
        
        # 데이터베이스 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("데이터베이스 테이블 생성 완료")
        
        # 시계열 테이블 생성
        TimescaleBase.metadata.create_all(bind=timescale_engine)
        logger.info("시계열 데이터 테이블 생성 완료")
        
    except Exception as e:
        logger.warning(f"데이터베이스 테이블 생성 실패 (계속 진행): {e}")


def test_connections():
    """데이터베이스 연결 테스트 (optional)"""
    if not engine:
        logger.info("데이터베이스 미사용 모드")
        return True
        
    try:
        # 메인 데이터베이스 연결 테스트
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("메인 데이터베이스 연결 성공")
        
        # 시계열 데이터베이스 연결 테스트
        if timescale_engine:
            with timescale_engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("시계열 데이터베이스 연결 성공")
        
        return True
        
    except Exception as e:
        logger.warning(f"데이터베이스 연결 테스트 실패 (계속 진행): {e}")
        return True  # 실패해도 계속 진행


# 데이터베이스 초기화 함수
def init_database():
    """데이터베이스 초기화 (optional)"""
    logger.info("데이터베이스 초기화 시작")
    
    # 연결 테스트
    test_connections()
    
    # 테이블 생성
    create_tables()
    
    logger.info("데이터베이스 초기화 완료")
