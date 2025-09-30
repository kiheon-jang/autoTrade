"""
백테스팅 엔진 - 수수료 포함 수익 계산
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from core.commission import CommissionCalculator, ExchangeType


class TradeStatus(Enum):
    """거래 상태"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class Trade:
    """거래 정보"""
    id: str
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    entry_amount: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_amount: Optional[float] = None
    exit_time: Optional[datetime] = None
    status: TradeStatus = TradeStatus.OPEN
    entry_commission: float = 0.0
    exit_commission: float = 0.0
    gross_profit: float = 0.0
    net_profit: float = 0.0
    return_pct: float = 0.0
    hold_duration: Optional[timedelta] = None
    signal_strength: float = 0.0
    signal_confidence: float = 0.0
    exit_reason: str = ""


@dataclass
class BacktestResult:
    """백테스트 결과"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    avg_trade_return: float
    avg_winning_trade: float
    avg_losing_trade: float
    largest_win: float
    largest_loss: float
    avg_hold_duration: timedelta
    total_commission: float
    net_profit: float
    gross_profit: float
    commission_impact: float  # 수수료가 수익에 미친 영향


class BacktestEngine:
    """백테스팅 엔진"""
    
    def __init__(self, 
                 initial_capital: float = 1000000,
                 commission_rate: float = 0.0015,  # 빗썸 수수료율
                 exchange: ExchangeType = ExchangeType.BITHUMB):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_calculator = CommissionCalculator()
        self.exchange = exchange
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = [initial_capital]
        self.timestamps: List[datetime] = []
        
    def run_backtest(self, 
                    strategy: BaseStrategy, 
                    data: pd.DataFrame,
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> BacktestResult:
        """백테스트 실행"""
        # 데이터 필터링
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        if data.empty:
            raise ValueError("No data available for backtesting")
        
        # 백테스트 초기화
        self._reset_backtest()
        
        # 전략 시작
        strategy.start()
        
        # 백테스트 실행
        for i in range(len(data)):
            current_data = data.iloc[:i+1]
            current_time = data.index[i]
            
            # 전략 분석
            signals = strategy.analyze(current_data)
            
            # 신호 처리
            for signal in signals:
                self._process_signal(signal, current_data, current_time)
            
            # 기존 포지션 관리
            self._manage_positions(strategy, current_data, current_time)
            
            # 자본 업데이트
            self._update_capital()
            
            # 자본 곡선 기록
            self.equity_curve.append(self.current_capital)
            self.timestamps.append(current_time)
        
        # 전략 중지
        strategy.stop()
        
        # 결과 계산
        result = self._calculate_results()
        
        return result
    
    def _reset_backtest(self):
        """백테스트 초기화"""
        self.current_capital = self.initial_capital
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.timestamps = []
    
    def _process_signal(self, signal: TradingSignal, data: pd.DataFrame, timestamp: datetime):
        """신호 처리"""
        if signal.signal_type == SignalType.BUY:
            self._open_long_position(signal, data, timestamp)
        elif signal.signal_type == SignalType.SELL:
            self._open_short_position(signal, data, timestamp)
        elif signal.signal_type == SignalType.CLOSE:
            self._close_all_positions(signal, data, timestamp)
    
    def _open_long_position(self, signal: TradingSignal, data: pd.DataFrame, timestamp: datetime):
        """롱 포지션 진입"""
        if signal.quantity <= 0:
            return
        
        # 진입 수수료 계산
        entry_commission = self.commission_calculator.calculate_commission(
            signal.quantity, signal.price, self.exchange
        )
        
        # 총 진입 비용
        total_cost = signal.quantity * signal.price + entry_commission
        
        # 자본 확인
        if total_cost > self.current_capital:
            return  # 자본 부족
        
        # 거래 생성
        trade = Trade(
            id=f"trade_{len(self.trades) + 1}",
            symbol="BTC",  # 기본값
            side="long",
            entry_price=signal.price,
            entry_amount=signal.quantity,
            entry_time=timestamp,
            entry_commission=entry_commission,
            signal_strength=signal.strength,
            signal_confidence=signal.confidence
        )
        
        self.trades.append(trade)
        self.current_capital -= total_cost
    
    def _open_short_position(self, signal: TradingSignal, data: pd.DataFrame, timestamp: datetime):
        """숏 포지션 진입"""
        if signal.quantity <= 0:
            return
        
        # 진입 수수료 계산
        entry_commission = self.commission_calculator.calculate_commission(
            signal.quantity, signal.price, self.exchange
        )
        
        # 총 진입 비용
        total_cost = signal.quantity * signal.price + entry_commission
        
        # 자본 확인
        if total_cost > self.current_capital:
            return  # 자본 부족
        
        # 거래 생성
        trade = Trade(
            id=f"trade_{len(self.trades) + 1}",
            symbol="BTC",  # 기본값
            side="short",
            entry_price=signal.price,
            entry_amount=signal.quantity,
            entry_time=timestamp,
            entry_commission=entry_commission,
            signal_strength=signal.strength,
            signal_confidence=signal.confidence
        )
        
        self.trades.append(trade)
        self.current_capital -= total_cost
    
    def _close_all_positions(self, signal: TradingSignal, data: pd.DataFrame, timestamp: datetime):
        """모든 포지션 청산"""
        for trade in self.trades:
            if trade.status == TradeStatus.OPEN:
                self._close_position(trade, signal.price, timestamp, "manual_close")
    
    def _manage_positions(self, strategy: BaseStrategy, data: pd.DataFrame, timestamp: datetime):
        """포지션 관리"""
        for trade in self.trades:
            if trade.status != TradeStatus.OPEN:
                continue
            
            # 청산 조건 확인
            should_close = False
            exit_reason = ""
            
            # 손절/익절 확인
            if trade.side == "long":
                if data['close'].iloc[-1] <= trade.entry_price * 0.98:  # 2% 손절
                    should_close = True
                    exit_reason = "stop_loss"
                elif data['close'].iloc[-1] >= trade.entry_price * 1.04:  # 4% 익절
                    should_close = True
                    exit_reason = "take_profit"
            else:  # short
                if data['close'].iloc[-1] >= trade.entry_price * 1.02:  # 2% 손절
                    should_close = True
                    exit_reason = "stop_loss"
                elif data['close'].iloc[-1] <= trade.entry_price * 0.96:  # 4% 익절
                    should_close = True
                    exit_reason = "take_profit"
            
            # 전략 기반 청산 확인
            if not should_close:
                should_close = strategy.should_exit_position(data, {
                    'entry_price': trade.entry_price,
                    'entry_time': trade.entry_time,
                    'side': trade.side,
                    'stop_loss': trade.entry_price * 0.98,
                    'take_profit': trade.entry_price * 1.04
                })
                if should_close:
                    exit_reason = "strategy_exit"
            
            # 포지션 청산
            if should_close:
                self._close_position(trade, data['close'].iloc[-1], timestamp, exit_reason)
    
    def _close_position(self, trade: Trade, exit_price: float, timestamp: datetime, reason: str):
        """포지션 청산"""
        if trade.status != TradeStatus.OPEN:
            return
        
        # 청산 수수료 계산
        exit_commission = self.commission_calculator.calculate_commission(
            trade.entry_amount, exit_price, self.exchange
        )
        
        # 거래 정보 업데이트
        trade.exit_price = exit_price
        trade.exit_amount = trade.entry_amount
        trade.exit_time = timestamp
        trade.exit_commission = exit_commission
        trade.status = TradeStatus.CLOSED
        trade.exit_reason = reason
        trade.hold_duration = timestamp - trade.entry_time
        
        # 손익 계산
        if trade.side == "long":
            trade.gross_profit = (exit_price - trade.entry_price) * trade.entry_amount
        else:  # short
            trade.gross_profit = (trade.entry_price - exit_price) * trade.entry_amount
        
        # 순수익 계산 (수수료 차감)
        trade.net_profit = trade.gross_profit - trade.entry_commission - trade.exit_commission
        
        # 수익률 계산
        trade.return_pct = trade.net_profit / (trade.entry_price * trade.entry_amount) * 100
        
        # 자본 업데이트
        self.current_capital += trade.entry_amount * exit_price - trade.exit_commission
    
    def _update_capital(self):
        """자본 업데이트"""
        # 현재 자본 = 현금 + 미청산 포지션 가치
        total_capital = self.current_capital
        
        for trade in self.trades:
            if trade.status == TradeStatus.OPEN:
                # 미청산 포지션의 현재 가치 계산
                # 실제로는 현재 가격이 필요하지만, 여기서는 단순화
                pass
        
        self.current_capital = total_capital
    
    def _calculate_results(self) -> BacktestResult:
        """백테스트 결과 계산"""
        if not self.trades:
            return BacktestResult(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, total_return=0.0, annualized_return=0.0,
                max_drawdown=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
                profit_factor=0.0, avg_trade_return=0.0, avg_winning_trade=0.0,
                avg_losing_trade=0.0, largest_win=0.0, largest_loss=0.0,
                avg_hold_duration=timedelta(0), total_commission=0.0,
                net_profit=0.0, gross_profit=0.0, commission_impact=0.0
            )
        
        # 기본 통계
        total_trades = len(self.trades)
        winning_trades = sum(1 for trade in self.trades if trade.net_profit > 0)
        losing_trades = sum(1 for trade in self.trades if trade.net_profit < 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # 수익 통계
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        net_profit = self.current_capital - self.initial_capital
        gross_profit = sum(trade.gross_profit for trade in self.trades)
        total_commission = sum(trade.entry_commission + trade.exit_commission for trade in self.trades)
        
        # 수수료 영향 계산 수정
        if gross_profit > 0:
            commission_impact = total_commission / gross_profit
        elif gross_profit < 0:
            # 손실이 있는 경우 수수료가 손실을 더 크게 만드는 영향
            commission_impact = total_commission / abs(gross_profit) if gross_profit != 0 else 0.0
        else:
            # gross_profit이 0인 경우 (거래가 없거나 손익이 0)
            commission_impact = 0.0
        
        # 연환산 수익률
        if self.timestamps:
            duration = (self.timestamps[-1] - self.timestamps[0]).days / 365.25
            annualized_return = (1 + total_return) ** (1 / duration) - 1 if duration > 0 else 0.0
        else:
            annualized_return = 0.0
        
        # 최대 낙폭
        max_drawdown = self._calculate_max_drawdown()
        
        # 샤프 비율
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # 소르티노 비율
        sortino_ratio = self._calculate_sortino_ratio()
        
        # 수익 팩터
        profit_factor = self._calculate_profit_factor()
        
        # 거래 통계
        avg_trade_return = sum(trade.net_profit for trade in self.trades) / total_trades
        avg_winning_trade = sum(trade.net_profit for trade in self.trades if trade.net_profit > 0) / max(winning_trades, 1)
        avg_losing_trade = sum(trade.net_profit for trade in self.trades if trade.net_profit < 0) / max(losing_trades, 1)
        largest_win = max((trade.net_profit for trade in self.trades), default=0.0)
        largest_loss = min((trade.net_profit for trade in self.trades), default=0.0)
        
        # 평균 보유 기간
        closed_trades = [trade for trade in self.trades if trade.hold_duration]
        avg_hold_duration = sum((trade.hold_duration for trade in closed_trades), timedelta(0)) / len(closed_trades) if closed_trades else timedelta(0)
        
        return BacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_return=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            profit_factor=profit_factor,
            avg_trade_return=avg_trade_return,
            avg_winning_trade=avg_winning_trade,
            avg_losing_trade=avg_losing_trade,
            largest_win=largest_win,
            largest_loss=largest_loss,
            avg_hold_duration=avg_hold_duration,
            total_commission=total_commission,
            net_profit=net_profit,
            gross_profit=gross_profit,
            commission_impact=commission_impact
        )
    
    def _calculate_max_drawdown(self) -> float:
        """최대 낙폭 계산"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        peak = self.equity_curve[0]
        max_dd = 0.0
        
        for value in self.equity_curve:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _calculate_sharpe_ratio(self) -> float:
        """샤프 비율 계산"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(self.equity_curve)):
            ret = (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # 무위험 수익률을 0으로 가정
        sharpe_ratio = mean_return / std_return * np.sqrt(252)  # 연환산
        
        return sharpe_ratio
    
    def _calculate_sortino_ratio(self) -> float:
        """소르티노 비율 계산"""
        if len(self.equity_curve) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(self.equity_curve)):
            ret = (self.equity_curve[i] - self.equity_curve[i-1]) / self.equity_curve[i-1]
            returns.append(ret)
        
        if not returns:
            return 0.0
        
        mean_return = np.mean(returns)
        negative_returns = [r for r in returns if r < 0]
        
        if not negative_returns:
            return float('inf')
        
        downside_std = np.std(negative_returns)
        
        if downside_std == 0:
            return 0.0
        
        sortino_ratio = mean_return / downside_std * np.sqrt(252)  # 연환산
        
        return sortino_ratio
    
    def _calculate_profit_factor(self) -> float:
        """수익 팩터 계산"""
        gross_profit = sum(trade.gross_profit for trade in self.trades if trade.gross_profit > 0)
        gross_loss = abs(sum(trade.gross_profit for trade in self.trades if trade.gross_profit < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def get_trade_history(self) -> List[Dict]:
        """거래 내역 조회"""
        return [
            {
                'id': trade.id,
                'symbol': trade.symbol,
                'side': trade.side,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'entry_time': trade.entry_time.isoformat(),
                'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                'gross_profit': trade.gross_profit,
                'net_profit': trade.net_profit,
                'return_pct': trade.return_pct,
                'hold_duration': str(trade.hold_duration) if trade.hold_duration else None,
                'entry_commission': trade.entry_commission,
                'exit_commission': trade.exit_commission,
                'total_commission': trade.entry_commission + trade.exit_commission,
                'exit_reason': trade.exit_reason,
                'signal_strength': trade.signal_strength,
                'signal_confidence': trade.signal_confidence
            }
            for trade in self.trades
        ]
    
    def get_equity_curve(self) -> List[Dict]:
        """자본 곡선 조회"""
        return [
            {
                'timestamp': timestamp.isoformat(),
                'equity': equity,
                'return_pct': (equity - self.initial_capital) / self.initial_capital * 100
            }
            for timestamp, equity in zip(self.timestamps, self.equity_curve)
        ]
