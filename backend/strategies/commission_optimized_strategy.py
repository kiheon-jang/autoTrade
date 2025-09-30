"""
수수료 최적화 전략
수수료를 고려하여 수익성을 개선한 전략들
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from .base_strategy import BaseStrategy, StrategyConfig, StrategyType, TradingSignal, SignalType
from core.commission import CommissionCalculator, ExchangeType


class CommissionOptimizedStrategy(BaseStrategy):
    """수수료 최적화 전략"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.commission_calc = CommissionCalculator()
        self.min_profit_threshold = config.parameters.get('min_profit_threshold', 0.01)  # 1% 최소 수익
        self.commission_buffer = config.parameters.get('commission_buffer', 0.002)  # 0.2% 수수료 버퍼
        self.min_hold_period = config.parameters.get('min_hold_period', 5)  # 최소 보유 기간
        
    def calculate_required_return(self, entry_price: float, exchange: ExchangeType = ExchangeType.BITHUMB) -> float:
        """수수료를 고려한 최소 필요 수익률 계산"""
        # 진입 수수료 (테이커)
        entry_commission_rate = self.commission_calc.commission_rates[exchange].taker_rate
        # 청산 수수료 (테이커)
        exit_commission_rate = self.commission_calc.commission_rates[exchange].taker_rate
        
        # 총 수수료율
        total_commission_rate = entry_commission_rate + exit_commission_rate
        
        # 수수료 + 버퍼를 고려한 최소 수익률
        required_return = total_commission_rate + self.commission_buffer + self.min_profit_threshold
        
        return required_return
    
    def should_trade(self, entry_price: float, target_price: float, 
                    exchange: ExchangeType = ExchangeType.BITHUMB) -> bool:
        """수수료를 고려한 거래 가능 여부 판단"""
        if pd.isna(entry_price) or pd.isna(target_price):
            return False
            
        # 예상 수익률 계산
        expected_return = (target_price - entry_price) / entry_price
        
        # 필요 수익률 계산
        required_return = self.calculate_required_return(entry_price, exchange)
        
        return expected_return >= required_return
    
    def calculate_optimal_position_size(self, capital: float, entry_price: float, 
                                      stop_loss_price: float, exchange: ExchangeType = ExchangeType.BITHUMB) -> float:
        """수수료를 고려한 최적 포지션 크기 계산"""
        # 기본 포지션 크기 (리스크 기반)
        base_quantity = self.calculate_position_size(capital, entry_price, stop_loss_price)
        
        # 수수료를 고려한 조정
        required_return = self.calculate_required_return(entry_price, exchange)
        
        # 수수료가 높을수록 포지션 크기 감소
        commission_factor = max(0.5, 1.0 - (required_return * 10))  # 최소 50%까지 감소
        adjusted_quantity = base_quantity * commission_factor
        
        return max(adjusted_quantity, 0.001)  # 최소 거래량 보장
    
    def should_enter_position(self, data: pd.DataFrame) -> bool:
        """포지션 진입 조건"""
        if len(data) < 50:
            return False
        
        # 현재 포지션 수 확인
        if len(self.positions) >= self.config.max_positions:
            return False
        
        # 최근 신호 분석
        signals = self.analyze(data)
        return len(signals) > 0 and signals[0].strength > 0.6
    
    def should_exit_position(self, data: pd.DataFrame, position) -> bool:
        """포지션 청산 조건"""
        if not position:
            return False
        
        # 손절/익절 조건
        current_price = data['close'].iloc[-1]
        
        # position이 딕셔너리인 경우 처리
        if isinstance(position, dict):
            side = position.get('side', 'long')
            stop_loss = position.get('stop_loss', current_price * 0.95)
            take_profit = position.get('take_profit', current_price * 1.05)
        else:
            side = position.side
            stop_loss = position.stop_loss
            take_profit = position.take_profit
        
        if side == 'long':
            # 손절
            if current_price <= stop_loss:
                return True
            # 익절
            if current_price >= take_profit:
                return True
        else:  # short
            # 손절
            if current_price >= stop_loss:
                return True
            # 익절
            if current_price <= take_profit:
                return True
        
        return False


