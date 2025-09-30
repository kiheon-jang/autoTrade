"""
차트 패턴 인식 엔진
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import talib


class PatternType(Enum):
    """패턴 타입"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class PatternSignal:
    """패턴 신호"""
    pattern_name: str
    pattern_type: PatternType
    confidence: float  # 0.0 ~ 1.0
    strength: float   # 0.0 ~ 1.0
    start_index: int
    end_index: int
    description: str


class PatternRecognizer:
    """차트 패턴 인식 엔진"""
    
    def __init__(self):
        self.patterns = {}
    
    def detect_doji(self, open_price: pd.Series, close: pd.Series, 
                   high: pd.Series, low: pd.Series, threshold: float = 0.1) -> List[PatternSignal]:
        """도지 패턴 탐지"""
        signals = []
        
        for i in range(len(open_price)):
            body_size = abs(close.iloc[i] - open_price.iloc[i])
            total_range = high.iloc[i] - low.iloc[i]
            
            if total_range > 0 and body_size / total_range < threshold:
                signals.append(PatternSignal(
                    pattern_name="Doji",
                    pattern_type=PatternType.NEUTRAL,
                    confidence=0.8,
                    strength=0.6,
                    start_index=i,
                    end_index=i,
                    description="도지 패턴 - 시장 불확실성"
                ))
        
        return signals
    
    def detect_hammer(self, open_price: pd.Series, close: pd.Series, 
                     high: pd.Series, low: pd.Series) -> List[PatternSignal]:
        """해머 패턴 탐지"""
        signals = []
        
        for i in range(len(open_price)):
            body_size = abs(close.iloc[i] - open_price.iloc[i])
            total_range = high.iloc[i] - low.iloc[i]
            upper_shadow = high.iloc[i] - max(open_price.iloc[i], close.iloc[i])
            lower_shadow = min(open_price.iloc[i], close.iloc[i]) - low.iloc[i]
            
            if (total_range > 0 and 
                body_size / total_range < 0.3 and 
                lower_shadow > body_size * 2 and 
                upper_shadow < body_size):
                
                pattern_type = PatternType.BULLISH if close.iloc[i] > open_price.iloc[i] else PatternType.BEARISH
                
                signals.append(PatternSignal(
                    pattern_name="Hammer",
                    pattern_type=pattern_type,
                    confidence=0.7,
                    strength=0.6,
                    start_index=i,
                    end_index=i,
                    description="해머 패턴 - 반전 신호"
                ))
        
        return signals
    
    def detect_engulfing(self, open_price: pd.Series, close: pd.Series, 
                        high: pd.Series, low: pd.Series) -> List[PatternSignal]:
        """엔걸핑 패턴 탐지"""
        signals = []
        
        for i in range(1, len(open_price)):
            prev_open = open_price.iloc[i-1]
            prev_close = close.iloc[i-1]
            curr_open = open_price.iloc[i]
            curr_close = close.iloc[i]
            
            # 강세 엔걸핑
            if (prev_close < prev_open and  # 이전 캔들이 음봉
                curr_close > curr_open and  # 현재 캔들이 양봉
                curr_open < prev_close and  # 현재 캔들 시가가 이전 캔들 종가보다 낮음
                curr_close > prev_open):    # 현재 캔들 종가가 이전 캔들 시가보다 높음
                
                signals.append(PatternSignal(
                    pattern_name="Bullish Engulfing",
                    pattern_type=PatternType.BULLISH,
                    confidence=0.8,
                    strength=0.7,
                    start_index=i-1,
                    end_index=i,
                    description="강세 엔걸핑 패턴"
                ))
            
            # 약세 엔걸핑
            elif (prev_close > prev_open and  # 이전 캔들이 양봉
                  curr_close < curr_open and  # 현재 캔들이 음봉
                  curr_open > prev_close and  # 현재 캔들 시가가 이전 캔들 종가보다 높음
                  curr_close < prev_open):    # 현재 캔들 종가가 이전 캔들 시가보다 낮음
                
                signals.append(PatternSignal(
                    pattern_name="Bearish Engulfing",
                    pattern_type=PatternType.BEARISH,
                    confidence=0.8,
                    strength=0.7,
                    start_index=i-1,
                    end_index=i,
                    description="약세 엔걸핑 패턴"
                ))
        
        return signals
    
    def detect_three_white_soldiers(self, open_price: pd.Series, close: pd.Series, 
                                   high: pd.Series, low: pd.Series) -> List[PatternSignal]:
        """삼백병 패턴 탐지"""
        signals = []
        
        for i in range(2, len(open_price)):
            # 연속 3개 양봉
            if (close.iloc[i-2] > open_price.iloc[i-2] and
                close.iloc[i-1] > open_price.iloc[i-1] and
                close.iloc[i] > open_price.iloc[i]):
                
                # 각 캔들이 이전 캔들보다 높은 고가
                if (high.iloc[i-1] > high.iloc[i-2] and
                    high.iloc[i] > high.iloc[i-1]):
                    
                    signals.append(PatternSignal(
                        pattern_name="Three White Soldiers",
                        pattern_type=PatternType.BULLISH,
                        confidence=0.9,
                        strength=0.8,
                        start_index=i-2,
                        end_index=i,
                        description="삼백병 패턴 - 강한 상승 신호"
                    ))
        
        return signals
    
    def detect_three_black_crows(self, open_price: pd.Series, close: pd.Series, 
                                high: pd.Series, low: pd.Series) -> List[PatternSignal]:
        """삼흉조 패턴 탐지"""
        signals = []
        
        for i in range(2, len(open_price)):
            # 연속 3개 음봉
            if (close.iloc[i-2] < open_price.iloc[i-2] and
                close.iloc[i-1] < open_price.iloc[i-1] and
                close.iloc[i] < open_price.iloc[i]):
                
                # 각 캔들이 이전 캔들보다 낮은 저가
                if (low.iloc[i-1] < low.iloc[i-2] and
                    low.iloc[i] < low.iloc[i-1]):
                    
                    signals.append(PatternSignal(
                        pattern_name="Three Black Crows",
                        pattern_type=PatternType.BEARISH,
                        confidence=0.9,
                        strength=0.8,
                        start_index=i-2,
                        end_index=i,
                        description="삼흉조 패턴 - 강한 하락 신호"
                    ))
        
        return signals
    
    def detect_head_and_shoulders(self, high: pd.Series, low: pd.Series, 
                                 window: int = 20) -> List[PatternSignal]:
        """헤드 앤 숄더 패턴 탐지"""
        signals = []
        
        for i in range(window, len(high) - window):
            # 최근 window 기간에서 최고점 찾기
            recent_highs = high.iloc[i-window:i+window]
            max_idx = recent_highs.idxmax()
            max_value = recent_highs.max()
            
            # 좌우 어깨 확인
            left_shoulder = high.iloc[i-window:max_idx].max()
            right_shoulder = high.iloc[max_idx:i+window].max()
            
            # 헤드 앤 숄더 패턴 조건
            if (left_shoulder > 0 and right_shoulder > 0 and
                abs(left_shoulder - right_shoulder) / max(left_shoulder, right_shoulder) < 0.05 and
                max_value > left_shoulder * 1.02 and
                max_value > right_shoulder * 1.02):
                
                signals.append(PatternSignal(
                    pattern_name="Head and Shoulders",
                    pattern_type=PatternType.BEARISH,
                    confidence=0.8,
                    strength=0.7,
                    start_index=i-window,
                    end_index=i+window,
                    description="헤드 앤 숄더 패턴 - 하락 반전 신호"
                ))
        
        return signals
    
    def detect_double_top(self, high: pd.Series, low: pd.Series, 
                         window: int = 20, tolerance: float = 0.02) -> List[PatternSignal]:
        """더블 탑 패턴 탐지"""
        signals = []
        
        for i in range(window, len(high) - window):
            # 첫 번째 고점
            first_peak = high.iloc[i-window:i].max()
            first_peak_idx = high.iloc[i-window:i].idxmax()
            
            # 두 번째 고점
            second_peak = high.iloc[i:i+window].max()
            second_peak_idx = high.iloc[i:i+window].idxmax()
            
            # 더블 탑 패턴 조건
            if (abs(first_peak - second_peak) / max(first_peak, second_peak) < tolerance and
                first_peak > high.iloc[i-window:i].mean() * 1.05 and
                second_peak > high.iloc[i:i+window].mean() * 1.05):
                
                signals.append(PatternSignal(
                    pattern_name="Double Top",
                    pattern_type=PatternType.BEARISH,
                    confidence=0.7,
                    strength=0.6,
                    start_index=first_peak_idx,
                    end_index=second_peak_idx,
                    description="더블 탑 패턴 - 하락 신호"
                ))
        
        return signals
    
    def detect_double_bottom(self, high: pd.Series, low: pd.Series, 
                           window: int = 20, tolerance: float = 0.02) -> List[PatternSignal]:
        """더블 바텀 패턴 탐지"""
        signals = []
        
        for i in range(window, len(low) - window):
            # 첫 번째 저점
            first_trough = low.iloc[i-window:i].min()
            first_trough_idx = low.iloc[i-window:i].idxmin()
            
            # 두 번째 저점
            second_trough = low.iloc[i:i+window].min()
            second_trough_idx = low.iloc[i:i+window].idxmin()
            
            # 더블 바텀 패턴 조건
            if (abs(first_trough - second_trough) / max(first_trough, second_trough) < tolerance and
                first_trough < low.iloc[i-window:i].mean() * 0.95 and
                second_trough < low.iloc[i:i+window].mean() * 0.95):
                
                signals.append(PatternSignal(
                    pattern_name="Double Bottom",
                    pattern_type=PatternType.BULLISH,
                    confidence=0.7,
                    strength=0.6,
                    start_index=first_trough_idx,
                    end_index=second_trough_idx,
                    description="더블 바텀 패턴 - 상승 신호"
                ))
        
        return signals
    
    def detect_triangle_pattern(self, high: pd.Series, low: pd.Series, 
                               window: int = 30) -> List[PatternSignal]:
        """삼각형 패턴 탐지"""
        signals = []
        
        for i in range(window, len(high)):
            recent_highs = high.iloc[i-window:i]
            recent_lows = low.iloc[i-window:i]
            
            # 상승 삼각형 (저점은 상승, 고점은 횡보)
            if (len(recent_lows) >= 3 and len(recent_highs) >= 3):
                low_trend = np.polyfit(range(len(recent_lows)), recent_lows, 1)[0]
                high_trend = np.polyfit(range(len(recent_highs)), recent_highs, 1)[0]
                
                if low_trend > 0 and abs(high_trend) < 0.001:  # 상승 삼각형
                    signals.append(PatternSignal(
                        pattern_name="Ascending Triangle",
                        pattern_type=PatternType.BULLISH,
                        confidence=0.6,
                        strength=0.5,
                        start_index=i-window,
                        end_index=i,
                        description="상승 삼각형 패턴"
                    ))
                
                elif high_trend < 0 and abs(low_trend) < 0.001:  # 하락 삼각형
                    signals.append(PatternSignal(
                        pattern_name="Descending Triangle",
                        pattern_type=PatternType.BEARISH,
                        confidence=0.6,
                        strength=0.5,
                        start_index=i-window,
                        end_index=i,
                        description="하락 삼각형 패턴"
                    ))
        
        return signals
    
    def detect_all_patterns(self, data: pd.DataFrame) -> List[PatternSignal]:
        """모든 패턴 탐지"""
        all_signals = []
        
        open_price = data['open']
        close = data['close']
        high = data['high']
        low = data['low']
        
        # 개별 패턴 탐지
        all_signals.extend(self.detect_doji(open_price, close, high, low))
        all_signals.extend(self.detect_hammer(open_price, close, high, low))
        all_signals.extend(self.detect_engulfing(open_price, close, high, low))
        all_signals.extend(self.detect_three_white_soldiers(open_price, close, high, low))
        all_signals.extend(self.detect_three_black_crows(open_price, close, high, low))
        all_signals.extend(self.detect_head_and_shoulders(high, low))
        all_signals.extend(self.detect_double_top(high, low))
        all_signals.extend(self.detect_double_bottom(high, low))
        all_signals.extend(self.detect_triangle_pattern(high, low))
        
        return all_signals


# 싱글톤 인스턴스
pattern_recognizer = PatternRecognizer()
