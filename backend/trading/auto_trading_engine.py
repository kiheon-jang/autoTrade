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
from trading.realtime_analyzer import get_realtime_analyzer
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
        
        # 실시간 시장 분석기 (100개 코인 계층적 분석)
        self.market_analyzer = get_realtime_analyzer()
        
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
            logger.info(f"🔄 전략 시작 요청: {strategy_recommendation.get('strategy_name', 'Unknown')}")
            logger.info(f"전략 타입: {strategy_recommendation.get('strategy_type', 'Unknown')}")
            logger.info(f"대상 코인: {strategy_recommendation.get('target_symbols', [])}")
            
            self.active_strategy = strategy_recommendation
            self.strategy_config = config
            
            # 리스크 설정 업데이트
            if 'max_risk' in config:
                self.max_risk_per_trade = config['max_risk']
            
            self.is_running = True
            logger.info(f"✅ is_running = True 설정됨")
            
            logger.info(f"자동거래 시작: {strategy_recommendation['strategy_name']}")
            logger.info(f"거래 모드: {self.trading_mode.value}")
            logger.info(f"초기 자본: {self.initial_capital:,.0f}원")
            
            # 실시간 분석기 시작
            logger.info("📡 실시간 시장 분석기 시작 중...")
            await self.market_analyzer.start()
            logger.info("📡 실시간 시장 분석기 시작됨")
            
            # 초기 신호를 ML 캐시에 주입 (즉시 거래 기회 제공)
            if 'ml_signals' in strategy_recommendation:
                for symbol, signal in strategy_recommendation['ml_signals'].items():
                    self.market_analyzer.ml_signals_cache[symbol] = signal
                    self.market_analyzer.ml_updated_at[symbol] = datetime.now()
                logger.info(f"✅ 초기 ML 신호 로드: {len(strategy_recommendation.get('ml_signals', {}))}개 코인")
            
            # 백그라운드에서 전략 실행 루프 시작
            strategy_type = strategy_recommendation.get('strategy_type', 'adaptive')
            logger.info(f"🔄 전략 루프 시작: {strategy_type}")
            try:
                self.strategy_task = asyncio.create_task(self._strategy_loop(strategy_type))
                logger.info(f"✅ 전략 루프 태스크 생성됨")
            except Exception as e:
                logger.error(f"❌ 전략 루프 태스크 생성 실패: {e}", exc_info=True)
                raise
                
            # 포지션 모니터링 시작 (손절/익절)
            logger.info("🔄 포지션 모니터링 시작...")
            try:
                self.monitoring_task = asyncio.create_task(self._monitor_positions())
                logger.info(f"✅ 포지션 모니터링 태스크 생성됨")
            except Exception as e:
                logger.error(f"❌ 포지션 모니터링 태스크 생성 실패: {e}", exc_info=True)
                raise
            
            logger.info(f"🚀 백그라운드 거래 엔진 시작됨 - {strategy_type} 전략")
            logger.info(f"✅ is_running 상태: {self.is_running}")
            
            # 거래 시작 확인을 위한 추가 로깅
            logger.info(f"📊 전략 루프 태스크 상태: {self.strategy_task is not None}")
            logger.info(f"📊 모니터링 태스크 상태: {self.monitoring_task is not None}")
            logger.info(f"📊 시장 분석기 상태: {self.market_analyzer is not None}")
            
            return {
                "success": True,
                "message": f"전략 '{strategy_recommendation['strategy_name']}' 실행 시작",
                "mode": self.trading_mode.value,
                "initial_capital": self.initial_capital
            }
            
        except Exception as e:
            logger.error(f"전략 시작 실패: {e}", exc_info=True)
            self.is_running = False
            raise
    
    async def stop_strategy(self):
        """전략 중지 및 모든 포지션 정리"""
        try:
            self.is_running = False
            
            # 실시간 분석기 중지
            await self.market_analyzer.stop()
            
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
                # 전략 타입별 실행 주기 (캐시 데이터 사용 - API 호출 없음!)
                if strategy_type == 'scalping':
                    interval = 10  # 10초마다 (초고빈도)
                elif strategy_type == 'dca':
                    interval = 3600  # 1시간마다 (정기 매수)
                else:
                    interval = 60  # 1분마다 (기본) - 5분에서 단축!
                
                # 전략 실행
                if strategy_type == 'momentum':
                    await self._execute_momentum_strategy()
                elif strategy_type == 'scalping':
                    await self._execute_scalping_strategy()
                elif strategy_type == 'swing_trading':
                    await self._execute_swing_strategy()
                elif strategy_type == 'dca':
                    await self._execute_dca_strategy()
                elif strategy_type == 'day_trading':
                    await self._execute_day_trading_strategy()
                elif strategy_type == 'long_term':
                    await self._execute_long_term_strategy()
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
        """모멘텀 전략 실행 (상위 100개 코인 스캔)"""
        try:
            # 거래 기회 상위 10개 가져오기
            top_opportunities = self.market_analyzer.get_top_opportunities(limit=10)
            
            logger.info(f"🔍 상위 기회 스캔: {len(top_opportunities)}개 발견")
            
            for opp in top_opportunities:
                symbol = opp['symbol']
                ml_signal = opp
                
                try:
                    # 매수 조건: BUY 신호 + 신뢰도 70% 이상
                    if opp['signal'] == 'BUY' and opp['confidence'] > 0.7:
                        # 이미 포지션이 있거나 포지션 한도 초과
                        if symbol in self.positions:
                            continue
                        
                        if len(self.positions) >= 5:  # 최대 5개 포지션
                            logger.info(f"⚠️ 최대 포지션 수 도달 (5개)")
                            break
                        
                        # Tier 1 코인은 우선순위
                        tier_bonus = 1.2 if opp['tier'] == 1 else 1.0
                        
                        logger.info(f"🎯 {symbol} [Tier {opp['tier']}] 모멘텀 매수 신호! (신뢰도: {opp['confidence']:.1%})")
                        
                        await self._execute_buy_order(
                            symbol=symbol,
                            confidence=opp['confidence'] * tier_bonus,
                            signal_strength=opp['strength']
                        )
                        
                except Exception as e:
                    logger.error(f"{symbol} 거래 실행 오류: {e}")
                    
        except Exception as e:
            logger.error(f"모멘텀 전략 실행 오류: {e}")
    
    async def _execute_scalping_strategy(self):
        """스캘핑 전략 실행 (Tier 1 집중 스캔)"""
        try:
            # Tier 1 (거래량 급등) 코인만 스캔 - 가장 변동성 큼
            tier_status = self.market_analyzer.get_tier_status()
            tier1_coins = tier_status['tier1']['coins']
            
            logger.info(f"⚡ 스캘핑 스캔: Tier 1 코인 {len(tier1_coins)}개")
            
            for symbol in tier1_coins:
                try:
                    # 실시간 분석 데이터
                    current_price = self.market_analyzer.get_current_price(symbol)
                    indicators = self.market_analyzer.get_indicators(symbol)
                    
                    if not current_price or not indicators:
                        continue
                    
                    # 실시간 RSI (1분마다 재계산됨)
                    rsi = indicators.get('rsi_14', 50)
                    
                    if rsi < 30 and symbol not in self.positions:  # 과매도
                        logger.info(f"🎯 {symbol} 과매도 감지 (RSI: {rsi:.2f}) - 스캘핑 매수")
                        await self._execute_buy_order(symbol, confidence=0.6, signal_strength=0.3, size_multiplier=0.5)
                    elif rsi > 70 and symbol in self.positions:  # 과매수
                        logger.info(f"🎯 {symbol} 과매수 감지 (RSI: {rsi:.2f}) - 스캘핑 매도")
                        await self._execute_sell_order(symbol, confidence=0.6, signal_strength=0.3)
                        
                except Exception as e:
                    logger.error(f"{symbol} 스캘핑 오류: {e}")
                    
        except Exception as e:
            logger.error(f"스캘핑 전략 실행 오류: {e}")
    
    async def _execute_swing_strategy(self):
        """스윙 트레이딩 전략 실행 (완전 실시간 분석)"""
        try:
            for symbol in ['BTC', 'ETH', 'XRP']:
                try:
                    # 실시간 분석 데이터
                    current_price = self.market_analyzer.get_current_price(symbol)
                    indicators = self.market_analyzer.get_indicators(symbol)
                    
                    if not current_price or not indicators:
                        continue
                    
                    # 실시간 이동평균선 (1분마다 재계산됨)
                    sma_5 = indicators.get('sma_5', 0)
                    sma_20 = indicators.get('sma_20', 0)
                    
                    logger.info(f"📊 {symbol} 가격: {current_price:,.0f}원, SMA(5): {sma_5:,.0f}, SMA(20): {sma_20:,.0f}")
                    
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
        """적응형 전략 실행 (전체 100개 코인 스캔)"""
        try:
            # 거래 기회 상위 15개 가져오기
            top_opportunities = self.market_analyzer.get_top_opportunities(limit=15)
            
            logger.info(f"🔍 적응형 전략: 상위 기회 {len(top_opportunities)}개 스캔")
            
            # 티어별로 로그
            tier1_opps = [o for o in top_opportunities if o['tier'] == 1]
            tier2_opps = [o for o in top_opportunities if o['tier'] == 2]
            
            if tier1_opps:
                logger.info(f"🔥 Tier 1 기회: {[o['symbol'] for o in tier1_opps]}")
            if tier2_opps:
                logger.info(f"💎 Tier 2 기회: {[o['symbol'] for o in tier2_opps]}")
            
            for opp in top_opportunities:
                symbol = opp['symbol']
                
                try:
                    if opp['signal'] == 'BUY' and opp['confidence'] > 0.7:
                        if symbol in self.positions or len(self.positions) >= 5:
                            continue
                        
                        logger.info(f"🎯 {symbol} [Tier {opp['tier']}] 적응형 매수! (신뢰도: {opp['confidence']:.1%})")
                        await self._execute_buy_order(symbol, opp['confidence'], opp['strength'])
                        
                    elif opp['signal'] == 'SELL' and symbol in self.positions:
                        logger.info(f"🎯 {symbol} [Tier {opp['tier']}] 적응형 매도! (신뢰도: {opp['confidence']:.1%})")
                        await self._execute_sell_order(symbol, opp['confidence'], opp['strength'])
                        
                except Exception as e:
                    logger.error(f"{symbol} 거래 실행 오류: {e}")
                    
        except Exception as e:
            logger.error(f"적응형 전략 실행 오류: {e}")
    
    async def _execute_buy_order(self, symbol: str, confidence: float, signal_strength: float, 
                                  size_multiplier: float = 1.0, fixed_amount: float = None):
        """매수 주문 실행"""
        try:
            # 실시간 가격 사용
            current_price = self.market_analyzer.get_current_price(symbol)
            if not current_price:
                logger.warning(f"{symbol} 현재 가격 없음 - 주문 스킵")
                return
            
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
                # 커미션 계산 (수량, 가격, 거래소, is_maker 순서)
                commission = self.commission_calc.calculate_commission(
                    quantity,
                    current_price,
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
            
            # 실시간 가격 사용
            current_price = self.market_analyzer.get_current_price(symbol)
            if not current_price:
                logger.warning(f"{symbol} 현재 가격 없음 - 주문 스킵")
                return
            
            # 페이퍼 트레이딩 모드
            if self.trading_mode == TradingMode.PAPER:
                # 전량 매도
                quantity = position.amount
                order_amount = quantity * current_price
                
                # 커미션 계산 (수량, 가격, 거래소, is_maker 순서)
                commission = self.commission_calc.calculate_commission(
                    quantity,
                    current_price,
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
                    # 실시간 가격 사용
                    current_price = self.market_analyzer.get_current_price(symbol)
                    if not current_price:
                        continue
                    
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
        # 보유 코인의 현재 가치 계산
        portfolio_value = 0.0
        for symbol, pos in self.positions.items():
            current_price = self.market_analyzer.get_current_price(symbol)
            if current_price:
                portfolio_value += pos.amount * current_price
        
        # 총 자산 = 현금 + 보유 코인 가치
        total_assets = self.current_capital + portfolio_value
        
        # 총 수수료 계산 (모든 거래에서 지불한 수수료 합계)
        total_commission = sum(trade.commission for trade in self.trades)
        
        # 실제 손익 = 총 자산 - 초기 자본 (수수료는 이미 current_capital에서 차감됨)
        total_pnl = total_assets - self.initial_capital
        pnl_pct = (total_pnl / self.initial_capital) * 100
        
        return {
            "is_running": self.is_running,
            "mode": self.trading_mode.value,
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "portfolio_value": portfolio_value,
            "total_assets": total_assets,
            "total_pnl": total_pnl,
            "pnl_percentage": pnl_pct,
            "total_commission": total_commission,
            "positions": {
                symbol: {
                    "amount": pos.amount,
                    "avg_price": pos.avg_price,
                    "side": pos.side,
                    "current_price": self.market_analyzer.get_current_price(symbol),
                    "unrealized_pnl": (self.market_analyzer.get_current_price(symbol) - pos.avg_price) * pos.amount if self.market_analyzer.get_current_price(symbol) else 0
                }
                for symbol, pos in self.positions.items()
            },
            "total_trades": len(self.trades),
            "trades": [
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "amount": trade.amount,
                    "price": trade.price,
                    "timestamp": trade.timestamp.isoformat(),
                    "status": trade.status,
                    "commission": trade.commission,
                    "order_id": trade.order_id
                }
                for trade in self.trades[-50:]  # 최근 50개 거래만
            ],
            "active_strategy": self.active_strategy.get('strategy_name') if self.active_strategy else None
        }

    async def _execute_day_trading_strategy(self):
        """데이트레이딩 전략 실행 - AI 추천 전략과 동일한 분석 로직 사용"""
        try:
            # AI 추천 전략과 동일한 분석 로직 사용
            # 거래 기회 상위 10개 가져오기
            top_opportunities = self.market_analyzer.get_top_opportunities(limit=10)
            
            logger.info(f"📈 데이트레이딩 스캔: {len(top_opportunities)}개 기회 발견")
            
            for opp in top_opportunities:
                symbol = opp['symbol']
                ml_signal = opp
                
                try:
                    # 매수 조건: BUY 신호 + 신뢰도 50% 이상 (완화)
                    if opp['signal'] == 'BUY' and opp['confidence'] > 0.5:
                        # 이미 포지션이 있거나 포지션 한도 초과
                        if symbol in self.positions:
                            continue
                        
                        if len(self.positions) >= 2:  # 최대 2개 포지션
                            logger.info(f"⚠️ 최대 포지션 수 도달 (2개)")
                            break
                        
                        # Tier 1 코인은 우선순위
                        tier_bonus = 1.2 if opp['tier'] == 1 else 1.0
                        
                        logger.info(f"🎯 {symbol} [Tier {opp['tier']}] 데이트레이딩 매수 신호! (신뢰도: {opp['confidence']:.1%})")
                        
                        await self._execute_buy_order(
                            symbol=symbol,
                            confidence=opp['confidence'] * tier_bonus,
                            signal_strength=opp['strength']
                        )
                        
                except Exception as e:
                    logger.error(f"{symbol} 데이트레이딩 거래 실행 오류: {e}")
                    
        except Exception as e:
            logger.error(f"데이트레이딩 전략 실행 오류: {e}")

    async def _execute_long_term_strategy(self):
        """장기 투자 전략 실행 - AI 추천 전략과 동일한 분석 로직 사용"""
        try:
            # AI 추천 전략과 동일한 분석 로직 사용
            # 거래 기회 상위 5개 가져오기
            top_opportunities = self.market_analyzer.get_top_opportunities(limit=5)
            
            logger.info(f"📊 장기 투자 스캔: {len(top_opportunities)}개 기회 발견")
            
            for opp in top_opportunities:
                symbol = opp['symbol']
                ml_signal = opp
                
                try:
                    # 매수 조건: BUY 신호 + 신뢰도 60% 이상 (완화)
                    if opp['signal'] == 'BUY' and opp['confidence'] > 0.6:
                        # 이미 포지션이 있거나 포지션 한도 초과
                        if symbol in self.positions:
                            continue
                        
                        if len(self.positions) >= 3:  # 최대 3개 포지션
                            logger.info(f"⚠️ 최대 포지션 수 도달 (3개)")
                            break
                        
                        # Tier 1 코인은 우선순위
                        tier_bonus = 1.3 if opp['tier'] == 1 else 1.0
                        
                        logger.info(f"🎯 {symbol} [Tier {opp['tier']}] 장기 투자 매수 신호! (신뢰도: {opp['confidence']:.1%})")
                        
                        await self._execute_buy_order(
                            symbol=symbol,
                            confidence=opp['confidence'] * tier_bonus,
                            signal_strength=opp['strength']
                        )
                        
                except Exception as e:
                    logger.error(f"{symbol} 장기 투자 거래 실행 오류: {e}")
                    
        except Exception as e:
            logger.error(f"장기 투자 전략 실행 오류: {e}")


# 전역 인스턴스
_trading_engine_instance: Optional[AutoTradingEngine] = None


def get_trading_engine(trading_mode: str = "paper", initial_capital: float = 1000000) -> AutoTradingEngine:
    """자동거래 엔진 인스턴스 반환"""
    global _trading_engine_instance
    
    logger.info(f"🔍 get_trading_engine 호출: mode={trading_mode}, capital={initial_capital}")
    logger.info(f"🔍 기존 인스턴스 존재: {_trading_engine_instance is not None}")
    
    if _trading_engine_instance is None:
        logger.info("🆕 새로운 AutoTradingEngine 인스턴스 생성")
        _trading_engine_instance = AutoTradingEngine(trading_mode, initial_capital)
    else:
        logger.info(f"♻️ 기존 인스턴스 재사용: is_running={_trading_engine_instance.is_running}")
    
    return _trading_engine_instance

