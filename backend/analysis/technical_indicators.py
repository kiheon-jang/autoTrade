"""
기술적 분석 지표 계산 엔진
"""
import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """신호 타입"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


@dataclass
class TechnicalSignal:
    """기술적 분석 신호"""
    signal_type: SignalType
    strength: float  # 0.0 ~ 1.0
    confidence: float  # 0.0 ~ 1.0
    indicator: str
    value: float
    timestamp: pd.Timestamp
    description: str


class TechnicalAnalyzer:
    """기술적 분석 엔진"""
    
    def __init__(self):
        self.indicators = {}
    
    def calculate_ma(self, data: pd.Series, period: int) -> pd.Series:
        """이동평균선 계산"""
        return data.rolling(window=period).mean()
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """지수이동평균선 계산"""
        return data.ewm(span=period).mean()
    
    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """단순이동평균선 계산"""
        result = talib.SMA(data.values, timeperiod=period)
        return pd.Series(result, index=data.index)
    
    def calculate_ema_talib(self, data: pd.Series, period: int) -> pd.Series:
        """지수이동평균선 계산 (TA-Lib)"""
        result = talib.EMA(data.values, timeperiod=period)
        return pd.Series(result, index=data.index)
    
    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        result = talib.RSI(data.values, timeperiod=period)
        return pd.Series(result, index=data.index)
    
    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD 계산"""
        macd, macd_signal, macd_hist = talib.MACD(data.values, fastperiod=fast, slowperiod=slow, signalperiod=signal)
        return {
            'macd': pd.Series(macd, index=data.index),
            'signal': pd.Series(macd_signal, index=data.index),
            'histogram': pd.Series(macd_hist, index=data.index)
        }
    
    def calculate_bollinger_bands(self, data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """볼린저 밴드 계산"""
        upper, middle, lower = talib.BBANDS(data.values, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        return {
            'upper': pd.Series(upper, index=data.index),
            'middle': pd.Series(middle, index=data.index),
            'lower': pd.Series(lower, index=data.index)
        }
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """스토캐스틱 계산"""
        k, d = talib.STOCH(high.values, low.values, close.values, 
                          fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
        return {
            'k': pd.Series(k, index=high.index),
            'd': pd.Series(d, index=high.index)
        }
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """ATR (Average True Range) 계산"""
        result = talib.ATR(high.values, low.values, close.values, timeperiod=period)
        return pd.Series(result, index=high.index)
    
    def calculate_cci(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """CCI (Commodity Channel Index) 계산"""
        result = talib.CCI(high.values, low.values, close.values, timeperiod=period)
        return pd.Series(result, index=high.index)
    
    def calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """OBV (On Balance Volume) 계산"""
        result = talib.OBV(close.values, volume.values)
        return pd.Series(result, index=close.index)
    
    def calculate_vwap(self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """VWAP (Volume Weighted Average Price) 계산"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    def calculate_fibonacci_retracement(self, high: float, low: float) -> Dict[str, float]:
        """피보나치 되돌림 계산"""
        diff = high - low
        return {
            '0%': high,
            '23.6%': high - diff * 0.236,
            '38.2%': high - diff * 0.382,
            '50%': high - diff * 0.5,
            '61.8%': high - diff * 0.618,
            '78.6%': high - diff * 0.786,
            '100%': low
        }
    
    def detect_support_resistance(self, data: pd.Series, window: int = 20, threshold: float = 0.02) -> Dict[str, List[float]]:
        """지지/저항선 탐지"""
        highs = data.rolling(window=window).max()
        lows = data.rolling(window=window).min()
        
        resistance_levels = []
        support_levels = []
        
        for i in range(window, len(data)):
            if data.iloc[i] == highs.iloc[i]:
                resistance_levels.append(data.iloc[i])
            if data.iloc[i] == lows.iloc[i]:
                support_levels.append(data.iloc[i])
        
        return {
            'resistance': resistance_levels,
            'support': support_levels
        }
    
    def calculate_volume_profile(self, price: pd.Series, volume: pd.Series, bins: int = 20) -> Dict[str, float]:
        """볼륨 프로파일 계산"""
        price_bins = pd.cut(price, bins=bins)
        volume_by_price = volume.groupby(price_bins).sum()
        
        return {
            'poc': volume_by_price.idxmax().mid,  # Point of Control
            'vah': volume_by_price.quantile(0.8),  # Value Area High
            'val': volume_by_price.quantile(0.2)   # Value Area Low
        }
    
    def generate_signals(self, data: pd.DataFrame) -> List[TechnicalSignal]:
        """종합 기술적 분석 신호 생성"""
        signals = []
        
        if len(data) < 50:  # 최소 데이터 요구량
            return signals
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # RSI 신호
        rsi = self.calculate_rsi(close)
        if not pd.isna(rsi.iloc[-1]):
            if rsi.iloc[-1] < 30:
                signals.append(TechnicalSignal(
                    signal_type=SignalType.BUY,
                    strength=0.8,
                    confidence=0.7,
                    indicator='RSI',
                    value=rsi.iloc[-1],
                    timestamp=close.index[-1],
                    description=f"RSI 과매도 구간 ({rsi.iloc[-1]:.2f})"
                ))
            elif rsi.iloc[-1] > 70:
                signals.append(TechnicalSignal(
                    signal_type=SignalType.SELL,
                    strength=0.8,
                    confidence=0.7,
                    indicator='RSI',
                    value=rsi.iloc[-1],
                    timestamp=close.index[-1],
                    description=f"RSI 과매수 구간 ({rsi.iloc[-1]:.2f})"
                ))
        
        # MACD 신호
        macd_data = self.calculate_macd(close)
        if not pd.isna(macd_data['macd'].iloc[-1]) and not pd.isna(macd_data['signal'].iloc[-1]):
            if macd_data['macd'].iloc[-1] > macd_data['signal'].iloc[-1] and macd_data['histogram'].iloc[-1] > 0:
                signals.append(TechnicalSignal(
                    signal_type=SignalType.BUY,
                    strength=0.6,
                    confidence=0.6,
                    indicator='MACD',
                    value=macd_data['histogram'].iloc[-1],
                    timestamp=close.index[-1],
                    description="MACD 골든크로스"
                ))
            elif macd_data['macd'].iloc[-1] < macd_data['signal'].iloc[-1] and macd_data['histogram'].iloc[-1] < 0:
                signals.append(TechnicalSignal(
                    signal_type=SignalType.SELL,
                    strength=0.6,
                    confidence=0.6,
                    indicator='MACD',
                    value=macd_data['histogram'].iloc[-1],
                    timestamp=close.index[-1],
                    description="MACD 데드크로스"
                ))
        
        # 볼린저 밴드 신호
        bb_data = self.calculate_bollinger_bands(close)
        if not pd.isna(bb_data['upper'].iloc[-1]) and not pd.isna(bb_data['lower'].iloc[-1]):
            current_price = close.iloc[-1]
            if current_price <= bb_data['lower'].iloc[-1]:
                signals.append(TechnicalSignal(
                    signal_type=SignalType.BUY,
                    strength=0.7,
                    confidence=0.6,
                    indicator='Bollinger Bands',
                    value=current_price,
                    timestamp=close.index[-1],
                    description="볼린저 밴드 하단 터치"
                ))
            elif current_price >= bb_data['upper'].iloc[-1]:
                signals.append(TechnicalSignal(
                    signal_type=SignalType.SELL,
                    strength=0.7,
                    confidence=0.6,
                    indicator='Bollinger Bands',
                    value=current_price,
                    timestamp=close.index[-1],
                    description="볼린저 밴드 상단 터치"
                ))
        
        # 이동평균선 신호
        ema_8 = self.calculate_ema(close, 8)
        ema_21 = self.calculate_ema(close, 21)
        ema_50 = self.calculate_ema(close, 50)
        
        if not pd.isna(ema_8.iloc[-1]) and not pd.isna(ema_21.iloc[-1]):
            if ema_8.iloc[-1] > ema_21.iloc[-1] and ema_8.iloc[-2] <= ema_21.iloc[-2]:
                signals.append(TechnicalSignal(
                    signal_type=SignalType.BUY,
                    strength=0.8,
                    confidence=0.7,
                    indicator='EMA Crossover',
                    value=ema_8.iloc[-1],
                    timestamp=close.index[-1],
                    description="EMA 8이 EMA 21을 상향 돌파"
                ))
            elif ema_8.iloc[-1] < ema_21.iloc[-1] and ema_8.iloc[-2] >= ema_21.iloc[-2]:
                signals.append(TechnicalSignal(
                    signal_type=SignalType.SELL,
                    strength=0.8,
                    confidence=0.7,
                    indicator='EMA Crossover',
                    value=ema_8.iloc[-1],
                    timestamp=close.index[-1],
                    description="EMA 8이 EMA 21을 하향 돌파"
                ))
        
        return signals
    
    def calculate_all_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """모든 기술적 지표 계산"""
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        indicators = {}
        
        # 이동평균선
        indicators['sma_5'] = self.calculate_sma(close, 5)
        indicators['sma_10'] = self.calculate_sma(close, 10)
        indicators['sma_20'] = self.calculate_sma(close, 20)
        indicators['sma_50'] = self.calculate_sma(close, 50)
        indicators['sma_100'] = self.calculate_sma(close, 100)
        indicators['sma_200'] = self.calculate_sma(close, 200)
        
        indicators['ema_8'] = self.calculate_ema_talib(close, 8)
        indicators['ema_13'] = self.calculate_ema_talib(close, 13)
        indicators['ema_21'] = self.calculate_ema_talib(close, 21)
        indicators['ema_50'] = self.calculate_ema_talib(close, 50)
        indicators['ema_200'] = self.calculate_ema_talib(close, 200)
        
        # 오실레이터
        indicators['rsi_14'] = self.calculate_rsi(close, 14)
        
        macd_data = self.calculate_macd(close)
        indicators['macd'] = macd_data['macd']
        indicators['macd_signal'] = macd_data['signal']
        indicators['macd_histogram'] = macd_data['histogram']
        
        stoch_data = self.calculate_stochastic(high, low, close)
        indicators['stochastic_k'] = stoch_data['k']
        indicators['stochastic_d'] = stoch_data['d']
        
        indicators['cci_20'] = self.calculate_cci(high, low, close, 20)
        
        # 변동성 지표
        indicators['atr_14'] = self.calculate_atr(high, low, close, 14)
        
        bb_data = self.calculate_bollinger_bands(close)
        indicators['bb_upper'] = bb_data['upper']
        indicators['bb_middle'] = bb_data['middle']
        indicators['bb_lower'] = bb_data['lower']
        
        # 볼륨 지표
        indicators['obv'] = self.calculate_obv(close, volume)
        indicators['vwap'] = self.calculate_vwap(high, low, close, volume)
        
        return indicators


# 싱글톤 인스턴스
technical_analyzer = TechnicalAnalyzer()
