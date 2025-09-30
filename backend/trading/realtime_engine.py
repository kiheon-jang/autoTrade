"""
실시간 거래 엔진
기존 백테스팅 엔진을 확장하여 실시간 거래 기능 구현
"""
import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

from backtesting.backtest_engine import BacktestEngine, Trade
from strategies.strategy_manager import StrategyManager, StrategyInstance, StrategyStatus
from services.bithumb_client import BithumbClient, BithumbAPIError
from core.commission import CommissionCalculator, ExchangeType
from models.order import Order, OrderType, OrderStatus, OrderSide
from data.realtime_collector import RealtimeDataCollector


class TradingMode(Enum):
    """거래 모드"""
    SIMULATION = "simulation"  # 시뮬레이션
    LIVE = "live"             # 실제 거래
    PAPER = "paper"           # 페이퍼 트레이딩


@dataclass
class RealtimeTrade:
    """실시간 거래 정보"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: float
    price: float
    timestamp: datetime
    order_id: Optional[str] = None
    status: str = "pending"  # pending, filled, cancelled, error
    commission: float = 0.0
    net_amount: float = 0.0
    strategy_id: Optional[str] = None
    signal_strength: float = 0.0
    signal_confidence: float = 0.0


@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    side: str
    amount: float
    avg_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    entry_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)


class RealtimeTradingEngine:
    """실시간 거래 엔진"""
    
    def __init__(self, 
                 mode: TradingMode = TradingMode.SIMULATION,
                 initial_capital: float = 1000000,
                 commission_rate: float = 0.0015):
        self.mode = mode
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_calculator = CommissionCalculator()
        self.exchange = ExchangeType.BITHUMB
        
        # 거래 관련
        self.positions: Dict[str, Position] = {}
        self.trades: List[RealtimeTrade] = []
        self.orders: Dict[str, Order] = {}
        
        # 전략 관리
        self.strategy_manager = StrategyManager()
        self.active_strategies: List[str] = []
        
        # 데이터 수집
        self.data_collector = RealtimeDataCollector()
        self.current_data: Dict[str, pd.DataFrame] = {}
        
        # 콜백 함수들
        self.on_trade_callback: Optional[Callable] = None
        self.on_position_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
        # 로깅
        self.logger = logging.getLogger(__name__)
        
        # 실행 상태
        self.is_running = False
        self.last_update = datetime.now()
    
    async def start(self, symbols: List[str], strategies: List[str] = None):
        """실시간 거래 시작"""
        try:
            self.logger.info(f"실시간 거래 엔진 시작 - 모드: {self.mode.value}")
            
            # 활성 전략 설정
            if strategies:
                self.active_strategies = strategies
                for strategy_id in strategies:
                    self.strategy_manager.start_strategy(strategy_id)
            
            # 데이터 수집 시작
            await self.data_collector.start_collection(symbols, ['market'])
            
            # 실시간 거래 루프를 백그라운드에서 시작
            self.is_running = True
            asyncio.create_task(self._trading_loop())
            
            self.logger.info("실시간 거래 엔진이 백그라운드에서 시작되었습니다.")
            
        except Exception as e:
            self.logger.error(f"거래 엔진 시작 오류: {e}")
            if self.on_error_callback:
                await self.on_error_callback(e)
    
    async def stop(self):
        """실시간 거래 중지"""
        self.logger.info("실시간 거래 엔진 중지")
        self.is_running = False
        
        # 데이터 수집 중지
        await self.data_collector.stop_collection()
        
        # 모든 전략 중지
        for strategy_id in self.active_strategies:
            self.strategy_manager.stop_strategy(strategy_id)
    
    async def _trading_loop(self):
        """실시간 거래 루프"""
        while self.is_running:
            try:
                # 최신 데이터 수집
                await self._update_market_data()
                
                # 활성 전략 실행
                await self._execute_strategies()
                
                # 포지션 관리
                await self._manage_positions()
                
                # 주문 상태 확인
                await self._check_order_status()
                
                # 업데이트 시간 기록
                self.last_update = datetime.now()
                
                # 1초 대기
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"거래 루프 오류: {e}")
                if self.on_error_callback:
                    await self.on_error_callback(e)
                await asyncio.sleep(5)  # 오류 시 5초 대기
    
    async def _update_market_data(self):
        """시장 데이터 업데이트"""
        for symbol in self.data_collector.data_buffer.keys():
            latest_data = self.data_collector.get_latest_data(symbol)
            if latest_data:
                # 데이터를 DataFrame으로 변환하여 저장
                if symbol not in self.current_data:
                    self.current_data[symbol] = pd.DataFrame()
                
                # 새로운 데이터 추가
                new_row = pd.DataFrame([{
                    'timestamp': latest_data['timestamp'],
                    'open': latest_data['price'],
                    'high': latest_data['price'],
                    'low': latest_data['price'],
                    'close': latest_data['price'],
                    'volume': latest_data['volume']
                }])
                
                self.current_data[symbol] = pd.concat([self.current_data[symbol], new_row], ignore_index=True)
                
                # 최근 100개 데이터만 유지
                if len(self.current_data[symbol]) > 100:
                    self.current_data[symbol] = self.current_data[symbol].tail(100)
    
    async def _execute_strategies(self):
        """전략 실행"""
        for symbol, data in self.current_data.items():
            if data.empty or len(data) < 20:  # 충분한 데이터가 없으면 스킵
                continue
            
            # 인덱스를 datetime으로 설정
            data.index = pd.to_datetime(data['timestamp'])
            
            # 활성 전략 실행
            strategy_results = self.strategy_manager.execute_strategies(data)
            
            for strategy_id, signals in strategy_results.items():
                for signal in signals:
                    await self._process_signal(signal, symbol, strategy_id)
    
    async def _process_signal(self, signal, symbol: str, strategy_id: str):
        """신호 처리"""
        try:
            if signal.signal_type.value == 'buy':
                await self._place_buy_order(symbol, signal, strategy_id)
            elif signal.signal_type.value == 'sell':
                await self._place_sell_order(symbol, signal, strategy_id)
            elif signal.signal_type.value == 'close':
                await self._close_position(symbol, signal, strategy_id)
                
        except Exception as e:
            self.logger.error(f"신호 처리 오류: {e}")
            if self.on_error_callback:
                await self.on_error_callback(e)
    
    async def _place_buy_order(self, symbol: str, signal, strategy_id: str):
        """매수 주문"""
        if self.mode == TradingMode.SIMULATION:
            await self._simulate_buy_order(symbol, signal, strategy_id)
        else:
            await self._execute_live_buy_order(symbol, signal, strategy_id)
    
    async def _place_sell_order(self, symbol: str, signal, strategy_id: str):
        """매도 주문"""
        if self.mode == TradingMode.SIMULATION:
            await self._simulate_sell_order(symbol, signal, strategy_id)
        else:
            await self._execute_live_sell_order(symbol, signal, strategy_id)
    
    async def _simulate_buy_order(self, symbol: str, signal, strategy_id: str):
        """시뮬레이션 매수 주문"""
        # 수수료 계산
        commission = self.commission_calculator.calculate_commission(
            signal.quantity, signal.price, self.exchange
        )
        
        # 총 비용
        total_cost = signal.quantity * signal.price + commission
        
        # 자본 확인
        if total_cost > self.current_capital:
            self.logger.warning(f"자본 부족: 필요 {total_cost:,.0f}원, 보유 {self.current_capital:,.0f}원")
            return
        
        # 거래 생성
        trade = RealtimeTrade(
            id=f"trade_{len(self.trades) + 1}",
            symbol=symbol,
            side="buy",
            amount=signal.quantity,
            price=signal.price,
            timestamp=datetime.now(),
            status="filled",
            commission=commission,
            net_amount=signal.quantity,
            strategy_id=strategy_id,
            signal_strength=signal.strength,
            signal_confidence=signal.confidence
        )
        
        self.trades.append(trade)
        self.current_capital -= total_cost
        
        # 포지션 업데이트
        if symbol in self.positions:
            pos = self.positions[symbol]
            # 평균 단가 계산
            total_amount = pos.amount + signal.quantity
            total_value = (pos.amount * pos.avg_price) + (signal.quantity * signal.price)
            pos.avg_price = total_value / total_amount
            pos.amount = total_amount
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                side="long",
                amount=signal.quantity,
                avg_price=signal.price
            )
        
        self.logger.info(f"시뮬레이션 매수: {symbol} {signal.quantity:.6f} @ {signal.price:,.0f}원")
        
        # 콜백 호출
        if self.on_trade_callback:
            await self.on_trade_callback(trade)
    
    async def _simulate_sell_order(self, symbol: str, signal, strategy_id: str):
        """시뮬레이션 매도 주문"""
        if symbol not in self.positions or self.positions[symbol].amount <= 0:
            self.logger.warning(f"매도할 포지션이 없음: {symbol}")
            return
        
        pos = self.positions[symbol]
        sell_amount = min(signal.quantity, pos.amount)
        
        # 수수료 계산
        commission = self.commission_calculator.calculate_commission(
            sell_amount, signal.price, self.exchange
        )
        
        # 수익 계산
        gross_profit = sell_amount * (signal.price - pos.avg_price)
        net_profit = gross_profit - commission
        
        # 거래 생성
        trade = RealtimeTrade(
            id=f"trade_{len(self.trades) + 1}",
            symbol=symbol,
            side="sell",
            amount=sell_amount,
            price=signal.price,
            timestamp=datetime.now(),
            status="filled",
            commission=commission,
            net_amount=sell_amount,
            strategy_id=strategy_id,
            signal_strength=signal.strength,
            signal_confidence=signal.confidence
        )
        
        self.trades.append(trade)
        self.current_capital += (sell_amount * signal.price) - commission
        
        # 포지션 업데이트
        pos.amount -= sell_amount
        pos.realized_pnl += net_profit
        
        if pos.amount <= 0:
            del self.positions[symbol]
        
        self.logger.info(f"시뮬레이션 매도: {symbol} {sell_amount:.6f} @ {signal.price:,.0f}원 (수익: {net_profit:,.0f}원)")
        
        # 콜백 호출
        if self.on_trade_callback:
            await self.on_trade_callback(trade)
    
    async def _execute_live_buy_order(self, symbol: str, signal, strategy_id: str):
        """실제 매수 주문 실행"""
        try:
            async with BithumbClient() as client:
                # 빗썸 매수 주문
                order_result = await client.buy_market_order(
                    order_currency=symbol,
                    payment_currency="KRW",
                    units=signal.quantity
                )
                
                if order_result.get("status") == "0000":
                    order_id = order_result.get("order_id")
                    
                    # 주문 저장
                    order = Order(
                        id=order_id,
                        symbol=symbol,
                        side=OrderSide.BUY,
                        type=OrderType.MARKET,
                        amount=signal.quantity,
                        price=signal.price,
                        status=OrderStatus.PENDING,
                        created_at=datetime.now(),
                        strategy_id=strategy_id
                    )
                    
                    self.orders[order_id] = order
                    self.logger.info(f"실제 매수 주문: {symbol} {signal.quantity:.6f} (주문ID: {order_id})")
                
        except BithumbAPIError as e:
            self.logger.error(f"빗썸 매수 주문 오류: {e}")
            if self.on_error_callback:
                await self.on_error_callback(e)
    
    async def _execute_live_sell_order(self, symbol: str, signal, strategy_id: str):
        """실제 매도 주문 실행"""
        try:
            async with BithumbClient() as client:
                # 빗썸 매도 주문
                order_result = await client.sell_market_order(
                    order_currency=symbol,
                    payment_currency="KRW",
                    units=signal.quantity
                )
                
                if order_result.get("status") == "0000":
                    order_id = order_result.get("order_id")
                    
                    # 주문 저장
                    order = Order(
                        id=order_id,
                        symbol=symbol,
                        side=OrderSide.SELL,
                        type=OrderType.MARKET,
                        amount=signal.quantity,
                        price=signal.price,
                        status=OrderStatus.PENDING,
                        created_at=datetime.now(),
                        strategy_id=strategy_id
                    )
                    
                    self.orders[order_id] = order
                    self.logger.info(f"실제 매도 주문: {symbol} {signal.quantity:.6f} (주문ID: {order_id})")
                
        except BithumbAPIError as e:
            self.logger.error(f"빗썸 매도 주문 오류: {e}")
            if self.on_error_callback:
                await self.on_error_callback(e)
    
    async def _manage_positions(self):
        """포지션 관리"""
        for symbol, position in self.positions.items():
            # 미실현 손익 계산
            if symbol in self.current_data and not self.current_data[symbol].empty:
                current_price = self.current_data[symbol]['close'].iloc[-1]
                position.unrealized_pnl = position.amount * (current_price - position.avg_price)
                position.last_update = datetime.now()
    
    async def _check_order_status(self):
        """주문 상태 확인"""
        if self.mode == TradingMode.SIMULATION:
            return  # 시뮬레이션 모드에서는 주문 상태 확인 불필요
        
        for order_id, order in self.orders.items():
            if order.status == OrderStatus.PENDING:
                try:
                    async with BithumbClient() as client:
                        # 주문 상태 조회
                        order_info = await client.get_order_detail(
                            order_id=order_id,
                            order_currency=order.symbol,
                            payment_currency="KRW"
                        )
                        
                        if order_info.get("status") == "0000":
                            # 주문 체결 확인
                            if order_info.get("data", {}).get("order_status") == "Completed":
                                order.status = OrderStatus.FILLED
                                order.filled_at = datetime.now()
                                self.logger.info(f"주문 체결: {order_id}")
                
                except Exception as e:
                    self.logger.error(f"주문 상태 확인 오류: {e}")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """포트폴리오 요약"""
        total_value = self.current_capital
        
        # 포지션 가치 계산
        for symbol, position in self.positions.items():
            if symbol in self.current_data and not self.current_data[symbol].empty:
                current_price = self.current_data[symbol]['close'].iloc[-1]
                position_value = position.amount * current_price
                total_value += position_value
        
        # 수익률 계산
        total_return = (total_value - self.initial_capital) / self.initial_capital
        
        return {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_value": total_value,
            "total_return": total_return,
            "positions": len(self.positions),
            "trades": len(self.trades),
            "active_strategies": len(self.active_strategies),
            "last_update": self.last_update.isoformat()
        }
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """포지션 정보"""
        positions_info = {}
        
        for symbol, position in self.positions.items():
            current_price = 0
            if symbol in self.current_data and not self.current_data[symbol].empty:
                current_price = self.current_data[symbol]['close'].iloc[-1]
            
            positions_info[symbol] = {
                "side": position.side,
                "amount": position.amount,
                "avg_price": position.avg_price,
                "current_price": current_price,
                "unrealized_pnl": position.unrealized_pnl,
                "realized_pnl": position.realized_pnl,
                "entry_time": position.entry_time.isoformat(),
                "last_update": position.last_update.isoformat()
            }
        
        return positions_info
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """최근 거래 내역"""
        recent_trades = self.trades[-limit:] if self.trades else []
        
        return [{
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side,
            "amount": trade.amount,
            "price": trade.price,
            "timestamp": trade.timestamp.isoformat(),
            "status": trade.status,
            "commission": trade.commission,
            "strategy_id": trade.strategy_id,
            "signal_strength": trade.signal_strength,
            "signal_confidence": trade.signal_confidence
        } for trade in recent_trades]


# 전역 거래 엔진 인스턴스
trading_engine: Optional[RealtimeTradingEngine] = None

def get_trading_engine() -> Optional[RealtimeTradingEngine]:
    """전역 거래 엔진 인스턴스 반환"""
    return trading_engine

def set_trading_engine(engine: RealtimeTradingEngine):
    """전역 거래 엔진 인스턴스 설정"""
    global trading_engine
    trading_engine = engine
