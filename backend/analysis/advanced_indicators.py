"""
고급 기술적 지표 계산 엔진
"""
import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class MarketRegime(Enum):
    """시장 상황 분류"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class MarketCondition:
    """시장 상황 정보"""
    regime: MarketRegime
    strength: float  # 0-1, 강도
    volatility: float
    trend_direction: str  # 'up', 'down', 'sideways'
    confidence: float  # 0-1, 신뢰도


class AdvancedIndicators:
    """고급 기술적 지표 계산기"""
    
    def __init__(self):
        self.lookback_periods = {
            'short': 20,
            'medium': 50,
            'long': 200
        }
    
    def calculate_ichimoku_cloud(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                                tenkan: int = 9, kijun: int = 26, senkou_b: int = 52) -> Dict[str, pd.Series]:
        """일목균형표 계산"""
        # 전환선 (Tenkan-sen)
        tenkan_high = high.rolling(tenkan).max()
        tenkan_low = low.rolling(tenkan).min()
        tenkan_sen = (tenkan_high + tenkan_low) / 2
        
        # 기준선 (Kijun-sen)
        kijun_high = high.rolling(kijun).max()
        kijun_low = low.rolling(kijun).min()
        kijun_sen = (kijun_high + kijun_low) / 2
        
        # 선행스팬 A (Senkou Span A)
        senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(kijun)
        
        # 선행스팬 B (Senkou Span B)
        senkou_high = high.rolling(senkou_b).max()
        senkou_low = low.rolling(senkou_b).min()
        senkou_span_b = ((senkou_high + senkou_low) / 2).shift(kijun)
        
        # 후행스팬 (Chikou Span)
        chikou_span = close.shift(-kijun)
        
        return {
            'tenkan_sen': tenkan_sen,
            'kijun_sen': kijun_sen,
            'senkou_span_a': senkou_span_a,
            'senkou_span_b': senkou_span_b,
            'chikou_span': chikou_span
        }
    
    def calculate_williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Williams %R 계산"""
        highest_high = high.rolling(period).max()
        lowest_low = low.rolling(period).min()
        williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
        return williams_r
    
    def calculate_money_flow_index(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                                  volume: pd.Series, period: int = 14) -> pd.Series:
        """Money Flow Index 계산"""
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(period).sum()
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(period).sum()
        
        mfi = 100 - (100 / (1 + positive_flow / negative_flow))
        return mfi
    
    def calculate_aroon(self, high: pd.Series, low: pd.Series, period: int = 25) -> Dict[str, pd.Series]:
        """Aroon 지표 계산"""
        aroon_up = ((period - high.rolling(period).apply(lambda x: period - 1 - x.argmax())) / period) * 100
        aroon_down = ((period - low.rolling(period).apply(lambda x: period - 1 - x.argmin())) / period) * 100
        aroon_oscillator = aroon_up - aroon_down
        
        return {
            'aroon_up': aroon_up,
            'aroon_down': aroon_down,
            'aroon_oscillator': aroon_oscillator
        }
    
    def calculate_parabolic_sar(self, high: pd.Series, low: pd.Series, 
                               acceleration: float = 0.02, maximum: float = 0.2) -> pd.Series:
        """Parabolic SAR 계산"""
        psar = talib.SAR(high.values, low.values, acceleration=acceleration, maximum=maximum)
        return pd.Series(psar, index=high.index)
    
    def calculate_keltner_channels(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                                   period: int = 20, multiplier: float = 2.0) -> Dict[str, pd.Series]:
        """Keltner Channels 계산"""
        typical_price = (high + low + close) / 3
        middle = typical_price.rolling(period).mean()
        atr = talib.ATR(high.values, low.values, close.values, timeperiod=period)
        atr_series = pd.Series(atr, index=high.index)
        
        upper = middle + (multiplier * atr_series)
        lower = middle - (multiplier * atr_series)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    def calculate_donchian_channels(self, high: pd.Series, low: pd.Series, period: int = 20) -> Dict[str, pd.Series]:
        """Donchian Channels 계산"""
        upper = high.rolling(period).max()
        lower = low.rolling(period).min()
        middle = (upper + lower) / 2
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    def calculate_volume_profile(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                               volume: pd.Series, bins: int = 20) -> Dict[str, float]:
        """Volume Profile 계산"""
        price_range = high.max() - low.min()
        bin_size = price_range / bins
        
        # 가격 구간별 거래량 집계
        volume_by_price = {}
        for i in range(len(close)):
            price_level = int((close.iloc[i] - low.min()) / bin_size)
            if price_level not in volume_by_price:
                volume_by_price[price_level] = 0
            volume_by_price[price_level] += volume.iloc[i]
        
        # POC (Point of Control) - 가장 많은 거래량이 발생한 가격대
        poc_level = max(volume_by_price, key=volume_by_price.get)
        poc_price = low.min() + (poc_level * bin_size)
        
        # Value Area (70% 거래량이 발생한 구간)
        total_volume = sum(volume_by_price.values())
        sorted_volumes = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        
        cumulative_volume = 0
        value_area_levels = []
        for level, vol in sorted_volumes:
            cumulative_volume += vol
            value_area_levels.append(level)
            if cumulative_volume >= total_volume * 0.7:
                break
        
        value_area_high = low.min() + (max(value_area_levels) * bin_size)
        value_area_low = low.min() + (min(value_area_levels) * bin_size)
        
        return {
            'poc': poc_price,
            'value_area_high': value_area_high,
            'value_area_low': value_area_low,
            'total_volume': total_volume
        }
    
    def calculate_market_regime(self, data: pd.DataFrame) -> MarketCondition:
        """시장 상황 분석"""
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 트렌드 분석
        ema_short = close.ewm(span=20).mean()
        ema_long = close.ewm(span=50).mean()
        
        # 변동성 분석
        returns = close.pct_change()
        volatility = returns.rolling(20).std()
        current_volatility = volatility.iloc[-1]
        
        # 거래량 분석
        volume_ma = volume.rolling(20).mean()
        volume_ratio = volume.iloc[-1] / volume_ma.iloc[-1]
        
        # 트렌드 방향 결정
        if ema_short.iloc[-1] > ema_long.iloc[-1] * 1.02:
            trend_direction = 'up'
            trend_strength = min(1.0, (ema_short.iloc[-1] - ema_long.iloc[-1]) / ema_long.iloc[-1])
        elif ema_short.iloc[-1] < ema_long.iloc[-1] * 0.98:
            trend_direction = 'down'
            trend_strength = min(1.0, (ema_long.iloc[-1] - ema_short.iloc[-1]) / ema_long.iloc[-1])
        else:
            trend_direction = 'sideways'
            trend_strength = 0.0
        
        # 시장 상황 분류
        if trend_strength > 0.3:
            if trend_direction == 'up':
                regime = MarketRegime.TRENDING_UP
            else:
                regime = MarketRegime.TRENDING_DOWN
        elif current_volatility > volatility.quantile(0.8):
            regime = MarketRegime.VOLATILE
        elif current_volatility < volatility.quantile(0.2):
            regime = MarketRegime.LOW_VOLATILITY
        else:
            regime = MarketRegime.RANGING
        
        # 신뢰도 계산
        confidence = min(1.0, trend_strength + (1 - abs(volume_ratio - 1)))
        
        return MarketCondition(
            regime=regime,
            strength=trend_strength,
            volatility=current_volatility,
            trend_direction=trend_direction,
            confidence=confidence
        )
    
    def calculate_support_resistance_levels(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                                          lookback: int = 20, min_touches: int = 2) -> Dict[str, List[float]]:
        """지지/저항선 계산 (고도화)"""
        # 피벗 포인트 찾기
        highs = []
        lows = []
        
        for i in range(lookback, len(high) - lookback):
            # 고점 찾기
            if all(high.iloc[i] >= high.iloc[i-lookback:i]) and all(high.iloc[i] >= high.iloc[i+1:i+lookback+1]):
                highs.append(high.iloc[i])
            
            # 저점 찾기
            if all(low.iloc[i] <= low.iloc[i-lookback:i]) and all(low.iloc[i] <= low.iloc[i+1:i+lookback+1]):
                lows.append(low.iloc[i])
        
        # 클러스터링으로 유사한 레벨들 그룹화
        def cluster_levels(levels, tolerance=0.01):
            if not levels:
                return []
            
            levels = sorted(levels)
            clusters = []
            current_cluster = [levels[0]]
            
            for level in levels[1:]:
                if level <= current_cluster[-1] * (1 + tolerance):
                    current_cluster.append(level)
                else:
                    if len(current_cluster) >= min_touches:
                        clusters.append(sum(current_cluster) / len(current_cluster))
                    current_cluster = [level]
            
            if len(current_cluster) >= min_touches:
                clusters.append(sum(current_cluster) / len(current_cluster))
            
            return clusters
        
        resistance_levels = cluster_levels(highs)
        support_levels = cluster_levels(lows)
        
        return {
            'resistance': resistance_levels,
            'support': support_levels
        }
    
    def calculate_fibonacci_retracement_advanced(self, high: pd.Series, low: pd.Series, 
                                                lookback: int = 50) -> Dict[str, float]:
        """고급 피보나치 되돌림 계산"""
        recent_high = high.rolling(lookback).max().iloc[-1]
        recent_low = low.rolling(lookback).min().iloc[-1]
        
        price_range = recent_high - recent_low
        
        # 확장된 피보나치 레벨
        fib_levels = {
            'fib_0': recent_high,
            'fib_23.6': recent_high - (price_range * 0.236),
            'fib_38.2': recent_high - (price_range * 0.382),
            'fib_50': recent_high - (price_range * 0.5),
            'fib_61.8': recent_high - (price_range * 0.618),
            'fib_78.6': recent_high - (price_range * 0.786),
            'fib_100': recent_low,
            'fib_127.2': recent_low - (price_range * 0.272),
            'fib_161.8': recent_low - (price_range * 0.618),
            'fib_200': recent_low - (price_range * 1.0)
        }
        
        return fib_levels
