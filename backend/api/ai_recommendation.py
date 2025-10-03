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
user_preferences = {
    "trading_style": "balanced",  # conservative, balanced, aggressive
    "risk_tolerance": "medium",    # low, medium, high
    "max_position_size": 0.3,
    "stop_loss_pct": 0.05,
    "take_profit_pct": 0.10,
    "preferred_strategies": []
}


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
    trading_style: str = "balanced"  # conservative, balanced, aggressive
    risk_tolerance: str = "medium"  # low, medium, high


class UserPreferencesRequest(BaseModel):
    """사용자 투자 성향 설정 요청"""
    trading_style: str = "balanced"  # conservative, balanced, aggressive
    risk_tolerance: str = "medium"  # low, medium, high
    max_position_size: float = 0.3  # 최대 포지션 크기 (자본 대비)
    stop_loss_pct: float = 0.05  # 손절 비율
    take_profit_pct: float = 0.10  # 익절 비율
    preferred_strategies: List[str] = []  # 선호하는 전략 타입들


class TraditionalStrategyRequest(BaseModel):
    """전통적 전략 분석 요청"""
    symbols: List[str] = ["BTC", "ETH", "XRP"]
    timeframe: str = "1h"
    period_days: int = 30  # 분석 기간 (일)
    initial_capital: float = 1000000  # 초기 자본


class TraditionalStrategyResult(BaseModel):
    """전통적 전략 결과"""
    strategy_name: str
    strategy_type: str
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    avg_trade_return: float
    best_trade: float
    worst_trade: float
    volatility: float
    risk_level: str
    recommendation: str


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
        
        # 기존 거래가 실행 중이면 강력하게 중지
        if trading_engine.is_running:
            logger.info("🛑 AI 추천 전략: 기존 거래 강력 중지 시작")
            
            # 1단계: 정상 중지 시도
            try:
                await trading_engine.stop_strategy()
                logger.info("✅ AI 추천: 정상 중지 시도 완료")
            except Exception as e:
                logger.warning(f"⚠️ AI 추천: 정상 중지 실패: {e}")
            
            # 2단계: 강제 중지
            logger.info("🛑 AI 추천: 강제 중지 시작")
            trading_engine.is_running = False
            
            # 모든 태스크 강제 취소
            if hasattr(trading_engine, 'strategy_task') and trading_engine.strategy_task:
                trading_engine.strategy_task.cancel()
                logger.info("✅ AI 추천: strategy_task 취소")
            if hasattr(trading_engine, 'monitoring_task') and trading_engine.monitoring_task:
                trading_engine.monitoring_task.cancel()
                logger.info("✅ AI 추천: monitoring_task 취소")
            
            # 잠시 대기
            import asyncio
            await asyncio.sleep(2)
            
            # 3단계: 최종 확인 및 강제 정리
            if trading_engine.is_running:
                logger.warning("⚠️ AI 추천: 최종 강제 중지")
                trading_engine.is_running = False
                # 모든 포지션 강제 정리
                if hasattr(trading_engine, 'positions'):
                    trading_engine.positions.clear()
                if hasattr(trading_engine, 'trades'):
                    trading_engine.trades.clear()
            
            logger.info("✅ AI 추천: 기존 거래 강력 중지 완료")
        
        # StrategyManager에서도 기존 전략 중지
        try:
            from strategies.strategy_manager import strategy_manager
            active_strategies = strategy_manager.get_active_strategies()
            
            if active_strategies:
                logger.info(f"🛑 AI 추천: 기존 전략 중지: {active_strategies}")
                for strategy_id in active_strategies:
                    strategy_manager.stop_strategy(strategy_id)
                logger.info("✅ AI 추천: 기존 전략 중지 완료")
        except Exception as e:
            logger.error(f"AI 추천: 기존 전략 중지 실패: {e}")
        
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


@router.post("/user-preferences")
async def set_user_preferences(request: UserPreferencesRequest):
    """사용자 투자 성향 설정"""
    global user_preferences
    
    try:
        # 사용자 선호도 업데이트
        user_preferences.update({
            "trading_style": request.trading_style,
            "risk_tolerance": request.risk_tolerance,
            "max_position_size": request.max_position_size,
            "stop_loss_pct": request.stop_loss_pct,
            "take_profit_pct": request.take_profit_pct,
            "preferred_strategies": request.preferred_strategies
        })
        
        logger.info(f"사용자 선호도 업데이트: {user_preferences}")
        
        return {
            "success": True,
            "message": "사용자 투자 성향이 설정되었습니다",
            "preferences": user_preferences
        }
        
    except Exception as e:
        logger.error(f"사용자 선호도 설정 실패: {e}")
        raise HTTPException(status_code=500, detail=f"사용자 선호도 설정 실패: {str(e)}")


@router.get("/user-preferences")
async def get_user_preferences():
    """현재 사용자 투자 성향 조회"""
    return {
        "success": True,
        "preferences": user_preferences
    }


