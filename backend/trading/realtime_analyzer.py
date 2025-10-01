"""
실시간 시장 분석기 (계층적 분석 시스템)
Tier 1: 거래량 급등 10개 (1초) - 핫한 기회
Tier 2: 핵심 코인 20개 (5초) - 안정적  
Tier 3: 시가총액 상위 70개 (30초) - 전체 시장
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime, timedelta
from collections import deque
import pandas as pd
import numpy as np

from services.bithumb_client import BithumbClient
from analysis.technical_indicators import TechnicalAnalyzer
from analysis.ml_signals import MLSignalGenerator


logger = logging.getLogger(__name__)


class RealtimeMarketAnalyzer:
    """실시간 시장 분석기 (계층적 분석)"""
    
    # 핵심 코인 (Tier 2 - 고정)
    CORE_COINS = [
        'BTC', 'ETH', 'XRP', 'ADA', 'SOL', 
        'DOT', 'DOGE', 'MATIC', 'LINK', 'UNI',
        'AVAX', 'ATOM', 'LTC', 'ETC', 'BCH',
        'NEAR', 'ALGO', 'MANA', 'SAND', 'AXS'
    ]
    
    def __init__(self):
        self.bithumb_client = BithumbClient()
        
        # 계층별 코인 목록 (동적 업데이트)
        self.tier1_coins: List[str] = []  # 거래량 급등
        self.tier2_coins: List[str] = self.CORE_COINS[:20]  # 핵심 코인
        self.tier3_coins: List[str] = []  # 시가총액 상위
        
        # 전체 코인 목록
        self.all_coins: Set[str] = set()
        
        # 실시간 가격 저장
        self.current_prices: Dict[str, float] = {}
        self.price_history: Dict[str, deque] = {}
        self.volume_24h: Dict[str, float] = {}
        
        # 캔들 데이터 캐시
        self.candles_cache: Dict[str, pd.DataFrame] = {}
        
        # 기술적 지표 캐시
        self.indicators_cache: Dict[str, Dict] = {}
        self.indicators_updated_at: Dict[str, datetime] = {}
        
        # ML 예측 캐시
        self.ml_signals_cache: Dict[str, Dict] = {}
        self.ml_updated_at: Dict[str, datetime] = {}
        
        # 태스크
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
        
        # 코인 목록 초기화
        await self._update_coin_tiers()
        
        # 계층별 가격 스트림 시작
        asyncio.create_task(self._tier1_price_stream())  # 1초
        asyncio.create_task(self._tier2_price_stream())  # 5초
        asyncio.create_task(self._tier3_price_stream())  # 30초
        
        # 주기적 작업 시작
        asyncio.create_task(self._periodic_indicator_update())  # 1분
        asyncio.create_task(self._periodic_ml_update())  # 5분
        asyncio.create_task(self._periodic_tier_update())  # 1시간 - 티어 재구성
        
        logger.info(f"✅ 계층적 실시간 분석 시작")
        logger.info(f"📊 Tier 1 (1초): {len(self.tier1_coins)}개")
        logger.info(f"💎 Tier 2 (5초): {len(self.tier2_coins)}개")
        logger.info(f"📈 Tier 3 (30초): {len(self.tier3_coins)}개")
    
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
    
    async def _update_coin_tiers(self):
        """코인 계층 업데이트 (거래량 기반 동적 선택)"""
        try:
            # 빗썸 전체 티커 조회
            all_tickers = await self.bithumb_client.get_ticker('ALL')
            
            if not all_tickers or 'data' not in all_tickers:
                logger.warning("전체 티커 조회 실패 - 기본 코인 사용")
                self.tier1_coins = ['BTC', 'ETH', 'XRP']
                self.tier2_coins = self.CORE_COINS[:20]
                self.tier3_coins = []
                return
            
            coin_data = []
            for symbol, data in all_tickers['data'].items():
                if symbol == 'date':
                    continue
                
                try:
                    volume_24h = float(data.get('units_traded_24H', 0))
                    price = float(data.get('closing_price', 0))
                    prev_price = float(data.get('opening_price', price))
                    
                    # 변동률 계산
                    change_pct = ((price - prev_price) / prev_price * 100) if prev_price > 0 else 0
                    
                    coin_data.append({
                        'symbol': symbol,
                        'volume_24h': volume_24h,
                        'price': price,
                        'change_pct': abs(change_pct),
                        'market_cap': volume_24h * price  # 간이 시가총액
                    })
                except:
                    continue
            
            # 정렬
            coin_data.sort(key=lambda x: x['volume_24h'], reverse=True)
            
            # Tier 1: 거래량 급등 상위 10개 (변동률 5% 이상 + 거래량 상위)
            surge_coins = [c for c in coin_data if c['change_pct'] > 5][:10]
            self.tier1_coins = [c['symbol'] for c in surge_coins] if surge_coins else [c['symbol'] for c in coin_data[:10]]
            
            # Tier 2: 핵심 코인 20개 (고정 리스트 사용)
            self.tier2_coins = self.CORE_COINS[:20]
            
            # Tier 3: 시가총액 상위 70개 (Tier 1, 2 제외)
            tier12_symbols = set(self.tier1_coins + self.tier2_coins)
            remaining = [c for c in coin_data if c['symbol'] not in tier12_symbols]
            remaining.sort(key=lambda x: x['market_cap'], reverse=True)
            self.tier3_coins = [c['symbol'] for c in remaining[:70]]
            
            # 전체 코인 목록 업데이트
            self.all_coins = set(self.tier1_coins + self.tier2_coins + self.tier3_coins)
            
            # 가격 히스토리 초기화
            for symbol in self.all_coins:
                if symbol not in self.price_history:
                    self.price_history[symbol] = deque(maxlen=200)
            
            logger.info(f"🔥 Tier 1 (거래량 급등): {self.tier1_coins}")
            logger.info(f"💎 Tier 2 (핵심 코인): {len(self.tier2_coins)}개")
            logger.info(f"📊 Tier 3 (시총 상위): {len(self.tier3_coins)}개")
            
        except Exception as e:
            logger.error(f"코인 티어 업데이트 오류: {e}")
            # 기본값 설정
            self.tier1_coins = ['BTC', 'ETH', 'XRP']
            self.tier2_coins = self.CORE_COINS[:20]
            self.tier3_coins = []
    
    async def _periodic_tier_update(self):
        """1시간마다 코인 티어 재구성"""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # 1시간
                logger.info("🔄 코인 티어 재구성 중...")
                await self._update_coin_tiers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"티어 업데이트 오류: {e}")
    
    async def _tier1_price_stream(self):
        """Tier 1: 거래량 급등 코인 (1초마다)"""
        while self.is_running:
            try:
                for symbol in self.tier1_coins:
                    try:
                        await self._update_price(symbol)
                    except Exception as e:
                        logger.error(f"{symbol} T1 가격 조회 오류: {e}")
                
                await asyncio.sleep(1)  # 1초
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tier 1 스트림 오류: {e}")
    
    async def _tier2_price_stream(self):
        """Tier 2: 핵심 코인 (5초마다)"""
        while self.is_running:
            try:
                for symbol in self.tier2_coins:
                    try:
                        await self._update_price(symbol)
                    except Exception as e:
                        logger.error(f"{symbol} T2 가격 조회 오류: {e}")
                
                await asyncio.sleep(5)  # 5초
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tier 2 스트림 오류: {e}")
    
    async def _tier3_price_stream(self):
        """Tier 3: 시가총액 상위 (30초마다)"""
        while self.is_running:
            try:
                # 배치 처리 (10개씩)
                for i in range(0, len(self.tier3_coins), 10):
                    batch = self.tier3_coins[i:i+10]
                    
                    for symbol in batch:
                        try:
                            await self._update_price(symbol)
                        except Exception as e:
                            logger.error(f"{symbol} T3 가격 조회 오류: {e}")
                    
                    await asyncio.sleep(0.5)  # 배치 간 0.5초 대기
                
                await asyncio.sleep(30)  # 30초
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Tier 3 스트림 오류: {e}")
    
    async def _update_price(self, symbol: str):
        """단일 코인 가격 업데이트"""
        ticker = await self.bithumb_client.get_ticker(symbol)
        price = float(ticker['closing_price'])
        volume = float(ticker.get('units_traded_24H', 0))
        
        # 현재 가격 업데이트
        self.current_prices[symbol] = price
        self.volume_24h[symbol] = volume
        
        # 가격 히스토리 저장
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=200)
            
        self.price_history[symbol].append({
            'price': price,
            'timestamp': datetime.now(),
            'volume': volume
        })
    
    async def _periodic_indicator_update(self):
        """1분마다 기술적 지표 재계산 (계층별)"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # 1분 대기
                
                # Tier 1 코인 우선 처리 (가장 중요)
                for symbol in self.tier1_coins:
                    await self._update_indicators(symbol)
                
                # Tier 2 코인
                for symbol in self.tier2_coins:
                    if symbol not in self.tier1_coins:  # 중복 방지
                        await self._update_indicators(symbol)
                
                # Tier 3 코인 (5분에 1번만)
                current_minute = datetime.now().minute
                if current_minute % 5 == 0:  # 5분마다
                    for symbol in self.tier3_coins:
                        if symbol not in self.tier1_coins and symbol not in self.tier2_coins:
                            await self._update_indicators(symbol)
                
                logger.info(f"📊 지표 업데이트 완료: T1({len(self.tier1_coins)}) + T2({len(self.tier2_coins)}) + T3({len(self.tier3_coins) if current_minute % 5 == 0 else 0})")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"지표 업데이트 오류: {e}")
    
    async def _update_indicators(self, symbol: str):
        """단일 코인 지표 업데이트"""
        try:
            # 최근 200개 캔들 조회
            candles = await self._get_candles(symbol, count=200)
            
            if candles is not None and len(candles) > 50:
                # 기술적 지표 계산
                indicators = self.technical_analyzer.calculate_all(candles)
                
                # 캐시 업데이트
                self.indicators_cache[symbol] = indicators
                self.indicators_updated_at[symbol] = datetime.now()
                
        except Exception as e:
            logger.error(f"{symbol} 지표 계산 오류: {e}")
    
    async def _periodic_ml_update(self):
        """5분마다 ML 예측 재실행 (계층별)"""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # 5분 대기
                
                if not self.ml_generator:
                    continue
                
                # Tier 1 + Tier 2만 ML 예측 (리소스 절약)
                priority_coins = list(set(self.tier1_coins + self.tier2_coins))
                
                for symbol in priority_coins:
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
                            
                            if ml_signal.get('signal_type') != 'HOLD':
                                logger.info(f"🤖 {symbol} ML 신호: {ml_signal.get('signal_type')} (신뢰도: {ml_signal.get('confidence', 0):.1%})")
                            
                    except Exception as e:
                        logger.error(f"{symbol} ML 예측 오류: {e}")
                
                logger.info(f"🤖 ML 업데이트 완료: {len(priority_coins)}개 코인")
                
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
            'ml_updated_at': self.ml_updated_at.get(symbol),
            'tier': self._get_coin_tier(symbol),
            'volume_24h': self.volume_24h.get(symbol, 0)
        }
    
    def _get_coin_tier(self, symbol: str) -> int:
        """코인의 티어 반환"""
        if symbol in self.tier1_coins:
            return 1
        elif symbol in self.tier2_coins:
            return 2
        elif symbol in self.tier3_coins:
            return 3
        return 0
    
    def get_top_opportunities(self, limit: int = 10) -> List[Dict]:
        """거래 기회 상위 N개 반환"""
        opportunities = []
        
        for symbol in self.all_coins:
            ml_signal = self.get_ml_signal(symbol)
            
            if ml_signal.get('signal_type') in ['BUY', 'SELL']:
                opportunities.append({
                    'symbol': symbol,
                    'signal': ml_signal.get('signal_type'),
                    'confidence': ml_signal.get('confidence', 0),
                    'strength': ml_signal.get('strength', 0),
                    'price': self.get_current_price(symbol),
                    'tier': self._get_coin_tier(symbol),
                    'volume_24h': self.volume_24h.get(symbol, 0)
                })
        
        # 신뢰도 * 강도로 정렬
        opportunities.sort(
            key=lambda x: x['confidence'] * x['strength'] * (1.5 if x['tier'] == 1 else 1.0),
            reverse=True
        )
        
        return opportunities[:limit]
    
    def get_tier_status(self) -> Dict:
        """티어 상태 정보 반환"""
        return {
            'tier1': {
                'name': '거래량 급등',
                'coins': self.tier1_coins,
                'count': len(self.tier1_coins),
                'interval': '1초'
            },
            'tier2': {
                'name': '핵심 코인',
                'coins': self.tier2_coins,
                'count': len(self.tier2_coins),
                'interval': '5초'
            },
            'tier3': {
                'name': '시가총액 상위',
                'count': len(self.tier3_coins),
                'interval': '30초'
            },
            'total_coins': len(self.all_coins)
        }


# 전역 인스턴스
_analyzer_instance: Optional[RealtimeMarketAnalyzer] = None


def get_realtime_analyzer() -> RealtimeMarketAnalyzer:
    """실시간 분석기 인스턴스 반환 (싱글톤)"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        _analyzer_instance = RealtimeMarketAnalyzer()
    
    return _analyzer_instance

