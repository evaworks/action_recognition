# 动作识别系统

基于 YOLOv11-Pose 的实时动作识别系统，通过摄像头实时检测人体姿态动作，并通过 MQTT 协议发送动作指令。

## 功能特性

- 实时姿态检测：使用 YOLOv11-Pose 模型进行人体关键点检测
- 多动作识别：支持自定义动作配置，可同时识别多个动作
- MQTT 通信：支持通过 MQTT 协议发送动作消息和接收配置命令
- 动态配置：支持运行时动态添加、删除、重新加载动作配置
- 跨平台支持：支持 Windows、macOS、Linux，支持 CUDA、Apple GPU、CPU

## 目录结构

```
action_recognition/
├── main.py                 # 主程序入口
├── requirements.txt        # 项目依赖
├── .gitignore            # Git 忽略配置
│
├── src/                   # 源代码目录
│   ├── pose_camera.py     # 摄像头姿态识别主类
│   ├── config_loader.py   # 配置文件加载器
│   ├── keypoint_parser.py # 关键点解析器
│   ├── condition_engine.py# 条件引擎
│   ├── action_detector.py # 动作检测器
│   ├── mqtt_client.py     # MQTT 客户端
│   ├── message_sender.py  # 消息发送器
│   └── __init__.py
│
├── config/                # 配置文件目录
│   ├── actions.yaml       # 动作配置
│   ├── keypoints.yaml    # 关键点配置
│   └── mqtt.yaml         # MQTT 配置
│
├── models/                # 模型文件目录
│   ├── yolo11n-pose.pt   # Nano 模型
│   ├── yolo11s-pose.pt   # Small 模型
│   └── yolo11m-pose.pt   # Medium 模型
│
└── docs/                  # 文档目录
    └── MQTT_PROTOCOL.md  # MQTT 协议文档
```

## 环境配置

### 依赖

- Python 3.8+
- ultralytics >= 8.0.0
- opencv-python >= 4.8.0
- numpy >= 1.24.0
- PyYAML >= 6.0
- paho-mqtt >= 1.6.0

### 安装依赖

```bash
pip install -r requirements.txt
```

### 模型说明

项目提供三种模型选择：

| 模型 | 大小 | 速度 | 精度 |
|-----|------|------|------|
| yolo11n-pose.pt | ~50MB | 最快 | 较低 |
| yolo11s-pose.pt | ~100MB | 较快 | 中等 |
| yolo11m-pose.pt | ~300MB | 较慢 | 较高 |

默认使用 `yolo11s-pose.pt`。

## 使用方法

### 基本用法

```bash
# 使用默认配置运行
python main.py

# 指定模型
python main.py --model models/yolo11m-pose.pt

# 指定摄像头索引
python main.py --camera 0

# 开启调试模式
python main.py --debug
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|-----|------|-------|
| --model | YOLO 模型路径 | models/yolo11s-pose.pt |
| --config | 配置文件目录 | config |
| --camera | 摄像头索引 | 0 |
| --debug | 显示调试信息 | False |
| --hidden | 隐藏窗口后台运行 | False |

### 后台运行 (Windows)

```bash
python main.py --hidden
```

## 动作配置

### 配置格式

编辑 `config/actions.yaml` 文件：

```yaml
actions:
  动作名称:
    name: "动作中文名"
    trigger_cmd: "TRIGGER_CMD"
    description: "动作描述"
    conditions:
      - type: "position"          # 条件类型
        keypoint: "right_wrist"  # 关键点
        relation: "above"        # 关系
        target: "right_shoulder" # 目标关键点
        threshold: -30          # 阈值
    duration: 0.0                # 持续时间
    cooldown: 1.0               # 冷却时间
```

### 条件类型

#### 1. position（位置关系）

判断关键点相对于目标点的位置关系。

```yaml
- type: "position"
  keypoint: "right_wrist"
  relation: "above"        # above/below/left_of/right_of
  target: "right_shoulder"
  threshold: 0             # 偏移量
