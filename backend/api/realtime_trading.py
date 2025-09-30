"""
실시간 거래 API 엔드포인트
기존 API 구조를 확장하여 실시간 거래 기능 제공
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
import asyncio
import json
import logging

from trading.realtime_engine import RealtimeTradingEngine, TradingMode, RealtimeTrade, set_trading_engine
from strategies.strategy_manager import strategy_manager, StrategyConfig, StrategyType
from core.commission import ExchangeType

router = APIRouter()

# 전역 거래 엔진 인스턴스
trading_engine: Optional[RealtimeTradingEngine] = None
websocket_connections: List[WebSocket] = []

# 로깅 설정
logger = logging.getLogger(__name__)


class TradingStartRequest(BaseModel):
    """거래 시작 요청"""
    mode: str = "simulation"  # simulation, live, paper
    symbols: List[str] = ["BTC", "ETH"]
    strategies: List[str] = []
    initial_capital: float = 1000000


class TradingStopRequest(BaseModel):
    """거래 중지 요청"""
    force: bool = False


class OrderRequest(BaseModel):
    """주문 요청"""
    symbol: str
    side: str  # buy, sell
    amount: float
    price: Optional[float] = None
    order_type: str = "market"  # market, limit


class TradingResponse(BaseModel):
    """거래 응답"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


async def broadcast_to_websockets(message: Dict[str, Any]):
    """WebSocket 연결된 모든 클라이언트에게 메시지 전송"""
    if websocket_connections:
        disconnected = []
        for websocket in websocket_connections:
            try:
                await websocket.send_text(json.dumps(message))
            except:
                disconnected.append(websocket)
        
        # 연결이 끊어진 WebSocket 제거
        for ws in disconnected:
            websocket_connections.remove(ws)


async def on_trade_callback(trade: RealtimeTrade):
    """거래 콜백 함수"""
    message = {
        "type": "trade",
        "data": {
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side,
            "amount": trade.amount,
            "price": trade.price,
            "timestamp": trade.timestamp.isoformat(),
            "status": trade.status,
            "commission": trade.commission,
            "strategy_id": trade.strategy_id
        }
    }
    await broadcast_to_websockets(message)


async def on_position_callback(position_data: Dict[str, Any]):
    """포지션 콜백 함수"""
    message = {
        "type": "position",
        "data": position_data
    }
    await broadcast_to_websockets(message)


async def on_error_callback(error: Exception):
    """오류 콜백 함수"""
    message = {
        "type": "error",
        "data": {
            "error": str(error),
            "timestamp": datetime.now().isoformat()
        }
    }
    await broadcast_to_websockets(message)


@router.post("/start", response_model=TradingResponse)
async def start_trading(request: TradingStartRequest, background_tasks: BackgroundTasks):
    """실시간 거래 시작"""
    global trading_engine
    
    try:
        if trading_engine and trading_engine.is_running:
            raise HTTPException(status_code=400, detail="거래가 이미 실행 중입니다")
        
        # 거래 모드 설정
        mode = TradingMode.SIMULATION
        if request.mode == "live":
            mode = TradingMode.LIVE
        elif request.mode == "paper":
            mode = TradingMode.PAPER
        
        # 거래 엔진 생성
        trading_engine = RealtimeTradingEngine(
            mode=mode,
            initial_capital=request.initial_capital
        )
        
        # 전역 거래 엔진 인스턴스 설정
        set_trading_engine(trading_engine)
        
        # 콜백 함수 설정
        trading_engine.on_trade_callback = on_trade_callback
        trading_engine.on_position_callback = on_position_callback
        trading_engine.on_error_callback = on_error_callback
        
        # 백그라운드에서 거래 시작
        background_tasks.add_task(
            trading_engine.start,
            symbols=request.symbols,
            strategies=request.strategies
        )
        
        return TradingResponse(
            success=True,
            message=f"거래가 시작되었습니다 (모드: {request.mode})",
            data={
                "mode": request.mode,
                "symbols": request.symbols,
                "strategies": request.strategies,
                "initial_capital": request.initial_capital
            }
        )
        
    except Exception as e:
        logger.error(f"거래 시작 오류: {e}")
        raise HTTPException(status_code=500, detail=f"거래 시작 실패: {str(e)}")


@router.post("/stop", response_model=TradingResponse)
async def stop_trading(request: TradingStopRequest):
    """실시간 거래 중지"""
    global trading_engine
    
    try:
        if not trading_engine or not trading_engine.is_running:
            raise HTTPException(status_code=400, detail="실행 중인 거래가 없습니다")
        
        await trading_engine.stop()
        
        return TradingResponse(
            success=True,
            message="거래가 중지되었습니다",
            data={
                "stopped_at": datetime.now().isoformat(),
                "force": request.force
            }
        )
        
    except Exception as e:
        logger.error(f"거래 중지 오류: {e}")
        raise HTTPException(status_code=500, detail=f"거래 중지 실패: {str(e)}")


