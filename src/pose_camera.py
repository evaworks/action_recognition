"""摄像头姿态识别主程序"""
import os
import sys
import time
import json
import cv2
import numpy as np
from typing import Optional
from pathlib import Path

from ultralytics import YOLO

from .config_loader import ConfigLoader
from .keypoint_parser import KeypointParser
from .condition_engine import ConditionEngine
from .action_detector import ActionDetector


class PoseCamera:
    """摄像头姿态识别主类"""
    
    def __init__(self, model_path: str = None, config_dir: str = None, mqtt_enabled: bool = True):
        self.model_path = model_path
        self.config_dir = config_dir
        self.mqtt_enabled = mqtt_enabled
        
        self._init_config()
        self._init_model()
        self._init_detector()
        self._init_mqtt()
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = time.time()
        
    def _init_config(self) -> None:
        """初始化配置"""
        if self.config_dir is None:
            self.config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        self.config_loader = ConfigLoader(self.config_dir)
        self.config_loader.load_all()
        print(f"已加载 {len(self.config_loader.actions)} 个动作配置")
        
    def _init_model(self) -> None:
        """初始化YOLO模型"""
        if self.model_path is None:
            self.model_path = 'yolo11s-pose.pt'
            
        import torch
        
        if torch.cuda.is_available():
            device = 'cuda'
        elif torch.backends.mps.is_available():
            device = 'mps'
        else:
            device = 'cpu'
        
        device_name = 'CUDA' if device == 'cuda' else 'Apple GPU' if device == 'mps' else 'CPU'
        print(f"加载模型: {self.model_path}")
        print(f"使用设备: {device} ({device_name})")
        self.model = YOLO(self.model_path)
        self.model.to(device)
        print("模型加载完成")
        
    def _init_detector(self) -> None:
        """初始化动作检测器"""
        self.action_detector = ActionDetector(self.config_loader)
        
        self.action_detector.register_callback(self._on_action_triggered)
        
    def _init_mqtt(self) -> None:
        """初始化MQTT客户端"""
        self.mqtt_client = None
        self.message_sender = None
        
        if not self.mqtt_enabled:
            print("MQTT 已禁用")
            return
            
        if not self.config_loader.mqtt_enabled:
            print("MQTT 配置未找到，已禁用")
            return
            
        try:
            from .mqtt_client import MQTTClient
            from .message_sender import MessageSender
            
            self.mqtt_client = MQTTClient(self.config_loader.mqtt)
            if self.mqtt_client.connect():
                self.message_sender = MessageSender(self.mqtt_client)
                self.mqtt_client.register_message_callback(self._on_mqtt_message)
                print(f"MQTT 已连接: {self.mqtt_client.broker}:{self.mqtt_client.port}")
            else:
                print("MQTT 连接失败")
        except ImportError:
            print("paho-mqtt 未安装，MQTT 功能不可用")
        except Exception as e:
            print(f"MQTT 初始化失败: {e}")
    
    def _on_mqtt_message(self, topic: str, payload: str) -> None:
        """处理MQTT收到的配置命令"""
        try:
            data = json.loads(payload)
            command = data.get('command', '')
            device_id = data.get('device_id', '')
            
            if device_id and device_id != self.mqtt_client.device_id:
                print(f"[CONFIG] 忽略非本设备命令: {device_id}")
                return
            
            response_data = self._handle_config_command(command, data)
            
            if self.message_sender:
                self.message_sender.send_response_message(
                    command=command,
                    success=response_data.get('success', False),
                    message=response_data.get('message', ''),
                    extra_data=response_data.get('extra_data')
                )
                
        except json.JSONDecodeError:
            print(f"[CONFIG] JSON解析失败: {payload}")
        except Exception as e:
            print(f"[CONFIG] 命令处理错误: {e}")
    
    def _handle_config_command(self, command: str, data: dict) -> dict:
        """处理配置命令"""
        result = {
            "success": False,
            "message": ""
        }
        
        if command == 'list':
            actions = self.action_detector.get_actions()
            result['success'] = True
            result['extra_data'] = {
                "actions": [
                    {
                        "name": name,
                        "config": {
                            "trigger_cmd": action.trigger_cmd,
                            "name": action.name,
                            "duration": action.duration,
                            "cooldown": action.cooldown
                        }
                    }
                    for name, action in actions.items()
                ]
            }
            print(f"[CONFIG] 列出动作: {len(actions)} 个")
            
        elif command == 'reload':
            try:
                self.config_loader.reload()
                self.action_detector.reload_config()
                result['success'] = True
                result['message'] = f"已重新加载配置，当前 {len(self.action_detector.get_actions())} 个动作"
                print(f"[CONFIG] 重新加载配置成功")
            except Exception as e:
                result['message'] = f"重新加载失败: {e}"
                print(f"[CONFIG] 重新加载失败: {e}")
                
        elif command == 'add_action':
            action_name = data.get('action_name')
            action_config = data.get('config')
            if action_name and action_config:
                try:
                    success = self._add_action(action_name, action_config)
                    result['success'] = success
                    result['message'] = f"添加动作 {'成功' if success else '失败'}: {action_name}"
                    print(f"[CONFIG] 添加动作: {action_name}")
                except Exception as e:
                    result['message'] = f"添加动作失败: {e}"
            else:
                result['message'] = "缺少 action_name 或 config 参数"
                
        elif command == 'remove_action':
            action_name = data.get('action_name')
            if action_name:
                try:
                    success = self._remove_action(action_name)
                    result['success'] = success
                    result['message'] = f"删除动作 {'成功' if success else '失败'}: {action_name}"
                    print(f"[CONFIG] 删除动作: {action_name}")
                except Exception as e:
                    result['message'] = f"删除动作失败: {e}"
            else:
                result['message'] = "缺少 action_name 参数"
                
        else:
            result['message'] = f"未知命令: {command}"
            
        return result
    
    def _add_action(self, action_name: str, action_config: dict) -> bool:
        """动态添加动作"""
        from .action_detector import ActionState
        
        if action_name in self.action_detector.get_actions():
            print(f"[CONFIG] 动作已存在: {action_name}")
            return False
            
        action_state = ActionState(action_name, action_config)
        self.action_detector._actions[action_name] = action_state
        
        if not self.config_loader.add_action(action_name, action_config):
            print(f"[CONFIG] 警告: 保存配置到文件失败")
        
        print(f"[CONFIG] 已添加动作: {action_name}")
        return True
    
    def _remove_action(self, action_name: str) -> bool:
        """动态删除动作"""
        if action_name not in self.action_detector.get_actions():
            print(f"[CONFIG] 动作不存在: {action_name}")
            return False
            
        del self.action_detector._actions[action_name]
        
        if not self.config_loader.remove_action(action_name):
            print(f"[CONFIG] 警告: 保存配置到文件失败")
            
        print(f"[CONFIG] 已删除动作: {action_name}")
        return True
        
    def _on_action_triggered(self, action_name: str, trigger_cmd: str) -> None:
        """动作触发回调"""
        action = self.action_detector.get_actions()[action_name]
        RED = '\033[91m'
        RESET = '\033[0m'
        print(f"\n{RED}{'='*50}{RESET}")
        print(f"{RED}动作触发: {action.name}{RESET}")
        print(f"{RED}指令: {trigger_cmd}{RESET}")
        print(f"{RED}时间: {time.strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{RED}{'='*50}{RESET}\n")
        
        if self.message_sender:
            self.message_sender.send_action_message(
                action=trigger_cmd,
                action_name=action.name,
                confidence=1.0
            )
        
    def open_camera(self, camera_index: int = 0) -> bool:
        """打开摄像头"""
        self.cap = cv2.VideoCapture(camera_index)
        
        if not self.cap.isOpened():
            print(f"无法打开摄像头 {camera_index}")
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        print(f"摄像头已打开: {camera_index}")
        return True
    
    def process_frame(self, frame: np.ndarray, debug: bool = False) -> tuple:
        """
        处理单帧图像
        
        Args:
            frame: 输入帧
            debug: 是否显示调试信息
            
        Returns:
            (annotated_frame, detected_actions)
        """
        results = self.model(frame, stream=True, task='pose', verbose=False)
        
        detected_actions = []
        
        for result in results:
            if result.keypoints is not None and len(result.keypoints) > 0:
                keypoints_data = result.keypoints.data[0].cpu().numpy()
                
                keypoints = self.action_detector.keypoint_parser.parse(keypoints_data)
                
                if debug:
                    rw = keypoints.get('right_wrist')
                    rs = keypoints.get('right_shoulder')
                    lw = keypoints.get('left_wrist')
                    ls = keypoints.get('left_shoulder')
                    print(f"DEBUG: 右手腕={rw[:2] if rw else None}, 右肩膀={rs[:2] if rs else None}")
                    print(f"DEBUG: 左手腕={lw[:2] if lw else None}, 左肩膀={ls[:2] if ls else None}")
                    if rw and rs:
                        print(f"DEBUG: 右手腕y < 右肩膀y-0 ? {rw[1] < rs[1]}")
                
                current_time = time.time()
                actions = self.action_detector.detect(keypoints, current_time)
                
                if actions:
                    detected_actions.extend(actions)
                
                annotated = self._draw_keypoints(frame, keypoints)
            else:
                annotated = frame
                
        return annotated, detected_actions
    
    def _draw_keypoints(self, frame: np.ndarray, 
                       keypoints: dict) -> np.ndarray:
        """绘制关键点和骨架"""
        annotated = frame.copy()
        
        skeleton = [
            (5, 7), (7, 9), (6, 8), (8, 10),
            (5, 6), (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16)
        ]
        
        keypoints_map = self.config_loader.keypoints
        index_to_name = {v: k for k, v in keypoints_map.items()}
        
        for idx, (name, kp) in enumerate(keypoints.items()):
            x, y, conf = kp
            if conf > 0.3:
                cv2.circle(annotated, (int(x), int(y)), 5, (0, 255, 0), -1)
                cv2.putText(annotated, name, (int(x) + 10, int(y)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        for joint1_idx, joint2_idx in skeleton:
            name1 = index_to_name.get(joint1_idx)
            name2 = index_to_name.get(joint2_idx)
            
            if name1 and name2:
                kp1 = keypoints.get(name1)
                kp2 = keypoints.get(name2)
                
                if kp1 and kp2 and kp1[2] > 0.3 and kp2[2] > 0.3:
                    cv2.line(annotated, 
                            (int(kp1[0]), int(kp1[1])), 
                            (int(kp2[0]), int(kp2[1])), 
                            (0, 255, 255), 2)
                    
        return annotated
    
    def run(self, camera_index: int = 0, debug: bool = False, hidden: bool = False) -> None:
        """运行主循环"""
        if not self.open_camera(camera_index):
            return
            
        print("\n开始姿态识别... 按 'q' 退出")
        print("="*50)
        
        if hidden:
            import win32gui
            import win32con
        
        while True:
            ret, frame = self.cap.read()
            
            if not ret:
                print("无法读取帧")
                break
            
            self.frame_count += 1
            
            if self.frame_count % 30 == 0:
                current_time = time.time()
                self.fps = 30 / (current_time - self.last_fps_time)
                self.last_fps_time = current_time
            
            annotated_frame, actions = self.process_frame(frame, debug=debug)
            
            cv2.putText(annotated_frame, f"FPS: {self.fps:.1f}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                       1, (0, 255, 0), 2)
            
            for action_name, trigger_cmd in actions:
                cv2.putText(annotated_frame, f"Action: {trigger_cmd}", 
                           (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (0, 0, 255), 2)
            
            if hidden:
                hwnd = win32gui.FindWindow(None, 'Pose Recognition')
                if hwnd:
                    win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            
            cv2.imshow('Pose Recognition', annotated_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
        self.release()
        
    def release(self) -> None:
        """释放资源"""
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        print("\n程序已退出")


def create_pose_camera(model_path: str = None, config_dir: str = None, mqtt_enabled: bool = True) -> PoseCamera:
    """创建PoseCamera实例"""
    return PoseCamera(model_path, config_dir, mqtt_enabled)
