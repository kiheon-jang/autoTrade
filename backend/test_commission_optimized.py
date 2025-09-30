"""
수수료 최적화 전략 테스트
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from strategies.commission_optimized_strategy import LowFrequencyStrategy, BreakoutStrategy, MeanReversionStrategy
from strategies.base_strategy import StrategyConfig, StrategyType
from backtesting.backtest_engine import BacktestEngine
from core.commission import ExchangeType


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


def test_commission_optimized_strategies():
    """수수료 최적화 전략 테스트"""
    print("🚀 수수료 최적화 전략 테스트 시작")
    
    try:
        # 샘플 데이터 생성
        data = generate_sample_data(30)
        print(f"✅ 샘플 데이터 생성 완료: {len(data)}개 캔들")
        
        # 전략 설정
        strategies = []
        
        # 1. 저빈도 거래 전략
        low_freq_config = StrategyConfig(
            name="Low Frequency Strategy",
            strategy_type=StrategyType.SWING_TRADING,
            parameters={
                'ema_short': 50,
                'ema_long': 200,
                'rsi_period': 14,
                'volatility_period': 20,
                'min_volatility': 0.02,
                'min_profit_threshold': 0.02,  # 2% 최소 수익
                'commission_buffer': 0.003,    # 0.3% 수수료 버퍼
                'min_hold_period': 10
            },
            risk_per_trade=2.0,
            max_positions=1,
            stop_loss_pct=3.0,
            take_profit_pct=6.0
        )
        strategies.append(("Low Frequency", LowFrequencyStrategy(low_freq_config)))
        
        # 2. 돌파 전략
        breakout_config = StrategyConfig(
            name="Breakout Strategy",
            strategy_type=StrategyType.SWING_TRADING,
            parameters={
                'breakout_period': 20,
                'volume_threshold': 1.5,
                'min_breakout_pct': 0.03,
                'min_profit_threshold': 0.03,  # 3% 최소 수익
                'commission_buffer': 0.003,
                'min_hold_period': 5
            },
            risk_per_trade=2.5,
            max_positions=1,
            stop_loss_pct=2.5,
            take_profit_pct=8.0
        )
        strategies.append(("Breakout", BreakoutStrategy(breakout_config)))
        
        # 3. 평균 회귀 전략
        mean_reversion_config = StrategyConfig(
            name="Mean Reversion Strategy",
            strategy_type=StrategyType.SWING_TRADING,
            parameters={
                'bollinger_period': 20,
                'bollinger_std': 2.0,
                'rsi_period': 14,
                'oversold_threshold': 30,
                'overbought_threshold': 70,
                'min_profit_threshold': 0.015,  # 1.5% 최소 수익
                'commission_buffer': 0.002,
                'min_hold_period': 3
            },
            risk_per_trade=1.5,
            max_positions=1,
            stop_loss_pct=2.0,
            take_profit_pct=4.0
        )
        strategies.append(("Mean Reversion", MeanReversionStrategy(mean_reversion_config)))
        
        # 백테스팅 실행
        results = []
        
        for strategy_name, strategy in strategies:
            print(f"\n🔍 {strategy_name} 전략 테스트 중...")
            
            # 백테스팅 엔진 생성
            backtest_engine = BacktestEngine(
                initial_capital=100000,
                commission_rate=0.0015,  # 빗썸 테이커 수수료
                exchange=ExchangeType.BITHUMB
            )
            
            # 백테스팅 실행
            result = backtest_engine.run_backtest(strategy, data)
            
            # 결과 저장
            results.append({
                'strategy': strategy_name,
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'win_rate': result.win_rate,
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'max_drawdown': result.max_drawdown,
                'sharpe_ratio': result.sharpe_ratio,
                'sortino_ratio': result.sortino_ratio,
                'profit_factor': result.profit_factor,
                'total_commission': result.total_commission,
                'net_profit': result.net_profit,
                'gross_profit': result.gross_profit,
                'commission_impact': result.commission_impact
            })
            
            print(f"✅ {strategy_name} 완료:")
            print(f"  - 총 거래 수: {result.total_trades}")
            print(f"  - 승률: {result.win_rate:.2%}")
            print(f"  - 총 수익률: {result.total_return:.2%}")
            print(f"  - 순수익: {result.net_profit:.2f}원")
            print(f"  - 수수료 영향: {result.commission_impact:.2%}")
        
        # 결과 비교
        print("\n" + "="*60)
        print("📊 수수료 최적화 전략 비교 결과")
        print("="*60)
        
        for result in results:
            print(f"\n🏆 {result['strategy']}:")
            print(f"  * 총 수익률: {result['total_return']:.2%}")
            print(f"  * 연환산 수익률: {result['annualized_return']:.2%}")
            print(f"  * 최대 낙폭: {result['max_drawdown']:.2%}")
            print(f"  * 샤프 비율: {result['sharpe_ratio']:.2f}")
            print(f"  * 승률: {result['win_rate']:.2%}")
            print(f"  * 총 거래 수: {result['total_trades']}")
            print(f"  * 순수익: {result['net_profit']:.2f}원")
            print(f"  * 수수료 영향: {result['commission_impact']:.2%}")
        
        # 최고 성과 전략 찾기
        best_return = max(results, key=lambda x: x['total_return'])
        best_sharpe = max(results, key=lambda x: x['sharpe_ratio'])
        lowest_commission_impact = min(results, key=lambda x: x['commission_impact'])
        
        print(f"\n🏆 최고 성과:")
        print(f"  - 최고 수익률: {best_return['strategy']} ({best_return['total_return']:.2%})")
        print(f"  - 최고 샤프 비율: {best_sharpe['strategy']} ({best_sharpe['sharpe_ratio']:.2f})")
        print(f"  - 최저 수수료 영향: {lowest_commission_impact['strategy']} ({lowest_commission_impact['commission_impact']:.2%})")
        
        return True
        
    except Exception as e:
        print(f"❌ 수수료 최적화 전략 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_commission_optimized_strategies()