@router.get("/status", response_model=TradingResponse)
async def get_trading_status():
    """거래 상태 조회"""
    global trading_engine
    
    try:
        if not trading_engine:
            return TradingResponse(
                success=True,
                message="거래 엔진이 초기화되지 않았습니다",
                data={
                    "is_running": False,
                    "mode": None,
                    "active_strategies": [],
                    "positions": {},
                    "portfolio": {}
                }
            )
        
        portfolio_summary = trading_engine.get_portfolio_summary()
        positions = trading_engine.get_positions()
        
        return TradingResponse(
            success=True,
            message="거래 상태 조회 성공",
            data={
                "is_running": trading_engine.is_running,
                "mode": trading_engine.mode.value,
                "active_strategies": trading_engine.active_strategies,
                "positions": positions,
                "portfolio": portfolio_summary,
                "last_update": trading_engine.last_update.isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"거래 상태 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"거래 상태 조회 실패: {str(e)}")


@router.get("/positions", response_model=TradingResponse)
async def get_positions():
    """포지션 정보 조회"""
    global trading_engine
    
    try:
        if not trading_engine:
            raise HTTPException(status_code=400, detail="거래 엔진이 초기화되지 않았습니다")
        
        positions = trading_engine.get_positions()
        
        return TradingResponse(
            success=True,
            message="포지션 정보 조회 성공",
            data={"positions": positions}
        )
        
    except Exception as e:
        logger.error(f"포지션 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"포지션 조회 실패: {str(e)}")


@router.get("/trades", response_model=TradingResponse)
async def get_trades(limit: int = 50):
    """거래 내역 조회"""
    global trading_engine
    
    try:
        if not trading_engine:
            raise HTTPException(status_code=400, detail="거래 엔진이 초기화되지 않았습니다")
        
        trades = trading_engine.get_recent_trades(limit)
        
        return TradingResponse(
            success=True,
            message="거래 내역 조회 성공",
            data={"trades": trades, "total": len(trading_engine.trades)}
        )
        
    except Exception as e:
        logger.error(f"거래 내역 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"거래 내역 조회 실패: {str(e)}")


@router.post("/order", response_model=TradingResponse)
async def place_order(request: OrderRequest):
    """수동 주문 실행"""
    global trading_engine
    
    try:
        if not trading_engine or not trading_engine.is_running:
            raise HTTPException(status_code=400, detail="거래가 실행 중이 아닙니다")
        
        if trading_engine.mode == TradingMode.SIMULATION:
            # 시뮬레이션 모드에서는 수동 주문 불가
            raise HTTPException(status_code=400, detail="시뮬레이션 모드에서는 수동 주문을 지원하지 않습니다")
        
        # 실제 주문 실행 로직은 trading_engine에 구현
        # 여기서는 기본적인 검증만 수행
        
        if request.side not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="잘못된 주문 방향입니다")
        
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="주문 수량은 0보다 커야 합니다")
        
        return TradingResponse(
            success=True,
            message="주문이 접수되었습니다",
            data={
                "symbol": request.symbol,
                "side": request.side,
                "amount": request.amount,
                "price": request.price,
                "order_type": request.order_type,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"주문 실행 오류: {e}")
        raise HTTPException(status_code=500, detail=f"주문 실행 실패: {str(e)}")


@router.get("/strategies", response_model=TradingResponse)
async def get_available_strategies():
    """사용 가능한 전략 목록 조회"""
    try:
        strategies = strategy_manager.get_all_strategies()
        
        strategy_list = []
        for strategy_id, strategy_info in strategies.items():
            strategy_list.append({
                "id": strategy_id,
                "name": strategy_info["name"],
                "type": strategy_info["type"],
                "status": strategy_info["status"],
                "created_at": strategy_info["created_at"],
                "performance": strategy_info.get("performance", {})
            })
        
        return TradingResponse(
            success=True,
            message="전략 목록 조회 성공",
            data={"strategies": strategy_list}
        )
        
    except Exception as e:
        logger.error(f"전략 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"전략 목록 조회 실패: {str(e)}")


@router.post("/strategies/{strategy_id}/start", response_model=TradingResponse)
async def start_strategy(strategy_id: str):
    """전략 시작"""
    try:
        success = strategy_manager.start_strategy(strategy_id)
        
        if success:
            return TradingResponse(
                success=True,
                message=f"전략 {strategy_id}이 시작되었습니다",
                data={"strategy_id": strategy_id, "status": "active"}
            )
        else:
            raise HTTPException(status_code=400, detail="전략 시작에 실패했습니다")
        
    except Exception as e:
        logger.error(f"전략 시작 오류: {e}")
        raise HTTPException(status_code=500, detail=f"전략 시작 실패: {str(e)}")


@router.post("/strategies/{strategy_id}/stop", response_model=TradingResponse)
async def stop_strategy(strategy_id: str):
    """전략 중지"""
    try:
        success = strategy_manager.stop_strategy(strategy_id)
        
        if success:
            return TradingResponse(
                success=True,
                message=f"전략 {strategy_id}이 중지되었습니다",
                data={"strategy_id": strategy_id, "status": "inactive"}
            )
        else:
            raise HTTPException(status_code=400, detail="전략 중지에 실패했습니다")
        
    except Exception as e:
        logger.error(f"전략 중지 오류: {e}")
        raise HTTPException(status_code=500, detail=f"전략 중지 실패: {str(e)}")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 연결"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # 연결 확인 메시지 전송
        await websocket.send_text(json.dumps({
            "type": "connection",
            "data": {
                "message": "WebSocket 연결이 성공적으로 설정되었습니다",
                "timestamp": datetime.now().isoformat()
            }
        }))
        
        # 클라이언트로부터 메시지 수신 대기
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 클라이언트 요청 처리
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "data": {"timestamp": datetime.now().isoformat()}
                    }))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket 메시지 처리 오류: {e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"error": str(e)}
                }))
    
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        logger.info("WebSocket 연결이 종료되었습니다")


@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "trading_engine": trading_engine is not None and trading_engine.is_running,
        "websocket_connections": len(websocket_connections)
    }