```

#### 2. angle（角度）

判断关键点的角度。

```yaml
- type: "angle"
  keypoint: "left_knee"
  angle: "<"               # < / > / <= / >=
  threshold: 120          # 度数
```

#### 3. distance（距离）

判断两个关键点之间的距离。

```yaml
- type: "distance"
  point1: "left_wrist"
  point2: "right_wrist"
  relation: ">"
  threshold: 100          # 像素
```

### 预置动作

系统内置 6 个常用动作：

| 动作名称 | 触发指令 | 说明 |
|---------|----------|------|
| 站姿防护 | STAND_GUARD | 站立姿势双手举起防护头部 |
| 倒地防护 | FALL_GUARD | 深蹲下双手抱头 |
| 举起双手 | RAISE_BOTH_HANDS | 双手同时举起高于肩膀 |
| 下蹲防护 | SQUAT_GUARD | 蹲下姿势 |
| 举起右手 | RAISE_RIGHT_HAND | 右手腕高于右肩膀 |
| 举起左手 | RAISE_LEFT_HAND | 左手腕高于左肩膀 |

## MQTT 配置

编辑 `config/mqtt.yaml` 文件：

```yaml
mqtt:
  broker: "192.168.0.89"
  port: 1883
  username: ""
  password: ""
  client_id: "action_recognition"
  qos: 1
  
  reconnect:
    enabled: true
    interval: 5
    max_retries: 10
  
  heartbeat:
    enabled: true
    interval: 30
  
  response:
    topic: "action/{device_id}/response"
  
  config_topic: "action/config"
  
  device:
    device_id: "SN123456789"
```

详细协议说明请参阅 [MQTT_PROTOCOL.md](docs/MQTT_PROTOCOL.md)。

## 动态配置

系统支持通过 MQTT 动态配置：

### 查询所有动作

```json
{
  "command": "list",
  "device_id": "SN123456789"
}
```

### 重新加载配置

```json
{
  "command": "reload",
  "device_id": "SN123456789"
}
```

### 添加动作

```json
{
  "command": "add_action",
  "device_id": "SN123456789",
  "action_name": "wave_hand",
  "config": {
    "name": "挥手",
    "trigger_cmd": "WAVE_HAND",
    "description": "右手左右挥动",
    "conditions": [
      {
        "type": "position",
        "keypoint": "right_wrist",
        "relation": "above",
        "target": "right_shoulder",
        "threshold": -30
      }
    ],
    "duration": 0.0,
    "cooldown": 1.0
  }
}
```

### 删除动作

```json
{
  "command": "remove_action",
  "device_id": "SN123456789",
  "action_name": "wave_hand"
}
```

## 关键点说明

YOLOv11-Pose 使用 COCO 17 关键点格式：

| 索引 | 名称 | 说明 |
|-----|------|------|
| 0 | nose | 鼻子 |
| 1 | left_eye | 左眼 |
| 2 | right_eye | 右眼 |
| 3 | left_ear | 左耳 |
| 4 | right_ear | 右耳 |
| 5 | left_shoulder | 左肩膀 |
| 6 | right_shoulder | 右肩膀 |
| 7 | left_elbow | 左手肘 |
| 8 | right_elbow | 右手肘 |
| 9 | left_wrist | 左手腕 |
| 10 | right_wrist | 右手腕 |
| 11 | left_hip | 左臀部 |
| 12 | right_hip | 右臀部 |
| 13 | left_knee | 左膝盖 |
| 14 | right_knee | 右膝盖 |
| 15 | left_ankle | 左脚踝 |
| 16 | right_ankle | 右脚踝 |

## 开发说明

### 项目结构

- `src/pose_camera.py`: 主程序类，负责协调各模块
- `src/config_loader.py`: 配置加载，支持 YAML 格式
- `src/keypoint_parser.py`: 关键点解析
- `src/condition_engine.py`: 条件评估引擎
- `src/action_detector.py`: 动作检测器
- `src/mqtt_client.py`: MQTT 客户端封装
- `src/message_sender.py`: 消息发送器

## 许可证

MIT License