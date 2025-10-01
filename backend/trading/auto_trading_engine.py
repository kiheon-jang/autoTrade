"""
AI 전략 기반 자동 거래 엔진
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from services.bithumb_client import BithumbClient, BithumbAPIError
from trading.realtime_engine import RealtimeTradingEngine, TradingMode, RealtimeTrade, Position
from core.commission import CommissionCalculator, ExchangeType


logger = logging.getLogger(__name__)


class AutoTradingEngine:
    """AI 전략 기반 자동 거래 엔진"""
    
    def __init__(self, 
                 trading_mode: str = "paper",  # paper, live
                 initial_capital: float = 1000000):
        self.trading_mode = TradingMode.PAPER if trading_mode == "paper" else TradingMode.LIVE
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # 빗썸 클라이언트
        self.bithumb_client = BithumbClient()
        
        # 실시간 거래 엔진
        self.trading_engine = RealtimeTradingEngine(
            mode=self.trading_mode,
            initial_capital=initial_capital
        )
        
        # 커미션 계산기
        self.commission_calc = CommissionCalculator()
        
        # 활성 전략
        self.active_strategy = None
        self.strategy_config = None
        
        # 포지션 관리
        self.positions: Dict[str, Position] = {}
        self.trades: List[RealtimeTrade] = []
        
        # 리스크 관리
        self.max_position_size = 0.3  # 자본의 30%
        self.max_risk_per_trade = 0.02  # 거래당 2% 리스크
        self.stop_loss_pct = 0.05  # 5% 손절
        self.take_profit_pct = 0.10  # 10% 익절
        
        # 실행 상태
        self.is_running = False
        self.monitoring_task = None
        
    async def start_strategy(self, strategy_recommendation: Dict, config: Dict):
        """전략 시작"""
        try:
            self.active_strategy = strategy_recommendation
            self.strategy_config = config
            
            # 리스크 설정 업데이트
            if 'max_risk' in config:
                self.max_risk_per_trade = config['max_risk']
            
            self.is_running = True
            
            logger.info(f"자동거래 시작: {strategy_recommendation['strategy_name']}")
            logger.info(f"거래 모드: {self.trading_mode.value}")
            logger.info(f"초기 자본: {self.initial_capital:,.0f}원")
            
            # 백그라운드에서 전략 실행 루프 시작
            strategy_type = strategy_recommendation.get('strategy_type', 'adaptive')
            self.strategy_task = asyncio.create_task(self._strategy_loop(strategy_type))
                
            # 포지션 모니터링 시작 (손절/익절)
            self.monitoring_task = asyncio.create_task(self._monitor_positions())
            
            logger.info(f"백그라운드 거래 엔진 시작됨 - {strategy_type} 전략")
            
            return {
                "success": True,
                "message": f"전략 '{strategy_recommendation['strategy_name']}' 실행 시작",
                "mode": self.trading_mode.value,
                "initial_capital": self.initial_capital
            }
            
        except Exception as e:
            logger.error(f"전략 시작 실패: {e}", exc_info=True)
            raise
    
    async def stop_strategy(self):
        """전략 중지 및 모든 포지션 정리"""
        try:
            self.is_running = False
            
            # 전략 실행 루프 중지
            if hasattr(self, 'strategy_task') and self.strategy_task:
                self.strategy_task.cancel()
                try:
                    await self.strategy_task
                except asyncio.CancelledError:
                    pass
            
            # 모니터링 중지
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # 모든 포지션 청산
            await self._close_all_positions()
            
            logger.info("자동거래 중지 완료")
            
            return {
                "success": True,
                "message": "자동거래가 중지되었습니다",
                "final_capital": self.current_capital,
                "total_pnl": self.current_capital - self.initial_capital,
                "total_trades": len(self.trades)
            }
            
        except Exception as e:
            logger.error(f"전략 중지 실패: {e}")
            raise
    
    async def _strategy_loop(self, strategy_type: str):
        """전략 실행 루프 - 지속적으로 시장 분석 및 거래"""
        logger.info(f"🔄 전략 루프 시작: {strategy_type}")
        
        while self.is_running:
            try:
                # 전략 타입별 실행 주기
                if strategy_type == 'scalping':
                    interval = 30  # 30초마다 (고빈도)
                elif strategy_type == 'dca':
                    interval = 3600  # 1시간마다
                else:
                    interval = 300  # 5분마다 (기본)
                
                # 전략 실행
                if strategy_type == 'momentum':
                    await self._execute_momentum_strategy()
                elif strategy_type == 'scalping':
                    await self._execute_scalping_strategy()
                elif strategy_type == 'swing_trading':
                    await self._execute_swing_strategy()
                elif strategy_type == 'dca':
                    await self._execute_dca_strategy()
                else:
                    await self._execute_adaptive_strategy()
                
                logger.info(f"✓ {strategy_type} 전략 실행 완료, {interval}초 후 재실행")
                
                # 다음 실행까지 대기
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info("전략 루프 중지됨")
                break
            except Exception as e:
                logger.error(f"전략 실행 오류: {e}", exc_info=True)
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    async def _execute_momentum_strategy(self):
        """모멘텀 전략 실행 (실시간 시장 데이터로 재분석)"""
        try:
            # 현재 시장 데이터 다시 가져오기
            technical_signals = {}
            ml_signals = {}
            
            # 실시간 시장 데이터 조회
            for symbol in ['BTC', 'ETH', 'XRP']:
                try:
                    ticker = await self.bithumb_client.get_ticker(symbol)
                    current_price = float(ticker['closing_price'])
                    
                    # 간단한 시그널 생성 (실제로는 더 복잡한 분석 필요)
                    # 여기서는 원래 전략의 ML 신호 재사용
                    orig_ml = self.active_strategy.get('ml_signals', {}).get(symbol, {})
                    
                    if orig_ml.get('signal_type') == 'BUY' and orig_ml.get('confidence', 0) > 0.7:
                        # 이미 포지션이 있으면 스킵
                        if symbol in self.positions:
                            continue
                            
                        # 매수 실행
                        await self._execute_buy_order(
                            symbol=symbol,
                            confidence=orig_ml.get('confidence', 0.7),
                            signal_strength=orig_ml.get('strength', 0.5)
                        )
                        
                except Exception as e:
                    logger.error(f"{symbol} 분석 오류: {e}")
                    
        except Exception as e:
            logger.error(f"모멘텀 전략 실행 오류: {e}")
    
    async def _execute_scalping_strategy(self):
        """스캘핑 전략 실행 (실시간 분석)"""
        try:
            # 실시간 시장 데이터로 RSI 재계산
            for symbol in ['BTC', 'ETH']:
                try:
                    # 현재 가격 조회
                    ticker = await self.bithumb_client.get_ticker(symbol)
                    current_price = float(ticker['closing_price'])
                    
                    # 원래 신호 참조 (실제로는 실시간 RSI 계산 필요)
                    orig_signals = self.active_strategy.get('technical_signals', {}).get(symbol, {})
                    indicators = orig_signals.get('indicators', {})
                    rsi = indicators.get('rsi_14', 50)
                    
                    logger.info(f"📊 {symbol} RSI: {rsi:.2f}, 가격: {current_price:,.0f}원")
                    
                    if rsi < 30 and symbol not in self.positions:  # 과매도
                        logger.info(f"🎯 {symbol} 과매도 감지 (RSI: {rsi:.2f}) - 매수 시도")
                        await self._execute_buy_order(symbol, confidence=0.6, signal_strength=0.3, size_multiplier=0.5)
                    elif rsi > 70 and symbol in self.positions:  # 과매수
                        logger.info(f"🎯 {symbol} 과매수 감지 (RSI: {rsi:.2f}) - 매도 시도")
                        await self._execute_sell_order(symbol, confidence=0.6, signal_strength=0.3)
                        
                except Exception as e:
                    logger.error(f"{symbol} 스캘핑 오류: {e}")
                    
        except Exception as e:
            logger.error(f"스캘핑 전략 실행 오류: {e}")
    
    async def _execute_swing_strategy(self):
        """스윙 트레이딩 전략 실행 (실시간 분석)"""
        try:
            for symbol in ['BTC', 'ETH', 'XRP']:
                try:
                    # 현재 가격 조회
                    ticker = await self.bithumb_client.get_ticker(symbol)
                    current_price = float(ticker['closing_price'])
                    
                    # 원래 신호 참조
                    orig_signals = self.active_strategy.get('technical_signals', {}).get(symbol, {})
                    indicators = orig_signals.get('indicators', {})
                    
                    sma_5 = indicators.get('sma_5', 0)
                    sma_20 = indicators.get('sma_20', 0)
                    
                    logger.info(f"📊 {symbol} SMA(5): {sma_5:,.0f}, SMA(20): {sma_20:,.0f}")
                    
                    if sma_5 > sma_20 and symbol not in self.positions:  # 골든크로스
                        logger.info(f"🎯 {symbol} 골든크로스 감지 - 매수 시도")
                        await self._execute_buy_order(symbol, confidence=0.7, signal_strength=0.6)
                    elif sma_5 < sma_20 and symbol in self.positions:  # 데드크로스
                        logger.info(f"🎯 {symbol} 데드크로스 감지 - 매도 시도")
                        await self._execute_sell_order(symbol, confidence=0.7, signal_strength=0.6)
                        
                except Exception as e:
                    logger.error(f"{symbol} 스윙 분석 오류: {e}")
                    
        except Exception as e:
            logger.error(f"스윙 전략 실행 오류: {e}")
    
    async def _execute_dca_strategy(self):
        """달러 코스트 애버리징 전략 실행 (정기 매수)"""
        try:
            # 정기적으로 일정 금액 매수
            symbols = ['BTC', 'ETH']
            amount_per_symbol = self.current_capital * 0.05  # 자본의 5%씩
            
            logger.info(f"🔄 DCA 전략 실행: 각 코인 {amount_per_symbol:,.0f}원씩 매수")
            
            for symbol in symbols:
                try:
                    await self._execute_buy_order(
                        symbol, 
                        confidence=0.85, 
                        signal_strength=0.5,
                        fixed_amount=amount_per_symbol
                    )
                except Exception as e:
                    logger.error(f"{symbol} DCA 매수 오류: {e}")
                
        except Exception as e:
            logger.error(f"DCA 전략 실행 오류: {e}")
    
    async def _execute_adaptive_strategy(self):
        """적응형 전략 실행 (실시간 분석)"""
        try:
            # 실시간 시장 데이터로 재분석
            for symbol in ['BTC', 'ETH', 'XRP']:
                try:
                    # 현재 가격 조회
                    ticker = await self.bithumb_client.get_ticker(symbol)
                    current_price = float(ticker['closing_price'])
                    
                    # ML 신호 참조
                    ml_signal = self.active_strategy.get('ml_signals', {}).get(symbol, {})
                    signal_type = ml_signal.get('signal_type', 'HOLD')
                    confidence = ml_signal.get('confidence', 0.5)
                    
                    logger.info(f"📊 {symbol} ML 신호: {signal_type} (신뢰도: {confidence:.1%})")
                    
                    if signal_type == 'BUY' and confidence > 0.7 and symbol not in self.positions:
                        logger.info(f"🎯 {symbol} 매수 신호 감지 - 매수 시도")
                        await self._execute_buy_order(symbol, confidence, ml_signal.get('strength', 0.5))
                    elif signal_type == 'SELL' and symbol in self.positions:
                        logger.info(f"🎯 {symbol} 매도 신호 감지 - 매도 시도")
                        await self._execute_sell_order(symbol, confidence, ml_signal.get('strength', 0.5))
                        
                except Exception as e:
                    logger.error(f"{symbol} 적응형 분석 오류: {e}")
                    
        except Exception as e:
            logger.error(f"적응형 전략 실행 오류: {e}")
    
    async def _execute_buy_order(self, symbol: str, confidence: float, signal_strength: float, 
                                  size_multiplier: float = 1.0, fixed_amount: float = None):
        """매수 주문 실행"""
        try:
            # 현재 가격 조회
            ticker = await self.bithumb_client.get_ticker(symbol)
            current_price = float(ticker['closing_price'])
            
            # 포지션 크기 계산
            if fixed_amount:
                order_amount = fixed_amount
            else:
                max_position = self.current_capital * self.max_position_size * size_multiplier
                order_amount = min(max_position, self.current_capital * confidence * 0.3)
            
            # 최소 주문 금액 체크 (5,000원)
            if order_amount < 5000:
                logger.warning(f"{symbol} 매수 주문 금액 부족: {order_amount:,.0f}원")
                return
            
            # 주문 수량 계산
            quantity = order_amount / current_price
            
            # 페이퍼 트레이딩 모드
            if self.trading_mode == TradingMode.PAPER:
                # 커미션 계산
                commission = self.commission_calc.calculate_commission(
                    order_amount, 
                    ExchangeType.BITHUMB, 
                    is_maker=False
                )
                
                # 모의 거래 기록
                trade = RealtimeTrade(
                    id=f"paper_{datetime.now().timestamp()}",
                    symbol=symbol,
                    side='buy',
                    amount=quantity,
                    price=current_price,
                    timestamp=datetime.now(),
                    order_id=f"paper_order_{len(self.trades)}",
                    status='filled',
                    commission=commission,
                    net_amount=quantity,
                    strategy_id=self.active_strategy.get('strategy_id'),
                    signal_strength=signal_strength,
                    signal_confidence=confidence
                )
                
                self.trades.append(trade)
                self.current_capital -= (order_amount + commission)
                
                # 포지션 업데이트
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    total_amount = pos.amount + quantity
                    pos.avg_price = (pos.avg_price * pos.amount + current_price * quantity) / total_amount
                    pos.amount = total_amount
                else:
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        side='long',
                        amount=quantity,
                        avg_price=current_price
                    )
                
                logger.info(f"📈 [PAPER] {symbol} 매수: {quantity:.8f} @ {current_price:,.0f}원 (신뢰도: {confidence:.1%})")
                
            # 실거래 모드
            else:
                # 실제 API 주문
                order_result = await self.bithumb_client.place_order(
                    symbol=symbol,
                    side='bid',  # 매수
                    order_type='market',
                    quantity=quantity
                )
                
                logger.info(f"📈 [LIVE] {symbol} 매수 주문: {order_result}")
                
                # 주문 결과 기록
                # ... (실제 주문 결과 처리)
                
        except Exception as e:
            logger.error(f"{symbol} 매수 실행 오류: {e}")
    
    async def _execute_sell_order(self, symbol: str, confidence: float, signal_strength: float):
        """매도 주문 실행"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            
            # 현재 가격 조회
            ticker = await self.bithumb_client.get_ticker(symbol)
            current_price = float(ticker['closing_price'])
            
            # 페이퍼 트레이딩 모드
            if self.trading_mode == TradingMode.PAPER:
                # 전량 매도
                quantity = position.amount
                order_amount = quantity * current_price
                
                # 커미션 계산
                commission = self.commission_calc.calculate_commission(
                    order_amount,
                    ExchangeType.BITHUMB,
                    is_maker=False
                )
                
                # 손익 계산
                pnl = (current_price - position.avg_price) * quantity - commission
                
                # 모의 거래 기록
                trade = RealtimeTrade(
                    id=f"paper_{datetime.now().timestamp()}",
                    symbol=symbol,
                    side='sell',
                    amount=quantity,
                    price=current_price,
                    timestamp=datetime.now(),
                    order_id=f"paper_order_{len(self.trades)}",
                    status='filled',
                    commission=commission,
                    net_amount=quantity,
                    strategy_id=self.active_strategy.get('strategy_id'),
                    signal_strength=signal_strength,
                    signal_confidence=confidence
                )
                
                self.trades.append(trade)
                self.current_capital += (order_amount - commission)
                
                # 포지션 제거
                del self.positions[symbol]
                
                logger.info(f"📉 [PAPER] {symbol} 매도: {quantity:.8f} @ {current_price:,.0f}원 (손익: {pnl:+,.0f}원)")
                
            # 실거래 모드
            else:
                # 실제 API 주문
                order_result = await self.bithumb_client.place_order(
                    symbol=symbol,
                    side='ask',  # 매도
                    order_type='market',
                    quantity=position.amount
                )
                
                logger.info(f"📉 [LIVE] {symbol} 매도 주문: {order_result}")
                
        except Exception as e:
            logger.error(f"{symbol} 매도 실행 오류: {e}")
    
    async def _monitor_positions(self):
        """포지션 모니터링 및 손절/익절"""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # 10초마다 체크
                
                for symbol, position in list(self.positions.items()):
                    # 현재 가격 조회
                    ticker = await self.bithumb_client.get_ticker(symbol)
                    current_price = float(ticker['closing_price'])
                    
                    # 손익률 계산
                    pnl_pct = (current_price - position.avg_price) / position.avg_price
                    
                    # 손절 체크
                    if pnl_pct <= -self.stop_loss_pct:
                        logger.warning(f"⚠️ {symbol} 손절 실행: {pnl_pct:.1%}")
                        await self._execute_sell_order(symbol, confidence=1.0, signal_strength=1.0)
                    
                    # 익절 체크
                    elif pnl_pct >= self.take_profit_pct:
                        logger.info(f"✅ {symbol} 익절 실행: {pnl_pct:.1%}")
                        await self._execute_sell_order(symbol, confidence=1.0, signal_strength=1.0)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"포지션 모니터링 오류: {e}")
    
    async def _close_all_positions(self):
        """모든 포지션 청산"""
        for symbol in list(self.positions.keys()):
            try:
                await self._execute_sell_order(symbol, confidence=1.0, signal_strength=1.0)
            except Exception as e:
                logger.error(f"{symbol} 청산 실패: {e}")
    
    def get_status(self) -> Dict:
        """현재 상태 조회"""
        total_pnl = self.current_capital - self.initial_capital
        pnl_pct = (total_pnl / self.initial_capital) * 100
        
        return {
            "is_running": self.is_running,
            "mode": self.trading_mode.value,
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "total_pnl": total_pnl,
            "pnl_percentage": pnl_pct,
            "positions": {
                symbol: {
                    "amount": pos.amount,
                    "avg_price": pos.avg_price,
                    "side": pos.side
                }
                for symbol, pos in self.positions.items()
            },
            "total_trades": len(self.trades),
            "active_strategy": self.active_strategy.get('strategy_name') if self.active_strategy else None
        }


# 전역 인스턴스
_trading_engine_instance: Optional[AutoTradingEngine] = None


def get_trading_engine(trading_mode: str = "paper", initial_capital: float = 1000000) -> AutoTradingEngine:
    """자동거래 엔진 인스턴스 반환"""
    global _trading_engine_instance
    
    if _trading_engine_instance is None:
        _trading_engine_instance = AutoTradingEngine(trading_mode, initial_capital)
    
    return _trading_engine_instance

