# 자동거래 시스템 사용 가이드

## 🚀 기능 개요

AI 추천 전략을 선택하면 **실제 자동거래**가 시작됩니다!

### 구현된 기능

✅ **1. 전략 선택 시 자동 주문 실행**
- AI가 추천한 전략을 선택하면 즉시 거래 시작
- 기술적 지표와 ML 신호 기반 자동 매수/매도

✅ **2. 빗썸 API를 통한 실제 주문**
- 페이퍼 트레이딩(모의 거래) 모드
- 실거래 모드 (API 키 설정 시)

✅ **3. 포지션 관리 및 리스크 관리**
- 자본의 30% 최대 포지션 크기
- 거래당 2% 리스크 제한
- 자동 손절/익절 기능

✅ **4. 손절/익절 자동 실행**
- 5% 손실 시 자동 손절
- 10% 수익 시 자동 익절
- 10초마다 포지션 모니터링

---

## 🎯 거래 모드

### 1. 페이퍼 트레이딩 (기본값)
```javascript
{
  "strategy_id": "aggressive_buy_strategy",
  "auto_switch": true,
  "max_risk": 0.02,
  "trading_mode": "paper",      // 모의 거래
  "initial_capital": 1000000    // 초기 자본 100만원
}
```

- 💡 **실제 자금 없이 거래 테스트**
- 실시간 시세로 모의 거래
- 손익 계산 및 통계 제공

### 2. 실거래 모드
```javascript
{
  "strategy_id": "aggressive_buy_strategy",
  "auto_switch": true,
  "max_risk": 0.02,
  "trading_mode": "live",       // 실제 거래
  "initial_capital": 1000000
}
```

- ⚠️ **실제 자금으로 거래**
- 빗썸 API 키 설정 필요
- 실제 주문 실행 및 체결

---

## 📊 전략별 거래 방식

### 1. 적극적 매수 전략 (Momentum)
```
- BTC, ETH, XRP 중 ML 신호가 BUY인 코인 매수
- 신뢰도 70% 이상일 때 실행
- 포지션 크기: 자본의 30% × 신뢰도
```

### 2. 스캘핑 전략 (Scalping)
```
- RSI < 30: 매수 (과매도)
- RSI > 70: 매도 (과매수)
- 소액 고빈도 거래
```

### 3. 스윙 트레이딩 전략
```
- 골든크로스(SMA 5 > SMA 20): 매수
- 데드크로스(SMA 5 < SMA 20): 매도
- 중기 트렌드 추종
```

### 4. DCA 전략 (Dollar Cost Averaging)
```
- BTC, ETH에 정기적으로 분할 매수
- 각 코인에 자본의 5%씩 투자
- 변동성 분산 효과
```

---

## 🔧 API 엔드포인트

### 전략 선택 (거래 시작)
```http
POST /api/v1/ai/select-strategy
Content-Type: application/json

{
  "strategy_id": "aggressive_buy_strategy",
  "auto_switch": true,
  "max_risk": 0.02,
  "trading_mode": "paper",
  "initial_capital": 1000000
}
```

### 거래 상태 조회
```http
GET /api/v1/ai/trading-status

Response:
{
  "success": true,
  "is_trading": true,
  "strategy": {
    "id": "aggressive_buy_strategy",
    "name": "적극적 매수 전략",
    "type": "momentum",
    "started_at": "2025-10-01T12:30:00"
  },
  "trading": {
    "mode": "paper",
    "initial_capital": 1000000,
    "current_capital": 1025000,
    "total_pnl": 25000,
    "pnl_percentage": 2.5,
    "positions": {
      "BTC": {
        "amount": 0.005,
        "avg_price": 163000000,
        "side": "long"
      }
    },
    "total_trades": 3
  }
}
```

### 거래 중지
```http
POST /api/v1/ai/stop-autotrading

Response:
{
  "success": true,
  "message": "'적극적 매수 전략' 전략이 중지되었습니다",
  "trading_result": {
    "final_capital": 1025000,
    "total_pnl": 25000,
    "total_trades": 3
  }
}
```

---

## ⚙️ 리스크 관리 설정

### 기본 설정
```python
max_position_size = 0.3        # 자본의 30%
max_risk_per_trade = 0.02      # 거래당 2% 리스크
stop_loss_pct = 0.05           # 5% 손절
take_profit_pct = 0.10         # 10% 익절
```

