# MQTT 消息协议文档

## 1. 概述

本文档描述了动作识别系统与前端/技术人员之间通过MQTT协议进行通信的消息格式和接口定义。

### 1.1 协议特点

- **消息格式**: JSON
- **传输协议**: MQTT v3.1.1
- **QoS等级**: 1（至少一次投递）
- **字符编码**: UTF-8

---

## 2. MQTT 配置

### 2.1 配置文件位置

```
config/mqtt.yaml
```

### 2.2 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| mqtt.broker | string | localhost | MQTT服务器地址 |
| mqtt.port | int | 1883 | MQTT服务器端口 |
| mqtt.username | string | "" | 用户名（可选） |
| mqtt.password | string | "" | 密码（可选） |
| mqtt.client_id | string | action_recognition | 客户端ID |
| mqtt.qos | int | 1 | QoS等级 |
| mqtt.reconnect.enabled | bool | true | 是否启用自动重连 |
| mqtt.reconnect.interval | int | 5 | 重连间隔（秒） |
| mqtt.reconnect.max_retries | int | 10 | 最大重连次数，-1表示无限 |
| mqtt.heartbeat.enabled | bool | true | 是否启用心跳 |
| mqtt.heartbeat.interval | int | 30 | 心跳间隔（秒） |
| mqtt.response.topic | string | action/{device_id}/response | 统一消息Topic |
| mqtt.config_topic | string | action/config | 配置命令Topic（设备订阅） |
| mqtt.device.device_id | string | SN123456789 | 设备唯一SN码 |

### 2.3 配置示例

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

**注意**: `{device_id}` 占位符会自动替换为设备SN码

---

## 3. Topic设计

### 3.1 统一消息Topic

所有设备发送的消息（动作、心跳、响应）都通过统一的Topic发送：

| 消息类型 | 发送方 | 接收方 | Topic |
|---------|-------|-------|-------|
| 统一消息 | 设备 | 前端/技术人员 | `action/{sn}/response` |
| 配置命令 | 技术人员 | 设备 | `action/config` |

### 3.2 消息类型（type字段）

通过消息中的 `type` 字段区分消息类型：

| type值 | 说明 |
|-------|------|
| `action` | 动作消息 |
| `heartbeat` | 心跳消息 |
| `response` | 命令响应 |

### 3.3 多设备示例

假设有3台设备，SN分别为 `SN001`、`SN002`、`SN003`：

| 设备SN | Topic |
|--------|-------|
| SN001 | action/SN001/response |
| SN002 | action/SN002/response |
| SN003 | action/SN003/response |

### 3.4 订阅示例

```javascript
// 订阅所有设备的统一消息（动作、心跳、响应）
client.subscribe('action/+/response');

// 订阅特定设备
client.subscribe('action/SN123456789/response');

// 技术人员发送配置命令
client.publish('action/config', JSON.stringify(cmd));
```

---

## 4. 统一消息格式

所有设备发送的消息都使用以下统一格式：

