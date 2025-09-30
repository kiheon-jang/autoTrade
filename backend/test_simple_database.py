"""
간단한 데이터베이스 연결 테스트
SQLite를 사용한 기본 데이터베이스 연동 테스트
"""
import asyncio
import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(__file__))

async def test_sqlite_connection():
    """SQLite 데이터베이스 연결 테스트"""
    print("=== SQLite 데이터베이스 연결 테스트 ===")
    
    try:
        from core.database import engine, timescale_engine, Base, TimescaleBase
        from models.user import User
        from models.market_data import Ticker
        
        print("1. SQLite 데이터베이스 연결 테스트...")
        
        # 테이블 생성
        Base.metadata.create_all(bind=engine)
        TimescaleBase.metadata.create_all(bind=timescale_engine)
        print("   ✅ 테이블 생성 완료")
        
        # PostgreSQL 테스트
        print("2. PostgreSQL (SQLite) 사용자 데이터 테스트...")
        from core.database import get_db
        db = next(get_db())
        
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
        print("3. TimescaleDB (SQLite) 시장 데이터 테스트...")
        from core.database import get_timescale_db
        ts_db = next(get_timescale_db())
        
        # 테스트 티커 데이터 생성
        test_ticker = Ticker(
            symbol="BTC_KRW",
            timestamp=datetime.now(),
            opening_price=160000000.0,
            closing_price=162014000.0,
            high_price=165000000.0,
            low_price=158000000.0,
            volume=1000000.0,
            value=162014000000000.0,
            change_24h=2014000.0,
            change_rate_24h=0.0126,
            bid_price=161900000.0,
            ask_price=162100000.0,
            spread=200000.0
        )
        
        ts_db.add(test_ticker)
        ts_db.commit()
        ts_db.refresh(test_ticker)
        
        print(f"   ✅ 티커 데이터 생성 성공: ID {test_ticker.id}")
        
        # 데이터 조회 테스트
        print("4. 데이터 조회 테스트...")
        users = db.query(User).all()
        tickers = ts_db.query(Ticker).all()
        
        print(f"   ✅ 사용자 수: {len(users)}")
        print(f"   ✅ 티커 데이터 수: {len(tickers)}")
        
        # 정리
        db.delete(test_user)
        db.commit()
        ts_db.delete(test_ticker)
        ts_db.commit()
        
        print("✅ 모든 데이터베이스 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 간단한 데이터베이스 연동 테스트 시작\n")
    
    success = await test_sqlite_connection()
    
    if success:
        print("\n🎉 데이터베이스 연동 성공!")
        print("✅ SQLite: 사용자 데이터 저장/조회")
        print("✅ SQLite: 시계열 시장 데이터 저장/조회")
    else:
        print("\n❌ 데이터베이스 연동 실패")

if __name__ == "__main__":
    asyncio.run(main())
