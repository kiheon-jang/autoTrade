"""
포트폴리오 관리 시스템
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class RebalancingStrategy(Enum):
    """리밸런싱 전략"""
    TIME_BASED = "time_based"          # 시간 기반
    THRESHOLD_BASED = "threshold_based"  # 임계값 기반
    VOLATILITY_BASED = "volatility_based"  # 변동성 기반
    MOMENTUM_BASED = "momentum_based"    # 모멘텀 기반


class RiskModel(Enum):
    """리스크 모델"""
    EQUAL_WEIGHT = "equal_weight"      # 동일 가중
    MARKET_CAP = "market_cap"          # 시가총액 가중
    VOLATILITY_ADJUSTED = "volatility_adjusted"  # 변동성 조정
    SHARPE_OPTIMIZED = "sharpe_optimized"  # 샤프 비율 최적화


@dataclass
class Asset:
    """자산 정보"""
    symbol: str
    name: str
    current_price: float
    weight: float
    target_weight: float
    volatility: float
    expected_return: float
    correlation_matrix: Optional[np.ndarray] = None


@dataclass
class PortfolioMetrics:
    """포트폴리오 지표"""
    total_value: float
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float  # 95% VaR
    cvar_95: float  # 95% CVaR
    diversification_ratio: float
    concentration_risk: float


@dataclass
class RebalancingSignal:
    """리밸런싱 신호"""
    should_rebalance: bool
    reason: str
    current_weights: Dict[str, float]
    target_weights: Dict[str, float]
    expected_impact: float
    urgency: str  # 'low', 'medium', 'high'


class PortfolioManager:
    """포트폴리오 관리자"""
    
    def __init__(self, initial_capital: float = 1000000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.assets: Dict[str, Asset] = {}
        self.portfolio_history = []
        self.rebalancing_strategy = RebalancingStrategy.THRESHOLD_BASED
        self.risk_model = RiskModel.SHARPE_OPTIMIZED
        
        # 리밸런싱 설정
        self.rebalancing_threshold = 0.05  # 5% 임계값
        self.last_rebalancing = datetime.now()
        self.rebalancing_frequency = timedelta(days=7)  # 주간 리밸런싱
        
        # 리스크 관리 설정
        self.max_position_size = 0.3  # 최대 포지션 30%
        self.min_position_size = 0.01  # 최소 포지션 1%
        self.max_correlation = 0.7  # 최대 상관관계 70%
        
        # 성과 추적
        self.performance_metrics = {}
    
    def add_asset(self, symbol: str, name: str, target_weight: float, 
                  current_price: float = 0.0) -> None:
        """자산 추가"""
        self.assets[symbol] = Asset(
            symbol=symbol,
            name=name,
            current_price=current_price,
            weight=0.0,
            target_weight=target_weight,
            volatility=0.0,
            expected_return=0.0
        )
    
    def update_asset_prices(self, price_data: Dict[str, float]) -> None:
        """자산 가격 업데이트"""
        for symbol, price in price_data.items():
            if symbol in self.assets:
                self.assets[symbol].current_price = price
    
    def calculate_portfolio_metrics(self, returns_data: pd.DataFrame) -> PortfolioMetrics:
        """포트폴리오 지표 계산"""
        if returns_data.empty:
            return PortfolioMetrics(
                total_value=self.current_capital,
                total_return=0.0,
                annualized_return=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                var_95=0.0,
                cvar_95=0.0,
                diversification_ratio=0.0,
                concentration_risk=0.0
            )
        
        # 포트폴리오 수익률 계산
        weights = np.array([asset.weight for asset in self.assets.values()])
        portfolio_returns = (returns_data * weights).sum(axis=1)
        
        # 기본 지표
        total_return = (1 + portfolio_returns).prod() - 1
        annualized_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        volatility = portfolio_returns.std() * np.sqrt(252)
        
        # 샤프 비율
        risk_free_rate = 0.02  # 2% 무위험 수익률
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 소르티노 비율
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (annualized_return - risk_free_rate) / downside_volatility if downside_volatility > 0 else 0
        
        # 최대 낙폭
        cumulative_returns = (1 + portfolio_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # VaR 및 CVaR
        var_95 = np.percentile(portfolio_returns, 5)
        cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
        
        # 다양화 비율
        diversification_ratio = self._calculate_diversification_ratio(returns_data, weights)
        
        # 집중도 리스크
        concentration_risk = self._calculate_concentration_risk(weights)
        
        return PortfolioMetrics(
            total_value=self.current_capital * (1 + total_return),
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            cvar_95=cvar_95,
            diversification_ratio=diversification_ratio,
            concentration_risk=concentration_risk
        )
    
    def _calculate_diversification_ratio(self, returns_data: pd.DataFrame, weights: np.ndarray) -> float:
        """다양화 비율 계산"""
        if returns_data.empty:
            return 0.0
        
        # 개별 자산의 가중 평균 변동성
        individual_volatilities = returns_data.std() * np.sqrt(252)
        weighted_avg_volatility = np.sum(weights * individual_volatilities)
        
        # 포트폴리오 변동성
        portfolio_returns = (returns_data * weights).sum(axis=1)
        portfolio_volatility = portfolio_returns.std() * np.sqrt(252)
        
        return weighted_avg_volatility / portfolio_volatility if portfolio_volatility > 0 else 0
    
    def _calculate_concentration_risk(self, weights: np.ndarray) -> float:
        """집중도 리스크 계산 (헤르핀달 지수)"""
        return np.sum(weights ** 2)
    
    def optimize_portfolio_weights(self, returns_data: pd.DataFrame, 
                                  risk_model: RiskModel = None) -> Dict[str, float]:
        """포트폴리오 가중치 최적화"""
        if risk_model is None:
            risk_model = self.risk_model
        
        if returns_data.empty:
            # 동일 가중 반환
            equal_weight = 1.0 / len(self.assets)
            return {symbol: equal_weight for symbol in self.assets.keys()}
        
        if risk_model == RiskModel.EQUAL_WEIGHT:
            return self._equal_weight_allocation()
        
        elif risk_model == RiskModel.MARKET_CAP:
            return self._market_cap_allocation()
        
        elif risk_model == RiskModel.VOLATILITY_ADJUSTED:
            return self._volatility_adjusted_allocation(returns_data)
        
        elif risk_model == RiskModel.SHARPE_OPTIMIZED:
            return self._sharpe_optimized_allocation(returns_data)
        
        else:
            return self._equal_weight_allocation()
    
    def _equal_weight_allocation(self) -> Dict[str, float]:
        """동일 가중 할당"""
        equal_weight = 1.0 / len(self.assets)
        return {symbol: equal_weight for symbol in self.assets.keys()}
    
    def _market_cap_allocation(self) -> Dict[str, float]:
        """시가총액 가중 할당"""
        # 실제로는 시가총액 데이터가 필요하지만, 여기서는 모의 데이터 사용
        market_caps = {
            'BTC': 0.4,
            'ETH': 0.3,
            'ADA': 0.1,
            'DOT': 0.1,
            'LINK': 0.1
        }
        
        total_cap = sum(market_caps.values())
        return {symbol: market_caps.get(symbol, 0.1) / total_cap for symbol in self.assets.keys()}
    
    def _volatility_adjusted_allocation(self, returns_data: pd.DataFrame) -> Dict[str, float]:
        """변동성 조정 할당"""
        volatilities = returns_data.std() * np.sqrt(252)
        inverse_volatilities = 1 / volatilities
        total_inverse_vol = inverse_volatilities.sum()
        
        weights = {}
        for symbol in self.assets.keys():
            if symbol in returns_data.columns:
                weights[symbol] = inverse_volatilities[symbol] / total_inverse_vol
            else:
                weights[symbol] = 1.0 / len(self.assets)
        
        return weights
    
    def _sharpe_optimized_allocation(self, returns_data: pd.DataFrame) -> Dict[str, float]:
        """샤프 비율 최적화 할당"""
        def negative_sharpe(weights):
            portfolio_return = np.sum(returns_data.mean() * weights) * 252
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(returns_data.cov() * 252, weights)))
            return -(portfolio_return - 0.02) / portfolio_volatility  # 2% 무위험 수익률
        
        # 제약 조건
        constraints = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        bounds = tuple((0, 1) for _ in range(len(self.assets)))
        
        # 초기 가중치
        initial_weights = np.array([1.0 / len(self.assets)] * len(self.assets))
        
        # 최적화
        result = minimize(negative_sharpe, initial_weights, method='SLSQP', 
                         bounds=bounds, constraints=constraints)
        
        if result.success:
            weights = result.x
        else:
            weights = initial_weights
        
        return {symbol: weights[i] for i, symbol in enumerate(self.assets.keys())}
    
    def check_rebalancing_signal(self) -> RebalancingSignal:
        """리밸런싱 신호 확인"""
        current_weights = {symbol: asset.weight for symbol, asset in self.assets.items()}
        target_weights = {symbol: asset.target_weight for symbol, asset in self.assets.items()}
        
        # 가중치 편차 계산
        weight_deviations = {}
        max_deviation = 0.0
        total_deviation = 0.0
        
        for symbol in self.assets.keys():
            deviation = abs(current_weights[symbol] - target_weights[symbol])
            weight_deviations[symbol] = deviation
            max_deviation = max(max_deviation, deviation)
            total_deviation += deviation
        
        # 리밸런싱 필요성 판단
        should_rebalance = False
        reason = ""
        
        if self.rebalancing_strategy == RebalancingStrategy.THRESHOLD_BASED:
            if max_deviation > self.rebalancing_threshold:
                should_rebalance = True
                reason = f"최대 편차 {max_deviation:.3f}이 임계값 {self.rebalancing_threshold} 초과"
        
        elif self.rebalancing_strategy == RebalancingStrategy.TIME_BASED:
            if datetime.now() - self.last_rebalancing > self.rebalancing_frequency:
                should_rebalance = True
                reason = "정기 리밸런싱 시점"
        
        # 긴급도 계산
        urgency = "low"
        if max_deviation > 0.1:  # 10% 이상 편차
            urgency = "high"
        elif max_deviation > 0.05:  # 5% 이상 편차
            urgency = "medium"
        
        return RebalancingSignal(
            should_rebalance=should_rebalance,
            reason=reason,
            current_weights=current_weights,
            target_weights=target_weights,
            expected_impact=total_deviation,
            urgency=urgency
        )
    
    def execute_rebalancing(self, new_weights: Dict[str, float]) -> Dict[str, float]:
        """리밸런싱 실행"""
        # 거래 비용 계산
        current_weights = {symbol: asset.weight for symbol, asset in self.assets.items()}
        weight_changes = {symbol: new_weights[symbol] - current_weights[symbol] 
                         for symbol in self.assets.keys()}
        
        # 거래 비용 (수수료)
        total_turnover = sum(abs(change) for change in weight_changes.values())
        transaction_cost = total_turnover * 0.0015  # 0.15% 수수료
        
        # 가중치 업데이트
        for symbol, new_weight in new_weights.items():
            if symbol in self.assets:
                self.assets[symbol].weight = new_weight
        
        # 리밸런싱 시간 업데이트
        self.last_rebalancing = datetime.now()
        
        # 포트폴리오 히스토리 업데이트
        self.portfolio_history.append({
            'timestamp': datetime.now(),
            'weights': new_weights.copy(),
            'transaction_cost': transaction_cost,
            'total_turnover': total_turnover
        })
        
        return weight_changes
    
    def calculate_correlation_matrix(self, returns_data: pd.DataFrame) -> pd.DataFrame:
        """상관관계 행렬 계산"""
        if returns_data.empty:
            return pd.DataFrame()
        
        return returns_data.corr()
    
    def detect_correlation_breaks(self, returns_data: pd.DataFrame, 
                                 window: int = 30) -> Dict[str, List[str]]:
        """상관관계 변화 감지"""
        if len(returns_data) < window * 2:
            return {}
        
        correlation_breaks = {}
        
        # 롤링 상관관계 계산
        rolling_corr = returns_data.rolling(window).corr()
        
        # 최근 상관관계와 과거 상관관계 비교
        recent_corr = rolling_corr.iloc[-window:].mean()
        historical_corr = rolling_corr.iloc[-window*2:-window].mean()
        
        # 상관관계 변화 감지
        for symbol in returns_data.columns:
            breaks = []
            for other_symbol in returns_data.columns:
                if symbol != other_symbol:
                    corr_change = abs(recent_corr.loc[symbol, other_symbol] - 
                                    historical_corr.loc[symbol, other_symbol])
                    if corr_change > 0.3:  # 30% 이상 변화
                        breaks.append(other_symbol)
            
            if breaks:
                correlation_breaks[symbol] = breaks
        
        return correlation_breaks
    
    def generate_portfolio_report(self) -> Dict[str, Any]:
        """포트폴리오 리포트 생성"""
        current_weights = {symbol: asset.weight for symbol, asset in self.assets.items()}
        target_weights = {symbol: asset.target_weight for symbol, asset in self.assets.items()}
        
        # 가중치 편차
        weight_deviations = {symbol: abs(current_weights[symbol] - target_weights[symbol])
                           for symbol in self.assets.keys()}
        
        # 리밸런싱 신호
        rebalancing_signal = self.check_rebalancing_signal()
        
        return {
            'portfolio_summary': {
                'total_assets': len(self.assets),
                'current_capital': self.current_capital,
                'rebalancing_strategy': self.rebalancing_strategy.value,
                'risk_model': self.risk_model.value
            },
            'current_weights': current_weights,
            'target_weights': target_weights,
            'weight_deviations': weight_deviations,
            'rebalancing_signal': {
                'should_rebalance': rebalancing_signal.should_rebalance,
                'reason': rebalancing_signal.reason,
                'urgency': rebalancing_signal.urgency,
                'expected_impact': rebalancing_signal.expected_impact
            },
            'last_rebalancing': self.last_rebalancing.isoformat(),
            'next_rebalancing': (self.last_rebalancing + self.rebalancing_frequency).isoformat()
        }
