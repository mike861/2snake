## 通信协议

多人贪食蛇游戏使用自定义的通信协议来管理客户端和服务器之间的交互。以下是协议的详细说明，基于 `network.py` 中的实现。

### 消息类型

#### 1. `JOIN`
- **示例数据**:
  ```json
  { "type": "JOIN", "player_id": "player-uuid", "player_name": "Player1" }
  ```
- **字段说明**:
  - `type`: 消息类型，表示加入游戏的请求
  - `player_id`: 玩家唯一标识符
  - `player_name`: 玩家名称

---

#### 2. `LEAVE`
- **示例数据**:
  ```json
  { "type": "LEAVE", "player_id": "player-uuid" }
  ```
- **字段说明**:
  - `type`: 消息类型，表示玩家离开游戏的请求
  - `player_id`: 玩家唯一标识符

---

#### 3. `GAME_STATE`
- **示例数据**:
  ```json
  { 
    "type": "GAME_STATE", 
    "state": { 
      "players": [ 
        { "id": "player-uuid", "position": [5, 5], "score": 10 }, 
        { "id": "another-player-uuid", "position": [3, 4], "score": 15 } 
      ], 
      "food": { "position": [7, 8] }, 
      "status": "running" 
    } 
  }
  ```
- **字段说明**:
  - `type`: 消息类型，表示游戏状态更新
  - `state`: 游戏状态对象
    - `players`: 玩家列表
      - `id`: 玩家唯一标识符
      - `position`: 玩家位置
      - `score`: 玩家得分
    - `food`: 食物位置
      - `position`: 食物位置
    - `status`: 游戏状态

---

#### 4. `MOVE`
- **示例数据**:
  ```json
  { "type": "MOVE", "player_id": "player-uuid", "direction": [1, 0] }
  ```
- **字段说明**:
  - `type`: 消息类型，表示移动指令
  - `player_id`: 玩家唯一标识符
  - `direction`: 移动方向（数组，x和y的增量）

---

#### 5. `START`
- **示例数据**:
  ```json
  { "type": "START", "game_id": "game-uuid" }
  ```
- **字段说明**:
  - `type`: 消息类型，表示游戏开始的请求
  - `game_id`: 游戏唯一标识符

---

#### 6. `END`
- **示例数据**:
  ```json
  { 
    "type": "END", 
    "winner_id": "player-uuid", 
    "final_scores": { "player-uuid": 20, "another-player-uuid": 15 } 
  }
  ```
- **字段说明**:
  - `type`: 消息类型，表示游戏结束的通知
  - `winner_id`: 胜利者的玩家唯一标识符
  - `final_scores`: 最终得分

---

#### 7. `HEARTBEAT`
- **示例数据**:
  ```json
  { "type": "HEARTBEAT", "player_id": "player-uuid" }
  ```
- **字段说明**:
  - `type`: 消息类型，表示心跳检测
  - `player_id`: 玩家唯一标识符

---

#### 8. `ERROR`
- **示例数据**:
  ```json
  { "type": "ERROR", "message": "Player not found" }
  ```
- **字段说明**:
  - `type`: 消息类型，表示错误信息
  - `message`: 错误描述

---

### 实现来源

所有消息类型的具体实现和处理逻辑可以在 `network.py` 文件中找到。该文件负责管理客户端与服务器之间的通信，包括消息的发送、接收和解析。

### 示例用法

- **启动服务器**：
  ```bash
  ./venv/bin/python3 src/server.py --host 0.0.0.0 --port 7001 --debug
  ```

- **连接客户端**：
  ```bash
  python src/main.py
  ```

- **发送移动指令**：
  客户端发送带有方向数据的移动指令：
  ```json
  {
    "type": "MOVE",
    "data": {"direction": [1, 0]},
    "player_id": "player-uuid"
  }
  ``` 