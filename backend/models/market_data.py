"""
시장 데이터 관련 데이터베이스 모델 (TimescaleDB용)
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Index
from sqlalchemy.sql import func
from datetime import datetime
from core.database import TimescaleBase as Base


class Ticker(Base):
    """실시간 시세 데이터 모델 (TimescaleDB)"""
    __tablename__ = "tickers"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)  # BTC_KRW
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 시세 정보
    opening_price = Column(Float, nullable=False)
    closing_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    
    # 거래량 정보
    volume = Column(Float, nullable=False)
    value = Column(Float, nullable=False)  # 거래대금
    
    # 변동률
    change_24h = Column(Float, nullable=False)
    change_rate_24h = Column(Float, nullable=False)
    
    # 호가 정보
    bid_price = Column(Float, nullable=True)
    ask_price = Column(Float, nullable=True)
    spread = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<Ticker(symbol='{self.symbol}', price={self.closing_price}, time='{self.timestamp}')>"


class OrderBook(Base):
    """호가창 데이터 모델 (TimescaleDB)"""
    __tablename__ = "orderbooks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 매수 호가 (JSON 배열)
    bids = Column(Text, nullable=False)  # [{"price": 1000000, "quantity": 0.1}, ...]
    
    # 매도 호가 (JSON 배열)
    asks = Column(Text, nullable=False)  # [{"price": 1001000, "quantity": 0.1}, ...]
    
    # 호가창 통계
    bid_volume = Column(Float, nullable=True)
    ask_volume = Column(Float, nullable=True)
    spread = Column(Float, nullable=True)
    mid_price = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<OrderBook(symbol='{self.symbol}', time='{self.timestamp}')>"


class Transaction(Base):
    """체결 내역 데이터 모델 (TimescaleDB)"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 체결 정보
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    value = Column(Float, nullable=False)  # price * quantity
    
    # 체결 방향
    side = Column(String(10), nullable=False)  # buy, sell
    
    # 빗썸 체결 ID
    bithumb_tx_id = Column(String(100), unique=True, index=True, nullable=True)
    
    def __repr__(self):
        return f"<Transaction(symbol='{self.symbol}', price={self.price}, quantity={self.quantity})>"


class Candle(Base):
    """캔들 데이터 모델 (TimescaleDB)"""
    __tablename__ = "candles"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)  # 1m, 5m, 15m, 1h, 4h, 1d
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # OHLCV 데이터
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    
    # 추가 지표
    vwap = Column(Float, nullable=True)  # 거래량 가중 평균가
    rsi = Column(Float, nullable=True)  # RSI 지표
    macd = Column(Float, nullable=True)  # MACD 지표
    bollinger_upper = Column(Float, nullable=True)  # 볼린저 밴드 상단
    bollinger_middle = Column(Float, nullable=True)  # 볼린저 밴드 중단
    bollinger_lower = Column(Float, nullable=True)  # 볼린저 밴드 하단
    
    def __repr__(self):
        return f"<Candle(symbol='{self.symbol}', timeframe='{self.timeframe}', close={self.close_price})>"


class TechnicalIndicator(Base):
    """기술적 지표 데이터 모델 (TimescaleDB)"""
    __tablename__ = "technical_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 이동평균선
    ma_5 = Column(Float, nullable=True)
    ma_10 = Column(Float, nullable=True)
    ma_20 = Column(Float, nullable=True)
    ma_50 = Column(Float, nullable=True)
    ma_100 = Column(Float, nullable=True)
    ma_200 = Column(Float, nullable=True)
    
    # 지수이동평균선
    ema_8 = Column(Float, nullable=True)
    ema_13 = Column(Float, nullable=True)
    ema_21 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    ema_200 = Column(Float, nullable=True)
    
    # 오실레이터
    rsi_14 = Column(Float, nullable=True)
    stochastic_k = Column(Float, nullable=True)
    stochastic_d = Column(Float, nullable=True)
    macd_line = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    cci_20 = Column(Float, nullable=True)
    
    # 변동성 지표
    atr_14 = Column(Float, nullable=True)
    bollinger_upper = Column(Float, nullable=True)
    bollinger_middle = Column(Float, nullable=True)
    bollinger_lower = Column(Float, nullable=True)
    keltner_upper = Column(Float, nullable=True)
    keltner_middle = Column(Float, nullable=True)
    keltner_lower = Column(Float, nullable=True)
    
    # 볼륨 지표
    volume_ma_20 = Column(Float, nullable=True)
    obv = Column(Float, nullable=True)  # On Balance Volume
    vwap = Column(Float, nullable=True)  # Volume Weighted Average Price
    
    def __repr__(self):
        return f"<TechnicalIndicator(symbol='{self.symbol}', timeframe='{self.timeframe}', rsi={self.rsi_14})>"


# TimescaleDB 하이퍼테이블 설정을 위한 인덱스
Index('idx_tickers_symbol_time', Ticker.symbol, Ticker.timestamp)
Index('idx_orderbooks_symbol_time', OrderBook.symbol, OrderBook.timestamp)
Index('idx_transactions_symbol_time', Transaction.symbol, Transaction.timestamp)
Index('idx_candles_symbol_timeframe_time', Candle.symbol, Candle.timeframe, Candle.timestamp)
Index('idx_indicators_symbol_timeframe_time', TechnicalIndicator.symbol, TechnicalIndicator.timeframe, TechnicalIndicator.timestamp)
