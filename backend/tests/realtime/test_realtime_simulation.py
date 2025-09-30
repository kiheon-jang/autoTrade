"""
실시간 거래 시뮬레이션 테스트
빗썸 API 1.0을 활용한 실시간 거래 시스템 시뮬레이션 테스트
"""
import asyncio
import os
from dotenv import load_dotenv
from trading.realtime_engine import RealtimeTradingEngine, TradingMode
from strategies.strategy_manager import StrategyManager
from strategies.commission_optimized_strategy import LowFrequencyStrategy, BreakoutStrategy
from strategies.base_strategy import StrategyConfig, StrategyType
from data.realtime_collector import RealtimeDataCollector
from core.commission import ExchangeType

# 환경 변수 로드
load_dotenv('../.env')

async def test_realtime_simulation():
    """실시간 거래 시뮬레이션 테스트"""
    print("=== 실시간 거래 시뮬레이션 테스트 ===")
    
    try:
        # API 키 확인
        api_key = os.getenv("BITHUMB_API_KEY")
        secret_key = os.getenv("BITHUMB_SECRET_KEY")
        
        print(f"API Key: {api_key[:10]}..." if api_key else "API Key: None")
        print(f"Secret Key: {secret_key[:10]}..." if secret_key else "Secret Key: None")
        
        if not api_key or not secret_key:
            print("❌ API 키가 설정되지 않았습니다.")
            return
    except Exception as e:
        print(f"❌ API 키 확인 중 에러: {e}")
        return
    
    try:
        # 실시간 거래 엔진 생성 (시뮬레이션 모드)
        print("🔧 실시간 거래 엔진 생성 중...")
        trading_engine = RealtimeTradingEngine(
            mode=TradingMode.SIMULATION,  # 시뮬레이션 모드
            initial_capital=1000000,  # 100만원
            commission_rate=0.0015  # 빗썸 수수료율
        )
        print("✅ 실시간 거래 엔진 생성 완료")
        
        # 전략 매니저 설정
        print("🔧 전략 매니저 설정 중...")
        strategy_manager = StrategyManager()
        print("✅ 전략 매니저 설정 완료")
    except Exception as e:
        print(f"❌ 엔진/매니저 생성 중 에러: {e}")
        return
    
    try:
        # 저빈도 전략 추가
        print("🔧 저빈도 전략 생성 중...")
        low_freq_config = StrategyConfig(
            name="Low Frequency Strategy",
            strategy_type=StrategyType.SCALPING,
            parameters={
                "symbol": "BTC/KRW",
                "timeframe": "1m",
                "max_positions": 3,
                "risk_per_trade": 0.01
            }
        )
        low_freq_strategy_id = strategy_manager.create_strategy(
            name="Low Frequency Strategy",
            strategy_type=StrategyType.SCALPING,
            config=low_freq_config
        )
        print(f"✅ 저빈도 전략 생성 완료: {low_freq_strategy_id}")
        
        # 브레이크아웃 전략 추가
        print("🔧 브레이크아웃 전략 생성 중...")
        breakout_config = StrategyConfig(
            name="Breakout Strategy",
            strategy_type=StrategyType.SWING_TRADING,
            parameters={
                "symbol": "BTC/KRW",
                "timeframe": "15m",
                "max_positions": 2,
                "risk_per_trade": 0.02
            }
        )
        breakout_strategy_id = strategy_manager.create_strategy(
            name="Breakout Strategy",
            strategy_type=StrategyType.SWING_TRADING,
            config=breakout_config
        )
        print(f"✅ 브레이크아웃 전략 생성 완료: {breakout_strategy_id}")
        
        # 전략 활성화
        print("🔧 전략 활성화 중...")
        strategy_manager.start_strategy(low_freq_strategy_id)
        strategy_manager.start_strategy(breakout_strategy_id)
        print("✅ 전략 활성화 완료")
    except Exception as e:
        print(f"❌ 전략 생성/활성화 중 에러: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        print(f"✅ 활성화된 전략 수: {len([s for s in strategy_manager.strategies.values() if s.status.value == 'active'])}")
        
        # 실시간 거래 엔진 시작
        print("\n🚀 실시간 거래 엔진 시작...")
        await trading_engine.start(["BTC"], [low_freq_strategy_id, breakout_strategy_id])
        print("✅ 실시간 거래 엔진 시작 완료")
        
        # 30초간 시뮬레이션 실행
        print("⏱️ 30초간 시뮬레이션 실행 중...")
        await asyncio.sleep(30)
        print("✅ 시뮬레이션 실행 완료")
        
        # 포트폴리오 상태 확인
        print("🔧 포트폴리오 상태 확인 중...")
        portfolio = trading_engine.get_portfolio_summary()
        print(f"\n📊 포트폴리오 상태:")
        print(f"  - 총 자산: {portfolio['total_value']:,.0f}원")
        print(f"  - 현재 자본: {portfolio['current_capital']:,.0f}원")
        print(f"  - 오픈 포지션: {portfolio['open_positions_count']}개")
        print(f"  - 총 거래 수: {portfolio['total_trades_count']}회")
        
        # 포지션 정보
        print("🔧 포지션 정보 확인 중...")
        positions = trading_engine.get_positions()
        if positions:
            print(f"\n📈 오픈 포지션:")
            for pos in positions:
                print(f"  - {pos['symbol']}: {pos['side']} {pos['current_amount']} @ {pos['entry_price']}")
        else:
            print("📈 오픈 포지션 없음")
        
        # 최근 거래 내역
        print("🔧 거래 내역 확인 중...")
        trades = trading_engine.get_recent_trades(5)
        if trades:
            print(f"\n💼 최근 거래 내역:")
            for trade in trades[-3:]:  # 최근 3개만 표시
                print(f"  - {trade['symbol']}: {trade['side']} {trade['entry_amount']} @ {trade['entry_price']}")
        else:
            print("💼 거래 내역 없음")
        
        # 주문 내역
        print("🔧 주문 내역 확인 중...")
        orders = trading_engine.get_order_history(5)
        if orders:
            print(f"\n📋 최근 주문 내역:")
            for order in orders[-3:]:  # 최근 3개만 표시
                print(f"  - {order['symbol']}: {order['side']} {order['quantity']} @ {order['price']} ({order['status']})")
        else:
            print("📋 주문 내역 없음")
        
        print("\n✅ 시뮬레이션 완료!")
        
    except Exception as e:
        print(f"❌ 시뮬레이션 에러: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            # 실시간 거래 엔진 중지
            print("\n🛑 실시간 거래 엔진 중지...")
            await trading_engine.stop()
            print("✅ 엔진 중지 완료")
        except Exception as e:
            print(f"❌ 엔진 중지 중 에러: {e}")

async def test_api_endpoints():
    """API 엔드포인트 테스트"""
    print("\n=== API 엔드포인트 테스트 ===")
    
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 서버 상태 확인
            print("1. 서버 상태 확인...")
            try:
                response = await client.get(f"{base_url}/health")
                print(f"   상태: {response.status_code}")
            except Exception as e:
                print(f"   ❌ 서버 연결 실패: {e}")
                return
            
            # 실시간 거래 상태 확인
            print("2. 실시간 거래 상태 확인...")
            try:
                response = await client.get(f"{base_url}/api/v1/realtime/status")
                print(f"   상태: {response.status_code}")
                if response.status_code == 200:
                    print(f"   응답: {response.json()}")
            except Exception as e:
                print(f"   ❌ 실시간 거래 상태 확인 실패: {e}")
            
            # 포트폴리오 대시보드
            print("3. 포트폴리오 대시보드...")
            try:
                response = await client.get(f"{base_url}/api/v1/monitoring/dashboard")
                print(f"   상태: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   총 자산: {data.get('total_value', 0):,.0f}원")
                    print(f"   오픈 포지션: {data.get('open_positions_count', 0)}개")
            except Exception as e:
                print(f"   ❌ 포트폴리오 대시보드 확인 실패: {e}")
            
    except Exception as e:
        print(f"❌ API 테스트 에러: {e}")
        print("💡 서버가 실행되지 않았을 수 있습니다. 'python main.py'로 서버를 시작하세요.")

if __name__ == "__main__":
    print("빗썸 API 1.0 실시간 거래 시뮬레이션 테스트 시작...")
    asyncio.run(test_realtime_simulation())
    print("\n" + "="*50)
    asyncio.run(test_api_endpoints())
