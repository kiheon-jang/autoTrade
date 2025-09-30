"""
빗썸 API 클라이언트 테스트 스크립트 (수정된 버전)
"""
import asyncio
import json
from services.bithumb_client_fixed import BithumbClient


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
            btc_data = btc_ticker.get('data', {})
            print(f"✅ BTC 시세: {btc_data.get('closing_price', 'N/A')} KRW")
            print(f"   변동률: {btc_data.get('fluctate_rate_1D', 'N/A')}%")
            
            # 3. 호가창 조회
            print("\n3. BTC 호가창 조회")
            orderbook = await client.get_orderbook("BTC")
            orderbook_data = orderbook.get('data', {})
            print(f"✅ BTC 호가창 조회 성공")
            print(f"   매수 최고가: {orderbook_data.get('bids', [{}])[0].get('price', 'N/A')} KRW")
            print(f"   매도 최저가: {orderbook_data.get('asks', [{}])[0].get('price', 'N/A')} KRW")
            
            # 4. 체결 내역 조회
            print("\n4. BTC 체결 내역 조회")
            transactions = await client.get_transaction_history("BTC")
            transaction_data = transactions.get('data', [])
            print(f"✅ BTC 체결 내역 조회 성공: {len(transaction_data)}건")
            if transaction_data:
                latest = transaction_data[0]
                print(f"   최신 체결: {latest.get('price', 'N/A')} KRW, {latest.get('units_traded', 'N/A')} BTC")
            
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
            balance_data = balance.get('data', {})
            print(f"✅ 잔고 조회 성공")
            print(f"   KRW 잔고: {balance_data.get('total_krw', 'N/A')} KRW")
            print(f"   BTC 잔고: {balance_data.get('total_btc', 'N/A')} BTC")
            
            # 2. 주문 조회
            print("\n2. 주문 조회")
            orders = await client.get_orders()
            orders_data = orders.get('data', [])
            print(f"✅ 주문 조회 성공: {len(orders_data)}건")
            
            # 3. 체결 내역 조회
            print("\n3. 체결 내역 조회")
            transactions = await client.get_user_transactions()
            transactions_data = transactions.get('data', [])
            print(f"✅ 체결 내역 조회 성공: {len(transactions_data)}건")
            
            return True
            
        except Exception as e:
            print(f"❌ Private API 테스트 실패: {e}")
            return False


async def test_websocket():
    """WebSocket 테스트"""
    print("\n🌐 WebSocket 테스트 시작...")
    
    try:
        # 3초 동안 실시간 데이터 수집
        client = BithumbClient()
        print("WebSocket 연결 시도 중...")
        ticker_data = await client.get_realtime_ticker(["BTC_KRW"], duration=3)
        print(f"✅ WebSocket 테스트 성공: {len(ticker_data)}개 데이터 수신")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket 테스트 실패: {e}")
        return False


async def main():
    """메인 테스트 함수"""
    print("🚀 빗썸 API 클라이언트 테스트 시작 (수정된 버전)\n")
    
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
