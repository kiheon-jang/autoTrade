"""
모니터링 관련 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import pandas as pd
import numpy as np
import asyncio
import json
import logging

from trading.realtime_engine import get_trading_engine
from strategies.strategy_manager import strategy_manager
from core.commission import CommissionCalculator, ExchangeType

router = APIRouter()
logger = logging.getLogger(__name__)

# WebSocket 연결 관리자
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket 연결 추가. 총 연결 수: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.logger.info(f"WebSocket 연결 제거. 총 연결 수: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.logger.error(f"개인 메시지 전송 실패: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                self.logger.error(f"브로드캐스트 전송 실패: {e}")
                disconnected.append(connection)
        
        # 연결이 끊어진 WebSocket 제거
        for connection in disconnected:
            self.disconnect(connection)

# 전역 연결 관리자
manager = ConnectionManager()


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


@router.get("/portfolio")
async def get_portfolio():
    """포트폴리오 현황 조회"""
    try:
        # 기본 포트폴리오 데이터 반환
        return {
            "total_value": 1000000,
            "total_return": 50000,
            "total_return_rate": 5.0,
            "today_return": 10000,
            "today_return_rate": 1.0,
            "positions": [],
            "cash_balance": 1000000,
            "message": "포트폴리오 현황을 성공적으로 조회했습니다"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"포트폴리오 조회 실패: {str(e)}")


@router.get("/performance")
async def get_performance():
    """성과 분석 조회"""
    # TODO: 성과 분석 데이터 조회 구현
    return {"message": "성과 분석 기능은 구현 예정입니다"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """실시간 모니터링 WebSocket 연결"""
    await manager.connect(websocket)
    try:
        while True:
            # 클라이언트로부터 메시지 수신 (선택사항)
            try:
                data = await websocket.receive_text()
                # 클라이언트 요청 처리 (필요시)
                logger.info(f"클라이언트 메시지 수신: {data}")
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket 메시지 수신 오류: {e}")
                break
            
            # 1초마다 실시간 데이터 전송
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 연결 오류: {e}")
        manager.disconnect(websocket)


async def broadcast_realtime_data():
    """실시간 데이터 브로드캐스트 (백그라운드 태스크)"""
    while True:
        try:
            if manager.active_connections:
                # 실시간 데이터 수집
                trading_engine = get_trading_engine()
                if trading_engine and trading_engine.is_running:
                    # 대시보드 데이터
                    dashboard_data = await get_dashboard_data()
                    
                    # 성과 지표
                    performance_data = await get_performance_metrics()
                    
                    # 실시간 데이터 패키지
                    realtime_data = {
                        "type": "realtime_update",
                        "timestamp": datetime.now().isoformat(),
                        "dashboard": dashboard_data.dict(),
                        "performance": performance_data.dict()
                    }
                    
                    # 모든 연결된 클라이언트에게 브로드캐스트
                    await manager.broadcast(json.dumps(realtime_data))
                
        except Exception as e:
            logger.error(f"실시간 데이터 브로드캐스트 오류: {e}")
        
        # 1초 간격으로 업데이트
        await asyncio.sleep(1)


async def get_dashboard_data() -> DashboardData:
    """대시보드 데이터 조회 (내부 함수)"""
    try:
        trading_engine = get_trading_engine()
        if not trading_engine or not trading_engine.is_running:
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
        
        portfolio = trading_engine.get_portfolio_summary()
        positions = trading_engine.get_positions()
        trades = trading_engine.get_recent_trades(100)
        
        # 일일 PnL 계산
        daily_pnl = 0
        if trades:
            today = datetime.now().date()
            today_trades = [t for t in trades if t.get('timestamp', datetime.now()).date() == today]
            daily_pnl = sum([t.get('pnl', 0) for t in today_trades])
        
        # 승률 계산
        win_rate = 0
        if trades:
            winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
            win_rate = len(winning_trades) / len(trades) * 100
        
        # 샤프 비율 계산
        sharpe_ratio = 0
        if len(trades) > 1:
            returns = [t.get('pnl', 0) for t in trades]
            if returns:
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = mean_return / std_return if std_return > 0 else 0
        
        # 최대 낙폭 계산
        max_drawdown = 0
        if trades:
            cumulative_returns = np.cumsum([t.get('pnl', 0) for t in trades])
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(np.min(drawdowns)) * 100 if len(drawdowns) > 0 else 0
        
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
        
    except Exception as e:
        logger.error(f"대시보드 데이터 조회 오류: {e}")
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


async def get_performance_metrics() -> PerformanceMetrics:
    """성과 지표 조회 (내부 함수)"""
    try:
        trading_engine = get_trading_engine()
        if not trading_engine or not trading_engine.is_running:
            return PerformanceMetrics(
                total_return=0,
                annualized_return=0,
                volatility=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                max_drawdown=0,
                win_rate=0,
                profit_factor=0,
                avg_trade_return=0,
                commission_impact=0
            )
        
        trades = trading_engine.get_recent_trades(1000)
        if not trades:
            return PerformanceMetrics(
                total_return=0,
                annualized_return=0,
                volatility=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                max_drawdown=0,
                win_rate=0,
                profit_factor=0,
                avg_trade_return=0,
                commission_impact=0
            )
        
        # 기본 계산
        returns = [t.get('pnl', 0) for t in trades]
        total_return = sum(returns)
        
        # 연환산 수익률
        if trades:
            first_trade = min(trades, key=lambda x: x.get('timestamp', datetime.now()))
            last_trade = max(trades, key=lambda x: x.get('timestamp', datetime.now()))
            days = (last_trade.get('timestamp', datetime.now()) - first_trade.get('timestamp', datetime.now())).days
            annualized_return = (total_return / days * 365) if days > 0 else 0
        else:
            annualized_return = 0
        
        # 변동성
        volatility = np.std(returns) if returns else 0
        
        # 샤프 비율
        sharpe_ratio = np.mean(returns) / volatility if volatility > 0 else 0
        
        # 소르티노 비율
        negative_returns = [r for r in returns if r < 0]
        downside_volatility = np.std(negative_returns) if negative_returns else 0
        sortino_ratio = np.mean(returns) / downside_volatility if downside_volatility > 0 else 0
        
        # 최대 낙폭
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdowns)) * 100 if len(drawdowns) > 0 else 0
        
        # 승률
        winning_trades = [r for r in returns if r > 0]
        win_rate = len(winning_trades) / len(returns) * 100 if returns else 0
        
        # 수익 팩터
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # 평균 거래 수익률
        avg_trade_return = np.mean(returns) if returns else 0
        
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
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade_return=avg_trade_return,
            commission_impact=commission_impact
        )
        
    except Exception as e:
        logger.error(f"성과 지표 조회 오류: {e}")
        return PerformanceMetrics(
            total_return=0,
            annualized_return=0,
            volatility=0,
            sharpe_ratio=0,
            sortino_ratio=0,
            max_drawdown=0,
            win_rate=0,
            profit_factor=0,
            avg_trade_return=0,
            commission_impact=0
        )


@router.get("/alerts")
async def get_alerts():
    """알림 조회"""
    # TODO: 알림 조회 구현
    return {"message": "알림 조회 기능은 구현 예정입니다"}
