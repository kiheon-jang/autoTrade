# 데이터베이스 스키마 문서

## 📊 데이터베이스 구조 개요

이 프로젝트는 3개의 데이터베이스를 사용합니다:
- **PostgreSQL**: 사용자, 전략, 주문 등 메타데이터 저장
- **TimescaleDB**: 시계열 시장 데이터 저장 (PostgreSQL 확장)
- **Redis**: 실시간 캐싱 및 세션 관리

## 🗄️ PostgreSQL 스키마

### 사용자 관련 테이블

#### users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    last_login TIMESTAMP WITH TIME ZONE,
    bithumb_api_key VARCHAR(255),
    bithumb_secret_key VARCHAR(255),
    telegram_chat_id VARCHAR(50),
    email_notifications BOOLEAN DEFAULT TRUE,
    telegram_notifications BOOLEAN DEFAULT FALSE,
    max_risk_per_trade VARCHAR(10) DEFAULT '2.0',
    max_total_risk VARCHAR(10) DEFAULT '10.0',
    max_positions INTEGER DEFAULT 5
);
```

#### user_sessions
```sql
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    ip_address VARCHAR(45),
    user_agent TEXT
);
```

### 전략 관련 테이블

#### strategies
```sql
CREATE TABLE strategies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(50) NOT NULL, -- scalping, day_trading, swing_trading, long_term
    description TEXT,
    parameters JSONB NOT NULL DEFAULT '{}',
    risk_per_trade FLOAT DEFAULT 2.0,
    max_positions INTEGER DEFAULT 5,
    stop_loss_pct FLOAT DEFAULT 2.0,
    take_profit_pct FLOAT DEFAULT 4.0,
    is_active BOOLEAN DEFAULT FALSE,
    is_backtesting BOOLEAN DEFAULT FALSE,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    total_pnl FLOAT DEFAULT 0.0,
    win_rate FLOAT DEFAULT 0.0,
    max_drawdown FLOAT DEFAULT 0.0,
    sharpe_ratio FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    last_executed TIMESTAMP WITH TIME ZONE
);
```

#### strategy_executions
```sql
CREATE TABLE strategy_executions (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    execution_type VARCHAR(50) NOT NULL, -- signal, order, error
    signal_data JSONB,
    order_data JSONB,
    error_message TEXT,
    market_data JSONB,
    success BOOLEAN DEFAULT TRUE,
    execution_time FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### backtest_results
```sql
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    initial_capital FLOAT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    total_return FLOAT DEFAULT 0.0,
    annual_return FLOAT DEFAULT 0.0,
    max_drawdown FLOAT DEFAULT 0.0,
    sharpe_ratio FLOAT DEFAULT 0.0,
    sortino_ratio FLOAT DEFAULT 0.0,
    win_rate FLOAT DEFAULT 0.0,
    profit_factor FLOAT DEFAULT 0.0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    avg_win FLOAT DEFAULT 0.0,
    avg_loss FLOAT DEFAULT 0.0,
    largest_win FLOAT DEFAULT 0.0,
    largest_loss FLOAT DEFAULT 0.0,
    equity_curve JSONB,
    trade_history JSONB,
    monthly_returns JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    execution_time FLOAT
);
```

### 주문 관련 테이블

#### orders
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    strategy_id INTEGER,
    bithumb_order_id VARCHAR(100) UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    order_type order_type_enum NOT NULL, -- buy, sell
    order_side VARCHAR(10) NOT NULL, -- bid, ask
    quantity FLOAT NOT NULL,
    price FLOAT,
    filled_quantity FLOAT DEFAULT 0.0,
    remaining_quantity FLOAT NOT NULL,
    status order_status_enum DEFAULT 'pending',
    fee FLOAT DEFAULT 0.0,
    fee_currency VARCHAR(10) DEFAULT 'KRW',
    average_fill_price FLOAT,
    total_filled_value FLOAT DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    notes TEXT
);
```

#### trades
```sql
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    strategy_id INTEGER,
    bithumb_trade_id VARCHAR(100) UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    trade_side VARCHAR(10) NOT NULL, -- buy, sell
    quantity FLOAT NOT NULL,
    price FLOAT NOT NULL,
    value FLOAT NOT NULL,
    fee FLOAT DEFAULT 0.0,
    fee_currency VARCHAR(10) DEFAULT 'KRW',
    trade_time TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### positions
```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    strategy_id INTEGER,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- long, short
    quantity FLOAT NOT NULL,
    entry_price FLOAT NOT NULL,
    current_price FLOAT,
    unrealized_pnl FLOAT DEFAULT 0.0,
    realized_pnl FLOAT DEFAULT 0.0,
    total_pnl FLOAT DEFAULT 0.0,
    stop_loss_price FLOAT,
    take_profit_price FLOAT,
    is_active BOOLEAN DEFAULT TRUE,
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

#### portfolios
```sql
CREATE TABLE portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    total_balance FLOAT DEFAULT 0.0,
    available_balance FLOAT DEFAULT 0.0,
    invested_balance FLOAT DEFAULT 0.0,
    total_return FLOAT DEFAULT 0.0,
    daily_return FLOAT DEFAULT 0.0,
    max_drawdown FLOAT DEFAULT 0.0,
    sharpe_ratio FLOAT DEFAULT 0.0,
    holdings JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    last_rebalanced TIMESTAMP WITH TIME ZONE
);
```

## 📈 TimescaleDB 스키마 (시계열 데이터)

### 시장 데이터 테이블

#### tickers (하이퍼테이블)
```sql
CREATE TABLE tickers (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    opening_price FLOAT NOT NULL,
    closing_price FLOAT NOT NULL,
    high_price FLOAT NOT NULL,
    low_price FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    value FLOAT NOT NULL,
    change_24h FLOAT NOT NULL,
    change_rate_24h FLOAT NOT NULL,
    bid_price FLOAT,
    ask_price FLOAT,
    spread FLOAT
);

