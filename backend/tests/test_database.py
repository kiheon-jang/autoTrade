"""
데이터베이스 연결 및 스키마 테스트 스크립트
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import init_database, test_connections, get_db, get_redis
from models.user import User, UserSession
from models.strategy import Strategy
from models.order import Order, OrderType, OrderStatus
from models.market_data import Ticker, Candle
from sqlalchemy.orm import Session


def test_database_connections():
    """데이터베이스 연결 테스트"""
    print("🔍 데이터베이스 연결 테스트 시작...")
    
    try:
        # 연결 테스트
        success = test_connections()
        if success:
            print("✅ 모든 데이터베이스 연결 성공")
            return True
        else:
            print("❌ 데이터베이스 연결 실패")
            return False
    except Exception as e:
        print(f"❌ 데이터베이스 연결 테스트 실패: {e}")
        return False


def test_database_initialization():
    """데이터베이스 초기화 테스트"""
    print("\n🏗️ 데이터베이스 초기화 테스트 시작...")
    
    try:
        init_database()
        print("✅ 데이터베이스 초기화 성공")
        return True
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")
        return False


def test_model_operations():
    """모델 CRUD 작업 테스트"""
    print("\n📊 모델 CRUD 작업 테스트 시작...")
    
    try:
        db = next(get_db())
        
        # 1. 사용자 생성 테스트
        print("1. 사용자 생성 테스트")
        test_user = User(
            username="test_user",
            email="test@example.com",
            hashed_password="hashed_password_here",
            bithumb_api_key="test_api_key",
            bithumb_secret_key="test_secret_key"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"✅ 사용자 생성 성공: ID={test_user.id}")
        
        # 2. 전략 생성 테스트
        print("2. 전략 생성 테스트")
        test_strategy = Strategy(
            user_id=test_user.id,
            name="Test Strategy",
            strategy_type="scalping",
            parameters={"ema_short": 8, "ema_long": 21},
            risk_per_trade=2.0,
            max_positions=3
        )
        db.add(test_strategy)
        db.commit()
        db.refresh(test_strategy)
        print(f"✅ 전략 생성 성공: ID={test_strategy.id}")
        
        # 3. 주문 생성 테스트
        print("3. 주문 생성 테스트")
        test_order = Order(
            user_id=test_user.id,
            strategy_id=test_strategy.id,
            symbol="BTC_KRW",
            order_type=OrderType.BUY,
            order_side="bid",
            quantity=0.001,
            price=50000000.0,
            remaining_quantity=0.001,
            status=OrderStatus.PENDING
        )
        db.add(test_order)
        db.commit()
        db.refresh(test_order)
        print(f"✅ 주문 생성 성공: ID={test_order.id}")
        
        # 4. 시세 데이터 생성 테스트
        print("4. 시세 데이터 생성 테스트")
        test_ticker = Ticker(
            symbol="BTC_KRW",
            timestamp=datetime.now(),
            opening_price=50000000.0,
            closing_price=50100000.0,
            high_price=50200000.0,
            low_price=49900000.0,
            volume=100.0,
            value=5000000000.0,
            change_24h=100000.0,
            change_rate_24h=0.2
        )
        db.add(test_ticker)
        db.commit()
        db.refresh(test_ticker)
        print(f"✅ 시세 데이터 생성 성공: ID={test_ticker.id}")
        
        # 5. 캔들 데이터 생성 테스트
        print("5. 캔들 데이터 생성 테스트")
        test_candle = Candle(
            symbol="BTC_KRW",
            timeframe="1m",
            timestamp=datetime.now(),
            open_price=50000000.0,
            high_price=50100000.0,
            low_price=49900000.0,
            close_price=50050000.0,
            volume=50.0
        )
        db.add(test_candle)
        db.commit()
        db.refresh(test_candle)
        print(f"✅ 캔들 데이터 생성 성공: ID={test_candle.id}")
        
        # 6. 데이터 조회 테스트
        print("6. 데이터 조회 테스트")
        users = db.query(User).all()
        strategies = db.query(Strategy).all()
        orders = db.query(Order).all()
        tickers = db.query(Ticker).all()
        
        print(f"✅ 사용자 조회: {len(users)}명")
        print(f"✅ 전략 조회: {len(strategies)}개")
        print(f"✅ 주문 조회: {len(orders)}건")
        print(f"✅ 시세 조회: {len(tickers)}건")
        
        # 7. 데이터 업데이트 테스트
        print("7. 데이터 업데이트 테스트")
        test_user.is_active = False
        test_strategy.is_active = True
        test_order.status = OrderStatus.FILLED
        db.commit()
        print("✅ 데이터 업데이트 성공")
        
        # 8. 데이터 삭제 테스트
        print("8. 데이터 삭제 테스트")
        db.delete(test_order)
        db.delete(test_strategy)
        db.delete(test_user)
        db.delete(test_ticker)
        db.delete(test_candle)
        db.commit()
        print("✅ 데이터 삭제 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ 모델 CRUD 작업 실패: {e}")
        return False
    finally:
        db.close()


def test_redis_operations():
    """Redis 작업 테스트"""
    print("\n🔴 Redis 작업 테스트 시작...")
    
    try:
        redis_client = get_redis()
        
        # 1. 기본 작업 테스트
        print("1. Redis 기본 작업 테스트")
        redis_client.set("test_key", "test_value", ex=60)
        value = redis_client.get("test_key")
        print(f"✅ Redis SET/GET 성공: {value}")
        
        # 2. 해시 작업 테스트
        print("2. Redis 해시 작업 테스트")
        redis_client.hset("test_hash", mapping={"field1": "value1", "field2": "value2"})
        hash_data = redis_client.hgetall("test_hash")
        print(f"✅ Redis 해시 작업 성공: {hash_data}")
        
        # 3. 리스트 작업 테스트
        print("3. Redis 리스트 작업 테스트")
        redis_client.lpush("test_list", "item1", "item2", "item3")
        list_data = redis_client.lrange("test_list", 0, -1)
        print(f"✅ Redis 리스트 작업 성공: {list_data}")
        
        # 4. 정리
        redis_client.delete("test_key", "test_hash", "test_list")
        print("✅ Redis 데이터 정리 완료")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis 작업 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 데이터베이스 테스트 시작\n")
    
    # 1. 연결 테스트
    connection_success = test_database_connections()
    
    # 2. 초기화 테스트
    init_success = test_database_initialization()
    
    # 3. 모델 작업 테스트
    model_success = test_model_operations()
    
    # 4. Redis 작업 테스트
    redis_success = test_redis_operations()
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 데이터베이스 테스트 결과 요약")
    print("="*50)
    print(f"데이터베이스 연결: {'✅ 성공' if connection_success else '❌ 실패'}")
    print(f"데이터베이스 초기화: {'✅ 성공' if init_success else '❌ 실패'}")
    print(f"모델 CRUD 작업: {'✅ 성공' if model_success else '❌ 실패'}")
    print(f"Redis 작업: {'✅ 성공' if redis_success else '❌ 실패'}")
    
    if all([connection_success, init_success, model_success, redis_success]):
        print("\n🎉 모든 데이터베이스 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 설정을 확인해주세요.")


if __name__ == "__main__":
    main()
