"""
실시간 시장 분석기 (WebSocket + 주기적 재계산)
업계 표준 방식: WebSocket 가격 수신 + 캔들 단위 지표 계산
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import pandas as pd
import numpy as np

from services.bithumb_client import BithumbClient
from analysis.technical_indicators import TechnicalAnalyzer
from analysis.ml_signals import MLSignalGenerator


logger = logging.getLogger(__name__)


class RealtimeMarketAnalyzer:
    """실시간 시장 분석기"""
    
    def __init__(self, symbols: List[str] = ['BTC', 'ETH', 'XRP']):
        self.symbols = symbols
        self.bithumb_client = BithumbClient()
        
        # 실시간 가격 저장 (WebSocket)
        self.current_prices: Dict[str, float] = {}
        self.price_history: Dict[str, deque] = {
            symbol: deque(maxlen=200) for symbol in symbols
        }
        
        # 캔들 데이터 캐시 (1분봉)
        self.candles_cache: Dict[str, pd.DataFrame] = {}
        
        # 기술적 지표 캐시
        self.indicators_cache: Dict[str, Dict] = {}
        self.indicators_updated_at: Dict[str, datetime] = {}
        
        # ML 예측 캐시
        self.ml_signals_cache: Dict[str, Dict] = {}
        self.ml_updated_at: Dict[str, datetime] = {}
        
        # WebSocket 태스크
        self.ws_task = None
        self.is_running = False
        
        # 분석기
        self.technical_analyzer = TechnicalAnalyzer()
        try:
            self.ml_generator = MLSignalGenerator()
        except:
            self.ml_generator = None
            logger.warning("ML 신호 생성기 초기화 실패 - ML 기능 비활성화")
    
    async def start(self):
        """실시간 분석 시작"""
        self.is_running = True
        
        # WebSocket 연결 시작
        self.ws_task = asyncio.create_task(self._websocket_price_stream())
        
        # 주기적 작업 시작
        asyncio.create_task(self._periodic_indicator_update())
        asyncio.create_task(self._periodic_ml_update())
        
        logger.info(f"✅ 실시간 분석 시작: {self.symbols}")
    
    async def stop(self):
        """실시간 분석 중지"""
        self.is_running = False
        
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
        
        logger.info("실시간 분석 중지")
    
    async def _websocket_price_stream(self):
        """WebSocket으로 실시간 가격 수신"""
        while self.is_running:
            try:
                # 빗썸은 WebSocket 대신 REST API 폴링 사용 (공식 제한)
                # 1초마다 가격 조회 (Rate Limit: 90/sec 이므로 안전)
                for symbol in self.symbols:
                    try:
                        ticker = await self.bithumb_client.get_ticker(symbol)
                        price = float(ticker['closing_price'])
                        
                        # 현재 가격 업데이트
                        self.current_prices[symbol] = price
                        
                        # 가격 히스토리 저장
                        self.price_history[symbol].append({
                            'price': price,
                            'timestamp': datetime.now(),
                            'volume': float(ticker.get('units_traded_24H', 0))
                        })
                        
                    except Exception as e:
                        logger.error(f"{symbol} 가격 조회 오류: {e}")
                
                await asyncio.sleep(1)  # 1초마다
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket 스트림 오류: {e}")
                await asyncio.sleep(5)
    
    async def _periodic_indicator_update(self):
        """1분마다 기술적 지표 재계산"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # 1분 대기
                
                for symbol in self.symbols:
                    try:
                        # 최근 200개 캔들 조회
                        candles = await self._get_candles(symbol, count=200)
                        
                        if candles is not None and len(candles) > 50:
                            # 기술적 지표 계산
                            indicators = self.technical_analyzer.calculate_all(candles)
                            
                            # 캐시 업데이트
                            self.indicators_cache[symbol] = indicators
                            self.indicators_updated_at[symbol] = datetime.now()
                            
                            logger.info(f"📊 {symbol} 지표 업데이트: RSI={indicators.get('rsi_14', 0):.2f}")
                            
                    except Exception as e:
                        logger.error(f"{symbol} 지표 계산 오류: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"지표 업데이트 오류: {e}")
    
    async def _periodic_ml_update(self):
        """5분마다 ML 예측 재실행"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # 5분 대기
                
                if not self.ml_generator:
                    continue
                
                for symbol in self.symbols:
                    try:
                        # 최근 데이터로 ML 예측
                        candles = await self._get_candles(symbol, count=100)
                        indicators = self.indicators_cache.get(symbol, {})
                        
                        if candles is not None and indicators:
                            # ML 신호 생성
                            ml_signal = self.ml_generator.generate_signal(candles, indicators)
                            
                            # 캐시 업데이트
                            self.ml_signals_cache[symbol] = ml_signal
                            self.ml_updated_at[symbol] = datetime.now()
                            
                            logger.info(f"🤖 {symbol} ML 신호 업데이트: {ml_signal.get('signal_type', 'HOLD')} (신뢰도: {ml_signal.get('confidence', 0):.1%})")
                            
                    except Exception as e:
                        logger.error(f"{symbol} ML 예측 오류: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"ML 업데이트 오류: {e}")
    
    async def _get_candles(self, symbol: str, count: int = 200) -> Optional[pd.DataFrame]:
        """캔들 데이터 조회 및 캐싱"""
        try:
            # 캔들 데이터 조회 (1분봉)
            candles_data = await self.bithumb_client.get_candlestick(
                symbol=symbol,
                interval='1m'
            )
            
            if not candles_data:
                return None
            
            # DataFrame 변환
            df = pd.DataFrame(candles_data)
            
            # 필요한 컬럼만 선택 및 타입 변환
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 최근 count개만 유지
            df = df.tail(count)
            
            # 캐시 업데이트
            self.candles_cache[symbol] = df
            
            return df
            
        except Exception as e:
            logger.error(f"{symbol} 캔들 조회 오류: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """현재 가격 조회 (실시간)"""
        return self.current_prices.get(symbol)
    
    def get_indicators(self, symbol: str) -> Dict:
        """최신 기술적 지표 조회 (1분마다 갱신)"""
        return self.indicators_cache.get(symbol, {})
    
    def get_ml_signal(self, symbol: str) -> Dict:
        """최신 ML 신호 조회 (5분마다 갱신)"""
        return self.ml_signals_cache.get(symbol, {
            'signal_type': 'HOLD',
            'confidence': 0.5,
            'strength': 0.5
        })
    
    def get_analysis(self, symbol: str) -> Dict:
        """종합 분석 데이터 조회"""
        return {
            'current_price': self.get_current_price(symbol),
            'indicators': self.get_indicators(symbol),
            'ml_signal': self.get_ml_signal(symbol),
            'indicators_updated_at': self.indicators_updated_at.get(symbol),
            'ml_updated_at': self.ml_updated_at.get(symbol)
        }


# 전역 인스턴스
_analyzer_instance: Optional[RealtimeMarketAnalyzer] = None


def get_realtime_analyzer(symbols: List[str] = ['BTC', 'ETH', 'XRP']) -> RealtimeMarketAnalyzer:
    """실시간 분석기 인스턴스 반환 (싱글톤)"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        _analyzer_instance = RealtimeMarketAnalyzer(symbols)
    
    return _analyzer_instance

