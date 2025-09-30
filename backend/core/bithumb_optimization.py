"""
빗썸 수수료 최적화 시스템
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import requests
import time


class OrderType(Enum):
    """주문 타입"""
    MARKET = "market"  # 시장가
    LIMIT = "limit"    # 지정가
    STOP = "stop"      # 스탑


class MakerTakerStrategy(Enum):
    """메이커/테이커 전략"""
    MAKER_ONLY = "maker_only"      # 메이커만
    TAKER_ONLY = "taker_only"      # 테이커만
    ADAPTIVE = "adaptive"          # 적응형
    HYBRID = "hybrid"              # 하이브리드


@dataclass
class CommissionOptimization:
    """수수료 최적화 정보"""
    strategy: MakerTakerStrategy
    expected_commission: float
    expected_savings: float
    execution_time: float
    success_probability: float
    risk_level: str  # 'low', 'medium', 'high'


class BithumbOptimizer:
    """빗썸 수수료 최적화기"""
    
    def __init__(self):
        # 빗썸 수수료 구조
        self.commission_rates = {
            'maker': 0.0005,  # 0.05% (지정가)
            'taker': 0.0015,  # 0.15% (시장가)
            'vip_maker': 0.0003,  # VIP 메이커
            'vip_taker': 0.0012,  # VIP 테이커
        }
        
        # 거래량별 수수료 할인
        self.volume_discounts = {
            1000000: 0.0004,    # 100만원 이상: 0.04%
            5000000: 0.0003,    # 500만원 이상: 0.03%
            10000000: 0.0002,   # 1000만원 이상: 0.02%
            50000000: 0.0001,   # 5000만원 이상: 0.01%
        }
        
        # 리베이트 정보
        self.rebate_rates = {
            'maker_rebate': 0.0001,  # 메이커 리베이트 0.01%
            'volume_bonus': 0.00005,  # 거래량 보너스
        }
    
    def calculate_optimal_strategy(self, order_size: float, market_volatility: float,
                                 urgency: str = 'normal') -> CommissionOptimization:
        """최적 수수료 전략 계산"""
        
        # 시장 상황 분석
        if market_volatility > 0.05:  # 고변동성
            if urgency == 'high':
                return self._high_urgency_strategy(order_size)
            else:
                return self._adaptive_strategy(order_size, market_volatility)
        else:  # 저변동성
            return self._maker_optimized_strategy(order_size)
    
    def _maker_optimized_strategy(self, order_size: float) -> CommissionOptimization:
        """메이커 최적화 전략"""
        # 지정가 주문으로 메이커 수수료 적용
        commission = order_size * self.commission_rates['maker']
        
        # 리베이트 적용
        rebate = order_size * self.rebate_rates['maker_rebate']
        net_commission = commission - rebate
        
        return CommissionOptimization(
            strategy=MakerTakerStrategy.MAKER_ONLY,
            expected_commission=net_commission,
            expected_savings=order_size * (self.commission_rates['taker'] - self.commission_rates['maker']),
            execution_time=30.0,  # 30초 예상
            success_probability=0.85,
            risk_level='low'
        )
    
    def _high_urgency_strategy(self, order_size: float) -> CommissionOptimization:
        """고급속성 전략"""
        # 시장가 주문으로 즉시 체결
        commission = order_size * self.commission_rates['taker']
        
        return CommissionOptimization(
            strategy=MakerTakerStrategy.TAKER_ONLY,
            expected_commission=commission,
            expected_savings=0.0,
            execution_time=5.0,  # 5초 예상
            success_probability=0.99,
            risk_level='high'
        )
    
    def _adaptive_strategy(self, order_size: float, volatility: float) -> CommissionOptimization:
        """적응형 전략"""
        # 변동성에 따른 하이브리드 전략
        if volatility > 0.03:  # 중간 변동성
            # 부분 지정가 + 부분 시장가
            maker_ratio = 0.6
            taker_ratio = 0.4
            
            maker_commission = order_size * maker_ratio * self.commission_rates['maker']
            taker_commission = order_size * taker_ratio * self.commission_rates['taker']
            total_commission = maker_commission + taker_commission
            
            savings = order_size * (self.commission_rates['taker'] - 
                                   (maker_ratio * self.commission_rates['maker'] + 
                                    taker_ratio * self.commission_rates['taker']))
            
            return CommissionOptimization(
                strategy=MakerTakerStrategy.HYBRID,
                expected_commission=total_commission,
                expected_savings=savings,
                execution_time=15.0,
                success_probability=0.90,
                risk_level='medium'
            )
        else:
            return self._maker_optimized_strategy(order_size)
    
    def calculate_volume_discount(self, monthly_volume: float) -> float:
        """거래량 할인 계산"""
        for threshold, rate in sorted(self.volume_discounts.items()):
            if monthly_volume >= threshold:
                return rate
        return self.commission_rates['maker']
    
    def optimize_order_splitting(self, total_amount: float, market_depth: Dict) -> List[Dict]:
        """주문 분할 최적화"""
        optimal_splits = []
        
        # 시장 깊이 분석
        available_volume = sum([level['volume'] for level in market_depth['bids'][:5]])
        
        if total_amount <= available_volume * 0.1:  # 시장 깊이의 10% 이하
            # 단일 지정가 주문
            optimal_splits.append({
                'type': 'limit',
                'amount': total_amount,
                'price': market_depth['bids'][0]['price'] * 0.999,  # 약간 낮은 가격
                'expected_commission': total_amount * self.commission_rates['maker']
            })
        else:
            # 다단계 주문 분할
            remaining_amount = total_amount
            split_ratio = 0.3  # 첫 번째 주문은 30%
            
            # 첫 번째: 지정가 주문
            first_amount = total_amount * split_ratio
            optimal_splits.append({
                'type': 'limit',
                'amount': first_amount,
                'price': market_depth['bids'][0]['price'] * 0.999,
                'expected_commission': first_amount * self.commission_rates['maker']
            })
            
            # 두 번째: 시장가 주문 (나머지)
            remaining_amount -= first_amount
            optimal_splits.append({
                'type': 'market',
                'amount': remaining_amount,
                'price': None,  # 시장가
                'expected_commission': remaining_amount * self.commission_rates['taker']
            })
        
        return optimal_splits
    
    def calculate_timing_optimization(self, order_data: pd.DataFrame) -> Dict:
        """거래 타이밍 최적화"""
        # 시간대별 수수료 패턴 분석
        hourly_stats = order_data.groupby(order_data.index.hour).agg({
            'volume': 'mean',
            'volatility': 'mean',
            'spread': 'mean'
        })
        
        # 최적 거래 시간대 찾기
        optimal_hours = hourly_stats[
            (hourly_stats['volume'] > hourly_stats['volume'].quantile(0.7)) &
            (hourly_stats['spread'] < hourly_stats['spread'].quantile(0.3))
        ].index.tolist()
        
        # 요일별 패턴
        daily_stats = order_data.groupby(order_data.index.dayofweek).agg({
            'volume': 'mean',
            'volatility': 'mean'
        })
        
        optimal_days = daily_stats[
            daily_stats['volume'] > daily_stats['volume'].quantile(0.7)
        ].index.tolist()
        
        return {
            'optimal_hours': optimal_hours,
            'optimal_days': optimal_days,
            'avoid_hours': hourly_stats[
                hourly_stats['spread'] > hourly_stats['spread'].quantile(0.8)
            ].index.tolist(),
            'high_volatility_hours': hourly_stats[
                hourly_stats['volatility'] > hourly_stats['volatility'].quantile(0.8)
            ].index.tolist()
        }
    
    def calculate_rebate_optimization(self, trading_history: List[Dict]) -> Dict:
        """리베이트 최적화"""
        total_volume = sum([trade['amount'] for trade in trading_history])
        maker_trades = [trade for trade in trading_history if trade['type'] == 'limit']
        taker_trades = [trade for trade in trading_history if trade['type'] == 'market']
        
        maker_volume = sum([trade['amount'] for trade in maker_trades])
        taker_volume = sum([trade['amount'] for trade in taker_trades])
        
        # 현재 리베이트
        current_rebate = maker_volume * self.rebate_rates['maker_rebate']
        
        # 최적화된 리베이트 (더 많은 메이커 거래)
        optimal_maker_ratio = 0.8  # 80% 메이커 거래 목표
        optimal_maker_volume = total_volume * optimal_maker_ratio
        optimal_rebate = optimal_maker_volume * self.rebate_rates['maker_rebate']
        
        # 추가 거래량 보너스
        volume_bonus = 0
        for threshold, bonus_rate in self.volume_discounts.items():
            if total_volume >= threshold:
                volume_bonus = total_volume * bonus_rate
        
        return {
            'current_rebate': current_rebate,
            'optimal_rebate': optimal_rebate,
            'potential_savings': optimal_rebate - current_rebate,
            'volume_bonus': volume_bonus,
            'maker_ratio_improvement': optimal_maker_ratio - (maker_volume / total_volume),
            'recommended_strategy': 'increase_maker_orders' if optimal_rebate > current_rebate else 'maintain_current'
        }
    
    def generate_optimization_report(self, trading_data: pd.DataFrame, 
                                   portfolio_value: float) -> Dict:
        """수수료 최적화 리포트 생성"""
        # 기본 통계
        total_volume = trading_data['amount'].sum()
        total_commission = trading_data['commission'].sum()
        avg_commission_rate = total_commission / total_volume
        
        # 메이커/테이커 비율
        maker_orders = trading_data[trading_data['type'] == 'limit']
        taker_orders = trading_data[trading_data['type'] == 'market']
        
        maker_ratio = len(maker_orders) / len(trading_data)
        taker_ratio = len(taker_orders) / len(trading_data)
        
        # 최적화 기회 분석
        potential_savings = self._calculate_potential_savings(trading_data)
        
        # 권장사항
        recommendations = self._generate_recommendations(trading_data, portfolio_value)
        
        return {
            'summary': {
                'total_volume': total_volume,
                'total_commission': total_commission,
                'avg_commission_rate': avg_commission_rate,
                'maker_ratio': maker_ratio,
                'taker_ratio': taker_ratio
            },
            'optimization_opportunities': potential_savings,
            'recommendations': recommendations,
            'next_actions': self._generate_next_actions(trading_data)
        }
    
    def _calculate_potential_savings(self, trading_data: pd.DataFrame) -> Dict:
        """잠재적 절약 계산"""
        current_commission = trading_data['commission'].sum()
        
        # 모든 거래를 메이커로 했을 때
        maker_commission = trading_data['amount'].sum() * self.commission_rates['maker']
        potential_savings = current_commission - maker_commission
        
        # 리베이트 포함 절약
        rebate_savings = trading_data['amount'].sum() * self.rebate_rates['maker_rebate']
        total_potential_savings = potential_savings + rebate_savings
        
        return {
            'commission_savings': potential_savings,
            'rebate_savings': rebate_savings,
            'total_savings': total_potential_savings,
            'savings_percentage': (total_potential_savings / current_commission) * 100
        }
    
    def _generate_recommendations(self, trading_data: pd.DataFrame, 
                                portfolio_value: float) -> List[str]:
        """권장사항 생성"""
        recommendations = []
        
        maker_ratio = len(trading_data[trading_data['type'] == 'limit']) / len(trading_data)
        
        if maker_ratio < 0.7:
            recommendations.append("메이커 주문 비율을 70% 이상으로 증가시키세요")
        
        if portfolio_value > 10000000:  # 1000만원 이상
            recommendations.append("VIP 수수료 혜택을 신청하세요")
        
        if trading_data['amount'].mean() < 100000:  # 평균 거래액이 10만원 미만
            recommendations.append("거래 단위를 늘려 수수료 효율성을 높이세요")
        
        return recommendations
    
    def _generate_next_actions(self, trading_data: pd.DataFrame) -> List[str]:
        """다음 액션 아이템 생성"""
        actions = []
        
        # 거래 패턴 분석
        hourly_pattern = trading_data.groupby(trading_data.index.hour)['amount'].sum()
        best_hour = hourly_pattern.idxmax()
        
        actions.append(f"최적 거래 시간: {best_hour}시")
        actions.append("지정가 주문 비율을 늘리세요")
        actions.append("거래량 보너스 혜택을 확인하세요")
        
        return actions
