"""
머신러닝 기반 신호 생성 엔진
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
import joblib
import os


class MLModelType(Enum):
    """머신러닝 모델 타입"""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LOGISTIC_REGRESSION = "logistic_regression"
    ENSEMBLE = "ensemble"


@dataclass
class MLSignal:
    """ML 신호 정보"""
    signal_type: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0-1
    probability: float  # 0-1
    features_importance: Dict[str, float]
    model_used: str
    timestamp: pd.Timestamp


class MLSignalGenerator:
    """머신러닝 기반 신호 생성기"""
    
    def __init__(self, model_type: MLModelType = MLModelType.ENSEMBLE):
        self.model_type = model_type
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.is_trained = False
        
    def create_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """특성 생성"""
        df = data.copy()
        
        # 기본 가격 특성
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['high_low_ratio'] = df['high'] / df['low']
        df['close_open_ratio'] = df['close'] / df['open']
        
        # 이동평균 특성
        for period in [5, 10, 20, 50]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            df[f'price_sma_{period}_ratio'] = df['close'] / df[f'sma_{period}']
            df[f'price_ema_{period}_ratio'] = df['close'] / df[f'ema_{period}']
        
        # 변동성 특성
        df['volatility_5'] = df['returns'].rolling(5).std()
        df['volatility_20'] = df['returns'].rolling(20).std()
        df['volatility_ratio'] = df['volatility_5'] / df['volatility_20']
        
        # 거래량 특성
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['price_volume'] = df['close'] * df['volume']
        
        # 기술적 지표 특성
        from analysis.technical_indicators import TechnicalAnalyzer
        ti = TechnicalAnalyzer()
        
        # RSI
        rsi = ti.calculate_rsi(df['close'], 14)
        df['rsi'] = rsi
        df['rsi_oversold'] = (rsi < 30).astype(int)
        df['rsi_overbought'] = (rsi > 70).astype(int)
        
        # MACD
        macd_data = ti.calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        
        # 볼린저 밴드
        bb_data = ti.calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # 스토캐스틱
        stoch_data = ti.calculate_stochastic(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch_data['k']
        df['stoch_d'] = stoch_data['d']
        
        # ATR
        atr = ti.calculate_atr(df['high'], df['low'], df['close'])
        df['atr'] = atr
        df['atr_ratio'] = atr / df['close']
        
        # 지연 특성 (과거 데이터)
        for lag in [1, 2, 3, 5, 10]:
            df[f'returns_lag_{lag}'] = df['returns'].shift(lag)
            df[f'volume_ratio_lag_{lag}'] = df['volume_ratio'].shift(lag)
        
        # 롤링 통계
        for period in [5, 10, 20]:
            df[f'returns_mean_{period}'] = df['returns'].rolling(period).mean()
            df[f'returns_std_{period}'] = df['returns'].rolling(period).std()
            df[f'returns_skew_{period}'] = df['returns'].rolling(period).skew()
            df[f'returns_kurt_{period}'] = df['returns'].rolling(period).kurt()
        
        # 시장 상황 특성
        df['trend_strength'] = abs(df['price_sma_20_ratio'] - 1)
        df['volatility_regime'] = pd.cut(df['volatility_20'], 
                                        bins=[0, df['volatility_20'].quantile(0.33), 
                                              df['volatility_20'].quantile(0.67), float('inf')],
                                        labels=['low', 'medium', 'high'])
        
        return df
    
    def create_target(self, data: pd.DataFrame, future_periods: int = 5, 
                     profit_threshold: float = 0.02) -> pd.Series:
        """타겟 변수 생성 (미래 수익률 기반)"""
        future_returns = data['close'].shift(-future_periods) / data['close'] - 1
        
        # 수익률이 임계값 이상이면 매수(1), 이하면 매도(-1), 그 외는 보유(0)
        target = np.where(future_returns > profit_threshold, 1,
                         np.where(future_returns < -profit_threshold, -1, 0))
        
        return pd.Series(target, index=data.index)
    
    def prepare_training_data(self, data: pd.DataFrame, 
                            feature_columns: List[str] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """훈련 데이터 준비"""
        # 특성 생성
        df = self.create_features(data)
        
        # 타겟 생성
        target = self.create_target(df)
        
        # 특성 선택
        if feature_columns is None:
            # 수치형 특성만 선택
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            feature_columns = [col for col in numeric_columns 
                             if col not in ['open', 'high', 'low', 'close', 'volume']]
        
        self.feature_columns = feature_columns
        
        # 결측값 처리
        df_features = df[feature_columns].fillna(method='ffill').fillna(0)
        
        # 무한값 처리
        df_features = df_features.replace([np.inf, -np.inf], 0)
        
        # 타겟과 특성의 인덱스 맞추기
        valid_idx = target.notna() & df_features.notna().all(axis=1)
        
        return df_features[valid_idx], target[valid_idx]
    
    def train_models(self, X: pd.DataFrame, y: pd.Series):
        """모델 훈련"""
        # 데이터 분할
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # 특성 스케일링
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        self.scalers['main'] = scaler
        
        # 모델 훈련
        if self.model_type == MLModelType.RANDOM_FOREST:
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            model.fit(X_train_scaled, y_train)
            self.models['main'] = model
            
        elif self.model_type == MLModelType.GRADIENT_BOOSTING:
            model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            model.fit(X_train_scaled, y_train)
            self.models['main'] = model
            
        elif self.model_type == MLModelType.LOGISTIC_REGRESSION:
            model = LogisticRegression(
                random_state=42,
                class_weight='balanced',
                max_iter=1000
            )
            model.fit(X_train_scaled, y_train)
            self.models['main'] = model
            
        elif self.model_type == MLModelType.ENSEMBLE:
            # 앙상블 모델
            rf = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=42)
            gb = GradientBoostingClassifier(n_estimators=50, learning_rate=0.1, random_state=42)
            lr = LogisticRegression(random_state=42, max_iter=1000)
            
            rf.fit(X_train_scaled, y_train)
            gb.fit(X_train_scaled, y_train)
            lr.fit(X_train_scaled, y_train)
            
            self.models['random_forest'] = rf
            self.models['gradient_boosting'] = gb
            self.models['logistic_regression'] = lr
        
        # 성능 평가
        if self.model_type == MLModelType.ENSEMBLE:
            # 앙상블 예측
            rf_pred = self.models['random_forest'].predict(X_test_scaled)
            gb_pred = self.models['gradient_boosting'].predict(X_test_scaled)
            lr_pred = self.models['logistic_regression'].predict(X_test_scaled)
            
            # 투표 기반 앙상블
            ensemble_pred = np.round((rf_pred + gb_pred + lr_pred) / 3)
            accuracy = accuracy_score(y_test, ensemble_pred)
        else:
            pred = self.models['main'].predict(X_test_scaled)
            accuracy = accuracy_score(y_test, pred)
        
        print(f"모델 정확도: {accuracy:.3f}")
        self.is_trained = True
        
        return accuracy
    
    def generate_signal(self, data: pd.DataFrame) -> MLSignal:
        """ML 신호 생성"""
        if not self.is_trained:
            raise ValueError("모델이 훈련되지 않았습니다. train_models()를 먼저 실행하세요.")
        
        # 특성 생성
        df = self.create_features(data)
        features = df[self.feature_columns].fillna(method='ffill').fillna(0)
        features = features.replace([np.inf, -np.inf], 0)
        
        # 최신 데이터만 사용
        latest_features = features.iloc[-1:].values
        
        # 특성 스케일링
        latest_features_scaled = self.scalers['main'].transform(latest_features)
        
        if self.model_type == MLModelType.ENSEMBLE:
            # 앙상블 예측
            rf_pred = self.models['random_forest'].predict(latest_features_scaled)[0]
            gb_pred = self.models['gradient_boosting'].predict(latest_features_scaled)[0]
            lr_pred = self.models['logistic_regression'].predict(latest_features_scaled)[0]
            
            # 확률 예측
            rf_proba = self.models['random_forest'].predict_proba(latest_features_scaled)[0]
            gb_proba = self.models['gradient_boosting'].predict_proba(latest_features_scaled)[0]
            lr_proba = self.models['logistic_regression'].predict_proba(latest_features_scaled)[0]
            
            # 평균 확률
            avg_proba = (rf_proba + gb_proba + lr_proba) / 3
            
            # 투표 기반 예측
            prediction = np.round((rf_pred + gb_pred + lr_pred) / 3)
            confidence = np.max(avg_proba)
            
            # 특성 중요도 (랜덤 포레스트 기준)
            feature_importance = dict(zip(self.feature_columns, 
                                        self.models['random_forest'].feature_importances_))
            
        else:
            prediction = self.models['main'].predict(latest_features_scaled)[0]
            proba = self.models['main'].predict_proba(latest_features_scaled)[0]
            confidence = np.max(proba)
            
            if hasattr(self.models['main'], 'feature_importances_'):
                feature_importance = dict(zip(self.feature_columns, 
                                            self.models['main'].feature_importances_))
            else:
                feature_importance = {}
        
        # 신호 타입 결정
        signal_map = {-1: 'sell', 0: 'hold', 1: 'buy'}
        signal_type = signal_map.get(prediction, 'hold')
        
        return MLSignal(
            signal_type=signal_type,
            confidence=confidence,
            probability=confidence,
            features_importance=feature_importance,
            model_used=self.model_type.value,
            timestamp=pd.Timestamp.now()
        )
    
    def save_models(self, filepath: str):
        """모델 저장"""
        model_data = {
            'models': self.models,
            'scalers': self.scalers,
            'feature_columns': self.feature_columns,
            'model_type': self.model_type.value,
            'is_trained': self.is_trained
        }
        joblib.dump(model_data, filepath)
    
    def load_models(self, filepath: str):
        """모델 로드"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {filepath}")
        
        model_data = joblib.load(filepath)
        self.models = model_data['models']
        self.scalers = model_data['scalers']
        self.feature_columns = model_data['feature_columns']
        self.model_type = MLModelType(model_data['model_type'])
        self.is_trained = model_data['is_trained']
