"""
매매 수수료 계산 시스템
"""
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum


class ExchangeType(Enum):
    """거래소 타입"""
    BITHUMB = "bithumb"
    UPBIT = "upbit"
    BINANCE = "binance"


@dataclass
class CommissionRate:
    """수수료율 정보"""
    maker_rate: float  # 메이커 수수료율 (0.0005 = 0.05%)
    taker_rate: float  # 테이커 수수료율 (0.0015 = 0.15%)
    min_commission: float  # 최소 수수료
    max_commission: float  # 최대 수수료


class CommissionCalculator:
    """수수료 계산기"""
    
    def __init__(self):
        # 거래소별 수수료율 설정
        self.commission_rates = {
            ExchangeType.BITHUMB: CommissionRate(
                maker_rate=0.0005,  # 0.05%
                taker_rate=0.0015,  # 0.15%
                min_commission=0.0,
                max_commission=float('inf')
            ),
            ExchangeType.UPBIT: CommissionRate(
                maker_rate=0.0005,  # 0.05%
                taker_rate=0.0015,  # 0.15%
                min_commission=0.0,
                max_commission=float('inf')
            ),
            ExchangeType.BINANCE: CommissionRate(
                maker_rate=0.001,   # 0.1%
                taker_rate=0.001,   # 0.1%
                min_commission=0.0,
                max_commission=float('inf')
            )
        }
    
    def calculate_commission(self, 
                           amount: float, 
                           price: float, 
                           exchange: ExchangeType = ExchangeType.BITHUMB,
                           is_maker: bool = False) -> float:
        """수수료 계산"""
        if amount <= 0 or price <= 0:
            return 0.0
        
        # 거래 금액 계산
        trade_value = amount * price
        
        # 수수료율 선택
        commission_rate = self.commission_rates.get(exchange)
        if not commission_rate:
            return 0.0
        
        rate = commission_rate.maker_rate if is_maker else commission_rate.taker_rate
        
        # 수수료 계산
        commission = trade_value * rate
        
        # 최소/최대 수수료 적용
        commission = max(commission, commission_rate.min_commission)
        commission = min(commission, commission_rate.max_commission)
        
        return commission
    
    def calculate_net_profit(self, 
                          entry_amount: float,
                          entry_price: float,
                          exit_amount: float,
                          exit_price: float,
                          exchange: ExchangeType = ExchangeType.BITHUMB) -> float:
        """수수료 포함 순수익 계산"""
        if entry_amount <= 0 or exit_amount <= 0:
            return 0.0
        
        # 진입 수수료
        entry_commission = self.calculate_commission(entry_amount, entry_price, exchange)
        
        # 청산 수수료
        exit_commission = self.calculate_commission(exit_amount, exit_price, exchange)
        
        # 총 수수료
        total_commission = entry_commission + exit_commission
        
        # 거래 손익
        gross_profit = (exit_price - entry_price) * min(entry_amount, exit_amount)
        
        # 순수익 (수수료 차감)
        net_profit = gross_profit - total_commission
        
        return net_profit
    
    def calculate_break_even_price(self, 
                                 entry_price: float,
                                 entry_amount: float,
                                 exit_amount: float,
                                 exchange: ExchangeType = ExchangeType.BITHUMB) -> float:
        """손익분기점 가격 계산"""
        if entry_amount <= 0 or exit_amount <= 0:
            return entry_price
        
        # 진입 수수료
        entry_commission = self.calculate_commission(entry_amount, entry_price, exchange)
        
        # 청산 시 수수료를 고려한 손익분기점
        # (exit_price - entry_price) * amount - entry_commission - exit_commission = 0
        # exit_price * amount - entry_price * amount - entry_commission - exit_price * amount * rate = 0
        # exit_price * amount * (1 - rate) = entry_price * amount + entry_commission
        
        rate = self.commission_rates.get(exchange).taker_rate
        break_even_price = (entry_price * exit_amount + entry_commission) / (exit_amount * (1 - rate))
        
        return break_even_price
    
    def calculate_required_return(self, 
                                entry_price: float,
                                entry_amount: float,
                                target_profit: float,
                                exchange: ExchangeType = ExchangeType.BITHUMB) -> float:
        """목표 수익을 위한 필요 수익률 계산"""
        if entry_amount <= 0 or target_profit <= 0:
            return 0.0
        
        # 진입 수수료
        entry_commission = self.calculate_commission(entry_amount, entry_price, exchange)
        
        # 수수료를 고려한 목표 가격
        # target_profit = (exit_price - entry_price) * amount - total_commission
        # exit_price = (target_profit + total_commission) / amount + entry_price
        
        rate = self.commission_rates.get(exchange).taker_rate
        required_price = (target_profit + entry_commission) / (entry_amount * (1 - rate)) + entry_price
        
        # 필요 수익률 계산
        required_return = (required_price - entry_price) / entry_price
        
        return required_return
    
    def get_commission_info(self, exchange: ExchangeType = ExchangeType.BITHUMB) -> Dict:
        """수수료 정보 조회"""
        commission_rate = self.commission_rates.get(exchange)
        if not commission_rate:
            return {}
        
        return {
            'exchange': exchange.value,
            'maker_rate': commission_rate.maker_rate,
            'taker_rate': commission_rate.taker_rate,
            'maker_rate_pct': commission_rate.maker_rate * 100,
            'taker_rate_pct': commission_rate.taker_rate * 100,
            'min_commission': commission_rate.min_commission,
            'max_commission': commission_rate.max_commission
        }


# 싱글톤 인스턴스
commission_calculator = CommissionCalculator()
