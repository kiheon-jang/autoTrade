"""
전략 관련 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class StrategyCreate(BaseModel):
    """전략 생성 요청"""
    name: str
    strategy_type: str  # scalping, day_trading, swing_trading, long_term
    parameters: dict
    risk_per_trade: float
    max_positions: int


class StrategyUpdate(BaseModel):
    """전략 수정 요청"""
    name: Optional[str] = None
    parameters: Optional[dict] = None
    risk_per_trade: Optional[float] = None
    max_positions: Optional[int] = None


@router.post("/create")
async def create_strategy(strategy: StrategyCreate):
    """전략 생성"""
    try:
        from strategies.strategy_manager import strategy_manager, StrategyConfig, StrategyType
        
        # 전략 타입 변환
        strategy_type_map = {
            "scalping": StrategyType.SCALPING,
            "day_trading": StrategyType.DAY_TRADING,
            "swing_trading": StrategyType.SWING_TRADING,
            "long_term": StrategyType.LONG_TERM
        }
        
        strategy_type = strategy_type_map.get(strategy.strategy_type, StrategyType.SCALPING)
        
        # 전략 설정 생성
        config = StrategyConfig(
            name=strategy.name,
            strategy_type=strategy_type,
            parameters=strategy.parameters,
            risk_per_trade=strategy.risk_per_trade,
            max_positions=strategy.max_positions
        )
        
        # 전략 생성
        strategy_id = strategy_manager.create_strategy(
            name=strategy.name,
            strategy_type=strategy_type,
            config=config
        )
        
        return {
            "strategy_id": strategy_id,
            "message": "전략이 성공적으로 생성되었습니다",
            "strategy": strategy.dict()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전략 생성 실패: {str(e)}")


@router.get("/list")
async def get_strategies():
    """전략 목록 조회"""
    try:
        from strategies.strategy_manager import strategy_manager
        
        strategies = strategy_manager.get_all_strategies()
        
        return {
            "strategies": strategies,
            "total": len(strategies),
            "message": "전략 목록을 성공적으로 조회했습니다"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전략 목록 조회 실패: {str(e)}")


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str):
    """특정 전략 조회"""
    try:
        from strategies.strategy_manager import strategy_manager
        
        strategy_info = strategy_manager.get_strategy_info(strategy_id)
        
        if not strategy_info:
            raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다")
        
        return {
            "strategy": strategy_info,
            "message": f"전략 {strategy_id} 정보를 성공적으로 조회했습니다"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전략 조회 실패: {str(e)}")


@router.put("/{strategy_id}/start")
async def start_strategy(strategy_id: str):
    """전략 시작"""
    try:
        from strategies.strategy_manager import strategy_manager
        from trading.realtime_engine import get_trading_engine
        
        # 전략 존재 확인
        strategy_info = strategy_manager.get_strategy_info(strategy_id)
        if not strategy_info:
            raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다")
        
        # 거래 엔진에 전략 추가
        trading_engine = get_trading_engine()
        if not trading_engine:
            raise HTTPException(status_code=400, detail="거래 엔진이 실행되지 않았습니다")
        
        # 전략 활성화
        success = strategy_manager.activate_strategy(strategy_id)
        
        if success:
            return {"message": f"전략 {strategy_id}가 성공적으로 시작되었습니다"}
        else:
            raise HTTPException(status_code=400, detail="전략 시작에 실패했습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전략 시작 실패: {str(e)}")


@router.put("/{strategy_id}/stop")
async def stop_strategy(strategy_id: str):
    """전략 중지"""
    try:
        from strategies.strategy_manager import strategy_manager
        
        # 전략 존재 확인
        strategy_info = strategy_manager.get_strategy_info(strategy_id)
        if not strategy_info:
            raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다")
        
        # 전략 비활성화
        success = strategy_manager.deactivate_strategy(strategy_id)
        
        if success:
            return {"message": f"전략 {strategy_id}가 성공적으로 중지되었습니다"}
        else:
            raise HTTPException(status_code=400, detail="전략 중지에 실패했습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전략 중지 실패: {str(e)}")


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str):
    """전략 삭제"""
    try:
        from strategies.strategy_manager import strategy_manager
        
        # 전략 존재 확인
        strategy_info = strategy_manager.get_strategy_info(strategy_id)
        if not strategy_info:
            raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다")
        
        # 전략 삭제
        success = strategy_manager.remove_strategy(strategy_id)
        
        if success:
            return {"message": f"전략 {strategy_id}가 성공적으로 삭제되었습니다"}
        else:
            raise HTTPException(status_code=400, detail="전략 삭제에 실패했습니다")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전략 삭제 실패: {str(e)}")
