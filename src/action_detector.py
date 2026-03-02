"""动作检测器模块"""
from typing import Dict, List, Tuple, Any, Optional, Callable
import time
from .config_loader import ConfigLoader
from .keypoint_parser import KeypointParser
from .condition_engine import ConditionEngine

class ActionState:
    """动作状态"""
    
    def __init__(self, action_name: str, config: Dict[str, Any]):
        self.action_name = action_name
        self.name = config.get('name', action_name)
        self.trigger_cmd = config.get('trigger_cmd')
        self.conditions = config.get('conditions', [])
        self.duration = config.get('duration', 0.3)
        self.cooldown = config.get('cooldown', 1.0)
        
        self.is_active = False
        self.start_time: Optional[float] = None
        self.last_trigger_time: Optional[float] = None
        
    def check_and_trigger(self, conditions_met: bool, current_time: float) -> Optional[str]:
        """
        检查动作状态并触发
        
        Args:
            conditions_met: 条件是否满足
            current_time: 当前时间戳
            
        Returns:
            触发的指令或None
        """
        if conditions_met:
            if not self.is_active:
                self.is_active = True
                self.start_time = current_time
            
            if self.start_time is not None and (current_time - self.start_time) >= self.duration:
                cooldown_ok = self.last_trigger_time is None or (current_time - self.last_trigger_time) >= self.cooldown
                if cooldown_ok:
                    self.last_trigger_time = current_time
                    return self.trigger_cmd
        else:
            self.is_active = False
            self.start_time = None
            
        return None


class ActionDetector:
    """动作检测器，管理所有动作的状态和检测"""
    
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.keypoint_parser = KeypointParser(config_loader)
        self.condition_engine = ConditionEngine(self.keypoint_parser)
        
        self._actions: Dict[str, ActionState] = {}
        self._init_actions()
        
        self.callbacks: List[Callable[[str, str], None]] = []
        
    def _init_actions(self) -> None:
        """初始化所有动作"""
        actions_config = self.config_loader.actions
        for action_name, action_config in actions_config.items():
            self._actions[action_name] = ActionState(action_name, action_config)
            
    def detect(self, keypoints: Dict[str, Tuple[float, float, float]], 
               frame_time: float, exclusive: bool = True) -> List[Tuple[str, str]]:
        """
        检测动作
        
        Args:
            keypoints: 关键点字典
            frame_time: 帧时间戳
            exclusive: 是否互斥模式（只触发一个动作）
            
        Returns:
            动作检测结果列表 [(action_name, trigger_cmd), ...]
        """
        if not self.keypoint_parser.is_valid_pose(keypoints):
            return []
        
        self.condition_engine.update_references(keypoints)
        
        results = []
        
        for action_name, action_state in self._actions.items():
            conditions_met = self.condition_engine.evaluate(
                keypoints, action_state.conditions
            )
            
            trigger_cmd = action_state.check_and_trigger(conditions_met, frame_time)
            
            if trigger_cmd:
                results.append((action_name, trigger_cmd))
                self._notify_callbacks(action_name, trigger_cmd)
                # 触发动作时，给其他所有动作设置冷却，并退出循环
                for other_name, other_state in self._actions.items():
                    if other_name != action_name:
                        other_state.last_trigger_time = frame_time
                break
                
        return results
    
    def register_callback(self, callback: Callable[[str, str], None]) -> None:
        """注册动作触发回调"""
        self.callbacks.append(callback)
        
    def _notify_callbacks(self, action_name: str, trigger_cmd: str) -> None:
        """通知所有回调"""
        for callback in self.callbacks:
            try:
                callback(action_name, trigger_cmd)
            except Exception as e:
                print(f"Callback error: {e}")
                
    def reset(self) -> None:
        """重置所有动作状态"""
        for action_state in self._actions.values():
            action_state.is_active = False
            action_state.start_time = None
        self.condition_engine.reset_references()
        
    def reload_config(self) -> None:
        """重新加载配置"""
        self.config_loader.reload()
        self._actions.clear()
        self._init_actions()
        
    def get_actions(self) -> Dict[str, ActionState]:
        """获取所有动作状态"""
        return self._actions
