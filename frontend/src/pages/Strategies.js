import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Table, 
  Button, 
  Space, 
  Tag, 
  Modal, 
  Form, 
  Input, 
  Select, 
  InputNumber,
  message,
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  PlusOutlined, 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  DeleteOutlined,
  EditOutlined,
  EyeOutlined
} from '@ant-design/icons';
import styled from 'styled-components';
import { strategyAPI } from '../services/api';

const { Title } = Typography;
const { Option } = Select;

const StrategiesContainer = styled.div`
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
  
  .type-day-trading {
    background: #f6ffed;
    color: #52c41a;
  }
  
  .type-swing-trading {
    background: #fff7e6;
    color: #fa8c16;
  }
  
  .type-long-term {
    background: #f9f0ff;
    color: #722ed1;
  }
`;

const Strategies = () => {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState(null);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchStrategies();
  }, []);

  const fetchStrategies = async () => {
    try {
      setLoading(true);
      const response = await strategyAPI.getStrategies();
      setStrategies(response.data.strategies || []);
    } catch (error) {
      message.error('전략 목록을 불러오는데 실패했습니다.');
      console.error('전략 목록 로딩 실패:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStrategy = async (values) => {
    try {
      await strategyAPI.createStrategy(values);
      message.success('전략이 성공적으로 생성되었습니다.');
      setModalVisible(false);
      form.resetFields();
      fetchStrategies();
    } catch (error) {
      message.error('전략 생성에 실패했습니다.');
      console.error('전략 생성 실패:', error);
    }
  };

  const handleStartStrategy = async (id) => {
    try {
      await strategyAPI.startStrategy(id);
      message.success('전략이 시작되었습니다.');
      fetchStrategies();
    } catch (error) {
      message.error('전략 시작에 실패했습니다.');
      console.error('전략 시작 실패:', error);
    }
  };

  const handleStopStrategy = async (id) => {
    try {
      await strategyAPI.stopStrategy(id);
      message.success('전략이 중지되었습니다.');
      fetchStrategies();
    } catch (error) {
      message.error('전략 중지에 실패했습니다.');
      console.error('전략 중지 실패:', error);
    }
  };

  const handleDeleteStrategy = async (id) => {
    try {
      await strategyAPI.deleteStrategy(id);
      message.success('전략이 삭제되었습니다.');
      fetchStrategies();
    } catch (error) {
      message.error('전략 삭제에 실패했습니다.');
      console.error('전략 삭제 실패:', error);
    }
  };

  const getStrategyTypeConfig = (type) => {
    const typeMap = {
      scalping: { color: 'blue', text: '스캘핑', className: 'type-scalping' },
      day_trading: { color: 'green', text: '데이트레이딩', className: 'type-day-trading' },
      swing_trading: { color: 'orange', text: '스윙트레이딩', className: 'type-swing-trading' },
      long_term: { color: 'purple', text: '장기투자', className: 'type-long-term' },
    };
    return typeMap[type] || { color: 'default', text: type, className: 'type-default' };
  };

  const columns = [
    {
      title: '전략명',
      dataIndex: 'name',
      key: 'name',
      render: (name) => <strong>{name}</strong>,
    },
    {
      title: '타입',
      dataIndex: 'strategy_type',
      key: 'strategy_type',
      render: (type) => {
        const config = getStrategyTypeConfig(type);
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '상태',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? '실행중' : '중지됨'}
        </Tag>
      ),
    },
    {
      title: '리스크',
      dataIndex: 'risk_per_trade',
      key: 'risk_per_trade',
      render: (risk) => `${(risk * 100).toFixed(1)}%`,
    },
    {
      title: '최대 포지션',
      dataIndex: 'max_positions',
      key: 'max_positions',
    },
    {
      title: '생성일',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: '작업',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button 
            type="text" 
            icon={<EyeOutlined />} 
            onClick={() => console.log('전략 상세 보기:', record.id)}
          />
          <Button 
            type="text" 
            icon={<EditOutlined />} 
            onClick={() => console.log('전략 수정:', record.id)}
          />
          {record.is_active ? (
            <Button 
              type="text" 
              icon={<PauseCircleOutlined />} 
              onClick={() => handleStopStrategy(record.id)}
            />
          ) : (
            <Button 
              type="text" 
              icon={<PlayCircleOutlined />} 
              onClick={() => handleStartStrategy(record.id)}
            />
          )}
          <Popconfirm
            title="정말 삭제하시겠습니까?"
            onConfirm={() => handleDeleteStrategy(record.id)}
            okText="삭제"
            cancelText="취소"
          >
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />} 
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <StrategiesContainer>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2}>전략 관리</Title>
        <Button 
          type="primary" 
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
        >
          새 전략 생성
        </Button>
      </div>

      {/* 전략 통계 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic 
              title="총 전략 수" 
              value={strategies.length} 
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic 
              title="실행중인 전략" 
              value={strategies.filter(s => s.is_active).length} 
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic 
              title="중지된 전략" 
              value={strategies.filter(s => !s.is_active).length} 
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 전략 목록 */}
      <Card title="전략 목록">
        <Table
          dataSource={strategies}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} / 총 ${total}개`,
          }}
        />
      </Card>

      {/* 전략 생성 모달 */}
      <Modal
        title="새 전략 생성"
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateStrategy}
        >
          <Form.Item
            name="name"
            label="전략명"
            rules={[{ required: true, message: '전략명을 입력해주세요.' }]}
          >
            <Input placeholder="전략명을 입력하세요" />
          </Form.Item>

          <Form.Item
            name="strategy_type"
            label="전략 타입"
            rules={[{ required: true, message: '전략 타입을 선택해주세요.' }]}
          >
            <Select placeholder="전략 타입을 선택하세요">
              <Option value="scalping">스캘핑</Option>
              <Option value="day_trading">데이트레이딩</Option>
              <Option value="swing_trading">스윙트레이딩</Option>
              <Option value="long_term">장기투자</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="risk_per_trade"
            label="거래당 리스크 (%)"
            rules={[{ required: true, message: '리스크 비율을 입력해주세요.' }]}
          >
            <InputNumber
              min={0.1}
              max={10}
              step={0.1}
              style={{ width: '100%' }}
              placeholder="예: 2.0"
            />
          </Form.Item>

          <Form.Item
            name="max_positions"
            label="최대 포지션 수"
            rules={[{ required: true, message: '최대 포지션 수를 입력해주세요.' }]}
          >
            <InputNumber
              min={1}
              max={20}
              style={{ width: '100%' }}
              placeholder="예: 5"
            />
          </Form.Item>

          <Form.Item
            name="parameters"
            label="전략 파라미터"
            initialValue={{}}
          >
            <Input.TextArea
              rows={4}
              placeholder="전략별 파라미터를 JSON 형태로 입력하세요"
            />
          </Form.Item>
        </Form>
      </Modal>
    </StrategiesContainer>
  );
};

export default Strategies;


