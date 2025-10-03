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
    
    def __getstate__(self):
        """pickle 시 socket 객체 제외"""
        state = self.__dict__.copy()
        # WebSocket 연결은 직렬화하지 않음
        state['active_connections'] = []
        return state
    
    def __setstate__(self, state):
        """unpickle 시 초기화"""
        self.__dict__.update(state)
        self.active_connections = []

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
    traditional_strategies: List[str] = []


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


@router.get("/strategy-status")
async def get_strategy_status():
    """전략 상태 조회"""
    try:
        from strategies.strategy_manager import strategy_manager
        return {
            "total_strategies": len(strategy_manager.strategies),
            "active_strategies": len(strategy_manager.active_strategies),
            "strategy_list": list(strategy_manager.strategies.keys()),
            "active_list": strategy_manager.active_strategies.copy()
        }
    except Exception as e:
        logger.error(f"전략 상태 조회 실패: {e}")
        return {"error": str(e)}

@router.get("/ai-strategy-details")
async def get_ai_strategy_details():
    """AI 추천 전략 상세 정보 조회"""
    try:
        from trading.auto_trading_engine import get_trading_engine
        from strategies.strategy_manager import strategy_manager
        
        # 전통적 전략이 실행 중인지 확인
        active_strategies = strategy_manager.get_active_strategies()
        traditional_strategies = [s for s in active_strategies if s.startswith('traditional_')]
        
        if traditional_strategies:
            return {"success": False, "message": "전통적 전략이 실행 중입니다"}
        
        trading_engine = get_trading_engine()
        if not trading_engine or not trading_engine.is_running:
            return {"success": False, "message": "AI 추천 전략이 실행 중이 아닙니다"}
        
        # 포트폴리오 요약 정보
        status = trading_engine.get_status()
        portfolio_summary = {
            "total_assets": status.get('total_assets', 0),
            "total_pnl": status.get('total_pnl', 0),
            "pnl_percentage": status.get('pnl_percentage', 0),
            "win_rate": status.get('win_rate', 0),
            "max_drawdown": status.get('max_drawdown', 0)
        }
        
        # 전략 정보 가져오기
        strategy_name = "AI 추천 전략"
        strategy_type = "ai_recommended"
        
        # 현재 실행 중인 전략 정보 확인
        if hasattr(trading_engine, 'current_strategy') and trading_engine.current_strategy:
            strategy_info = trading_engine.current_strategy
            strategy_name = strategy_info.get('strategy_name', 'AI 추천 전략')
            strategy_type = strategy_info.get('strategy_type', 'ai_recommended')
        
        # 최근 거래 내역 포맷팅
        recent_trades = []
        for trade in trading_engine.trades[-10:]:  # 최근 10개 거래
            try:
                if hasattr(trade, 'id'):
                    recent_trades.append({
                        "id": getattr(trade, 'id', ''),
                        "symbol": getattr(trade, 'symbol', ''),
                        "type": getattr(trade, 'type', ''),
                        "amount": getattr(trade, 'amount', 0),
                        "price": getattr(trade, 'price', 0),
                        "timestamp": getattr(trade, 'timestamp', ''),
                        "status": getattr(trade, 'status', ''),
                        "net_profit": getattr(trade, 'net_profit', 0)
                    })
                else:
                    # 딕셔너리 형태의 거래 데이터 처리
                    recent_trades.append({
                        "id": trade.get('id', ''),
                        "symbol": trade.get('symbol', ''),
                        "type": trade.get('type', ''),
                        "amount": trade.get('amount', 0),
                        "price": trade.get('price', 0),
                        "timestamp": trade.get('timestamp', ''),
                        "status": trade.get('status', ''),
                        "net_profit": trade.get('net_profit', 0)
                    })
            except Exception as e:
                logger.warning(f"AI 전략 거래 데이터 처리 오류: {e}")
                # 기본값으로 처리
                recent_trades.append({
                    "id": '',
                    "symbol": '',
                    "type": '',
                    "amount": 0,
                    "price": 0,
                    "timestamp": '',
                    "status": '',
                    "net_profit": 0
                })
        
        # 현재 포지션 정보
        current_positions = []
        for symbol, pos in trading_engine.positions.items():
            current_positions.append({
                "symbol": symbol,
                "amount": pos.amount,
                "avg_price": pos.avg_price,
                "current_price": trading_engine.market_analyzer.get_current_price(symbol) if trading_engine.market_analyzer else 0,
                "unrealized_pnl": pos.amount * (trading_engine.market_analyzer.get_current_price(symbol) - pos.avg_price) if trading_engine.market_analyzer else 0
            })
        
        return {
            "success": True,
            "is_trading": True,
            "strategy": {
                "id": getattr(trading_engine, 'current_strategy', {}).get("strategy_id", "ai_strategy"),
                "name": strategy_name,
                "type": strategy_type
            },
            "trading": {
                "mode": trading_engine.trading_mode.value,
                "initial_capital": trading_engine.initial_capital,
                "current_capital": trading_engine.current_capital,
                "total_assets": portfolio_summary.get("total_assets", 0),
                "pnl_percentage": portfolio_summary.get("pnl_percentage", 0),
                "total_return": portfolio_summary.get("total_pnl", 0),
                "open_positions": len(trading_engine.positions),
                "total_trades": len(trading_engine.trades),
                "win_rate": portfolio_summary.get("win_rate", 0),
                "max_drawdown": portfolio_summary.get("max_drawdown", 0)
            },
            "recent_trades": recent_trades,
            "current_positions": current_positions
        }
    except Exception as e:
        logger.error(f"AI 추천 전략 상세 정보 조회 실패: {e}")
        return {"success": False, "error": str(e)}

