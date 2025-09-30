"""
백테스팅 엔진 테스트 스크립트
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtesting.backtest_engine import BacktestEngine, ExchangeType
from strategies.strategy_manager import strategy_manager, StrategyConfig, StrategyType
from strategies.base_strategy import StrategyType as BaseStrategyType
from core.commission import commission_calculator


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


def test_commission_calculator():
    """수수료 계산기 테스트"""
    print("🔍 수수료 계산기 테스트 시작...")
    
    try:
        # 기본 수수료 계산
        commission = commission_calculator.calculate_commission(
            amount=1.0, price=50000, exchange=ExchangeType.BITHUMB
        )
        print(f"✅ 기본 수수료 계산: {commission:.2f}원")
        
        # 메이커/테이커 수수료 비교
        maker_commission = commission_calculator.calculate_commission(
            amount=1.0, price=50000, exchange=ExchangeType.BITHUMB, is_maker=True
        )
        taker_commission = commission_calculator.calculate_commission(
            amount=1.0, price=50000, exchange=ExchangeType.BITHUMB, is_maker=False
        )
        print(f"✅ 메이커 수수료: {maker_commission:.2f}원")
        print(f"✅ 테이커 수수료: {taker_commission:.2f}원")
        
        # 순수익 계산
        net_profit = commission_calculator.calculate_net_profit(
            entry_amount=1.0, entry_price=50000,
            exit_amount=1.0, exit_price=51000,
            exchange=ExchangeType.BITHUMB
        )
        print(f"✅ 순수익 계산: {net_profit:.2f}원")
        
        # 손익분기점 계산
        break_even_price = commission_calculator.calculate_break_even_price(
            entry_price=50000, entry_amount=1.0, exit_amount=1.0,
            exchange=ExchangeType.BITHUMB
        )
        print(f"✅ 손익분기점: {break_even_price:.2f}원")
        
        # 필요 수익률 계산
        required_return = commission_calculator.calculate_required_return(
            entry_price=50000, entry_amount=1.0, target_profit=1000,
            exchange=ExchangeType.BITHUMB
        )
        print(f"✅ 필요 수익률: {required_return:.4f} ({required_return*100:.2f}%)")
        
        # 수수료 정보 조회
        commission_info = commission_calculator.get_commission_info(ExchangeType.BITHUMB)
        print(f"✅ 수수료 정보: {commission_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ 수수료 계산기 테스트 실패: {e}")
        return False


def test_backtest_engine():
    """백테스팅 엔진 테스트"""
    print("\n🔍 백테스팅 엔진 테스트 시작...")
    
    try:
        # 샘플 데이터 생성
        data = generate_sample_data(30)
        print(f"✅ 샘플 데이터 생성 완료: {len(data)}개 캔들")
        
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
        
        # 전략 생성
        strategy_id = strategy_manager.create_strategy("Test Scalping", StrategyType.SCALPING, scalping_config)
        strategy = strategy_manager.strategies[strategy_id].strategy
        
        # 백테스팅 엔진 생성
        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0015,
            exchange=ExchangeType.BITHUMB
        )
        
        # 백테스트 실행
        result = engine.run_backtest(strategy, data)
        
        print(f"✅ 백테스트 완료:")
        print(f"  - 총 거래 수: {result.total_trades}")
        print(f"  - 승률: {result.win_rate:.2%}")
        print(f"  - 총 수익률: {result.total_return:.2%}")
        print(f"  - 연환산 수익률: {result.annualized_return:.2%}")
        print(f"  - 최대 낙폭: {result.max_drawdown:.2%}")
        print(f"  - 샤프 비율: {result.sharpe_ratio:.2f}")
        print(f"  - 수익 팩터: {result.profit_factor:.2f}")
        print(f"  - 총 수수료: {result.total_commission:.2f}원")
        print(f"  - 순수익: {result.net_profit:.2f}원")
        print(f"  - 수수료 영향: {result.commission_impact:.2%}")
        
        # 거래 내역 조회
        trade_history = engine.get_trade_history()
        print(f"✅ 거래 내역: {len(trade_history)}개")
        
        # 자본 곡선 조회
        equity_curve = engine.get_equity_curve()
        print(f"✅ 자본 곡선: {len(equity_curve)}개 포인트")
        
        return True
        
    except Exception as e:
        print(f"❌ 백테스팅 엔진 테스트 실패: {e}")
        return False


def test_strategy_comparison():
    """전략 비교 테스트"""
    print("\n🔍 전략 비교 테스트 시작...")
    
    try:
        # 여러 전략 생성
        strategies = []
        
        # 스캘핑 전략
        scalping_config = StrategyConfig(
            name="Scalping Test",
            strategy_type=StrategyType.SCALPING,
            parameters={'ema_short': 8, 'ema_long': 21, 'rsi_period': 14},
            risk_per_trade=1.0
        )
        scalping_id = strategy_manager.create_strategy("Scalping Test", StrategyType.SCALPING, scalping_config)
        strategies.append(scalping_id)
        
        # 데이트레이딩 전략
        day_trading_config = StrategyConfig(
            name="Day Trading Test",
            strategy_type=StrategyType.DAY_TRADING,
            parameters={'ema_short': 13, 'ema_long': 50, 'gap_threshold': 0.02},
            risk_per_trade=2.0
        )
        day_trading_id = strategy_manager.create_strategy("Day Trading Test", StrategyType.DAY_TRADING, day_trading_config)
        strategies.append(day_trading_id)
        
        # 스윙 트레이딩 전략
        swing_config = StrategyConfig(
            name="Swing Trading Test",
            strategy_type=StrategyType.SWING_TRADING,
            parameters={'ema_short': 21, 'ema_long': 50, 'ema_trend': 200},
            risk_per_trade=3.0
        )
        swing_id = strategy_manager.create_strategy("Swing Trading Test", StrategyType.SWING_TRADING, swing_config)
        strategies.append(swing_id)
        
        # 장기 투자 전략
        long_term_config = StrategyConfig(
            name="Long Term Test",
            strategy_type=StrategyType.LONG_TERM,
            parameters={'dca_amount': 100000, 'dca_interval': 7, 'target_allocation': 0.7},
            risk_per_trade=5.0
        )
        long_term_id = strategy_manager.create_strategy("Long Term Test", StrategyType.LONG_TERM, long_term_config)
        strategies.append(long_term_id)
        
        # 샘플 데이터 생성
        data = generate_sample_data(30)
        
        # 각 전략별 백테스트 실행
        results = []
        for strategy_id in strategies:
            strategy = strategy_manager.strategies[strategy_id].strategy
            
            engine = BacktestEngine(
                initial_capital=1000000,
                commission_rate=0.0015,
                exchange=ExchangeType.BITHUMB
            )
            
            result = engine.run_backtest(strategy, data)
            
            results.append({
                'strategy_id': strategy_id,
                'strategy_name': strategy_manager.strategies[strategy_id].name,
                'total_return': result.total_return,
                'annualized_return': result.annualized_return,
                'max_drawdown': result.max_drawdown,
                'sharpe_ratio': result.sharpe_ratio,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades,
                'net_profit': result.net_profit,
                'commission_impact': result.commission_impact
            })
        
        # 결과 출력
        print("✅ 전략 비교 결과:")
        for result in results:
            print(f"  - {result['strategy_name']}:")
            print(f"    * 총 수익률: {result['total_return']:.2%}")
            print(f"    * 연환산 수익률: {result['annualized_return']:.2%}")
            print(f"    * 최대 낙폭: {result['max_drawdown']:.2%}")
            print(f"    * 샤프 비율: {result['sharpe_ratio']:.2f}")
            print(f"    * 승률: {result['win_rate']:.2%}")
            print(f"    * 총 거래 수: {result['total_trades']}")
            print(f"    * 순수익: {result['net_profit']:.2f}원")
            print(f"    * 수수료 영향: {result['commission_impact']:.2%}")
            print()
        
        # 최고 성과 전략 찾기
        best_return = max(results, key=lambda x: x['total_return'])
        best_sharpe = max(results, key=lambda x: x['sharpe_ratio'])
        lowest_drawdown = min(results, key=lambda x: x['max_drawdown'])
        
        print("🏆 최고 성과:")
        print(f"  - 최고 수익률: {best_return['strategy_name']} ({best_return['total_return']:.2%})")
        print(f"  - 최고 샤프 비율: {best_sharpe['strategy_name']} ({best_sharpe['sharpe_ratio']:.2f})")
        print(f"  - 최저 낙폭: {lowest_drawdown['strategy_name']} ({lowest_drawdown['max_drawdown']:.2%})")
        
        return True
        
    except Exception as e:
        print(f"❌ 전략 비교 테스트 실패: {e}")
        return False


def test_commission_impact():
    """수수료 영향 테스트"""
    print("\n🔍 수수료 영향 테스트 시작...")
    
    try:
        # 수수료율별 백테스트 실행
        commission_rates = [0.0, 0.0005, 0.0015, 0.003, 0.005]  # 0%, 0.05%, 0.15%, 0.3%, 0.5%
        
        # 스캘핑 전략 생성
        scalping_config = StrategyConfig(
            name="Commission Test",
            strategy_type=StrategyType.SCALPING,
            parameters={'ema_short': 8, 'ema_long': 21, 'rsi_period': 14},
            risk_per_trade=1.0
        )
        
        strategy_id = strategy_manager.create_strategy("Commission Test", StrategyType.SCALPING, scalping_config)
        strategy = strategy_manager.strategies[strategy_id].strategy
        
        # 샘플 데이터 생성
        data = generate_sample_data(30)
        
        results = []
        for rate in commission_rates:
            engine = BacktestEngine(
                initial_capital=1000000,
                commission_rate=rate,
                exchange=ExchangeType.BITHUMB
            )
            
            result = engine.run_backtest(strategy, data)
            
            results.append({
                'commission_rate': rate,
                'commission_rate_pct': rate * 100,
                'total_return': result.total_return,
                'net_profit': result.net_profit,
                'total_commission': result.total_commission,
                'commission_impact': result.commission_impact
            })
        
        print("✅ 수수료율별 성과 비교:")
        for result in results:
            print(f"  - 수수료율 {result['commission_rate_pct']:.2f}%:")
            print(f"    * 총 수익률: {result['total_return']:.2%}")
            print(f"    * 순수익: {result['net_profit']:.2f}원")
            print(f"    * 총 수수료: {result['total_commission']:.2f}원")
            print(f"    * 수수료 영향: {result['commission_impact']:.2%}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 수수료 영향 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 백테스팅 엔진 테스트 시작\n")
    
    # 1. 수수료 계산기 테스트
    commission_success = test_commission_calculator()
    
    # 2. 백테스팅 엔진 테스트
    backtest_success = test_backtest_engine()
    
    # 3. 전략 비교 테스트
    comparison_success = test_strategy_comparison()
    
    # 4. 수수료 영향 테스트
    commission_impact_success = test_commission_impact()
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 백테스팅 엔진 테스트 결과 요약")
    print("="*50)
    print(f"수수료 계산기: {'✅ 성공' if commission_success else '❌ 실패'}")
    print(f"백테스팅 엔진: {'✅ 성공' if backtest_success else '❌ 실패'}")
    print(f"전략 비교: {'✅ 성공' if comparison_success else '❌ 실패'}")
    print(f"수수료 영향: {'✅ 성공' if commission_impact_success else '❌ 실패'}")
    
    if all([commission_success, backtest_success, comparison_success, commission_impact_success]):
        print("\n🎉 모든 백테스팅 엔진 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 설정을 확인해주세요.")


if __name__ == "__main__":
    main()
