"""
데이터베이스 연결 및 설정
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import redis
from typing import Generator
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# PostgreSQL 데이터베이스 엔진
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# TimescaleDB 엔진 (시계열 데이터용)
timescale_engine = create_engine(
    settings.TIMESCALE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# 세션 팩토리
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TimescaleSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=timescale_engine)

# Redis 연결
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

# 베이스 클래스
Base = declarative_base()
TimescaleBase = declarative_base()


def get_db() -> Generator:
    """PostgreSQL 데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_timescale_db() -> Generator:
    """TimescaleDB 세션 의존성"""
    db = TimescaleSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> redis.Redis:
    """Redis 클라이언트 반환"""
    return redis_client


def create_tables():
    """데이터베이스 테이블 생성"""
    try:
        # 모든 모델 임포트
        from models.user import User, UserSession
        from models.strategy import Strategy, StrategyExecution, BacktestResult
        from models.order import Order, Trade, Position, Portfolio
        from models.market_data import Ticker, OrderBook, Transaction, Candle, TechnicalIndicator
        
        # PostgreSQL 테이블 생성
        Base.metadata.create_all(bind=engine)
        logger.info("PostgreSQL 테이블 생성 완료")
        
        # TimescaleDB 테이블 생성
        TimescaleBase.metadata.create_all(bind=timescale_engine)
        logger.info("TimescaleDB 테이블 생성 완료")
        
        # TimescaleDB 하이퍼테이블 설정
        with timescale_engine.connect() as conn:
            # 시계열 테이블을 하이퍼테이블로 변환
            conn.execute("SELECT create_hypertable('tickers', 'timestamp', if_not_exists => TRUE)")
            conn.execute("SELECT create_hypertable('orderbooks', 'timestamp', if_not_exists => TRUE)")
            conn.execute("SELECT create_hypertable('transactions', 'timestamp', if_not_exists => TRUE)")
            conn.execute("SELECT create_hypertable('candles', 'timestamp', if_not_exists => TRUE)")
            conn.execute("SELECT create_hypertable('technical_indicators', 'timestamp', if_not_exists => TRUE)")
            
            # 데이터 보존 정책 설정 (30일)
            conn.execute("SELECT add_retention_policy('tickers', INTERVAL '30 days', if_not_exists => TRUE)")
            conn.execute("SELECT add_retention_policy('orderbooks', INTERVAL '30 days', if_not_exists => TRUE)")
            conn.execute("SELECT add_retention_policy('transactions', INTERVAL '30 days', if_not_exists => TRUE)")
            conn.execute("SELECT add_retention_policy('candles', INTERVAL '30 days', if_not_exists => TRUE)")
            conn.execute("SELECT add_retention_policy('technical_indicators', INTERVAL '30 days', if_not_exists => TRUE)")
            
        logger.info("TimescaleDB 하이퍼테이블 설정 완료")
        
    except Exception as e:
        logger.error(f"데이터베이스 테이블 생성 실패: {e}")
        raise


def test_connections():
    """데이터베이스 연결 테스트"""
    try:
        # PostgreSQL 연결 테스트
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("PostgreSQL 연결 성공")
        
        # TimescaleDB 연결 테스트
        with timescale_engine.connect() as conn:
            conn.execute("SELECT 1")
        logger.info("TimescaleDB 연결 성공")
        
        # Redis 연결 테스트
        redis_client.ping()
        logger.info("Redis 연결 성공")
        
        return True
        
    except Exception as e:
        logger.error(f"데이터베이스 연결 테스트 실패: {e}")
        return False


# 데이터베이스 초기화 함수
def init_database():
    """데이터베이스 초기화"""
    logger.info("데이터베이스 초기화 시작")
    
    # 연결 테스트
    if not test_connections():
        raise Exception("데이터베이스 연결 실패")
    
    # 테이블 생성
    create_tables()
    
    logger.info("데이터베이스 초기화 완료")
