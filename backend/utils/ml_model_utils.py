"""
머신러닝 모델 유틸리티 함수들
"""
import os
import joblib
import pickle
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import cross_val_score
import logging

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """모델 평가 유틸리티"""
    
    @staticmethod
    def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: Optional[np.ndarray] = None) -> Dict[str, float]:
        """모델 성능 지표 계산"""
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),
            'f1_score': f1_score(y_true, y_pred, average='weighted', zero_division=0)
        }
        
        if y_proba is not None and len(np.unique(y_true)) > 2:
            try:
                metrics['auc_score'] = roc_auc_score(y_true, y_proba, multi_class='ovr')
            except:
                metrics['auc_score'] = 0.0
        else:
            metrics['auc_score'] = 0.0
            
        return metrics
    
    @staticmethod
    def cross_validate_model(model, X: pd.DataFrame, y: pd.Series, cv: int = 5) -> Dict[str, float]:
        """교차 검증 수행"""
        try:
            accuracy_scores = cross_val_score(model, X, y, cv=cv, scoring='accuracy')
            precision_scores = cross_val_score(model, X, y, cv=cv, scoring='precision_weighted')
            recall_scores = cross_val_score(model, X, y, cv=cv, scoring='recall_weighted')
            f1_scores = cross_val_score(model, X, y, cv=cv, scoring='f1_weighted')
            
            return {
                'cv_accuracy_mean': np.mean(accuracy_scores),
                'cv_accuracy_std': np.std(accuracy_scores),
                'cv_precision_mean': np.mean(precision_scores),
                'cv_precision_std': np.std(precision_scores),
                'cv_recall_mean': np.mean(recall_scores),
                'cv_recall_std': np.std(recall_scores),
                'cv_f1_mean': np.mean(f1_scores),
                'cv_f1_std': np.std(f1_scores)
            }
        except Exception as e:
            logger.error(f"교차 검증 실패: {e}")
            return {}


class ModelStorage:
    """모델 저장 및 로드 유틸리티"""
    
    def __init__(self, storage_path: str = "models/storage"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def save_model(self, model, model_id: int, version: str, metadata: Dict = None) -> str:
        """모델 저장"""
        filename = f"model_{model_id}_v{version}.joblib"
        filepath = os.path.join(self.storage_path, filename)
        
        # 모델 데이터 구성
        model_data = {
            'model': model,
            'metadata': metadata or {},
            'saved_at': datetime.now().isoformat(),
            'version': version
        }
        
        # 모델 저장
        joblib.dump(model_data, filepath)
        
        # 파일 크기 계산
        file_size = os.path.getsize(filepath)
        
        logger.info(f"모델 저장 완료: {filepath} ({file_size} bytes)")
        
        return filepath
    
    def load_model(self, filepath: str):
        """모델 로드"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {filepath}")
        
        model_data = joblib.load(filepath)
        return model_data
    
    def delete_model(self, filepath: str) -> bool:
        """모델 파일 삭제"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"모델 파일 삭제 완료: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"모델 파일 삭제 실패: {e}")
            return False
    
    def list_models(self, model_id: int = None) -> List[Dict]:
        """저장된 모델 목록 조회"""
        models = []
        
        for filename in os.listdir(self.storage_path):
            if filename.startswith("model_") and filename.endswith(".joblib"):
                filepath = os.path.join(self.storage_path, filename)
                
                # 파일 정보 추출
                parts = filename.replace(".joblib", "").split("_")
                if len(parts) >= 3:
                    file_model_id = int(parts[1])
                    version = parts[2]
                    
                    if model_id is None or file_model_id == model_id:
                        stat = os.stat(filepath)
                        models.append({
                            'filename': filename,
                            'filepath': filepath,
                            'model_id': file_model_id,
                            'version': version,
                            'size_bytes': stat.st_size,
                            'created_at': datetime.fromtimestamp(stat.st_ctime),
                            'modified_at': datetime.fromtimestamp(stat.st_mtime)
                        })
        
        return sorted(models, key=lambda x: x['modified_at'], reverse=True)