@router.get("/traditional-strategy-details")
async def get_traditional_strategy_details():
    """전통적 전략 상세 정보 조회"""
    try:
        from strategies.strategy_manager import strategy_manager
        from trading.auto_trading_engine import get_trading_engine
        
        traditional_strategies = [s for s in strategy_manager.get_active_strategies() 
                                if s.startswith('traditional_')]
        
        if not traditional_strategies:
            return {"success": False, "message": "실행 중인 전통적 전략이 없습니다"}
        
        # 첫 번째 전통적 전략의 정보 반환
        strategy_id = traditional_strategies[0]
        strategy_info = strategy_manager.strategies.get(strategy_id)
        
        if not strategy_info:
            return {"success": False, "message": "전략 정보를 찾을 수 없습니다"}
        
        # 거래 엔진에서 포트폴리오 정보 가져오기
        trading_engine = get_trading_engine()
        if trading_engine:
            status = trading_engine.get_status()
            positions = list(trading_engine.positions.values()) if hasattr(trading_engine, 'positions') else []
            trades = trading_engine.trades[-50:] if hasattr(trading_engine, 'trades') else []
        else:
            status = {}
            positions = []
            trades = []
        
        # 수익률 계산
        total_return = status.get('pnl_percentage', 0)
        pnl_percentage = total_return
        
        # 최근 거래 내역 포맷팅
        recent_trades = []
        for trade in trades[-10:]:  # 최근 10개 거래
            try:
                if hasattr(trade, 'id'):
                    recent_trades.append({
                        "id": getattr(trade, 'id', ''),
                        "symbol": getattr(trade, 'symbol', ''),
                        "type": getattr(trade, 'type', ''),
                        "amount": getattr(trade, 'amount', 0),
                        "price": getattr(trade, 'price', 0),
                        "timestamp": getattr(trade, 'timestamp', ''),
                        "status": getattr(trade, 'status', ''),
                        "net_profit": getattr(trade, 'net_profit', 0)
                    })
                else:
                    # 딕셔너리 형태의 거래 데이터 처리
                    recent_trades.append({
                        "id": trade.get('id', ''),
                        "symbol": trade.get('symbol', ''),
                        "type": trade.get('type', ''),
                        "amount": trade.get('amount', 0),
                        "price": trade.get('price', 0),
                        "timestamp": trade.get('timestamp', ''),
                        "status": trade.get('status', ''),
                        "net_profit": trade.get('net_profit', 0)
                    })
            except Exception as e:
                logger.warning(f"거래 데이터 처리 오류: {e}")
                # 기본값으로 처리
                recent_trades.append({
                    "id": '',
                    "symbol": '',
                    "type": '',
                    "amount": 0,
                    "price": 0,
                    "timestamp": '',
                    "status": '',
                    "net_profit": 0
                })
        
        # 현재 포지션 정보
        current_positions = []
        for symbol, pos in trading_engine.positions.items() if trading_engine else []:
            current_positions.append({
                "symbol": symbol,
                "amount": pos.amount,
                "avg_price": pos.avg_price,
                "current_price": trading_engine.market_analyzer.get_current_price(symbol) if trading_engine else 0,
                "unrealized_pnl": pos.amount * (trading_engine.market_analyzer.get_current_price(symbol) - pos.avg_price) if trading_engine else 0
            })
        
        # 전략명 매핑
        strategy_name_mapping = {
            'traditional_day_trading': '데이트레이딩 전략',
            'traditional_scalping': '스캘핑 전략', 
            'traditional_swing': '스윙트레이딩 전략',
            'traditional_long_term': '장기 투자 전략'
        }
        
        strategy_name = strategy_name_mapping.get(strategy_id, strategy_info.name)
        
        return {
            "success": True,
            "is_trading": True,
            "strategy": {
                "id": strategy_id,
                "name": strategy_name,
                "type": strategy_info.config.strategy_type.value,
                "status": strategy_info.status.value
            },
            "trading": {
                "mode": "paper",
                "initial_capital": status.get('initial_capital', 1000000),
                "current_capital": status.get('current_capital', 1000000),
                "total_assets": status.get('total_assets', 1000000),
                "pnl_percentage": pnl_percentage,
                "total_return": total_return,
                "open_positions": len(positions),
                "total_trades": len(trades),
                "win_rate": calculate_win_rate(trades),
                "max_drawdown": calculate_max_drawdown(trades)
            },
            "recent_trades": recent_trades,
            "current_positions": current_positions
        }
    except Exception as e:
        logger.error(f"전통적 전략 상세 정보 조회 실패: {e}")
        return {"success": False, "error": str(e)}

