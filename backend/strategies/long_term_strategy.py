"""
장기 투자 전략 구현 (DCA, 리밸런싱)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy, StrategyConfig, StrategyType, SignalType, TradingSignal
from analysis.technical_indicators import technical_analyzer


class LongTermStrategy(BaseStrategy):
    """장기 투자 전략 - DCA, 리밸런싱을 통한 장기 수익 추구"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.dca_amount = config.parameters.get('dca_amount', 100000)  # 10만원
        self.dca_interval = config.parameters.get('dca_interval', 7)  # 7일
        self.rebalance_threshold = config.parameters.get('rebalance_threshold', 0.05)  # 5%
        self.target_allocation = config.parameters.get('target_allocation', 0.7)  # 70%
        self.ema_long = config.parameters.get('ema_long', 200)
        self.ema_trend = config.parameters.get('ema_trend', 500)
        self.volatility_threshold = config.parameters.get('volatility_threshold', 0.3)
        self.max_drawdown = config.parameters.get('max_drawdown', 0.2)  # 20%
    
    def calculate_portfolio_allocation(self, data: pd.DataFrame, current_balance: float) -> Dict:
        """포트폴리오 할당 계산"""
        if len(data) < 50:
            return {'allocation': 0.0, 'reason': 'insufficient_data'}
        
        close = data['close']
        current_price = close.iloc[-1]
        
        # 장기 이동평균선 계산
        ema_long = technical_analyzer.calculate_ema_talib(close, self.ema_long)
        ema_trend = technical_analyzer.calculate_ema_talib(close, self.ema_trend)
        
        # 현재 할당률 계산
        current_allocation = (current_balance * self.target_allocation) / current_price
        
        # 트렌드 분석
        trend_score = 0
        if not pd.isna(ema_long.iloc[-1]) and not pd.isna(ema_trend.iloc[-1]):
            if current_price > ema_long.iloc[-1]:
                trend_score += 1
            if ema_long.iloc[-1] > ema_trend.iloc[-1]:
                trend_score += 1
        
        # 변동성 분석
        returns = close.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # 연환산 변동성
        
        # 할당률 조정
        if trend_score >= 2 and volatility < self.volatility_threshold:
            target_allocation = self.target_allocation
            reason = "강한 상승 트렌드 + 낮은 변동성"
        elif trend_score >= 1:
            target_allocation = self.target_allocation * 0.8
            reason = "중간 트렌드"
        else:
            target_allocation = self.target_allocation * 0.5
            reason = "약한 트렌드"
        
        return {
            'allocation': target_allocation,
            'current_allocation': current_allocation,
            'trend_score': trend_score,
            'volatility': volatility,
            'reason': reason
        }
    
    def should_dca_buy(self, data: pd.DataFrame, last_dca_date: datetime) -> bool:
        """DCA 매수 조건"""
        # 시간 간격 확인
        if (datetime.now() - last_dca_date).days < self.dca_interval:
            return False
        
        # 기본 DCA 조건 (시간 기반)
        return True
    
    def should_rebalance(self, data: pd.DataFrame, current_allocation: float) -> bool:
        """리밸런싱 조건"""
        target_allocation = self.target_allocation
        
        # 할당률 차이 확인
        allocation_diff = abs(current_allocation - target_allocation) / target_allocation
        
        return allocation_diff > self.rebalance_threshold
    
    def calculate_drawdown(self, data: pd.DataFrame) -> float:
        """최대 낙폭 계산"""
        if len(data) < 20:
            return 0.0
        
        close = data['close']
        peak = close.expanding().max()
        drawdown = (close - peak) / peak
        max_drawdown = drawdown.min()
        
        return abs(max_drawdown)
    
    def analyze(self, data: pd.DataFrame) -> List[TradingSignal]:
        """장기 투자 분석"""
        signals = []
        
        if len(data) < 100:
            return signals
        
        # 기술적 지표 계산
        close = data['close']
        current_price = close.iloc[-1]
        
        # 장기 이동평균선 계산
        ema_long = technical_analyzer.calculate_ema_talib(close, self.ema_long)
        ema_trend = technical_analyzer.calculate_ema_talib(close, self.ema_trend)
        
        # RSI 계산 (장기)
        rsi = technical_analyzer.calculate_rsi(close, 14)
        
        # 변동성 계산
        returns = close.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)
        
        # 최대 낙폭 계산
        max_dd = self.calculate_drawdown(data)
        
        # 현재 값들
        current_ema_long = ema_long.iloc[-1]
        current_ema_trend = ema_trend.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # 신호 생성 로직
        signal_strength = 0.0
        signal_confidence = 0.0
        signal_type = SignalType.HOLD
        reason_parts = []
        
        # 1. 장기 트렌드 확인
        if (not pd.isna(current_ema_long) and not pd.isna(current_ema_trend) and
            current_price > current_ema_long and current_ema_long > current_ema_trend):
            signal_strength += 0.4
            signal_confidence += 0.3
            signal_type = SignalType.BUY
            reason_parts.append("강한 장기 상승 트렌드")
        
        # 2. RSI 확인 (장기 관점)
        if not pd.isna(current_rsi):
            if current_rsi < 50:  # 중립선 이하
                signal_strength += 0.2
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.BUY
                reason_parts.append("RSI 매수 구간")
            elif current_rsi > 70:  # 과매수
                signal_strength += 0.2
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.SELL
                reason_parts.append("RSI 과매수")
        
        # 3. 변동성 확인
        if volatility < self.volatility_threshold:
            signal_confidence += 0.1
            reason_parts.append("낮은 변동성")
        elif volatility > 0.5:  # 높은 변동성
            signal_confidence *= 0.8
            reason_parts.append("높은 변동성")
        
        # 4. 최대 낙폭 확인
        if max_dd > self.max_drawdown:
            signal_confidence *= 0.7
            reason_parts.append("높은 최대 낙폭")
        
        # 5. DCA 조건 확인
        if signal_type == SignalType.BUY:
            # DCA 매수 신호
            signal_strength += 0.3
            signal_confidence += 0.2
            reason_parts.append("DCA 매수")
        
        # 신호 생성
        if signal_type != SignalType.HOLD and signal_strength > 0.4:
            # 포지션 크기 계산 (장기 투자는 큰 크기)
            quantity = self.calculate_position_size(1000000, current_price, current_price * 0.05)  # 5% 리스크
            
            # 손절/익절가 계산 (장기 투자는 넓은 범위)
            stop_loss = self.calculate_stop_loss(current_price, signal_type)
            take_profit = self.calculate_take_profit(current_price, signal_type)
            
            signal = TradingSignal(
                signal_type=signal_type,
                strength=min(signal_strength, 1.0),
                confidence=min(signal_confidence, 1.0),
                price=current_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=datetime.now(),
                reason=" | ".join(reason_parts),
                metadata={
                    'ema_long': current_ema_long,
                    'ema_trend': current_ema_trend,
                    'rsi': current_rsi,
                    'volatility': volatility,
                    'max_drawdown': max_dd,
                    'strategy': 'long_term'
                }
            )
            
            signals.append(signal)
        
        return signals
    
    def should_enter_position(self, data: pd.DataFrame) -> bool:
        """포지션 진입 조건"""
        if len(data) < 50:
            return False
        
        # 현재 포지션 수 확인
        if len(self.positions) >= self.config.max_positions:
            return False
        
        # 최근 신호 분석
        signals = self.analyze(data)
        return len(signals) > 0 and signals[0].strength > 0.5
    
    def should_exit_position(self, data: pd.DataFrame, position: Dict) -> bool:
        """포지션 청산 조건"""
        if not position:
            return False
        
        current_price = data['close'].iloc[-1]
        entry_price = position.get('entry_price', 0)
        entry_time = position.get('entry_time', datetime.now())
        
        # 1. 손절/익절 조건
        if position.get('side') == 'long':
            if current_price <= position.get('stop_loss', 0):
                return True
            if current_price >= position.get('take_profit', 0):
                return True
        else:
            if current_price >= position.get('stop_loss', 0):
                return True
            if current_price <= position.get('take_profit', 0):
                return True
        
        # 2. 장기 트렌드 반전 시 청산
        if len(data) >= 50:
            ema_long = technical_analyzer.calculate_ema_talib(data['close'], self.ema_long)
            ema_trend = technical_analyzer.calculate_ema_talib(data['close'], self.ema_trend)
            
            if not pd.isna(ema_long.iloc[-1]) and not pd.isna(ema_trend.iloc[-1]):
                if position.get('side') == 'long' and ema_long.iloc[-1] < ema_trend.iloc[-1]:
                    return True
                elif position.get('side') == 'short' and ema_long.iloc[-1] > ema_trend.iloc[-1]:
                    return True
        
        # 3. 최대 낙폭 초과 시 청산
        max_dd = self.calculate_drawdown(data)
        if max_dd > self.max_drawdown:
            return True
        
        # 4. 장기 보유 후 청산 (1년)
        if (datetime.now() - entry_time).days >= 365:
            return True
        
        return False
    
    def get_strategy_info(self) -> Dict:
        """전략 정보 반환"""
        return {
            'name': 'Long Term Strategy',
            'type': 'long_term',
            'description': 'DCA, 리밸런싱을 통한 장기 수익 추구',
            'parameters': {
                'dca_amount': self.dca_amount,
                'dca_interval': self.dca_interval,
                'rebalance_threshold': self.rebalance_threshold,
                'target_allocation': self.target_allocation,
                'max_drawdown': self.max_drawdown
            },
            'performance': self.get_performance_metrics()
        }
