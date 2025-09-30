"""
실시간 데이터 수집 시스템
"""
import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import websockets
import logging
from concurrent.futures import ThreadPoolExecutor
import time
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from services.bithumb_client import BithumbClient
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))


@dataclass
class MarketData:
    """시장 데이터"""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    volatility: float = 0.0


@dataclass
class NewsEvent:
    """뉴스 이벤트"""
    title: str
    content: str
    sentiment: str  # 'positive', 'negative', 'neutral'
    impact_score: float  # 0-1
    timestamp: datetime
    source: str
    symbols: List[str] = field(default_factory=list)


@dataclass
class SocialSentiment:
    """소셜 센티먼트"""
    symbol: str
    sentiment_score: float  # -1 to 1
    mention_count: int
    timestamp: datetime
    source: str  # 'twitter', 'reddit', 'telegram'


class RealtimeDataCollector:
    """실시간 데이터 수집기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.websocket_connections = {}
        self.data_buffer = {}
        self.subscribers = {}
        self.running = False
        # 환경 변수에서 API 키 로드
        api_key = os.getenv('BITHUMB_API_KEY')
        secret_key = os.getenv('BITHUMB_SECRET_KEY')
        
        if not api_key or not secret_key:
            self.logger.warning("빗썸 API 키가 설정되지 않았습니다. 공개 API만 사용 가능합니다.")
            self.bithumb_client = BithumbClient()
        else:
            self.bithumb_client = BithumbClient(api_key, secret_key)
        
        # API 엔드포인트
        self.bithumb_api = "https://api.bithumb.com/public"
        self.upbit_api = "https://api.upbit.com/v1"
        self.binance_api = "https://api.binance.com/api/v3"
        
        # 뉴스 소스
        self.news_sources = {
            'coindesk': 'https://www.coindesk.com/api/v1/news',
            'cointelegraph': 'https://cointelegraph.com/api/v1/news',
            'crypto_news': 'https://cryptonews.com/api/v1/news'
        }
        
        # 소셜 미디어 소스
        self.social_sources = {
            'twitter': 'https://api.twitter.com/2/tweets/search/recent',
            'reddit': 'https://www.reddit.com/r/cryptocurrency/hot.json',
            'telegram': 'https://api.telegram.org/bot'
        }
    
    async def start_collection(self, symbols: List[str], 
                             data_types: List[str] = None) -> None:
        """데이터 수집 시작"""
        if data_types is None:
            data_types = ['market', 'news', 'social']
        
        self.running = True
        self.symbols = symbols
        
        # 각 데이터 타입별 수집 태스크를 백그라운드에서 시작
        if 'market' in data_types:
            asyncio.create_task(self._collect_market_data())
        
        if 'news' in data_types:
            asyncio.create_task(self._collect_news_data())
        
        if 'social' in data_types:
            asyncio.create_task(self._collect_social_sentiment())
        
        # 데이터 수집이 시작되었음을 알림
        self.logger.info(f"데이터 수집 시작: {symbols}, 타입: {data_types}")
    
    async def _collect_market_data(self):
        """시장 데이터 수집"""
        while self.running:
            try:
                for symbol in self.symbols:
                    # 빗썸 데이터
                    try:
                        bithumb_data = await self._fetch_bithumb_data(symbol)
                        if bithumb_data:
                            await self._process_market_data(bithumb_data)
                    except Exception as e:
                        self.logger.warning(f"빗썸 데이터 수집 실패: {e}")
                    
                    # 업비트 데이터
                    try:
                        upbit_data = await self._fetch_upbit_data(symbol)
                        if upbit_data:
                            await self._process_market_data(upbit_data)
                    except Exception as e:
                        self.logger.warning(f"업비트 데이터 수집 실패: {e}")
                    
                    # 바이낸스 데이터
                    try:
                        binance_data = await self._fetch_binance_data(symbol)
                        if binance_data:
                            await self._process_market_data(binance_data)
                    except Exception as e:
                        self.logger.warning(f"바이낸스 데이터 수집 실패: {e}")
                
                await asyncio.sleep(1)  # 1초 간격
                
            except Exception as e:
                self.logger.error(f"시장 데이터 수집 오류: {e}")
                await asyncio.sleep(5)
    
    async def _fetch_bithumb_data(self, symbol: str) -> Optional[Dict]:
        """빗썸 데이터 수집"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.bithumb_api}/ticker/{symbol}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'exchange': 'bithumb',
                            'symbol': symbol,
                            'price': float(data['data']['closing_price']),
                            'volume': float(data['data']['acc_trade_value_24H']),
                            'timestamp': datetime.now()
                        }
        except Exception as e:
            self.logger.error(f"빗썸 데이터 수집 오류: {e}")
        return None
    
    async def _fetch_upbit_data(self, symbol: str) -> Optional[Dict]:
        """업비트 데이터 수집"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.upbit_api}/ticker"
                params = {'markets': f'KRW-{symbol}'}
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            ticker = data[0]
                            return {
                                'exchange': 'upbit',
                                'symbol': symbol,
                                'price': float(ticker['trade_price']),
                                'volume': float(ticker['acc_trade_volume_24h']),
                                'timestamp': datetime.now()
                            }
        except Exception as e:
            self.logger.error(f"업비트 데이터 수집 오류: {e}")
        return None
    
    async def _fetch_binance_data(self, symbol: str) -> Optional[Dict]:
        """바이낸스 데이터 수집"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.binance_api}/ticker/24hr"
                params = {'symbol': f'{symbol}USDT'}
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'exchange': 'binance',
                            'symbol': symbol,
                            'price': float(data['lastPrice']),
                            'volume': float(data['volume']),
                            'timestamp': datetime.now()
                        }
        except Exception as e:
            self.logger.error(f"바이낸스 데이터 수집 오류: {e}")
        return None
    
    async def _process_market_data(self, data: Dict):
        """시장 데이터 처리"""
        symbol = data['symbol']
        
        # 데이터 버퍼에 저장
        if symbol not in self.data_buffer:
            self.data_buffer[symbol] = []
        
        self.data_buffer[symbol].append(data)
        
        # 최근 100개 데이터만 유지
        if len(self.data_buffer[symbol]) > 100:
            self.data_buffer[symbol] = self.data_buffer[symbol][-100:]
        
        # 구독자에게 알림
        if symbol in self.subscribers:
            for callback in self.subscribers[symbol]:
                try:
                    await callback(data)
                except Exception as e:
                    self.logger.error(f"구독자 콜백 오류: {e}")
    
    async def _collect_news_data(self):
        """뉴스 데이터 수집"""
        while self.running:
            try:
                for source_name, source_url in self.news_sources.items():
                    news_items = await self._fetch_news_from_source(source_name, source_url)
                    for news in news_items:
                        await self._process_news_data(news)
                
                await asyncio.sleep(300)  # 5분 간격
                
            except Exception as e:
                self.logger.error(f"뉴스 데이터 수집 오류: {e}")
                await asyncio.sleep(60)
    
    async def _fetch_news_from_source(self, source: str, url: str) -> List[NewsEvent]:
        """뉴스 소스에서 데이터 수집"""
        news_items = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 소스별 파싱
                        if source == 'coindesk':
                            news_items = self._parse_coindesk_news(data)
                        elif source == 'cointelegraph':
                            news_items = self._parse_cointelegraph_news(data)
                        elif source == 'crypto_news':
                            news_items = self._parse_crypto_news(data)
        
        except Exception as e:
            self.logger.error(f"{source} 뉴스 수집 오류: {e}")
        
        return news_items
    
    def _parse_coindesk_news(self, data: Dict) -> List[NewsEvent]:
        """코인데스크 뉴스 파싱"""
        news_items = []
        
        for item in data.get('articles', []):
            sentiment = self._analyze_sentiment(item.get('title', '') + ' ' + item.get('description', ''))
            
            news_items.append(NewsEvent(
                title=item.get('title', ''),
                content=item.get('description', ''),
                sentiment=sentiment,
                impact_score=self._calculate_impact_score(item),
                timestamp=datetime.now(),
                source='coindesk',
                symbols=self._extract_symbols(item.get('title', '') + ' ' + item.get('description', ''))
            ))
        
        return news_items
    
    def _parse_cointelegraph_news(self, data: Dict) -> List[NewsEvent]:
        """코인텔레그래프 뉴스 파싱"""
        # 실제 API 구조에 맞게 구현
        return []
    
    def _parse_crypto_news(self, data: Dict) -> List[NewsEvent]:
        """크립토 뉴스 파싱"""
        # 실제 API 구조에 맞게 구현
        return []
    
    def _analyze_sentiment(self, text: str) -> str:
        """텍스트 센티먼트 분석"""
        # 간단한 키워드 기반 센티먼트 분석
        positive_keywords = ['bullish', 'moon', 'pump', 'surge', 'rally', 'breakthrough']
        negative_keywords = ['bearish', 'crash', 'dump', 'fall', 'decline', 'correction']
        
        text_lower = text.lower()
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text_lower)
        
        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _calculate_impact_score(self, news_item: Dict) -> float:
        """뉴스 영향도 점수 계산"""
        # 제목 길이, 키워드 중요도 등을 고려한 점수
        title = news_item.get('title', '')
        
        # 중요 키워드 가중치
        important_keywords = ['bitcoin', 'ethereum', 'regulation', 'adoption', 'partnership']
        keyword_score = sum(1 for keyword in important_keywords if keyword.lower() in title.lower())
        
        # 제목 길이 점수
        length_score = min(len(title) / 100, 1.0)
        
        return min((keyword_score * 0.3 + length_score * 0.7), 1.0)
    
    def _extract_symbols(self, text: str) -> List[str]:
        """텍스트에서 암호화폐 심볼 추출"""
        symbols = []
        common_symbols = ['BTC', 'ETH', 'XRP', 'ADA', 'DOT', 'LINK', 'UNI', 'AAVE']
        
        for symbol in common_symbols:
            if symbol in text.upper():
                symbols.append(symbol)
        
        return symbols
    
    async def _collect_social_sentiment(self):
        """소셜 센티먼트 수집"""
        while self.running:
            try:
                for symbol in self.symbols:
                    # 트위터 센티먼트
                    twitter_sentiment = await self._fetch_twitter_sentiment(symbol)
                    if twitter_sentiment:
                        await self._process_social_sentiment(twitter_sentiment)
                    
                    # 레딧 센티먼트
                    reddit_sentiment = await self._fetch_reddit_sentiment(symbol)
                    if reddit_sentiment:
                        await self._process_social_sentiment(reddit_sentiment)
                
                await asyncio.sleep(600)  # 10분 간격
                
            except Exception as e:
                self.logger.error(f"소셜 센티먼트 수집 오류: {e}")
                await asyncio.sleep(60)
    
    async def _fetch_twitter_sentiment(self, symbol: str) -> Optional[SocialSentiment]:
        """트위터 센티먼트 수집"""
        # 실제 트위터 API 연동 구현
        # 여기서는 모의 데이터 반환
        return SocialSentiment(
            symbol=symbol,
            sentiment_score=np.random.uniform(-1, 1),
            mention_count=np.random.randint(10, 1000),
            timestamp=datetime.now(),
            source='twitter'
        )
    
    async def _fetch_reddit_sentiment(self, symbol: str) -> Optional[SocialSentiment]:
        """레딧 센티먼트 수집"""
        # 실제 레딧 API 연동 구현
        # 여기서는 모의 데이터 반환
        return SocialSentiment(
            symbol=symbol,
            sentiment_score=np.random.uniform(-1, 1),
            mention_count=np.random.randint(5, 500),
            timestamp=datetime.now(),
            source='reddit'
        )
    
    async def _process_social_sentiment(self, sentiment: SocialSentiment):
        """소셜 센티먼트 처리"""
        # 구독자에게 알림
        if sentiment.symbol in self.subscribers:
            for callback in self.subscribers[sentiment.symbol]:
                try:
                    await callback(sentiment)
                except Exception as e:
                    self.logger.error(f"소셜 센티먼트 콜백 오류: {e}")
    
    def subscribe(self, symbol: str, callback: Callable):
        """데이터 구독"""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
    
    def unsubscribe(self, symbol: str, callback: Callable):
        """데이터 구독 해제"""
        if symbol in self.subscribers:
            try:
                self.subscribers[symbol].remove(callback)
            except ValueError:
                pass
    
    def get_latest_data(self, symbol: str, data_type: str = 'market') -> Optional[Any]:
        """최신 데이터 조회"""
        if symbol in self.data_buffer:
            if data_type == 'market':
                return self.data_buffer[symbol][-1] if self.data_buffer[symbol] else None
        return None
    
    async def get_bithumb_ticker(self, symbol: str) -> Optional[Dict]:
        """빗썸 티커 데이터 수집"""
        try:
            ticker_data = await self.bithumb_client.get_ticker(symbol)
            return ticker_data
        except Exception as e:
            self.logger.error(f"빗썸 티커 데이터 수집 실패: {e}")
            return None
    
    async def get_bithumb_orderbook(self, symbol: str) -> Optional[Dict]:
        """빗썸 호가 데이터 수집"""
        try:
            orderbook_data = await self.bithumb_client.get_orderbook(symbol)
            return orderbook_data
        except Exception as e:
            self.logger.error(f"빗썸 호가 데이터 수집 실패: {e}")
            return None
    
    async def get_bithumb_balance(self) -> Optional[Dict]:
        """빗썸 잔고 조회"""
        try:
            balance_data = await self.bithumb_client.get_balance()
            return balance_data
        except Exception as e:
            self.logger.error(f"빗썸 잔고 조회 실패: {e}")
            return None
    
    def get_historical_data(self, symbol: str, hours: int = 24) -> List[Dict]:
        """과거 데이터 조회"""
        if symbol not in self.data_buffer:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [data for data in self.data_buffer[symbol] 
                if data.get('timestamp', datetime.min) >= cutoff_time]
    
    async def stop_collection(self):
        """데이터 수집 중지"""
        self.running = False
        
        # 웹소켓 연결 종료
        for ws in self.websocket_connections.values():
            await ws.close()
        
        self.websocket_connections.clear()
        self.logger.info("데이터 수집 중지됨")
