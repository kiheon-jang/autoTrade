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
  Alert,
  Badge,
  Descriptions,
  Empty
} from 'antd';
import { 
  ThunderboltOutlined,
  DollarOutlined,
  RiseOutlined,
  FallOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlayCircleOutlined,
  StopOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { aiRecommendationAPI } from '../services/api';
import { useWebSocket } from '../hooks/useWebSocket';

const { Title, Text } = Typography;

const MonitoringContainer = styled.div`
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
  const [loading, setLoading] = useState(true);
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
          return [...prev.slice(-20), newEntry]; // 최근 20개만 유지
        });
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

  if (!tradingStatus || !tradingStatus.is_trading) {
    return (
      <MonitoringContainer>
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <span>
                현재 실행 중인 거래가 없습니다<br />
                <Text type="secondary">AI 추천 페이지에서 전략을 선택하여 거래를 시작하세요</Text>
              </span>
            }
          >
            <Button type="primary" href="/ai-recommendation">
              AI 추천 보러가기
            </Button>
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
                title="현재 자본"
                value={trading.current_capital}
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
              {Object.entries(trading.positions).map(([symbol, position]) => (
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
                      </Descriptions>
                    </Space>
                  </div>
                </Col>
              ))}
            </Row>
          )}
        </Card>

        {/* 거래 통계 */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card title="거래 통계">
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text>총 거래 수</Text>
                  <Title level={3}>{trading.total_trades || 0}건</Title>
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
            dataSource={[]} // 실제로는 거래 내역 데이터를 넣어야 함
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
