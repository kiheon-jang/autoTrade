"""
멀티 타임프레임 분석 엔진
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from analysis.technical_indicators import TechnicalAnalyzer, TechnicalSignal, SignalType
from analysis.pattern_recognition import PatternRecognizer, PatternSignal


class TimeframeType(Enum):
    """타임프레임 타입"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


@dataclass
class MultiTimeframeSignal:
    """멀티 타임프레임 신호"""
    primary_signal: TechnicalSignal
    supporting_signals: List[TechnicalSignal]
    conflicting_signals: List[TechnicalSignal]
    overall_strength: float
    overall_confidence: float
    timeframe_alignment: bool
    trend_direction: str  # "bullish", "bearish", "neutral"


class MultiTimeframeAnalyzer:
    """멀티 타임프레임 분석 엔진"""
    
    def __init__(self):
        self.technical_analyzer = TechnicalAnalyzer()
        self.pattern_recognizer = PatternRecognizer()
        self.timeframes = [
            TimeframeType.M15,
            TimeframeType.M30,
            TimeframeType.H1,
            TimeframeType.H4,
            TimeframeType.D1
        ]
    
    def resample_data(self, data: pd.DataFrame, timeframe: TimeframeType) -> pd.DataFrame:
        """데이터 리샘플링"""
        if timeframe == TimeframeType.M1:
            return data
        elif timeframe == TimeframeType.M5:
            return data.resample('5T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        elif timeframe == TimeframeType.M15:
            return data.resample('15T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        elif timeframe == TimeframeType.M30:
            return data.resample('30T').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        elif timeframe == TimeframeType.H1:
            return data.resample('1H').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        elif timeframe == TimeframeType.H4:
            return data.resample('4H').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        elif timeframe == TimeframeType.D1:
            return data.resample('1D').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        elif timeframe == TimeframeType.W1:
            return data.resample('1W').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
        
        return data
    
    def analyze_timeframe(self, data: pd.DataFrame, timeframe: TimeframeType) -> Dict[str, any]:
        """개별 타임프레임 분석"""
        resampled_data = self.resample_data(data, timeframe)
        
        if len(resampled_data) < 50:
            return {
                'timeframe': timeframe,
                'signals': [],
                'patterns': [],
                'trend': 'neutral',
                'strength': 0.0
            }
        
        # 기술적 지표 신호
        technical_signals = self.technical_analyzer.generate_signals(resampled_data)
        
        # 패턴 신호
        pattern_signals = self.pattern_recognizer.detect_all_patterns(resampled_data)
        
        # 트렌드 분석
        trend_direction, trend_strength = self.analyze_trend(resampled_data)
        
        return {
            'timeframe': timeframe,
            'signals': technical_signals,
            'patterns': pattern_signals,
            'trend': trend_direction,
            'strength': trend_strength
        }
    
    def analyze_trend(self, data: pd.DataFrame) -> Tuple[str, float]:
        """트렌드 분석"""
        close = data['close']
        
        if len(close) < 20:
            return 'neutral', 0.0
        
        # 단기, 중기, 장기 이동평균선
        ema_8 = self.technical_analyzer.calculate_ema_talib(close, 8)
        ema_21 = self.technical_analyzer.calculate_ema_talib(close, 21)
        ema_50 = self.technical_analyzer.calculate_ema_talib(close, 50)
        
        # 최근 값들
        current_price = close.iloc[-1]
        ema_8_current = ema_8.iloc[-1] if not pd.isna(ema_8.iloc[-1]) else current_price
        ema_21_current = ema_21.iloc[-1] if not pd.isna(ema_21.iloc[-1]) else current_price
        ema_50_current = ema_50.iloc[-1] if not pd.isna(ema_50.iloc[-1]) else current_price
        
        # 트렌드 방향 결정
        bullish_signals = 0
        bearish_signals = 0
        
        if current_price > ema_8_current:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if ema_8_current > ema_21_current:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        if ema_21_current > ema_50_current:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # 트렌드 강도 계산
        if bullish_signals > bearish_signals:
            trend_direction = 'bullish'
            trend_strength = bullish_signals / 3.0
        elif bearish_signals > bullish_signals:
            trend_direction = 'bearish'
            trend_strength = bearish_signals / 3.0
        else:
            trend_direction = 'neutral'
            trend_strength = 0.5
        
        return trend_direction, trend_strength
    
    def analyze_multi_timeframe(self, data: pd.DataFrame) -> MultiTimeframeSignal:
        """멀티 타임프레임 종합 분석"""
        timeframe_analyses = {}
        
        # 각 타임프레임별 분석
        for timeframe in self.timeframes:
            timeframe_analyses[timeframe] = self.analyze_timeframe(data, timeframe)
        
        # 주요 타임프레임 (H1) 신호를 기준으로 설정
        primary_timeframe = TimeframeType.H1
        primary_analysis = timeframe_analyses[primary_timeframe]
        
        if not primary_analysis['signals']:
            # 신호가 없는 경우 중립 신호 생성
            primary_signal = TechnicalSignal(
                signal_type=SignalType.HOLD,
                strength=0.0,
                confidence=0.0,
                indicator='Multi-Timeframe',
                value=0.0,
                timestamp=data.index[-1],
                description="멀티 타임프레임 분석 - 신호 없음"
            )
        else:
            # 가장 강한 신호를 주요 신호로 선택
            primary_signal = max(primary_analysis['signals'], key=lambda x: x.strength * x.confidence)
        
        # 지원 신호와 충돌 신호 분류
        supporting_signals = []
        conflicting_signals = []
        
        for timeframe, analysis in timeframe_analyses.items():
            for signal in analysis['signals']:
                if self._signals_align(primary_signal, signal):
                    supporting_signals.append(signal)
                else:
                    conflicting_signals.append(signal)
        
        # 전체 강도 및 신뢰도 계산
        overall_strength = self._calculate_overall_strength(primary_signal, supporting_signals, conflicting_signals)
        overall_confidence = self._calculate_overall_confidence(primary_signal, supporting_signals, conflicting_signals)
        
        # 타임프레임 정렬 확인
        timeframe_alignment = self._check_timeframe_alignment(timeframe_analyses)
        
        # 트렌드 방향 결정
        trend_direction = self._determine_trend_direction(timeframe_analyses)
        
        return MultiTimeframeSignal(
            primary_signal=primary_signal,
            supporting_signals=supporting_signals,
            conflicting_signals=conflicting_signals,
            overall_strength=overall_strength,
            overall_confidence=overall_confidence,
            timeframe_alignment=timeframe_alignment,
            trend_direction=trend_direction
        )
    
    def _signals_align(self, signal1: TechnicalSignal, signal2: TechnicalSignal) -> bool:
        """두 신호가 정렬되는지 확인"""
        if signal1.signal_type == SignalType.BUY and signal2.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            return True
        elif signal1.signal_type == SignalType.SELL and signal2.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            return True
        elif signal1.signal_type == SignalType.STRONG_BUY and signal2.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            return True
        elif signal1.signal_type == SignalType.STRONG_SELL and signal2.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            return True
        return False
    
    def _calculate_overall_strength(self, primary: TechnicalSignal, supporting: List[TechnicalSignal], 
                                  conflicting: List[TechnicalSignal]) -> float:
        """전체 강도 계산"""
        base_strength = primary.strength
        
        # 지원 신호로 인한 강도 증가
        support_bonus = sum(signal.strength for signal in supporting) * 0.1
        
        # 충돌 신호로 인한 강도 감소
        conflict_penalty = sum(signal.strength for signal in conflicting) * 0.15
        
        overall_strength = base_strength + support_bonus - conflict_penalty
        return max(0.0, min(1.0, overall_strength))
    
    def _calculate_overall_confidence(self, primary: TechnicalSignal, supporting: List[TechnicalSignal], 
                                    conflicting: List[TechnicalSignal]) -> float:
        """전체 신뢰도 계산"""
        base_confidence = primary.confidence
        
        # 지원 신호로 인한 신뢰도 증가
        support_bonus = sum(signal.confidence for signal in supporting) * 0.1
        
        # 충돌 신호로 인한 신뢰도 감소
        conflict_penalty = sum(signal.confidence for signal in conflicting) * 0.2
        
        overall_confidence = base_confidence + support_bonus - conflict_penalty
        return max(0.0, min(1.0, overall_confidence))
    
    def _check_timeframe_alignment(self, timeframe_analyses: Dict[TimeframeType, Dict]) -> bool:
        """타임프레임 정렬 확인"""
        trends = [analysis['trend'] for analysis in timeframe_analyses.values()]
        
        # 모든 타임프레임이 같은 방향을 가리키는지 확인
        if len(set(trends)) == 1:
            return True
        
        # 대부분의 타임프레임이 같은 방향을 가리키는지 확인
        trend_counts = {}
        for trend in trends:
            trend_counts[trend] = trend_counts.get(trend, 0) + 1
        
        max_count = max(trend_counts.values())
        return max_count >= len(trends) * 0.6  # 60% 이상 일치
    
    def _determine_trend_direction(self, timeframe_analyses: Dict[TimeframeType, Dict]) -> str:
        """트렌드 방향 결정"""
        trend_votes = {'bullish': 0, 'bearish': 0, 'neutral': 0}
        
        for analysis in timeframe_analyses.values():
            trend = analysis['trend']
            strength = analysis['strength']
            
            # 강도에 따른 가중치 적용
            if trend == 'bullish':
                trend_votes['bullish'] += strength
            elif trend == 'bearish':
                trend_votes['bearish'] += strength
            else:
                trend_votes['neutral'] += 1
        
        # 가장 많은 표를 받은 트렌드 방향 반환
        return max(trend_votes, key=trend_votes.get)
    
    def get_timeframe_summary(self, data: pd.DataFrame) -> Dict[str, any]:
        """타임프레임 요약 정보"""
        summary = {}
        
        for timeframe in self.timeframes:
            analysis = self.analyze_timeframe(data, timeframe)
            summary[timeframe.value] = {
                'trend': analysis['trend'],
                'strength': analysis['strength'],
                'signal_count': len(analysis['signals']),
                'pattern_count': len(analysis['patterns'])
            }
        
        return summary


# 싱글톤 인스턴스
multi_timeframe_analyzer = MultiTimeframeAnalyzer()
