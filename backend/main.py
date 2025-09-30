"""
빗썸 자동매매 시스템 메인 애플리케이션
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import logging

from core.config import settings
from api import trading, monitoring, analysis, backtesting, realtime_trading, ai_recommendation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # 시작 시 초기화 작업
    print("🚀 빗썸 자동매매 시스템 시작")
    
    # 실시간 데이터 브로드캐스트 백그라운드 태스크 시작
    from api.monitoring import broadcast_realtime_data
    broadcast_task = asyncio.create_task(broadcast_realtime_data())
    print("📡 실시간 데이터 브로드캐스트 시작")
    
    yield
    
    # 종료 시 정리 작업
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    print("🛑 빗썸 자동매매 시스템 종료")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Bithumb Auto Trading System",
    description="빗썸 API 기반 암호화폐 자동매매 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(trading.router, prefix="/api/v1/trading", tags=["거래"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["모니터링"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["분석"])
app.include_router(backtesting.router, prefix="/api/v1/backtesting", tags=["백테스팅"])
app.include_router(realtime_trading.router, prefix="/api/v1/realtime", tags=["실시간거래"])
app.include_router(ai_recommendation.router, prefix="/api/v1/ai", tags=["AI추천"])


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "빗썸 자동매매 시스템 API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8008,
        reload=True,
        log_level="info"
    )