class LowFrequencyStrategy(CommissionOptimizedStrategy):
    """저빈도 거래 전략 - 수수료 최적화"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.ema_short = config.parameters.get('ema_short', 50)
        self.ema_long = config.parameters.get('ema_long', 200)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.volatility_period = config.parameters.get('volatility_period', 20)
        self.min_volatility = config.parameters.get('min_volatility', 0.02)  # 최소 변동성 2%
        
    def analyze(self, data: pd.DataFrame) -> List[TradingSignal]:
        """저빈도 거래 신호 분석"""
        signals = []
        
        if len(data) < max(self.ema_long, self.volatility_period) + 10:
            return signals
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 기술적 지표 계산
        from analysis.technical_indicators import TechnicalAnalyzer
        ti = TechnicalAnalyzer()
        
        ema_short = ti.calculate_ema_talib(close, self.ema_short)
        ema_long = ti.calculate_ema_talib(close, self.ema_long)
        rsi = ti.calculate_rsi(close, self.rsi_period)
        
        # 변동성 계산
        returns = close.pct_change()
        volatility = returns.rolling(self.volatility_period).std()
        
        # 현재 값들
        current_price = close.iloc[-1]
        current_ema_short = ema_short.iloc[-1]
        current_ema_long = ema_long.iloc[-1]
        current_rsi = rsi.iloc[-1]
        current_volatility = volatility.iloc[-1]
        
        # 신호 생성 조건 (완화)
        signal_type = None
        signal_strength = 0.0
        signal_confidence = 0.0
        reason_parts = []
        
        # 1. 기본 트렌드 조건
        if (not pd.isna(current_ema_short) and not pd.isna(current_ema_long)):
            
            # 상승 신호: EMA 크로스 + RSI 과매도
            if (current_ema_short > current_ema_long and
                current_price > current_ema_short and
                current_rsi < 45):  # RSI 조건 완화
                
                # 수수료를 고려한 목표가 계산 (더 낮은 목표)
                target_price = current_price * 1.03  # 3% 목표 수익
                
                if self.should_trade(current_price, target_price):
                    signal_type = SignalType.BUY
                    signal_strength = 0.6
                    signal_confidence = 0.5
                    reason_parts.append("EMA 크로스 + RSI 과매도")
            
            # 하락 신호: EMA 크로스 + RSI 과매수
            elif (current_ema_short < current_ema_long and
                  current_price < current_ema_short and
                  current_rsi > 55):  # RSI 조건 완화
                
                # 수수료를 고려한 목표가 계산
                target_price = current_price * 0.97  # 3% 목표 수익
                
                if self.should_trade(current_price, target_price):
                    signal_type = SignalType.SELL
                    signal_strength = 0.6
                    signal_confidence = 0.5
                    reason_parts.append("EMA 크로스 + RSI 과매수")
        
        # 신호 생성 (조건 완화)
        if signal_type and signal_strength > 0.5:
            # 최적 포지션 크기 계산
            quantity = self.calculate_optimal_position_size(100000, current_price, 
                                                          current_price * 0.95, ExchangeType.BITHUMB)
            
            signal = TradingSignal(
                signal_type=signal_type,
                strength=signal_strength,
                confidence=signal_confidence,
                price=current_price,
                quantity=quantity,
                stop_loss=current_price * 0.95 if signal_type == SignalType.BUY else current_price * 1.05,
                take_profit=current_price * 1.05 if signal_type == SignalType.BUY else current_price * 0.95,
                timestamp=datetime.now(),
                reason=" | ".join(reason_parts),
                metadata={
                    'strategy': 'low_frequency',
                    'commission_optimized': True,
                    'required_return': self.calculate_required_return(current_price),
                    'volatility': current_volatility
                }
            )
            
            signals.append(signal)
        
        return signals


class BreakoutStrategy(CommissionOptimizedStrategy):
    """돌파 전략 - 수수료 최적화"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.breakout_period = config.parameters.get('breakout_period', 20)
        self.volume_threshold = config.parameters.get('volume_threshold', 1.5)  # 평균 대비 1.5배
        self.min_breakout_pct = config.parameters.get('min_breakout_pct', 0.03)  # 최소 3% 돌파
        
    def analyze(self, data: pd.DataFrame) -> List[TradingSignal]:
        """돌파 신호 분석"""
        signals = []
        
        if len(data) < self.breakout_period + 10:
            return signals
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 현재 값들
        current_price = close.iloc[-1]
        current_volume = volume.iloc[-1]
        avg_volume = volume.rolling(self.breakout_period).mean().iloc[-1]
        
        # 최근 고점/저점
        recent_high = high.rolling(self.breakout_period).max().iloc[-2]  # 전일까지
        recent_low = low.rolling(self.breakout_period).min().iloc[-2]
        
        signal_type = None
        signal_strength = 0.0
        signal_confidence = 0.0
        reason_parts = []
        
        # 상승 돌파 (조건 완화)
        if (current_price > recent_high * (1 + self.min_breakout_pct * 0.5) and  # 1.5% 돌파
            current_volume > avg_volume * 1.2):  # 볼륨 조건 완화
            
            # 수수료를 고려한 목표가 (더 낮은 목표)
            target_price = current_price * 1.04  # 4% 목표
            
            if self.should_trade(current_price, target_price):
                signal_type = SignalType.BUY
                signal_strength = 0.7
                signal_confidence = 0.6
                reason_parts.append(f"상승 돌파 ({self.min_breakout_pct*50:.1f}%)")
        
        # 하락 돌파 (조건 완화)
        elif (current_price < recent_low * (1 - self.min_breakout_pct * 0.5) and  # 1.5% 돌파
              current_volume > avg_volume * 1.2):  # 볼륨 조건 완화
            
            # 수수료를 고려한 목표가
            target_price = current_price * 0.96  # 4% 목표
            
            if self.should_trade(current_price, target_price):
                signal_type = SignalType.SELL
                signal_strength = 0.7
                signal_confidence = 0.6
                reason_parts.append(f"하락 돌파 ({self.min_breakout_pct*50:.1f}%)")
        
        # 신호 생성 (조건 완화)
        if signal_type and signal_strength > 0.6:
            quantity = self.calculate_optimal_position_size(100000, current_price, 
                                                          current_price * 0.95, ExchangeType.BITHUMB)
            
            signal = TradingSignal(
                signal_type=signal_type,
                strength=signal_strength,
                confidence=signal_confidence,
                price=current_price,
                quantity=quantity,
                stop_loss=current_price * 0.95 if signal_type == SignalType.BUY else current_price * 1.05,
                take_profit=current_price * 1.08 if signal_type == SignalType.BUY else current_price * 0.92,
                timestamp=datetime.now(),
                reason=" | ".join(reason_parts),
                metadata={
                    'strategy': 'breakout',
                    'commission_optimized': True,
                    'required_return': self.calculate_required_return(current_price),
                    'volume_ratio': current_volume / avg_volume
                }
            )
            
            signals.append(signal)
        
        return signals


