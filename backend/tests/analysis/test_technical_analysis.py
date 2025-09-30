"""
기술적 분석 엔진 테스트 스크립트
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.technical_indicators import TechnicalAnalyzer, technical_analyzer
from analysis.pattern_recognition import PatternRecognizer, pattern_recognizer
from analysis.multi_timeframe import MultiTimeframeAnalyzer, multi_timeframe_analyzer


def generate_sample_data(days: int = 100) -> pd.DataFrame:
    """샘플 데이터 생성"""
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                         end=datetime.now(), freq='1min')
    
    # 랜덤 워크로 가격 데이터 생성
    np.random.seed(42)
    price = 50000  # 시작 가격
    prices = [price]
    
    for _ in range(len(dates) - 1):
        change = np.random.normal(0, 100)  # 평균 0, 표준편차 100의 변화
        price += change
        prices.append(max(price, 1000))  # 최소 가격 1000
    
    # OHLCV 데이터 생성
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        if i == 0:
            open_price = close
        else:
            open_price = prices[i-1]
        
        high = max(open_price, close) + np.random.uniform(0, 200)
        low = min(open_price, close) - np.random.uniform(0, 200)
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


def test_technical_indicators():
    """기술적 지표 테스트"""
    print("🔍 기술적 지표 테스트 시작...")
    
    try:
        # 샘플 데이터 생성
        data = generate_sample_data(100)
        print(f"✅ 샘플 데이터 생성 완료: {len(data)}개 캔들")
        
        # 기술적 지표 계산
        analyzer = technical_analyzer
        
        # 모든 지표 계산
        indicators = analyzer.calculate_all_indicators(data)
        print(f"✅ 기술적 지표 계산 완료: {len(indicators)}개 지표")
        
        # 주요 지표 출력
        print("\n📊 주요 지표 값:")
        for name, values in indicators.items():
            if not pd.isna(values.iloc[-1]):
                print(f"  {name}: {values.iloc[-1]:.4f}")
        
        # 신호 생성
        signals = analyzer.generate_signals(data)
        print(f"\n📈 생성된 신호: {len(signals)}개")
        
        for signal in signals:
            print(f"  - {signal.signal_type.value}: {signal.description} (강도: {signal.strength:.2f}, 신뢰도: {signal.confidence:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ 기술적 지표 테스트 실패: {e}")
        return False


def test_pattern_recognition():
    """패턴 인식 테스트"""
    print("\n🔍 패턴 인식 테스트 시작...")
    
    try:
        # 샘플 데이터 생성
        data = generate_sample_data(100)
        
        # 패턴 탐지
        recognizer = pattern_recognizer
        patterns = recognizer.detect_all_patterns(data)
        
        print(f"✅ 패턴 탐지 완료: {len(patterns)}개 패턴")
        
        # 탐지된 패턴 출력
        for pattern in patterns:
            print(f"  - {pattern.pattern_name}: {pattern.description} (신뢰도: {pattern.confidence:.2f}, 강도: {pattern.strength:.2f})")
        
        return True
        
    except Exception as e:
        print(f"❌ 패턴 인식 테스트 실패: {e}")
        return False


def test_multi_timeframe_analysis():
    """멀티 타임프레임 분석 테스트"""
    print("\n🔍 멀티 타임프레임 분석 테스트 시작...")
    
    try:
        # 샘플 데이터 생성
        data = generate_sample_data(200)  # 더 많은 데이터 필요
        
        # 멀티 타임프레임 분석
        analyzer = multi_timeframe_analyzer
        
        # 타임프레임별 분석
        timeframe_summary = analyzer.get_timeframe_summary(data)
        print("✅ 타임프레임별 분석 완료:")
        
        for timeframe, summary in timeframe_summary.items():
            print(f"  {timeframe}: {summary['trend']} (강도: {summary['strength']:.2f}, 신호: {summary['signal_count']}개)")
        
        # 종합 분석
        multi_signal = analyzer.analyze_multi_timeframe(data)
        print(f"\n📊 종합 분석 결과:")
        print(f"  주요 신호: {multi_signal.primary_signal.signal_type.value}")
        print(f"  전체 강도: {multi_signal.overall_strength:.2f}")
        print(f"  전체 신뢰도: {multi_signal.overall_confidence:.2f}")
        print(f"  타임프레임 정렬: {multi_signal.timeframe_alignment}")
        print(f"  트렌드 방향: {multi_signal.trend_direction}")
        print(f"  지원 신호: {len(multi_signal.supporting_signals)}개")
        print(f"  충돌 신호: {len(multi_signal.conflicting_signals)}개")
        
        return True
        
    except Exception as e:
        print(f"❌ 멀티 타임프레임 분석 테스트 실패: {e}")
        return False


def test_performance():
    """성능 테스트"""
    print("\n🔍 성능 테스트 시작...")
    
    try:
        import time
        
        # 다양한 크기의 데이터로 성능 테스트
        test_sizes = [100, 500, 1000]
        
        for size in test_sizes:
            print(f"\n📊 데이터 크기: {size}개 캔들")
            
            data = generate_sample_data(size)
            
            # 기술적 지표 성능
            start_time = time.time()
            analyzer = technical_analyzer
            indicators = analyzer.calculate_all_indicators(data)
            signals = analyzer.generate_signals(data)
            end_time = time.time()
            
            print(f"  기술적 지표: {end_time - start_time:.3f}초")
            
            # 패턴 인식 성능
            start_time = time.time()
            recognizer = pattern_recognizer
            patterns = recognizer.detect_all_patterns(data)
            end_time = time.time()
            
            print(f"  패턴 인식: {end_time - start_time:.3f}초")
            
            # 멀티 타임프레임 성능
            start_time = time.time()
            multi_analyzer = multi_timeframe_analyzer
            multi_signal = multi_analyzer.analyze_multi_timeframe(data)
            end_time = time.time()
            
            print(f"  멀티 타임프레임: {end_time - start_time:.3f}초")
        
        return True
        
    except Exception as e:
        print(f"❌ 성능 테스트 실패: {e}")
        return False


def main():
    """메인 테스트 함수"""
    print("🚀 기술적 분석 엔진 테스트 시작\n")
    
    # 1. 기술적 지표 테스트
    indicators_success = test_technical_indicators()
    
    # 2. 패턴 인식 테스트
    patterns_success = test_pattern_recognition()
    
    # 3. 멀티 타임프레임 분석 테스트
    multi_timeframe_success = test_multi_timeframe_analysis()
    
    # 4. 성능 테스트
    performance_success = test_performance()
    
    # 결과 요약
    print("\n" + "="*50)
    print("📊 기술적 분석 엔진 테스트 결과 요약")
    print("="*50)
    print(f"기술적 지표: {'✅ 성공' if indicators_success else '❌ 실패'}")
    print(f"패턴 인식: {'✅ 성공' if patterns_success else '❌ 실패'}")
    print(f"멀티 타임프레임: {'✅ 성공' if multi_timeframe_success else '❌ 실패'}")
    print(f"성능 테스트: {'✅ 성공' if performance_success else '❌ 실패'}")
    
    if all([indicators_success, patterns_success, multi_timeframe_success, performance_success]):
        print("\n🎉 모든 기술적 분석 엔진 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 설정을 확인해주세요.")


if __name__ == "__main__":
    main()
