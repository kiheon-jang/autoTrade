"""
실제 API 연동 테스트 스크립트
빗썸/업비트 API를 통한 실제 시장 데이터 수집 테스트
"""
import asyncio
import sys
import os
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(__file__))

async def test_bithumb_api():
    """빗썸 API 테스트"""
    print("=== 빗썸 API 테스트 ===")
    
    try:
        from services.bithumb_client import BithumbClient
        
        # 빗썸 클라이언트 생성
        client = BithumbClient()
        
        # 공개 API 테스트
        print("1. 빗썸 공개 API 테스트...")
        ticker_data = await client.get_ticker("BTC")
        
        if ticker_data and 'data' in ticker_data:
            data = ticker_data['data']
            print(f"   ✅ BTC 현재가: {data.get('closing_price', 'N/A')}원")
            print(f"   ✅ 24시간 거래량: {data.get('acc_trade_value_24H', 'N/A')}원")
            print(f"   ✅ 24시간 변동률: {data.get('fluctate_rate_24H', 'N/A')}%")
        else:
            print("   ❌ 빗썸 API 응답 오류")
            return False
        
        # 호가 정보 테스트
        print("2. 빗썸 호가 정보 테스트...")
        orderbook_data = await client.get_orderbook("BTC")
        
        if orderbook_data and 'data' in orderbook_data:
            data = orderbook_data['data']
            print(f"   ✅ 매수 호가: {data.get('bids', [])[:3]}")
            print(f"   ✅ 매도 호가: {data.get('asks', [])[:3]}")
        else:
            print("   ❌ 호가 정보 조회 실패")
        
        return True
        
    except Exception as e:
        print(f"❌ 빗썸 API 테스트 실패: {e}")
        return False

async def test_realtime_collector():
    """실시간 데이터 수집기 테스트"""
    print("\n=== 실시간 데이터 수집기 테스트 ===")
    
    try:
        from data.realtime_collector import RealtimeDataCollector
        
        collector = RealtimeDataCollector()
        
        # 빗썸 데이터 수집 테스트
        print("1. 빗썸 데이터 수집 테스트...")
        bithumb_data = await collector._fetch_bithumb_data("BTC")
        
        if bithumb_data:
            print(f"   ✅ 빗썸 BTC 가격: {bithumb_data['price']:,.0f}원")
            print(f"   ✅ 거래량: {bithumb_data['volume']:,.0f}원")
            print(f"   ✅ 변동률: {bithumb_data.get('change_rate', 0):.2f}%")
        else:
            print("   ❌ 빗썸 데이터 수집 실패")
        
        # 업비트 데이터 수집 테스트
        print("2. 업비트 데이터 수집 테스트...")
        upbit_data = await collector._fetch_upbit_data("BTC")
        
        if upbit_data:
            print(f"   ✅ 업비트 BTC 가격: {upbit_data['price']:,.0f}원")
            print(f"   ✅ 거래량: {upbit_data['volume']:,.0f}원")
            print(f"   ✅ 변동률: {upbit_data.get('change_rate', 0):.2f}%")
        else:
            print("   ❌ 업비트 데이터 수집 실패")
        
        # 바이낸스 데이터 수집 테스트
        print("3. 바이낸스 데이터 수집 테스트...")
        binance_data = await collector._fetch_binance_data("BTC")
        
        if binance_data:
            print(f"   ✅ 바이낸스 BTC 가격: ${binance_data['price']:,.0f}")
            print(f"   ✅ 거래량: {binance_data['volume']:,.0f}")
            print(f"   ✅ 변동률: {binance_data.get('change_rate', 0):.2f}%")
        else:
            print("   ❌ 바이낸스 데이터 수집 실패")
        
        return True
        
    except Exception as e:
        print(f"❌ 실시간 데이터 수집기 테스트 실패: {e}")
        return False

async def test_backtesting_with_real_data():
    """실제 데이터를 사용한 백테스팅 테스트"""
    print("\n=== 실제 데이터 백테스팅 테스트 ===")
    
    try:
        from api.backtesting import fetch_real_market_data
        
        print("1. 실제 시장 데이터 수집...")
        data = await fetch_real_market_data(7, "BTC")  # 7일 데이터
        
        if not data.empty:
            print(f"   ✅ 데이터 수집 성공: {len(data)}개 데이터 포인트")
            print(f"   ✅ 최신 가격: {data['close'].iloc[-1]:,.0f}원")
            print(f"   ✅ 가격 범위: {data['close'].min():,.0f} ~ {data['close'].max():,.0f}원")
            print(f"   ✅ 평균 거래량: {data['volume'].mean():,.0f}")
        else:
            print("   ❌ 실제 데이터 수집 실패")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 백테스팅 데이터 테스트 실패: {e}")
        return False

async def test_strategy_management():
    """전략 관리 시스템 테스트"""
    print("\n=== 전략 관리 시스템 테스트 ===")
    
    try:
        from strategies.strategy_manager import strategy_manager, StrategyConfig, StrategyType
        
        print("1. 전략 생성 테스트...")
        
        # 테스트 전략 설정
        config = StrategyConfig(
            name="TestStrategy",
            strategy_type=StrategyType.SCALPING,
            parameters={
                'min_profit_threshold': 0.01,
                'max_hold_hours': 1,
                'volume_threshold': 1000000
            },
            risk_per_trade=1.0,
            max_positions=3
        )
        
        # 전략 생성
        strategy_id = strategy_manager.create_strategy(
            name="TestStrategy",
            strategy_type=StrategyType.SCALPING,
            config=config
        )
        
        print(f"   ✅ 전략 생성 성공: {strategy_id}")
        
        # 전략 목록 조회
        print("2. 전략 목록 조회 테스트...")
        strategies = strategy_manager.get_all_strategies()
        print(f"   ✅ 등록된 전략 수: {len(strategies)}")
        
        # 전략 정보 조회
        print("3. 전략 정보 조회 테스트...")
        strategy_info = strategy_manager.get_strategy_info(strategy_id)
        if strategy_info:
            print(f"   ✅ 전략 정보: {strategy_info['name']}")
        else:
            print("   ❌ 전략 정보 조회 실패")
        
        return True
        
    except Exception as e:
        print(f"❌ 전략 관리 시스템 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 실제 API 연동 테스트 시작")
    print("=" * 50)
    
    test_results = []
    
    # 1. 빗썸 API 테스트
    bithumb_success = await test_bithumb_api()
    test_results.append(("빗썸 API", bithumb_success))
    
    # 2. 실시간 데이터 수집기 테스트
    collector_success = await test_realtime_collector()
    test_results.append(("실시간 데이터 수집기", collector_success))
    
    # 3. 백테스팅 데이터 테스트
    backtest_success = await test_backtesting_with_real_data()
    test_results.append(("백테스팅 데이터", backtest_success))
    
    # 4. 전략 관리 시스템 테스트
    strategy_success = await test_strategy_management()
    test_results.append(("전략 관리 시스템", strategy_success))
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    success_count = 0
    for test_name, success in test_results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{test_name}: {status}")
        if success:
            success_count += 1
    
    print(f"\n총 {len(test_results)}개 테스트 중 {success_count}개 성공")
    
    if success_count == len(test_results):
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")

if __name__ == "__main__":
    asyncio.run(main())
