"""
전략 관련 데이터베이스 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON
from sqlalchemy.sql import func
from datetime import datetime
from core.database import Base


class Strategy(Base):
    """전략 모델"""
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    strategy_type = Column(String(50), nullable=False)  # scalping, day_trading, swing_trading, long_term
    description = Column(Text, nullable=True)
    
    # 전략 파라미터 (JSON 형태로 저장)
    parameters = Column(JSON, nullable=False, default=dict)
    
    # 리스크 관리 설정
    risk_per_trade = Column(Float, default=2.0)  # 2%
    max_positions = Column(Integer, default=5)
    stop_loss_pct = Column(Float, default=2.0)   # 2%
    take_profit_pct = Column(Float, default=4.0) # 4%
    
    # 전략 상태
    is_active = Column(Boolean, default=False)
    is_backtesting = Column(Boolean, default=False)
    
    # 성과 지표
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_executed = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<Strategy(id={self.id}, name='{self.name}', type='{self.strategy_type}', active={self.is_active})>"


class StrategyExecution(Base):
    """전략 실행 로그 모델"""
    __tablename__ = "strategy_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # 실행 정보
    execution_type = Column(String(50), nullable=False)  # signal, order, error
    signal_data = Column(JSON, nullable=True)
    order_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # 시장 데이터 스냅샷
    market_data = Column(JSON, nullable=True)
    
    # 실행 결과
    success = Column(Boolean, default=True)
    execution_time = Column(Float, nullable=True)  # 실행 시간 (초)
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<StrategyExecution(id={self.id}, strategy_id={self.strategy_id}, type='{self.execution_type}')>"


class BacktestResult(Base):
    """백테스팅 결과 모델"""
    __tablename__ = "backtest_results"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # 백테스팅 설정
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    initial_capital = Column(Float, nullable=False)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    
    # 성과 지표
    total_return = Column(Float, default=0.0)
    annual_return = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    
    # 거래 통계
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    
    # 백테스팅 결과 데이터 (JSON)
    equity_curve = Column(JSON, nullable=True)
    trade_history = Column(JSON, nullable=True)
    monthly_returns = Column(JSON, nullable=True)
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    execution_time = Column(Float, nullable=True)  # 백테스팅 실행 시간 (초)
    
    def __repr__(self):
        return f"<BacktestResult(id={self.id}, strategy_id={self.strategy_id}, return={self.total_return:.2f}%)>"