```json
{
  "type": "action" | "heartbeat" | "response",
  "device_id": "SN123456789",
  "timestamp": "2026-03-02 14:30:00",
  "data": { ... }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | 消息类型：action/heartbeat/response |
| device_id | string | 是 | 设备SN码 |
| timestamp | string | 是 | 时间戳（格式：YYYY-MM-DD HH:MM:SS） |
| data | object | 是 | 消息数据 |

---

## 5. 具体消息格式

### 5.1 动作消息 (type: action)

设备检测到动作时发送。

**Topic**: `action/{sn}/response`

```json
{
  "type": "action",
  "device_id": "SN123456789",
  "device_id": "SN123456789",
  "timestamp": "2026-03-02 14:30:00",
  "data": {
    "action": "RAISE_RIGHT_HAND",
    "action_name": "举起右手",
    "confidence": 1.0
  }
}
```

**data字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| action | string | 动作指令 |
| action_name | string | 动作中文名称 |
| confidence | float | 置信度（0.0-1.0） |

---

### 5.2 心跳消息 (type: heartbeat)

设备定期发送的心跳消息。

**Topic**: `action/{sn}/response`

```json
{
  "type": "heartbeat",
  "device_id": "SN123456789",
  "device_id": "SN123456789",
  "timestamp": "2026-03-02 14:30:00",
  "data": {}
}
```

---

### 5.3 命令响应 (type: response)

设备响应配置命令。

**Topic**: `action/{sn}/response`

```json
{
  "type": "response",
  "device_id": "SN123456789",
  "device_id": "SN123456789",
  "timestamp": "2026-03-02 14:30:00",
  "data": {
    "command": "list",
    "success": true,
    "message": "成功",
    "actions": [...]
  }
}
```

**data字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| command | string | 命令类型 |
| success | bool | 是否成功 |
| message | string | 响应消息 |
| actions | array | 动作列表（list命令时） |

---

## 6. 配置命令

技术人员通过MQTT发送配置命令。

### 6.1 命令Topic

**Topic**: `action/config`

### 6.2 命令格式

#### 6.2.1 查询所有动作 (list)

```json
{
  "command": "list",
  "device_id": "SN123456789"
}
```

#### 6.2.2 重新加载配置 (reload)

```json
{
  "command": "reload",
  "device_id": "SN123456789"
}
```

#### 6.2.3 添加动作 (add_action)

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

#### 6.2.4 删除动作 (remove_action)

```json
{
  "command": "remove_action",
  "device_id": "SN123456789",
  "action_name": "wave_hand"
}
```

---

## 7. 命令响应示例

### 7.1 list 响应

```json
{
  "type": "response",
  "device_id": "SN123456789",
  "device_id": "SN123456789",
  "timestamp": "2026-03-02 14:30:00",
  "data": {
    "command": "list",
    "success": true,
    "message": "成功",
    "actions": [
      {
        "name": "stand_guard",
        "config": {
          "trigger_cmd": "STAND_GUARD",
          "name": "站姿防护",
          "duration": 0.0,
          "cooldown": 1.0
        }
      },
      {
        "name": "raise_right_hand",
        "config": {
          "trigger_cmd": "RAISE_RIGHT_HAND",
          "name": "举起右手",
          "duration": 0.0,
          "cooldown": 1.0
        }
      }
    ]
  }
}
```

### 7.2 add_action 响应

```json
{
  "type": "response",
  "device_id": "SN123456789",
  "device_id": "SN123456789",
  "timestamp": "2026-03-02 14:30:00",
  "data": {
    "command": "add_action",
    "success": true,
    "message": "添加动作成功: wave_hand"
  }
}
```

### 7.3 remove_action 响应

```json
{
  "type": "response",
  "device_id": "SN123456789",
  "device_id": "SN123456789",
  "timestamp": "2026-03-02 14:30:00",
  "data": {
    "command": "remove_action",
    "success": true,
    "message": "删除动作成功: wave_hand"
  }
}
```

### 7.4 reload 响应

```json
{
  "type": "response",
  "device_id": "SN123456789",
  "device_id": "SN123456789",
  "timestamp": "2026-03-02 14:30:00",
  "data": {
    "command": "reload",
    "success": true,
    "message": "已重新加载配置，当前 6 个动作"
  }
}
```

---

## 8. 完整通信流程

```
┌────────────────┐                              ┌────────────────┐
│   技术人员     │                              │     设备       │
│   (前端应用)   │                              │                │
│                │                              │ subscribe:     │
│  subscribe:    │                              │ action/config  │
│  action/+/    │                              └───────┬────────┘
│  response     │                                      │
└───────┬──────┘                                      │
        │                                             │
        │  PUBLISH                                    │
        │  Topic: action/config                       │
        │  Payload: {"command":"list",...}           │
        ├──────────────────────────────────────────► │
        │                                             │
        │  PUBLISH                                    │
        │  Topic: action/SN123456789/response        │
        │  Payload: {"type":"response",...}          │
        │◄───────────────────────────────────────────┤
        │                                             │
        │ (设备检测到动作)                            │
        │  PUBLISH                                    │
        │  Topic: action/SN123456789/response        │
        │  Payload: {"type":"action",...}           │
        │◄───────────────────────────────────────────┤
        │                                             │
        │ (设备定时心跳)                              │
        │  PUBLISH                                    │
        │  Topic: action/SN123456789/response        │
        │  Payload: {"type":"heartbeat",...}        │
        │◄───────────────────────────────────────────┤
