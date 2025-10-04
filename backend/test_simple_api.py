"""
간단한 API 테스트 서버
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="AutoTrade Test API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AutoTrade API is running!", "status": "success"}

@app.get("/api/v1/strategy/list")
async def get_strategies():
    return {
        "strategies": [
            {
                "id": 1,
                "name": "테스트 전략",
                "strategy_type": "scalping",
                "is_active": True,
                "risk_per_trade": 0.02,
                "max_positions": 5,
                "created_at": "2024-01-01T00:00:00Z"
            }
        ],
        "total": 1,
        "message": "전략 목록을 성공적으로 조회했습니다"
    }

@app.get("/api/v1/monitoring/dashboard")
async def get_dashboard():
    return {
        "portfolio": {
            "totalValue": 1000000,
            "totalReturn": 0.05,
            "totalReturnRate": 5.0,
            "todayReturn": 0.01,
            "todayReturnRate": 1.0
        },
        "strategies": [
            {
                "id": 1,
                "name": "테스트 전략",
                "strategy_type": "scalping",
                "is_active": True,
                "returnRate": 5.2
            }
        ],
        "recentTrades": [],
        "performance": [
            {"date": "2024-01-01", "value": 1000000},
            {"date": "2024-01-02", "value": 1050000}
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


