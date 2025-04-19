# Two Player Snake Game

一个使用 Kivy 开发的双人贪食蛇游戏，支持桌面和移动平台，并具有多人在线功能。

## 功能特点

- 多人在线对战
- 经典的贪食蛇玩法
- 碰撞检测
- 屏幕环绕效果
- 动态速度调整
- 独立的蛇移动控制
- 计分和计时系统
- 游戏结束界面

## 安装方法

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/two_player_snake.git
cd two_player_snake
```

2. 安装依赖：
```bash
pip install -r config/requirements.txt
```

## 游戏控制

### 玩家1（绿色蛇）
- W: 向上移动
- S: 向下移动
- A: 向左移动
- D: 向右移动

### 玩家2（蓝色蛇）
- ↑: 向上移动
- ↓: 向下移动
- ←: 向左移动
- →: 向右移动

## 游戏规则

1. 每个玩家控制一条蛇
2. 吃到红色食物会使蛇变长并增加10分
3. 撞到自己、对方的蛇身或障碍物会输掉游戏
4. 蛇可以穿过屏幕边界（环绕效果）
5. 游戏时间越长，会出现更多障碍物
6. 蛇越长，移动速度越快

## 多人游戏设置

要使用多人游戏功能，请按照以下步骤操作：

### 启动服务器

1. 确保您已安装所有依赖项并在项目目录中。
2. 启动服务器：
```bash
./venv/bin/python3 src/server.py --host 0.0.0.0 --port 7001 --debug
```
3. 服务器将开始监听端口 7001，等待客户端连接。

### 连接客户端

1. 启动游戏客户端：
```bash
python src/main.py
```
2. 输入服务器的 IP 地址和端口（例如，`0.0.0.0:7001`）以连接到服务器。
3. 一旦连接成功，您将能够与其他玩家进行多人游戏。

确保所有玩家都连接到同一服务器以进行游戏匹配。

## 运行游戏

```bash
python src/main.py
```

## 项目结构

```
two_player_snake/
├── src/
│   ├── __init__.py
│   ├── main.py        # 主游戏逻辑
│   ├── client_game.py # 客户端游戏逻辑
│   ├── server.py      # 服务器逻辑
│   ├── snake.kv       # Kivy UI 定义
│   ├── snake.py       # 蛇类定义
│   ├── config_manager.py # 配置管理
│   ├── config.ini     # 配置文件
│   └── sounds/        # 游戏音效
│       ├── eat.wav    # 吃食物音效
│       └── collision.wav # 碰撞音效
├── docs/              # 文档
│   ├── README.md
│   └── chat.md
├── assets/            # 资源文件
│   └── 2025-03-08 15.26.17.png
├── config/            # 配置文件
│   ├── buildozer.spec # 移动应用构建配置
│   ├── setup.py
│   └── requirements.txt
├── tests/             # 测试文件
├── venv/              # 虚拟环境
└── .gitignore
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 通信协议

多人贪食蛇游戏使用自定义的通信协议来管理客户端和服务器之间的交互。以下是协议的详细说明：

### 消息类型
- `JOIN`: 玩家加入游戏。
- `LEAVE`: 玩家离开游戏。
- `GAME_STATE`: 游戏状态更新。
- `MOVE`: 移动指令。
- `START`: 游戏开始。
- `END`: 游戏结束。
- `HEARTBEAT`: 心跳检测，确保连接活跃。
- `ERROR`: 错误信息。

### GameMessage 类
- 负责在客户端和服务器之间创建和解析消息。
- 将消息转换为 JSON 格式进行传输。

### GameServer 类
- 管理客户端连接和游戏逻辑。
- 处理传入的消息并相应地更新游戏状态。
- 向客户端发送消息以更新游戏事件。

### GameClient 类
- 管理与服务器的连接。
- 向服务器发送和接收消息。
- 处理游戏状态更新和用户输入。

### 心跳机制
- 定期发送心跳消息以确保连接活跃。
- 如果心跳消息失败，则移除非活动客户端。

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
    "type": "move",
    "data": {"direction": [1, 0]},
    "player_id": "player-uuid"
  }
  ```