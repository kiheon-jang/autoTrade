"""
빗썸 API 클라이언트 구현 (수정된 버전)
빗썸 공식 API 문서에 따른 정확한 엔드포인트 사용
"""
import asyncio
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Any
import httpx
import websockets
from urllib.parse import urlencode

from core.config import settings


class BithumbAPIError(Exception):
    """빗썸 API 에러"""
    pass


class BithumbClient:
    """빗썸 API 클라이언트 (수정된 버전)"""
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        self.api_key = api_key or settings.BITHUMB_API_KEY
        self.secret_key = secret_key or settings.BITHUMB_SECRET_KEY
        self.base_url = settings.BITHUMB_BASE_URL
        self.ws_url = settings.BITHUMB_WS_URL
        
        # HTTP 클라이언트 설정
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        # Rate Limit 관리
        self.last_request_time = 0
        self.min_request_interval = 1.0 / 90  # 초당 90회 제한
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    def _wait_for_rate_limit(self):
        """Rate Limit 대기"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def _generate_signature(self, endpoint: str, nonce: str, params: Dict[str, Any] = None) -> str:
        """빗썸 API 1.0 공식 서명 생성 방식"""
        if not self.secret_key:
            raise BithumbAPIError("Secret key is required for private API")
        
        if params is None:
            params = {}
        
        # 1. URL 인코딩된 파라미터 문자열 생성 (endpoint 추가하지 않음)
        post_data = urlencode(params) if params else ""
        
        # 2. 서명 메시지 생성 (구분자: chr(0) = null character)
        message = endpoint + chr(0) + post_data + chr(0) + nonce
        
        # 4. 빗썸 공식 서명 생성 (공식 샘플 방식)
        import base64
        
        # 1단계: HMAC-SHA512 암호화 (Secret Key는 원본 문자열 사용)
        h = hmac.new(
            self.secret_key.encode('utf-8'),  # 원본 문자열 그대로 사용
            message.encode('utf-8'),
            hashlib.sha512
        )
        
        # 2단계: hexdigest()로 16진수 문자열 생성
        hex_output = h.hexdigest()
        
        # 3단계: 16진수 문자열을 UTF-8로 인코딩 후 Base64 인코딩
        utf8_hex_output = hex_output.encode('utf-8')
        api_sign = base64.b64encode(utf8_hex_output).decode('utf-8')
        
        return api_sign
    
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                          is_private: bool = False) -> Dict[str, Any]:
        """HTTP 요청 실행"""
        self._wait_for_rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        if is_private:
            if not self.api_key or not self.secret_key:
                raise BithumbAPIError("API key and secret key are required for private API")
            
            # Private API를 위한 nonce 생성 (밀리초 단위)
            nonce = str(int(time.time() * 1000))
            
            # 서명 생성 (빗썸 공식 방식)
            signature = self._generate_signature(endpoint, nonce, params)
            
            # 헤더 설정 (빗썸 공식 방식)
            headers.update({
                "Api-Key": self.api_key,
                "Api-Sign": signature,
                "Api-Nonce": nonce
            })
            
            # POST 데이터에 endpoint 포함하지 않음 (빗썸 공식 방식)
            if params is None:
                params = {}
        
        try:
            if method.upper() == "GET":
                response = await self.http_client.get(url, params=params, headers=headers)
            else:
                response = await self.http_client.post(url, data=params, headers=headers)
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            raise BithumbAPIError(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            raise BithumbAPIError(f"Request error: {str(e)}")
    
    # Public API 메서드들 (빗썸 공식 API 문서 기준)
    async def get_ticker(self, currency: str = "ALL") -> Dict[str, Any]:
        """현재가 정보 조회"""
        endpoint = f"/public/ticker/{currency}"
        return await self._make_request("GET", endpoint)
    
    async def get_orderbook(self, currency: str) -> Dict[str, Any]:
        """호가 정보 조회"""
        endpoint = f"/public/orderbook/{currency}"
        return await self._make_request("GET", endpoint)
    
    async def get_transaction_history(self, currency: str) -> Dict[str, Any]:
        """체결 내역 조회"""
        endpoint = f"/public/transaction_history/{currency}"
        return await self._make_request("GET", endpoint)
    
    async def get_candlestick(self, symbol: str, interval: str = '1m') -> Dict[str, Any]:
        """캔들스틱(차트) 데이터 조회
        
        Args:
            symbol: 코인 심볼 (예: 'BTC_KRW')
            interval: 간격 ('1m', '3m', '5m', '10m', '30m', '1h', '6h', '12h', '24h')
        """
        endpoint = f"/public/candlestick/{symbol}/{interval}"
        return await self._make_request("GET", endpoint)
    
    # Private API 메서드들
    async def get_balance(self) -> Dict[str, Any]:
        """잔고 조회"""
        endpoint = "/info/balance"
        return await self._make_request("POST", endpoint, is_private=True)
    
    async def place_order(self, order_currency: str, payment_currency: str, 
                         units: str, price: str, type_: str) -> Dict[str, Any]:
        """주문하기"""
        endpoint = "/trade/place"
        params = {
            "order_currency": order_currency,
            "payment_currency": payment_currency,
            "units": units,
            "price": price,
            "type": type_  # bid(매수) 또는 ask(매도)
        }
        return await self._make_request("POST", endpoint, params, is_private=True)
    
    async def cancel_order(self, order_id: str, order_currency: str, 
                          payment_currency: str, type_: str) -> Dict[str, Any]:
        """주문 취소"""
        endpoint = "/trade/cancel"
        params = {
            "order_id": order_id,
            "order_currency": order_currency,
            "payment_currency": payment_currency,
            "type": type_
        }
        return await self._make_request("POST", endpoint, params, is_private=True)
    
    async def get_orders(self, order_currency: str = "ALL", 
                        payment_currency: str = "KRW") -> Dict[str, Any]:
        """주문 조회"""
        endpoint = "/info/orders"
        params = {
            "order_currency": order_currency,
            "payment_currency": payment_currency
        }
        return await self._make_request("POST", endpoint, params, is_private=True)
    
    async def get_user_transactions(self, order_currency: str = "ALL", 
                                   payment_currency: str = "KRW") -> Dict[str, Any]:
        """체결 내역 조회"""
        endpoint = "/info/user_transactions"
        params = {
            "order_currency": order_currency,
            "payment_currency": payment_currency
        }
        return await self._make_request("POST", endpoint, params, is_private=True)
    
    # WebSocket 연결 관리 (빗썸 WebSocket API 사용)
    async def connect_websocket(self, symbols: List[str], callback):
        """WebSocket 연결 및 실시간 데이터 수신"""
        try:
            # 빗썸 WebSocket URL 구성
            ws_url = f"{self.ws_url}?symbols={','.join(symbols)}"
            
            async with websockets.connect(ws_url) as websocket:
                print(f"WebSocket 연결 성공: {ws_url}")
                
                # 메시지 수신 루프
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        await callback(data)
                    except json.JSONDecodeError:
                        print(f"Invalid JSON received: {message}")
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    async def get_realtime_ticker(self, symbols: List[str], duration: int = 60):
        """실시간 티커 데이터 수집"""
        ticker_data = []
        
        async def ticker_callback(data):
            ticker_data.append({
                "timestamp": time.time(),
                "data": data
            })
        
        # 지정된 시간 동안 데이터 수집
        try:
            await asyncio.wait_for(
                self.connect_websocket(symbols, ticker_callback),
                timeout=duration
            )
        except asyncio.TimeoutError:
            print(f"WebSocket 데이터 수집 완료 ({duration}초)")
        
        return ticker_data


# 싱글톤 인스턴스
bithumb_client = BithumbClient()
