"""
주문 관련 데이터베이스 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON, Enum
from sqlalchemy.sql import func
from datetime import datetime
import enum
from core.database import Base


class OrderType(str, enum.Enum):
    """주문 타입"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, enum.Enum):
    """주문 상태"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"


class Order(Base):
    """주문 모델"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_id = Column(Integer, nullable=True, index=True)
    
    # 빗썸 주문 정보
    bithumb_order_id = Column(String(100), unique=True, index=True, nullable=True)
    
    # 주문 기본 정보
    symbol = Column(String(20), nullable=False, index=True)  # BTC_KRW
    order_type = Column(Enum(OrderType), nullable=False)
    order_side = Column(String(10), nullable=False)  # bid(매수), ask(매도)
    
    # 주문 수량 및 가격
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=True)  # 지정가 주문의 경우
    filled_quantity = Column(Float, default=0.0)
    remaining_quantity = Column(Float, nullable=False)
    
    # 주문 상태
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    
    # 수수료
    fee = Column(Float, default=0.0)
    fee_currency = Column(String(10), default="KRW")
    
    # 체결 정보
    average_fill_price = Column(Float, nullable=True)
    total_filled_value = Column(Float, default=0.0)
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    filled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # 메모
    notes = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<Order(id={self.id}, symbol='{self.symbol}', type='{self.order_type}', status='{self.status}')>"


class Trade(Base):
    """체결 내역 모델"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_id = Column(Integer, nullable=True, index=True)
    
    # 빗썸 체결 정보
    bithumb_trade_id = Column(String(100), unique=True, index=True, nullable=True)
    
    # 체결 기본 정보
    symbol = Column(String(20), nullable=False, index=True)
    trade_side = Column(String(10), nullable=False)  # buy, sell
    
    # 체결 수량 및 가격
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    value = Column(Float, nullable=False)  # quantity * price
    
    # 수수료
    fee = Column(Float, default=0.0)
    fee_currency = Column(String(10), default="KRW")
    
    # 시간 정보
    trade_time = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Trade(id={self.id}, symbol='{self.symbol}', side='{self.trade_side}', price={self.price})>"


class Position(Base):
    """포지션 모델"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    strategy_id = Column(Integer, nullable=True, index=True)
    
    # 포지션 기본 정보
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # long, short
    
    # 포지션 수량 및 가격
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    
    # 손익 계산
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    
    # 리스크 관리
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    
    # 포지션 상태
    is_active = Column(Boolean, default=True)
    
    # 시간 정보
    opened_at = Column(DateTime(timezone=True), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Position(id={self.id}, symbol='{self.symbol}', side='{self.side}', quantity={self.quantity})>"


class Portfolio(Base):
    """포트폴리오 모델"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # 포트폴리오 기본 정보
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    # 자산 정보
    total_balance = Column(Float, default=0.0)
    available_balance = Column(Float, default=0.0)
    invested_balance = Column(Float, default=0.0)
    
    # 성과 지표
    total_return = Column(Float, default=0.0)
    daily_return = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    # 포트폴리오 구성 (JSON)
    holdings = Column(JSON, nullable=True)  # {symbol: {quantity, value, percentage}}
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_rebalanced = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Portfolio(id={self.id}, name='{self.name}', balance={self.total_balance})>"
