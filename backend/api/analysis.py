"""
기술적 분석 관련 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd

from analysis.technical_indicators import technical_analyzer, TechnicalSignal
from analysis.pattern_recognition import pattern_recognizer, PatternSignal
from analysis.multi_timeframe import multi_timeframe_analyzer, MultiTimeframeSignal

router = APIRouter()


class AnalysisRequest(BaseModel):
    """분석 요청"""
    symbol: str
    timeframe: str = "1h"
    limit: int = 100


class TechnicalAnalysisResponse(BaseModel):
    """기술적 분석 응답"""
    symbol: str
    timeframe: str
    indicators: Dict[str, float]
    signals: List[Dict[str, any]]
    patterns: List[Dict[str, any]]
    multi_timeframe: Dict[str, any]
    timestamp: datetime
    
    model_config = {"arbitrary_types_allowed": True}


@router.post("/technical", response_model=TechnicalAnalysisResponse)
async def get_technical_analysis(request: AnalysisRequest):
    """기술적 분석 수행"""
    try:
        # 실제로는 데이터베이스에서 데이터를 가져와야 함
        # 여기서는 샘플 데이터 생성
        from test_technical_analysis import generate_sample_data
        data = generate_sample_data(request.limit)
        
        # 기술적 지표 계산
        indicators = technical_analyzer.calculate_all_indicators(data)
        
        # 지표 값 추출 (최신 값)
        indicator_values = {}
        for name, values in indicators.items():
            if not pd.isna(values.iloc[-1]):
                indicator_values[name] = float(values.iloc[-1])
        
        # 신호 생성
        signals = technical_analyzer.generate_signals(data)
        signal_data = []
        for signal in signals:
            signal_data.append({
                "type": signal.signal_type.value,
                "strength": signal.strength,
                "confidence": signal.confidence,
                "indicator": signal.indicator,
                "value": signal.value,
                "description": signal.description
            })
        
        # 패턴 탐지
        patterns = pattern_recognizer.detect_all_patterns(data)
        pattern_data = []
        for pattern in patterns:
            pattern_data.append({
                "name": pattern.pattern_name,
                "type": pattern.pattern_type.value,
                "confidence": pattern.confidence,
                "strength": pattern.strength,
                "description": pattern.description
            })
        
        # 멀티 타임프레임 분석
        multi_signal = multi_timeframe_analyzer.analyze_multi_timeframe(data)
        multi_timeframe_data = {
            "primary_signal": {
                "type": multi_signal.primary_signal.signal_type.value,
                "strength": multi_signal.primary_signal.strength,
                "confidence": multi_signal.primary_signal.confidence,
                "indicator": multi_signal.primary_signal.indicator,
                "description": multi_signal.primary_signal.description
            },
            "overall_strength": multi_signal.overall_strength,
            "overall_confidence": multi_signal.overall_confidence,
            "timeframe_alignment": multi_signal.timeframe_alignment,
            "trend_direction": multi_signal.trend_direction,
            "supporting_signals": len(multi_signal.supporting_signals),
            "conflicting_signals": len(multi_signal.conflicting_signals)
        }
        
        return TechnicalAnalysisResponse(
            symbol=request.symbol,
            timeframe=request.timeframe,
            indicators=indicator_values,
            signals=signal_data,
            patterns=pattern_data,
            multi_timeframe=multi_timeframe_data,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Technical analysis failed: {str(e)}")


@router.get("/indicators/{symbol}")
async def get_indicators(symbol: str, timeframe: str = "1h", limit: int = 100):
    """기술적 지표 조회"""
    try:
        # 실제로는 데이터베이스에서 데이터를 가져와야 함
        from test_technical_analysis import generate_sample_data
        data = generate_sample_data(limit)
        
        # 기술적 지표 계산
        indicators = technical_analyzer.calculate_all_indicators(data)
        
        # 지표 값 반환
        result = {}
        for name, values in indicators.items():
            if not pd.isna(values.iloc[-1]):
                result[name] = float(values.iloc[-1])
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": result,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get indicators: {str(e)}")


@router.get("/signals/{symbol}")
async def get_signals(symbol: str, timeframe: str = "1h", limit: int = 100):
    """거래 신호 조회"""
    try:
        # 실제로는 데이터베이스에서 데이터를 가져와야 함
        from test_technical_analysis import generate_sample_data
        data = generate_sample_data(limit)
        
        # 신호 생성
        signals = technical_analyzer.generate_signals(data)
        
        # 신호 데이터 변환
        signal_data = []
        for signal in signals:
            signal_data.append({
                "type": signal.signal_type.value,
                "strength": signal.strength,
                "confidence": signal.confidence,
                "indicator": signal.indicator,
                "value": signal.value,
                "description": signal.description,
                "timestamp": signal.timestamp.isoformat()
            })
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "signals": signal_data,
            "count": len(signal_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get signals: {str(e)}")


@router.get("/patterns/{symbol}")
async def get_patterns(symbol: str, timeframe: str = "1h", limit: int = 100):
    """차트 패턴 조회"""
    try:
        # 실제로는 데이터베이스에서 데이터를 가져와야 함
        from test_technical_analysis import generate_sample_data
        data = generate_sample_data(limit)
        
        # 패턴 탐지
        patterns = pattern_recognizer.detect_all_patterns(data)
        
        # 패턴 데이터 변환
        pattern_data = []
        for pattern in patterns:
            pattern_data.append({
                "name": pattern.pattern_name,
                "type": pattern.pattern_type.value,
                "confidence": pattern.confidence,
                "strength": pattern.strength,
                "description": pattern.description,
                "start_index": pattern.start_index,
                "end_index": pattern.end_index
            })
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "patterns": pattern_data,
            "count": len(pattern_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patterns: {str(e)}")


@router.get("/multi-timeframe/{symbol}")
async def get_multi_timeframe_analysis(symbol: str, limit: int = 200):
    """멀티 타임프레임 분석 조회"""
    try:
        # 실제로는 데이터베이스에서 데이터를 가져와야 함
        from test_technical_analysis import generate_sample_data
        data = generate_sample_data(limit)
        
        # 멀티 타임프레임 분석
        multi_signal = multi_timeframe_analyzer.analyze_multi_timeframe(data)
        
        # 타임프레임 요약
        timeframe_summary = multi_timeframe_analyzer.get_timeframe_summary(data)
        
        return {
            "success": True,
            "symbol": symbol,
            "analysis": {
                "primary_signal": {
                    "type": multi_signal.primary_signal.signal_type.value,
                    "strength": multi_signal.primary_signal.strength,
                    "confidence": multi_signal.primary_signal.confidence,
                    "indicator": multi_signal.primary_signal.indicator,
                    "description": multi_signal.primary_signal.description
                },
                "overall_strength": multi_signal.overall_strength,
                "overall_confidence": multi_signal.overall_confidence,
                "timeframe_alignment": multi_signal.timeframe_alignment,
                "trend_direction": multi_signal.trend_direction,
                "supporting_signals": len(multi_signal.supporting_signals),
                "conflicting_signals": len(multi_signal.conflicting_signals)
            },
            "timeframe_summary": timeframe_summary,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get multi-timeframe analysis: {str(e)}")


@router.get("/trend/{symbol}")
async def get_trend_analysis(symbol: str, timeframe: str = "1h", limit: int = 100):
    """트렌드 분석 조회"""
    try:
        # 실제로는 데이터베이스에서 데이터를 가져와야 함
        from test_technical_analysis import generate_sample_data
        data = generate_sample_data(limit)
        
        # 트렌드 분석
        trend_direction, trend_strength = multi_timeframe_analyzer.analyze_trend(data)
        
        # 이동평균선 계산
        close = data['close']
        ema_8 = technical_analyzer.calculate_ema_talib(close, 8)
        ema_21 = technical_analyzer.calculate_ema_talib(close, 21)
        ema_50 = technical_analyzer.calculate_ema_talib(close, 50)
        
        return {
            "success": True,
            "symbol": symbol,
            "timeframe": timeframe,
            "trend": {
                "direction": trend_direction,
                "strength": trend_strength,
                "moving_averages": {
                    "ema_8": float(ema_8.iloc[-1]) if not pd.isna(ema_8.iloc[-1]) else None,
                    "ema_21": float(ema_21.iloc[-1]) if not pd.isna(ema_21.iloc[-1]) else None,
                    "ema_50": float(ema_50.iloc[-1]) if not pd.isna(ema_50.iloc[-1]) else None
                }
            },
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trend analysis: {str(e)}")
