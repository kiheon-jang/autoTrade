"""
빗썸 클라이언트를 사용한 API 테스트
"""
import asyncio
import os
from dotenv import load_dotenv
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from services.bithumb_client import BithumbClient

# 환경 변수 로드
load_dotenv('../../.env')

async def test_bithumb_client():
    """빗썸 클라이언트 테스트"""
    print("=== 빗썸 클라이언트 테스트 ===")
    
    # API 키 확인 (새로운 키 사용)
    api_key = "13fe3082684f7e859cec64bbd06740be"
    secret_key = "7df353db18bc2fc7875631be6c565a70"
    
    print(f"API Key: {api_key[:10]}..." if api_key else "API Key: None")
    print(f"Secret Key: {secret_key[:10]}..." if secret_key else "Secret Key: None")
    
    if not api_key or not secret_key:
        print("❌ API 키가 환경 변수에 설정되지 않았습니다.")
        return
    
    # 빗썸 클라이언트 생성
    client = BithumbClient(api_key, secret_key)
    
    try:
        # 1. 공개 API 테스트
        print("\n1. 공개 API 테스트...")
        ticker = await client.get_ticker("BTC")
        print(f"   BTC 현재가: {ticker['data']['closing_price']}원")
        print("✅ 공개 API 정상 작동")
        
        # 2. 개인 API 테스트
        print("\n2. 개인 API 테스트...")
        balance = await client.get_balance()
        print(f"   잔고 정보: {balance}")
        print("✅ 개인 API 인증 성공!")
        
        # 3. 주문 조회 테스트
        print("\n3. 주문 조회 테스트...")
        orders = await client.get_orders("BTC", "KRW")
        print(f"   주문 정보: {orders}")
        print("✅ 주문 조회 성공!")
        
        # 4. 체결 내역 테스트
        print("\n4. 체결 내역 테스트...")
        transactions = await client.get_user_transactions("BTC", "KRW")
        print(f"   체결 내역: {transactions}")
        print("✅ 체결 내역 조회 성공!")
        
        print("\n🎉 모든 API 테스트 성공!")
        return True
        
    except Exception as e:
        print(f"❌ API 테스트 실패: {e}")
        return False
    finally:
        await client.http_client.aclose()

if __name__ == "__main__":
    asyncio.run(test_bithumb_client())