def calculate_win_rate(trades):
    """승률 계산"""
    if not trades:
        return 0
    winning_trades = [t for t in trades if t.get('net_profit', 0) > 0]
    return len(winning_trades) / len(trades) * 100

def calculate_max_drawdown(trades):
    """최대 낙폭 계산"""
    if not trades:
        return 0
    cumulative_returns = np.cumsum([t.get('net_profit', 0) for t in trades])
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdowns = (cumulative_returns - running_max) / running_max
    return np.min(drawdowns) * 100 if len(drawdowns) > 0 else 0

@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard():
    """대시보드 데이터 조회"""
    try:
        # AI 거래 시스템에서 실시간 데이터 가져오기
        try:
            from api.ai_recommendation import get_trading_status
            ai_status = await get_trading_status()
            
            if ai_status.get("is_trading", False):
                trading_data = ai_status.get("trading", {})
                
                # AI 거래 데이터를 DashboardData 형식으로 변환
                return DashboardData(
                    total_balance=trading_data.get("current_capital", 0.0),
                    total_return=trading_data.get("total_pnl", 0.0),
                    daily_pnl=trading_data.get("pnl_percentage", 0.0),
                    active_strategies=1,
                    open_positions=len(trading_data.get("positions", {})),
                    total_trades=trading_data.get("total_trades", 0),
                    win_rate=0.0,  # TODO: 계산 로직 추가
                    sharpe_ratio=0.0,  # TODO: 계산 로직 추가
                    max_drawdown=0.0,  # TODO: 계산 로직 추가
                    last_update=datetime.now().isoformat(),
                    traditional_strategies=[]
                )
        except Exception as e:
            logger.warning(f"AI 거래 데이터 조회 실패, 기본 엔진 사용: {e}")
        
        # 기본 거래 엔진에서 포트폴리오 정보 가져오기
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
            
        # 전략 매니저에서 활성 전략 수 확인
        active_strategies_count = 0
        try:
            from strategies.strategy_manager import strategy_manager
            active_strategies = strategy_manager.get_active_strategies()
            active_strategies_count = len(active_strategies)
            logger.info(f"활성 전략 목록: {active_strategies}")
            logger.info(f"전체 전략 수: {len(strategy_manager.strategies)}")
        except Exception as e:
            logger.error(f"전략 매니저 조회 실패: {e}")
            active_strategies_count = len(trading_engine.active_strategies) if trading_engine else 0
            
            # 전통적 전략 목록 가져오기
            traditional_strategies = []
            try:
                from strategies.strategy_manager import strategy_manager
                traditional_strategies = [s for s in strategy_manager.get_active_strategies() 
                                        if s.startswith('traditional_')]
            except Exception as e:
                logger.error(f"전통적 전략 조회 실패: {e}")
            
            return DashboardData(
                total_balance=portfolio.get('total_value', 0),
                total_return=portfolio.get('total_return', 0) * 100,
                daily_pnl=daily_pnl,
                active_strategies=active_strategies_count,
                open_positions=len(positions),
                total_trades=len(trades),
                win_rate=win_rate,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                last_update=datetime.now().isoformat(),
                traditional_strategies=traditional_strategies
            )
        else:
            # 거래 엔진이 실행 중이 아닌 경우에도 전략 매니저에서 활성 전략 수 확인
            active_strategies_count = 0
            try:
                from strategies.strategy_manager import strategy_manager
                active_strategies = strategy_manager.get_active_strategies()
                active_strategies_count = len(active_strategies)
                logger.info(f"거래 엔진 미실행 상태에서 활성 전략 목록: {active_strategies}")
            except Exception as e:
                logger.error(f"전략 매니저 조회 실패: {e}")
            
            # 전통적 전략 목록 가져오기
            traditional_strategies = []
            try:
                from strategies.strategy_manager import strategy_manager
                traditional_strategies = [s for s in strategy_manager.get_active_strategies() 
                                        if s.startswith('traditional_')]
            except Exception as e:
                logger.error(f"전통적 전략 조회 실패: {e}")
            
            return DashboardData(
                total_balance=0,
                total_return=0,
                daily_pnl=0,
                active_strategies=active_strategies_count,
                open_positions=0,
                total_trades=0,
                win_rate=0,
                sharpe_ratio=0,
                max_drawdown=0,
                last_update=datetime.now().isoformat(),
                traditional_strategies=traditional_strategies
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"대시보드 데이터 조회 실패: {str(e)}")