```

---

## 9. 动作指令表

| 指令 | 动作名称 | 说明 |
|------|----------|------|
| STAND_GUARD | 站姿防护 | 站立姿势双手举起防护头部 |
| RAISE_BOTH_HANDS | 举起双手 | 双手同时举起高于肩膀 |
| FALL_GUARD | 倒地防护 | 完全蹲下（膝盖弯曲90度以内） |
| SQUAT_GUARD | 下蹲防护 | 半蹲姿势（膝盖弯曲120度以内） |
| RAISE_RIGHT_HAND | 举起右手 | 右手腕高于右肩膀 |
| RAISE_LEFT_HAND | 举起左手 | 左手腕高于左肩膀 |

---

## 10. 条件类型说明

### 10.1 position（位置关系）

判断关键点相对于目标点的位置关系。

| 参数 | 说明 |
|------|------|
| keypoint | 关键点名称 |
| relation | 关系：above/below/left_of/right_of |
| target | 目标关键点 |
| threshold | 阈值（像素） |

### 10.2 angle（角度）

判断关键点的角度。

| 参数 | 说明 |
|------|------|
| keypoint | 关键点名称 |
| angle | 比较符：< / > / <= / >= |
| threshold | 阈值（度数） |

### 10.3 distance（距离）

判断两个关键点之间的距离。

| 参数 | 说明 |
|------|------|
| point1 | 关键点1 |
| point2 | 关键点2 |
| relation | 比较符：< / > / <= / >= |
| threshold | 阈值（像素） |

---

## 11. 使用示例

### 11.1 技术人员发送命令（Python）

```python
import paho.mqtt.client as mqtt
import json

def on_connect(client, userdata, flags, rc):
    print("Connected")
    # 订阅响应
    client.subscribe("action/+/response")
    # 发送list命令
    cmd = {"command": "list", "device_id": "SN123456789"}
    client.publish("action/config", json.dumps(cmd))

def on_message(client, userdata, msg):
    print(f"Topic: {msg.topic}")
    data = json.loads(msg.payload)
    print(f"Type: {data.get('type')}")
    print(f"Data: {data.get('data')}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("192.168.0.89", 1883, 60)
client.loop_forever()
```

### 11.2 技术人员发送命令（命令行）

```bash
# 查询所有动作
mosquitto_pub -t action/config -m '{"command": "list", "device_id": "SN123456789"}'

# 重新加载配置
mosquitto_pub -t action/config -m '{"command": "reload", "device_id": "SN123456789"}'

# 添加新动作
mosquitto_pub -t action/config -m '{
  "command": "add_action",
  "device_id": "SN123456789",
  "action_name": "test_action",
  "config": {
    "name": "测试动作",
    "trigger_cmd": "TEST_ACTION",
    "conditions": [{"type": "position", "keypoint": "right_wrist", "relation": "above", "target": "nose", "threshold": 0}],
    "duration": 0.0,
    "cooldown": 1.0
  }
}'

# 删除动作
mosquitto_pub -t action/config -m '{"command": "remove_action", "device_id": "SN123456789", "action_name": "test_action"}'
```

---

## 12. 故障排除

### 12.1 连接失败

1. 检查MQTT服务器是否运行
2. 检查broker地址和端口配置
3. 检查用户名和密码（如需要）
4. 检查网络连通性

### 12.2 消息发送失败

1. 检查MQTT连接状态
2. 检查topic配置是否正确
3. 查看日志中的错误信息

### 12.3 心跳不发送

1. 确认heartbeat.enabled设置为true
2. 检查MQTT连接是否成功建立

### 12.4 配置命令无响应

1. 确认订阅了正确的topic
2. 检查命令格式是否正确（device_id是否匹配）
3. 查看设备日志

---

## 13. 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-03-02 | 初始版本 |
| v1.1 | 2026-03-02 | 添加多设备支持和热加载配置 |
| v2.0 | 2026-03-02 | 统一消息格式，移除device_name |

---

## 14. 当前支持的条件类型

### 14.1 无需修改代码即可使用

通过MQTT添加新动作时，以下条件类型可以直接在YAML配置中使用：

| 类型 | 说明 | 示例 |
|------|------|------|
| `position` | 位置关系 | 右手腕高于右肩膀 |
| `angle` | 角度计算 | 膝盖角度 < 90° |
| `distance` | 距离计算 | 两手距离 > 100px |

### 14.2 预置动作（无需配置）

系统已内置6个常用动作：

| 动作 | 触发指令 | 条件 |
|------|----------|------|
| 站姿防护 | STAND_GUARD | 双手高于鼻子 |
| 举起双手 | RAISE_BOTH_HANDS | 双手高于肩膀 |
| 倒地防护 | FALL_GUARD | 膝盖角度 < 90° |
| 下蹲防护 | SQUAT_GUARD | 膝盖角度 < 120° |
| 举起右手 | RAISE_RIGHT_HAND | 右手腕高于右肩膀 |
| 举起左手 | RAISE_LEFT_HAND | 左手腕高于左肩膀 |

### 14.3 需要修改代码的情况

如果需要添加全新的检测逻辑（如手势识别、速度检测），需要修改 `condition_engine.py`：

| 新增功能 | 修改文件 | 说明 |
|---------|---------|------|
| 新条件类型 | condition_engine.py | 添加新的 evaluate_xxx 方法 |
| 新检测模型 | keypoint_parser.py | 添加新的解析逻辑 |