class MeanReversionStrategy(CommissionOptimizedStrategy):
    """평균 회귀 전략 - 수수료 최적화"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.bollinger_period = config.parameters.get('bollinger_period', 20)
        self.bollinger_std = config.parameters.get('bollinger_std', 2.0)
        self.rsi_period = config.parameters.get('rsi_period', 14)
        self.oversold_threshold = config.parameters.get('oversold_threshold', 30)
        self.overbought_threshold = config.parameters.get('overbought_threshold', 70)
        
    def analyze(self, data: pd.DataFrame) -> List[TradingSignal]:
        """평균 회귀 신호 분석"""
        signals = []
        
        if len(data) < self.bollinger_period + 10:
            return signals
        
        close = data['close']
        
        # 기술적 지표 계산
        from analysis.technical_indicators import TechnicalAnalyzer
        ti = TechnicalAnalyzer()
        
        bollinger = ti.calculate_bollinger_bands(close, self.bollinger_period, self.bollinger_std)
        rsi = ti.calculate_rsi(close, self.rsi_period)
        
        # 현재 값들
        current_price = close.iloc[-1]
        current_upper = bollinger['upper'].iloc[-1]
        current_middle = bollinger['middle'].iloc[-1]
        current_lower = bollinger['lower'].iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        signal_type = None
        signal_strength = 0.0
        signal_confidence = 0.0
        reason_parts = []
        
        # 과매도 구간에서 매수 (조건 완화)
        if (not pd.isna(current_lower) and not pd.isna(current_rsi) and
            current_price <= current_lower * 1.01 and current_rsi < 35):  # 조건 완화
            
            # 수수료를 고려한 목표가 (더 낮은 목표)
            target_price = current_price * 1.025  # 2.5% 목표
            
            if self.should_trade(current_price, target_price):
                signal_type = SignalType.BUY
                signal_strength = 0.6
                signal_confidence = 0.5
                reason_parts.append("볼린저 밴드 하단 + RSI 과매도")
        
        # 과매수 구간에서 매도 (조건 완화)
        elif (not pd.isna(current_upper) and not pd.isna(current_rsi) and
              current_price >= current_upper * 0.99 and current_rsi > 65):  # 조건 완화
            
            # 수수료를 고려한 목표가 (더 낮은 목표)
            target_price = current_price * 0.975  # 2.5% 목표
            
            if self.should_trade(current_price, target_price):
                signal_type = SignalType.SELL
                signal_strength = 0.6
                signal_confidence = 0.5
                reason_parts.append("볼린저 밴드 상단 + RSI 과매수")
        
        # 신호 생성 (조건 완화)
        if signal_type and signal_strength > 0.5:
            quantity = self.calculate_optimal_position_size(100000, current_price, 
                                                          current_price * 0.95, ExchangeType.BITHUMB)
            
            signal = TradingSignal(
                signal_type=signal_type,
                strength=signal_strength,
                confidence=signal_confidence,
                price=current_price,
                quantity=quantity,
                stop_loss=current_price * 0.95 if signal_type == SignalType.BUY else current_price * 1.05,
                take_profit=target_price,
                timestamp=datetime.now(),
                reason=" | ".join(reason_parts),
                metadata={
                    'strategy': 'mean_reversion',
                    'commission_optimized': True,
                    'required_return': self.calculate_required_return(current_price),
                    'bollinger_position': (current_price - current_lower) / (current_upper - current_lower)
                }
            )
            
            signals.append(signal)
        
        return signals