@router.get("/trades")
async def get_trades(limit: int = Query(100, ge=1, le=1000)):
    """거래 내역 조회"""
    try:
        # AI 거래 시스템에서 거래 내역 가져오기
        try:
            from api.ai_recommendation import get_trading_status
            ai_status = await get_trading_status()
            
            if ai_status.get("is_trading", False):
                trading_data = ai_status.get("trading", {})
                trades = trading_data.get("trades", [])
                
                # 거래 내역을 모니터링 형식으로 변환
                formatted_trades = []
                for trade in trades[-limit:]:  # 최근 거래만
                    formatted_trades.append({
                        "id": trade.get("id", ""),
                        "symbol": trade.get("symbol", ""),
                        "side": trade.get("side", ""),
                        "amount": trade.get("amount", 0.0),
                        "price": trade.get("price", 0.0),
                        "timestamp": trade.get("timestamp", ""),
                        "status": trade.get("status", ""),
                        "commission": trade.get("commission", 0.0),
                        "net_profit": 0.0,  # TODO: 계산 로직 추가
                        "gross_profit": 0.0  # TODO: 계산 로직 추가
                    })
                
                return {
                    "success": True,
                    "trades": formatted_trades,
                    "total": len(formatted_trades)
                }
        except Exception as e:
            logger.warning(f"AI 거래 데이터 조회 실패, 기본 엔진 사용: {e}")
        
        # 기본 거래 엔진에서 거래 내역 가져오기
        trading_engine = get_trading_engine()
        if not trading_engine or not trading_engine.is_running:
            return {"success": False, "trades": [], "total": 0}
        
        trades = trading_engine.get_recent_trades(limit)
        return {"success": True, "trades": trades, "total": len(trades)}
        
    except Exception as e:
        logger.error(f"거래 내역 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="거래 내역 조회 실패")

@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """성과 지표 조회"""
    try:
        # AI 거래 시스템에서 성과 데이터 가져오기
        try:
            from api.ai_recommendation import get_trading_status
            ai_status = await get_trading_status()
            
            if ai_status.get("is_trading", False):
                trading_data = ai_status.get("trading", {})
                
                # AI 거래 데이터를 성과 지표로 변환
                return PerformanceMetrics(
                    total_return=trading_data.get("total_pnl", 0.0),
                    annualized_return=0.0,  # TODO: 계산 로직 추가
                    volatility=0.0,  # TODO: 계산 로직 추가
                    sharpe_ratio=0.0,  # TODO: 계산 로직 추가
                    sortino_ratio=0.0,  # TODO: 계산 로직 추가
                    max_drawdown=0.0,  # TODO: 계산 로직 추가
                    win_rate=0.0,  # TODO: 계산 로직 추가
                    profit_factor=0.0,  # TODO: 계산 로직 추가
                    avg_trade_return=0.0,  # TODO: 계산 로직 추가
                    commission_impact=0.0  # TODO: 계산 로직 추가
                )
        except Exception as e:
            logger.warning(f"AI 거래 데이터 조회 실패, 기본 엔진 사용: {e}")
        
        # 기본 거래 엔진에서 성과 지표 가져오기
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
            # 비동기로 메시지 수신 대기 (타임아웃 포함)
            try:
                # 0.1초마다 체크하여 블로킹 방지
                message = await asyncio.wait_for(
                    websocket.receive_text(), 
                    timeout=0.1
                )
                # 클라이언트 요청 처리
                logger.info(f"클라이언트 메시지 수신: {message}")
                
                # ping 메시지에 pong 응답
                if message == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                # 타임아웃은 정상 - 계속 진행
                pass
            except WebSocketDisconnect:
                logger.info("클라이언트가 WebSocket 연결을 종료했습니다")
                break
            except Exception as e:
                logger.error(f"WebSocket 메시지 수신 오류: {e}")
                break
            
            # 짧은 대기로 CPU 사용률 최적화
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket 연결 정상 종료")
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


@router.get("/pnl-history")
async def get_pnl_history(limit: int = Query(50, ge=1, le=200)):
    """PnL 히스토리 조회"""
    try:
        # AI 거래 시스템에서 PnL 히스토리 가져오기
        try:
            from api.ai_recommendation import get_trading_status
            ai_status = await get_trading_status()
            
            if ai_status.get("is_trading", False):
                trading_data = ai_status.get("trading", {})
                current_pnl = trading_data.get("total_return", 0)
                current_time = datetime.now().strftime("%H:%M")
                
                # 현재 PnL을 히스토리에 추가
                pnl_history = [{
                    "time": current_time,
                    "pnl": current_pnl
                }]
                
                return {
                    "success": True,
                    "history": pnl_history,
                    "total": len(pnl_history)
                }
        except Exception as e:
            logger.warning(f"AI 거래 데이터 조회 실패, 기본 엔진 사용: {e}")
        
        # 기본 거래 엔진에서 PnL 히스토리 가져오기
        trading_engine = get_trading_engine()
        if not trading_engine or not trading_engine.is_running:
            return {"success": False, "history": [], "total": 0}
        
        # TODO: 실제 PnL 히스토리 구현
        # 현재는 빈 배열 반환
        return {"success": True, "history": [], "total": 0}
        
    except Exception as e:
        logger.error(f"PnL 히스토리 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="PnL 히스토리 조회 실패")
