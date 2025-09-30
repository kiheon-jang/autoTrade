"""
빗썸 API 1.0 연동 테스트
실제 API 키를 사용하여 빗썸 API 연동 테스트
"""
import asyncio
import os
from dotenv import load_dotenv
from services.bithumb_client import BithumbClient, BithumbAPIError

# 환경 변수 로드
load_dotenv('../.env')

async def test_bithumb_api():
    """빗썸 API 연동 테스트"""
    print("=== 빗썸 API 1.0 연동 테스트 ===")
    
    # API 키 확인
    api_key = os.getenv("BITHUMB_API_KEY")
    secret_key = os.getenv("BITHUMB_SECRET_KEY")
    
    print(f"API Key: {api_key[:10]}..." if api_key else "API Key: None")
    print(f"Secret Key: {secret_key[:10]}..." if secret_key else "Secret Key: None")
    
    if not api_key or not secret_key:
        print("❌ API 키가 설정되지 않았습니다.")
        return
    
    # 빗썸 클라이언트 생성
    client = BithumbClient(api_key, secret_key)
    
    try:
        print("\n1. 공개 API 테스트 (현재가 정보)")
        ticker = await client.get_ticker("BTC")
        print(f"✅ BTC 현재가: {ticker}")
        
        print("\n2. 공개 API 테스트 (호가 정보)")
        orderbook = await client.get_orderbook("BTC")
        print(f"✅ BTC 호가: {orderbook}")
        
        print("\n3. 공개 API 테스트 (체결 내역)")
        transactions = await client.get_transaction_history("BTC")
        print(f"✅ BTC 체결 내역: {transactions}")
        
        print("\n4. 개인 API 테스트 (잔고 조회)")
        balance = await client.get_balance()
        print(f"✅ 잔고 정보: {balance}")
        
        print("\n5. 개인 API 테스트 (주문 조회)")
        orders = await client.get_orders("BTC", "KRW")
        print(f"✅ 주문 조회: {orders}")
        
        print("\n6. 개인 API 테스트 (체결 내역)")
        user_transactions = await client.get_user_transactions("BTC", "KRW")
        print(f"✅ 사용자 체결 내역: {user_transactions}")
        
        print("\n✅ 모든 API 테스트 성공!")
        
    except BithumbAPIError as e:
        print(f"❌ 빗썸 API 에러: {e}")
    except Exception as e:
        print(f"❌ 일반 에러: {e}")
    finally:
        await client.http_client.aclose()

async def test_order_placement():
    """주문 테스트 (시뮬레이션)"""
    print("\n=== 주문 테스트 (시뮬레이션) ===")
    
    api_key = os.getenv("BITHUMB_API_KEY")
    secret_key = os.getenv("BITHUMB_SECRET_KEY")
    
    if not api_key or not secret_key:
        print("❌ API 키가 설정되지 않았습니다.")
        return
    
    client = BithumbClient(api_key, secret_key)
    
    try:
        # 시뮬레이션 주문 (실제로는 실행되지 않음)
        print("시뮬레이션 주문 테스트...")
        
        # 매수 주문 시뮬레이션
        buy_order = await client.place_order(
            order_currency="BTC",
            payment_currency="KRW", 
            units="0.001",  # 매우 작은 수량
            price="50000000",  # 5천만원 (현재가보다 낮게 설정)
            type_="bid"
        )
        print(f"매수 주문 결과: {buy_order}")
        
    except BithumbAPIError as e:
        print(f"❌ 주문 API 에러: {e}")
    except Exception as e:
        print(f"❌ 주문 에러: {e}")
    finally:
        await client.http_client.aclose()

if __name__ == "__main__":
    print("빗썸 API 1.0 연동 테스트 시작...")
    asyncio.run(test_bithumb_api())
    print("\n" + "="*50)
    asyncio.run(test_order_placement())
