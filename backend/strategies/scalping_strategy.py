"""
스캘핑 전략 구현 (Paul Rotter 스타일)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy, StrategyConfig, StrategyType, SignalType, TradingSignal
from analysis.technical_indicators import technical_analyzer


class ScalpingStrategy(BaseStrategy):
    """스캘핑 전략 - 빠른 진입/청산을 통한 소폭 수익 추구"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.ema_short = config.parameters.get('ema_short', 8)
        self.ema_long = config.parameters.get('ema_long', 21)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.rsi_oversold = config.parameters.get('rsi_oversold', 30)
        self.rsi_overbought = config.parameters.get('rsi_overbought', 70)
        self.volume_threshold = config.parameters.get('volume_threshold', 1.5)
        self.min_profit_pct = config.parameters.get('min_profit_pct', 0.5)
        self.max_hold_time = config.parameters.get('max_hold_time', 300)  # 5분
    
    def analyze(self, data: pd.DataFrame) -> List[TradingSignal]:
        """스캘핑 분석"""
        signals = []
        
        if len(data) < 50:
            return signals
        
        # 기술적 지표 계산
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # EMA 계산
        ema_short = technical_analyzer.calculate_ema_talib(close, self.ema_short)
        ema_long = technical_analyzer.calculate_ema_talib(close, self.ema_long)
        
        # RSI 계산
        rsi = technical_analyzer.calculate_rsi(close, self.rsi_period)
        
        # 볼린저 밴드 계산
        bb_data = technical_analyzer.calculate_bollinger_bands(close, 20, 2.0)
        
        # 스토캐스틱 계산
        stoch_data = technical_analyzer.calculate_stochastic(high, low, close, 14, 3)
        
        # 현재 값들
        current_price = close.iloc[-1]
        current_ema_short = ema_short.iloc[-1]
        current_ema_long = ema_long.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_bb_upper = bb_data['upper'].iloc[-1]
        current_bb_lower = bb_data['lower'].iloc[-1]
        current_stoch_k = stoch_data['k'].iloc[-1]
        current_stoch_d = stoch_data['d'].iloc[-1]
        
        # 볼륨 분석
        volume_ma = volume.rolling(20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / volume_ma if volume_ma > 0 else 1
        
        # 신호 생성 로직
        signal_strength = 0.0
        signal_confidence = 0.0
        signal_type = SignalType.HOLD
        reason_parts = []
        
        # 1. EMA 크로스오버 신호
        if not pd.isna(current_ema_short) and not pd.isna(current_ema_long):
            if current_ema_short > current_ema_long and ema_short.iloc[-2] <= ema_long.iloc[-2]:
                signal_strength += 0.4
                signal_confidence += 0.3
                signal_type = SignalType.BUY
                reason_parts.append("EMA 골든크로스")
            elif current_ema_short < current_ema_long and ema_short.iloc[-2] >= ema_long.iloc[-2]:
                signal_strength += 0.4
                signal_confidence += 0.3
                signal_type = SignalType.SELL
                reason_parts.append("EMA 데드크로스")
        
        # 2. RSI 과매수/과매도 신호
        if not pd.isna(current_rsi):
            if current_rsi < self.rsi_oversold:
                signal_strength += 0.3
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.BUY
                reason_parts.append("RSI 과매도")
            elif current_rsi > self.rsi_overbought:
                signal_strength += 0.3
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.SELL
                reason_parts.append("RSI 과매수")
        
        # 3. 볼린저 밴드 신호
        if not pd.isna(current_bb_upper) and not pd.isna(current_bb_lower):
            if current_price <= current_bb_lower:
                signal_strength += 0.2
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.BUY
                reason_parts.append("볼린저 밴드 하단")
            elif current_price >= current_bb_upper:
                signal_strength += 0.2
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.SELL
                reason_parts.append("볼린저 밴드 상단")
        
        # 4. 스토캐스틱 신호
        if not pd.isna(current_stoch_k) and not pd.isna(current_stoch_d):
            if current_stoch_k < 20 and current_stoch_d < 20:
                signal_strength += 0.1
                signal_confidence += 0.1
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.BUY
                reason_parts.append("스토캐스틱 과매도")
            elif current_stoch_k > 80 and current_stoch_d > 80:
                signal_strength += 0.1
                signal_confidence += 0.1
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.SELL
                reason_parts.append("스토캐스틱 과매수")
        
        # 5. 볼륨 확인
        if volume_ratio < self.volume_threshold:
            signal_confidence *= 0.5  # 볼륨 부족 시 신뢰도 감소
        
        # 신호 생성
        if signal_type != SignalType.HOLD and signal_strength > 0.3:
            # 포지션 크기 계산 (스캘핑은 작은 크기)
            quantity = self.calculate_position_size(100000, current_price, current_price * 0.01)  # 1% 리스크
            
            # 손절/익절가 계산
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
                    'ema_short': current_ema_short,
                    'ema_long': current_ema_long,
                    'rsi': current_rsi,
                    'volume_ratio': volume_ratio,
                    'strategy': 'scalping'
                }
            )
            
            signals.append(signal)
        
        return signals
    
    def should_enter_position(self, data: pd.DataFrame) -> bool:
        """포지션 진입 조건"""
        if len(data) < 20:
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
        
        # 1. 시간 기반 청산 (최대 보유 시간)
        if (datetime.now() - entry_time).seconds > self.max_hold_time:
            return True
        
        # 2. 손절/익절 조건
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
        
        # 3. 최소 수익률 달성 시 청산
        if position.get('side') == 'long':
            profit_pct = (current_price - entry_price) / entry_price * 100
        else:
            profit_pct = (entry_price - current_price) / entry_price * 100
        
        if profit_pct >= self.min_profit_pct:
            return True
        
        return False
    
    def get_strategy_info(self) -> Dict:
        """전략 정보 반환"""
        return {
            'name': 'Scalping Strategy',
            'type': 'scalping',
            'description': '빠른 진입/청산을 통한 소폭 수익 추구',
            'parameters': {
                'ema_short': self.ema_short,
                'ema_long': self.ema_long,
                'rsi_period': self.rsi_period,
                'min_profit_pct': self.min_profit_pct,
                'max_hold_time': self.max_hold_time
            },
            'performance': self.get_performance_metrics()
        }
