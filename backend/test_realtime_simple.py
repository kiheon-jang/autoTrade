"""
실시간 거래 시스템 간단 테스트
네트워크 연결 없이도 시뮬레이션 모드로 실행되는지 확인
"""
import asyncio
import traceback
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(__file__))

async def test_realtime_simple():
    try:
        print('=== 실시간 거래 시스템 간단 테스트 ===')
        
        # 1. 거래 엔진 초기화 (시뮬레이션 모드)
        print('1. 거래 엔진 초기화 중...')
        from trading.realtime_engine import RealtimeTradingEngine, TradingMode
        engine = RealtimeTradingEngine(
            mode=TradingMode.SIMULATION,
            initial_capital=100000,  # 10만원
            commission_rate=0.0015  # 0.15%
        )
        print('✅ 거래 엔진 초기화 완료')
        
        # 2. 전략 매니저를 통해 전략 추가
        print('2. 전략 추가 중...')
        from strategies.strategy_manager import strategy_manager, StrategyConfig, StrategyType
        
        low_freq_config = StrategyConfig(
            name='LowFrequencyStrategy',
            strategy_type=StrategyType.SCALPING,
            parameters={
                'min_profit_threshold': 0.02,  # 2% 최소 수익
                'max_hold_hours': 24,          # 최대 24시간 보유
                'volume_threshold': 1000000    # 100만원 이상 거래량
            }
        )
        
        strategy_id = strategy_manager.create_strategy(
            name='LowFrequencyStrategy',
            strategy_type=StrategyType.SCALPING,
            config=low_freq_config
        )
        print(f'✅ 전략 추가 완료: {strategy_id}')
        
        # 3. 포트폴리오 상태 확인
        print('3. 포트폴리오 상태 확인...')
        portfolio = engine.get_portfolio_summary()
        print(f'✅ 포트폴리오 상태: {portfolio}')
        
        # 4. 거래 엔진 시작 (네트워크 연결 없이)
        print('4. 거래 엔진 시작 중...')
        await engine.start(symbols=['BTC', 'ETH'])
        print('✅ 거래 엔진 시작')
        
        # 5. 잠시 실행 후 상태 확인
        print('5. 3초 대기 중...')
        await asyncio.sleep(3)
        
        portfolio_after = engine.get_portfolio_summary()
        print(f'✅ 실행 후 포트폴리오 상태: {portfolio_after}')
        
        # 6. 거래 엔진 중지
        print('6. 거래 엔진 중지 중...')
        await engine.stop()
        print('✅ 거래 엔진 중지')
        
        print('✅ 모든 테스트 통과!')
        
    except Exception as e:
        print(f'❌ 에러 발생: {e}')
        print(f'❌ 에러 타입: {type(e).__name__}')
        print('❌ 상세 에러 정보:')
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_realtime_simple())
