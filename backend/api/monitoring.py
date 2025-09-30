"""
모니터링 관련 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import pandas as pd
import numpy as np

from trading.realtime_engine import get_trading_engine
from strategies.strategy_manager import strategy_manager
from core.commission import CommissionCalculator, ExchangeType

router = APIRouter()


class DashboardData(BaseModel):
    """대시보드 데이터"""
    total_balance: float
    total_return: float
    daily_pnl: float
    active_strategies: int
    open_positions: int
    total_trades: int
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    last_update: str


class PerformanceMetrics(BaseModel):
    """성과 지표"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_trade_return: float
    commission_impact: float


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard():
    """대시보드 데이터 조회"""
    try:
        # 거래 엔진에서 포트폴리오 정보 가져오기
        trading_engine = get_trading_engine()
        if trading_engine and trading_engine.is_running:
            portfolio = trading_engine.get_portfolio_summary()
            positions = trading_engine.get_positions()
            trades = trading_engine.get_recent_trades(100)
            
            # 일일 수익률 계산
            daily_pnl = 0.0
            if trades:
                today = datetime.now().date()
                today_trades = [t for t in trades if datetime.fromisoformat(t['timestamp']).date() == today]
                daily_pnl = sum(t.get('net_profit', 0) for t in today_trades)
            
            # 승률 계산
            win_rate = 0.0
            if trades:
                winning_trades = [t for t in trades if t.get('net_profit', 0) > 0]
                win_rate = len(winning_trades) / len(trades) * 100
            
            # 샤프 비율 계산 (간단한 버전)
            sharpe_ratio = 0.0
            if len(trades) > 1:
                returns = [t.get('net_profit', 0) for t in trades]
                if np.std(returns) > 0:
                    sharpe_ratio = np.mean(returns) / np.std(returns)
            
            # 최대 낙폭 계산
            max_drawdown = 0.0
            if trades:
                cumulative_returns = np.cumsum([t.get('net_profit', 0) for t in trades])
                running_max = np.maximum.accumulate(cumulative_returns)
                drawdowns = (cumulative_returns - running_max) / running_max
                max_drawdown = np.min(drawdowns) * 100
            
            return DashboardData(
                total_balance=portfolio.get('total_value', 0),
                total_return=portfolio.get('total_return', 0) * 100,
                daily_pnl=daily_pnl,
                active_strategies=len(trading_engine.active_strategies) if trading_engine else 0,
                open_positions=len(positions),
                total_trades=len(trades),
                win_rate=win_rate,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                last_update=datetime.now().isoformat()
            )
        else:
            # 거래 엔진이 실행 중이 아닌 경우 기본값 반환
            return DashboardData(
                total_balance=0,
                total_return=0,
                daily_pnl=0,
                active_strategies=0,
                open_positions=0,
                total_trades=0,
                win_rate=0,
                sharpe_ratio=0,
                max_drawdown=0,
                last_update=datetime.now().isoformat()
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대시보드 데이터 조회 실패: {str(e)}")


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """성과 지표 조회"""
    try:
        trading_engine = get_trading_engine()
        if not trading_engine or not trading_engine.is_running:
            raise HTTPException(status_code=400, detail="거래 엔진이 실행 중이 아닙니다")
        
        trades = trading_engine.get_recent_trades(1000)  # 최근 1000개 거래
        
        if not trades:
            return PerformanceMetrics(
                total_return=0, annualized_return=0, volatility=0,
                sharpe_ratio=0, sortino_ratio=0, max_drawdown=0,
                win_rate=0, profit_factor=0, avg_trade_return=0, commission_impact=0
            )
        
        # 기본 통계 계산
        returns = [t.get('net_profit', 0) for t in trades]
        total_return = sum(returns)
        avg_return = np.mean(returns)
        volatility = np.std(returns)
        
        # 연환산 수익률 (간단한 계산)
        days = 30  # 가정: 30일간 거래
        annualized_return = (1 + total_return / 1000000) ** (365 / days) - 1
        
        # 샤프 비율
        sharpe_ratio = avg_return / volatility if volatility > 0 else 0
        
        # 소르티노 비율
        downside_returns = [r for r in returns if r < 0]
        downside_volatility = np.std(downside_returns) if downside_returns else 0
        sortino_ratio = avg_return / downside_volatility if downside_volatility > 0 else 0
        
        # 최대 낙폭
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0
        
        # 승률
        winning_trades = [r for r in returns if r > 0]
        win_rate = len(winning_trades) / len(returns) * 100 if returns else 0
        
        # 수익 팩터
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # 평균 거래 수익률
        avg_trade_return = avg_return
        
        # 수수료 영향
        total_commission = sum([t.get('commission', 0) for t in trades])
        gross_profit = sum([t.get('gross_profit', 0) for t in trades])
        commission_impact = total_commission / abs(gross_profit) * 100 if gross_profit != 0 else 0
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return * 100,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown * 100,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_return=avg_trade_return,
            commission_impact=commission_impact
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성과 지표 조회 실패: {str(e)}")


@router.get("/logs")
async def get_logs(limit: int = 100):
    """거래 로그 조회"""
    # TODO: 거래 로그 조회 구현
    return {
        "message": "거래 로그 조회 기능은 구현 예정입니다",
        "limit": limit
    }


@router.get("/performance")
async def get_performance():
    """성과 분석 조회"""
    # TODO: 성과 분석 데이터 조회 구현
    return {"message": "성과 분석 기능은 구현 예정입니다"}


@router.get("/alerts")
async def get_alerts():
    """알림 조회"""
    # TODO: 알림 조회 구현
    return {"message": "알림 조회 기능은 구현 예정입니다"}
