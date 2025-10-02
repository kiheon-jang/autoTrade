import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Button, 
  Space, 
  Tag, 
  Modal, 
  Form, 
  Select, 
  InputNumber,
  message,
  Typography,
  Row,
  Col,
  Statistic,
  Table,
  Progress,
  Tooltip
} from 'antd';
import { 
  PlayCircleOutlined, 
  BarChartOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  SafetyOutlined,
  RiseOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import { traditionalStrategyAPI } from '../services/api';

// API 기본 URL 가져오기
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8008';

const { Title, Text } = Typography;
const { Option } = Select;

const TraditionalStrategiesContainer = styled.div`
  .strategy-card {
    margin-bottom: 16px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
    
    &:hover {
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      transform: translateY(-2px);
    }
  }
  
  .strategy-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }
  
  .strategy-name {
    font-size: 1.25rem;
    font-weight: 600;
    color: #262626;
  }
  
  .strategy-type {
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
  }
  
  .type-scalping {
    background: #e6f7ff;
    color: #1890ff;
  }
  
  .type-daytrading {
    background: #f6ffed;
    color: #52c41a;
  }
  
  .type-swing {
    background: #fff7e6;
    color: #fa8c16;
  }
  
  .type-longterm {
    background: #f9f0ff;
    color: #722ed1;
  }
  
  .return-positive {
    color: #52c41a;
  }
  
  .return-negative {
    color: #ff4d4f;
  }
  
  .risk-high {
    color: #ff4d4f;
  }
  
  .risk-medium {
    color: #fa8c16;
  }
  
  .risk-low {
    color: #52c41a;
  }
`;

const TraditionalStrategies = () => {
  const [strategies, setStrategies] = useState(() => {
    const saved = localStorage.getItem('traditionalStrategies');
    return saved ? JSON.parse(saved) : [];
  });
  const [loading, setLoading] = useState(false);
  const [selectingStrategy, setSelectingStrategy] = useState(false);
  const [analysisModalVisible, setAnalysisModalVisible] = useState(false);
  const [analysisForm] = Form.useForm();
  const [selectedStrategy, setSelectedStrategy] = useState(() => {
    return localStorage.getItem('selectedTraditionalStrategy') || null;
  });

  // strategies 상태가 변경될 때마다 localStorage에 저장
  useEffect(() => {
    if (strategies.length > 0) {
      localStorage.setItem('traditionalStrategies', JSON.stringify(strategies));
    }
  }, [strategies]);

  // selectedStrategy 상태가 변경될 때마다 localStorage에 저장
  useEffect(() => {
    if (selectedStrategy) {
      localStorage.setItem('selectedTraditionalStrategy', selectedStrategy);
    }
  }, [selectedStrategy]);

  // 컴포넌트 마운트 시 백엔드 상태 확인 및 localStorage 정리
  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/monitoring/strategy-status`);
        const data = await response.json();
        
        // 백엔드에 활성 전략이 없으면 localStorage 정리
        if (data.active_strategies === 0) {
          localStorage.removeItem('selectedTraditionalStrategy');
          setSelectedStrategy(null);
        }
      } catch (error) {
        console.error('백엔드 상태 확인 실패:', error);
        // 에러 발생 시에도 localStorage 정리
        localStorage.removeItem('selectedTraditionalStrategy');
        setSelectedStrategy(null);
      }
    };

    checkBackendStatus();
  }, []);

  const handleAnalyzeStrategies = async (values) => {
    try {
      setLoading(true);
      const response = await traditionalStrategyAPI.analyzeTraditionalStrategies({
        symbols: values.symbols || ['BTC', 'ETH', 'XRP'],
        timeframe: values.timeframe || '1h',
        period_days: values.period_days || 30,
        initial_capital: values.initial_capital || 1000000
      });
      
      setStrategies(response.strategies || []);
      setAnalysisModalVisible(false);
      analysisForm.resetFields();
      message.success('전략 분석이 완료되었습니다.');
    } catch (error) {
      message.error('전략 분석에 실패했습니다.');
      console.error('전략 분석 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectStrategy = async (strategyType, symbols = ['BTC', 'ETH', 'XRP', 'ADA', 'DOT']) => {
    try {
      setSelectingStrategy(true);
      
      // 이미 선택된 전략을 다시 클릭하면 중지
      if (selectedStrategy === strategyType) {
        const response = await traditionalStrategyAPI.stopTraditionalStrategy();
        message.success(response.message || '전략이 중지되었습니다.');
        setSelectedStrategy(null);
        return;
      }
      
      const response = await traditionalStrategyAPI.selectTraditionalStrategy(strategyType, symbols);
      message.success(`${response.strategy.name}이 전체 코인 대상으로 실행되었습니다.`);
      setSelectedStrategy(strategyType);
    } catch (error) {
      message.error('전략 선택에 실패했습니다.');
      console.error('전략 선택 실패:', error);
    } finally {
      setSelectingStrategy(false);
    }
  };

  const getStrategyTypeConfig = (type) => {
    const typeMap = {
      scalping: { color: 'blue', text: '스캘핑', className: 'type-scalping', icon: <ThunderboltOutlined /> },
      daytrading: { color: 'green', text: '데이트레이딩', className: 'type-daytrading', icon: <ClockCircleOutlined /> },
      swing: { color: 'orange', text: '스윙트레이딩', className: 'type-swing', icon: <RiseOutlined /> },
      longterm: { color: 'purple', text: '롱텀', className: 'type-longterm', icon: <SafetyOutlined /> },
    };
    return typeMap[type] || { color: 'default', text: type, className: 'type-default', icon: <BarChartOutlined /> };
  };

  const getRiskLevelColor = (riskLevel) => {
    switch (riskLevel) {
      case 'high': return 'risk-high';
      case 'medium': return 'risk-medium';
      case 'low': return 'risk-low';
      default: return '';
    }
  };

  const formatPercentage = (value) => {
    if (value > 0) return <span className="return-positive">+{value.toFixed(2)}%</span>;
    if (value < 0) return <span className="return-negative">{value.toFixed(2)}%</span>;
    return <span>{value.toFixed(2)}%</span>;
  };

  const columns = [
    {
      title: '전략명',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
      render: (name, record) => {
        const config = getStrategyTypeConfig(record.strategy_type);
        return (
          <Space>
            {config.icon}
            <strong>{name}</strong>
            <Tag color={config.color} className={config.className}>
              {config.text}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: '총 수익률',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (value) => formatPercentage(value * 100),
      sorter: (a, b) => a.total_return - b.total_return,
    },
    {
      title: '연환산 수익률',
      dataIndex: 'annual_return',
      key: 'annual_return',
      render: (value) => formatPercentage(value * 100),
      sorter: (a, b) => a.annual_return - b.annual_return,
    },
    {
      title: '승률',
      dataIndex: 'win_rate',
      key: 'win_rate',
      render: (value) => `${(value * 100).toFixed(1)}%`,
      sorter: (a, b) => a.win_rate - b.win_rate,
    },
    {
      title: '총 거래',
      dataIndex: 'total_trades',
      key: 'total_trades',
      render: (value) => value.toLocaleString(),
      sorter: (a, b) => a.total_trades - b.total_trades,
    },
    {
      title: '최대 손실',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      render: (value) => <span className="return-negative">-{value.toFixed(2)}%</span>,
      sorter: (a, b) => a.max_drawdown - b.max_drawdown,
    },
    {
      title: '리스크',
      dataIndex: 'risk_level',
      key: 'risk_level',
      render: (level) => (
        <Tag className={getRiskLevelColor(level)}>
          {level === 'high' ? '높음' : level === 'medium' ? '보통' : '낮음'}
        </Tag>
      ),
    },
    {
      title: '작업',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type={selectedStrategy === record.strategy_type ? "default" : "primary"}
            icon={selectedStrategy === record.strategy_type ? <SafetyOutlined /> : <PlayCircleOutlined />}
            loading={selectingStrategy}
            onClick={() => handleSelectStrategy(record.strategy_type)}
          >
            {selectedStrategy === record.strategy_type ? '실행 중' : (selectingStrategy ? '실행 중...' : '선택')}
          </Button>
          <Tooltip title={record.recommendation}>
            <Button 
              type="text" 
              icon={<InfoCircleOutlined />}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <TraditionalStrategiesContainer>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Title level={2}>전통적 거래 전략</Title>
          {selectedStrategy && (
            <Text type="success" style={{ fontSize: '14px' }}>
              ✓ {getStrategyTypeConfig(selectedStrategy).text} 전략이 실행 중입니다
            </Text>
          )}
        </div>
        <Button 
          type="primary" 
          icon={<BarChartOutlined />}
          onClick={() => setAnalysisModalVisible(true)}
        >
          전략 분석 실행
        </Button>
      </div>

      {/* 전략 통계 */}
      {strategies.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic 
                title="분석된 전략 수" 
                value={strategies.length} 
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic 
                title="최고 수익률" 
                value={Math.max(...strategies.map(s => s.total_return * 100)).toFixed(2)} 
                suffix="%"
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic 
                title="평균 승률" 
                value={(strategies.reduce((sum, s) => sum + s.win_rate, 0) / strategies.length * 100).toFixed(1)} 
                suffix="%"
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic 
                title="총 거래 수" 
                value={strategies.reduce((sum, s) => sum + s.total_trades, 0).toLocaleString()} 
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 전략 목록 */}
      <Card title="전략 분석 결과">
        <Table
          dataSource={strategies}
          columns={columns}
          rowKey="strategy_type"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} / 총 ${total}개`,
          }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ margin: 0 }}>
                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <Card size="small" title="수익률 정보">
                      <Statistic title="평균 거래 수익" value={record.avg_trade_return * 100} suffix="%" precision={2} />
                      <Statistic title="최고 거래" value={record.best_trade * 100} suffix="%" precision={2} />
                      <Statistic title="최악 거래" value={record.worst_trade * 100} suffix="%" precision={2} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" title="리스크 정보">
                      <Statistic title="변동성" value={record.volatility * 100} suffix="%" precision={2} />
                      <Statistic title="샤프 비율" value={record.sharpe_ratio} precision={2} />
                      <Progress 
                        percent={record.max_drawdown * 100} 
                        status="exception" 
                        format={() => `최대 손실: ${(record.max_drawdown * 100).toFixed(2)}%`}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" title="추천">
                      <Text>{record.recommendation}</Text>
                    </Card>
                  </Col>
                </Row>
              </div>
            ),
          }}
        />
      </Card>

      {/* 전략 분석 모달 */}
      <Modal
        title="전통적 전략 분석"
        open={analysisModalVisible}
        onCancel={() => {
          setAnalysisModalVisible(false);
          analysisForm.resetFields();
        }}
        onOk={() => {
          analysisForm.submit();
        }}
        confirmLoading={loading}
        width={600}
      >
        <Form
          form={analysisForm}
          layout="vertical"
          onFinish={handleAnalyzeStrategies}
          initialValues={{
            symbols: ['BTC', 'ETH', 'XRP'],
            timeframe: '1h',
            period_days: 30,
            initial_capital: 1000000
          }}
        >
          <Form.Item
            name="symbols"
            label="분석할 코인"
            rules={[{ required: true, message: '분석할 코인을 선택해주세요.' }]}
          >
            <Select mode="multiple" placeholder="분석할 코인을 선택하세요">
              <Option value="BTC">BTC</Option>
              <Option value="ETH">ETH</Option>
              <Option value="XRP">XRP</Option>
              <Option value="ADA">ADA</Option>
              <Option value="DOT">DOT</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="timeframe"
            label="시간 프레임"
            rules={[{ required: true, message: '시간 프레임을 선택해주세요.' }]}
          >
            <Select placeholder="시간 프레임을 선택하세요">
              <Option value="1m">1분</Option>
              <Option value="5m">5분</Option>
              <Option value="15m">15분</Option>
              <Option value="1h">1시간</Option>
              <Option value="4h">4시간</Option>
              <Option value="1d">1일</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="period_days"
            label="분석 기간 (일)"
            rules={[{ required: true, message: '분석 기간을 입력해주세요.' }]}
          >
            <InputNumber
              min={7}
              max={365}
              style={{ width: '100%' }}
              placeholder="예: 30"
            />
          </Form.Item>

          <Form.Item
            name="initial_capital"
            label="초기 자본 (원)"
            rules={[{ required: true, message: '초기 자본을 입력해주세요.' }]}
          >
            <InputNumber
              min={100000}
              max={100000000}
              step={100000}
              style={{ width: '100%' }}
              placeholder="예: 1,000,000"
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value.replace(/\$\s?|(,*)/g, '')}
            />
          </Form.Item>
        </Form>
      </Modal>
    </TraditionalStrategiesContainer>
  );
};

export default TraditionalStrategies;
