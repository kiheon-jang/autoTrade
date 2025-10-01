"""
AI 전략 추천 시스템 API
실제 시장 데이터를 기반으로 한 실시간 전략 추천 및 자동 변경
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import asyncio
import json
import logging
import pandas as pd
import numpy as np
import aiohttp
import asyncio

from analysis.technical_indicators import technical_analyzer

router = APIRouter()
logger = logging.getLogger(__name__)

# 전역 변수
current_recommendations = {}
active_strategy = None
recommendation_history = []


class MarketAnalysisRequest(BaseModel):
    """시장 분석 요청"""
    symbols: List[str] = ["BTC", "ETH", "XRP"]
    timeframe: str = "1h"
    analysis_depth: str = "comprehensive"


class StrategyRecommendation(BaseModel):
    """전략 추천 정보"""
    strategy_id: str
    strategy_name: str
    strategy_type: str
    confidence_score: float
    expected_return: float
    risk_level: str
    market_conditions: Dict[str, Any]
    reasoning: str
    technical_signals: Dict[str, Any]  # Dict로 변경
    ml_signals: Dict[str, Any]  # Dict로 변경
    pattern_analysis: Dict[str, Any]  # Dict로 변경
    recommendation_reason: str
    validity_period: int  # 분 단위
    created_at: datetime


class AIRecommendationResponse(BaseModel):
    """AI 추천 응답"""
    success: bool
    recommendations: List[StrategyRecommendation]
    market_summary: Dict[str, Any]
    analysis_timestamp: datetime
    next_update: datetime


class StrategySelectionRequest(BaseModel):
    """전략 선택 요청"""
    strategy_id: str
    auto_switch: bool = True
    max_risk: float = 0.05  # 5%


async def fetch_real_market_data(symbol: str, timeframe: str = "1h", limit: int = 100) -> pd.DataFrame:
    """실제 시장 데이터 수집"""
    try:
        # 빗썸 API에서 실제 데이터 수집
        async with aiohttp.ClientSession() as session:
            # 빗썸 공개 API (인증 불필요)
            url = f"https://api.bithumb.com/public/candlestick/{symbol}_KRW/{timeframe}"
            params = {"count": limit}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "0000":
                        candles = data.get("data", [])
                        
                        # 데이터 변환
                        df_data = []
                        for candle in candles:
                            df_data.append({
                                'timestamp': pd.to_datetime(int(candle[0]), unit='ms'),
                                'open': float(candle[1]),
                                'high': float(candle[2]),
                                'low': float(candle[3]),
                                'close': float(candle[4]),
                                'volume': float(candle[5])
                            })
                        
                        df = pd.DataFrame(df_data)
                        df = df.set_index('timestamp')
                        df = df.sort_index()
                        return df
                    else:
                        logger.warning(f"빗썸 API 오류: {data.get('message', 'Unknown error')}")
                else:
                    logger.warning(f"빗썸 API HTTP 오류: {response.status}")
                    
    except Exception as e:
        logger.error(f"시장 데이터 수집 실패 {symbol}: {e}")
    
    # 실패 시 더미 데이터 반환 (개발용)
    logger.warning(f"실제 데이터 수집 실패, 더미 데이터 사용: {symbol}")
    dates = pd.date_range(end=datetime.now(), periods=limit, freq='1min')
    np.random.seed(42)
    
    base_price = 50000 if symbol == "BTC" else 3000 if symbol == "ETH" else 0.5
    price_changes = np.random.normal(0, 0.02, limit)
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.randint(100000, 1000000, limit)
    })
    return data.set_index('timestamp')


@router.get("/test")
async def test_endpoint():
    """테스트 엔드포인트"""
    return {"message": "AI 추천 시스템이 정상 작동합니다", "timestamp": datetime.now()}

@router.post("/analyze-market", response_model=AIRecommendationResponse)
async def analyze_market_and_recommend(request: MarketAnalysisRequest):
    """시장 분석 및 전략 추천"""
    try:
        logger.info(f"시장 분석 시작: {request.symbols}")
        
        # 1. 실제 시장 데이터 수집
        market_data = {}
        for symbol in request.symbols:
            try:
                data = await fetch_real_market_data(symbol, request.timeframe, 100)
                if data is not None and not data.empty:
                    market_data[symbol] = data
                    logger.info(f"데이터 수집 성공: {symbol} ({len(data)}개 캔들)")
                else:
                    logger.warning(f"데이터 수집 실패: {symbol}")
            except Exception as e:
                logger.error(f"데이터 수집 오류 {symbol}: {e}")
                continue
        
        if not market_data:
            raise HTTPException(status_code=400, detail="시장 데이터를 수집할 수 없습니다")
        
        # 2. 종합 시장 분석
        market_analysis = await _comprehensive_market_analysis(market_data)
        
        # 3. AI 전략 추천 생성
        recommendations = _create_basic_recommendations(market_analysis)
        logger.info(f"생성된 추천 수: {len(recommendations)}")
        
        # 4. 추천 결과 저장
        global current_recommendations
        current_recommendations = {rec.strategy_id: rec for rec in recommendations}
        recommendation_history.extend(recommendations)
        
        # 최근 100개만 유지
        if len(recommendation_history) > 100:
            recommendation_history[:] = recommendation_history[-100:]
        
        return AIRecommendationResponse(
            success=True,
            recommendations=recommendations,
            market_summary=market_analysis,
            analysis_timestamp=datetime.now(),
            next_update=datetime.now() + timedelta(minutes=30)
        )
        
    except Exception as e:
        logger.error(f"시장 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시장 분석 실패: {str(e)}")


@router.post("/select-strategy")
async def select_strategy(request: StrategySelectionRequest, background_tasks: BackgroundTasks):
    """사용자가 추천된 전략 선택 및 실제 거래 시작"""
    try:
        global active_strategy
        
        if request.strategy_id not in current_recommendations:
            raise HTTPException(status_code=400, detail="선택한 전략이 유효하지 않습니다")
        
        selected_recommendation = current_recommendations[request.strategy_id]
        
        # 전략 설정
        strategy_config = {
            "strategy_type": selected_recommendation.strategy_type,
            "auto_switch": request.auto_switch,
            "max_risk": request.max_risk,
            "confidence_threshold": 0.7,
            "trading_mode": getattr(request, 'trading_mode', 'paper')  # paper or live
        }
        
        # 자동거래 엔진 가져오기
        from trading.auto_trading_engine import get_trading_engine
        
        trading_engine = get_trading_engine(
            trading_mode=strategy_config['trading_mode'],
            initial_capital=getattr(request, 'initial_capital', 1000000)
        )
        
        # 전략 데이터 변환
        strategy_data = {
            "strategy_id": request.strategy_id,
            "strategy_name": selected_recommendation.strategy_name,
            "strategy_type": selected_recommendation.strategy_type,
            "confidence_score": selected_recommendation.confidence_score,
            "technical_signals": selected_recommendation.technical_signals,
            "ml_signals": selected_recommendation.ml_signals,
            "pattern_analysis": selected_recommendation.pattern_analysis
        }
        
        # 실제 거래 시작
        trading_result = await trading_engine.start_strategy(strategy_data, strategy_config)
        
        # 백그라운드에서 전략 모니터링 시작
        if request.auto_switch:
            background_tasks.add_task(
                _monitor_strategy_performance,
                selected_recommendation,
                strategy_config
            )
        
        # 활성 전략 저장
        active_strategy = {
            "strategy_id": request.strategy_id,
            "recommendation": selected_recommendation,
            "config": strategy_config,
            "started_at": datetime.now(),
            "auto_switch": request.auto_switch,
            "trading_engine": trading_engine
        }
        
        return {
            "success": True,
            "message": f"전략 '{selected_recommendation.strategy_name}'이 활성화되었습니다",
            "strategy": {
                "id": request.strategy_id,
                "name": selected_recommendation.strategy_name,
                "type": selected_recommendation.strategy_type,
                "confidence": selected_recommendation.confidence_score,
                "auto_switch": request.auto_switch
            },
            "trading": trading_result
        }
        
    except Exception as e:
        logger.error(f"전략 선택 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"전략 선택 실패: {str(e)}")


@router.get("/current-recommendations")
async def get_current_recommendations():
    """현재 추천된 전략들 조회"""
    global current_recommendations, active_strategy
    return {
        "success": True,
        "recommendations": list(current_recommendations.values()),
        "active_strategy": active_strategy,
        "timestamp": datetime.now()
    }


@router.get("/recommendation-history")
async def get_recommendation_history(limit: int = 20):
    """추천 히스토리 조회"""
    return {
        "success": True,
        "history": recommendation_history[-limit:],
        "total_count": len(recommendation_history)
    }


async def _comprehensive_market_analysis(market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """종합 시장 분석"""
    analysis = {
        "overall_trend": "neutral",
        "volatility_level": "medium",
        "market_sentiment": "neutral",
        "technical_signals": {},
        "ml_predictions": {},
        "pattern_analysis": {},
        "risk_assessment": "medium"
    }
    
    try:
        # 1. 기술적 분석
        for symbol, data in market_data.items():
            if data.empty:
                continue
                
            # 기술적 지표 계산
            indicators = technical_analyzer.calculate_all_indicators(data)
            signals = technical_analyzer.generate_signals(data)
            
            analysis["technical_signals"][symbol] = {
                "indicators": {name: float(val.iloc[-1]) if not pd.isna(val.iloc[-1]) else None 
                              for name, val in indicators.items()},
                "signals": [{
                    "type": signal.signal_type.value,
                    "strength": signal.strength,
                    "confidence": signal.confidence,
                    "description": signal.description
                } for signal in signals]
            }
        
        # 2. 머신러닝 예측 (간단한 휴리스틱)
        for symbol, data in market_data.items():
            if data.empty or len(data) < 50:
                continue
                
            # 간단한 휴리스틱 기반 예측
            close_prices = data['close']
            sma_20 = close_prices.rolling(window=20).mean()
            sma_50 = close_prices.rolling(window=50).mean()
            
            current_price = close_prices.iloc[-1]
            current_sma_20 = sma_20.iloc[-1]
            current_sma_50 = sma_50.iloc[-1]
            
            # 트렌드 판단
            if current_price > current_sma_20 > current_sma_50:
                signal_type = "BUY"
                confidence = 0.8
            elif current_price < current_sma_20 < current_sma_50:
                signal_type = "SELL"
                confidence = 0.8
            else:
                signal_type = "HOLD"
                confidence = 0.5
            
            analysis["ml_predictions"][symbol] = {
                "signal_type": signal_type,
                "confidence": confidence,
                "strength": 0.7,
                "features": {
                    "trend": "up" if current_price > current_sma_20 else "down",
                    "momentum": float((current_price - current_sma_20) / current_sma_20 * 100)
                }
            }
        
        # 3. 패턴 분석 (간단한 패턴)
        for symbol, data in market_data.items():
            if data.empty:
                continue
                
            patterns = []
            close_prices = data['close']
            
            # 간단한 패턴 감지
            if len(close_prices) >= 5:
                recent_prices = close_prices.tail(5)
                if all(recent_prices.iloc[i] > recent_prices.iloc[i-1] for i in range(1, 5)):
                    patterns.append({
                        "name": "Uptrend",
                        "type": "trend",
                        "confidence": 0.7,
                        "strength": 0.6,
                        "description": "상승 추세 패턴 감지"
                    })
                elif all(recent_prices.iloc[i] < recent_prices.iloc[i-1] for i in range(1, 5)):
                    patterns.append({
                        "name": "Downtrend",
                        "type": "trend",
                        "confidence": 0.7,
                        "strength": 0.6,
                        "description": "하락 추세 패턴 감지"
                    })
            
            analysis["pattern_analysis"][symbol] = patterns
        
        # 4. 종합 시장 판단
        analysis = _determine_market_conditions(analysis)
        
    except Exception as e:
        logger.error(f"시장 분석 오류: {e}")
    
    return analysis


def _create_basic_recommendations(market_analysis: Dict) -> List[StrategyRecommendation]:
    """실제 시장 분석 기반 AI 추천 생성"""
    recommendations = []
    
    try:
        # 시장 조건 분석
        market_trend = market_analysis.get("overall_trend", "neutral")
        volatility = market_analysis.get("volatility_level", "medium")
        sentiment = market_analysis.get("market_sentiment", "neutral")
        risk_level = market_analysis.get("risk_assessment", "medium")
        
        # 기술적 신호 분석
        technical_signals = market_analysis.get("technical_signals", {})
        ml_predictions = market_analysis.get("ml_predictions", {})
        
        # BTC 신호 분석
        btc_signals = technical_signals.get("BTC", {}).get("signals", [])
        btc_ml = ml_predictions.get("BTC", {})
        
        # 신호 기반 추천 생성
        buy_signals = [s for s in btc_signals if s.get("type") == "buy"]
        sell_signals = [s for s in btc_signals if s.get("type") == "sell"]
        
        logger.info(f"시장 분석 결과: trend={market_trend}, volatility={volatility}, buy_signals={len(buy_signals)}, sell_signals={len(sell_signals)}")
        
        # 1. 매수 신호가 강한 경우 - 적극적 매수 전략
        if len(buy_signals) > len(sell_signals) and btc_ml.get("signal_type") == "BUY":
            confidence = min(0.9, 0.7 + (len(buy_signals) * 0.1))
            expected_return = 0.15 + (btc_ml.get("confidence", 0.5) * 0.1)
            
            rec = StrategyRecommendation(
                strategy_id="aggressive_buy_strategy",
                strategy_name="적극적 매수 전략",
                strategy_type="momentum",
                confidence_score=confidence,
                expected_return=expected_return,
                risk_level="high",
                market_conditions=market_analysis,
                reasoning=f"강한 매수 신호({len(buy_signals)}개)와 ML 예측(BUY, {btc_ml.get('confidence', 0.5):.1f})을 기반으로 한 적극적 매수 전략",
                technical_signals=technical_signals,
                ml_signals=ml_predictions,
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason=f"현재 {len(buy_signals)}개의 매수 신호와 ML 예측으로 상승 추세가 확인되어 적극적 매수 전략을 추천합니다",
                validity_period=120,  # 2시간
                created_at=datetime.now()
            )
            recommendations.append(rec)
        
        # 2. 하락 추세인 경우 - 공매도 또는 대기 전략
        elif market_trend == "bearish" and len(sell_signals) > 0:
            rec = StrategyRecommendation(
                strategy_id="bear_market_strategy",
                strategy_name="하락장 대응 전략",
                strategy_type="defensive",
                confidence_score=0.8,
                expected_return=-0.05,  # 손실 최소화
                risk_level="low",
                market_conditions=market_analysis,
                reasoning=f"하락 추세와 {len(sell_signals)}개의 매도 신호를 기반으로 한 방어적 전략",
                technical_signals=technical_signals,
                ml_signals=ml_predictions,
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason=f"현재 하락 추세가 확인되어 리스크를 최소화하는 방어적 전략을 추천합니다",
                validity_period=240,  # 4시간
                created_at=datetime.now()
            )
            recommendations.append(rec)
        
        # 3. 고변동성 시장 - 스캘핑 전략
        elif volatility == "high":
            rec = StrategyRecommendation(
                strategy_id="scalping_high_vol",
                strategy_name="고변동성 스캘핑 전략",
                strategy_type="scalping",
                confidence_score=0.75,
                expected_return=0.08,
                risk_level="high",
                market_conditions=market_analysis,
                reasoning=f"고변동성 환경에서 단기 수익을 추구하는 스캘핑 전략",
                technical_signals=technical_signals,
                ml_signals=ml_predictions,
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason=f"현재 변동성이 높아 단기 스캘핑 전략으로 수익 기회를 포착할 수 있습니다",
                validity_period=60,  # 1시간
                created_at=datetime.now()
            )
            recommendations.append(rec)
        
        # 4. 중립적 시장 - 스윙트레이딩
        else:
            confidence = 0.7 + (btc_ml.get("confidence", 0.5) * 0.1)
            expected_return = 0.12 + (btc_ml.get("strength", 0.5) * 0.05)
            
            rec = StrategyRecommendation(
                strategy_id="swing_trading_neutral",
                strategy_name="중립 시장 스윙트레이딩",
                strategy_type="swing_trading",
                confidence_score=confidence,
                expected_return=expected_return,
                risk_level="medium",
                market_conditions=market_analysis,
                reasoning=f"중립적 시장 환경에서 중기 트렌드를 활용한 스윙트레이딩 전략",
                technical_signals=technical_signals,
                ml_signals=ml_predictions,
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason=f"현재 중립적 시장에서 ML 신호 강도 {btc_ml.get('strength', 0.5):.1f}를 활용한 스윙트레이딩이 적합합니다",
                validity_period=180,  # 3시간
                created_at=datetime.now()
            )
            recommendations.append(rec)
        
        # 5. DCA 전략 (항상 추천)
        dca_rec = StrategyRecommendation(
            strategy_id="dca_strategy",
            strategy_name="달러 코스트 애버리징",
            strategy_type="dca",
            confidence_score=0.85,
            expected_return=0.08,
            risk_level="low",
            market_conditions=market_analysis,
            reasoning="시장 변동성을 분산하여 장기적으로 안정적인 수익을 추구하는 DCA 전략",
            technical_signals=technical_signals,
            ml_signals=ml_predictions,
            pattern_analysis=market_analysis.get("pattern_analysis", {}),
            recommendation_reason="변동성이 큰 암호화폐 시장에서 리스크를 분산하는 DCA 전략을 추천합니다",
            validity_period=1440,  # 24시간
            created_at=datetime.now()
        )
        recommendations.append(dca_rec)
        
        logger.info(f"실제 시장 분석 기반 추천 {len(recommendations)}개 생성 완료")
        
    except Exception as e:
        logger.error(f"AI 추천 생성 실패: {e}", exc_info=True)
    
    return recommendations


async def _generate_simple_recommendations(market_analysis: Dict) -> List[StrategyRecommendation]:
    """간단한 AI 전략 추천 생성"""
    recommendations = []
    
    try:
        # 기본 추천 항상 생성
        basic_recommendation = StrategyRecommendation(
            strategy_id="ai_adaptive_strategy",
            strategy_name="AI 적응형 전략",
            strategy_type="adaptive",
            confidence_score=0.75,
            expected_return=0.12,
            risk_level="medium",
            market_conditions=market_analysis,
            reasoning="시장 조건에 따라 자동으로 전략을 조정하는 AI 기반 전략",
            technical_signals=market_analysis.get("technical_signals", {}),
            ml_signals=market_analysis.get("ml_predictions", {}),
            pattern_analysis=market_analysis.get("pattern_analysis", {}),
            recommendation_reason="현재 시장 조건을 분석한 AI 추천 전략입니다",
            validity_period=240,
            created_at=datetime.now()
        )
        recommendations.append(basic_recommendation)
        
        # 추가 추천
        trend_recommendation = StrategyRecommendation(
            strategy_id="swing_trading_trend",
            strategy_name="스윙트레이딩 전략",
            strategy_type="swing_trading",
            confidence_score=0.78,
            expected_return=0.15,
            risk_level="medium",
            market_conditions=market_analysis,
            reasoning="중기 트렌드를 활용한 스윙트레이딩 전략",
            technical_signals=market_analysis.get("technical_signals", {}),
            ml_signals=market_analysis.get("ml_predictions", {}),
            pattern_analysis=market_analysis.get("pattern_analysis", {}),
            recommendation_reason="현재 시장에서 효과적인 스윙트레이딩 전략입니다",
            validity_period=180,
            created_at=datetime.now()
        )
        recommendations.append(trend_recommendation)
        
        logger.info(f"간단한 추천 {len(recommendations)}개 생성 완료")
        
    except Exception as e:
        logger.error(f"간단한 추천 생성 실패: {e}", exc_info=True)
    
    return recommendations


async def _generate_strategy_recommendations(market_analysis: Dict, market_data: Dict) -> List[StrategyRecommendation]:
    """AI 전략 추천 생성"""
    recommendations = []
    
    try:
        # 시장 조건 추출
        market_trend = market_analysis.get("overall_trend", "neutral")
        volatility = market_analysis.get("volatility_level", "medium")
        sentiment = market_analysis.get("market_sentiment", "neutral")
        
        logger.info(f"시장 조건 분석: trend={market_trend}, volatility={volatility}, sentiment={sentiment}")
        
        # 기본 추천 항상 생성
        basic_recommendation = StrategyRecommendation(
            strategy_id="ai_adaptive_strategy",
            strategy_name="AI 적응형 전략",
            strategy_type="adaptive",
            confidence_score=0.75,
            expected_return=0.12,
            risk_level="medium",
            market_conditions=market_analysis,
            reasoning="시장 조건에 따라 자동으로 전략을 조정하는 AI 기반 전략",
            technical_signals=market_analysis.get("technical_signals", {}),
            ml_signals=market_analysis.get("ml_predictions", {}),
            pattern_analysis=market_analysis.get("pattern_analysis", {}),
            recommendation_reason=f"현재 시장 트렌드({market_trend})와 변동성({volatility})을 고려한 최적 전략입니다",
            validity_period=240,
            created_at=datetime.now()
        )
        recommendations.append(basic_recommendation)
        logger.info(f"기본 추천 생성 완료: {basic_recommendation.strategy_id}")
        
        # 고변동성 전략
        if volatility == "high":
            high_vol_recommendation = StrategyRecommendation(
                strategy_id="day_trading_high_vol",
                strategy_name="고변동성 데이트레이딩",
                strategy_type="day_trading",
                confidence_score=0.85,
                expected_return=0.08,
                risk_level="high",
                market_conditions=market_analysis,
                reasoning="고변동성 시장에서 단기 수익 기회 포착",
                technical_signals=market_analysis.get("technical_signals", {}),
                ml_signals=market_analysis.get("ml_predictions", {}),
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason="변동성이 높은 시장에서 데이트레이딩 전략이 효과적입니다",
                validity_period=60,
                created_at=datetime.now()
            )
            recommendations.append(high_vol_recommendation)
            logger.info(f"고변동성 추천 생성 완료: {high_vol_recommendation.strategy_id}")
        
        # 트렌드 기반 전략
        if market_trend in ["bullish", "bearish"]:
            trend_recommendation = StrategyRecommendation(
                strategy_id="swing_trading_trend",
                strategy_name="트렌드 기반 스윙트레이딩",
                strategy_type="swing_trading",
                confidence_score=0.78,
                expected_return=0.12,
                risk_level="medium",
                market_conditions=market_analysis,
                reasoning="명확한 트렌드에서 중기 수익 추구",
                technical_signals=market_analysis.get("technical_signals", {}),
                ml_signals=market_analysis.get("ml_predictions", {}),
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason="트렌드가 명확한 시장에서 스윙트레이딩이 적합합니다",
                validity_period=180,
                created_at=datetime.now()
            )
            recommendations.append(trend_recommendation)
            logger.info(f"트렌드 추천 생성 완료: {trend_recommendation.strategy_id}")
        
        # 상승 트렌드 전략
        if market_trend == "bullish":
            bullish_recommendation = StrategyRecommendation(
                strategy_id="long_term_bull",
                strategy_name="장기 상승 투자",
                strategy_type="long_term",
                confidence_score=0.72,
                expected_return=0.25,
                risk_level="low",
                market_conditions=market_analysis,
                reasoning="상승 트렌드에서 장기 수익 추구",
                technical_signals=market_analysis.get("technical_signals", {}),
                ml_signals=market_analysis.get("ml_predictions", {}),
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason="상승 트렌드가 지속될 것으로 예상되어 장기투자가 적합합니다",
                validity_period=1440,
                created_at=datetime.now()
            )
            recommendations.append(bullish_recommendation)
            logger.info(f"상승 추천 생성 완료: {bullish_recommendation.strategy_id}")
        
        # 저변동성 전략
        if volatility == "low":
            low_vol_recommendation = StrategyRecommendation(
                strategy_id="commission_optimized",
                strategy_name="수수료 최적화 전략",
                strategy_type="commission_optimized",
                confidence_score=0.68,
                expected_return=0.05,
                risk_level="low",
                market_conditions=market_analysis,
                reasoning="저변동성 시장에서 수수료 최적화",
                technical_signals=market_analysis.get("technical_signals", {}),
                ml_signals=market_analysis.get("ml_predictions", {}),
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason="저변동성 시장에서는 수수료 최적화 전략이 효과적입니다",
                validity_period=120,
                created_at=datetime.now()
            )
            recommendations.append(low_vol_recommendation)
            logger.info(f"저변동성 추천 생성 완료: {low_vol_recommendation.strategy_id}")
        
        logger.info(f"총 {len(recommendations)}개 추천 생성 완료")
        
    except Exception as e:
        logger.error(f"전략 추천 생성 실패: {e}", exc_info=True)
    
    return recommendations


def _determine_market_conditions(analysis: Dict) -> Dict:
    """시장 조건 판단"""
    try:
        # 기술적 신호 분석
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0
        
        for symbol, signals in analysis.get("technical_signals", {}).items():
            for signal in signals.get("signals", []):
                total_signals += 1
                if signal["type"] == "BUY":
                    bullish_signals += 1
                elif signal["type"] == "SELL":
                    bearish_signals += 1
        
        # ML 예측 분석
        ml_bullish = 0
        ml_bearish = 0
        for symbol, prediction in analysis.get("ml_predictions", {}).items():
            if prediction["signal_type"] == "BUY":
                ml_bullish += 1
            elif prediction["signal_type"] == "SELL":
                ml_bearish += 1
        
        # 종합 판단
        if total_signals > 0:
            bullish_ratio = bullish_signals / total_signals
            if bullish_ratio > 0.6:
                analysis["overall_trend"] = "bullish"
                analysis["market_sentiment"] = "positive"
            elif bullish_ratio < 0.4:
                analysis["overall_trend"] = "bearish"
                analysis["market_sentiment"] = "negative"
            else:
                analysis["overall_trend"] = "neutral"
                analysis["market_sentiment"] = "neutral"
        
        # 변동성 분석
        volatility_scores = []
        for symbol, signals in analysis.get("technical_signals", {}).items():
            indicators = signals.get("indicators", {})
            if "volatility_20" in indicators and indicators["volatility_20"]:
                volatility_scores.append(indicators["volatility_20"])
        
        if volatility_scores:
            avg_volatility = np.mean(volatility_scores)
            if avg_volatility > 0.05:
                analysis["volatility_level"] = "high"
                analysis["risk_assessment"] = "high"
            elif avg_volatility < 0.02:
                analysis["volatility_level"] = "low"
                analysis["risk_assessment"] = "low"
            else:
                analysis["volatility_level"] = "medium"
                analysis["risk_assessment"] = "medium"
        
    except Exception as e:
        logger.error(f"시장 조건 판단 오류: {e}")
    
    return analysis


async def _monitor_strategy_performance(recommendation: StrategyRecommendation, config: Dict):
    """전략 성능 모니터링 및 자동 변경"""
    try:
        logger.info(f"전략 모니터링 시작: {recommendation.strategy_name}")
        
        while True:
            await asyncio.sleep(300)  # 5분마다 체크
            
            # 현재 시장 데이터 재분석
            current_analysis = await _comprehensive_market_analysis({})
            
            # 전략 유효성 검증
            if not _validate_strategy_performance(recommendation, current_analysis):
                logger.info(f"전략 유효성 저하 감지: {recommendation.strategy_name}")
                
                # 새로운 추천 생성
                new_recommendations = await _generate_strategy_recommendations(current_analysis, {})
                
                if new_recommendations:
                    # 가장 높은 신뢰도의 전략으로 자동 변경
                    best_recommendation = max(new_recommendations, key=lambda x: x.confidence_score)
                    
                    if best_recommendation.confidence_score > recommendation.confidence_score:
                        logger.info(f"전략 자동 변경: {recommendation.strategy_name} -> {best_recommendation.strategy_name}")
                        
                        # 전략 변경 로직 구현
                        await _switch_strategy(best_recommendation)
                        break
            
    except Exception as e:
        logger.error(f"전략 모니터링 오류: {e}")


def _validate_strategy_performance(recommendation: StrategyRecommendation, current_analysis: Dict) -> bool:
    """전략 성능 유효성 검증"""
    try:
        # 신뢰도 임계값 체크
        if recommendation.confidence_score < 0.5:
            return False
        
        # 시장 조건 변화 체크
        current_trend = current_analysis.get("overall_trend", "neutral")
        original_conditions = recommendation.market_conditions
        
        # 트렌드 변화가 크면 전략 변경 고려
        if original_conditions.get("overall_trend") != current_trend:
            return False
        
        # 유효성 기간 체크
        validity_end = recommendation.created_at + timedelta(minutes=recommendation.validity_period)
        if datetime.now() > validity_end:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"전략 유효성 검증 오류: {e}")
        return False


async def _switch_strategy(new_recommendation: StrategyRecommendation):
    """전략 자동 변경"""
    try:
        global active_strategy
        
        # 기존 전략 중지
        if active_strategy:
            logger.info(f"기존 전략 중지: {active_strategy['strategy_id']}")
        
        # 새 전략 활성화
        active_strategy = {
            "strategy_id": new_recommendation.strategy_id,
            "recommendation": new_recommendation,
            "config": {
                "strategy_type": new_recommendation.strategy_type,
                "auto_switch": True,
                "max_risk": 0.05,
                "confidence_threshold": 0.7
            },
            "started_at": datetime.now(),
            "auto_switch": True
        }
        
        logger.info(f"새 전략 활성화: {new_recommendation.strategy_name}")
        
    except Exception as e:
        logger.error(f"전략 변경 오류: {e}")


@router.get("/active-strategy")
async def get_active_strategy():
    """현재 활성 전략 조회"""
    return {
        "success": True,
        "active_strategy": active_strategy,
        "timestamp": datetime.now()
    }


@router.post("/stop-autotrading")
async def stop_autotrading():
    """자동거래 중지"""
    try:
        global active_strategy
        
        if not active_strategy:
            return {
                "success": False,
                "message": "실행 중인 전략이 없습니다"
            }
        
        # 거래 엔진 중지
        if 'trading_engine' in active_strategy:
            trading_engine = active_strategy['trading_engine']
            stop_result = await trading_engine.stop_strategy()
        else:
            stop_result = {"success": True, "message": "전략 모니터링만 중지"}
        
        # 활성 전략 초기화
        strategy_name = active_strategy.get('recommendation', {}).strategy_name
        active_strategy = None
        
        return {
            "success": True,
            "message": f"'{strategy_name}' 전략이 중지되었습니다",
            "trading_result": stop_result
        }
        
    except Exception as e:
        logger.error(f"자동거래 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=f"자동거래 중지 실패: {str(e)}")


@router.get("/trading-status")
async def get_trading_status():
    """자동거래 상태 조회"""
    try:
        global active_strategy
        
        if not active_strategy or 'trading_engine' not in active_strategy:
            return {
                "success": True,
                "is_trading": False,
                "message": "실행 중인 거래가 없습니다"
            }
        
        trading_engine = active_strategy['trading_engine']
        status = trading_engine.get_status()
        
        return {
            "success": True,
            "is_trading": True,
            "strategy": {
                "id": active_strategy['strategy_id'],
                "name": active_strategy['recommendation'].strategy_name,
                "type": active_strategy['recommendation'].strategy_type,
                "started_at": active_strategy['started_at'].isoformat()
            },
            "trading": status,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"거래 상태 조회 실패: {e}")
        return {
            "success": False,
            "message": f"상태 조회 실패: {str(e)}"
        }


@router.get("/old-stop-endpoint")
async def old_stop_autotrading_endpoint():
    """이전 엔드포인트 (하위 호환성)"""
    global active_strategy
    
    if active_strategy:
        strategy_name = active_strategy["recommendation"].strategy_name
        active_strategy = None
        
        return {
            "success": True,
            "message": f"오토트레이딩이 중지되었습니다 (전략: {strategy_name})",
            "timestamp": datetime.now()
        }
    else:
        return {
            "success": False,
            "message": "활성화된 전략이 없습니다",
            "timestamp": datetime.now()
        }