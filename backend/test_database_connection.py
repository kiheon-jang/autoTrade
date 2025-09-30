"""
데이터베이스 연결 테스트 스크립트
PostgreSQL, TimescaleDB, Redis 연결 확인
"""
import asyncio
import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(__file__))

async def test_database_connections():
    """데이터베이스 연결 테스트"""
    print("=== 데이터베이스 연결 테스트 ===")
    
    try:
        from core.database import test_connections, init_database
        from core.config import settings
        
        print(f"1. PostgreSQL URL: {settings.DATABASE_URL}")
        print(f"2. TimescaleDB URL: {settings.TIMESCALE_URL}")
        print(f"3. Redis URL: {settings.REDIS_URL}")
        
        # 연결 테스트
        print("\n4. 데이터베이스 연결 테스트 중...")
        success = test_connections()
        
        if success:
            print("✅ 모든 데이터베이스 연결 성공!")
            
            # 데이터베이스 초기화
            print("\n5. 데이터베이스 초기화 중...")
            init_database()
            print("✅ 데이터베이스 초기화 완료!")
            
        else:
            print("❌ 데이터베이스 연결 실패")
            return False
            
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {e}")
        return False
    
    return True

async def test_data_operations():
    """데이터베이스 작업 테스트"""
    print("\n=== 데이터베이스 작업 테스트 ===")
    
    try:
        from core.database import get_db, get_timescale_db, get_redis
        from models.market_data import Ticker
        from models.user import User
        from sqlalchemy.orm import Session
        
        # PostgreSQL 테스트
        print("1. PostgreSQL 사용자 데이터 테스트...")
        db: Session = next(get_db())
        
        # 테스트 사용자 생성
        test_user = User(
            username="test_user",
            email="test@example.com",
            hashed_password="test_password_hash"
        )
        
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"   ✅ 사용자 생성 성공: ID {test_user.id}")
        
        # TimescaleDB 테스트
        print("2. TimescaleDB 시장 데이터 테스트...")
        ts_db: Session = next(get_timescale_db())
        
        # 테스트 티커 데이터 생성
        test_ticker = Ticker(
            exchange="bithumb",
            symbol="BTC",
            price=162014000.0,
            volume=1000000.0,
            timestamp=datetime.now()
        )
        
        ts_db.add(test_ticker)
        ts_db.commit()
        ts_db.refresh(test_ticker)
        
        print(f"   ✅ 티커 데이터 생성 성공: ID {test_ticker.id}")
        
        # Redis 테스트
        print("3. Redis 캐시 테스트...")
        redis_client = get_redis()
        
        # 캐시 데이터 저장
        redis_client.set("test_key", "test_value", ex=60)
        cached_value = redis_client.get("test_key")
        
        print(f"   ✅ Redis 캐시 테스트 성공: {cached_value}")
        
        # 정리
        db.delete(test_user)
        db.commit()
        ts_db.delete(test_ticker)
        ts_db.commit()
        redis_client.delete("test_key")
        
        print("✅ 모든 데이터베이스 작업 테스트 성공!")
        
    except Exception as e:
        print(f"❌ 데이터베이스 작업 테스트 실패: {e}")
        return False
    
    return True

async def main():
    """메인 테스트 함수"""
    print("🚀 데이터베이스 연동 테스트 시작\n")
    
    # 연결 테스트
    connection_success = await test_database_connections()
    if not connection_success:
        print("\n❌ 데이터베이스 연결 실패로 테스트 중단")
        return
    
    # 데이터 작업 테스트
    operation_success = await test_data_operations()
    if not operation_success:
        print("\n❌ 데이터베이스 작업 실패")
        return
    
    print("\n🎉 모든 데이터베이스 테스트 성공!")
    print("✅ PostgreSQL: 사용자 데이터 저장/조회")
    print("✅ TimescaleDB: 시계열 시장 데이터 저장/조회")
    print("✅ Redis: 실시간 캐싱")

if __name__ == "__main__":
    asyncio.run(main())
