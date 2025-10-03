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
import { useWebSocket } from '../hooks/useWebSocket';

// API 기본 URL 가져오기
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8008';

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
  const [pnlHistory, setPnlHistory] = useState([
    { time: '09:00', pnl: 0 },
    { time: '09:30', pnl: 150 },
    { time: '10:00', pnl: -200 },
    { time: '10:30', pnl: 300 },
    { time: '11:00', pnl: 100 },
    { time: '11:30', pnl: -150 },
    { time: '12:00', pnl: 250 },
    { time: '12:30', pnl: 400 },
    { time: '13:00', pnl: 200 },
    { time: '13:30', pnl: -100 },
    { time: '14:00', pnl: 350 },
    { time: '14:30', pnl: 500 },
    { time: '15:00', pnl: 300 },
    { time: '15:30', pnl: 150 },
    { time: '16:00', pnl: 200 },
    { time: '16:30', pnl: -50 },
    { time: '17:00', pnl: 100 },
    { time: '17:30', pnl: 250 },
    { time: '18:00', pnl: 400 },
    { time: '18:30', pnl: 300 },
    { time: '19:00', pnl: 200 },
    { time: '19:30', pnl: 150 },
    { time: '20:00', pnl: 100 },
    { time: '20:30', pnl: 50 },
    { time: '21:00', pnl: -100 },
    { time: '21:21', pnl: -443 }
  ]);
  const [loading, setLoading] = useState(true);
  const [analysisLog, setAnalysisLog] = useState([]);
  const [aiStrategyDetails, setAiStrategyDetails] = useState(null);
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
        if (response.total_return !== undefined) {
          setPnlHistory(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            pnl: response.total_return
          }].slice(-20)); // 최근 20개만 유지
        }
        
        // 분석 로그 업데이트 (상위 기회들)
        if (response.analysis && response.analysis.top_opportunities) {
          const topOpps = response.analysis.top_opportunities.slice(0, 10);
          const logEntry = {
            timestamp: new Date().toLocaleTimeString(),
            opportunities: topOpps.map(opp => `${opp.symbol}: ${opp.signal}`).join(', ')
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
        ...data
    }));
  };

  const handleStopTrading = async () => {
    try {
      await aiRecommendationAPI.stopTrading();
      setTradingStatus(null);
    } catch (error) {
      console.error('거래 중지 실패:', error);
    }
  };

  const formatTradeSide = (side) => (
    <Tag color={side === 'buy' ? 'green' : 'red'}>
      {side === 'buy' ? '매수' : '매도'}
    </Tag>
  );

  const formatTradeStatus = (status) => {
    const statusConfig = {
      pending: { color: 'processing', text: '대기' },
      filled: { color: 'success', text: '체결' },
      cancelled: { color: 'default', text: '취소' },
      error: { color: 'error', text: '오류' }
    };
    const config = statusConfig[status] || statusConfig.pending;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // AI 추천 전략 상세 정보 조회
  useEffect(() => {
    const fetchAiStrategy = async () => {
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
    };
    
    fetchAiStrategy();
    const interval = setInterval(fetchAiStrategy, 5000); // 5초마다 업데이트
    return () => clearInterval(interval);
  }, []);

  // AI 추천 전략이 실행 중인 경우 상세 모니터링 화면 표시
  if (aiStrategyDetails && aiStrategyDetails.is_trading) {
    const { strategy, trading } = aiStrategyDetails;
    const pnlPercentage = trading.pnl_percentage || 0;
    const isProfitable = trading.total_return >= 0;

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
                      <PlayCircleOutlined /> AI 전략 실행 중
                    </Text>
                  } />
                  <div>
                    <Text style={{ color: 'rgba(255,255,255,0.8)' }}>실행 전략</Text>
                    <br />
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
                    handleStopTrading();
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
                    render: (symbol) => (
                      <Space>
                        <CrownOutlined />
                        <Text strong>{symbol}</Text>
                      </Space>
                    )
                  },
                  {
                    title: '수량',
                    dataIndex: 'amount',
                    key: 'amount',
                    render: (amount) => amount?.toFixed(8)
                  },
                  {
                    title: '평균가',
                    dataIndex: 'avg_price',
                    key: 'avg_price',
                    render: (price) => `${price?.toLocaleString()}원`
                  },
                  {
                    title: '미실현 손익',
                    dataIndex: 'unrealized_pnl',
                    key: 'unrealized_pnl',
                    render: (pnl) => (
                      <Text style={{ color: pnl >= 0 ? '#52c41a' : '#ff4d4f' }}>
                        {pnl?.toLocaleString()}원
                      </Text>
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
              <ResponsiveContainer width="100%" height={300}>
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


          {/* 실시간 분석 현황 (AI Strategy) */}
          <Card 
            title={
              <Space>
                <SearchOutlined spin />
                <span>실시간 시장 분석</span>
                <Badge count={tradingStatus?.analysis?.scanning_coins || 99} style={{ backgroundColor: '#52c41a' }} />
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
                      {tradingStatus?.analysis?.tiers?.tier1?.count || 0}개
                    </Title>
                    <Text type="secondary">1초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier1?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="orange">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier1?.coins?.length > 5 && <Text type="secondary">...</Text>}
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
                      {tradingStatus?.analysis?.tiers?.tier2?.count || 0}개
                    </Title>
                    <Text type="secondary">5초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus?.analysis?.tiers?.tier2?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="green">{coin}</Tag>
                      ))}
                      {tradingStatus?.analysis?.tiers?.tier2?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#e6f7ff', borderLeft: '4px solid #1890ff' }}>
                  <Space direction="vertical">
                    <Space>
                      <TrophyOutlined style={{ color: '#1890ff', fontSize: 20 }} />
                      <Text strong>매수/매도 신호</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus?.analysis?.buy_signals || 0} / {tradingStatus?.analysis?.sell_signals || 0}
                    </Title>
                    <Text type="secondary">실시간 신호</Text>
                    <div style={{ marginTop: 8 }}>
                      <Tag color="green">매수 {tradingStatus?.analysis?.buy_signals || 0}</Tag>
                      <Tag color="red">매도 {tradingStatus?.analysis?.sell_signals || 0}</Tag>
                    </div>
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
                    key: 'symbol'
    },
    {
      title: '타입',
                    dataIndex: 'type',
                    key: 'type',
                    render: (type) => (
                      <Tag color={type === 'buy' ? 'green' : 'red'}>
                        {type === 'buy' ? '매수' : '매도'}
        </Tag>
                    )
    },
    {
      title: '수량',
      dataIndex: 'amount',
      key: 'amount',
                    render: (amount) => amount?.toFixed(8)
    },
    {
      title: '가격',
      dataIndex: 'price',
      key: 'price',
                    render: (price) => `${price?.toLocaleString()}원`
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (status) => {
        const statusConfig = {
                        pending: { color: 'processing', text: '대기' },
          filled: { color: 'success', text: '체결' },
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

  // 거래가 실행 중이 아닌 경우
  if ((!tradingStatus || !tradingStatus.is_trading) && (!aiStrategyDetails || !aiStrategyDetails.is_trading)) {
    return (
      <MonitoringContainer>
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                현재 실행 중인 거래가 없습니다<br />
                <Text type="secondary">
                  AI 추천 페이지에서 전략을 선택하여 거래를 시작하세요
                </Text>
              </span>
            }
          >
            <Space>
            <Button type="primary" href="/ai-recommendation">
              AI 추천 보러가기
            </Button>
            </Space>
          </Empty>
        </Card>
      </MonitoringContainer>
    );
  }

  // 기본 모니터링 화면 (기존 거래 상태)
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
                  <br />
                  <Title level={4} style={{ color: 'white', margin: 0 }}>
                    {tradingStatus?.mode === 'paper' ? '📝 페이퍼 트레이딩' : '💰 실거래'}
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
                value={tradingStatus?.initial_capital}
                precision={0}
                prefix={<DollarOutlined />}
                suffix="원"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="현재 자본"
                value={tradingStatus?.current_capital}
                precision={0}
                prefix={<DollarOutlined />}
                suffix="원"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="총 손익"
                value={tradingStatus?.total_return}
                precision={0}
                valueStyle={{ color: tradingStatus?.total_return >= 0 ? '#3f8600' : '#cf1322' }}
                prefix={tradingStatus?.total_return >= 0 ? <RiseOutlined /> : <FallOutlined />}
                suffix="원"
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="수익률"
                value={tradingStatus?.pnl_percentage}
                precision={2}
                valueStyle={{ color: tradingStatus?.pnl_percentage >= 0 ? '#3f8600' : '#cf1322' }}
                prefix={tradingStatus?.pnl_percentage >= 0 ? <RiseOutlined /> : <FallOutlined />}
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
                value={tradingStatus?.total_trades || 0}
                prefix={<ThunderboltOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card>
              <Statistic
                title="오픈 포지션"
                value={tradingStatus?.open_positions || 0}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card>
              <Statistic
                title="최대 낙폭"
                value={tradingStatus?.max_drawdown || 0}
                precision={2}
                suffix="%"
                valueStyle={{ color: '#cf1322' }}
              />
            </Card>
          </Col>
        </Row>

        {/* 현재 포지션 */}
        {tradingStatus?.positions && tradingStatus.positions.length > 0 && (
          <Card title="현재 포지션">
            <Table
              dataSource={tradingStatus.positions}
              columns={[
                {
                  title: '코인',
                  dataIndex: 'symbol',
                  key: 'symbol',
                  render: (symbol) => (
                    <Space>
                      <CrownOutlined />
                      <Text strong>{symbol}</Text>
                    </Space>
                  )
                },
                {
                  title: '수량',
                  dataIndex: 'amount',
                  key: 'amount',
                  render: (amount) => amount?.toFixed(8)
                },
                {
                  title: '평균가',
                  dataIndex: 'avg_price',
                  key: 'avg_price',
                  render: (price) => `${price?.toLocaleString()}원`
                },
                {
                  title: '미실현 손익',
                  dataIndex: 'unrealized_pnl',
                  key: 'unrealized_pnl',
                  render: (pnl) => (
                    <Text style={{ color: pnl >= 0 ? '#52c41a' : '#ff4d4f' }}>
                      {pnl?.toLocaleString()}원
                    </Text>
                  )
                }
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        )}

        {/* 수익 차트 */}
        {pnlHistory.length > 0 && (
          <Card title="실시간 수익 추이">
            <ResponsiveContainer width="100%" height={300}>
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
                  stroke={tradingStatus?.total_return >= 0 ? '#52c41a' : '#ff4d4f'}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        )}

        {/* 최근 거래 내역 */}
        {tradingStatus?.recent_trades && tradingStatus.recent_trades.length > 0 && (
          <Card title="최근 거래 내역">
            <Table
              dataSource={tradingStatus.recent_trades}
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
                  key: 'symbol'
                },
                {
                  title: '타입',
                  dataIndex: 'side',
                  key: 'side',
                  render: formatTradeSide
                },
                {
                  title: '수량',
                  dataIndex: 'amount',
                  key: 'amount',
                  render: (amount) => amount?.toFixed(8)
                },
                {
                  title: '가격',
                  dataIndex: 'price',
                  key: 'price',
                  render: (price) => `${price?.toLocaleString()}원`
                },
                {
                  title: '상태',
                  dataIndex: 'status',
                  key: 'status',
                  render: formatTradeStatus
                }
              ]}
              pagination={{ pageSize: 5 }}
              size="small"
            />
          </Card>
        )}

        {/* 실시간 분석 현황 */}
        {tradingStatus?.analysis && (
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
                      {tradingStatus.analysis.tiers?.tier1?.count || 0}개
                    </Title>
                    <Text type="secondary">1초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus.analysis.tiers?.tier1?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="orange">{coin}</Tag>
                      ))}
                      {tradingStatus.analysis.tiers?.tier1?.coins?.length > 5 && <Text type="secondary">...</Text>}
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
                      {tradingStatus.analysis.tiers?.tier2?.count || 0}개
                    </Title>
                    <Text type="secondary">5초마다 스캔</Text>
                    <div style={{ marginTop: 8 }}>
                      {tradingStatus.analysis.tiers?.tier2?.coins?.slice(0, 5).map(coin => (
                        <Tag key={coin} color="green">{coin}</Tag>
                      ))}
                      {tradingStatus.analysis.tiers?.tier2?.coins?.length > 5 && <Text type="secondary">...</Text>}
                    </div>
                  </Space>
                </Card>
              </Col>
              
              <Col xs={24} md={8}>
                <Card size="small" style={{ background: '#e6f7ff', borderLeft: '4px solid #1890ff' }}>
                  <Space direction="vertical">
                    <Space>
                      <TrophyOutlined style={{ color: '#1890ff', fontSize: 20 }} />
                      <Text strong>매수/매도 신호</Text>
                    </Space>
                    <Title level={4} style={{ margin: 0 }}>
                      {tradingStatus.analysis.buy_signals || 0} / {tradingStatus.analysis.sell_signals || 0}
                    </Title>
                    <Text type="secondary">실시간 신호</Text>
                    <div style={{ marginTop: 8 }}>
                      <Tag color="green">매수 {tradingStatus.analysis.buy_signals || 0}</Tag>
                      <Tag color="red">매도 {tradingStatus.analysis.sell_signals || 0}</Tag>
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>
          </Card>
        )}
      </Space>
    </MonitoringContainer>
  );
};

export default Monitoring;