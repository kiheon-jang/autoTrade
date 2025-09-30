"""
기본 전략 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from enum import Enum


class StrategyType(Enum):
    """전략 타입"""
    SCALPING = "scalping"
    DAY_TRADING = "day_trading"
    SWING_TRADING = "swing_trading"
    LONG_TERM = "long_term"


class SignalType(Enum):
    """신호 타입"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


@dataclass
class TradingSignal:
    """거래 신호"""
    signal_type: SignalType
    strength: float  # 0.0 ~ 1.0
    confidence: float  # 0.0 ~ 1.0
    price: float
    quantity: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timestamp: datetime = None
    reason: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class StrategyConfig:
    """전략 설정"""
    name: str
    strategy_type: StrategyType
    parameters: Dict[str, Any]
    risk_per_trade: float = 2.0  # 2%
    max_positions: int = 5
    stop_loss_pct: float = 2.0  # 2%
    take_profit_pct: float = 4.0  # 4%
    enabled: bool = True


class BaseStrategy(ABC):
    """기본 전략 클래스"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.is_active = False
        self.positions = []
        self.trade_history = []
        self.performance_metrics = {}
    
    @abstractmethod
    def analyze(self, data: pd.DataFrame) -> List[TradingSignal]:
        """시장 데이터 분석 및 신호 생성"""
        pass
    
    @abstractmethod
    def should_enter_position(self, data: pd.DataFrame) -> bool:
        """포지션 진입 조건 확인"""
        pass
    
    @abstractmethod
    def should_exit_position(self, data: pd.DataFrame, position: Dict) -> bool:
        """포지션 청산 조건 확인"""
        pass
    
    def calculate_position_size(self, account_balance: float, price: float, risk_amount: float) -> float:
        """포지션 크기 계산"""
        if risk_amount <= 0 or price <= 0:
            return 0.0
        
        # 리스크 금액을 기반으로 포지션 크기 계산
        position_size = risk_amount / price
        return min(position_size, account_balance * 0.1)  # 최대 10% 리스크
    
    def calculate_stop_loss(self, entry_price: float, signal_type: SignalType) -> float:
        """손절가 계산"""
        if signal_type == SignalType.BUY:
            return entry_price * (1 - self.config.stop_loss_pct / 100)
        else:
            return entry_price * (1 + self.config.stop_loss_pct / 100)
    
    def calculate_take_profit(self, entry_price: float, signal_type: SignalType) -> float:
        """익절가 계산"""
        if signal_type == SignalType.BUY:
            return entry_price * (1 + self.config.take_profit_pct / 100)
        else:
            return entry_price * (1 - self.config.take_profit_pct / 100)
    
    def validate_signal(self, signal: TradingSignal, data: pd.DataFrame) -> bool:
        """신호 유효성 검증"""
        if not signal or not data.empty:
            return False
        
        # 기본 유효성 검사
        if signal.strength < 0.3 or signal.confidence < 0.3:
            return False
        
        # 가격 유효성 검사
        current_price = data['close'].iloc[-1]
        if abs(signal.price - current_price) / current_price > 0.05:  # 5% 이상 차이
            return False
        
        return True
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """성과 지표 계산"""
        if not self.trade_history:
            return {}
        
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for trade in self.trade_history if trade.get('pnl', 0) > 0)
        losing_trades = total_trades - winning_trades
        
        total_pnl = sum(trade.get('pnl', 0) for trade in self.trade_history)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / total_trades if total_trades > 0 else 0
        }
    
    def start(self):
        """전략 시작"""
        self.is_active = True
    
    def stop(self):
        """전략 중지"""
        self.is_active = False
    
    def reset(self):
        """전략 리셋"""
        self.positions = []
        self.trade_history = []
        self.performance_metrics = {}
