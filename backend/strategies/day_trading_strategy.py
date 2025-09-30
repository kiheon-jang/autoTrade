"""
데이트레이딩 전략 구현 (Bull Flag, Gap Trading, Pivot Point)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from strategies.base_strategy import BaseStrategy, StrategyConfig, StrategyType, SignalType, TradingSignal
from analysis.technical_indicators import technical_analyzer


class DayTradingStrategy(BaseStrategy):
    """데이트레이딩 전략 - 일중 거래를 통한 중기 수익 추구"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.ema_short = config.parameters.get('ema_short', 13)
        self.ema_long = config.parameters.get('ema_long', 50)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.bb_period = config.parameters.get('bb_period', 20)
        self.bb_std = config.parameters.get('bb_std', 2.0)
        self.volume_ma_period = config.parameters.get('volume_ma_period', 20)
        self.gap_threshold = config.parameters.get('gap_threshold', 0.02)  # 2%
        self.flag_retracement = config.parameters.get('flag_retracement', 0.382)  # 38.2%
        self.pivot_lookback = config.parameters.get('pivot_lookback', 5)
    
    def detect_gap(self, data: pd.DataFrame) -> Dict:
        """갭 탐지"""
        if len(data) < 2:
            return {'has_gap': False}
        
        prev_close = data['close'].iloc[-2]
        current_open = data['open'].iloc[-1]
        gap_pct = (current_open - prev_close) / prev_close
        
        return {
            'has_gap': abs(gap_pct) > self.gap_threshold,
            'gap_pct': gap_pct,
            'gap_type': 'up' if gap_pct > 0 else 'down',
            'prev_close': prev_close,
            'current_open': current_open
        }
    
    def detect_bull_flag(self, data: pd.DataFrame) -> Dict:
        """불 플래그 패턴 탐지"""
        if len(data) < 20:
            return {'has_flag': False}
        
        # 최근 20개 캔들에서 고점과 저점 찾기
        recent_data = data.tail(20)
        high_point = recent_data['high'].max()
        low_point = recent_data['low'].min()
        
        # 플래그 폴 (상승 후 하락)
        flag_pole_start = recent_data['low'].idxmin()
        flag_pole_end = recent_data['high'].idxmax()
        
        if flag_pole_start >= flag_pole_end:
            return {'has_flag': False}
        
        # 플래그 폴 높이
        flag_pole_height = high_point - low_point
        
        # 플래그 리트레이스먼트 확인
        current_price = data['close'].iloc[-1]
        retracement_pct = (high_point - current_price) / flag_pole_height
        
        return {
            'has_flag': retracement_pct >= self.flag_retracement and retracement_pct <= 0.618,
            'flag_pole_height': flag_pole_height,
            'retracement_pct': retracement_pct,
            'high_point': high_point,
            'low_point': low_point
        }
    
    def calculate_pivot_points(self, data: pd.DataFrame) -> Dict:
        """피벗 포인트 계산"""
        if len(data) < self.pivot_lookback:
            return {}
        
        recent_data = data.tail(self.pivot_lookback)
        high = recent_data['high'].max()
        low = recent_data['low'].min()
        close = data['close'].iloc[-1]
        
        # 피벗 포인트 계산
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        
        return {
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            's1': s1,
            's2': s2,
            'high': high,
            'low': low,
            'close': close
        }
    
    def analyze(self, data: pd.DataFrame) -> List[TradingSignal]:
        """데이트레이딩 분석"""
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
        bb_data = technical_analyzer.calculate_bollinger_bands(close, self.bb_period, self.bb_std)
        
        # 볼륨 분석
        volume_ma = volume.rolling(self.volume_ma_period).mean()
        
        # 현재 값들
        current_price = close.iloc[-1]
        current_ema_short = ema_short.iloc[-1]
        current_ema_long = ema_long.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_bb_upper = bb_data['upper'].iloc[-1]
        current_bb_lower = bb_data['lower'].iloc[-1]
        current_volume = volume.iloc[-1]
        current_volume_ma = volume_ma.iloc[-1]
        
        # 패턴 탐지
        gap_info = self.detect_gap(data)
        flag_info = self.detect_bull_flag(data)
        pivot_points = self.calculate_pivot_points(data)
        
        # 신호 생성 로직
        signal_strength = 0.0
        signal_confidence = 0.0
        signal_type = SignalType.HOLD
        reason_parts = []
        
        # 1. 갭 거래 신호
        if gap_info.get('has_gap', False):
            gap_pct = gap_info.get('gap_pct', 0)
            if gap_pct > 0:  # 상승 갭
                signal_strength += 0.4
                signal_confidence += 0.3
                signal_type = SignalType.BUY
                reason_parts.append(f"상승갭 ({gap_pct:.2%})")
            else:  # 하락 갭
                signal_strength += 0.4
                signal_confidence += 0.3
                signal_type = SignalType.SELL
                reason_parts.append(f"하락갭 ({gap_pct:.2%})")
        
        # 2. 불 플래그 패턴
        if flag_info.get('has_flag', False):
            signal_strength += 0.3
            signal_confidence += 0.4
            if signal_type == SignalType.HOLD:
                signal_type = SignalType.BUY
            reason_parts.append("불 플래그 패턴")
        
        # 3. 피벗 포인트 신호
        if pivot_points:
            pivot = pivot_points.get('pivot', 0)
            r1 = pivot_points.get('r1', 0)
            s1 = pivot_points.get('s1', 0)
            
            if current_price > r1:
                signal_strength += 0.2
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.BUY
                reason_parts.append("피벗 R1 돌파")
            elif current_price < s1:
                signal_strength += 0.2
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.SELL
                reason_parts.append("피벗 S1 이탈")
        
        # 4. EMA 트렌드 확인
        if not pd.isna(current_ema_short) and not pd.isna(current_ema_long):
            if current_ema_short > current_ema_long and current_price > current_ema_short:
                signal_strength += 0.2
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.BUY
                reason_parts.append("EMA 상승 트렌드")
            elif current_ema_short < current_ema_long and current_price < current_ema_short:
                signal_strength += 0.2
                signal_confidence += 0.2
                if signal_type == SignalType.HOLD:
                    signal_type = SignalType.SELL
                reason_parts.append("EMA 하락 트렌드")
        
        # 5. RSI 확인
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
        
        # 6. 볼륨 확인
        volume_ratio = current_volume / current_volume_ma if current_volume_ma > 0 else 1
        if volume_ratio < 1.2:  # 볼륨 부족
            signal_confidence *= 0.7
        
        # 신호 생성
        if signal_type != SignalType.HOLD and signal_strength > 0.4:
            # 포지션 크기 계산
            quantity = self.calculate_position_size(100000, current_price, current_price * 0.02)  # 2% 리스크
            
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
                    'gap_info': gap_info,
                    'flag_info': flag_info,
                    'pivot_points': pivot_points,
                    'strategy': 'day_trading'
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
        return len(signals) > 0 and signals[0].strength > 0.6
    
    def should_exit_position(self, data: pd.DataFrame, position: Dict) -> bool:
        """포지션 청산 조건"""
        if not position:
            return False
        
        current_price = data['close'].iloc[-1]
        entry_price = position.get('entry_price', 0)
        entry_time = position.get('entry_time', datetime.now())
        
        # 1. 일중 거래 종료 (장 마감)
        current_hour = datetime.now().hour
        if current_hour >= 15:  # 오후 3시 이후 청산
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
        
        # 3. 트렌드 반전 시 청산
        if len(data) >= 10:
            ema_short = technical_analyzer.calculate_ema_talib(data['close'], self.ema_short)
            ema_long = technical_analyzer.calculate_ema_talib(data['close'], self.ema_long)
            
            if not pd.isna(ema_short.iloc[-1]) and not pd.isna(ema_long.iloc[-1]):
                if position.get('side') == 'long' and ema_short.iloc[-1] < ema_long.iloc[-1]:
                    return True
                elif position.get('side') == 'short' and ema_short.iloc[-1] > ema_long.iloc[-1]:
                    return True
        
        return False
    
    def get_strategy_info(self) -> Dict:
        """전략 정보 반환"""
        return {
            'name': 'Day Trading Strategy',
            'type': 'day_trading',
            'description': '일중 거래를 통한 중기 수익 추구',
            'parameters': {
                'ema_short': self.ema_short,
                'ema_long': self.ema_long,
                'gap_threshold': self.gap_threshold,
                'flag_retracement': self.flag_retracement,
                'pivot_lookback': self.pivot_lookback
            },
            'performance': self.get_performance_metrics()
        }
