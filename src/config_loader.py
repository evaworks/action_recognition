"""配置加载模块"""
import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path


class ConfigLoader:
    """配置加载器，负责加载YAML配置文件"""
    
    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        self.config_dir = Path(config_dir)
        self._actions_config: Dict[str, Any] = {}
        self._keypoints_config: Dict[str, Any] = {}
        self._mqtt_config: Dict[str, Any] = {}
        
    def load_all(self) -> None:
        """加载所有配置文件"""
        self.load_actions_config()
        self.load_keypoints_config()
        self.load_mqtt_config()
        
    def load_actions_config(self) -> Dict[str, Any]:
        """加载动作配置文件"""
        config_path = self.config_dir / 'actions.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            self._actions_config = yaml.safe_load(f)
        return self._actions_config
    
    def load_keypoints_config(self) -> Dict[str, Any]:
        """加载关键点配置文件"""
        config_path = self.config_dir / 'keypoints.yaml'
        with open(config_path, 'r', encoding='utf-8') as f:
            self._keypoints_config = yaml.safe_load(f)
        return self._keypoints_config
    
    def load_mqtt_config(self) -> Dict[str, Any]:
        """加载MQTT配置文件"""
        config_path = self.config_dir / 'mqtt.yaml'
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self._mqtt_config = yaml.safe_load(f)
        return self._mqtt_config
    
    @property
    def actions(self) -> Dict[str, Any]:
        """获取动作配置"""
        return self._actions_config.get('actions', {})
    
    @property
    def keypoints(self) -> Dict[str, Any]:
        """获取关键点配置"""
        return self._keypoints_config.get('keypoints', {})
    
    @property
    def composite_keypoints(self) -> Dict[str, Any]:
        """获取复合关键点配置"""
        return self._keypoints_config.get('composite_keypoints', {})
    
    @property
    def reference_keypoints(self) -> Dict[str, Any]:
        """获取参考关键点配置"""
        return self._keypoints_config.get('reference_keypoints', {})
    
    @property
    def mqtt(self) -> Dict[str, Any]:
        """获取MQTT配置"""
        return self._mqtt_config
    
    @property
    def mqtt_enabled(self) -> bool:
        """是否启用MQTT"""
        return bool(self._mqtt_config.get('mqtt'))
    
    def get_action_config(self, action_name: str) -> Optional[Dict[str, Any]]:
        """获取指定动作的配置"""
        return self.actions.get(action_name)
    
    def get_keypoint_index(self, keypoint_name: str) -> Optional[int]:
        """获取关键点索引"""
        return self.keypoints.get(keypoint_name)
    
    def reload(self) -> None:
        """重新加载配置"""
        self.load_all()
    
    def save_actions_config(self) -> bool:
        """保存动作配置到文件"""
        try:
            config_path = self.config_dir / 'actions.yaml'
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self._actions_config, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception as e:
            print(f"[ConfigLoader] 保存动作配置失败: {e}")
            return False
    
    def add_action(self, action_name: str, action_config: Dict[str, Any]) -> bool:
        """添加动作配置"""
        if 'actions' not in self._actions_config:
            self._actions_config['actions'] = {}
        
        if action_name in self._actions_config['actions']:
            return False
            
        self._actions_config['actions'][action_name] = action_config
        return self.save_actions_config()
    
    def remove_action(self, action_name: str) -> bool:
        """删除动作配置"""
        if action_name not in self._actions_config.get('actions', {}):
            return False
            
        del self._actions_config['actions'][action_name]
        return self.save_actions_config()


def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """获取配置加载器单例"""
    loader = ConfigLoader(config_dir)
    loader.load_all()
    return loader
