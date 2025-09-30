"""
고도화된 전략 시스템 통합 테스트
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import sys
import os

# 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.advanced_indicators import AdvancedIndicators, MarketRegime
from analysis.ml_signals import MLSignalGenerator, MLModelType
from core.bithumb_optimization import BithumbOptimizer, MakerTakerStrategy
from data.realtime_collector import RealtimeDataCollector
from portfolio.portfolio_manager import PortfolioManager, RiskModel, RebalancingStrategy


class EnhancedStrategyTester:
    """고도화된 전략 테스터"""
    
    def __init__(self):
        self.advanced_indicators = AdvancedIndicators()
        self.ml_generator = MLSignalGenerator(MLModelType.ENSEMBLE)
        self.bithumb_optimizer = BithumbOptimizer()
        self.portfolio_manager = PortfolioManager(initial_capital=1000000)
        self.data_collector = RealtimeDataCollector()
        
        # 테스트 데이터 생성
        self.sample_data = self._generate_sample_data()
        
    def _generate_sample_data(self, days: int = 100) -> pd.DataFrame:
        """샘플 데이터 생성"""
        np.random.seed(42)
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                             end=datetime.now(), freq='1H')
        
        # 다중 자산 데이터 생성
        assets = ['BTC', 'ETH', 'ADA', 'DOT', 'LINK']
        data = {}
        
        for asset in assets:
            # 각 자산별로 다른 특성의 가격 데이터 생성
            base_price = {'BTC': 50000, 'ETH': 3000, 'ADA': 0.5, 'DOT': 20, 'LINK': 15}[asset]
            
            # 랜덤 워크 + 트렌드
            returns = np.random.normal(0.0001, 0.02, len(dates))  # 시간당 수익률
            prices = [base_price]
            
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # OHLCV 데이터 생성
            data[f'{asset}_close'] = prices
            data[f'{asset}_high'] = [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices]
            data[f'{asset}_low'] = [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices]
            data[f'{asset}_volume'] = np.random.uniform(1000, 10000, len(dates))
        
        df = pd.DataFrame(data, index=dates)
        
        # 기본 OHLCV 컬럼 추가 (BTC 기준)
        df['open'] = df['BTC_close'].shift(1).fillna(df['BTC_close'].iloc[0])
        df['high'] = df['BTC_high']
        df['low'] = df['BTC_low']
        df['close'] = df['BTC_close']
        df['volume'] = df['BTC_volume']
        
        return df
    
    def test_advanced_indicators(self):
        """고급 지표 테스트"""
        print("🔍 고급 기술적 지표 테스트")
        print("=" * 50)
        
        data = self.sample_data
        
        # 일목균형표
        ichimoku = self.advanced_indicators.calculate_ichimoku_cloud(
            data['high'], data['low'], data['close']
        )
        print(f"일목균형표 전환선: {ichimoku['tenkan_sen'].iloc[-1]:.2f}")
        print(f"일목균형표 기준선: {ichimoku['kijun_sen'].iloc[-1]:.2f}")
        
        # Williams %R
        williams_r = self.advanced_indicators.calculate_williams_r(
            data['high'], data['low'], data['close']
        )
        print(f"Williams %R: {williams_r.iloc[-1]:.2f}")
        
        # Money Flow Index
        mfi = self.advanced_indicators.calculate_money_flow_index(
            data['high'], data['low'], data['close'], data['volume']
        )
        print(f"Money Flow Index: {mfi.iloc[-1]:.2f}")
        
        # Aroon 지표
        aroon = self.advanced_indicators.calculate_aroon(data['high'], data['low'])
        print(f"Aroon Up: {aroon['aroon_up'].iloc[-1]:.2f}")
        print(f"Aroon Down: {aroon['aroon_down'].iloc[-1]:.2f}")
        
        # 시장 상황 분석
        market_condition = self.advanced_indicators.calculate_market_regime(data)
        print(f"시장 상황: {market_condition.regime.value}")
        print(f"트렌드 강도: {market_condition.strength:.3f}")
        print(f"변동성: {market_condition.volatility:.3f}")
        print(f"신뢰도: {market_condition.confidence:.3f}")
        
        # 지지/저항선
        support_resistance = self.advanced_indicators.calculate_support_resistance_levels(
            data['high'], data['low'], data['close']
        )
        print(f"저항선: {support_resistance['resistance']}")
        print(f"지지선: {support_resistance['support']}")
        
        print("✅ 고급 지표 테스트 완료\n")
    
    def test_ml_signals(self):
        """ML 신호 생성 테스트"""
        print("🤖 머신러닝 신호 생성 테스트")
        print("=" * 50)
        
        # 훈련 데이터 준비
        X, y = self.ml_generator.prepare_training_data(self.sample_data)
        print(f"특성 수: {X.shape[1]}")
        print(f"샘플 수: {X.shape[0]}")
        print(f"타겟 분포: {y.value_counts().to_dict()}")
        
        # 모델 훈련
        accuracy = self.ml_generator.train_models(X, y)
        print(f"모델 정확도: {accuracy:.3f}")
        
        # 신호 생성
        signal = self.ml_generator.generate_signal(self.sample_data)
        print(f"ML 신호: {signal.signal_type}")
        print(f"신뢰도: {signal.confidence:.3f}")
        print(f"확률: {signal.probability:.3f}")
        print(f"사용된 모델: {signal.model_used}")
        
        # 주요 특성 중요도
        top_features = sorted(signal.features_importance.items(), 
                            key=lambda x: x[1], reverse=True)[:5]
        print("주요 특성 중요도:")
        for feature, importance in top_features:
            print(f"  {feature}: {importance:.3f}")
        
        print("✅ ML 신호 테스트 완료\n")
    
    def test_bithumb_optimization(self):
        """빗썸 수수료 최적화 테스트"""
        print("💰 빗썸 수수료 최적화 테스트")
        print("=" * 50)
        
        # 최적 전략 계산
        order_size = 1000000  # 100만원
        market_volatility = 0.03  # 3% 변동성
        
        optimization = self.bithumb_optimizer.calculate_optimal_strategy(
            order_size, market_volatility, urgency='normal'
        )
        
        print(f"권장 전략: {optimization.strategy.value}")
        print(f"예상 수수료: {optimization.expected_commission:,.0f}원")
        print(f"예상 절약: {optimization.expected_savings:,.0f}원")
        print(f"체결 시간: {optimization.execution_time:.1f}초")
        print(f"성공 확률: {optimization.success_probability:.1%}")
        print(f"리스크 레벨: {optimization.risk_level}")
        
        # 거래량 할인 계산
        monthly_volume = 50000000  # 5000만원
        discount_rate = self.bithumb_optimizer.calculate_volume_discount(monthly_volume)
        print(f"거래량 할인율: {discount_rate:.4f} ({discount_rate*100:.2f}%)")
        
        # 주문 분할 최적화
        market_depth = {
            'bids': [
                {'price': 50000, 'volume': 1000},
                {'price': 49999, 'volume': 2000},
                {'price': 49998, 'volume': 1500}
            ],
            'asks': [
                {'price': 50001, 'volume': 800},
                {'price': 50002, 'volume': 1200},
                {'price': 50003, 'volume': 1000}
            ]
        }
        
        optimal_splits = self.bithumb_optimizer.optimize_order_splitting(
            total_amount=500000, market_depth=market_depth
        )
        
        print("최적 주문 분할:")
        for i, split in enumerate(optimal_splits):
            print(f"  {i+1}. {split['type']} 주문: {split['amount']:,.0f}원, "
                  f"수수료: {split['expected_commission']:,.0f}원")
        
        print("✅ 빗썸 최적화 테스트 완료\n")
    
    def test_portfolio_management(self):
        """포트폴리오 관리 테스트"""
        print("📊 포트폴리오 관리 테스트")
        print("=" * 50)
        
        # 자산 추가
        assets = ['BTC', 'ETH', 'ADA', 'DOT', 'LINK']
        target_weights = [0.4, 0.3, 0.1, 0.1, 0.1]
        
        for symbol, weight in zip(assets, target_weights):
            self.portfolio_manager.add_asset(symbol, f"{symbol} 코인", weight)
        
        # 가격 데이터 업데이트
        price_data = {
            'BTC': 50000, 'ETH': 3000, 'ADA': 0.5, 
            'DOT': 20, 'LINK': 15
        }
        self.portfolio_manager.update_asset_prices(price_data)
        
        # 수익률 데이터 생성
        returns_data = pd.DataFrame()
        for asset in assets:
            returns_data[asset] = np.random.normal(0.001, 0.02, 100)
        
        # 포트폴리오 지표 계산
        metrics = self.portfolio_manager.calculate_portfolio_metrics(returns_data)
        print(f"총 가치: {metrics.total_value:,.0f}원")
        print(f"총 수익률: {metrics.total_return:.2%}")
        print(f"연환산 수익률: {metrics.annualized_return:.2%}")
        print(f"변동성: {metrics.volatility:.2%}")
        print(f"샤프 비율: {metrics.sharpe_ratio:.3f}")
        print(f"소르티노 비율: {metrics.sortino_ratio:.3f}")
        print(f"최대 낙폭: {metrics.max_drawdown:.2%}")
        print(f"VaR 95%: {metrics.var_95:.2%}")
        print(f"CVaR 95%: {metrics.cvar_95:.2%}")
        print(f"다양화 비율: {metrics.diversification_ratio:.3f}")
        print(f"집중도 리스크: {metrics.concentration_risk:.3f}")
        
        # 리밸런싱 신호 확인
        rebalancing_signal = self.portfolio_manager.check_rebalancing_signal()
        print(f"\n리밸런싱 필요: {rebalancing_signal.should_rebalance}")
        print(f"이유: {rebalancing_signal.reason}")
        print(f"긴급도: {rebalancing_signal.urgency}")
        
        # 포트폴리오 최적화
        optimal_weights = self.portfolio_manager.optimize_portfolio_weights(
            returns_data, RiskModel.SHARPE_OPTIMIZED
        )
        print("\n최적 가중치:")
        for symbol, weight in optimal_weights.items():
            print(f"  {symbol}: {weight:.3f}")
        
        # 상관관계 분석
        correlation_matrix = self.portfolio_manager.calculate_correlation_matrix(returns_data)
        print(f"\n상관관계 행렬 크기: {correlation_matrix.shape}")
        
        # 포트폴리오 리포트
        report = self.portfolio_manager.generate_portfolio_report()
        print(f"\n포트폴리오 요약:")
        print(f"  총 자산 수: {report['portfolio_summary']['total_assets']}")
        print(f"  현재 자본: {report['portfolio_summary']['current_capital']:,.0f}원")
        print(f"  리밸런싱 전략: {report['portfolio_summary']['rebalancing_strategy']}")
        print(f"  리스크 모델: {report['portfolio_summary']['risk_model']}")
        
        print("✅ 포트폴리오 관리 테스트 완료\n")
    
    async def test_realtime_data_collection(self):
        """실시간 데이터 수집 테스트"""
        print("📡 실시간 데이터 수집 테스트")
        print("=" * 50)
        
        # 데이터 수집기 초기화
        symbols = ['BTC', 'ETH']
        
        # 구독 콜백 함수
        async def market_data_callback(data):
            print(f"시장 데이터 수신: {data['symbol']} - {data['price']:,.0f}원")
        
        async def news_callback(news):
            print(f"뉴스 수신: {news.title[:50]}... (센티먼트: {news.sentiment})")
        
        async def sentiment_callback(sentiment):
            print(f"센티먼트 수신: {sentiment.symbol} - {sentiment.sentiment_score:.3f}")
        
        # 구독 등록
        for symbol in symbols:
            self.data_collector.subscribe(symbol, market_data_callback)
        
        # 짧은 시간 동안 데이터 수집 테스트
        print("5초간 데이터 수집 테스트...")
        collection_task = asyncio.create_task(
            self.data_collector.start_collection(symbols, ['market'])
        )
        
        await asyncio.sleep(5)
        await self.data_collector.stop_collection()
        
        # 수집된 데이터 확인
        for symbol in symbols:
            latest_data = self.data_collector.get_latest_data(symbol)
            if latest_data:
                print(f"{symbol} 최신 데이터: {latest_data}")
            
            historical_data = self.data_collector.get_historical_data(symbol, hours=1)
            print(f"{symbol} 과거 데이터 수: {len(historical_data)}")
        
        print("✅ 실시간 데이터 수집 테스트 완료\n")
    
    def run_comprehensive_test(self):
        """종합 테스트 실행"""
        print("🚀 고도화된 전략 시스템 종합 테스트")
        print("=" * 60)
        print(f"테스트 시작 시간: {datetime.now()}")
        print()
        
        try:
            # 1. 고급 지표 테스트
            self.test_advanced_indicators()
            
            # 2. ML 신호 테스트
            self.test_ml_signals()
            
            # 3. 빗썸 최적화 테스트
            self.test_bithumb_optimization()
            
            # 4. 포트폴리오 관리 테스트
            self.test_portfolio_management()
            
            # 5. 실시간 데이터 수집 테스트
            print("📡 실시간 데이터 수집 테스트 (비동기)")
            print("=" * 50)
            asyncio.run(self.test_realtime_data_collection())
            
            print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ 테스트 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    tester = EnhancedStrategyTester()
    tester.run_comprehensive_test()