@router.post("/traditional-strategies")
async def analyze_traditional_strategies(request: TraditionalStrategyRequest):
    """전통적인 거래 전략들의 수익률 분석"""
    try:
        logger.info(f"전통적 전략 분석 시작: {request.symbols}, {request.period_days}일")
        
        # 시장 데이터 수집
        market_data = {}
        for symbol in request.symbols:
            data = await fetch_real_market_data(symbol, request.timeframe, request.period_days * 24)
            if not data.empty:
                market_data[symbol] = data
        
        if not market_data:
            raise HTTPException(status_code=400, detail="시장 데이터를 가져올 수 없습니다")
        
        # 각 전략별 수익률 계산
        results = []
        
        # 1. 스캘핑 전략
        scalping_result = await _calculate_scalping_strategy(market_data, request.initial_capital)
        results.append(scalping_result)
        
        # 2. 데이트레이딩 전략
        daytrading_result = await _calculate_daytrading_strategy(market_data, request.initial_capital)
        results.append(daytrading_result)
        
        # 3. 스윙트레이딩 전략
        swing_result = await _calculate_swing_strategy(market_data, request.initial_capital)
        results.append(swing_result)
        
        # 4. 롱텀 전략
        longterm_result = await _calculate_longterm_strategy(market_data, request.initial_capital)
        results.append(longterm_result)
        
        # 결과 정렬 (수익률 기준)
        results.sort(key=lambda x: x.total_return, reverse=True)
        
        return {
            "success": True,
            "strategies": results,
            "analysis_period": f"{request.period_days}일",
            "initial_capital": request.initial_capital,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"전통적 전략 분석 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"전통적 전략 분석 실패: {str(e)}")


@router.post("/stop-traditional-strategy")
async def stop_traditional_strategy():
    """전통적 전략 중지"""
    try:
        from trading.auto_trading_engine import get_trading_engine
        from strategies.strategy_manager import strategy_manager
        
        # AutoTradingEngine 중지
        trading_engine = get_trading_engine()
        if trading_engine and trading_engine.is_running:
            logger.info("🛑 전통적 전략 중지 시작")
            await trading_engine.stop_strategy()
            logger.info("✅ AutoTradingEngine 중지 완료")
        
        # StrategyManager에서 전통적 전략 중지
        active_strategies = strategy_manager.get_active_strategies()
        traditional_strategies = [s for s in active_strategies if s.startswith('traditional_')]
        
        if traditional_strategies:
            logger.info(f"🛑 StrategyManager에서 전통적 전략 중지: {traditional_strategies}")
            for strategy_id in traditional_strategies:
                strategy_manager.stop_strategy(strategy_id)
            logger.info("✅ StrategyManager 전통적 전략 중지 완료")
        
        return {
            "success": True,
            "message": "전통적 전략이 중지되었습니다"
        }
        
    except Exception as e:
        logger.error(f"전통적 전략 중지 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"전통적 전략 중지 실패: {str(e)}")

@router.post("/select-traditional-strategy")
async def select_traditional_strategy(strategy_type: str, symbols: List[str] = None, background_tasks: BackgroundTasks = None):
    """전통적 전략 선택 및 실행"""
    print(f"🚀 select_traditional_strategy API 호출됨: strategy_type={strategy_type}, symbols={symbols}")
    logger.info(f"🚀 select_traditional_strategy API 호출됨: strategy_type={strategy_type}, symbols={symbols}")
    try:
        # 기본 코인 설정 (전체 코인 대상)
        if symbols is None:
            try:
                # 빗썸에서 실제 거래 가능한 모든 코인 목록 가져오기
                from services.bithumb_client import BithumbClient
                bithumb_client = BithumbClient()
                
                # 빗썸 API에서 거래 가능한 코인 목록 조회
                ticker_data = await bithumb_client.get_ticker("ALL")
                if ticker_data and 'data' in ticker_data:
                    # KRW 기준 거래 가능한 코인들만 필터링
                    symbols = [coin for coin in ticker_data['data'].keys() 
                              if coin != 'date' and coin != 'BTC' and 'KRW' in str(ticker_data['data'][coin])]
                    # BTC는 별도로 추가
                    if 'BTC' not in symbols:
                        symbols.append('BTC')
                else:
                    # API 실패 시 기본 코인 목록 사용
                    symbols = [
                        'BTC', 'ETH', 'XRP', 'ADA', 'DOT', 'LINK', 'UNI', 'AAVE', 'SOL', 'MATIC',
                        'AVAX', 'ATOM', 'NEAR', 'FTM', 'ALGO', 'VET', 'ICP', 'FIL', 'TRX', 'LTC',
                        'BCH', 'ETC', 'XLM', 'HBAR', 'MANA', 'SAND', 'AXS', 'CHZ', 'ENJ', 'BAT'
                    ]
                
                logger.info(f"빗썸에서 거래 가능한 코인 {len(symbols)}개 확인: {symbols[:10]}...")
                
            except Exception as e:
                logger.error(f"빗썸 코인 목록 조회 실패: {e}")
                # 실패 시 기본 코인 목록 사용
                symbols = [
                    'BTC', 'ETH', 'XRP', 'ADA', 'DOT', 'LINK', 'UNI', 'AAVE', 'SOL', 'MATIC',
                    'AVAX', 'ATOM', 'NEAR', 'FTM', 'ALGO', 'VET', 'ICP', 'FIL', 'TRX', 'LTC',
                    'BCH', 'ETC', 'XLM', 'HBAR', 'MANA', 'SAND', 'AXS', 'CHZ', 'ENJ', 'BAT'
                ]
        
        logger.info(f"전통적 전략 선택: {strategy_type}, 대상 코인: {symbols}")
        # 전략별 설정
        strategy_configs = {
            "scalping": {
                "strategy_name": "스캘핑 전략",
                "strategy_type": "scalping",
                "execution_interval": 10,  # 10초
                "max_positions": 3,
                "stop_loss": 0.01,  # 1%
                "take_profit": 0.02,  # 2%
                "position_size": 0.1  # 10%
            },
            "daytrading": {
                "strategy_name": "데이트레이딩 전략",
                "strategy_type": "day_trading",
                "execution_interval": 300,  # 5분
                "max_positions": 2,
                "stop_loss": 0.03,  # 3%
                "take_profit": 0.05,  # 5%
                "position_size": 0.2  # 20%
            },
            "swing": {
                "strategy_name": "스윙트레이딩 전략",
                "strategy_type": "swing_trading",
                "execution_interval": 3600,  # 1시간
                "max_positions": 1,
                "stop_loss": 0.05,  # 5%
                "take_profit": 0.10,  # 10%
                "position_size": 0.3  # 30%
            },
            "longterm": {
                "strategy_name": "롱텀 전략",
                "strategy_type": "long_term",
                "execution_interval": 86400,  # 1일
                "max_positions": 1,
                "stop_loss": 0.10,  # 10%
                "take_profit": 0.20,  # 20%
                "position_size": 0.5  # 50%
            }
        }
        
        if strategy_type not in strategy_configs:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 전략 타입: {strategy_type}")
        
        config = strategy_configs[strategy_type]
        
        # 자동거래 엔진 가져오기
        from trading.auto_trading_engine import get_trading_engine
        
        trading_engine = get_trading_engine(
            trading_mode="paper",
            initial_capital=user_preferences.get("max_position_size", 0.3) * 1000000
        )
        
        # 기존 거래가 실행 중이면 강력하게 중지
        if trading_engine.is_running:
            logger.info("🛑 기존 거래 강력 중지 시작")
            
            # 1단계: 정상 중지 시도
            try:
                await trading_engine.stop_strategy()
                logger.info("✅ 정상 중지 시도 완료")
            except Exception as e:
                logger.warning(f"⚠️ 정상 중지 실패: {e}")
            
            # 2단계: 강제 중지
            logger.info("🛑 강제 중지 시작")
            trading_engine.is_running = False
            
            # 모든 태스크 강제 취소
            if hasattr(trading_engine, 'strategy_task') and trading_engine.strategy_task:
                trading_engine.strategy_task.cancel()
                logger.info("✅ strategy_task 취소")
            if hasattr(trading_engine, 'monitoring_task') and trading_engine.monitoring_task:
                trading_engine.monitoring_task.cancel()
                logger.info("✅ monitoring_task 취소")
            
            # 잠시 대기
            import asyncio
            await asyncio.sleep(2)
            
            # 3단계: 최종 확인 및 강제 정리
            if trading_engine.is_running:
                logger.warning("⚠️ 최종 강제 중지")
                trading_engine.is_running = False
                # 모든 포지션 강제 정리
                if hasattr(trading_engine, 'positions'):
                    trading_engine.positions.clear()
                if hasattr(trading_engine, 'trades'):
                    trading_engine.trades.clear()
            
            logger.info("✅ 기존 거래 강력 중지 완료")
        
        # StrategyManager에서도 기존 전통적 전략 중지
        try:
            from strategies.strategy_manager import strategy_manager
            active_strategies = strategy_manager.get_active_strategies()
            traditional_strategies = [s for s in active_strategies if s.startswith('traditional_')]
            
            if traditional_strategies:
                logger.info(f"🛑 기존 전통적 전략 중지: {traditional_strategies}")
                for strategy_id in traditional_strategies:
                    strategy_manager.stop_strategy(strategy_id)
                logger.info("✅ 기존 전통적 전략 중지 완료")
        except Exception as e:
            logger.error(f"기존 전통적 전략 중지 실패: {e}")
        
        # AutoTradingEngine 강제 중지 (기존 전통적 전략이 있는 경우)
        if trading_engine.is_running:
            logger.info("🛑 AutoTradingEngine 강제 중지")
            trading_engine.is_running = False
            if hasattr(trading_engine, 'strategy_task') and trading_engine.strategy_task:
                trading_engine.strategy_task.cancel()
            if hasattr(trading_engine, 'monitoring_task') and trading_engine.monitoring_task:
                trading_engine.monitoring_task.cancel()
            logger.info("✅ AutoTradingEngine 강제 중지 완료")
        
        # 전략 데이터 생성
        strategy_data = {
            "strategy_id": f"traditional_{strategy_type}",
            "strategy_name": config["strategy_name"],
            "strategy_type": config["strategy_type"],
            "confidence_score": 0.8,
            "technical_signals": {},
            "ml_signals": {},
            "pattern_analysis": {},
            "target_symbols": symbols  # 대상 코인 추가
        }
        
        # 전략 실행
        logger.info(f"🔄 trading_engine.start_strategy 호출 시작")
        logger.info(f"strategy_data: {strategy_data}")
        logger.info(f"config: {config}")
        
        try:
            trading_result = await trading_engine.start_strategy(strategy_data, config)
            logger.info(f"✅ trading_engine.start_strategy 성공: {trading_result}")
        except Exception as e:
            logger.error(f"❌ trading_engine.start_strategy 실패: {e}", exc_info=True)
            raise
        
        # 실시간 모니터링을 위한 전략 등록
        try:
            from strategies.strategy_manager import strategy_manager
            logger.info(f"전통적 전략 등록 시작: {strategy_type}")
            strategy_id = strategy_manager.register_strategy(
                strategy_id=f"traditional_{strategy_type}",
                strategy_name=config["strategy_name"],
                strategy_type=config["strategy_type"],
                is_active=True,
                target_symbols=symbols,
                config=config
            )
            logger.info(f"전통적 전략 등록 완료: {strategy_id}")
            logger.info(f"현재 활성 전략 수: {len(strategy_manager.get_active_strategies())}")
        except Exception as e:
            logger.error(f"전통적 전략 등록 실패: {e}", exc_info=True)
        
        return {
            "success": True,
            "message": f"{config['strategy_name']}이 실행되었습니다",
            "strategy": {
                "name": config["strategy_name"],
                "type": config["strategy_type"],
                "execution_interval": config["execution_interval"],
                "max_positions": config["max_positions"],
                "stop_loss": config["stop_loss"],
                "take_profit": config["take_profit"]
            },
            "trading": trading_result
        }
        
    except Exception as e:
        logger.error(f"전통적 전략 선택 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"전통적 전략 선택 실패: {str(e)}")


async def _calculate_scalping_strategy(market_data: Dict[str, pd.DataFrame], initial_capital: float) -> TraditionalStrategyResult:
    """스캘핑 전략 수익률 계산"""
    try:
        total_trades = 0
        winning_trades = 0
        trade_returns = []
        max_drawdown = 0
        current_drawdown = 0
        peak_capital = initial_capital
        current_capital = initial_capital
        
        for symbol, data in market_data.items():
            if len(data) < 100:  # 최소 데이터 요구량
                continue
                
            # RSI 기반 스캘핑 신호 생성
            rsi = technical_analyzer.calculate_rsi(data['close'], 14)
            
            for i in range(50, len(data)):  # 충분한 데이터 확보 후 시작
                if pd.isna(rsi.iloc[i]):
                    continue
                    
                current_price = data['close'].iloc[i]
                
                # 매수 신호: RSI < 30 (과매도)
                if rsi.iloc[i] < 30:
                    # 1% 수익률로 매도 (스캘핑)
                    target_price = current_price * 1.01
                    
                    # 다음 캔들에서 목표가 달성 확인
                    for j in range(i+1, min(i+10, len(data))):  # 최대 10캔들 내
                        if data['high'].iloc[j] >= target_price:
                            trade_return = 0.01  # 1% 수익
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            winning_trades += 1
                            break
                        elif data['low'].iloc[j] <= current_price * 0.995:  # 0.5% 손절
                            trade_return = -0.005
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            break
                
                # 매도 신호: RSI > 70 (과매수)
                elif rsi.iloc[i] > 70:
                    # 1% 수익률로 매도
                    target_price = current_price * 0.99
                    
                    for j in range(i+1, min(i+10, len(data))):
                        if data['low'].iloc[j] <= target_price:
                            trade_return = 0.01
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            winning_trades += 1
                            break
                        elif data['high'].iloc[j] >= current_price * 1.005:  # 0.5% 손절
                            trade_return = -0.005
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            break
                
                # 드로다운 계산
                if current_capital > peak_capital:
                    peak_capital = current_capital
                    current_drawdown = 0
                else:
                    current_drawdown = (peak_capital - current_capital) / peak_capital
                    max_drawdown = max(max_drawdown, current_drawdown)
        
        # 결과 계산
        total_return = (current_capital - initial_capital) / initial_capital
        annual_return = total_return * (365 / 30)  # 30일 기준 연환산
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0
        volatility = np.std(trade_returns) if trade_returns else 0
        sharpe_ratio = avg_trade_return / volatility if volatility > 0 else 0
        
        # 리스크 레벨 결정
        if max_drawdown > 0.1 or volatility > 0.05:
            risk_level = "high"
        elif max_drawdown > 0.05 or volatility > 0.03:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 추천 메시지
        if total_return > 0.1:
            recommendation = "높은 수익률을 보이는 스캘핑 전략입니다. 단, 높은 변동성을 고려해야 합니다."
        elif total_return > 0.05:
            recommendation = "적당한 수익률을 보이는 스캘핑 전략입니다."
        else:
            recommendation = "수익률이 낮은 스캘핑 전략입니다. 다른 전략을 고려해보세요."
        
        return TraditionalStrategyResult(
            strategy_name="스캘핑 전략",
            strategy_type="scalping",
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            avg_trade_return=avg_trade_return,
            best_trade=max(trade_returns) if trade_returns else 0,
            worst_trade=min(trade_returns) if trade_returns else 0,
            volatility=volatility,
            risk_level=risk_level,
            recommendation=recommendation
        )
        
    except Exception as e:
        logger.error(f"스캘핑 전략 계산 오류: {e}")
        return TraditionalStrategyResult(
            strategy_name="스캘핑 전략",
            strategy_type="scalping",
            total_return=0,
            annual_return=0,
            max_drawdown=0,
            sharpe_ratio=0,
            win_rate=0,
            total_trades=0,
            avg_trade_return=0,
            best_trade=0,
            worst_trade=0,
            volatility=0,
            risk_level="unknown",
            recommendation="계산 오류가 발생했습니다."
        )


async def _calculate_daytrading_strategy(market_data: Dict[str, pd.DataFrame], initial_capital: float) -> TraditionalStrategyResult:
    """데이트레이딩 전략 수익률 계산"""
    try:
        total_trades = 0
        winning_trades = 0
        trade_returns = []
        max_drawdown = 0
        current_drawdown = 0
        peak_capital = initial_capital
        current_capital = initial_capital
        
        for symbol, data in market_data.items():
            if len(data) < 200:  # 최소 데이터 요구량
                continue
                
            # MACD 기반 데이트레이딩 신호
            macd_data = technical_analyzer.calculate_macd(data['close'])
            macd = macd_data['macd']
            signal = macd_data['signal']
            histogram = macd_data['histogram']
            
            for i in range(100, len(data)):  # 충분한 데이터 확보 후 시작
                if pd.isna(macd.iloc[i]) or pd.isna(signal.iloc[i]):
                    continue
                    
                current_price = data['close'].iloc[i]
                
                # 매수 신호: MACD > Signal and Histogram > 0
                if macd.iloc[i] > signal.iloc[i] and histogram.iloc[i] > 0:
                    # 3% 수익률로 매도 (데이트레이딩)
                    target_price = current_price * 1.03
                    stop_loss_price = current_price * 0.97
                    
                    # 다음 캔들들에서 목표가 또는 손절가 달성 확인
                    for j in range(i+1, min(i+24, len(data))):  # 최대 24시간 (1일)
                        if data['high'].iloc[j] >= target_price:
                            trade_return = 0.03  # 3% 수익
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            winning_trades += 1
                            break
                        elif data['low'].iloc[j] <= stop_loss_price:
                            trade_return = -0.03  # 3% 손실
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            break
                
                # 매도 신호: MACD < Signal and Histogram < 0
                elif macd.iloc[i] < signal.iloc[i] and histogram.iloc[i] < 0:
                    # 3% 수익률로 매도
                    target_price = current_price * 0.97
                    stop_loss_price = current_price * 1.03
                    
                    for j in range(i+1, min(i+24, len(data))):
                        if data['low'].iloc[j] <= target_price:
                            trade_return = 0.03
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            winning_trades += 1
                            break
                        elif data['high'].iloc[j] >= stop_loss_price:
                            trade_return = -0.03
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            break
                
                # 드로다운 계산
                if current_capital > peak_capital:
                    peak_capital = current_capital
                    current_drawdown = 0
                else:
                    current_drawdown = (peak_capital - current_capital) / peak_capital
                    max_drawdown = max(max_drawdown, current_drawdown)
        
        # 결과 계산
        total_return = (current_capital - initial_capital) / initial_capital
        annual_return = total_return * (365 / 30)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0
        volatility = np.std(trade_returns) if trade_returns else 0
        sharpe_ratio = avg_trade_return / volatility if volatility > 0 else 0
        
        # 리스크 레벨 결정
        if max_drawdown > 0.15 or volatility > 0.08:
            risk_level = "high"
        elif max_drawdown > 0.08 or volatility > 0.05:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 추천 메시지
        if total_return > 0.15:
            recommendation = "높은 수익률을 보이는 데이트레이딩 전략입니다."
        elif total_return > 0.08:
            recommendation = "적당한 수익률을 보이는 데이트레이딩 전략입니다."
        else:
            recommendation = "수익률이 낮은 데이트레이딩 전략입니다. 다른 전략을 고려해보세요."
        
        return TraditionalStrategyResult(
            strategy_name="데이트레이딩 전략",
            strategy_type="daytrading",
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            avg_trade_return=avg_trade_return,
            best_trade=max(trade_returns) if trade_returns else 0,
            worst_trade=min(trade_returns) if trade_returns else 0,
            volatility=volatility,
            risk_level=risk_level,
            recommendation=recommendation
        )
        
    except Exception as e:
        logger.error(f"데이트레이딩 전략 계산 오류: {e}")
        return TraditionalStrategyResult(
            strategy_name="데이트레이딩 전략",
            strategy_type="daytrading",
            total_return=0,
            annual_return=0,
            max_drawdown=0,
            sharpe_ratio=0,
            win_rate=0,
            total_trades=0,
            avg_trade_return=0,
            best_trade=0,
            worst_trade=0,
            volatility=0,
            risk_level="unknown",
            recommendation="계산 오류가 발생했습니다."
        )


async def _calculate_swing_strategy(market_data: Dict[str, pd.DataFrame], initial_capital: float) -> TraditionalStrategyResult:
    """스윙트레이딩 전략 수익률 계산"""
    try:
        total_trades = 0
        winning_trades = 0
        trade_returns = []
        max_drawdown = 0
        current_drawdown = 0
        peak_capital = initial_capital
        current_capital = initial_capital
        
        for symbol, data in market_data.items():
            if len(data) < 200:
                continue
                
            # 이동평균선 기반 스윙트레이딩
            sma_20 = technical_analyzer.calculate_sma(data['close'], 20)
            sma_50 = technical_analyzer.calculate_sma(data['close'], 50)
            
            for i in range(100, len(data)):
                if pd.isna(sma_20.iloc[i]) or pd.isna(sma_50.iloc[i]):
                    continue
                    
                current_price = data['close'].iloc[i]
                
                # 매수 신호: SMA20 > SMA50 (골든크로스)
                if sma_20.iloc[i] > sma_50.iloc[i] and sma_20.iloc[i-1] <= sma_50.iloc[i-1]:
                    # 10% 수익률로 매도 (스윙트레이딩)
                    target_price = current_price * 1.10
                    stop_loss_price = current_price * 0.90
                    
                    # 다음 캔들들에서 목표가 또는 손절가 달성 확인
                    for j in range(i+1, min(i+168, len(data))):  # 최대 1주일
                        if data['high'].iloc[j] >= target_price:
                            trade_return = 0.10  # 10% 수익
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            winning_trades += 1
                            break
                        elif data['low'].iloc[j] <= stop_loss_price:
                            trade_return = -0.10  # 10% 손실
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            break
                
                # 매도 신호: SMA20 < SMA50 (데드크로스)
                elif sma_20.iloc[i] < sma_50.iloc[i] and sma_20.iloc[i-1] >= sma_50.iloc[i-1]:
                    # 10% 수익률로 매도
                    target_price = current_price * 0.90
                    stop_loss_price = current_price * 1.10
                    
                    for j in range(i+1, min(i+168, len(data))):
                        if data['low'].iloc[j] <= target_price:
                            trade_return = 0.10
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            winning_trades += 1
                            break
                        elif data['high'].iloc[j] >= stop_loss_price:
                            trade_return = -0.10
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            break
                
                # 드로다운 계산
                if current_capital > peak_capital:
                    peak_capital = current_capital
                    current_drawdown = 0
                else:
                    current_drawdown = (peak_capital - current_capital) / peak_capital
                    max_drawdown = max(max_drawdown, current_drawdown)
        
        # 결과 계산
        total_return = (current_capital - initial_capital) / initial_capital
        annual_return = total_return * (365 / 30)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0
        volatility = np.std(trade_returns) if trade_returns else 0
        sharpe_ratio = avg_trade_return / volatility if volatility > 0 else 0
        
        # 리스크 레벨 결정
        if max_drawdown > 0.20 or volatility > 0.10:
            risk_level = "high"
        elif max_drawdown > 0.10 or volatility > 0.06:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 추천 메시지
        if total_return > 0.20:
            recommendation = "높은 수익률을 보이는 스윙트레이딩 전략입니다."
        elif total_return > 0.10:
            recommendation = "적당한 수익률을 보이는 스윙트레이딩 전략입니다."
        else:
            recommendation = "수익률이 낮은 스윙트레이딩 전략입니다. 다른 전략을 고려해보세요."
        
        return TraditionalStrategyResult(
            strategy_name="스윙트레이딩 전략",
            strategy_type="swing",
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            avg_trade_return=avg_trade_return,
            best_trade=max(trade_returns) if trade_returns else 0,
            worst_trade=min(trade_returns) if trade_returns else 0,
            volatility=volatility,
            risk_level=risk_level,
            recommendation=recommendation
        )
        
    except Exception as e:
        logger.error(f"스윙트레이딩 전략 계산 오류: {e}")
        return TraditionalStrategyResult(
            strategy_name="스윙트레이딩 전략",
            strategy_type="swing",
            total_return=0,
            annual_return=0,
            max_drawdown=0,
            sharpe_ratio=0,
            win_rate=0,
            total_trades=0,
            avg_trade_return=0,
            best_trade=0,
            worst_trade=0,
            volatility=0,
            risk_level="unknown",
            recommendation="계산 오류가 발생했습니다."
        )


async def _calculate_longterm_strategy(market_data: Dict[str, pd.DataFrame], initial_capital: float) -> TraditionalStrategyResult:
    """롱텀 전략 수익률 계산"""
    try:
        total_trades = 0
        winning_trades = 0
        trade_returns = []
        max_drawdown = 0
        current_drawdown = 0
        peak_capital = initial_capital
        current_capital = initial_capital
        
        for symbol, data in market_data.items():
            if len(data) < 200:
                continue
                
            # 200일 이동평균선 기반 롱텀 전략
            sma_200 = technical_analyzer.calculate_sma(data['close'], 200)
            
            for i in range(200, len(data)):
                if pd.isna(sma_200.iloc[i]):
                    continue
                    
                current_price = data['close'].iloc[i]
                
                # 매수 신호: 가격 > SMA200 (상승 추세)
                if current_price > sma_200.iloc[i] and data['close'].iloc[i-1] <= sma_200.iloc[i-1]:
                    # 20% 수익률로 매도 (롱텀)
                    target_price = current_price * 1.20
                    stop_loss_price = current_price * 0.80
                    
                    # 다음 캔들들에서 목표가 또는 손절가 달성 확인
                    for j in range(i+1, len(data)):  # 전체 기간
                        if data['high'].iloc[j] >= target_price:
                            trade_return = 0.20  # 20% 수익
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            winning_trades += 1
                            break
                        elif data['low'].iloc[j] <= stop_loss_price:
                            trade_return = -0.20  # 20% 손실
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            break
                
                # 매도 신호: 가격 < SMA200 (하락 추세)
                elif current_price < sma_200.iloc[i] and data['close'].iloc[i-1] >= sma_200.iloc[i-1]:
                    # 20% 수익률로 매도
                    target_price = current_price * 0.80
                    stop_loss_price = current_price * 1.20
                    
                    for j in range(i+1, len(data)):
                        if data['low'].iloc[j] <= target_price:
                            trade_return = 0.20
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            winning_trades += 1
                            break
                        elif data['high'].iloc[j] >= stop_loss_price:
                            trade_return = -0.20
                            trade_returns.append(trade_return)
                            current_capital *= (1 + trade_return)
                            total_trades += 1
                            break
                
                # 드로다운 계산
                if current_capital > peak_capital:
                    peak_capital = current_capital
                    current_drawdown = 0
                else:
                    current_drawdown = (peak_capital - current_capital) / peak_capital
                    max_drawdown = max(max_drawdown, current_drawdown)
        
        # 결과 계산
        total_return = (current_capital - initial_capital) / initial_capital
        annual_return = total_return * (365 / 30)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        avg_trade_return = np.mean(trade_returns) if trade_returns else 0
        volatility = np.std(trade_returns) if trade_returns else 0
        sharpe_ratio = avg_trade_return / volatility if volatility > 0 else 0
        
        # 리스크 레벨 결정
        if max_drawdown > 0.30 or volatility > 0.15:
            risk_level = "high"
        elif max_drawdown > 0.15 or volatility > 0.08:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 추천 메시지
        if total_return > 0.30:
            recommendation = "높은 수익률을 보이는 롱텀 전략입니다."
        elif total_return > 0.15:
            recommendation = "적당한 수익률을 보이는 롱텀 전략입니다."
        else:
            recommendation = "수익률이 낮은 롱텀 전략입니다. 다른 전략을 고려해보세요."
        
        return TraditionalStrategyResult(
            strategy_name="롱텀 전략",
            strategy_type="longterm",
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            avg_trade_return=avg_trade_return,
            best_trade=max(trade_returns) if trade_returns else 0,
            worst_trade=min(trade_returns) if trade_returns else 0,
            volatility=volatility,
            risk_level=risk_level,
            recommendation=recommendation
        )
        
    except Exception as e:
        logger.error(f"롱텀 전략 계산 오류: {e}")
        return TraditionalStrategyResult(
            strategy_name="롱텀 전략",
            strategy_type="longterm",
            total_return=0,
            annual_return=0,
            max_drawdown=0,
            sharpe_ratio=0,
            win_rate=0,
            total_trades=0,
            avg_trade_return=0,
            best_trade=0,
            worst_trade=0,
            volatility=0,
            risk_level="unknown",
            recommendation="계산 오류가 발생했습니다."
        )


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
    """사용자 성향을 고려한 AI 추천 생성"""
    global user_preferences
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
        
        # 사용자 성향에 따른 임계값 조정
        trading_style = user_preferences.get("trading_style", "balanced")
        risk_tolerance = user_preferences.get("risk_tolerance", "medium")
        
        logger.info(f"시장 분석 결과: trend={market_trend}, volatility={volatility}, buy_signals={len(buy_signals)}, sell_signals={len(sell_signals)}")
        logger.info(f"사용자 성향: trading_style={trading_style}, risk_tolerance={risk_tolerance}")
        
        # 1. 상승장인 경우 - 사용자 성향에 따른 매수 전략
        if market_trend == "bullish" and len(buy_signals) > len(sell_signals):
            # 사용자 성향에 따른 전략 조정
            if trading_style == "aggressive":
                confidence = min(0.95, 0.8 + (len(buy_signals) * 0.1))
                expected_return = 0.20 + (btc_ml.get("confidence", 0.5) * 0.1)
                strategy_name = "상승장 공격적 매수 전략"
                risk_level = "high"
                validity_period = 180  # 3시간
            elif trading_style == "conservative":
                confidence = min(0.8, 0.6 + (len(buy_signals) * 0.05))
                expected_return = 0.10 + (btc_ml.get("confidence", 0.5) * 0.05)
                strategy_name = "상승장 안전 매수 전략"
                risk_level = "medium"
                validity_period = 240  # 4시간
            else:  # balanced
                confidence = min(0.9, 0.7 + (len(buy_signals) * 0.1))
                expected_return = 0.15 + (btc_ml.get("confidence", 0.5) * 0.1)
                strategy_name = "상승장 균형 매수 전략"
                risk_level = "high"
                validity_period = 120  # 2시간
            
            rec = StrategyRecommendation(
                strategy_id=f"bull_market_{trading_style}",
                strategy_name=strategy_name,
                strategy_type="momentum",
                confidence_score=confidence,
                expected_return=expected_return,
                risk_level=risk_level,
                market_conditions=market_analysis,
                reasoning=f"상승장 확인과 강한 매수 신호({len(buy_signals)}개)를 기반으로 한 {trading_style} 매수 전략",
                technical_signals=technical_signals,
                ml_signals=ml_predictions,
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason=f"현재 상승장이 확인되어 {trading_style} 매수 전략을 추천합니다",
                validity_period=validity_period,
                created_at=datetime.now()
            )
            recommendations.append(rec)
        
        # 2. 하락장인 경우 - 사용자 성향에 따른 방어 전략
        elif market_trend == "bearish" and len(sell_signals) > len(buy_signals) * 1.5:
            if trading_style == "aggressive":
                # 공격적 투자자는 하락장에서도 기회를 찾음
                rec = StrategyRecommendation(
                    strategy_id="bear_market_aggressive",
                    strategy_name="하락장 역발상 전략",
                    strategy_type="contrarian",
                    confidence_score=0.7,
                    expected_return=0.05,  # 하락장에서도 수익 추구
                    risk_level="high",
                    market_conditions=market_analysis,
                    reasoning=f"하락장에서도 기회를 찾는 공격적 전략 - {len(sell_signals)}개 매도 신호 무시",
                    technical_signals=technical_signals,
                    ml_signals=ml_predictions,
                    pattern_analysis=market_analysis.get("pattern_analysis", {}),
                    recommendation_reason=f"하락장이지만 공격적 투자 성향으로 역발상 기회를 추구합니다",
                    validity_period=120,  # 2시간
                    created_at=datetime.now()
                )
                recommendations.append(rec)
            else:
                # 보수적/균형 투자자는 방어적 전략
                rec = StrategyRecommendation(
                    strategy_id="bear_market_defensive",
                    strategy_name="하락장 방어 전략",
                    strategy_type="defensive",
                    confidence_score=0.8,
                    expected_return=-0.02,  # 손실 최소화
                    risk_level="low",
                    market_conditions=market_analysis,
                    reasoning=f"하락장 확인과 {len(sell_signals)}개의 매도 신호를 기반으로 한 방어적 전략",
                    technical_signals=technical_signals,
                    ml_signals=ml_predictions,
                    pattern_analysis=market_analysis.get("pattern_analysis", {}),
                    recommendation_reason=f"현재 하락장이 명확히 확인되어 리스크를 최소화하는 방어적 전략을 추천합니다",
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
        
        # 4. 중립적 시장 - 사용자 성향에 따른 전략
        else:
            # 매수 신호가 더 많은 경우
            if len(buy_signals) > len(sell_signals):
                if trading_style == "aggressive":
                    confidence = 0.8 + (btc_ml.get("confidence", 0.5) * 0.1)
                    expected_return = 0.15 + (btc_ml.get("strength", 0.5) * 0.05)
                    strategy_name = "중립장 공격적 스윙트레이딩"
                    risk_level = "high"
                elif trading_style == "conservative":
                    confidence = 0.6 + (btc_ml.get("confidence", 0.5) * 0.05)
                    expected_return = 0.08 + (btc_ml.get("strength", 0.5) * 0.03)
                    strategy_name = "중립장 안전 스윙트레이딩"
                    risk_level = "low"
                else:  # balanced
                    confidence = 0.7 + (btc_ml.get("confidence", 0.5) * 0.1)
                    expected_return = 0.12 + (btc_ml.get("strength", 0.5) * 0.05)
                    strategy_name = "중립장 균형 스윙트레이딩"
                    risk_level = "medium"
                
                rec = StrategyRecommendation(
                    strategy_id=f"swing_trading_{trading_style}",
                    strategy_name=strategy_name,
                    strategy_type="swing_trading",
                    confidence_score=confidence,
                    expected_return=expected_return,
                    risk_level=risk_level,
                    market_conditions=market_analysis,
                    reasoning=f"중립적 시장에서 매수 신호 우세({len(buy_signals)}개)를 활용한 {trading_style} 스윙트레이딩 전략",
                    technical_signals=technical_signals,
                    ml_signals=ml_predictions,
                    pattern_analysis=market_analysis.get("pattern_analysis", {}),
                    recommendation_reason=f"현재 중립적 시장에서 매수 신호가 우세하여 {trading_style} 스윙트레이딩이 적합합니다",
                    validity_period=180,  # 3시간
                    created_at=datetime.now()
                )
                recommendations.append(rec)
            
            # 매도 신호가 더 많은 경우
            elif len(sell_signals) > len(buy_signals):
                if trading_style == "aggressive":
                    # 공격적 투자자는 매도 신호가 많아도 기회를 찾음
                    rec = StrategyRecommendation(
                        strategy_id="contrarian_aggressive",
                        strategy_name="중립장 역발상 전략",
                        strategy_type="contrarian",
                        confidence_score=0.7,
                        expected_return=0.10,
                        risk_level="high",
                        market_conditions=market_analysis,
                        reasoning=f"중립적 시장에서 매도 신호 우세({len(sell_signals)}개)를 무시하고 기회를 찾는 공격적 전략",
                        technical_signals=technical_signals,
                        ml_signals=ml_predictions,
                        pattern_analysis=market_analysis.get("pattern_analysis", {}),
                        recommendation_reason=f"중립적 시장에서 매도 신호가 우세하지만 공격적 투자 성향으로 역발상 기회를 추구합니다",
                        validity_period=120,  # 2시간
                        created_at=datetime.now()
                    )
                    recommendations.append(rec)
                else:
                    # 보수적/균형 투자자는 신중한 접근
                    rec = StrategyRecommendation(
                        strategy_id="cautious_neutral",
                        strategy_name="신중한 중립 전략",
                        strategy_type="defensive",
                        confidence_score=0.6,
                        expected_return=0.05,
                        risk_level="low",
                        market_conditions=market_analysis,
                        reasoning=f"중립적 시장에서 매도 신호 우세({len(sell_signals)}개)를 고려한 신중한 전략",
                        technical_signals=technical_signals,
                        ml_signals=ml_predictions,
                        pattern_analysis=market_analysis.get("pattern_analysis", {}),
                        recommendation_reason=f"현재 중립적 시장에서 매도 신호가 우세하여 신중한 접근이 필요합니다",
                        validity_period=180,  # 3시간
                        created_at=datetime.now()
                    )
                    recommendations.append(rec)
            
            # 신호가 비슷한 경우 - 적응형 전략
            else:
                if trading_style == "aggressive":
                    strategy_name = "적응형 공격 전략"
                    confidence = 0.7
                    expected_return = 0.12
                    risk_level = "high"
                elif trading_style == "conservative":
                    strategy_name = "적응형 안전 전략"
                    confidence = 0.6
                    expected_return = 0.06
                    risk_level = "low"
                else:  # balanced
                    strategy_name = "적응형 균형 전략"
                    confidence = 0.65
                    expected_return = 0.08
                    risk_level = "medium"
                
                rec = StrategyRecommendation(
                    strategy_id=f"adaptive_{trading_style}",
                    strategy_name=strategy_name,
                    strategy_type="adaptive",
                    confidence_score=confidence,
                    expected_return=expected_return,
                    risk_level=risk_level,
                    market_conditions=market_analysis,
                    reasoning=f"중립적 시장에서 신호가 혼재된 상황에서 시장 변화에 적응하는 {trading_style} 전략",
                    technical_signals=technical_signals,
                    ml_signals=ml_predictions,
                    pattern_analysis=market_analysis.get("pattern_analysis", {}),
                    recommendation_reason=f"현재 중립적 시장에서 신호가 혼재되어 {trading_style} 적응형 전략이 적합합니다",
                    validity_period=180,  # 3시간
                    created_at=datetime.now()
                )
                recommendations.append(rec)
        
        # 5. DCA 전략 (사용자 성향에 따라 조정)
        if trading_style == "aggressive":
            # 공격적 투자자는 DCA보다는 기회 포착에 집중
            dca_rec = StrategyRecommendation(
                strategy_id="dca_aggressive",
                strategy_name="공격적 DCA 전략",
                strategy_type="dca",
                confidence_score=0.7,
                expected_return=0.12,  # 더 높은 수익 목표
                risk_level="medium",
                market_conditions=market_analysis,
                reasoning="공격적 투자 성향에 맞춰 더 큰 금액으로 DCA를 실행하는 전략",
                technical_signals=technical_signals,
                ml_signals=ml_predictions,
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason="공격적 투자 성향에 맞춰 더 큰 금액으로 DCA를 실행하여 수익을 극대화합니다",
                validity_period=1440,  # 24시간
                created_at=datetime.now()
            )
        elif trading_style == "conservative":
            # 보수적 투자자는 안전한 DCA
            dca_rec = StrategyRecommendation(
                strategy_id="dca_conservative",
                strategy_name="안전한 DCA 전략",
                strategy_type="dca",
                confidence_score=0.9,
                expected_return=0.05,  # 안전한 수익 목표
                risk_level="low",
                market_conditions=market_analysis,
                reasoning="보수적 투자 성향에 맞춰 작은 금액으로 안전하게 DCA를 실행하는 전략",
                technical_signals=technical_signals,
                ml_signals=ml_predictions,
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason="보수적 투자 성향에 맞춰 작은 금액으로 안전하게 DCA를 실행하여 리스크를 최소화합니다",
                validity_period=1440,  # 24시간
                created_at=datetime.now()
            )
        else:  # balanced
            # 균형 투자자는 표준 DCA
            dca_rec = StrategyRecommendation(
                strategy_id="dca_balanced",
                strategy_name="균형 DCA 전략",
                strategy_type="dca",
                confidence_score=0.85,
                expected_return=0.08,
                risk_level="low",
                market_conditions=market_analysis,
                reasoning="균형 투자 성향에 맞춰 적절한 금액으로 DCA를 실행하는 전략",
                technical_signals=technical_signals,
                ml_signals=ml_predictions,
                pattern_analysis=market_analysis.get("pattern_analysis", {}),
                recommendation_reason="균형 투자 성향에 맞춰 적절한 금액으로 DCA를 실행하여 안정적인 수익을 추구합니다",
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
    """시장 조건 판단 - 개선된 로직"""
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
        ml_total = 0
        for symbol, prediction in analysis.get("ml_predictions", {}).items():
            ml_total += 1
            if prediction["signal_type"] == "BUY":
                ml_bullish += 1
            elif prediction["signal_type"] == "SELL":
                ml_bearish += 1
        
        # 가중치 기반 종합 판단 (기술적 신호 70%, ML 예측 30%)
        technical_weight = 0.7
        ml_weight = 0.3
        
        # 기술적 신호 점수
        tech_score = 0.5  # 기본값 (중립)
        if total_signals > 0:
            tech_bullish_ratio = bullish_signals / total_signals
            tech_score = tech_bullish_ratio
        
        # ML 예측 점수
        ml_score = 0.5  # 기본값 (중립)
        if ml_total > 0:
            ml_bullish_ratio = ml_bullish / ml_total
            ml_score = ml_bullish_ratio
        
        # 종합 점수 계산
        overall_score = (tech_score * technical_weight) + (ml_score * ml_weight)
        
        # 트렌드 판단 (더 엄격한 기준 적용)
        if overall_score > 0.65:  # 65% 이상이면 상승장
            analysis["overall_trend"] = "bullish"
            analysis["market_sentiment"] = "positive"
        elif overall_score < 0.35:  # 35% 이하면 하락장
            analysis["overall_trend"] = "bearish"
            analysis["market_sentiment"] = "negative"
        else:  # 35-65% 사이면 중립
            analysis["overall_trend"] = "neutral"
            analysis["market_sentiment"] = "neutral"
        
        # 디버깅을 위한 로그 추가
        logger.info(f"시장 조건 판단: tech_score={tech_score:.3f}, ml_score={ml_score:.3f}, overall_score={overall_score:.3f}, trend={analysis['overall_trend']}")
        
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
        
        # 실시간 분석 현황 추가
        analyzer_status = trading_engine.market_analyzer.get_tier_status()
        recent_opportunities = trading_engine.market_analyzer.get_top_opportunities(limit=20)
        
        return {
            "success": True,
            "is_trading": True,
            "strategy": {
                "id": active_strategy['strategy_id'],
                "name": active_strategy['recommendation'].strategy_name,
                "type": active_strategy['recommendation'].strategy_type,
                "started_at": active_strategy['started_at'].isoformat()
            },
            "trading": {
                **status,
                "strategy_name": active_strategy['recommendation'].strategy_name,
                "strategy_type": active_strategy['recommendation'].strategy_type,
                "confidence": active_strategy['recommendation'].confidence_score,
                "risk_level": active_strategy['recommendation'].risk_level
            },
            "analysis": {
                "tiers": analyzer_status,
                "top_opportunities": recent_opportunities,
                "scanning_coins": analyzer_status['total_coins']
            },
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