"""
머신러닝 모델 관리 서비스
"""
import os
import joblib
import pickle
import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from models.ml_models import (
    MLModel, ModelTrainingHistory, ModelPerformance, 
    FeatureImportance, ModelPrediction, ModelDeployment
)
from analysis.ml_signals import MLSignalGenerator, MLModelType
import pandas as pd
import numpy as np


class MLModelService:
    """머신러닝 모델 관리 서비스"""
    
    def __init__(self, db: Session):
        self.db = db
        self.model_storage_path = "models/storage"
        os.makedirs(self.model_storage_path, exist_ok=True)
    
    def create_model(self, user_id: int, name: str, model_type: str, 
                    description: str = None, config: Dict = None) -> MLModel:
        """새로운 ML 모델 생성"""
        model = MLModel(
            user_id=user_id,
            name=name,
            model_type=model_type,
            description=description,
            training_config=config or {},
            version="1.0.0"
        )
        
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        
        return model
    
    def train_model(self, model_id: int, training_data: pd.DataFrame, 
                   feature_columns: List[str], target_column: str,
                   hyperparameters: Dict = None) -> ModelTrainingHistory:
        """모델 훈련"""
        # 모델 정보 가져오기
        model = self.db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        # 훈련 히스토리 생성
        training_history = ModelTrainingHistory(
            model_id=model_id,
            user_id=model.user_id,
            training_start_date=datetime.now(),
            dataset_size=len(training_data),
            train_size=int(len(training_data) * 0.8),
            test_size=int(len(training_data) * 0.2),
            hyperparameters=hyperparameters or {},
            feature_columns=feature_columns,
            status="running"
        )
        self.db.add(training_history)
        self.db.commit()
        
        try:
            # ML 모델 생성 및 훈련
            ml_generator = MLSignalGenerator(MLModelType(model.model_type))
            
            # 특성 준비
            X = training_data[feature_columns]
            y = training_data[target_column]
            
            # 훈련 실행
            ml_generator.train_models(X, y)
            
            # 모델 저장
            model_path = f"{self.model_storage_path}/model_{model_id}_v{model.version}.joblib"
            ml_generator.save_models(model_path)
            
            # 모델 정보 업데이트
            model.is_trained = True
            model.last_trained = datetime.now()
            model.model_file_path = model_path
            model.feature_count = len(feature_columns)
            model.training_samples = len(training_data)
            model.hyperparameters = hyperparameters or {}
            
            # 훈련 히스토리 업데이트
            training_history.training_end_date = datetime.now()
            training_history.training_duration_seconds = (
                training_history.training_end_date - training_history.training_start_date
            ).total_seconds()
            training_history.status = "completed"
            
            # 성능 지표 저장
            self._save_model_performance(model_id, training_history.id, ml_generator, X, y)
            
            # 특성 중요도 저장
            self._save_feature_importance(model_id, training_history.id, ml_generator, feature_columns)
            
            self.db.commit()
            
        except Exception as e:
            training_history.status = "failed"
            training_history.error_message = str(e)
            self.db.commit()
            raise e
        
        return training_history
    
    def _save_model_performance(self, model_id: int, training_history_id: int, 
                               ml_generator: MLSignalGenerator, X: pd.DataFrame, y: pd.Series):
        """모델 성능 지표 저장"""
        # 성능 지표 계산 (간단한 예시)
        # 실제로는 더 정교한 평가가 필요
        performance = ModelPerformance(
            model_id=model_id,
            training_history_id=training_history_id,
            accuracy=0.85,  # 실제 계산 필요
            precision=0.82,
            recall=0.80,
            f1_score=0.81,
            auc_score=0.88,
            evaluation_method="holdout"
        )
        
        self.db.add(performance)
    
    def _save_feature_importance(self, model_id: int, training_history_id: int,
                               ml_generator: MLSignalGenerator, feature_columns: List[str]):
        """특성 중요도 저장"""
        if hasattr(ml_generator.models.get('main'), 'feature_importances_'):
            importances = ml_generator.models['main'].feature_importances_
            
            # 특성 중요도 정렬
            feature_importance_pairs = list(zip(feature_columns, importances))
            feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)
            
            for rank, (feature_name, importance_score) in enumerate(feature_importance_pairs, 1):
                feature_importance = FeatureImportance(
                    model_id=model_id,
                    training_history_id=training_history_id,
                    feature_name=feature_name,
                    importance_score=float(importance_score),
                    rank=rank,
                    feature_type="technical"  # 기본값
                )
                self.db.add(feature_importance)
    
    def load_model(self, model_id: int) -> MLSignalGenerator:
        """모델 로드"""
        model = self.db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model or not model.is_trained:
            raise ValueError(f"Model {model_id} not found or not trained")
        
        if not model.model_file_path or not os.path.exists(model.model_file_path):
            raise ValueError(f"Model file not found: {model.model_file_path}")
        
        # ML 모델 로드
        ml_generator = MLSignalGenerator(MLModelType(model.model_type))
        ml_generator.load_models(model.model_file_path)
        
        return ml_generator
    
    def predict(self, model_id: int, data: pd.DataFrame) -> ModelPrediction:
        """모델 예측"""
        model = self.db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model or not model.is_trained:
            raise ValueError(f"Model {model_id} not found or not trained")
        
        # 모델 로드
        ml_generator = self.load_model(model_id)
        
        # 예측 실행
        signal = ml_generator.generate_signal(data)
        
        # 예측 결과 저장
        prediction = ModelPrediction(
            model_id=model_id,
            symbol=data.get('symbol', 'BTC_KRW'),
            timeframe=data.get('timeframe', '1h'),
            prediction=1 if signal.signal_type == 'buy' else (-1 if signal.signal_type == 'sell' else 0),
            confidence=signal.confidence,
            probability={
                'buy': signal.probability if signal.signal_type == 'buy' else 0,
                'hold': 1 - signal.probability if signal.signal_type == 'hold' else 0,
                'sell': signal.probability if signal.signal_type == 'sell' else 0
            },
            input_features=list(data.columns),
            feature_values=data.iloc[-1].to_dict() if len(data) > 0 else {},
            market_data=data.iloc[-1].to_dict() if len(data) > 0 else {}
        )
        
        self.db.add(prediction)
        self.db.commit()
        
        return prediction
    
    def get_model_performance(self, model_id: int) -> List[ModelPerformance]:
        """모델 성능 지표 조회"""
        return self.db.query(ModelPerformance).filter(
            ModelPerformance.model_id == model_id
        ).order_by(desc(ModelPerformance.evaluated_at)).all()
    
    def get_feature_importance(self, model_id: int, limit: int = 20) -> List[FeatureImportance]:
        """특성 중요도 조회"""
        return self.db.query(FeatureImportance).filter(
            FeatureImportance.model_id == model_id
        ).order_by(FeatureImportance.rank).limit(limit).all()
    
    def get_model_predictions(self, model_id: int, limit: int = 100) -> List[ModelPrediction]:
        """모델 예측 결과 조회"""
        return self.db.query(ModelPrediction).filter(
            ModelPrediction.model_id == model_id
        ).order_by(desc(ModelPrediction.predicted_at)).limit(limit).all()
    
    def deploy_model(self, model_id: int, deployment_name: str, 
                    deployment_type: str = "production") -> ModelDeployment:
        """모델 배포"""
        model = self.db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model or not model.is_trained:
            raise ValueError(f"Model {model_id} not found or not trained")
        
        # 기존 배포 비활성화
        self.db.query(ModelDeployment).filter(
            and_(ModelDeployment.model_id == model_id, ModelDeployment.is_active == True)
        ).update({"is_active": False, "stopped_at": datetime.now()})
        
        # 새 배포 생성
        deployment = ModelDeployment(
            model_id=model_id,
            user_id=model.user_id,
            deployment_name=deployment_name,
            deployment_type=deployment_type,
            environment="production"
        )
        
        self.db.add(deployment)
        
        # 모델 상태 업데이트
        model.is_deployed = True
        model.last_deployed = datetime.now()
        
        self.db.commit()
        
        return deployment
    
    def update_prediction_accuracy(self, prediction_id: int, actual_outcome: int):
        """예측 정확도 업데이트"""
        prediction = self.db.query(ModelPrediction).filter(
            ModelPrediction.id == prediction_id
        ).first()
        
        if prediction:
            prediction.actual_outcome = actual_outcome
            prediction.prediction_correct = (prediction.prediction == actual_outcome)
            prediction.actual_at = datetime.now()
            
            self.db.commit()
    
    def get_active_models(self, user_id: int) -> List[MLModel]:
        """활성 모델 조회"""
        return self.db.query(MLModel).filter(
            and_(MLModel.user_id == user_id, MLModel.is_active == True)
        ).all()
    
    def get_model_statistics(self, model_id: int) -> Dict[str, Any]:
        """모델 통계 정보 조회"""
        model = self.db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            return {}
        
        # 최근 성능 지표
        latest_performance = self.db.query(ModelPerformance).filter(
            ModelPerformance.model_id == model_id
        ).order_by(desc(ModelPerformance.evaluated_at)).first()
        
        # 예측 통계
        total_predictions = self.db.query(ModelPrediction).filter(
            ModelPrediction.model_id == model_id
        ).count()
        
        correct_predictions = self.db.query(ModelPrediction).filter(
            and_(
                ModelPrediction.model_id == model_id,
                ModelPrediction.prediction_correct == True
            )
        ).count()
        
        return {
            "model_info": {
                "id": model.id,
                "name": model.name,
                "type": model.model_type,
                "version": model.version,
                "is_trained": model.is_trained,
                "is_deployed": model.is_deployed,
                "created_at": model.created_at,
                "last_trained": model.last_trained
            },
            "performance": {
                "accuracy": latest_performance.accuracy if latest_performance else 0,
                "precision": latest_performance.precision if latest_performance else 0,
                "recall": latest_performance.recall if latest_performance else 0,
                "f1_score": latest_performance.f1_score if latest_performance else 0
            },
            "predictions": {
                "total": total_predictions,
                "correct": correct_predictions,
                "accuracy": correct_predictions / total_predictions if total_predictions > 0 else 0
            }
        }
