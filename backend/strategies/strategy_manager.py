"""
전략 매니저 - 여러 전략을 관리하고 실행
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass
from enum import Enum

from strategies.base_strategy import BaseStrategy, StrategyConfig, StrategyType, TradingSignal
from strategies.scalping_strategy import ScalpingStrategy
from strategies.day_trading_strategy import DayTradingStrategy
from strategies.swing_trading_strategy import SwingTradingStrategy
from strategies.long_term_strategy import LongTermStrategy


class StrategyStatus(Enum):
    """전략 상태"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class StrategyInstance:
    """전략 인스턴스"""
    id: str
    name: str
    strategy: BaseStrategy
    config: StrategyConfig
    status: StrategyStatus
    created_at: datetime
    last_executed: Optional[datetime] = None
    performance: Dict[str, Any] = None


class StrategyManager:
    """전략 매니저"""
    
    def __init__(self):
        self.strategies: Dict[str, StrategyInstance] = {}
        self.active_strategies: List[str] = []
        self.strategy_types = {
            StrategyType.SCALPING: ScalpingStrategy,
            StrategyType.DAY_TRADING: DayTradingStrategy,
            StrategyType.SWING_TRADING: SwingTradingStrategy,
            StrategyType.LONG_TERM: LongTermStrategy
        }
    
    def create_strategy(self, name: str, strategy_type: StrategyType, 
                       config: StrategyConfig) -> str:
        """전략 생성"""
        strategy_id = f"{strategy_type.value}_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 전략 클래스 가져오기
        strategy_class = self.strategy_types.get(strategy_type)
        if not strategy_class:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        # 전략 인스턴스 생성
        strategy_instance = strategy_class(config)
        
        # 전략 인스턴스 래핑
        strategy_wrapper = StrategyInstance(
            id=strategy_id,
            name=name,
            strategy=strategy_instance,
            config=config,
            status=StrategyStatus.INACTIVE,
            created_at=datetime.now(),
            performance={}
        )
        
        # 전략 등록
        self.strategies[strategy_id] = strategy_wrapper
        
        return strategy_id
    
    def register_strategy(self, strategy_id: str, strategy_name: str, 
                         strategy_type: str, is_active: bool = True,
                         target_symbols: List[str] = None, config: Dict = None):
        """전략 등록 (외부에서 전략을 등록할 때 사용)"""
        # 전략 타입 매핑
        type_mapping = {
            'scalping': StrategyType.SCALPING,
            'day_trading': StrategyType.DAY_TRADING,
            'swing_trading': StrategyType.SWING_TRADING,
            'long_term': StrategyType.LONG_TERM
        }
        
        strategy_enum_type = type_mapping.get(strategy_type, StrategyType.DAY_TRADING)
        
        # 기본 설정 생성
        if config is None:
            config = StrategyConfig(
                name=strategy_name,
                strategy_type=strategy_enum_type,
                risk_per_trade=0.02,
                max_positions=3,
                stop_loss_pct=0.05,
                take_profit_pct=0.10,
                enabled=True,
                parameters={}
            )
        else:
            # dict를 StrategyConfig로 변환
            if isinstance(config, dict):
                config = StrategyConfig(
                    name=strategy_name,
                    strategy_type=strategy_enum_type,
                    risk_per_trade=config.get('risk_per_trade', 0.02),
                    max_positions=config.get('max_positions', 3),
                    stop_loss_pct=config.get('stop_loss', 0.05),
                    take_profit_pct=config.get('take_profit', 0.10),
                    enabled=True,
                    parameters=config.get('parameters', {})
                )
        
        # 전략 클래스 가져오기
        strategy_class = self.strategy_types.get(strategy_enum_type)
        if not strategy_class:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        # 전략 인스턴스 생성
        strategy_instance = strategy_class(config)
        
        # 전략 인스턴스 래핑
        strategy_wrapper = StrategyInstance(
            id=strategy_id,
            name=strategy_name,
            strategy=strategy_instance,
            config=config,
            status=StrategyStatus.ACTIVE if is_active else StrategyStatus.INACTIVE,
            created_at=datetime.now(),
            performance={}
        )
        
        # 전략 등록
        self.strategies[strategy_id] = strategy_wrapper
        print(f"전략 등록됨: {strategy_id}, 상태: {strategy_wrapper.status}")
        
        # 활성 전략에 추가
        if is_active and strategy_id not in self.active_strategies:
            self.active_strategies.append(strategy_id)
            print(f"활성 전략에 추가됨: {strategy_id}")
        
        print(f"현재 활성 전략 수: {len(self.active_strategies)}")
        print(f"현재 전체 전략 수: {len(self.strategies)}")
        
        return strategy_id
    
    def start_strategy(self, strategy_id: str) -> bool:
        """전략 시작"""
        if strategy_id not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_id]
        strategy.strategy.start()
        strategy.status = StrategyStatus.ACTIVE
        
        if strategy_id not in self.active_strategies:
            self.active_strategies.append(strategy_id)
        
        return True
    
    def stop_strategy(self, strategy_id: str) -> bool:
        """전략 중지"""
        if strategy_id not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_id]
        
        # 전략 중지 시도
        try:
            if hasattr(strategy.strategy, 'stop'):
                strategy.strategy.stop()
        except Exception as e:
            print(f"전략 중지 오류: {e}")
        
        strategy.status = StrategyStatus.INACTIVE
        
        if strategy_id in self.active_strategies:
            self.active_strategies.remove(strategy_id)
        
        print(f"전략 중지됨: {strategy_id}, 활성 전략 수: {len(self.active_strategies)}")
        return True
    
    def pause_strategy(self, strategy_id: str) -> bool:
        """전략 일시정지"""
        if strategy_id not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_id]
        strategy.status = StrategyStatus.PAUSED
        
        if strategy_id in self.active_strategies:
            self.active_strategies.remove(strategy_id)
        
        return True
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """전략 삭제"""
        if strategy_id not in self.strategies:
            return False
        
        # 활성 전략에서 제거
        if strategy_id in self.active_strategies:
            self.active_strategies.remove(strategy_id)
        
        # 전략 삭제
        del self.strategies[strategy_id]
        
        return True
    
    def execute_strategies(self, data: pd.DataFrame) -> Dict[str, List[TradingSignal]]:
        """모든 활성 전략 실행"""
        results = {}
        
        for strategy_id in self.active_strategies:
            if strategy_id not in self.strategies:
                continue
            
            strategy = self.strategies[strategy_id]
            
            try:
                # 전략 실행
                signals = strategy.strategy.analyze(data)
                results[strategy_id] = signals
                
                # 실행 시간 업데이트
                strategy.last_executed = datetime.now()
                
                # 성과 지표 업데이트
                strategy.performance = strategy.strategy.get_performance_metrics()
                
            except Exception as e:
                print(f"Error executing strategy {strategy_id}: {e}")
                strategy.status = StrategyStatus.ERROR
                results[strategy_id] = []
        
        return results
    
    def get_strategy_signals(self, strategy_id: str, data: pd.DataFrame) -> List[TradingSignal]:
        """특정 전략의 신호 조회"""
        if strategy_id not in self.strategies:
            return []
        
        strategy = self.strategies[strategy_id]
        
        try:
            return strategy.strategy.analyze(data)
        except Exception as e:
            print(f"Error getting signals for strategy {strategy_id}: {e}")
            return []
    
    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """모든 전략 정보 조회"""
        strategies = []
        
        for strategy_id, strategy in self.strategies.items():
            strategies.append({
                'id': strategy_id,
                'name': strategy.name,
                'type': strategy.config.strategy_type.value,
                'status': strategy.status.value,
                'created_at': strategy.created_at.isoformat(),
                'last_executed': strategy.last_executed.isoformat() if strategy.last_executed else None,
                'performance': strategy.performance,
                'config': {
                    'risk_per_trade': strategy.config.risk_per_trade,
                    'max_positions': strategy.config.max_positions,
                    'stop_loss_pct': strategy.config.stop_loss_pct,
                    'take_profit_pct': strategy.config.take_profit_pct,
                    'enabled': strategy.config.enabled
                }
            })
        
        return strategies
    
    def get_strategy_info(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """특정 전략 정보 조회"""
        if strategy_id not in self.strategies:
            return None
        
        strategy = self.strategies[strategy_id]
        
        return {
            'id': strategy_id,
            'name': strategy.name,
            'type': strategy.config.strategy_type.value,
            'status': strategy.status.value,
            'created_at': strategy.created_at.isoformat(),
            'last_executed': strategy.last_executed.isoformat() if strategy.last_executed else None,
            'performance': strategy.performance,
            'config': {
                'risk_per_trade': strategy.config.risk_per_trade,
                'max_positions': strategy.config.max_positions,
                'stop_loss_pct': strategy.config.stop_loss_pct,
                'take_profit_pct': strategy.config.take_profit_pct,
                'enabled': strategy.config.enabled,
                'parameters': strategy.config.parameters
            }
        }
    
    def update_strategy_config(self, strategy_id: str, config: StrategyConfig) -> bool:
        """전략 설정 업데이트"""
        if strategy_id not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_id]
        strategy.config = config
        
        # 전략 인스턴스 재생성
        strategy_class = self.strategy_types.get(config.strategy_type)
        if strategy_class:
            strategy.strategy = strategy_class(config)
        
        return True
    
    def get_active_strategies(self) -> List[str]:
        """활성 전략 목록 조회"""
        return self.active_strategies.copy()
    
    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """전략 성과 조회"""
        if strategy_id not in self.strategies:
            return {}
        
        strategy = self.strategies[strategy_id]
        return strategy.performance or {}
    
    def reset_strategy(self, strategy_id: str) -> bool:
        """전략 리셋"""
        if strategy_id not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_id]
        strategy.strategy.reset()
        strategy.performance = {}
        strategy.last_executed = None
        
        return True
    
    def get_strategy_statistics(self) -> Dict[str, Any]:
        """전략 통계 조회"""
        total_strategies = len(self.strategies)
        active_strategies = len(self.active_strategies)
        paused_strategies = sum(1 for s in self.strategies.values() if s.status == StrategyStatus.PAUSED)
        error_strategies = sum(1 for s in self.strategies.values() if s.status == StrategyStatus.ERROR)
        
        # 전략 타입별 통계
        type_stats = {}
        for strategy in self.strategies.values():
            strategy_type = strategy.config.strategy_type.value
            if strategy_type not in type_stats:
                type_stats[strategy_type] = 0
            type_stats[strategy_type] += 1
        
        return {
            'total_strategies': total_strategies,
            'active_strategies': active_strategies,
            'paused_strategies': paused_strategies,
            'error_strategies': error_strategies,
            'type_distribution': type_stats
        }


# 싱글톤 인스턴스
strategy_manager = StrategyManager()
