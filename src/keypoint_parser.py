"""关键点解析模块"""
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from .config_loader import ConfigLoader


class KeypointParser:
    """关键点解析器，从YOLO输出中提取和计算关键点"""
    
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.keypoints_map = config_loader.keypoints
        self.composite_keypoints = config_loader.composite_keypoints
        
    def parse(self, yolo_keypoints: np.ndarray) -> Dict[str, Tuple[float, float, float]]:
        """
        解析YOLO输出的关键点
        
        Args:
            yolo_keypoints: YOLO模型输出的关键点数据，shape为(17, 3)，包含[x, y, confidence]
            
        Returns:
            关键点字典，key为关键点名称，value为(x, y, confidence)元组
        """
        keypoints = {}
        
        for name, index in self.keypoints_map.items():
            if index < len(yolo_keypoints):
                kp = yolo_keypoints[index]
                keypoints[name] = (float(kp[0]), float(kp[1]), float(kp[2]))
        
        self._compute_composite_keypoints(keypoints)
        
        return keypoints
    
    def _compute_composite_keypoints(self, keypoints: Dict[str, Tuple[float, float, float]]) -> None:
        """
        计算复合关键点
        
        Args:
            keypoints: 基础关键点字典，会被原地修改添加复合关键点
        """
        for comp_name, comp_config in self.composite_keypoints.items():
            if len(comp_config) >= 2:
                kp1_name = comp_config[0]
                kp2_name = comp_config[1]
                
                if kp1_name in keypoints and kp2_name in keypoints:
                    kp1 = keypoints[kp1_name]
                    kp2 = keypoints[kp2_name]
                    
                    if comp_config[2] == 'center':
                        cx = (kp1[0] + kp2[0]) / 2
                        cy = (kp1[1] + kp2[1]) / 2
                        conf = (kp1[2] + kp2[2]) / 2
                        keypoints[comp_name] = (cx, cy, conf)
    
    def get_keypoint(self, keypoints: Dict[str, Tuple[float, float, float]], 
                     keypoint_name: str) -> Optional[Tuple[float, float, float]]:
        """
        获取指定关键点的坐标
        
        Args:
            keypoints: 关键点字典
            keypoint_name: 关键点名称
            
        Returns:
            (x, y, confidence)或None
        """
        return keypoints.get(keypoint_name)
    
    def get_confidence(self, keypoints: Dict[str, Tuple[float, float, float]], 
                       keypoint_name: str) -> float:
        """获取关键点的置信度"""
        kp = self.get_keypoint(keypoints, keypoint_name)
        return kp[2] if kp else 0.0
    
    def is_valid_pose(self, keypoints: Dict[str, Tuple[float, float, float]], 
                      min_confidence: float = 0.3) -> bool:
        """
        检查姿态是否有效
        
        Args:
            keypoints: 关键点字典
            min_confidence: 最小置信度阈值
            
        Returns:
            姿态是否有效
        """
        required_keypoints = ['left_shoulder', 'right_shoulder', 
                              'left_hip', 'right_hip']
        
        for name in required_keypoints:
            kp = self.get_keypoint(keypoints, name)
            if kp is None or kp[2] < min_confidence:
                return False
        
        return True
    
    def calculate_angle(self, keypoints: Dict[str, Tuple[float, float, float]],
                        point1: str, vertex: str, point2: str) -> float:
        """
        计算三个点形成的角度
        
        Args:
            keypoints: 关键点字典
            point1: 端点1
            vertex: 顶点（角度所在点）
            point2: 端点2
            
        Returns:
            角度（度数）
        """
        p1 = self.get_keypoint(keypoints, point1)
        v = self.get_keypoint(keypoints, vertex)
        p2 = self.get_keypoint(keypoints, point2)
        
        if not all([p1, v, p2]):
            return 180.0
        
        v1 = np.array([p1[0] - v[0], p1[1] - v[1]])
        v2 = np.array([p2[0] - v[0], p2[1] - v[1]])
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-6)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.arccos(cos_angle) * 180.0 / np.pi
        
        return float(angle)
    
    def calculate_distance(self, keypoints: Dict[str, Tuple[float, float, float]],
                           point1: str, point2: str) -> float:
        """计算两点之间的距离（像素）"""
        p1 = self.get_keypoint(keypoints, point1)
        p2 = self.get_keypoint(keypoints, point2)
        
        if not p1 or not p2:
            return 0.0
        
        return float(np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2))
