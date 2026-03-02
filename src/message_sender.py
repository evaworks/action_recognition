"""消息发送器模块"""
import json
import time
from typing import Dict, Any, Optional, Tuple
from .mqtt_client import MQTTClient


class MessageSender:
    """消息发送器，负责构建和发送统一格式的JSON消息"""
    
    def __init__(self, mqtt_client: MQTTClient):
        self.mqtt_client = mqtt_client
        device_info = mqtt_client.get_device_info()
        self.response_topic = mqtt_client.response_topic.format(**device_info)
        self.qos = mqtt_client.qos
    
    def _build_base_message(self, msg_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """构建基础消息格式"""
        device_info = self.mqtt_client.get_device_info()
        return {
            "type": msg_type,
            "device_id": device_info["device_id"],
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "data": data
        }
        
    def send_action_message(
        self,
        action: str,
        action_name: str,
        confidence: float = 1.0,
        keypoints_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送动作消息
        
        Args:
            action: 动作指令（如 RAISE_RIGHT_HAND）
            action_name: 动作名称（如 举起右手）
            confidence: 置信度
            keypoints_data: 关键点数据（可选）
            
        Returns:
            发送是否成功
        """
        data = {
            "action": action,
            "action_name": action_name,
            "confidence": confidence
        }
        
        if keypoints_data:
            data["keypoints"] = keypoints_data
            
        message = self._build_base_message("action", data)
        json_str = json.dumps(message, ensure_ascii=False)
        
        print(f"[MQTT] 发送动作消息: {json_str}")
        
        return self.mqtt_client.publish(self.response_topic, json_str, self.qos)
        
    def send_batch_actions(
        self,
        actions: list,
        keypoints_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送批量动作消息
        
        Args:
            actions: 动作列表 [{"action": "...", "action_name": "..."}, ...]
            keypoints_data: 关键点数据
            
        Returns:
            发送是否成功
        """
        data = {
            "actions": actions
        }
        
        if keypoints_data:
            data["keypoints"] = keypoints_data
            
        message = self._build_base_message("action", data)
        json_str = json.dumps(message, ensure_ascii=False)
        
        print(f"[MQTT] 发送批量消息: {json_str}")
        
        return self.mqtt_client.publish(self.response_topic, json_str, self.qos)
        
    def send_response_message(
        self,
        command: str,
        success: bool,
        message: str = "",
        extra_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        发送命令响应消息
        
        Args:
            command: 命令类型（list/reload/add_action/remove_action）
            success: 是否成功
            message: 响应消息
            extra_data: 额外数据
            
        Returns:
            发送是否成功
        """
        data = {
            "command": command,
            "success": success,
            "message": message
        }
        
        if extra_data:
            data.update(extra_data)
            
        message = self._build_base_message("response", data)
        json_str = json.dumps(message, ensure_ascii=False)
        
        print(f"[MQTT] 发送响应消息: {json_str}")
        
        return self.mqtt_client.publish(self.response_topic, json_str, self.qos)


def create_message_sender(mqtt_client: MQTTClient) -> MessageSender:
    """创建消息发送器"""
    return MessageSender(mqtt_client)