### 커미션 계산
```python
# 빗썸 수수료
maker_fee = 0.25%
taker_fee = 0.25%
```

---

## 📝 로그 예시

### 페이퍼 트레이딩
```
2025-10-01 12:30:15 INFO 자동거래 시작: 적극적 매수 전략
2025-10-01 12:30:15 INFO 거래 모드: paper
2025-10-01 12:30:15 INFO 초기 자본: 1,000,000원
2025-10-01 12:30:16 INFO 📈 [PAPER] BTC 매수: 0.00500000 @ 163,000,000원 (신뢰도: 80.0%)
2025-10-01 12:35:20 INFO 📈 [PAPER] ETH 매수: 0.04000000 @ 5,913,400원 (신뢰도: 60.0%)
2025-10-01 12:45:30 INFO ✅ BTC 익절 실행: 10.2%
2025-10-01 12:45:31 INFO 📉 [PAPER] BTC 매도: 0.00500000 @ 179,626,000원 (손익: +83,130원)
```

### 실거래
```
2025-10-01 12:30:15 INFO 자동거래 시작: 적극적 매수 전략
2025-10-01 12:30:15 INFO 거래 모드: live
2025-10-01 12:30:16 INFO 📈 [LIVE] BTC 매수 주문: {'order_id': '1234567890', 'status': 'placed'}
```

---

## ⚠️ 주의사항

### 1. 페이퍼 트레이딩으로 먼저 테스트
- 실제 자금 투입 전 충분한 테스트 필수
- 전략 성능 검증 후 실거래 진행

### 2. API 키 보안
- 빗썸 API 키를 안전하게 보관
- 읽기 전용 키는 사용 불가 (주문 권한 필요)
- IP 화이트리스트 설정 권장

### 3. 리스크 관리
- 투자 가능 금액의 일부만 사용
- 손절선 반드시 설정
- 과도한 레버리지 지양

### 4. 시장 모니터링
- 급격한 시장 변동 시 수동 개입 필요
- 전략 성능 정기 점검
- 손실 한도 설정

---

## 🔐 실거래 설정 방법

### 1. 빗썸 API 키 발급
1. 빗썸 로그인
2. 설정 > API 관리
3. API 키 생성 (주문 권한 포함)
4. API Key와 Secret Key 저장

### 2. 환경변수 설정
```bash
# .env 파일
BITHUMB_API_KEY=your_api_key_here
BITHUMB_SECRET_KEY=your_secret_key_here
```

### 3. 실거래 모드로 전략 선택
```javascript
// 프론트엔드에서
await api.selectStrategy({
  strategy_id: "aggressive_buy_strategy",
  auto_switch: true,
  max_risk: 0.02,
  trading_mode: "live",        // 실거래!
  initial_capital: 1000000
});
```

---

## 📈 성과 모니터링

### 대시보드에서 확인 가능한 정보
- 실시간 수익/손실 (PnL)
- 현재 포지션 현황
- 거래 내역
- 전략 성과 지표
- 리스크 지표

### API로 조회
```javascript
// 거래 상태 조회
const status = await api.getTradingStatus();

console.log(`현재 자본: ${status.trading.current_capital.toLocaleString()}원`);
console.log(`총 손익: ${status.trading.total_pnl.toLocaleString()}원`);
console.log(`수익률: ${status.trading.pnl_percentage.toFixed(2)}%`);
```

---

## 🚨 비상 대응

### 긴급 중지
```javascript
// 모든 거래 즉시 중지 및 포지션 청산
await api.stopAutoTrading();
```

### 로그 확인
```bash
tail -f /tmp/autotrade_backend.log
```

---

## 💡 팁

1. **처음 사용 시**: 페이퍼 트레이딩으로 1주일 이상 테스트
2. **소액부터 시작**: 실거래는 소액부터 점진적으로 증액
3. **다양한 전략 테스트**: 시장 상황에 맞는 전략 선택
4. **정기 점검**: 주 1회 이상 전략 성과 분석
5. **손절 준수**: 감정적 판단 배제, 시스템 신뢰

---

## 📚 참고 문서

- [빗썸 API 문서](https://apidocs.bithumb.com/)
- [기술적 지표 설명](./docs/technical_indicators.md)
- [전략 백테스팅 가이드](./docs/backtesting_guide.md)

