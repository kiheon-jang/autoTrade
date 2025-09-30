"""
백테스팅 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import pandas as pd
import numpy as np

from backtesting.backtest_engine import BacktestEngine, BacktestResult
from strategies.strategy_manager import strategy_manager, StrategyConfig, StrategyType
from strategies.base_strategy import StrategyType as BaseStrategyType
from core.commission import ExchangeType

router = APIRouter()


class BacktestRequest(BaseModel):
    """백테스트 요청"""
    strategy_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_capital: float = 1000000
    commission_rate: float = 0.0015
    exchange: str = "bithumb"


class BacktestResponse(BaseModel):
    """백테스트 응답"""
    strategy_id: str
    strategy_name: str
    backtest_period: Dict[str, str]
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    profit_factor: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_return: float
    avg_winning_trade: float
    avg_losing_trade: float
    largest_win: float
    largest_loss: float
    avg_hold_duration: str
    total_commission: float
    net_profit: float
    gross_profit: float
    commission_impact: float
    equity_curve: List[Dict[str, Any]]
    trade_history: List[Dict[str, Any]]
    timestamp: datetime


def generate_sample_data(days: int = 30, symbol: str = "BTC") -> pd.DataFrame:
    """샘플 데이터 생성"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                         end=datetime.now(), freq='1H')
    
    # 랜덤 워크로 가격 데이터 생성
    np.random.seed(42)
    price = 50000  # 시작 가격
    prices = [price]
    
    for _ in range(len(dates) - 1):
        change = np.random.normal(0, 200)  # 평균 0, 표준편차 200의 변화
        price += change
        prices.append(max(price, 1000))  # 최소 가격 1000
    
    # OHLCV 데이터 생성
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        if i == 0:
            open_price = close
        else:
            open_price = prices[i-1]
        
        high = max(open_price, close) + np.random.uniform(0, 100)
        low = min(open_price, close) - np.random.uniform(0, 100)
        volume = np.random.uniform(1000, 10000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """백테스트 실행"""
    try:
        # 전략 조회
        strategy_info = strategy_manager.get_strategy_info(request.strategy_id)
        if not strategy_info:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # 전략 인스턴스 가져오기
        strategy = strategy_manager.strategies[request.strategy_id].strategy
        
        # 샘플 데이터 생성 (실제로는 데이터베이스에서 가져옴)
        data = generate_sample_data(30)
        
        # 백테스트 엔진 생성
        exchange = ExchangeType.BITHUMB if request.exchange == "bithumb" else ExchangeType.UPBIT
        engine = BacktestEngine(
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            exchange=exchange
        )
        
        # 백테스트 실행
        result = engine.run_backtest(
            strategy=strategy,
            data=data,
            start_date=request.start_date,
            end_date=request.end_date
        )
        
        # 응답 생성
        response = BacktestResponse(
            strategy_id=request.strategy_id,
            strategy_name=strategy_info['name'],
            backtest_period={
                'start': request.start_date.isoformat() if request.start_date else data.index[0].isoformat(),
                'end': request.end_date.isoformat() if request.end_date else data.index[-1].isoformat()
            },
            initial_capital=request.initial_capital,
            final_capital=request.initial_capital + result.net_profit,
            total_return=result.total_return,
            annualized_return=result.annualized_return,
            max_drawdown=result.max_drawdown,
            sharpe_ratio=result.sharpe_ratio,
            sortino_ratio=result.sortino_ratio,
            profit_factor=result.profit_factor,
            win_rate=result.win_rate,
            total_trades=result.total_trades,
            winning_trades=result.winning_trades,
            losing_trades=result.losing_trades,
            avg_trade_return=result.avg_trade_return,
            avg_winning_trade=result.avg_winning_trade,
            avg_losing_trade=result.avg_losing_trade,
            largest_win=result.largest_win,
            largest_loss=result.largest_loss,
            avg_hold_duration=str(result.avg_hold_duration),
            total_commission=result.total_commission,
            net_profit=result.net_profit,
            gross_profit=result.gross_profit,
            commission_impact=result.commission_impact,
            equity_curve=engine.get_equity_curve(),
            trade_history=engine.get_trade_history(),
            timestamp=datetime.now()
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/strategies")
async def get_available_strategies():
    """사용 가능한 전략 목록 조회"""
    try:
        strategies = strategy_manager.get_all_strategies()
        return {
            "strategies": strategies,
            "total": len(strategies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get strategies: {str(e)}")


@router.get("/strategy/{strategy_id}")
async def get_strategy_info(strategy_id: str):
    """특정 전략 정보 조회"""
    try:
        strategy_info = strategy_manager.get_strategy_info(strategy_id)
        if not strategy_info:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return strategy_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get strategy info: {str(e)}")


@router.post("/strategy/create")
async def create_strategy(
    name: str = Body(...),
    strategy_type: str = Body(...),
    parameters: Dict[str, Any] = Body(...),
    risk_per_trade: float = Body(2.0),
    max_positions: int = Body(5),
    stop_loss_pct: float = Body(2.0),
    take_profit_pct: float = Body(4.0)
):
    """새 전략 생성"""
    try:
        # 전략 타입 변환
        strategy_type_enum = StrategyType.SCALPING
        if strategy_type == "day_trading":
            strategy_type_enum = StrategyType.DAY_TRADING
        elif strategy_type == "swing_trading":
            strategy_type_enum = StrategyType.SWING_TRADING
        elif strategy_type == "long_term":
            strategy_type_enum = StrategyType.LONG_TERM
        
        # 전략 설정 생성
        config = StrategyConfig(
            name=name,
            strategy_type=strategy_type_enum,
            parameters=parameters,
            risk_per_trade=risk_per_trade,
            max_positions=max_positions,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
        
        # 전략 생성
        strategy_id = strategy_manager.create_strategy(name, strategy_type_enum, config)
        
        return {
            "strategy_id": strategy_id,
            "message": "Strategy created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create strategy: {str(e)}")


@router.get("/commission/info")
async def get_commission_info(exchange: str = Query("bithumb")):
    """수수료 정보 조회"""
    try:
        from core.commission import commission_calculator
        
        exchange_type = ExchangeType.BITHUMB if exchange == "bithumb" else ExchangeType.UPBIT
        commission_info = commission_calculator.get_commission_info(exchange_type)
        
        return commission_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get commission info: {str(e)}")


@router.post("/commission/calculate")
async def calculate_commission(
    amount: float = Body(...),
    price: float = Body(...),
    exchange: str = Body("bithumb"),
    is_maker: bool = Body(False)
):
    """수수료 계산"""
    try:
        from core.commission import commission_calculator
        
        exchange_type = ExchangeType.BITHUMB if exchange == "bithumb" else ExchangeType.UPBIT
        commission = commission_calculator.calculate_commission(
            amount, price, exchange_type, is_maker
        )
        
        return {
            "amount": amount,
            "price": price,
            "trade_value": amount * price,
            "commission": commission,
            "commission_rate": commission / (amount * price) if amount * price > 0 else 0,
            "net_amount": amount * price - commission
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate commission: {str(e)}")


@router.get("/performance/compare")
async def compare_strategies(
    strategy_ids: List[str] = Query(...),
    initial_capital: float = Query(1000000),
    commission_rate: float = Query(0.0015)
):
    """전략 성과 비교"""
    try:
        results = []
        
        for strategy_id in strategy_ids:
            # 전략 조회
            strategy_info = strategy_manager.get_strategy_info(strategy_id)
            if not strategy_info:
                continue
            
            # 전략 인스턴스 가져오기
            strategy = strategy_manager.strategies[strategy_id].strategy
            
            # 샘플 데이터 생성
            data = generate_sample_data(30)
            
            # 백테스트 실행
            engine = BacktestEngine(
                initial_capital=initial_capital,
                commission_rate=commission_rate
            )
            
            result = engine.run_backtest(strategy, data)
            
            results.append({
                "strategy_id": strategy_id,
                "strategy_name": strategy_info['name'],
                "total_return": result.total_return,
                "annualized_return": result.annualized_return,
                "max_drawdown": result.max_drawdown,
                "sharpe_ratio": result.sharpe_ratio,
                "win_rate": result.win_rate,
                "total_trades": result.total_trades,
                "net_profit": result.net_profit,
                "commission_impact": result.commission_impact
            })
        
        return {
            "comparison": results,
            "summary": {
                "best_return": max(results, key=lambda x: x['total_return']) if results else None,
                "best_sharpe": max(results, key=lambda x: x['sharpe_ratio']) if results else None,
                "lowest_drawdown": min(results, key=lambda x: x['max_drawdown']) if results else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare strategies: {str(e)}")
