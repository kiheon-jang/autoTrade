"""
전략 관련 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from core.database import get_db
from models.strategy import Strategy, StrategyExecution

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
async def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db)):
    """전략 생성"""
    try:
        # 데이터베이스에 전략 저장
        db_strategy = Strategy(
            name=strategy.name,
            strategy_type=strategy.strategy_type,
            parameters=strategy.parameters,
            risk_per_trade=strategy.risk_per_trade,
            max_positions=strategy.max_positions,
            is_active=False,
            created_at=datetime.now()
        )
        
        db.add(db_strategy)
        db.commit()
        db.refresh(db_strategy)
        
        return {
            "strategy_id": str(db_strategy.id),
            "message": f"전략 '{strategy.name}'이 성공적으로 생성되었습니다",
            "strategy": {
                "id": db_strategy.id,
                "name": db_strategy.name,
                "strategy_type": db_strategy.strategy_type,
                "parameters": db_strategy.parameters,
                "risk_per_trade": db_strategy.risk_per_trade,
                "max_positions": db_strategy.max_positions,
                "is_active": db_strategy.is_active,
                "created_at": db_strategy.created_at
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"전략 생성 실패: {str(e)}")


@router.get("/list")
async def get_strategies(db: Session = Depends(get_db)):
    """전략 목록 조회"""
    try:
        strategies = db.query(Strategy).all()
        
        strategy_list = []
        for strategy in strategies:
            strategy_list.append({
                "id": strategy.id,
                "name": strategy.name,
                "strategy_type": strategy.strategy_type,
                "parameters": strategy.parameters,
                "risk_per_trade": strategy.risk_per_trade,
                "max_positions": strategy.max_positions,
                "is_active": strategy.is_active,
                "created_at": strategy.created_at,
                "updated_at": strategy.updated_at
            })
        
        return {
            "strategies": strategy_list,
            "total": len(strategy_list),
            "message": "전략 목록을 성공적으로 조회했습니다"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전략 목록 조회 실패: {str(e)}")


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """특정 전략 조회"""
    try:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="전략을 찾을 수 없습니다")
        
        return {
            "strategy": {
                "id": strategy.id,
                "name": strategy.name,
                "strategy_type": strategy.strategy_type,
                "parameters": strategy.parameters,
                "risk_per_trade": strategy.risk_per_trade,
                "max_positions": strategy.max_positions,
                "is_active": strategy.is_active,
                "created_at": strategy.created_at,
                "updated_at": strategy.updated_at
            },
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
