import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Button, 
  Form, 
  Input, 
  Select, 
  DatePicker, 
  InputNumber,
  message,
  Row,
  Col,
  Typography,
  Table,
  Tag,
  Progress,
  Statistic,
  Space
} from 'antd';
import { 
  PlayCircleOutlined, 
  BarChartOutlined,
  DownloadOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { backtestingAPI } from '../services/api';

const { Title } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

const BacktestingContainer = styled.div`
  .backtest-form {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
  
  .result-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }
  
  .metric-card {
    text-align: center;
    padding: 16px;
    border-radius: 8px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }
  
  .metric-value {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 4px;
  }
  
  .metric-label {
    font-size: 0.875rem;
    opacity: 0.9;
  }
`;

const Backtesting = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [backtestResult, setBacktestResult] = useState(null);
  const [backtestHistory, setBacktestHistory] = useState([]);

  useEffect(() => {
    fetchBacktestHistory();
  }, []);

  const fetchBacktestHistory = async () => {
    try {
      // 백테스팅 히스토리 조회 (실제 API 연동 시 구현)
      setBacktestHistory([]);
    } catch (error) {
      console.error('백테스팅 히스토리 로딩 실패:', error);
    }
  };

  const handleRunBacktest = async (values) => {
    try {
      setLoading(true);
      const response = await backtestingAPI.runBacktest(values);
      setBacktestResult(response.data);
      message.success('백테스팅이 완료되었습니다.');
    } catch (error) {
      message.error('백테스팅 실행에 실패했습니다.');
      console.error('백테스팅 실행 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const historyColumns = [
    {
      title: '실행일',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleString(),
    },
    {
      title: '전략',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
    },
    {
      title: '기간',
      dataIndex: 'period',
      key: 'period',
    },
    {
      title: '수익률',
      dataIndex: 'total_return',
      key: 'total_return',
      render: (return_rate) => (
        <Tag color={return_rate >= 0 ? 'green' : 'red'}>
          {return_rate >= 0 ? '+' : ''}{return_rate.toFixed(2)}%
        </Tag>
      ),
    },
    {
      title: '샤프 비율',
      dataIndex: 'sharpe_ratio',
      key: 'sharpe_ratio',
      render: (ratio) => ratio.toFixed(2),
    },
    {
      title: '최대 낙폭',
      dataIndex: 'max_drawdown',
      key: 'max_drawdown',
      render: (drawdown) => (
        <Tag color="red">
          -{drawdown.toFixed(2)}%
        </Tag>
      ),
    },
    {
      title: '작업',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button type="link" size="small">
            상세보기
          </Button>
          <Button type="link" size="small" icon={<DownloadOutlined />}>
            리포트 다운로드
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <BacktestingContainer>
      <Title level={2}>백테스팅</Title>

      {/* 백테스팅 설정 */}
      <Card title="백테스팅 설정" className="backtest-form">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleRunBacktest}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12}>
              <Form.Item
                name="strategy_id"
                label="전략 선택"
                rules={[{ required: true, message: '전략을 선택해주세요.' }]}
              >
                <Select placeholder="백테스팅할 전략을 선택하세요">
                  <Option value="1">스캘핑 전략</Option>
                  <Option value="2">데이트레이딩 전략</Option>
                  <Option value="3">스윙트레이딩 전략</Option>
                  <Option value="4">장기투자 전략</Option>
                </Select>
              </Form.Item>
            </Col>
            
            <Col xs={24} sm={12}>
              <Form.Item
                name="symbol"
                label="거래 심볼"
                rules={[{ required: true, message: '거래 심볼을 선택해주세요.' }]}
              >
                <Select placeholder="거래할 심볼을 선택하세요">
                  <Option value="BTC">BTC</Option>
                  <Option value="ETH">ETH</Option>
                  <Option value="XRP">XRP</Option>
                </Select>
              </Form.Item>
            </Col>
            
            <Col xs={24} sm={12}>
              <Form.Item
                name="start_date"
                label="시작일"
                rules={[{ required: true, message: '시작일을 선택해주세요.' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            
            <Col xs={24} sm={12}>
              <Form.Item
                name="end_date"
                label="종료일"
                rules={[{ required: true, message: '종료일을 선택해주세요.' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            
            <Col xs={24} sm={12}>
              <Form.Item
                name="initial_capital"
                label="초기 자본"
                rules={[{ required: true, message: '초기 자본을 입력해주세요.' }]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="예: 1000000"
                  formatter={value => `₩ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  parser={value => value.replace(/₩\s?|(,*)/g, '')}
                />
              </Form.Item>
            </Col>
            
            <Col xs={24} sm={12}>
              <Form.Item
                name="commission_rate"
                label="수수료율 (%)"
                initialValue={0.25}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  min={0}
                  max={1}
                  step={0.01}
                  placeholder="예: 0.25"
                />
              </Form.Item>
            </Col>
          </Row>
          
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<PlayCircleOutlined />}
              size="large"
            >
              백테스팅 실행
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* 백테스팅 결과 */}
      {backtestResult && (
        <Card title="백테스팅 결과" className="result-card">
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={24} sm={6}>
              <div className="metric-card">
                <div className="metric-value">
                  {backtestResult.total_return >= 0 ? '+' : ''}
                  {backtestResult.total_return.toFixed(2)}%
                </div>
                <div className="metric-label">총 수익률</div>
              </div>
            </Col>
            <Col xs={24} sm={6}>
              <div className="metric-card">
                <div className="metric-value">
                  {backtestResult.sharpe_ratio.toFixed(2)}
                </div>
                <div className="metric-label">샤프 비율</div>
              </div>
            </Col>
            <Col xs={24} sm={6}>
              <div className="metric-card">
                <div className="metric-value">
                  -{backtestResult.max_drawdown.toFixed(2)}%
                </div>
                <div className="metric-label">최대 낙폭</div>
              </div>
            </Col>
            <Col xs={24} sm={6}>
              <div className="metric-card">
                <div className="metric-value">
                  {backtestResult.win_rate.toFixed(1)}%
                </div>
                <div className="metric-label">승률</div>
              </div>
            </Col>
          </Row>

          {/* 성과 차트 */}
          <Card title="포트폴리오 성과" style={{ marginBottom: 24 }}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={backtestResult.performance_data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#1890ff" 
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          {/* 상세 통계 */}
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={8}>
              <Statistic 
                title="총 거래 수" 
                value={backtestResult.total_trades} 
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col xs={24} sm={8}>
              <Statistic 
                title="승리 거래" 
                value={backtestResult.winning_trades} 
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col xs={24} sm={8}>
              <Statistic 
                title="패배 거래" 
                value={backtestResult.losing_trades} 
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Col>
          </Row>
        </Card>
      )}

      {/* 백테스팅 히스토리 */}
      <Card 
        title="백테스팅 히스토리" 
        extra={
          <Button icon={<HistoryOutlined />}>
            전체 히스토리
          </Button>
        }
      >
        <Table
          dataSource={backtestHistory}
          columns={historyColumns}
          rowKey="id"
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
          }}
        />
      </Card>
    </BacktestingContainer>
  );
};

export default Backtesting;
