"""
거래 관련 API 엔드포인트
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from services.bithumb_client import BithumbClient

router = APIRouter()


@router.get("/tickers")
async def get_tickers():
    """전체 코인 시세 조회"""
    try:
        async with BithumbClient() as client:
            ticker_data = await client.get_ticker("ALL")
            return {
                "success": True,
                "data": ticker_data.get("data", {}),
                "message": "시세 조회 성공"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시세 조회 실패: {str(e)}")


@router.get("/orderbook/{coin}")
async def get_orderbook(coin: str):
    """호가창 조회"""
    try:
        async with BithumbClient() as client:
            orderbook_data = await client.get_orderbook(coin)
            return {
                "success": True,
                "data": orderbook_data.get("data", {}),
                "message": f"{coin} 호가창 조회 성공"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"호가창 조회 실패: {str(e)}")


@router.get("/transactions/{coin}")
async def get_transactions(coin: str):
    """체결 내역 조회"""
    try:
        async with BithumbClient() as client:
            transaction_data = await client.get_transaction_history(coin)
            return {
                "success": True,
                "data": transaction_data.get("data", []),
                "message": f"{coin} 체결 내역 조회 성공"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"체결 내역 조회 실패: {str(e)}")


@router.get("/balance")
async def get_balance():
    """잔고 조회"""
    try:
        async with BithumbClient() as client:
            balance_data = await client.get_balance()
            return {
                "success": True,
                "data": balance_data.get("data", {}),
                "message": "잔고 조회 성공"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"잔고 조회 실패: {str(e)}")


@router.get("/orders/active")
async def get_active_orders():
    """활성 주문 조회"""
    try:
        async with BithumbClient() as client:
            orders_data = await client.get_orders()
            return {
                "success": True,
                "data": orders_data.get("data", []),
                "message": "활성 주문 조회 성공"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"활성 주문 조회 실패: {str(e)}")


@router.get("/orders/history")
async def get_order_history():
    """주문 내역 조회"""
    try:
        async with BithumbClient() as client:
            transactions_data = await client.get_user_transactions()
            return {
                "success": True,
                "data": transactions_data.get("data", []),
                "message": "주문 내역 조회 성공"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주문 내역 조회 실패: {str(e)}")
