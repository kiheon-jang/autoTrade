import { useState, useEffect, useRef } from 'react';

const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);
  const socketRef = useRef(null);

  useEffect(() => {
    // WebSocket 연결
    const connectWebSocket = () => {
      try {
        // FastAPI WebSocket 엔드포인트에 직접 연결
                socketRef.current = new WebSocket('ws://localhost:8010/api/v1/monitoring/ws');

        socketRef.current.onopen = () => {
          console.log('WebSocket 연결됨');
          setIsConnected(true);
          setError(null);
        };

        socketRef.current.onclose = () => {
          console.log('WebSocket 연결 끊김');
          setIsConnected(false);
        };

        socketRef.current.onerror = (err) => {
          console.error('WebSocket 연결 오류:', err);
          setError('WebSocket 연결 실패');
          setIsConnected(false);
        };

        socketRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('WebSocket 메시지 수신:', data);
            setLastMessage(data);
          } catch (error) {
            console.error('메시지 파싱 오류:', error);
          }
        };

      } catch (error) {
        console.error('WebSocket 연결 실패:', error);
        setError(error.message);
        setIsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
    };
  }, []);

  const sendMessage = (message) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    }
  };

  const subscribe = (event, callback) => {
    // FastAPI WebSocket은 이벤트 기반이 아닌 메시지 기반이므로
    // lastMessage를 통해 데이터를 받습니다
    console.log('WebSocket 구독:', event);
  };

  const unsubscribe = (event, callback) => {
    console.log('WebSocket 구독 해제:', event);
  };

  return {
    isConnected,
    lastMessage,
    error,
    sendMessage,
    subscribe,
    unsubscribe,
  };
};

export { useWebSocket };
export default useWebSocket;