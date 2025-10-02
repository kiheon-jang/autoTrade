import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Table, 
  Tag, 
  Typography, 
  Statistic,
  Progress,
  Space,
  Button,
  Badge,
  Descriptions,
  Empty
} from 'antd';
import { 
  ThunderboltOutlined,
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
  SearchOutlined,
  FireOutlined,
  CrownOutlined,
  TrophyOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { aiRecommendationAPI } from '../services/api';

// API 기본 URL 가져오기
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8008';
import { useWebSocket } from '../hooks/useWebSocket';

const { Title, Text } = Typography;

const MonitoringContainer = styled.div.withConfig({
  shouldForwardProp: (prop) => prop !== 'status',
})`
  .status-badge {
    margin-right: 12px;
  }
  
  .trading-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
  }
  
  .position-card {
    border-left: 4px solid #52c41a;
    padding: 16px;
    margin-bottom: 12px;
    background: #f6ffed;
    border-radius: 8px;
  }
  
  .pnl-positive {
    color: #52c41a;
    font-weight: 600;
  }
  
  .pnl-negative {
    color: #ff4d4f;
    font-weight: 600;
  }
  
  .trade-row {
    padding: 12px;
    border-bottom: 1px solid #f0f0f0;
    
    &:hover {
      background: #fafafa;
    }
  }
`;

const Monitoring = () => {
  const [tradingStatus, setTradingStatus] = useState(null);
  const [pnlHistory, setPnlHistory] = useState([]);
  const { isConnected, lastMessage } = useWebSocket();

  useEffect(() => {
    fetchTradingStatus();
    const interval = setInterval(fetchTradingStatus, 5000); // 5초마다 업데이트
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (lastMessage && lastMessage.type === 'trading_update') {
      updateTradingData(lastMessage);
    }
  }, [lastMessage]);

  const fetchTradingStatus = async () => {
    try {
      const response = await aiRecommendationAPI.getTradingStatus();
      
      if (response.is_trading) {
        setTradingStatus(response);
        
        // PnL 히스토리 업데이트
        setPnlHistory(prev => {
          const newEntry = {
            time: new Date().toLocaleTimeString(),
            pnl: response.trading.total_pnl,
            capital: response.trading.current_capital
          };
          return [...prev.slice(-20), newEntry];
        });
        
        // 분석 로그 업데이트 (상위 기회들)
        if (response.analysis && response.analysis.top_opportunities) {
          const topOpps = response.analysis.top_opportunities.slice(0, 10);
          const logEntry = {
            timestamp: new Date().toLocaleTimeString(),
            scanning: response.analysis.scanning_coins,
            opportunities: topOpps
          };
          setAnalysisLog(prev => [logEntry, ...prev.slice(0, 9)]);
        }
      } else {
        setTradingStatus(null);
      }
    } catch (error) {
      console.error('거래 상태 조회 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateTradingData = (data) => {
    setTradingStatus(prev => ({
      ...prev,
      trading: {
        ...prev.trading,
        ...data
      }
    }));
  };

  const handleStopTrading = async () => {
    try {
      await aiRecommendationAPI.stopAutoTrading();
      setTradingStatus(null);
      setPnlHistory([]);
    } catch (error) {
      console.error('거래 중지 실패:', error);
    }
  };

  const tradesColumns = [
    {
      title: '시간',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (time) => new Date(time).toLocaleTimeString(),
    },
    {
      title: '코인',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (symbol) => <Tag color="blue">{symbol}</Tag>,
    },
    {
      title: '타입',
      dataIndex: 'side',
      key: 'side',
      render: (side) => (
        <Tag color={side === 'buy' ? 'green' : 'red'}>
          {side === 'buy' ? '매수' : '매도'}
        </Tag>
      ),
    },
    {
      title: '수량',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount) => amount?.toFixed(8),
    },
    {
      title: '가격',
      dataIndex: 'price',
      key: 'price',
      render: (price) => `${price?.toLocaleString()}원`,
    },
    {
      title: '수수료',
      dataIndex: 'commission',
      key: 'commission',
      render: (commission) => `${commission?.toLocaleString()}원`,
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig = {
          filled: { color: 'success', text: '체결' },
          pending: { color: 'processing', text: '대기' },
          cancelled: { color: 'default', text: '취소' },
          error: { color: 'error', text: '오류' }
        };
        const config = statusConfig[status] || statusConfig.pending;
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
  ];

  // 전통적 전략 상태 확인
  const [traditionalStrategies, setTraditionalStrategies] = useState([]);
  const [traditionalStrategyDetails, setTraditionalStrategyDetails] = useState(null);
  const [aiStrategyDetails, setAiStrategyDetails] = useState(null);
  
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        // 전통적 전략 상태 조회
        const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/strategy-status`);
        const data = await response.json();
        setTraditionalStrategies(data.active_list || []);
        
        // 전통적 전략이 있으면 상세 정보도 가져오기
        if (data.active_list && data.active_list.length > 0) {
          const detailsResponse = await fetch(`${API_BASE_URL}/api/v1/monitoring/traditional-strategy-details`);
          const detailsData = await detailsResponse.json();
          console.log('전통적 전략 상세 정보:', detailsData);
          if (detailsData.success) {
            setTraditionalStrategyDetails(detailsData);
          }
        } else {
          setTraditionalStrategyDetails(null);
        }
        
        // AI 추천 전략 상세 정보 조회
        try {
          const aiDetailsResponse = await fetch(`${API_BASE_URL}/api/v1/monitoring/ai-strategy-details`);
          const aiDetailsData = await aiDetailsResponse.json();
          if (aiDetailsData.success) {
            setAiStrategyDetails(aiDetailsData);
          } else {
            setAiStrategyDetails(null);
          }
        } catch (error) {
          console.error('AI 추천 전략 상세 정보 조회 실패:', error);
          setAiStrategyDetails(null);
        }
      } catch (error) {
        console.error('전략 상태 조회 실패:', error);
      }
    };
    
    fetchStrategies();
    const interval = setInterval(fetchStrategies, 5000); // 5초마다 업데이트
    return () => clearInterval(interval);
  }, []);

  // AI 추천 전략이 실행 중인 경우 상세 모니터링 화면 표시
  if (aiStrategyDetails && aiStrategyDetails.is_trading) {
    const { strategy, trading } = aiStrategyDetails;
    const pnlPercentage = trading.pnl_percentage || 0;
    const isProfitable = pnlPercentage > 0;

    return (
      <MonitoringContainer>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 거래 상태 헤더 (AI Strategy) */}
          <Card className="trading-card">
            <Row gutter={24} align="middle">
              <Col flex="auto">
                <Space size="large">
                  <Badge status="processing" text={
                    <Text style={{ color: 'white', fontSize: '16px' }}>
                      <PlayCircleOutlined /> AI 추천 전략 실행 중
                    </Text>
                  } />
                  <div>
                    <Text style={{ color: 'rgba(255,255,255,0.8)' }}>실행 전략</Text>
                    <Title level={4} style={{ color: 'white', margin: 0 }}>
                      {strategy.name} ({strategy.type})
                    </Title>
                  </div>
                  <div>
                    <Text style={{ color: 'rgba(255,255,255,0.8)' }}>거래 모드</Text>
                    <Title level={4} style={{ color: 'white', margin: 0 }}>
                      {trading.mode === 'paper' ? '📝 페이퍼 트레이딩' : '💰 실거래'}
                    </Title>
                  </div>
                </Space>
              </Col>
              <Col>
                <Button 
                  danger 
                  icon={<StopOutlined />} 
                  size="large"
                  onClick={() => {
                    // AI 전략 중지 로직 (추후 구현)
                    console.log('AI 전략 중지');
                  }}
                >
                  전략 중지
                </Button>
              </Col>
            </Row>
          </Card>

          {/* 실시간 수익/손실 (AI Strategy) */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="초기 자본"
                  value={trading.initial_capital}
                  precision={0}
                  prefix={<DollarOutlined />}
                  suffix="원"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="💰 총 자산"
                  value={trading.total_assets || trading.current_capital}
                  precision={0}
                  prefix={<DollarOutlined />}
                  suffix="원"
                />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  현금: {trading.current_capital?.toLocaleString()}원 + 
                  코인: {trading.portfolio_value?.toLocaleString() || 0}원
                </Text>
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="총 손익"
                  value={trading.total_return}
                  precision={0}
                  valueStyle={{ color: isProfitable ? '#3f8600' : '#cf1322' }}
                  prefix={isProfitable ? <RiseOutlined /> : <FallOutlined />}
                  suffix="원"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="수익률"
                  value={pnlPercentage}
                  precision={2}
                  valueStyle={{ color: isProfitable ? '#3f8600' : '#cf1322' }}
                  prefix={isProfitable ? <RiseOutlined /> : <FallOutlined />}
                  suffix="%"
                />
              </Card>
            </Col>
          </Row>

          {/* 거래 통계 (AI Strategy) */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="총 거래 수"
                  value={trading.total_trades || 0}
                  prefix={<ThunderboltOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="오픈 포지션"
                  value={trading.open_positions || 0}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="최대 낙폭"
                  value={trading.max_drawdown || 0}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: '#cf1322' }}
                />
              </Card>
            </Col>
          </Row>

          {/* 현재 포지션 (AI Strategy) */}
          {aiStrategyDetails.current_positions && aiStrategyDetails.current_positions.length > 0 && (
            <Card title="현재 포지션">
              <Table
                dataSource={aiStrategyDetails.current_positions}
                columns={[
                  {
                    title: '코인',
                    dataIndex: 'symbol',
                    key: 'symbol',
                    render: (symbol) => <Tag color="blue">{symbol}</Tag>
                  },
                  {
                    title: '보유량',
                    dataIndex: 'amount',
                    key: 'amount',
                    render: (amount) => amount.toFixed(6)
                  },
                  {
                    title: '평균 단가',
                    dataIndex: 'avg_price',
                    key: 'avg_price',
                    render: (price) => `${price.toLocaleString()}원`
                  },
                  {
                    title: '현재 가격',
                    dataIndex: 'current_price',
                    key: 'current_price',
                    render: (price) => `${price.toLocaleString()}원`
                  },
                  {
                    title: '미실현 손익',
                    dataIndex: 'unrealized_pnl',
                    key: 'unrealized_pnl',
                    render: (pnl) => (
                      <span style={{ color: pnl > 0 ? '#52c41a' : '#ff4d4f' }}>
                        {pnl > 0 ? '+' : ''}{pnl.toLocaleString()}원
                      </span>
                    )
                  }
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          )}

          {/* 수익 차트 (AI Strategy) */}
          {pnlHistory.length > 0 && (
            <Card title="실시간 수익 추이">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={pnlHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value) => `${value.toLocaleString()}원`}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="pnl" 
                    stroke={isProfitable ? '#52c41a' : '#ff4d4f'}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* 현재 포지션 (AI Strategy) */}
          <Card 
            title={
              <Space>
                <ThunderboltOutlined />
                <span>현재 포지션</span>
                <Badge count={aiStrategyDetails.current_positions?.length || 0} />
              </Space>
            }
          >
            {(!aiStrategyDetails.current_positions || aiStrategyDetails.current_positions.length === 0) ? (
              <Empty description="보유 중인 포지션이 없습니다" />
            ) : (
              <Row gutter={[16, 16]}>
                {aiStrategyDetails.current_positions.map((position, index) => {
                  const unrealizedPnl = position.unrealized_pnl || 0;
                  const isProfitPosition = unrealizedPnl > 0;
                  return (
                    <Col xs={24} sm={12} lg={8} key={position.symbol}>
                      <div className="position-card">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Space>
                            <Tag color="blue" style={{ fontSize: '16px' }}>{position.symbol}</Tag>
                            <Tag color="green">롱</Tag>
                          </Space>
                          <Descriptions size="small" column={1}>
                            <Descriptions.Item label="수량">
                              {position.amount?.toFixed(8)}
                            </Descriptions.Item>
                            <Descriptions.Item label="평균가">
                              {position.avg_price?.toLocaleString()}원
                            </Descriptions.Item>
                            {position.current_price && (
                              <Descriptions.Item label="현재가">
                                {position.current_price?.toLocaleString()}원
                              </Descriptions.Item>
                            )}
                            <Descriptions.Item label="미실현 손익">
                              <Text className={isProfitPosition ? 'pnl-positive' : 'pnl-negative'}>
                                {unrealizedPnl > 0 ? '+' : ''}{unrealizedPnl.toLocaleString()}원
                              </Text>
                            </Descriptions.Item>
                          </Descriptions>
                        </Space>
                      </div>
                    </Col>
                  );
                })}
              </Row>
            )}
          </Card>

          {/* 실시간 분석 현황 (AI Strategy) */}
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>실시간 시장 분석</span>
                <Badge count={traditionalStrategies.length} style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#fff7e6', borderLeft: '4px solid #fa8c16' }}>
                  <Space direction="vertical">
                    <Space>
                      <FireOutlined style={{ color: '#fa8c16', fontSize: 20 }} />
                      <Text strong>Tier 1: 거래량 급등</Text>
                    </Space>
                    <Text type="secondary">고거래량 코인 모니터링</Text>
                    <Text style={{ fontSize: '18px', fontWeight: 'bold', color: '#fa8c16' }}>
                      {traditionalStrategies.length}개 코인 분석 중
                    </Text>
                  </Space>
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a' }}>
                  <Space direction="vertical">
                    <Space>
                      <RiseOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                      <Text strong>매수 신호</Text>
                    </Space>
                    <Text type="secondary">기술적 분석 기반</Text>
                    <Text style={{ fontSize: '18px', fontWeight: 'bold', color: '#52c41a' }}>
                      {aiStrategyDetails.current_positions?.length || 0}개 포지션
                    </Text>
                  </Space>
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#fff1f0', borderLeft: '4px solid #ff4d4f' }}>
                  <Space direction="vertical">
                    <Space>
                      <FallOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
                      <Text strong>매도 신호</Text>
                    </Space>
                    <Text type="secondary">리스크 관리</Text>
                    <Text style={{ fontSize: '18px', fontWeight: 'bold', color: '#ff4d4f' }}>
                      {trading.max_drawdown || 0}% 최대 낙폭
                    </Text>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 최근 거래 내역 (AI Strategy) */}
          {aiStrategyDetails.recent_trades && aiStrategyDetails.recent_trades.length > 0 && (
            <Card title="최근 거래 내역">
              <Table
                dataSource={aiStrategyDetails.recent_trades}
                columns={[
                  {
                    title: '시간',
                    dataIndex: 'timestamp',
                    key: 'timestamp',
                    render: (timestamp) => new Date(timestamp).toLocaleString()
                  },
                  {
                    title: '코인',
                    dataIndex: 'symbol',
                    key: 'symbol',
                    render: (symbol) => <Tag color="blue">{symbol}</Tag>
                  },
                  {
                    title: '거래 유형',
                    dataIndex: 'side',
                    key: 'side',
                    render: (side) => (
                      <Tag color={side === 'buy' ? 'green' : 'red'}>
                        {side === 'buy' ? '매수' : '매도'}
                      </Tag>
                    )
                  },
                  {
                    title: '수량',
                    dataIndex: 'amount',
                    key: 'amount',
                    render: (amount) => amount.toFixed(6)
                  },
                  {
                    title: '가격',
                    dataIndex: 'price',
                    key: 'price',
                    render: (price) => `${price.toLocaleString()}원`
                  },
                  {
                    title: '손익',
                    dataIndex: 'net_profit',
                    key: 'net_profit',
                    render: (profit) => (
                      <span style={{ color: profit > 0 ? '#52c41a' : '#ff4d4f' }}>
                        {profit > 0 ? '+' : ''}{profit.toLocaleString()}원
                      </span>
                    )
                  },
                  {
                    title: '상태',
                    dataIndex: 'status',
                    key: 'status',
                    render: (status) => {
                      const statusConfig = {
                        filled: { color: 'success', text: '체결' },
                        pending: { color: 'processing', text: '대기' },
                        cancelled: { color: 'default', text: '취소' },
                        error: { color: 'error', text: '오류' }
                      };
                      const config = statusConfig[status] || statusConfig.pending;
                      return <Tag color={config.color}>{config.text}</Tag>;
                    }
                  }
                ]}
                pagination={{ pageSize: 5 }}
                size="small"
              />
            </Card>
          )}
        </Space>
      </MonitoringContainer>
    );
  }

  // 전통적 전략이 실행 중인 경우 AI 전략과 동일한 모니터링 화면 표시
  if (traditionalStrategyDetails && traditionalStrategyDetails.is_trading) {
    const { strategy, trading } = traditionalStrategyDetails;
    const pnlPercentage = trading.pnl_percentage || 0;
    const isProfitable = pnlPercentage > 0;

    return (
      <MonitoringContainer>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* 거래 상태 헤더 */}
          <Card className="trading-card">
            <Row gutter={24} align="middle">
              <Col flex="auto">
                <Space size="large">
                  <Badge status="processing" text={
                    <Text style={{ color: 'white', fontSize: '16px' }}>
                      <PlayCircleOutlined /> 전통적 전략 실행 중
                    </Text>
                  } />
                  <div>
                    <Text style={{ color: 'rgba(255,255,255,0.8)' }}>실행 전략</Text>
                    <Title level={4} style={{ color: 'white', margin: 0 }}>
                      {strategy.name} ({strategy.type})
                    </Title>
                  </div>
                  <div>
                    <Text style={{ color: 'rgba(255,255,255,0.8)' }}>거래 모드</Text>
                    <Title level={4} style={{ color: 'white', margin: 0 }}>
                      {trading.mode === 'paper' ? '📝 페이퍼 트레이딩' : '💰 실거래'}
                    </Title>
                  </div>
                </Space>
              </Col>
              <Col>
                <Button 
                  danger 
                  icon={<StopOutlined />} 
                  size="large"
                  onClick={() => {
                    // 전통적 전략 중지 로직 (추후 구현)
                    console.log('전통적 전략 중지');
                  }}
                >
                  전략 중지
                </Button>
              </Col>
            </Row>
          </Card>

          {/* 실시간 수익/손실 */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="초기 자본"
                  value={trading.initial_capital}
                  precision={0}
                  prefix={<DollarOutlined />}
                  suffix="원"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="💰 총 자산"
                  value={trading.total_assets || trading.current_capital}
                  precision={0}
                  prefix={<DollarOutlined />}
                  suffix="원"
                />
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  현금: {trading.current_capital?.toLocaleString()}원 + 
                  코인: {trading.portfolio_value?.toLocaleString() || 0}원
                </Text>
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="총 손익"
                  value={trading.total_return}
                  precision={0}
                  valueStyle={{ color: isProfitable ? '#3f8600' : '#cf1322' }}
                  prefix={isProfitable ? <RiseOutlined /> : <FallOutlined />}
                  suffix="원"
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card>
                <Statistic
                  title="수익률"
                  value={pnlPercentage}
                  precision={2}
                  valueStyle={{ color: isProfitable ? '#3f8600' : '#cf1322' }}
                  prefix={isProfitable ? <RiseOutlined /> : <FallOutlined />}
                  suffix="%"
                />
              </Card>
            </Col>
          </Row>

          {/* 거래 통계 */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="총 거래 수"
                  value={trading.total_trades || 0}
                  prefix={<ThunderboltOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="오픈 포지션"
                  value={trading.open_positions || 0}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="최대 낙폭"
                  value={trading.max_drawdown || 0}
                  precision={2}
                  suffix="%"
                  valueStyle={{ color: '#cf1322' }}
                />
              </Card>
            </Col>
          </Row>

          {/* 현재 포지션 */}
          {traditionalStrategyDetails.current_positions && traditionalStrategyDetails.current_positions.length > 0 && (
            <Card title="현재 포지션">
              <Table
                dataSource={traditionalStrategyDetails.current_positions}
                columns={[
                  {
                    title: '코인',
                    dataIndex: 'symbol',
                    key: 'symbol',
                    render: (symbol) => <Tag color="blue">{symbol}</Tag>
                  },
                  {
                    title: '보유량',
                    dataIndex: 'amount',
                    key: 'amount',
                    render: (amount) => amount.toFixed(6)
                  },
                  {
                    title: '평균 단가',
                    dataIndex: 'avg_price',
                    key: 'avg_price',
                    render: (price) => `${price.toLocaleString()}원`
                  },
                  {
                    title: '현재 가격',
                    dataIndex: 'current_price',
                    key: 'current_price',
                    render: (price) => `${price.toLocaleString()}원`
                  },
                  {
                    title: '미실현 손익',
                    dataIndex: 'unrealized_pnl',
                    key: 'unrealized_pnl',
                    render: (pnl) => (
                      <span style={{ color: pnl > 0 ? '#52c41a' : '#ff4d4f' }}>
                        {pnl > 0 ? '+' : ''}{pnl.toLocaleString()}원
                      </span>
                    )
                  }
                ]}
                pagination={false}
                size="small"
              />
            </Card>
          )}

          {/* 수익 차트 (Traditional Strategy) */}
          {pnlHistory.length > 0 && (
            <Card title="실시간 수익 추이">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={pnlHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value) => `${value.toLocaleString()}원`}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="pnl" 
                    stroke={isProfitable ? '#52c41a' : '#ff4d4f'}
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* 현재 포지션 (Traditional Strategy) */}
          <Card 
            title={
              <Space>
                <ThunderboltOutlined />
                <span>현재 포지션</span>
                <Badge count={traditionalStrategyDetails.current_positions?.length || 0} />
              </Space>
            }
          >
            {(!traditionalStrategyDetails.current_positions || traditionalStrategyDetails.current_positions.length === 0) ? (
              <Empty description="보유 중인 포지션이 없습니다" />
            ) : (
              <Row gutter={[16, 16]}>
                {traditionalStrategyDetails.current_positions.map((position, index) => {
                  const unrealizedPnl = position.unrealized_pnl || 0;
                  const isProfitPosition = unrealizedPnl > 0;
                  return (
                    <Col xs={24} sm={12} lg={8} key={position.symbol}>
                      <div className="position-card">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Space>
                            <Tag color="blue" style={{ fontSize: '16px' }}>{position.symbol}</Tag>
                            <Tag color="green">롱</Tag>
                          </Space>
                          <Descriptions size="small" column={1}>
                            <Descriptions.Item label="수량">
                              {position.amount?.toFixed(8)}
                            </Descriptions.Item>
                            <Descriptions.Item label="평균가">
                              {position.avg_price?.toLocaleString()}원
                            </Descriptions.Item>
                            {position.current_price && (
                              <Descriptions.Item label="현재가">
                                {position.current_price?.toLocaleString()}원
                              </Descriptions.Item>
                            )}
                            <Descriptions.Item label="미실현 손익">
                              <Text className={isProfitPosition ? 'pnl-positive' : 'pnl-negative'}>
                                {unrealizedPnl > 0 ? '+' : ''}{unrealizedPnl.toLocaleString()}원
                              </Text>
                            </Descriptions.Item>
                          </Descriptions>
                        </Space>
                      </div>
                    </Col>
                  );
                })}
              </Row>
            )}
          </Card>

          {/* 실시간 분석 현황 (Traditional Strategy) */}
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>실시간 시장 분석</span>
                <Badge count={traditionalStrategies.length} style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#fff7e6', borderLeft: '4px solid #fa8c16' }}>
                  <Space direction="vertical">
                    <Space>
                      <FireOutlined style={{ color: '#fa8c16', fontSize: 20 }} />
                      <Text strong>Tier 1: 거래량 급등</Text>
                    </Space>
                    <Text type="secondary">고거래량 코인 모니터링</Text>
                    <Text style={{ fontSize: '18px', fontWeight: 'bold', color: '#fa8c16' }}>
                      {traditionalStrategies.length}개 코인 분석 중
                    </Text>
                  </Space>
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a' }}>
                  <Space direction="vertical">
                    <Space>
                      <RiseOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                      <Text strong>매수 신호</Text>
                    </Space>
                    <Text type="secondary">기술적 분석 기반</Text>
                    <Text style={{ fontSize: '18px', fontWeight: 'bold', color: '#52c41a' }}>
                      {traditionalStrategyDetails.current_positions?.length || 0}개 포지션
                    </Text>
                  </Space>
                </Card>
              </Col>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#fff1f0', borderLeft: '4px solid #ff4d4f' }}>
                  <Space direction="vertical">
                    <Space>
                      <FallOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />
                      <Text strong>매도 신호</Text>
                    </Space>
                    <Text type="secondary">리스크 관리</Text>
                    <Text style={{ fontSize: '18px', fontWeight: 'bold', color: '#ff4d4f' }}>
                      {trading.max_drawdown || 0}% 최대 낙폭
                    </Text>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>

          {/* 최근 거래 내역 (Traditional Strategy) */}
          {traditionalStrategyDetails.recent_trades && traditionalStrategyDetails.recent_trades.length > 0 && (
            <Card title="최근 거래 내역">
              <Table
                dataSource={traditionalStrategyDetails.recent_trades}
                columns={[
                  {
                    title: '시간',
                    dataIndex: 'timestamp',
                    key: 'timestamp',
                    render: (timestamp) => new Date(timestamp).toLocaleString()
                  },
                  {
                    title: '코인',
                    dataIndex: 'symbol',
                    key: 'symbol',
                    render: (symbol) => <Tag color="blue">{symbol}</Tag>
                  },
                  {
                    title: '거래 유형',
                    dataIndex: 'side',
                    key: 'side',
                    render: (side) => (
                      <Tag color={side === 'buy' ? 'green' : 'red'}>
                        {side === 'buy' ? '매수' : '매도'}
                      </Tag>
                    )
                  },
                  {
                    title: '수량',
                    dataIndex: 'amount',
                    key: 'amount',
                    render: (amount) => amount.toFixed(6)
                  },
                  {
                    title: '가격',
                    dataIndex: 'price',
                    key: 'price',
                    render: (price) => `${price.toLocaleString()}원`
                  },
                  {
                    title: '손익',
                    dataIndex: 'net_profit',
                    key: 'net_profit',
                    render: (profit) => (
                      <span style={{ color: profit > 0 ? '#52c41a' : '#ff4d4f' }}>
                        {profit > 0 ? '+' : ''}{profit.toLocaleString()}원
                      </span>
                    )
                  },
                  {
                    title: '상태',
                    dataIndex: 'status',
                    key: 'status',
                    render: (status) => {
                      const statusConfig = {
                        filled: { color: 'success', text: '체결' },
                        pending: { color: 'processing', text: '대기' },
                        cancelled: { color: 'default', text: '취소' },
                        error: { color: 'error', text: '오류' }
                      };
                      const config = statusConfig[status] || statusConfig.pending;
                      return <Tag color={config.color}>{config.text}</Tag>;
                    }
                  }
                ]}
                pagination={{ pageSize: 5 }}
                size="small"
              />
            </Card>
          )}
        </Space>
      </MonitoringContainer>
    );
  }

  if ((!tradingStatus || !tradingStatus.is_trading) && (!aiStrategyDetails || !aiStrategyDetails.is_trading) && (!traditionalStrategyDetails || !traditionalStrategyDetails.is_trading)) {
    return (
      <MonitoringContainer>
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                현재 실행 중인 거래가 없습니다<br />
                <Text type="secondary">
                  AI 추천 또는 전통적 전략 페이지에서 전략을 선택하여 거래를 시작하세요
                </Text>
              </span>
            }
          >
            <Space>
            <Button type="primary" href="/ai-recommendation">
              AI 추천 보러가기
            </Button>
              <Button href="/traditional-strategies">
                전통적 전략 보러가기
              </Button>
            </Space>
          </Empty>
        </Card>
      </MonitoringContainer>
    );
  }

  const { strategy, trading } = tradingStatus;
  const pnlPercentage = trading.pnl_percentage || 0;
  const isProfitable = pnlPercentage > 0;

  return (
    <MonitoringContainer>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 거래 상태 헤더 */}
        <Card className="trading-card">
          <Row gutter={24} align="middle">
            <Col flex="auto">
              <Space size="large">
                <Badge status="processing" text={
                  <Text style={{ color: 'white', fontSize: '16px' }}>
                    <PlayCircleOutlined /> 거래 실행 중
                  </Text>
                } />
                <div>
                  <Text style={{ color: 'rgba(255,255,255,0.8)' }}>실행 전략</Text>
                  <Title level={4} style={{ color: 'white', margin: 0 }}>
                    {strategy.name} ({strategy.type})
                  </Title>
                </div>
                <div>
                  <Text style={{ color: 'rgba(255,255,255,0.8)' }}>거래 모드</Text>
                  <Title level={4} style={{ color: 'white', margin: 0 }}>
                    {trading.mode === 'paper' ? '📝 페이퍼 트레이딩' : '💰 실거래'}
                  </Title>
                </div>
              </Space>
            </Col>
            <Col>
              <Button 
                danger 
                icon={<StopOutlined />} 
                size="large"
                onClick={handleStopTrading}
              >
                거래 중지
              </Button>
            </Col>
          </Row>
        </Card>

        {/* 실시간 수익/손실 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="초기 자본"
                value={trading.initial_capital}
                precision={0}
                prefix={<DollarOutlined />}
                suffix="원"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="💰 총 자산"
                value={trading.total_assets || trading.current_capital}
                precision={0}
                prefix={<DollarOutlined />}
                suffix="원"
              />
              <Text type="secondary" style={{ fontSize: '12px' }}>
                현금: {trading.current_capital?.toLocaleString()}원 + 
                코인: {trading.portfolio_value?.toLocaleString() || 0}원
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="총 손익"
                value={trading.total_pnl}
                precision={0}
                valueStyle={{ color: isProfitable ? '#3f8600' : '#cf1322' }}
                prefix={isProfitable ? <RiseOutlined /> : <FallOutlined />}
                suffix="원"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="수익률"
                value={pnlPercentage}
                precision={2}
                valueStyle={{ color: isProfitable ? '#3f8600' : '#cf1322' }}
                prefix={isProfitable ? <RiseOutlined /> : <FallOutlined />}
                suffix="%"
              />
            </Card>
          </Col>
        </Row>

        {/* 수익 차트 */}
        {pnlHistory.length > 0 && (
          <Card title="실시간 수익 추이">
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={pnlHistory}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip 
                  formatter={(value) => `${value.toLocaleString()}원`}
                />
                <Line 
                  type="monotone" 
                  dataKey="pnl" 
                  stroke={isProfitable ? '#52c41a' : '#ff4d4f'}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        )}

        {/* 현재 포지션 */}
        <Card 
          title={
            <Space>
              <ThunderboltOutlined />
              <span>현재 포지션</span>
              <Badge count={Object.keys(trading.positions || {}).length} />
            </Space>
          }
        >
          {Object.keys(trading.positions || {}).length === 0 ? (
            <Empty description="보유 중인 포지션이 없습니다" />
          ) : (
            <Row gutter={[16, 16]}>
              {Object.entries(trading.positions).map(([symbol, position], index) => {
                const unrealizedPnl = position.unrealized_pnl || 0;
                const isProfitPosition = unrealizedPnl > 0;
                return (
                  <Col xs={24} sm={12} lg={8} key={symbol}>
                    <div className="position-card">
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Space>
                          <Tag color="blue" style={{ fontSize: '16px' }}>{symbol}</Tag>
                          <Tag color="green">{position.side === 'long' ? '롱' : '숏'}</Tag>
                        </Space>
                        <Descriptions size="small" column={1}>
                          <Descriptions.Item label="수량">
                            {position.amount?.toFixed(8)}
                          </Descriptions.Item>
                          <Descriptions.Item label="평균가">
                            {position.avg_price?.toLocaleString()}원
                          </Descriptions.Item>
                          {position.current_price && (
                            <Descriptions.Item label="현재가">
                              {position.current_price?.toLocaleString()}원
                            </Descriptions.Item>
                          )}
                          <Descriptions.Item label="미실현 손익">
                            <Text className={isProfitPosition ? 'pnl-positive' : 'pnl-negative'}>
                              {unrealizedPnl > 0 ? '+' : ''}{unrealizedPnl.toLocaleString()}원
                            </Text>
                          </Descriptions.Item>
                        </Descriptions>
                      </Space>
                    </div>
                  </Col>
                );
              })}
            </Row>
          )}
        </Card>

        {/* 실시간 분석 현황 */}
        {tradingStatus.analysis && (
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>실시간 시장 분석</span>
                <Badge count={tradingStatus.analysis.scanning_coins} style={{ backgroundColor: '#52c41a' }} />
              </Space>
            }
          >
            <Row gutter={[16, 16]}>
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#fff7e6', borderLeft: '4px solid #fa8c16' }}>
                  <Space direction="vertical">
                    <Space>
                      <FireOutlined style={{ color: '#fa8c16', fontSize: 20 }} />
                      <Text strong>Tier 1: 거래량 급등</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus.analysis.tiers.tier1.count}개
                    </Title>
                    <Text type="secondary">1초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus.analysis.tiers.tier1.coins.slice(0, 5).map(coin => (
                        <Tag key={coin} color="orange">{coin}</Tag>
                      ))}
                      {tradingStatus.analysis.tiers.tier1.coins.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#f6ffed', borderLeft: '4px solid #52c41a' }}>
                  <Space direction="vertical">
                    <Space>
                      <CrownOutlined style={{ color: '#52c41a', fontSize: 20 }} />
                      <Text strong>Tier 2: 핵심 코인</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus.analysis.tiers.tier2.count}개
                    </Title>
                    <Text type="secondary">5초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus.analysis.tiers.tier2.coins.slice(0, 5).map(coin => (
                        <Tag key={coin} color="green">{coin}</Tag>
                      ))}
                      {tradingStatus.analysis.tiers.tier2.coins.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#e6f7ff', borderLeft: '4px solid #1890ff' }}>
                  <Space direction="vertical">
                    <Space>
                      <TrophyOutlined style={{ color: '#1890ff', fontSize: 20 }} />
                      <Text strong>Tier 3: 시총 상위</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus.analysis.tiers.tier3.count}개
                    </Title>
                    <Text type="secondary">30초마다 스캔</Text>
                  </Space>
                </Card>
              </Col>
            </Row>

            {/* 상위 거래 기회 */}
            <Card 
              title="발견된 거래 기회 (실시간)" 
              style={{ marginTop: 16 }}
              size="small"
            >
              <Table
                dataSource={tradingStatus.analysis.top_opportunities}
                size="small"
                pagination={false}
                scroll={{ y: 300 }}
                columns={[
                  {
                    title: 'Tier',
                    dataIndex: 'tier',
                    key: 'tier',
                    width: 60,
                    render: (tier) => {
                      const config = {
                        1: { color: 'orange', icon: <FireOutlined /> },
                        2: { color: 'green', icon: <CrownOutlined /> },
                        3: { color: 'blue', icon: <TrophyOutlined /> }
                      };
                      return <Tag color={config[tier]?.color} icon={config[tier]?.icon}>T{tier}</Tag>;
                    }
                  },
                  {
                    title: '코인',
                    dataIndex: 'symbol',
                    key: 'symbol',
                    render: (symbol) => <Text strong>{symbol}</Text>
                  },
                  {
                    title: '신호',
                    dataIndex: 'signal',
                    key: 'signal',
                    render: (signal) => (
                      <Tag color={signal === 'BUY' ? 'green' : 'red'}>
                        {signal === 'BUY' ? '매수' : '매도'}
                      </Tag>
                    )
                  },
                  {
                    title: '신뢰도',
                    dataIndex: 'confidence',
                    key: 'confidence',
                    render: (conf) => (
                      <Progress 
                        percent={Math.round(conf * 100)} 
                        size="small"
                        strokeColor={conf > 0.7 ? '#52c41a' : '#faad14'}
                      />
                    )
                  },
                  {
                    title: '강도',
                    dataIndex: 'strength',
                    key: 'strength',
                    render: (str) => <Text>{(str * 100).toFixed(0)}%</Text>
                  },
                  {
                    title: '가격',
                    dataIndex: 'price',
                    key: 'price',
                    render: (price) => price ? `${price.toLocaleString()}원` : '-'
                  }
                ]}
              />
            </Card>
          </Card>
        )}

        {/* 거래 통계 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card title="거래 통계">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text>총 거래 수</Text>
                  <Title level={3}>{trading.total_trades || 0}건</Title>
                </div>
                <div>
                  <Text type="secondary">총 수수료</Text>
                  <Text strong style={{ display: 'block', fontSize: '18px', color: '#ff4d4f' }}>
                    -{(trading.total_commission || 0).toLocaleString()}원
                  </Text>
                </div>
                <Progress 
                  percent={100} 
                  status="active"
                  strokeColor={{
                    '0%': '#108ee9',
                    '100%': '#87d068',
                  }}
                />
              </Space>
            </Card>
          </Col>
          
          <Col xs={24} md={12}>
            <Card title="리스크 지표">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text>포지션 비율</Text>
                  <Progress 
                    percent={Math.min(Object.keys(trading.positions || {}).length * 20, 100)} 
                    status={Object.keys(trading.positions || {}).length > 3 ? 'exception' : 'normal'}
                  />
                </div>
                <div>
                  <Text>자본 활용률</Text>
                  <Progress 
                    percent={Math.min((trading.current_capital / trading.initial_capital) * 100, 100)} 
                    strokeColor={isProfitable ? '#52c41a' : '#ff4d4f'}
                  />
                </div>
              </Space>
            </Card>
          </Col>
        </Row>

        {/* 거래 내역 */}
        <Card 
          title="실시간 거래 내역"
          extra={
            <Badge status={isConnected ? 'processing' : 'default'} 
              text={isConnected ? '실시간 연결' : '연결 끊김'} 
            />
          }
        >
          <Table
            dataSource={trading.trades || []}
            columns={tradesColumns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
            locale={{ emptyText: '거래 내역이 없습니다' }}
          />
        </Card>

        {/* 전략 정보 */}
        <Card title="전략 정보">
          <Descriptions bordered column={2}>
            <Descriptions.Item label="전략 ID">{strategy.id}</Descriptions.Item>
            <Descriptions.Item label="전략 타입">
              <Tag color="purple">{strategy.type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="시작 시간" span={2}>
              {new Date(strategy.started_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="거래 모드">
              {trading.mode === 'paper' ? (
                <Tag color="blue">페이퍼 트레이딩 (모의)</Tag>
              ) : (
                <Tag color="red">실거래</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="실행 상태">
              <Badge status="processing" text="실행 중" />
            </Descriptions.Item>
          </Descriptions>
        </Card>
      </Space>
    </MonitoringContainer>
  );
};

export default Monitoring;
