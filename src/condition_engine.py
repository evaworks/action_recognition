"""条件引擎模块"""
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from .keypoint_parser import KeypointParser


class ConditionEngine:
    """条件评估引擎，负责评估各种动作条件"""
    
    def __init__(self, keypoint_parser: KeypointParser):
        self.keypoint_parser = keypoint_parser
        self.reference_values: Dict[str, float] = {}
        
    def evaluate(self, keypoints: Dict[str, Tuple[float, float, float]], 
                 conditions: List[Dict[str, Any]]) -> bool:
        """
        评估所有条件是否满足
        
        Args:
            keypoints: 关键点字典
            conditions: 条件列表
            
        Returns:
            所有条件是否都满足
        """
        if not conditions:
            return True
            
        for condition in conditions:
            if not self._evaluate_single(keypoints, condition):
                return False
        return True
    
    def _evaluate_single(self, keypoints: Dict[str, Tuple[float, float, float]], 
                        condition: Dict[str, Any]) -> bool:
        """评估单个条件"""
        condition_type = condition.get('type')
        
        if condition_type == 'position':
            return self._evaluate_position(keypoints, condition)
        elif condition_type == 'height_ratio':
            return self._evaluate_height_ratio(keypoints, condition)
        elif condition_type == 'angle':
            return self._evaluate_angle(keypoints, condition)
        elif condition_type == 'distance':
            return self._evaluate_distance(keypoints, condition)
        
        return False
    
    def _evaluate_position(self, keypoints: Dict[str, Tuple[float, float, float]], 
                          condition: Dict[str, Any]) -> bool:
        """
        评估位置关系条件
        
        支持的关系:
        - above: keypoint在target上方（y坐标更小）
        - below: keypoint在target下方（y坐标更大）
        - left_of: keypoint在target左侧（x坐标更小）
        - right_of: keypoint在target右侧（x坐标更大）
        """
        keypoint = condition.get('keypoint')
        target = condition.get('target')
        relation = condition.get('relation')
        threshold = condition.get('threshold', 0)
        
        kp1 = self.keypoint_parser.get_keypoint(keypoints, keypoint)
        kp2 = self.keypoint_parser.get_keypoint(keypoints, target)
        
        if not kp1 or not kp2:
            return False
        
        if relation == 'above':
            return (kp1[1] + threshold) < kp2[1]
        elif relation == 'below':
            return (kp1[1] - threshold) > kp2[1]
        elif relation == 'left_of':
            return (kp1[0] + threshold) < kp2[0]
        elif relation == 'right_of':
            return (kp1[0] - threshold) > kp2[0]
        
        return False
    
    def _evaluate_height_ratio(self, keypoints: Dict[str, Tuple[float, float, float]], 
                               condition: Dict[str, Any]) -> bool:
        """
        评估高度比例条件
        
        例如：当前臀部高度 / 参考臀部高度 < 0.6
        """
        keypoint = condition.get('keypoint')
        reference = condition.get('reference')
        ratio = condition.get('ratio', 1.0)
        
        kp = self.keypoint_parser.get_keypoint(keypoints, keypoint)
        if not kp:
            return False
        
        if reference == 'standing_hip':
            ref_value = self.get_reference('standing_hip_y', kp[1])
            if ref_value is None:
                return False
            current_ratio = kp[1] / ref_value
            return current_ratio < ratio
        
        return False
    
    def _evaluate_angle(self, keypoints: Dict[str, Tuple[float, float, float]], 
                       condition: Dict[str, Any]) -> bool:
        """评估角度条件"""
        keypoint = condition.get('keypoint')
        angle_op = condition.get('angle')
        threshold = condition.get('threshold', 180)
        
        if keypoint == 'left_knee':
            angle = self.keypoint_parser.calculate_angle(
                keypoints, 'left_hip', 'left_knee', 'left_ankle'
            )
        elif keypoint == 'right_knee':
            angle = self.keypoint_parser.calculate_angle(
                keypoints, 'right_hip', 'right_knee', 'right_ankle'
            )
        elif keypoint == 'left_elbow':
            angle = self.keypoint_parser.calculate_angle(
                keypoints, 'left_shoulder', 'left_elbow', 'left_wrist'
            )
        elif keypoint == 'right_elbow':
            angle = self.keypoint_parser.calculate_angle(
                keypoints, 'right_shoulder', 'right_elbow', 'right_wrist'
            )
        elif keypoint == 'left_hip':
            angle = self.keypoint_parser.calculate_angle(
                keypoints, 'left_shoulder', 'left_hip', 'left_knee'
            )
        elif keypoint == 'right_hip':
            angle = self.keypoint_parser.calculate_angle(
                keypoints, 'right_shoulder', 'right_hip', 'right_knee'
            )
        else:
            return False
        
        if angle_op == '<':
            return angle < threshold
        elif angle_op == '>':
            return angle > threshold
        elif angle_op == '<=':
            return angle <= threshold
        elif angle_op == '>=':
            return angle >= threshold
        
        return False
    
    def _evaluate_distance(self, keypoints: Dict[str, Tuple[float, float, float]], 
                          condition: Dict[str, Any]) -> bool:
        """评估距离条件"""
        point1 = condition.get('point1')
        point2 = condition.get('point2')
        relation = condition.get('relation')
        threshold = condition.get('threshold', 0)
        
        distance = self.keypoint_parser.calculate_distance(keypoints, point1, point2)
        
        if relation == '>':
            return distance > threshold
        elif relation == '<':
            return distance < threshold
        elif relation == '>=':
            return distance >= threshold
        elif relation == '<=':
            return distance <= threshold
        
        return False
    
    def update_references(self, keypoints: Dict[str, Tuple[float, float, float]]) -> None:
        """更新参考值，用于比例计算"""
        hip_center = self.keypoint_parser.get_keypoint(keypoints, 'hip_center')
        if hip_center and hip_center[2] > 0.5:
            self.reference_values['standing_hip_y'] = hip_center[1]
    
    def get_reference(self, name: str, default: float = None) -> Optional[float]:
        """获取参考值"""
        return self.reference_values.get(name, default)
    
    def reset_references(self) -> None:
        """重置参考值"""
        self.reference_values.clear()