-- 하이퍼테이블로 변환
SELECT create_hypertable('tickers', 'timestamp');
```

#### orderbooks (하이퍼테이블)
```sql
CREATE TABLE orderbooks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    bids TEXT NOT NULL, -- JSON 배열
    asks TEXT NOT NULL, -- JSON 배열
    bid_volume FLOAT,
    ask_volume FLOAT,
    spread FLOAT,
    mid_price FLOAT
);

SELECT create_hypertable('orderbooks', 'timestamp');
```

#### transactions (하이퍼테이블)
```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price FLOAT NOT NULL,
    quantity FLOAT NOT NULL,
    value FLOAT NOT NULL,
    side VARCHAR(10) NOT NULL,
    bithumb_tx_id VARCHAR(100) UNIQUE
);

SELECT create_hypertable('transactions', 'timestamp');
```

#### candles (하이퍼테이블)
```sql
CREATE TABLE candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    open_price FLOAT NOT NULL,
    high_price FLOAT NOT NULL,
    low_price FLOAT NOT NULL,
    close_price FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    vwap FLOAT,
    rsi FLOAT,
    macd FLOAT,
    bollinger_upper FLOAT,
    bollinger_middle FLOAT,
    bollinger_lower FLOAT
);

SELECT create_hypertable('candles', 'timestamp');
```

#### technical_indicators (하이퍼테이블)
```sql
CREATE TABLE technical_indicators (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    -- 이동평균선
    ma_5 FLOAT, ma_10 FLOAT, ma_20 FLOAT, ma_50 FLOAT, ma_100 FLOAT, ma_200 FLOAT,
    -- 지수이동평균선
    ema_8 FLOAT, ema_13 FLOAT, ema_21 FLOAT, ema_50 FLOAT, ema_200 FLOAT,
    -- 오실레이터
    rsi_14 FLOAT, stochastic_k FLOAT, stochastic_d FLOAT,
    macd_line FLOAT, macd_signal FLOAT, macd_histogram FLOAT, cci_20 FLOAT,
    -- 변동성 지표
    atr_14 FLOAT, bollinger_upper FLOAT, bollinger_middle FLOAT, bollinger_lower FLOAT,
    keltner_upper FLOAT, keltner_middle FLOAT, keltner_lower FLOAT,
    -- 볼륨 지표
    volume_ma_20 FLOAT, obv FLOAT, vwap FLOAT
);

SELECT create_hypertable('technical_indicators', 'timestamp');
```

## 🔴 Redis 스키마

### 캐시 키 구조

```
# 사용자 세션
session:{session_token} -> JSON
user:{user_id}:active_sessions -> SET

# 시장 데이터 캐시
ticker:{symbol} -> JSON (TTL: 1초)
orderbook:{symbol} -> JSON (TTL: 1초)
candle:{symbol}:{timeframe}:{timestamp} -> JSON (TTL: 1시간)

# 전략 실행 상태
strategy:{strategy_id}:status -> JSON
strategy:{strategy_id}:signals -> LIST (최근 100개)

# 주문 상태
order:{order_id}:status -> JSON
user:{user_id}:active_orders -> SET

# 알림 큐
notifications:{user_id} -> LIST
telegram_queue -> LIST
```

## 📊 인덱스 전략

### PostgreSQL 인덱스
```sql
-- 사용자 관련
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);

-- 전략 관련
CREATE INDEX idx_strategies_user_id ON strategies(user_id);
CREATE INDEX idx_strategies_active ON strategies(is_active);
CREATE INDEX idx_strategy_executions_strategy_id ON strategy_executions(strategy_id);
CREATE INDEX idx_strategy_executions_created_at ON strategy_executions(created_at);

-- 주문 관련
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_strategy_id ON orders(strategy_id);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_trade_time ON trades(trade_time);
```

### TimescaleDB 인덱스
```sql
-- 시계열 데이터 인덱스
CREATE INDEX idx_tickers_symbol_time ON tickers(symbol, timestamp);
CREATE INDEX idx_orderbooks_symbol_time ON orderbooks(symbol, timestamp);
CREATE INDEX idx_transactions_symbol_time ON transactions(symbol, timestamp);
CREATE INDEX idx_candles_symbol_timeframe_time ON candles(symbol, timeframe, timestamp);
CREATE INDEX idx_indicators_symbol_timeframe_time ON technical_indicators(symbol, timeframe, timestamp);
```

## 🔄 데이터 보존 정책

### TimescaleDB 보존 정책
```sql
-- 30일 데이터 보존
SELECT add_retention_policy('tickers', INTERVAL '30 days');
SELECT add_retention_policy('orderbooks', INTERVAL '30 days');
SELECT add_retention_policy('transactions', INTERVAL '30 days');
SELECT add_retention_policy('candles', INTERVAL '30 days');
SELECT add_retention_policy('technical_indicators', INTERVAL '30 days');
```

## 🚀 성능 최적화

### 연결 풀링
- PostgreSQL: 최대 10개 연결, 20개 오버플로우
- TimescaleDB: 최대 10개 연결, 20개 오버플로우
- Redis: 연결 풀링 자동 관리

### 쿼리 최적화
- 시계열 데이터는 TimescaleDB의 압축 기능 활용
- 자주 조회되는 데이터는 Redis 캐싱
- 복합 인덱스로 조회 성능 최적화

### 모니터링
- 데이터베이스 연결 상태 모니터링
- 쿼리 성능 모니터링
- 디스크 사용량 모니터링
