"""
실시간 모니터링 대시보드 테스트
"""
import asyncio
import websockets
import json
import traceback
import sys

async def test_websocket_connection():
    """WebSocket 연결 테스트"""
    try:
        print("=== 실시간 모니터링 WebSocket 테스트 ===")
        
        # WebSocket 연결
        uri = "ws://localhost:8000/api/v1/monitoring/ws"
        print(f"WebSocket 연결 시도: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 연결 성공")
            
            # 10초간 실시간 데이터 수신
            print("📡 실시간 데이터 수신 중... (10초)")
            for i in range(10):
                try:
                    # 메시지 수신 (타임아웃 2초)
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    data = json.loads(message)
                    
                    print(f"📊 데이터 수신 ({i+1}/10):")
                    print(f"   타입: {data.get('type', 'unknown')}")
                    print(f"   타임스탬프: {data.get('timestamp', 'unknown')}")
                    
                    if 'dashboard' in data:
                        dashboard = data['dashboard']
                        print(f"   💰 총 잔고: {dashboard.get('total_balance', 0):,.0f}원")
                        print(f"   📈 총 수익률: {dashboard.get('total_return', 0):.2f}%")
                        print(f"   📊 일일 PnL: {dashboard.get('daily_pnl', 0):,.0f}원")
                        print(f"   🎯 활성 전략: {dashboard.get('active_strategies', 0)}개")
                        print(f"   📍 오픈 포지션: {dashboard.get('open_positions', 0)}개")
                        print(f"   🔄 총 거래: {dashboard.get('total_trades', 0)}회")
                        print(f"   🏆 승률: {dashboard.get('win_rate', 0):.1f}%")
                        print(f"   📊 샤프 비율: {dashboard.get('sharpe_ratio', 0):.2f}")
                        print(f"   📉 최대 낙폭: {dashboard.get('max_drawdown', 0):.2f}%")
                    
                    if 'performance' in data:
                        performance = data['performance']
                        print(f"   📈 연환산 수익률: {performance.get('annualized_return', 0):.2f}%")
                        print(f"   📊 변동성: {performance.get('volatility', 0):.2f}")
                        print(f"   🎯 수익 팩터: {performance.get('profit_factor', 0):.2f}")
                        print(f"   💸 수수료 영향: {performance.get('commission_impact', 0):.2f}%")
                    
                    print("   " + "="*50)
                    
                except asyncio.TimeoutError:
                    print(f"   ⏰ 타임아웃 ({i+1}/10)")
                except Exception as e:
                    print(f"   ❌ 데이터 수신 오류: {e}")
            
            print("✅ WebSocket 테스트 완료")
            
    except websockets.exceptions.ConnectionRefused:
        print("❌ WebSocket 연결 실패: 서버가 실행 중이 아닙니다")
        print("   서버를 먼저 시작하세요: python main.py")
    except Exception as e:
        print(f"❌ WebSocket 테스트 오류: {e}")
        print(f"❌ 에러 타입: {type(e).__name__}")
        traceback.print_exc()
        sys.exit(1)

async def test_http_endpoints():
    """HTTP 엔드포인트 테스트"""
    try:
        print("\n=== HTTP 엔드포인트 테스트 ===")
        
        import aiohttp
        
        base_url = "http://localhost:8000"
        
        # 대시보드 데이터 조회
        print("1. 대시보드 데이터 조회...")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/v1/monitoring/dashboard") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ 대시보드 데이터 조회 성공")
                    print(f"   💰 총 잔고: {data.get('total_balance', 0):,.0f}원")
                    print(f"   📈 총 수익률: {data.get('total_return', 0):.2f}%")
                    print(f"   📊 일일 PnL: {data.get('daily_pnl', 0):,.0f}원")
                else:
                    print(f"❌ 대시보드 데이터 조회 실패: {response.status}")
            
            # 성과 지표 조회
            print("2. 성과 지표 조회...")
            async with session.get(f"{base_url}/api/v1/monitoring/performance") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ 성과 지표 조회 성공")
                    print(f"   📈 총 수익률: {data.get('total_return', 0):.2f}%")
                    print(f"   📊 샤프 비율: {data.get('sharpe_ratio', 0):.2f}")
                    print(f"   🏆 승률: {data.get('win_rate', 0):.1f}%")
                else:
                    print(f"❌ 성과 지표 조회 실패: {response.status}")
            
            # 헬스 체크
            print("3. 헬스 체크...")
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ 헬스 체크 성공: {data.get('status', 'unknown')}")
                else:
                    print(f"❌ 헬스 체크 실패: {response.status}")
        
    except aiohttp.ClientConnectorError:
        print("❌ HTTP 연결 실패: 서버가 실행 중이 아닙니다")
        print("   서버를 먼저 시작하세요: python main.py")
    except Exception as e:
        print(f"❌ HTTP 테스트 오류: {e}")
        print(f"❌ 에러 타입: {type(e).__name__}")
        traceback.print_exc()

async def main():
    """메인 테스트 함수"""
    print("🚀 실시간 모니터링 대시보드 테스트 시작")
    
    # HTTP 엔드포인트 테스트
    await test_http_endpoints()
    
    # WebSocket 연결 테스트
    await test_websocket_connection()
    
    print("\n🎉 모든 테스트 완료!")

if __name__ == "__main__":
    asyncio.run(main())
