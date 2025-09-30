"""
전략 엔진 테스트 스크립트
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.strategy_manager import strategy_manager, StrategyConfig, StrategyType
from strategies.base_strategy import StrategyType as BaseStrategyType


def generate_sample_data(days: int = 30) -> pd.DataFrame:
    """샘플 데이터 생성"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                         end=datetime.now(), freq='1H')
    
    # 랜덤 워크로 가격 데이터 생성
    np.random.seed(42)
    price = 50000  # 시작 가격
    prices = [price]
    
    for _ in range(len(dates) - 1):
        change = np.random.normal(0, 200)  # 평균 0, 표준편차 200의 변화
        price += change
        prices.append(max(price, 1000))  # 최소 가격 1000
    
    # OHLCV 데이터 생성
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        if i == 0:
            open_price = close
        else:
            open_price = prices[i-1]
        
        high = max(open_price, close) + np.random.uniform(0, 100)
        low = min(open_price, close) - np.random.uniform(0, 100)
        volume = np.random.uniform(1000, 10000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


def test_strategy_creation():
    """전략 생성 테스트"""
    print("🔍 전략 생성 테스트 시작...")
    
    try:
        # 스캘핑 전략 생성
        scalping_config = StrategyConfig(
            name="Test Scalping",
            strategy_type=StrategyType.SCALPING,
            parameters={
                'ema_short': 8,
                'ema_long': 21,
                'rsi_period': 14,
                'min_profit_pct': 0.5,
                'max_hold_time': 300
            },
            risk_per_trade=1.0,
            max_positions=3,
            stop_loss_pct=1.0,
            take_profit_pct=2.0
        )
        
        scalping_id = strategy_manager.create_strategy("Test Scalping", StrategyType.SCALPING, scalping_config)
        print(f"✅ 스캘핑 전략 생성: {scalping_id}")
        
        # 데이트레이딩 전략 생성
        day_trading_config = StrategyConfig(
            name="Test Day Trading",
            strategy_type=StrategyType.DAY_TRADING,
            parameters={
                'ema_short': 13,
                'ema_long': 50,
                'gap_threshold': 0.02,
                'flag_retracement': 0.382,
                'pivot_lookback': 5
            },
            risk_per_trade=2.0,
            max_positions=2,
            stop_loss_pct=2.0,
            take_profit_pct=4.0
        )
        
        day_trading_id = strategy_manager.create_strategy("Test Day Trading", StrategyType.DAY_TRADING, day_trading_config)
        print(f"✅ 데이트레이딩 전략 생성: {day_trading_id}")
        
        # 스윙 트레이딩 전략 생성
        swing_config = StrategyConfig(
            name="Test Swing Trading",
            strategy_type=StrategyType.SWING_TRADING,
            parameters={
                'ema_short': 21,
                'ema_long': 50,
                'ema_trend': 200,
                'fibonacci_levels': [0.236, 0.382, 0.5, 0.618, 0.786],
                'min_trend_strength': 0.6
            },
            risk_per_trade=3.0,
            max_positions=1,
            stop_loss_pct=3.0,
            take_profit_pct=6.0
        )
        
        swing_id = strategy_manager.create_strategy("Test Swing Trading", StrategyType.SWING_TRADING, swing_config)
        print(f"✅ 스윙 트레이딩 전략 생성: {swing_id}")
        
        # 장기 투자 전략 생성
        long_term_config = StrategyConfig(
            name="Test Long Term",
            strategy_type=StrategyType.LONG_TERM,
            parameters={
                'dca_amount': 100000,
                'dca_interval': 7,
                'rebalance_threshold': 0.05,
                'target_allocation': 0.7,
                'max_drawdown': 0.2
            },
            risk_per_trade=5.0,
            max_positions=1,
            stop_loss_pct=5.0,
            take_profit_pct=10.0
        )
        
        long_term_id = strategy_manager.create_strategy("Test Long Term", StrategyType.LONG_TERM, long_term_config)
        print(f"✅ 장기 투자 전략 생성: {long_term_id}")
        
        return [scalping_id, day_trading_id, swing_id, long_term_id]
        
    except Exception as e:
        print(f"❌ 전략 생성 테스트 실패: {e}")
        return []


def test_strategy_execution(strategy_ids: list):
    """전략 실행 테스트"""
    print("\n🔍 전략 실행 테스트 시작...")
    
    try:
        # 샘플 데이터 생성
        data = generate_sample_data(30)
        print(f"✅ 샘플 데이터 생성 완료: {len(data)}개 캔들")
        
        # 전략 시작
        for strategy_id in strategy_ids:
            strategy_manager.start_strategy(strategy_id)
            print(f"✅ 전략 시작: {strategy_id}")
        
        # 전략 실행
        results = strategy_manager.execute_strategies(data)
        print(f"✅ 전략 실행 완료: {len(results)}개 전략")
        
        # 결과 출력
        for strategy_id, signals in results.items():
            print(f"  - {strategy_id}: {len(signals)}개 신호")
            for signal in signals:
                print(f"    * {signal.signal_type.value}: {signal.reason} (강도: {signal.strength:.2f}, 신뢰도: {signal.confidence:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ 전략 실행 테스트 실패: {e}")
        return False


def test_strategy_management(strategy_ids: list):
    """전략 관리 테스트"""
    print("\n🔍 전략 관리 테스트 시작...")
    
    try:
        # 모든 전략 조회
        all_strategies = strategy_manager.get_all_strategies()
        print(f"✅ 전체 전략 조회: {len(all_strategies)}개")
        
        # 활성 전략 조회
        active_strategies = strategy_manager.get_active_strategies()
        print(f"✅ 활성 전략: {len(active_strategies)}개")
        
        # 전략 정보 조회
        for strategy_id in strategy_ids:
            strategy_info = strategy_manager.get_strategy_info(strategy_id)
            if strategy_info:
                print(f"  - {strategy_info['name']}: {strategy_info['status']}")
        
        # 전략 일시정지
        if strategy_ids:
            strategy_manager.pause_strategy(strategy_ids[0])
            print(f"✅ 전략 일시정지: {strategy_ids[0]}")
        
        # 전략 재시작
        if strategy_ids:
            strategy_manager.start_strategy(strategy_ids[0])
            print(f"✅ 전략 재시작: {strategy_ids[0]}")
        
        # 전략 통계
        stats = strategy_manager.get_strategy_statistics()
        print(f"✅ 전략 통계: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ 전략 관리 테스트 실패: {e}")
        return False


def test_individual_strategies():
    """개별 전략 테스트"""
    print("\n🔍 개별 전략 테스트 시작...")
    
    try:
        # 샘플 데이터 생성
        data = generate_sample_data(30)
        
        # 스캘핑 전략 테스트
        scalping_config = StrategyConfig(
            name="Scalping Test",
            strategy_type=StrategyType.SCALPING,
            parameters={'ema_short': 8, 'ema_long': 21, 'rsi_period': 14},
            risk_per_trade=1.0
        )
        
        from strategies.scalping_strategy import ScalpingStrategy
        scalping_strategy = ScalpingStrategy(scalping_config)
        scalping_signals = scalping_strategy.analyze(data)
        print(f"✅ 스캘핑 전략: {len(scalping_signals)}개 신호")
        
        # 데이트레이딩 전략 테스트
        day_trading_config = StrategyConfig(
            name="Day Trading Test",
            strategy_type=StrategyType.DAY_TRADING,
            parameters={'ema_short': 13, 'ema_long': 50, 'gap_threshold': 0.02},
            risk_per_trade=2.0
        )
        
        from strategies.day_trading_strategy import DayTradingStrategy
        day_trading_strategy = DayTradingStrategy(day_trading_config)
        day_trading_signals = day_trading_strategy.analyze(data)
        print(f"✅ 데이트레이딩 전략: {len(day_trading_signals)}개 신호")
        
        # 스윙 트레이딩 전략 테스트
        swing_config = StrategyConfig(
            name="Swing Trading Test",
            strategy_type=StrategyType.SWING_TRADING,
            parameters={'ema_short': 21, 'ema_long': 50, 'ema_trend': 200},
            risk_per_trade=3.0
        )
        
        from strategies.swing_trading_strategy import SwingTradingStrategy
        swing_strategy = SwingTradingStrategy(swing_config)
        swing_signals = swing_strategy.analyze(data)
        print(f"✅ 스윙 트레이딩 전략: {len(swing_signals)}개 신호")
        
        # 장기 투자 전략 테스트
        long_term_config = StrategyConfig(
            name="Long Term Test",
            strategy_type=StrategyType.LONG_TERM,
            parameters={'dca_amount': 100000, 'dca_interval': 7, 'target_allocation': 0.7},
            risk_per_trade=5.0
        )
        
        from strategies.long_term_strategy import LongTermStrategy
        long_term_strategy = LongTermStrategy(long_term_config)
        long_term_signals = long_term_strategy.analyze(data)
        print(f"✅ 장기 투자 전략: {len(long_term_signals)}개 신호")
        
        return True
        
    except Exception as e:
        print(f"❌ 개별 전략 테스트 실패: {e}")
        return False


def test_performance():
    """성능 테스트"""
    print("\n🔍 성능 테스트 시작...")
    
    try:
        import time
        
        # 다양한 크기의 데이터로 성능 테스트
        test_sizes = [100, 500, 1000]
        
        for size in test_sizes:
            print(f"\n📊 데이터 크기: {size}개 캔들")
            
            data = generate_sample_data(size)
            
            # 전략 실행 성능
            start_time = time.time()
            
            # 스캘핑 전략
            scalping_config = StrategyConfig(
                name="Performance Test",
                strategy_type=StrategyType.SCALPING,
                parameters={'ema_short': 8, 'ema_long': 21},
                risk_per_trade=1.0
            )
            
            from strategies.scalping_strategy import ScalpingStrategy
            scalping_strategy = ScalpingStrategy(scalping_config)
            signals = scalping_strategy.analyze(data)
            
            end_time = time.time()
            
            print(f"  스캘핑 전략: {end_time - start_time:.3f}초, {len(signals)}개 신호")
        
        return True
        
    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 전략 엔진 테스트 시작\n")
    
    # 1. 전략 생성 테스트
    strategy_ids = test_strategy_creation()
    
    # 2. 전략 실행 테스트
    execution_success = test_strategy_execution(strategy_ids)
    
    # 3. 전략 관리 테스트
    management_success = test_strategy_management(strategy_ids)
    
    # 4. 개별 전략 테스트
    individual_success = test_individual_strategies()
    
    # 5. 성능 테스트
    performance_success = test_performance()
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 전략 엔진 테스트 결과 요약")
    print("="*50)
    print(f"전략 생성: {'✅ 성공' if strategy_ids else '❌ 실패'}")
    print(f"전략 실행: {'✅ 성공' if execution_success else '❌ 실패'}")
    print(f"전략 관리: {'✅ 성공' if management_success else '❌ 실패'}")
    print(f"개별 전략: {'✅ 성공' if individual_success else '❌ 실패'}")
    print(f"성능 테스트: {'✅ 성공' if performance_success else '❌ 실패'}")
    
    if all([strategy_ids, execution_success, management_success, individual_success, performance_success]):
        print("\n🎉 모든 전략 엔진 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 설정을 확인해주세요.")


if __name__ == "__main__":
    main()
