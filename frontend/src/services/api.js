import axios from 'axios';

// 백엔드 API 기본 설정
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8008';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터
api.interceptors.request.use(
  (config) => {
    // 토큰이 있으면 헤더에 추가
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터
api.interceptors.response.use(
  (response) => {
    // 자동으로 response.data 반환
    return response.data;
  },
  (error) => {
    if (error.response?.status === 401) {
      // 인증 오류 시 로그아웃
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 백엔드 API 엔드포인트를 그대로 사용
export const strategyAPI = {
  // 전략 목록 조회
  getStrategies: () => api.get('/api/v1/strategy/list'),
  
  // 전략 상세 조회
  getStrategy: (id) => api.get(`/api/v1/strategy/${id}`),
  
  // 전략 생성
  createStrategy: (data) => api.post('/api/v1/strategy/create', data),
  
  // 전략 시작
  startStrategy: (id) => api.put(`/api/v1/strategy/${id}/start`),
  
  // 전략 중지
  stopStrategy: (id) => api.put(`/api/v1/strategy/${id}/stop`),
  
  // 전략 삭제
  deleteStrategy: (id) => api.delete(`/api/v1/strategy/${id}`),
};

// 백테스팅 API (백엔드 엔드포인트 사용)
export const backtestingAPI = {
  // 백테스팅 실행
  runBacktest: (data) => api.post('/api/v1/backtesting/run', data),
  
  // 백테스팅 결과 조회
  getBacktestResult: (id) => api.get(`/api/v1/backtesting/result/${id}`),
};

// 모니터링 API (백엔드 엔드포인트 사용)
export const monitoringAPI = {
  // 대시보드 데이터
  getDashboard: () => api.get('/api/v1/monitoring/dashboard'),
  
  // 포트폴리오 현황
  getPortfolio: () => api.get('/api/v1/monitoring/portfolio'),
  
  // 거래 내역
  getTrades: (params) => api.get('/api/v1/monitoring/trades', { params }),
  
  // 실시간 데이터
  getRealtimeData: () => api.get('/api/v1/monitoring/realtime'),
  
  // 성과 지표
  getPerformance: () => api.get('/api/v1/monitoring/performance'),
  
  // 거래 로그
  getLogs: (limit = 100) => api.get('/api/v1/monitoring/logs', { params: { limit } }),
  
  // 알림
  getAlerts: () => api.get('/api/v1/monitoring/alerts'),
};

// AI 추천 API (백엔드 엔드포인트 사용)
export const aiRecommendationAPI = {
  // 시장 분석 및 전략 추천
  analyzeMarketAndRecommend: (data) => api.post('/api/v1/ai/analyze-market', data),
  
  // 전략 선택 (실제 거래 시작)
  selectStrategy: (data) => api.post('/api/v1/ai/select-strategy', data),
  
  // 현재 추천 조회
  getCurrentRecommendations: () => api.get('/api/v1/ai/current-recommendations'),
  
  // 추천 히스토리
  getRecommendationHistory: (limit = 20) => api.get('/api/v1/ai/recommendation-history', { params: { limit } }),
  
  // 활성 전략 조회
  getActiveStrategy: () => api.get('/api/v1/ai/active-strategy'),
  
  // 거래 상태 조회
  getTradingStatus: () => api.get('/api/v1/ai/trading-status'),
  
  // 오토트레이딩 중지
  stopAutoTrading: () => api.post('/api/v1/ai/stop-autotrading'),
  
  // 사용자 선호도 설정
  setUserPreferences: (data) => api.post('/api/v1/ai/user-preferences', data),
  
  // 사용자 선호도 조회
  getUserPreferences: () => api.get('/api/v1/ai/user-preferences'),
};

// 전통적 전략 API
export const traditionalStrategyAPI = {
  // 전통적 전략 분석
  analyzeTraditionalStrategies: (data) => api.post('/api/v1/ai/traditional-strategies', data),
  
  // 전통적 전략 선택 및 실행
  selectTraditionalStrategy: (strategyType, symbols) => api.post(`/api/v1/ai/select-traditional-strategy?strategy_type=${strategyType}`, symbols),
  
  // 전통적 전략 중지
  stopTraditionalStrategy: () => api.post('/api/v1/ai/stop-traditional-strategy'),
};

// 통합 API 객체
export const apiService = {
  ...strategyAPI,
  ...backtestingAPI,
  ...monitoringAPI,
  ...aiRecommendationAPI,
};

export default api;
