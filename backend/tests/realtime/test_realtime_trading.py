"""
실시간 거래 시스템 테스트
"""
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading.realtime_engine import RealtimeTradingEngine, TradingMode
from strategies.strategy_manager import StrategyManager, StrategyConfig, StrategyType
from strategies.scalping_strategy import ScalpingStrategy
from strategies.swing_trading_strategy import SwingTradingStrategy


class RealtimeTradingTester:
    """실시간 거래 테스터"""
    
    def __init__(self):
        self.trading_engine = None
        self.strategy_manager = StrategyManager()
        self.test_results = {}
    
    def create_test_strategies(self):
        """테스트용 전략 생성"""
        # 스캘핑 전략
        scalping_config = StrategyConfig(
            name="Test Scalping",
            strategy_type=StrategyType.SCALPING,
            parameters={
                'ema_short': 5,
                'ema_long': 20,
                'rsi_period': 14,
                'profit_target': 0.002,
                'stop_loss': 0.001
            },
            risk_per_trade=1.0,
            max_positions=3,
            stop_loss_pct=1.0,
            take_profit_pct=2.0,
            enabled=True
        )
        
        scalping_id = self.strategy_manager.create_strategy(
            "Test Scalping", StrategyType.SCALPING, scalping_config
        )
        
        # 스윙 트레이딩 전략
        swing_config = StrategyConfig(
            name="Test Swing",
            strategy_type=StrategyType.SWING_TRADING,
            parameters={
                'ema_short': 21,
                'ema_long': 50,
                'ema_trend': 200,
                'rsi_period': 14,
                'min_trend_strength': 0.3
            },
            risk_per_trade=2.0,
            max_positions=2,
            stop_loss_pct=2.0,
            take_profit_pct=4.0,
            enabled=True
        )
        
        swing_id = self.strategy_manager.create_strategy(
            "Test Swing", StrategyType.SWING_TRADING, swing_config
        )
        
        return [scalping_id, swing_id]
    
    def generate_test_data(self, symbol: str, days: int = 7) -> pd.DataFrame:
        """테스트용 시장 데이터 생성"""
        np.random.seed(42)
        
        # 시간 범위 생성 (1분 간격)
        start_time = datetime.now() - timedelta(days=days)
        time_range = pd.date_range(start=start_time, end=datetime.now(), freq='1min')
        
        # 가격 데이터 생성 (랜덤 워크)
        base_price = 50000 if symbol == 'BTC' else 3000
        returns = np.random.normal(0.0001, 0.02, len(time_range))
        prices = [base_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # OHLCV 데이터 생성
        data = []
        for i, (timestamp, price) in enumerate(zip(time_range, prices)):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                'timestamp': timestamp,
                'open': prices[i-1] if i > 0 else price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    async def test_simulation_mode(self):
        """시뮬레이션 모드 테스트"""
        print("🎯 시뮬레이션 모드 테스트")
        print("=" * 50)
        
        # 거래 엔진 생성
        self.trading_engine = RealtimeTradingEngine(
            mode=TradingMode.SIMULATION,
            initial_capital=1000000
        )
        
        # 전략 생성
        strategy_ids = self.create_test_strategies()
        
        # 테스트 데이터 생성
        btc_data = self.generate_test_data('BTC', 1)
        eth_data = self.generate_test_data('ETH', 1)
        
        # 데이터 수집기에 데이터 주입
        self.trading_engine.data_collector.data_buffer = {
            'BTC': [{'timestamp': datetime.now(), 'price': row['close'], 'volume': row['volume']} 
                   for _, row in btc_data.iterrows()],
            'ETH': [{'timestamp': datetime.now(), 'price': row['close'], 'volume': row['volume']} 
                   for _, row in eth_data.iterrows()]
        }
        
        # 거래 시작
        await self.trading_engine.start(
            symbols=['BTC', 'ETH'],
            strategies=strategy_ids
        )
        
        # 10초간 거래 실행
        print("10초간 거래 실행 중...")
        await asyncio.sleep(10)
        
        # 결과 확인
        portfolio = self.trading_engine.get_portfolio_summary()
        positions = self.trading_engine.get_positions()
        trades = self.trading_engine.get_recent_trades(10)
        
        print(f"포트폴리오 요약:")
        print(f"  초기 자본: {portfolio['initial_capital']:,.0f}원")
        print(f"  현재 자본: {portfolio['current_capital']:,.0f}원")
        print(f"  총 가치: {portfolio['total_value']:,.0f}원")
        print(f"  총 수익률: {portfolio['total_return']:.2%}")
        print(f"  활성 전략: {portfolio['active_strategies']}개")
        print(f"  포지션: {portfolio['positions']}개")
        print(f"  거래: {portfolio['trades']}개")
        
        print(f"\n포지션 정보:")
        for symbol, pos in positions.items():
            print(f"  {symbol}: {pos['side']} {pos['amount']:.6f} @ {pos['avg_price']:,.0f}원")
            print(f"    미실현 손익: {pos['unrealized_pnl']:,.0f}원")
            print(f"    실현 손익: {pos['realized_pnl']:,.0f}원")
        
        print(f"\n최근 거래 내역:")
        for trade in trades[-5:]:  # 최근 5개 거래
            print(f"  {trade['timestamp']}: {trade['side']} {trade['symbol']} {trade['amount']:.6f} @ {trade['price']:,.0f}원")
            print(f"    수수료: {trade['commission']:,.0f}원, 전략: {trade['strategy_id']}")
        
        # 거래 중지
        await self.trading_engine.stop()
        
        self.test_results['simulation'] = {
            'success': True,
            'portfolio': portfolio,
            'positions': positions,
            'trades_count': len(trades)
        }
        
        print("✅ 시뮬레이션 모드 테스트 완료\n")
    
    async def test_strategy_execution(self):
        """전략 실행 테스트"""
        print("🤖 전략 실행 테스트")
        print("=" * 50)
        
        # 전략 매니저 테스트
        strategy_ids = self.create_test_strategies()
        
        print(f"생성된 전략: {len(strategy_ids)}개")
        for strategy_id in strategy_ids:
            strategy_info = self.strategy_manager.get_strategy_info(strategy_id)
            print(f"  {strategy_id}: {strategy_info['name']} ({strategy_info['type']})")
        
        # 전략 시작
        for strategy_id in strategy_ids:
            success = self.strategy_manager.start_strategy(strategy_id)
            print(f"전략 {strategy_id} 시작: {'성공' if success else '실패'}")
        
        # 테스트 데이터로 전략 실행
        test_data = self.generate_test_data('BTC', 1)
        test_data.index = pd.to_datetime(test_data['timestamp'])
        
        # 전략 실행
        results = self.strategy_manager.execute_strategies(test_data)
        
        print(f"\n전략 실행 결과:")
        for strategy_id, signals in results.items():
            print(f"  {strategy_id}: {len(signals)}개 신호 생성")
            for signal in signals[:3]:  # 최대 3개 신호만 표시
                print(f"    {signal.signal_type.value}: 강도 {signal.strength:.2f}, 신뢰도 {signal.confidence:.2f}")
        
        # 전략 중지
        for strategy_id in strategy_ids:
            self.strategy_manager.stop_strategy(strategy_id)
            print(f"전략 {strategy_id} 중지")
        
        self.test_results['strategy_execution'] = {
            'success': True,
            'strategies_created': len(strategy_ids),
            'signals_generated': sum(len(signals) for signals in results.values())
        }
        
        print("✅ 전략 실행 테스트 완료\n")
    
    async def test_data_collection(self):
        """데이터 수집 테스트"""
        print("📡 데이터 수집 테스트")
        print("=" * 50)
        
        # 데이터 수집기 생성
        from data.realtime_collector import RealtimeDataCollector
        collector = RealtimeDataCollector()
        
        # 구독 콜백 함수
        async def data_callback(data):
            print(f"데이터 수신: {data['symbol']} - {data['price']:,.0f}원")
        
        # 구독 등록
        collector.subscribe('BTC', data_callback)
        collector.subscribe('ETH', data_callback)
        
        # 짧은 시간 동안 데이터 수집
        print("5초간 데이터 수집 테스트...")
        collection_task = asyncio.create_task(
            collector.start_collection(['BTC', 'ETH'], ['market'])
        )
        
        await asyncio.sleep(5)
        await collector.stop_collection()
        
        # 수집된 데이터 확인
        btc_data = collector.get_latest_data('BTC')
        eth_data = collector.get_latest_data('ETH')
        
        print(f"BTC 최신 데이터: {btc_data}")
        print(f"ETH 최신 데이터: {eth_data}")
        
        btc_history = collector.get_historical_data('BTC', hours=1)
        eth_history = collector.get_historical_data('ETH', hours=1)
        
        print(f"BTC 과거 데이터: {len(btc_history)}개")
        print(f"ETH 과거 데이터: {len(eth_history)}개")
        
        self.test_results['data_collection'] = {
            'success': True,
            'btc_data': btc_data is not None,
            'eth_data': eth_data is not None,
            'btc_history_count': len(btc_history),
            'eth_history_count': len(eth_history)
        }
        
        print("✅ 데이터 수집 테스트 완료\n")
    
    async def test_portfolio_management(self):
        """포트폴리오 관리 테스트"""
        print("📊 포트폴리오 관리 테스트")
        print("=" * 50)
        
        # 거래 엔진 생성
        engine = RealtimeTradingEngine(
            mode=TradingMode.SIMULATION,
            initial_capital=1000000
        )
        
        # 모의 거래 실행
        from strategies.base_strategy import TradingSignal, SignalType
        
        # 매수 신호 생성
        buy_signal = TradingSignal(
            signal_type=SignalType.BUY,
            strength=0.8,
            confidence=0.7,
            price=50000,
            quantity=0.01,
            stop_loss=49000,
            take_profit=51000,
            timestamp=datetime.now(),
            reason="테스트 매수 신호"
        )
        
        # 매도 신호 생성
        sell_signal = TradingSignal(
            signal_type=SignalType.SELL,
            strength=0.9,
            confidence=0.8,
            price=52000,
            quantity=0.01,
            stop_loss=53000,
            take_profit=51000,
            timestamp=datetime.now(),
            reason="테스트 매도 신호"
        )
        
        # 시뮬레이션 거래 실행
        await engine._simulate_buy_order('BTC', buy_signal, 'test_strategy')
        await engine._simulate_sell_order('BTC', sell_signal, 'test_strategy')
        
        # 포트폴리오 요약
        portfolio = engine.get_portfolio_summary()
        positions = engine.get_positions()
        trades = engine.get_recent_trades()
        
        print(f"포트폴리오 요약:")
        print(f"  초기 자본: {portfolio['initial_capital']:,.0f}원")
        print(f"  현재 자본: {portfolio['current_capital']:,.0f}원")
        print(f"  총 가치: {portfolio['total_value']:,.0f}원")
        print(f"  총 수익률: {portfolio['total_return']:.2%}")
        
        print(f"\n포지션 정보:")
        for symbol, pos in positions.items():
            print(f"  {symbol}: {pos['side']} {pos['amount']:.6f} @ {pos['avg_price']:,.0f}원")
            print(f"    미실현 손익: {pos['unrealized_pnl']:,.0f}원")
            print(f"    실현 손익: {pos['realized_pnl']:,.0f}원")
        
        print(f"\n거래 내역:")
        for trade in trades:
            print(f"  {trade['timestamp']}: {trade['side']} {trade['symbol']} {trade['amount']:.6f} @ {trade['price']:,.0f}원")
            print(f"    수수료: {trade['commission']:,.0f}원")
        
        self.test_results['portfolio_management'] = {
            'success': True,
            'portfolio': portfolio,
            'positions': positions,
            'trades_count': len(trades)
        }
        
        print("✅ 포트폴리오 관리 테스트 완료\n")
    
    async def run_comprehensive_test(self):
        """종합 테스트 실행"""
        print("🚀 실시간 거래 시스템 종합 테스트")
        print("=" * 60)
        print(f"테스트 시작 시간: {datetime.now()}")
        print()
        
        try:
            # 1. 전략 실행 테스트
            await self.test_strategy_execution()
            
            # 2. 데이터 수집 테스트
            await self.test_data_collection()
            
            # 3. 포트폴리오 관리 테스트
            await self.test_portfolio_management()
            
            # 4. 시뮬레이션 모드 테스트
            await self.test_simulation_mode()
            
            # 테스트 결과 요약
            print("📊 테스트 결과 요약")
            print("=" * 50)
            
            total_tests = len(self.test_results)
            successful_tests = sum(1 for result in self.test_results.values() if result['success'])
            
            print(f"총 테스트: {total_tests}개")
            print(f"성공: {successful_tests}개")
            print(f"실패: {total_tests - successful_tests}개")
            print(f"성공률: {successful_tests/total_tests*100:.1f}%")
            
            print("\n상세 결과:")
            for test_name, result in self.test_results.items():
                status = "✅ 성공" if result['success'] else "❌ 실패"
                print(f"  {test_name}: {status}")
            
            print("\n🎉 모든 테스트가 완료되었습니다!")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    tester = RealtimeTradingTester()
    asyncio.run(tester.run_comprehensive_test())
