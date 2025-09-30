"""
간단한 기술적 분석 테스트
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.technical_indicators import technical_analyzer


def generate_simple_data(days: int = 10) -> pd.DataFrame:
    """간단한 샘플 데이터 생성"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                         end=datetime.now(), freq='1H')
    
    # 간단한 가격 데이터 생성
    np.random.seed(42)
    base_price = 50000
    prices = []
    
    for i in range(len(dates)):
        if i == 0:
            price = base_price
        else:
            change = np.random.normal(0, 100)
            price = prices[-1] + change
        prices.append(max(price, 1000))
    
    # OHLCV 데이터 생성
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        if i == 0:
            open_price = close
        else:
            open_price = prices[i-1]
        
        high = max(open_price, close) + np.random.uniform(0, 50)
        low = min(open_price, close) - np.random.uniform(0, 50)
        volume = np.random.uniform(1000, 5000)
        
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


def test_basic_indicators():
    """기본 지표 테스트"""
    print("🔍 기본 기술적 지표 테스트 시작...")
    
    try:
        # 샘플 데이터 생성
        data = generate_simple_data(10)
        print(f"✅ 샘플 데이터 생성 완료: {len(data)}개 캔들")
        
        # 기본 지표 계산
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 이동평균선
        sma_20 = technical_analyzer.calculate_sma(close, 20)
        ema_21 = technical_analyzer.calculate_ema_talib(close, 21)
        
        print(f"✅ SMA 20: {sma_20.iloc[-1]:.2f}")
        print(f"✅ EMA 21: {ema_21.iloc[-1]:.2f}")
        
        # RSI
        rsi = technical_analyzer.calculate_rsi(close, 14)
        print(f"✅ RSI 14: {rsi.iloc[-1]:.2f}")
        
        # MACD
        macd_data = technical_analyzer.calculate_macd(close)
        print(f"✅ MACD: {macd_data['macd'].iloc[-1]:.2f}")
        print(f"✅ MACD Signal: {macd_data['signal'].iloc[-1]:.2f}")
        
        # 볼린저 밴드
        bb_data = technical_analyzer.calculate_bollinger_bands(close)
        print(f"✅ BB Upper: {bb_data['upper'].iloc[-1]:.2f}")
        print(f"✅ BB Middle: {bb_data['middle'].iloc[-1]:.2f}")
        print(f"✅ BB Lower: {bb_data['lower'].iloc[-1]:.2f}")
        
        # 신호 생성
        signals = technical_analyzer.generate_signals(data)
        print(f"✅ 생성된 신호: {len(signals)}개")
        
        for signal in signals:
            print(f"  - {signal.signal_type.value}: {signal.description}")
        
        return True
        
    except Exception as e:
        print(f"❌ 기본 지표 테스트 실패: {e}")
        return False


def test_api_integration():
    """API 통합 테스트"""
    print("\n🔍 API 통합 테스트 시작...")
    
    try:
        # FastAPI 서버가 실행 중인지 확인
        import requests
        
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ FastAPI 서버 연결 성공")
            else:
                print("❌ FastAPI 서버 응답 오류")
                return False
        except requests.exceptions.RequestException:
            print("❌ FastAPI 서버 연결 실패 - 서버가 실행 중인지 확인하세요")
            return False
        
        # 분석 API 테스트
        try:
            response = requests.get("http://localhost:8000/api/v1/analysis/indicators/BTC", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print("✅ 분석 API 응답 성공")
                print(f"  - 지표 개수: {len(data.get('indicators', {}))}")
                return True
            else:
                print(f"❌ 분석 API 응답 오류: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 분석 API 요청 실패: {e}")
            return False
        
    except ImportError:
        print("❌ requests 모듈이 설치되지 않음 - pip install requests")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 간단한 기술적 분석 테스트 시작\n")
    
    # 1. 기본 지표 테스트
    indicators_success = test_basic_indicators()
    
    # 2. API 통합 테스트
    api_success = test_api_integration()
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 간단한 기술적 분석 테스트 결과")
    print("="*50)
    print(f"기본 지표: {'✅ 성공' if indicators_success else '❌ 실패'}")
    print(f"API 통합: {'✅ 성공' if api_success else '❌ 실패'}")
    
    if indicators_success:
        print("\n🎉 기술적 분석 엔진이 정상적으로 작동합니다!")
    else:
        print("\n⚠️ 기술적 분석 엔진에 문제가 있습니다.")


if __name__ == "__main__":
    main()
