"""
수정된 테스트 - start 메서드 문제 해결
"""
import asyncio
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv('../.env')

async def test_realtime_engine():
    """실시간 거래 엔진 테스트 (수정된 버전)"""
    print("=== 실시간 거래 엔진 테스트 ===")
    
    try:
        from trading.realtime_engine import RealtimeTradingEngine, TradingMode
        from strategies.strategy_manager import StrategyManager
        from strategies.base_strategy import StrategyConfig, StrategyType
        
        # 엔진 생성
        print("1. 엔진 생성...")
        engine = RealtimeTradingEngine(
            mode=TradingMode.SIMULATION,
            initial_capital=1000000,
            commission_rate=0.0015
        )
        
        # 전략 매니저 생성
        print("2. 전략 매니저 생성...")
        strategy_manager = StrategyManager()
        
        # 전략 생성
        print("3. 전략 생성...")
        config = StrategyConfig(
            name="Test Strategy",
            strategy_type=StrategyType.SCALPING,
            parameters={
                "symbol": "BTC/KRW",
                "timeframe": "1m",
                "max_positions": 1,
                "risk_per_trade": 0.01
            }
        )
        strategy_id = strategy_manager.create_strategy(
            name="Test Strategy",
            strategy_type=StrategyType.SCALPING,
            config=config
        )
        
        # 전략 활성화
        print("4. 전략 활성화...")
        strategy_manager.start_strategy(strategy_id)
        
        # 엔진 시작 (별도 태스크로 실행)
        print("5. 엔진 시작...")
        start_task = asyncio.create_task(engine.start(["BTC"], [strategy_id]))
        
        # 5초 대기
        print("6. 5초 대기...")
        await asyncio.sleep(5)
        
        # 상태 확인
        print("7. 상태 확인...")
        portfolio = engine.get_portfolio_summary()
        print(f"   총 자산: {portfolio.get('total_value', 0):,.0f}원")
        print(f"   오픈 포지션: {portfolio.get('open_positions_count', 0)}개")
        print(f"   총 거래 수: {portfolio.get('total_trades_count', 0)}회")
        print(f"   포트폴리오 전체: {portfolio}")
        
        # 엔진 중지
        print("8. 엔진 중지...")
        await engine.stop()
        
        # 시작 태스크 취소
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            print("   시작 태스크 취소됨")
        
        print("\n✅ 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 에러: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("수정된 실시간 거래 엔진 테스트 시작...")
    asyncio.run(test_realtime_engine())