class FeatureAnalyzer:
    """특성 분석 유틸리티"""
    
    @staticmethod
    def analyze_feature_importance(model, feature_names: List[str]) -> List[Dict]:
        """특성 중요도 분석"""
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            
            # 특성 중요도 정렬
            feature_importance_pairs = list(zip(feature_names, importances))
            feature_importance_pairs.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for rank, (feature_name, importance_score) in enumerate(feature_importance_pairs, 1):
                results.append({
                    'feature_name': feature_name,
                    'importance_score': float(importance_score),
                    'rank': rank,
                    'relative_importance': float(importance_score / max(importances)) if max(importances) > 0 else 0
                })
            
            return results
        else:
            logger.warning("모델이 feature_importances_ 속성을 지원하지 않습니다")
            return []
    
    @staticmethod
    def categorize_features(feature_names: List[str]) -> Dict[str, List[str]]:
        """특성을 카테고리별로 분류"""
        categories = {
            'price': [],
            'volume': [],
            'volatility': [],
            'technical': [],
            'derived': [],
            'other': []
        }
        
        for feature in feature_names:
            feature_lower = feature.lower()
            
            if any(keyword in feature_lower for keyword in ['price', 'close', 'open', 'high', 'low']):
                categories['price'].append(feature)
            elif any(keyword in feature_lower for keyword in ['volume', 'vol']):
                categories['volume'].append(feature)
            elif any(keyword in feature_lower for keyword in ['volatility', 'std', 'var']):
                categories['volatility'].append(feature)
            elif any(keyword in feature_lower for keyword in ['rsi', 'macd', 'bollinger', 'sma', 'ema']):
                categories['technical'].append(feature)
            elif any(keyword in feature_lower for keyword in ['ratio', 'change', 'pct']):
                categories['derived'].append(feature)
            else:
                categories['other'].append(feature)
        
        return categories


class ModelValidator:
    """모델 검증 유틸리티"""
    
    @staticmethod
    def validate_training_data(data: pd.DataFrame, feature_columns: List[str], target_column: str) -> Tuple[bool, List[str]]:
        """훈련 데이터 검증"""
        errors = []
        
        # 기본 검증
        if data.empty:
            errors.append("훈련 데이터가 비어있습니다")
            return False, errors
        
        if len(data) < 10:
            errors.append("훈련 데이터가 너무 적습니다 (최소 10개 필요)")
        
        # 특성 컬럼 검증
        missing_features = [col for col in feature_columns if col not in data.columns]
        if missing_features:
            errors.append(f"누락된 특성 컬럼: {missing_features}")
        
        # 타겟 컬럼 검증
        if target_column not in data.columns:
            errors.append(f"타겟 컬럼을 찾을 수 없습니다: {target_column}")
        
        # 결측값 검증
        if data[feature_columns].isnull().any().any():
            null_columns = data[feature_columns].isnull().any()
            null_cols = null_columns[null_columns].index.tolist()
            errors.append(f"결측값이 있는 특성: {null_cols}")
        
        # 타겟 변수 분포 검증
        if target_column in data.columns:
            target_values = data[target_column].value_counts()
            if len(target_values) < 2:
                errors.append("타겟 변수에 클래스가 1개만 있습니다")
            elif target_values.min() < 2:
                errors.append("일부 클래스의 샘플 수가 너무 적습니다")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_model_performance(metrics: Dict[str, float], thresholds: Dict[str, float] = None) -> Tuple[bool, List[str]]:
        """모델 성능 검증"""
        if thresholds is None:
            thresholds = {
                'accuracy': 0.5,
                'precision': 0.5,
                'recall': 0.5,
                'f1_score': 0.5
            }
        
        warnings = []
        
        for metric, threshold in thresholds.items():
            if metric in metrics and metrics[metric] < threshold:
                warnings.append(f"{metric}이 임계값({threshold})보다 낮습니다: {metrics[metric]:.3f}")
        
        return len(warnings) == 0, warnings


class ModelMonitor:
    """모델 모니터링 유틸리티"""
    
    def __init__(self):
        self.performance_history = []
    
    def track_performance(self, model_id: int, metrics: Dict[str, float], timestamp: datetime = None):
        """성능 지표 추적"""
        if timestamp is None:
            timestamp = datetime.now()
        
        record = {
            'model_id': model_id,
            'timestamp': timestamp,
            'metrics': metrics
        }
        
        self.performance_history.append(record)
        
        # 최근 100개 기록만 유지
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
    
    def get_performance_trend(self, model_id: int, metric: str) -> List[float]:
        """성능 트렌드 조회"""
        model_records = [r for r in self.performance_history if r['model_id'] == model_id]
        return [r['metrics'].get(metric, 0) for r in model_records]
    
    def detect_performance_degradation(self, model_id: int, metric: str, threshold: float = 0.1) -> bool:
        """성능 저하 감지"""
        trend = self.get_performance_trend(model_id, metric)
        
        if len(trend) < 2:
            return False
        
        # 최근 성능과 이전 성능 비교
        recent_performance = trend[-1]
        previous_performance = trend[-2]
        
        degradation = (previous_performance - recent_performance) / previous_performance
        
        return degradation > threshold
