"""
스윙 트레이딩 전략 구현 (피보나치 되돌림, 이동평균 크로스오버)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy, StrategyConfig, StrategyType, SignalType, TradingSignal
from analysis.technical_indicators import technical_analyzer


class SwingTradingStrategy(BaseStrategy):
    """스윙 트레이딩 전략 - 중기 트렌드를 활용한 수익 추구"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.ema_short = config.parameters.get('ema_short', 21)
        self.ema_long = config.parameters.get('ema_long', 50)
        self.ema_trend = config.parameters.get('ema_trend', 200)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.fibonacci_levels = config.parameters.get('fibonacci_levels', [0.236, 0.382, 0.5, 0.618, 0.786])
        self.trend_lookback = config.parameters.get('trend_lookback', 20)
        self.volume_ma_period = config.parameters.get('volume_ma_period', 20)
        self.min_trend_strength = config.parameters.get('min_trend_strength', 0.4)
    
    def identify_trend(self, data: pd.DataFrame) -> Dict:
        """트렌드 식별"""
        if len(data) < self.trend_lookback:
            return {'trend': 'neutral', 'strength': 0.0}
        
        recent_data = data.tail(self.trend_lookback)
        close = recent_data['close']
        high = recent_data['high']
        low = recent_data['low']
        
        # 트렌드 강도 계산
        price_change = (close.iloc[-1] - close.iloc[0]) / close.iloc[0]
        volatility = (high.max() - low.min()) / close.mean()
        
        # 이동평균선 기반 트렌드
        ema_short = technical_analyzer.calculate_ema_talib(close, self.ema_short)
        ema_long = technical_analyzer.calculate_ema_talib(close, self.ema_long)
        ema_trend = technical_analyzer.calculate_ema_talib(close, self.ema_trend)
        
        trend_signals = 0
        total_signals = 0
        
        if not pd.isna(ema_short.iloc[-1]) and not pd.isna(ema_long.iloc[-1]):
            if ema_short.iloc[-1] > ema_long.iloc[-1]:
                trend_signals += 1
            total_signals += 1
        
        if not pd.isna(ema_long.iloc[-1]) and not pd.isna(ema_trend.iloc[-1]):
            if ema_long.iloc[-1] > ema_trend.iloc[-1]:
                trend_signals += 1
            total_signals += 1
        
        if not pd.isna(close.iloc[-1]) and not pd.isna(ema_trend.iloc[-1]):
            if close.iloc[-1] > ema_trend.iloc[-1]:
                trend_signals += 1
            total_signals += 1
        
        trend_strength = trend_signals / total_signals if total_signals > 0 else 0.5
        
        # 트렌드 방향 결정
        if trend_strength > 0.6:
            trend_direction = 'bullish'
        elif trend_strength < 0.4:
            trend_direction = 'bearish'
        else:
            trend_direction = 'neutral'
        
        return {
            'trend': trend_direction,
            'strength': trend_strength,
            'price_change': price_change,
            'volatility': volatility
        }
    
    def calculate_fibonacci_levels(self, data: pd.DataFrame) -> Dict:
        """피보나치 되돌림 레벨 계산"""
        if len(data) < 20:
            return {}
        
        # 최근 20개 캔들에서 고점과 저점 찾기
        recent_data = data.tail(20)
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        
        # 피보나치 레벨 계산
        fib_levels = {}
        for level in self.fibonacci_levels:
            fib_price = swing_low + (swing_high - swing_low) * level
            fib_levels[f'fib_{int(level*100)}'] = fib_price
        
        return {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'levels': fib_levels,
            'range': swing_high - swing_low
        }
    
    def detect_support_resistance(self, data: pd.DataFrame) -> Dict:
        """지지/저항선 탐지"""
        if len(data) < 50:
            return {'support': [], 'resistance': []}
        
        close = data['close']
        high = data['high']
        low = data['low']
        
        # 최근 50개 캔들에서 지지/저항선 찾기
        recent_data = data.tail(50)
        
        # 저점들 찾기 (지지선)
        support_levels = []
        for i in range(2, len(recent_data) - 2):
            if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i-2] and
                recent_data['low'].iloc[i] < recent_data['low'].iloc[i+2]):
                support_levels.append(recent_data['low'].iloc[i])
        
        # 고점들 찾기 (저항선)
        resistance_levels = []
        for i in range(2, len(recent_data) - 2):
            if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i-2] and
                recent_data['high'].iloc[i] > recent_data['high'].iloc[i+2]):
                resistance_levels.append(recent_data['high'].iloc[i])
        
        return {
            'support': support_levels,
            'resistance': resistance_levels
        }
    
    def analyze(self, data: pd.DataFrame) -> List[TradingSignal]:
        """스윙 트레이딩 분석"""
        signals = []
        
        if len(data) < 100:
            return signals
        
        # 기술적 지표 계산
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # EMA 계산
        from analysis.technical_indicators import TechnicalAnalyzer
        ti = TechnicalAnalyzer()
        ema_short = ti.calculate_ema_talib(close, self.ema_short)
        ema_long = ti.calculate_ema_talib(close, self.ema_long)
        ema_trend = ti.calculate_ema_talib(close, self.ema_trend)
        
        # RSI 계산
        rsi = ti.calculate_rsi(close, self.rsi_period)
        
        # 볼륨 분석
        volume_ma = volume.rolling(self.volume_ma_period).mean()
        
        # 현재 값들
        current_price = close.iloc[-1]
        current_ema_short = ema_short.iloc[-1]
        current_ema_long = ema_long.iloc[-1]
        current_ema_trend = ema_trend.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_volume = volume.iloc[-1]
        current_volume_ma = volume_ma.iloc[-1]
        
        # 트렌드 분석
        trend_info = self.identify_trend(data)
        fibonacci_levels = self.calculate_fibonacci_levels(data)
        support_resistance = self.detect_support_resistance(data)
        
        # 신호 생성 로직
        signal_strength = 0.0
        signal_confidence = 0.0
        signal_type = SignalType.HOLD
        reason_parts = []
        
        # 1. 트렌드 기반 신호 (조건 완화)
        if trend_info['trend'] in ['bullish', 'neutral'] and trend_info['strength'] > 0.3:
            # 상승 트렌드에서 매수 신호
            if (not pd.isna(current_ema_short) and not pd.isna(current_ema_long) and
                current_ema_short > current_ema_long and current_price > current_ema_short):
                signal_strength += 0.4
                signal_confidence += 0.3
                signal_type = SignalType.BUY
                reason_parts.append("상승 트렌드 + EMA 크로스")
        
        elif trend_info['trend'] in ['bearish', 'neutral'] and trend_info['strength'] > 0.3:
            # 하락 트렌드에서 매도 신호
            if (not pd.isna(current_ema_short) and not pd.isna(current_ema_long) and
                current_ema_short < current_ema_long and current_price < current_ema_short):
                signal_strength += 0.4
                signal_confidence += 0.3
                signal_type = SignalType.SELL
                reason_parts.append("하락 트렌드 + EMA 크로스")
        
        # 2. 피보나치 되돌림 신호
        if fibonacci_levels:
            swing_high = fibonacci_levels.get('swing_high', 0)
            swing_low = fibonacci_levels.get('swing_low', 0)
            fib_levels = fibonacci_levels.get('levels', {})
            
            # 피보나치 레벨 근처에서 신호 생성
            for level_name, level_price in fib_levels.items():
                if abs(current_price - level_price) / current_price < 0.02:  # 2% 이내
                    if trend_info['trend'] == 'bullish':
                        signal_strength += 0.3
                        signal_confidence += 0.2
                        if signal_type == SignalType.HOLD:
                            signal_type = SignalType.BUY
                        reason_parts.append(f"피보나치 {level_name} 지지")
                    elif trend_info['trend'] == 'bearish':
                        signal_strength += 0.3
                        signal_confidence += 0.2
                        if signal_type == SignalType.HOLD:
                            signal_type = SignalType.SELL
                        reason_parts.append(f"피보나치 {level_name} 저항")
        
        # 3. 지지/저항선 신호
        if support_resistance:
            support_levels = support_resistance.get('support', [])
            resistance_levels = support_resistance.get('resistance', [])
            
            # 지지선 근처에서 매수 신호
            for support in support_levels:
                if abs(current_price - support) / current_price < 0.03:  # 3% 이내
                    if trend_info['trend'] == 'bullish':
                        signal_strength += 0.2
                        signal_confidence += 0.2
                        if signal_type == SignalType.HOLD:
                            signal_type = SignalType.BUY
                        reason_parts.append("지지선 터치")
                    break
            
            # 저항선 근처에서 매도 신호
            for resistance in resistance_levels:
                if abs(current_price - resistance) / current_price < 0.03:  # 3% 이내
                    if trend_info['trend'] == 'bearish':
                        signal_strength += 0.2
                        signal_confidence += 0.2
                        if signal_type == SignalType.HOLD:
                            signal_type = SignalType.SELL
                        reason_parts.append("저항선 터치")
                    break
        
        # 4. RSI 확인
        if not pd.isna(current_rsi):
            if current_rsi < 40 and signal_type == SignalType.BUY:
                signal_confidence += 0.1
                reason_parts.append("RSI 매수 구간")
            elif current_rsi > 60 and signal_type == SignalType.SELL:
                signal_confidence += 0.1
                reason_parts.append("RSI 매도 구간")
            elif (current_rsi > 70 and signal_type == SignalType.BUY) or \
                 (current_rsi < 30 and signal_type == SignalType.SELL):
                signal_confidence *= 0.5  # RSI와 반대 신호 시 신뢰도 감소
        
        # 5. 볼륨 확인
        volume_ratio = current_volume / current_volume_ma if current_volume_ma > 0 else 1
        if volume_ratio < 1.0:  # 볼륨 부족
            signal_confidence *= 0.8
        
        # 추가 신호 조건 (더 간단한 조건)
        if signal_type == SignalType.HOLD:
            # 단순 EMA 크로스 신호
            if (not pd.isna(current_ema_short) and not pd.isna(current_ema_long) and
                current_ema_short > current_ema_long and current_price > current_ema_short):
                signal_type = SignalType.BUY
                signal_strength = 0.3
                signal_confidence = 0.2
                reason_parts.append("EMA 크로스 매수")
            elif (not pd.isna(current_ema_short) and not pd.isna(current_ema_long) and
                  current_ema_short < current_ema_long and current_price < current_ema_short):
                signal_type = SignalType.SELL
                signal_strength = 0.3
                signal_confidence = 0.2
                reason_parts.append("EMA 크로스 매도")
            # 더 간단한 조건: 가격이 EMA 위/아래에 있으면 신호 생성
            elif (not pd.isna(current_ema_short) and current_price > current_ema_short):
                signal_type = SignalType.BUY
                signal_strength = 0.2
                signal_confidence = 0.1
                reason_parts.append("가격 > EMA 매수")
            elif (not pd.isna(current_ema_short) and current_price < current_ema_short):
                signal_type = SignalType.SELL
                signal_strength = 0.2
                signal_confidence = 0.1
                reason_parts.append("가격 < EMA 매도")
        
        # 신호 생성 (조건 완화)
        if signal_type != SignalType.HOLD and signal_strength >= 0.2:
            # 포지션 크기 계산
            quantity = self.calculate_position_size(100000, current_price, current_price * 0.03)  # 3% 리스크
            
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
                    'ema_trend': current_ema_trend,
                    'rsi': current_rsi,
                    'volume_ratio': volume_ratio,
                    'trend_info': trend_info,
                    'fibonacci_levels': fibonacci_levels,
                    'support_resistance': support_resistance,
                    'strategy': 'swing_trading'
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
        return len(signals) > 0 and signals[0].strength > 0.6
    
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
        
        # 2. 트렌드 반전 시 청산
        if len(data) >= 20:
            trend_info = self.identify_trend(data)
            if position.get('side') == 'long' and trend_info['trend'] == 'bearish':
                return True
            elif position.get('side') == 'short' and trend_info['trend'] == 'bullish':
                return True
        
        # 3. 장기 보유 후 청산 (7일)
        if (datetime.now() - entry_time).days >= 7:
            return True
        
        return False
    
    def get_strategy_info(self) -> Dict:
        """전략 정보 반환"""
        return {
            'name': 'Swing Trading Strategy',
            'type': 'swing_trading',
            'description': '중기 트렌드를 활용한 수익 추구',
            'parameters': {
                'ema_short': self.ema_short,
                'ema_long': self.ema_long,
                'ema_trend': self.ema_trend,
                'fibonacci_levels': self.fibonacci_levels,
                'min_trend_strength': self.min_trend_strength
            },
            'performance': self.get_performance_metrics()
        }
