"""MQTT客户端模块"""
import json
import time
import threading
from typing import Optional, Dict, Any, Callable, List
import paho.mqtt.client as mqtt
from pathlib import Path


class MQTTClient:
    """MQTT客户端，支持连接管理、重连和心跳"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mqtt_config = config.get('mqtt', {})
        
        self.broker = self.mqtt_config.get('broker', 'localhost')
        self.port = self.mqtt_config.get('port', 1883)
        self.username = self.mqtt_config.get('username', '')
        self.password = self.mqtt_config.get('password', '')
        self.client_id = self.mqtt_config.get('client_id', 'action_recognition')
        self.qos = self.mqtt_config.get('qos', 1)
        
        reconnect_config = self.mqtt_config.get('reconnect', {})
        self.reconnect_enabled = reconnect_config.get('enabled', True)
        self.reconnect_interval = reconnect_config.get('interval', 5)
        self.max_retries = reconnect_config.get('max_retries', 10)
        
        heartbeat_config = self.mqtt_config.get('heartbeat', {})
        self.heartbeat_enabled = heartbeat_config.get('enabled', True)
        self.heartbeat_interval = heartbeat_config.get('interval', 30)
        
        device_config = self.mqtt_config.get('device', {})
        self.device_id = device_config.get('device_id', 'device_001')
        
        self.config_topic = self.mqtt_config.get('config_topic', 'action/config')
        
        response_config = self.mqtt_config.get('response', {})
        self.response_topic = response_config.get('topic', 'action/{device_id}/response')
        
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        self._connected = False
        self._should_reconnect = True
        self._reconnect_count = 0
        self._heartbeat_thread: Optional[threading.Thread] = None
        
        self._message_callbacks: List[Callable[[str, str], None]] = []
        
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self._connected = True
            self._reconnect_count = 0
            print(f"[MQTT] 连接成功: {self.broker}:{self.port}")
            
            self._subscribe_config_topic()
            
            if self.heartbeat_enabled:
                self._start_heartbeat()
        else:
            print(f"[MQTT] 连接失败，错误码: {rc}")
            
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self._connected = False
        print(f"[MQTT] 连接断开，错误码: {rc}")
        
        if self.reconnect_enabled and self._should_reconnect:
            self._reconnect()
            
    def _on_message(self, client, userdata, msg):
        """接收消息回调"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            print(f"[MQTT] 收到消息 [{topic}]: {payload}")
            
            for callback in self._message_callbacks:
                try:
                    callback(topic, payload)
                except Exception as e:
                    print(f"[MQTT] 消息处理回调错误: {e}")
        except Exception as e:
            print(f"[MQTT] 消息处理错误: {e}")
            
    def _subscribe_config_topic(self):
        """订阅配置命令Topic"""
        try:
            result = self.client.subscribe(self.config_topic, qos=self.qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                print(f"[MQTT] 已订阅配置命令 Topic: {self.config_topic}")
            else:
                print(f"[MQTT] 订阅失败，错误码: {result[0]}")
        except Exception as e:
            print(f"[MQTT] 订阅配置命令Topic失败: {e}")
            
    def register_message_callback(self, callback: Callable[[str, str], None]):
        """注册消息接收回调"""
        self._message_callbacks.append(callback)
            
    def _reconnect(self):
        """重连机制"""
        if self.max_retries > 0 and self._reconnect_count >= self.max_retries:
            print(f"[MQTT] 达到最大重连次数: {self.max_retries}")
            return
            
        self._reconnect_count += 1
        print(f"[MQTT] 正在重连... ({self._reconnect_count})")
        
        retry_count = 0
        while self._should_reconnect and retry_count < self.max_retries:
            try:
                self.client.connect(self.broker, self.port, keepalive=60)
                self.client.loop_start()
                return
            except Exception as e:
                retry_count += 1
                print(f"[MQTT] 重连失败: {e}")
                time.sleep(self.reconnect_interval)
                
    def _start_heartbeat(self):
        """启动心跳"""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        
        device_info = self.get_device_info()
        response_topic = self.response_topic.format(**device_info)
            
        def heartbeat_loop():
            while self._should_reconnect and self._connected:
                try:
                    heartbeat_msg = {
                        "type": "heartbeat",
                        "device_id": self.device_id,
                        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
                        "data": {}
                    }
                    self.client.publish(
                        response_topic,
                        json.dumps(heartbeat_msg),
                        qos=self.qos
                    )
                    print(f"[MQTT] 心跳已发送到 {response_topic}")
                except Exception as e:
                    print(f"[MQTT] 心跳发送失败: {e}")
                time.sleep(self.heartbeat_interval)
                
        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
    def connect(self) -> bool:
        """连接到MQTT服务器"""
        try:
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT] 连接失败: {e}")
            return False
            
    def disconnect(self):
        """断开连接"""
        self._should_reconnect = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2)
        self.client.loop_stop()
        self.client.disconnect()
        print("[MQTT] 已断开连接")
        
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
        
    def publish(self, topic: str, payload: str, qos: Optional[int] = None) -> bool:
        """发布消息"""
        if not self._connected:
            print("[MQTT] 未连接，无法发送消息")
            return False
            
        try:
            qos = qos if qos is not None else self.qos
            result = self.client.publish(topic, payload, qos=qos)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                print(f"[MQTT] 发送失败，错误码: {result.rc}")
                return False
        except Exception as e:
            print(f"[MQTT] 发送消息异常: {e}")
            return False
            
    def get_device_info(self) -> Dict[str, str]:
        """获取设备信息"""
        return {
            "device_id": self.device_id
        }


def create_mqtt_client(config: Dict[str, Any]) -> MQTTClient:
    """创建MQTT客户端"""
    return MQTTClient(config)
