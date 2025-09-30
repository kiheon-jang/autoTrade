"""
AI 추천 시스템만을 위한 최소 서버
데이터베이스 의존성 없이 AI 추천 기능만 테스트
"""
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
from datetime import datetime

from api.ai_recommendation import router as ai_router

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="AI Strategy Recommendation API",
    description="AI 기반 전략 추천 시스템",
    version="1.0.0"
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AI 추천 라우터만 등록
app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI추천"])


# 더미 모니터링 엔드포인트 추가 (프론트엔드 호환성)
@app.get("/api/v1/monitoring/dashboard")
async def get_dashboard():
    """대시보드 데이터 (더미)"""
    return {
        "portfolio": {
            "total_value": 1000000,
            "total_return": 50000,
            "total_return_rate": 5.0,
            "today_return": 10000,
            "today_return_rate": 1.0,
        },
        "strategies": [
            {
                "id": "1",
                "name": "AI 추천 전략",
                "type": "ai_recommendation",
                "is_active": True,
                "performance": 8.5
            }
        ],
        "recent_trades": [
            {
                "id": "1",
                "symbol": "BTC",
                "type": "buy",
                "amount": 0.1,
                "price": 50000,
                "timestamp": "2025-10-01T08:00:00Z"
            }
        ],
        "performance": [
            {"date": "2025-10-01", "value": 1000000},
            {"date": "2025-10-02", "value": 1050000},
            {"date": "2025-10-03", "value": 1020000}
        ]
    }


@app.get("/api/v1/monitoring/portfolio")
async def get_portfolio():
    """포트폴리오 현황 (더미)"""
    return {
        "total_value": 1000000,
        "total_return": 50000,
        "total_return_rate": 5.0,
        "today_return": 10000,
        "today_return_rate": 1.0,
        "positions": [
            {
                "symbol": "BTC",
                "amount": 0.1,
                "value": 50000,
                "return_rate": 5.2
            },
            {
                "symbol": "ETH",
                "amount": 1.0,
                "value": 3000,
                "return_rate": 3.8
            }
        ],
        "cash_balance": 470000,
        "message": "포트폴리오 현황을 성공적으로 조회했습니다"
    }


# 더미 WebSocket 엔드포인트
@app.websocket("/api/v1/monitoring/ws")
async def websocket_endpoint(websocket):
    """WebSocket 엔드포인트 (더미)"""
    await websocket.accept()
    try:
        while True:
            # 간단한 하트비트 메시지 전송
            await websocket.send_text('{"type": "heartbeat", "timestamp": "' + str(datetime.now()) + '"}')
            await asyncio.sleep(30)  # 30초마다 하트비트
    except Exception as e:
        print(f"WebSocket 오류: {e}")
    finally:
        await websocket.close()


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "AI 전략 추천 시스템 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "ai_server:app",
        host="0.0.0.0",
        port=8010,
        reload=True,
        log_level="info"
    )
