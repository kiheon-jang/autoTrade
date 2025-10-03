"""
머신러닝 모델 관리 API
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import pandas as pd

from core.database import get_db
from services.ml_model_service import MLModelService
from models.ml_models import MLModel, ModelTrainingHistory, ModelPerformance, FeatureImportance, ModelPrediction, ModelDeployment

router = APIRouter(prefix="/api/ml-models", tags=["ML Models"])


# Request/Response Models
class CreateModelRequest(BaseModel):
    name: str
    model_type: str  # random_forest, gradient_boosting, logistic_regression, ensemble
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class TrainModelRequest(BaseModel):
    model_id: int
    training_data: Dict[str, Any]  # JSON 형태의 훈련 데이터
    feature_columns: List[str]
    target_column: str
    hyperparameters: Optional[Dict[str, Any]] = None


class PredictRequest(BaseModel):
    model_id: int
    data: Dict[str, Any]  # 예측할 데이터
    symbol: str = "BTC_KRW"
    timeframe: str = "1h"


class DeployModelRequest(BaseModel):
    model_id: int
    deployment_name: str
    deployment_type: str = "production"


class ModelResponse(BaseModel):
    id: int
    name: str
    model_type: str
    description: Optional[str]
    is_active: bool
    is_trained: bool
    is_deployed: bool
    version: str
    feature_count: int
    training_samples: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    created_at: datetime
    last_trained: Optional[datetime]
    last_deployed: Optional[datetime]

    class Config:
        from_attributes = True


class TrainingHistoryResponse(BaseModel):
    id: int
    model_id: int
    training_start_date: datetime
    training_end_date: Optional[datetime]
    training_duration_seconds: Optional[float]
    dataset_size: int
    train_size: int
    test_size: int
    status: str
    test_accuracy: float
    test_precision: float
    test_recall: float
    test_f1_score: float

    class Config:
        from_attributes = True


class PerformanceResponse(BaseModel):
    id: int
    model_id: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_score: Optional[float]
    evaluation_method: str
    evaluated_at: datetime

    class Config:
        from_attributes = True


class FeatureImportanceResponse(BaseModel):
    id: int
    model_id: int
    feature_name: str
    importance_score: float
    rank: int
    feature_type: Optional[str]
    feature_category: Optional[str]

    class Config:
        from_attributes = True


class PredictionResponse(BaseModel):
    id: int
    model_id: int
    symbol: str
    timeframe: str
    prediction: int
    confidence: float
    probability: Optional[Dict[str, float]]
    predicted_at: datetime
    actual_outcome: Optional[int]
    prediction_correct: Optional[bool]

    class Config:
        from_attributes = True


class ModelStatisticsResponse(BaseModel):
    model_info: Dict[str, Any]
    performance: Dict[str, float]
    predictions: Dict[str, Any]


# API Endpoints
@router.post("/", response_model=ModelResponse)
async def create_model(
    request: CreateModelRequest,
    user_id: int = 1,  # TODO: 실제 인증에서 가져오기
    db: Session = Depends(get_db)
):
    """새로운 ML 모델 생성"""
    try:
        service = MLModelService(db)
        model = service.create_model(
            user_id=user_id,
            name=request.name,
            model_type=request.model_type,
            description=request.description,
            config=request.config
        )
        
        return ModelResponse(
            id=model.id,
            name=model.name,
            model_type=model.model_type,
            description=model.description,
            is_active=model.is_active,
            is_trained=model.is_trained,
            is_deployed=model.is_deployed,
            version=model.version,
            feature_count=model.feature_count,
            training_samples=model.training_samples,
            accuracy=model.accuracy,
            precision=model.precision,
            recall=model.recall,
            f1_score=model.f1_score,
            created_at=model.created_at,
            last_trained=model.last_trained,
            last_deployed=model.last_deployed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 생성 실패: {str(e)}")


@router.post("/train", response_model=TrainingHistoryResponse)
async def train_model(
    request: TrainModelRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """모델 훈련"""
    try:
        service = MLModelService(db)
        
        # JSON 데이터를 DataFrame으로 변환
        training_data = pd.DataFrame(request.training_data)
        
        # 백그라운드에서 훈련 실행
        training_history = service.train_model(
            model_id=request.model_id,
            training_data=training_data,
            feature_columns=request.feature_columns,
            target_column=request.target_column,
            hyperparameters=request.hyperparameters
        )
        
        return TrainingHistoryResponse(
            id=training_history.id,
            model_id=training_history.model_id,
            training_start_date=training_history.training_start_date,
            training_end_date=training_history.training_end_date,
            training_duration_seconds=training_history.training_duration_seconds,
            dataset_size=training_history.dataset_size,
            train_size=training_history.train_size,
            test_size=training_history.test_size,
            status=training_history.status,
            test_accuracy=training_history.test_accuracy,
            test_precision=training_history.test_precision,
            test_recall=training_history.test_recall,
            test_f1_score=training_history.test_f1_score
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 훈련 실패: {str(e)}")


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictRequest,
    db: Session = Depends(get_db)
):
    """모델 예측"""
    try:
        service = MLModelService(db)
        
        # JSON 데이터를 DataFrame으로 변환
        data = pd.DataFrame([request.data])
        data['symbol'] = request.symbol
        data['timeframe'] = request.timeframe
        
        prediction = service.predict(
            model_id=request.model_id,
            data=data
        )
        
        return PredictionResponse(
            id=prediction.id,
            model_id=prediction.model_id,
            symbol=prediction.symbol,
            timeframe=prediction.timeframe,
            prediction=prediction.prediction,
            confidence=prediction.confidence,
            probability=prediction.probability,
            predicted_at=prediction.predicted_at,
            actual_outcome=prediction.actual_outcome,
            prediction_correct=prediction.prediction_correct
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 실패: {str(e)}")


@router.post("/deploy")
async def deploy_model(
    request: DeployModelRequest,
    db: Session = Depends(get_db)
):
    """모델 배포"""
    try:
        service = MLModelService(db)
        deployment = service.deploy_model(
            model_id=request.model_id,
            deployment_name=request.deployment_name,
            deployment_type=request.deployment_type
        )
        
        return {
            "id": deployment.id,
            "model_id": deployment.model_id,
            "deployment_name": deployment.deployment_name,
            "deployment_type": deployment.deployment_type,
            "is_active": deployment.is_active,
            "deployed_at": deployment.deployed_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 배포 실패: {str(e)}")


@router.get("/", response_model=List[ModelResponse])
async def get_models(
    user_id: int = 1,  # TODO: 실제 인증에서 가져오기
    db: Session = Depends(get_db)
):
    """모델 목록 조회"""
    try:
        service = MLModelService(db)
        models = service.get_active_models(user_id)
        
        return [
            ModelResponse(
                id=model.id,
                name=model.name,
                model_type=model.model_type,
                description=model.description,
                is_active=model.is_active,
                is_trained=model.is_trained,
                is_deployed=model.is_deployed,
                version=model.version,
                feature_count=model.feature_count,
                training_samples=model.training_samples,
                accuracy=model.accuracy,
                precision=model.precision,
                recall=model.recall,
                f1_score=model.f1_score,
                created_at=model.created_at,
                last_trained=model.last_trained,
                last_deployed=model.last_deployed
            ) for model in models
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 실패: {str(e)}")


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """특정 모델 조회"""
    try:
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="모델을 찾을 수 없습니다")
        
        return ModelResponse(
            id=model.id,
            name=model.name,
            model_type=model.model_type,
            description=model.description,
            is_active=model.is_active,
            is_trained=model.is_trained,
            is_deployed=model.is_deployed,
            version=model.version,
            feature_count=model.feature_count,
            training_samples=model.training_samples,
            accuracy=model.accuracy,
            precision=model.precision,
            recall=model.recall,
            f1_score=model.f1_score,
            created_at=model.created_at,
            last_trained=model.last_trained,
            last_deployed=model.last_deployed
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 조회 실패: {str(e)}")


@router.get("/{model_id}/performance", response_model=List[PerformanceResponse])
async def get_model_performance(
    model_id: int,
    db: Session = Depends(get_db)
):
    """모델 성능 지표 조회"""
    try:
        service = MLModelService(db)
        performances = service.get_model_performance(model_id)
        
        return [
            PerformanceResponse(
                id=perf.id,
                model_id=perf.model_id,
                accuracy=perf.accuracy,
                precision=perf.precision,
                recall=perf.recall,
                f1_score=perf.f1_score,
                auc_score=perf.auc_score,
                evaluation_method=perf.evaluation_method,
                evaluated_at=perf.evaluated_at
            ) for perf in performances
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"성능 지표 조회 실패: {str(e)}")


@router.get("/{model_id}/features", response_model=List[FeatureImportanceResponse])
async def get_feature_importance(
    model_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """특성 중요도 조회"""
    try:
        service = MLModelService(db)
        features = service.get_feature_importance(model_id, limit)
        
        return [
            FeatureImportanceResponse(
                id=feat.id,
                model_id=feat.model_id,
                feature_name=feat.feature_name,
                importance_score=feat.importance_score,
                rank=feat.rank,
                feature_type=feat.feature_type,
                feature_category=feat.feature_category
            ) for feat in features
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"특성 중요도 조회 실패: {str(e)}")


@router.get("/{model_id}/predictions", response_model=List[PredictionResponse])
async def get_model_predictions(
    model_id: int,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """모델 예측 결과 조회"""
    try:
        service = MLModelService(db)
        predictions = service.get_model_predictions(model_id, limit)
        
        return [
            PredictionResponse(
                id=pred.id,
                model_id=pred.model_id,
                symbol=pred.symbol,
                timeframe=pred.timeframe,
                prediction=pred.prediction,
                confidence=pred.confidence,
                probability=pred.probability,
                predicted_at=pred.predicted_at,
                actual_outcome=pred.actual_outcome,
                prediction_correct=pred.prediction_correct
            ) for pred in predictions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 결과 조회 실패: {str(e)}")


@router.get("/{model_id}/statistics", response_model=ModelStatisticsResponse)
async def get_model_statistics(
    model_id: int,
    db: Session = Depends(get_db)
):
    """모델 통계 정보 조회"""
    try:
        service = MLModelService(db)
        statistics = service.get_model_statistics(model_id)
        
        return ModelStatisticsResponse(**statistics)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 통계 조회 실패: {str(e)}")


@router.put("/{model_id}/predictions/{prediction_id}/accuracy")
async def update_prediction_accuracy(
    model_id: int,
    prediction_id: int,
    actual_outcome: int,
    db: Session = Depends(get_db)
):
    """예측 정확도 업데이트"""
    try:
        service = MLModelService(db)
        service.update_prediction_accuracy(prediction_id, actual_outcome)
        
        return {"message": "예측 정확도가 업데이트되었습니다"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 정확도 업데이트 실패: {str(e)}")
