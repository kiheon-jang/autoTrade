"""
머신러닝 모델 관련 데이터베이스 모델
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, JSON, LargeBinary
from sqlalchemy.sql import func
from datetime import datetime
from core.database import Base


class MLModel(Base):
    """ML 모델 기본 정보 모델"""
    __tablename__ = "ml_models"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)  # random_forest, gradient_boosting, logistic_regression, ensemble
    description = Column(Text, nullable=True)
    
    # 모델 상태
    is_active = Column(Boolean, default=False)
    is_trained = Column(Boolean, default=False)
    is_deployed = Column(Boolean, default=False)
    
    # 모델 메타데이터
    version = Column(String(20), default="1.0.0")
    feature_count = Column(Integer, default=0)
    training_samples = Column(Integer, default=0)
    
    # 훈련 설정 (JSON)
    training_config = Column(JSON, nullable=True)
    hyperparameters = Column(JSON, nullable=True)
    
    # 모델 파일 정보
    model_file_path = Column(String(255), nullable=True)  # 로컬 파일 경로
    model_size_bytes = Column(Integer, default=0)
    
    # 성과 지표 (최신)
    accuracy = Column(Float, default=0.0)
    precision = Column(Float, default=0.0)
    recall = Column(Float, default=0.0)
    f1_score = Column(Float, default=0.0)
    auc_score = Column(Float, default=0.0)
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_trained = Column(DateTime(timezone=True), nullable=True)
    last_deployed = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<MLModel(id={self.id}, name='{self.name}', type='{self.model_type}', active={self.is_active})>"


class ModelTrainingHistory(Base):
    """모델 훈련 히스토리 모델"""
    __tablename__ = "model_training_history"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # 훈련 설정
    training_start_date = Column(DateTime(timezone=True), nullable=False)
    training_end_date = Column(DateTime(timezone=True), nullable=True)
    training_duration_seconds = Column(Float, nullable=True)
    
    # 데이터셋 정보
    dataset_size = Column(Integer, nullable=False)
    train_size = Column(Integer, nullable=False)
    test_size = Column(Integer, nullable=False)
    validation_size = Column(Integer, default=0)
    
    # 훈련 파라미터
    hyperparameters = Column(JSON, nullable=True)
    feature_columns = Column(JSON, nullable=True)
    
    # 성능 지표
    train_accuracy = Column(Float, default=0.0)
    test_accuracy = Column(Float, default=0.0)
    train_precision = Column(Float, default=0.0)
    test_precision = Column(Float, default=0.0)
    train_recall = Column(Float, default=0.0)
    test_recall = Column(Float, default=0.0)
    train_f1_score = Column(Float, default=0.0)
    test_f1_score = Column(Float, default=0.0)
    train_auc = Column(Float, default=0.0)
    test_auc = Column(Float, default=0.0)
    
    # 훈련 상태
    status = Column(String(20), default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ModelTrainingHistory(id={self.id}, model_id={self.model_id}, status='{self.status}')>"


class ModelPerformance(Base):
    """모델 성능 지표 모델"""
    __tablename__ = "model_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, nullable=False, index=True)
    training_history_id = Column(Integer, nullable=True, index=True)
    
    # 성능 지표
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    auc_score = Column(Float, nullable=True)
    
    # 추가 지표
    confusion_matrix = Column(JSON, nullable=True)
    classification_report = Column(JSON, nullable=True)
    roc_curve_data = Column(JSON, nullable=True)
    precision_recall_curve = Column(JSON, nullable=True)
    
    # 평가 설정
    evaluation_method = Column(String(50), default="holdout")  # holdout, cross_validation, time_series_split
    cv_folds = Column(Integer, nullable=True)
    
    # 시간 정보
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<ModelPerformance(id={self.id}, model_id={self.model_id}, accuracy={self.accuracy:.3f})>"


class FeatureImportance(Base):
    """특성 중요도 모델"""
    __tablename__ = "feature_importance"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, nullable=False, index=True)
    training_history_id = Column(Integer, nullable=True, index=True)
    
    # 특성 정보
    feature_name = Column(String(100), nullable=False)
    importance_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    
    # 특성 메타데이터
    feature_type = Column(String(50), nullable=True)  # technical, fundamental, derived
    feature_category = Column(String(50), nullable=True)  # price, volume, volatility, etc.
    
    # 시간 정보
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<FeatureImportance(id={self.id}, feature='{self.feature_name}', score={self.importance_score:.4f})>"


class ModelPrediction(Base):
    """모델 예측 결과 모델"""
    __tablename__ = "model_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, nullable=False, index=True)
    
    # 예측 정보
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    prediction = Column(Integer, nullable=False)  # -1: sell, 0: hold, 1: buy
    confidence = Column(Float, nullable=False)
    probability = Column(JSON, nullable=True)  # 각 클래스별 확률
    
    # 입력 특성
    input_features = Column(JSON, nullable=True)
    feature_values = Column(JSON, nullable=True)
    
    # 시장 데이터 스냅샷
    market_data = Column(JSON, nullable=True)
    
    # 예측 결과
    actual_outcome = Column(Integer, nullable=True)  # 실제 결과 (나중에 업데이트)
    prediction_correct = Column(Boolean, nullable=True)  # 예측 정확도
    
    # 시간 정보
    predicted_at = Column(DateTime(timezone=True), server_default=func.now())
    actual_at = Column(DateTime(timezone=True), nullable=True)  # 실제 결과 확인 시점
    
    def __repr__(self):
        return f"<ModelPrediction(id={self.id}, model_id={self.model_id}, symbol='{self.symbol}', prediction={self.prediction})>"


class ModelDeployment(Base):
    """모델 배포 정보 모델"""
    __tablename__ = "model_deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # 배포 정보
    deployment_name = Column(String(100), nullable=False)
    deployment_type = Column(String(50), nullable=False)  # production, staging, testing
    environment = Column(String(50), nullable=False)  # development, production
    
    # 배포 설정
    auto_retrain = Column(Boolean, default=False)
    performance_threshold = Column(Float, default=0.7)
    retrain_frequency_days = Column(Integer, default=30)
    
    # 배포 상태
    is_active = Column(Boolean, default=True)
    deployment_status = Column(String(20), default="deployed")  # deployed, failed, stopped
    
    # 성능 모니터링
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    current_accuracy = Column(Float, default=0.0)
    last_performance_check = Column(DateTime(timezone=True), nullable=True)
    
    # 시간 정보
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<ModelDeployment(id={self.id}, model_id={self.model_id}, name='{self.deployment_name}', active={self.is_active})>"
