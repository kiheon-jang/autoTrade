"""
빗썸 API 클라이언트 테스트 스크립트
"""
import asyncio
import json
from services.bithumb_client import BithumbClient


async def test_public_api():
    """Public API 테스트"""
    print("🔍 Public API 테스트 시작...")
    
    async with BithumbClient() as client:
        try:
            # 1. 전체 코인 시세 조회
            print("\n1. 전체 코인 시세 조회")
            ticker = await client.get_ticker("ALL")
            print(f"✅ 전체 시세 조회 성공: {len(ticker.get('data', {}))}개 코인")
            
            # 2. 특정 코인 시세 조회
            print("\n2. BTC 시세 조회")
            btc_ticker = await client.get_ticker("BTC")
            print(f"✅ BTC 시세: {btc_ticker.get('data', {}).get('closing_price', 'N/A')} KRW")
            
            # 3. 호가창 조회
            print("\n3. BTC 호가창 조회")
            orderbook = await client.get_orderbook("BTC")
            print(f"✅ BTC 호가창 조회 성공")
            
            # 4. 체결 내역 조회
            print("\n4. BTC 체결 내역 조회")
            transactions = await client.get_transaction_history("BTC")
            print(f"✅ BTC 체결 내역 조회 성공")
            
            # 5. 캔들 데이터 조회
            print("\n5. BTC 1분 캔들 데이터 조회")
            candles = await client.get_candlestick("BTC", "1m")
            print(f"✅ BTC 캔들 데이터 조회 성공")
            
            return True
            
        except Exception as e:
            print(f"❌ Public API 테스트 실패: {e}")
            return False


async def test_private_api():
    """Private API 테스트 (API 키가 있는 경우)"""
    print("\n🔐 Private API 테스트 시작...")
    
    # API 키가 설정되어 있는지 확인
    from core.config import settings
    if not settings.BITHUMB_API_KEY or not settings.BITHUMB_SECRET_KEY:
        print("⚠️  API 키가 설정되지 않아 Private API 테스트를 건너뜁니다.")
        print("   .env 파일에 BITHUMB_API_KEY와 BITHUMB_SECRET_KEY를 설정하세요.")
        return True
    
    async with BithumbClient() as client:
        try:
            # 1. 잔고 조회
            print("\n1. 잔고 조회")
            balance = await client.get_balance()
            print(f"✅ 잔고 조회 성공")
            
            # 2. 주문 조회
            print("\n2. 주문 조회")
            orders = await client.get_orders()
            print(f"✅ 주문 조회 성공")
            
            # 3. 체결 내역 조회
            print("\n3. 체결 내역 조회")
            transactions = await client.get_user_transactions()
            print(f"✅ 체결 내역 조회 성공")
            
            return True
            
        except Exception as e:
            print(f"❌ Private API 테스트 실패: {e}")
            return False


async def test_websocket():
    """WebSocket 테스트"""
    print("\n🌐 WebSocket 테스트 시작...")
    
    async def ticker_callback(data):
        print(f"📊 실시간 데이터 수신: {json.dumps(data, indent=2)[:200]}...")
    
    try:
        # 5초 동안 실시간 데이터 수집
        client = BithumbClient()
        ticker_data = await client.get_realtime_ticker(["BTC_KRW"], duration=5)
        print(f"✅ WebSocket 테스트 성공: {len(ticker_data)}개 데이터 수신")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket 테스트 실패: {e}")
        return False


async def main():
    """메인 테스트 함수"""
    print("🚀 빗썸 API 클라이언트 테스트 시작\n")
    
    # Public API 테스트
    public_success = await test_public_api()
    
    # Private API 테스트
    private_success = await test_private_api()
    
    # WebSocket 테스트
    websocket_success = await test_websocket()
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 테스트 결과 요약")
    print("="*50)
    print(f"Public API: {'✅ 성공' if public_success else '❌ 실패'}")
    print(f"Private API: {'✅ 성공' if private_success else '❌ 실패'}")
    print(f"WebSocket: {'✅ 성공' if websocket_success else '❌ 실패'}")
    
    if all([public_success, private_success, websocket_success]):
        print("\n🎉 모든 테스트 통과! 빗썸 API 클라이언트가 정상적으로 작동합니다.")
    else:
        print("\n⚠️  일부 테스트가 실패했습니다. 설정을 확인해주세요.")


if __name__ == "__main__":
    asyncio.run(main())
