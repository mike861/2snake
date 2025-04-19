#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snake Game Server Module
"""

import socket
import threading
import uuid
import time
import random
import logging

from .protocol import GameMessage, DEFAULT_HOST, DEFAULT_PORT, BUFFER_SIZE, HEARTBEAT_INTERVAL

logger = logging.getLogger('Snake.Network.Server')

class GameServer:
    """Game server class, handles client connections and game logic"""
    
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.clients = {}  # {player_id: (conn, addr)}
        self.games = {}    # {game_id: Game}
        self.waiting_players = []  # List of player IDs waiting for matching
        self.game_queue = []  # List of clients waiting for a game
        self.thread = None
        
    def start(self):
        """Start the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)  # Maximum of 5 connections waiting in queue
            self.running = True
            
            logger.warning(f"Server started, listening on {self.host}:{self.port}")
            
            # Start matching thread
            threading.Thread(target=self._match_players, daemon=True).start()
            
            # Start heartbeat checking thread
            threading.Thread(target=self._heartbeat_checker, daemon=True).start()
            
            # Main thread accepts client connections
            self._accept_clients()
        except Exception as e:
            logger.error(f"Server startup failed: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        # Notify all clients of server shutdown
        for player_id, (conn, _) in self.clients.items():
            try:
                self._send_message(conn, GameMessage(GameMessage.ERROR, {'error': 'Server shutting down'}, player_id))
                conn.close()
            except:
                pass
        
        # Close server socket
        if self.socket:
            self.socket.close()
            self.socket = None
            
        logger.warning("Server has stopped")
    
    def _accept_clients(self):
        """Accept client connections"""
        while self.running:
            try:
                conn, addr = self.socket.accept()
                logger.warning(f"New connection: {addr}")
                
                # Create a handling thread for each client
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                if self.running:
                    logger.error(f"Failed to accept connection: {e}")
    
    def _handle_client(self, conn, addr):
        """Process client connection"""
        player_id = None
        
        try:
            # 接收初始消息
            data = conn.recv(BUFFER_SIZE)
            if not data:
                logger.warning(f"Empty data received from {addr}")
                return
            
            # 解析消息
            raw_data = data.decode('utf-8')
            logger.warning(f"Raw data received from client: {raw_data}")
            message = GameMessage.from_json(raw_data)
            
            # 验证初始消息类型
            if message.type == GameMessage.ERROR:
                logger.warning(f"Failed to parse initial message from {addr}")
                conn.close()
                return
                
            # 处理初始消息
            if message.type == GameMessage.CONNECT:
                # 新客户端连接请求
                player_id = str(uuid.uuid4())
                self.clients[player_id] = (conn, addr)
                
                # 发送确认消息
                self._send_message(conn, GameMessage(
                    GameMessage.CONNECT_ACK,
                    {'player_id': player_id, 'status': 'connected'},
                    player_id
                ))
                
                logger.warning(f"Player {player_id} connected from {addr}")
                
                # 继续处理后续消息
                while self.running:
                    try:
                        data = conn.recv(BUFFER_SIZE)
                        if not data:
                            logger.warning(f"Client {player_id} disconnected (empty data)")
                            break
                        
                        message = GameMessage.from_json(data.decode('utf-8'))
                        self._process_message(message, conn)
                    except ConnectionResetError:
                        logger.warning(f"Client {player_id} connection reset")
                        break
                    except Exception as e:
                        logger.error(f"Error handling message from {player_id}: {e}")
                        logger.exception(e)
            else:
                # 意外的消息类型
                logger.warning(f"Unexpected initial message type {message.type} from {addr}")
                conn.close()
                return
        
        except ConnectionResetError:
            logger.warning(f"Client disconnected during handshake: {addr}")
        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
            logger.exception(e)
        finally:
            # 客户端断开连接清理
            if player_id:
                self._handle_client_disconnect(player_id)
            
            try:
                conn.close()
            except:
                pass
            
            logger.warning(f"Connection with {addr} closed")
    
    def _send_message(self, conn, message):
        """Send message to client"""
        try:
            json_data = message.to_json()
            # Add newline as message boundary
            json_data += '\n'
            conn.sendall(json_data.encode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    def _process_message(self, message, conn):
        """Process incoming message"""
        try:
            player_id = message.client_id
            
            # 记录消息信息
            logger.warning(f"Processing message: {message.type} from {player_id}")
            
            # 连接请求
            if message.type == GameMessage.CONNECT:
                # 新客户端连接
                if player_id is None:
                    # 生成新的客户端ID
                    player_id = str(uuid.uuid4())
                    self.clients[player_id] = (conn, conn.getpeername())
                    logger.warning(f"New client connected, assigned ID: {player_id}")
                    
                    # 发送确认消息
                    self._send_message(conn, GameMessage(
                        GameMessage.CONNECT_ACK,
                        {'player_id': player_id, 'status': 'connected'},
                        player_id
                    ))
                    
                    # 添加到等待队列
                    self.waiting_players.append(player_id)
                    logger.warning(f"Player {player_id} added to waiting queue")
                    
                    # 尝试匹配玩家
                    self._match_players()
                    
            # 匹配请求
            elif message.type == GameMessage.MATCH:
                # 客户端请求匹配
                if player_id not in self.waiting_players:
                    self.waiting_players.append(player_id)
                    logger.warning(f"Player {player_id} requested match, added to waiting queue")
                    
                    # 尝试匹配玩家
                    self._match_players()
                    
            # 游戏命令
            elif message.type == GameMessage.COMMAND:
                # 客户端发送的游戏命令
                command_data = message.data
                command_type = command_data.get('command_type')
                game_id = command_data.get('game_id')
                
                logger.warning(f"Received {command_type} command from player {player_id} for game {game_id}")
                logger.warning(f"Command data: {command_data}")
                logger.warning(f"Raw message data: {message.data}")
                
                # 确保游戏存在
                if game_id not in self.games:
                    logger.warning(f"Command for non-existent game: {game_id}")
                    self._send_message(conn, GameMessage(
                        GameMessage.ERROR,
                        {'message': 'Game not found'},
                        player_id
                    ))
                    return
                    
                game = self.games[game_id]
                
                # 确保玩家在该游戏中
                if player_id not in game['players']:
                    logger.warning(f"Player {player_id} not in game {game_id}")
                    self._send_message(conn, GameMessage(
                        GameMessage.ERROR,
                        {'message': 'Not in this game'},
                        player_id
                    ))
                    return
                
                # 获取玩家在游戏中的索引
                player_idx = game['players'].index(player_id)
                
                # 处理不同类型的命令
                result = False
                if command_type == 'direction':
                    # 方向命令
                    direction = command_data.get('direction')
                    logger.warning(f"Direction command from player {player_id} (idx {player_idx}): {direction}")
                    logger.warning(f"Current direction: {game['state']['directions'][player_idx]}")
                    logger.warning(f"Snake position before move: {game['state'][f'snake{player_idx+1}']}")
                    
                    if direction and len(direction) == 2:
                        # 验证方向值是否有效 (-1, 0, 1)
                        dx, dy = direction
                        logger.warning(f"Parsed direction components: dx={dx}, dy={dy}")
                        
                        if dx in [-1, 0, 1] and dy in [-1, 0, 1]:
                            # 更新方向
                            old_direction = game['state']['directions'][player_idx]
                            game['state']['directions'][player_idx] = direction
                            logger.warning(f"Player {player_id} direction updated from {old_direction} to {direction}")
                            logger.warning(f"Direction update successful, new direction set for next move")
                            result = True
                        else:
                            logger.warning(f"Invalid direction values: {direction}, dx={dx}, dy={dy}")
                    else:
                        logger.warning(f"Invalid direction format: {direction}, length={len(direction) if direction else 'None'}")
                else:
                    logger.warning(f"Unknown command type: {command_type}")
                
                # 发送命令确认
                self._send_message(conn, GameMessage(
                    GameMessage.COMMAND_ACK,
                    {
                        'command_type': command_type,
                        'result': result
                    },
                    player_id
                ))
                
                logger.warning(f"Command {command_type} processed, result: {result}")
                
            # 断开连接
            elif message.type == GameMessage.DISCONNECT:
                # 客户端断开连接
                self._handle_client_disconnect(player_id)
                
            # 心跳消息
            elif message.type == GameMessage.HEARTBEAT:
                # 心跳消息，回复相同类型
                self._send_message(conn, GameMessage(
                    GameMessage.HEARTBEAT,
                    {},
                    player_id
                ))
                
            else:
                logger.warning(f"Unhandled message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.exception(e)
    
    def _match_players(self):
        """Match waiting players and start games"""
        # 需要至少两名玩家才能匹配
        if len(self.waiting_players) < 2:
            logger.warning(f"Not enough players to match: {len(self.waiting_players)} waiting")
            return
            
        # 获取前两名等待的玩家
        player1_id = self.waiting_players.pop(0)
        player2_id = self.waiting_players.pop(0)
        
        # 确保两名玩家都仍然连接
        if player1_id not in self.clients or player2_id not in self.clients:
            # 如果有一名玩家断开连接，将另一名玩家放回等待队列
            if player1_id in self.clients:
                self.waiting_players.append(player1_id)
            if player2_id in self.clients:
                self.waiting_players.append(player2_id)
            logger.warning("Player disconnected during matching, returning available player to queue")
            return
            
        # 创建新游戏
        game_id = str(uuid.uuid4())
        logger.warning(f"Matching players {player1_id} and {player2_id} in game {game_id}")
        
        # 初始化游戏状态
        game_state = {
            'players': [player1_id, player2_id],
            'snake1': [[8, 10], [8, 11], [8, 12]],  # 第一名玩家的蛇，初始位置更靠近中央
            'snake2': [[12, 10], [12, 11], [12, 12]],  # 第二名玩家的蛇，初始位置更靠近中央
            'directions': [[0, -1], [0, -1]],  # 蛇的方向：两条蛇都向上移动
            'food': [10, 10],  # 食物位置放在中间
            'scores': [0, 0],  # 玩家分数
            'game_time': 0,  # 游戏时间
            'just_ate': [False, False]  # 是否刚吃到食物
        }
        
        # 创建游戏对象
        game = {
            'id': game_id,
            'players': [player1_id, player2_id],
            'status': 'waiting',  # 游戏状态: waiting, running, finished
            'state': game_state,
            'created_at': time.time()
        }
        
        # 保存游戏
        self.games[game_id] = game
        
        # 发送匹配确认消息给两名玩家
        for i, player_id in enumerate([player1_id, player2_id]):
            if player_id in self.clients:
                try:
                    conn = self.clients[player_id][0]
                    self._send_message(conn, GameMessage(
                        GameMessage.MATCH_ACK,
                        {
                            'game_id': game_id,
                            'player_idx': i,  # 0 或 1
                            'opponent_id': player2_id if i == 0 else player1_id
                        },
                        player_id
                    ))
                    logger.warning(f"Match confirmation sent to player {player_id}")
                except Exception as e:
                    logger.error(f"Error sending match confirmation to player {player_id}: {e}")
                    
        # 稍等片刻，让客户端处理匹配消息
        time.sleep(1.0)
                
        # 发送游戏开始消息
        for i, player_id in enumerate([player1_id, player2_id]):
            if player_id in self.clients:
                try:
                    conn = self.clients[player_id][0]
                    self._send_message(conn, GameMessage(
                        GameMessage.GAME_START,
                        {
                            'game_id': game_id,
                            'player_idx': i,
                            'state': game_state
                        },
                        player_id
                    ))
                    logger.warning(f"Game start message sent to player {player_id}")
                except Exception as e:
                    logger.error(f"Error sending game start to player {player_id}: {e}")
        
        # 启动游戏循环线程
        game_thread = threading.Thread(target=self._game_loop, args=(game_id,))
        game_thread.daemon = True
        game_thread.start()
        logger.warning(f"Game loop started for game {game_id}")
    
    def _game_loop(self, game_id):
        """Game main loop, updates game state and sends to clients"""
        game = self.games.get(game_id)
        if not game:
            return
        
        # Mark game as running
        game['status'] = 'running'
        last_update = time.time()
        move_interval = 0.2  # 修改蛇移动的时间间隔，从0.5秒改为0.2秒移动一次，加快移动速度
        last_move_time = time.time()
        
        # 记录初始游戏状态
        logger.warning(f"Starting game loop for game {game_id}")
        self._log_game_state(game_id)
        
        # 坐标系统说明：
        # 在这个游戏中，[x,y]中的y是反向的：
        # [0,-1]表示向上移动，[0,1]表示向下移动
        # [-1,0]表示向左移动，[1,0]表示向右移动
        
        # Game main loop
        while self.running and game_id in self.games:
            try:
                game = self.games[game_id]
                
                # Calculate time delta
                now = time.time()
                dt = now - last_update
                last_update = now
                
                # Update game time
                game['state']['game_time'] += dt
                
                # 每隔一段时间更新蛇的位置
                if now - last_move_time >= move_interval:
                    last_move_time = now
                    
                    # 记录蛇的移动日志
                    logger.warning(f"Moving snakes in game {game_id}")
                    logger.warning(f"Snake1 current direction: {game['state']['directions'][0]}")
                    logger.warning(f"Snake2 current direction: {game['state']['directions'][1]}")
                    
                    # 标记是否有蛇吃到食物
                    just_ate = [False, False]
                    
                    # 更新蛇的位置
                    for i in range(2):
                        direction = game['state']['directions'][i]
                        
                        # 获取蛇的当前位置
                        snake_key = f'snake{i+1}'
                        snake = game['state'][snake_key]
                        
                        if not snake:  # 如果蛇不存在，跳过
                            continue
                        
                        # 获取蛇头位置
                        head_x, head_y = snake[0]
                        
                        # 计算新的头部位置
                        new_head_x = head_x + direction[0]
                        new_head_y = head_y + direction[1]
                        
                        # 打印调试信息
                        logger.warning(f"Snake {i+1} moving from [{head_x},{head_y}] to [{new_head_x},{new_head_y}] with direction {direction}")
                        
                        # 检查边界碰撞 (假设游戏区域是20x20)
                        grid_size = 20
                        # 添加详细日志用于调试边界检测
                        logger.warning(f"Snake {i+1} boundary check: pos=[{new_head_x},{new_head_y}], grid_size={grid_size}")
                        
                        if new_head_x < 0 or new_head_x >= grid_size or new_head_y < 0 or new_head_y >= grid_size:
                            # 蛇撞墙，游戏结束
                            logger.warning(f"Snake {i+1} hit wall at [{new_head_x},{new_head_y}], boundaries: x=[0,{grid_size-1}], y=[0,{grid_size-1}]")
                            self._end_game(game_id, 1-i)  # 另一方获胜
                            return
                        
                        # 检查蛇与蛇的碰撞
                        other_snake_key = f'snake{2 if i == 0 else 1}'
                        other_snake = game['state'][other_snake_key]
                        
                        collision = False
                        for segment in snake[:-1]:  # 检查自己身体（除尾部外）
                            if new_head_x == segment[0] and new_head_y == segment[1]:
                                collision = True
                                logger.warning(f"Snake {i+1} collided with itself at [{new_head_x},{new_head_y}]")
                                break
                                
                        for segment in other_snake:  # 检查对方身体
                            if new_head_x == segment[0] and new_head_y == segment[1]:
                                collision = True
                                logger.warning(f"Snake {i+1} collided with other snake at [{new_head_x},{new_head_y}]")
                                break
                                
                        if collision:
                            # 蛇撞到自己或对方，游戏结束
                            logger.warning(f"Snake {i+1} collided at [{new_head_x},{new_head_y}]")
                            self._end_game(game_id, 1-i)  # 另一方获胜
                            return
                        
                        # 检查是否吃到食物
                        food_x, food_y = game['state']['food']
                        if new_head_x == food_x and new_head_y == food_y:
                            # 蛇吃到食物，增加得分并生成新食物
                            just_ate[i] = True
                            game['state']['scores'][i] += 1
                            logger.warning(f"Snake {i+1} ate food at [{food_x},{food_y}]")
                            
                            # 生成新的食物位置
                            while True:
                                new_food_x = random.randint(0, grid_size - 1)
                                new_food_y = random.randint(0, grid_size - 1)
                                
                                # 确保新食物不会出现在蛇身上
                                collision = False
                                for s in range(2):
                                    snake_key = f'snake{s+1}'
                                    for segment in game['state'][snake_key]:
                                        if new_food_x == segment[0] and new_food_y == segment[1]:
                                            collision = True
                                            break
                                    if collision:
                                        break
                                
                                if not collision:
                                    game['state']['food'] = [new_food_x, new_food_y]
                                    logger.warning(f"New food spawned at [{new_food_x},{new_food_y}]")
                                    break
                        
                        # 在蛇头位置创建新的头部
                        new_head = [new_head_x, new_head_y]
                        snake.insert(0, new_head)
                        
                        # 如果没有吃到食物，删除尾部；否则保留尾部（蛇会增长）
                        if not just_ate[i]:
                            snake.pop()
                        else:
                            logger.warning(f"Snake {i+1} grows to length {len(snake)}")
                    
                    # 更新游戏状态中的蛇位置
                    logger.warning(f"Updated snake positions: Snake1={game['state']['snake1']}, Snake2={game['state']['snake2']}")
                    
                    # 检查获胜条件 - 如果有玩家达到一定分数（例如10分）
                    for i in range(2):
                        if game['state']['scores'][i] >= 10:
                            logger.warning(f"Player {i+1} won with 10 points!")
                            self._end_game(game_id, i)
                            return
                
                # 发送游戏状态更新给每个玩家
                for i, player_id in enumerate(game['players']):
                    try:
                        if player_id in self.clients:
                            msg = GameMessage(GameMessage.GAME_STATE, game['state'], player_id)
                            self._send_message(self.clients[player_id][0], msg)
                    except Exception as e:
                        logger.error(f"Failed to send state to player {i+1}: {e}")
                
                # 短暂休眠，减少CPU使用
                time.sleep(0.05)  # 减少休眠时间，使状态更新更频繁
                
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
                logger.exception(e)
    
    def _heartbeat_checker(self):
        """Heartbeat detection, remove inactive clients"""
        while self.running:
            try:
                # Send heartbeat to all clients
                for player_id, (conn, _) in list(self.clients.items()):
                    try:
                        self._send_message(conn, GameMessage(GameMessage.HEARTBEAT, {}, player_id))
                    except:
                        # If sending fails, remove client
                        if player_id in self.clients:
                            del self.clients[player_id]
                        if player_id in self.waiting_players:
                            self.waiting_players.remove(player_id)
                        logger.warning(f"Player {player_id} heartbeat detection failed, removed")
            except Exception as e:
                logger.error(f"Heartbeat checking error: {e}")
            
            time.sleep(HEARTBEAT_INTERVAL)

    def _end_game(self, game_id, winner_idx=None):
        """End game and notify players
        
        Args:
            game_id: ID of the game to end
            winner_idx: Index of the winning player (0 or 1), None for a draw
        """
        try:
            if game_id not in self.games:
                logger.warning(f"Tried to end non-existent game: {game_id}")
                return
                
            game = self.games[game_id]
            
            # Log game end with detailed results
            logger.warning("=" * 50)
            logger.warning(f"GAME ENDED - Game ID: {game_id}")
            
            result_msg = ""
            if winner_idx is None:
                result_msg = "Game ended in a draw!"
                logger.warning("Result: DRAW")
            else:
                winner_id = game['players'][winner_idx]
                loser_id = game['players'][1 - winner_idx]
                winner_score = game['state']['scores'][winner_idx]
                loser_score = game['state']['scores'][1 - winner_idx]
                
                result_msg = f"Player {winner_id} wins with score {winner_score} against {loser_score}!"
                logger.warning(f"Result: Player {winner_id} WINS")
                logger.warning(f"Final Score: {winner_score} - {loser_score}")
            
            # Record game duration
            duration = game['state']['game_time']
            logger.warning(f"Game Duration: {duration:.2f} seconds")
            
            # Log final positions
            logger.warning(f"Final Snake 1 Position: {game['state']['snake1']}")
            logger.warning(f"Final Snake 2 Position: {game['state']['snake2']}")
            logger.warning("=" * 50)
                
            # Notify players about game end
            for i, player_id in enumerate(game['players']):
                if player_id in self.clients:
                    try:
                        conn = self.clients[player_id][0]
                        
                        # 构建游戏结果消息
                        is_winner = (i == winner_idx) if winner_idx is not None else None
                        end_message = {
                            'result': 'win' if is_winner else ('draw' if winner_idx is None else 'lose'),
                            'message': result_msg,
                            'final_state': game['state']
                        }
                        
                        # 发送游戏结束消息
                        self._send_message(conn, GameMessage(
                            GameMessage.GAME_END,
                            end_message,
                            player_id
                        ))
                        logger.warning(f"Game end notification sent to player {player_id}")
                    except Exception as e:
                        logger.error(f"Error sending game end to player {player_id}: {e}")
            
            # 从活动游戏列表中移除
            del self.games[game_id]
            logger.warning(f"Game {game_id} removed from active games")
            
        except Exception as e:
            logger.error(f"Error ending game {game_id}: {e}")
            logger.exception(e)

    def _log_game_state(self, game_id):
        """Log detailed game state for debugging"""
        if game_id not in self.games:
            logger.warning(f"Cannot log state for non-existent game: {game_id}")
            return
            
        game = self.games[game_id]
        state = game['state']
        
        logger.warning("=" * 50)
        logger.warning(f"GAME STATE DETAILS - Game ID: {game_id}")
        logger.warning(f"Status: {game['status']}")
        logger.warning(f"Players: {game['players']}")
        logger.warning(f"Game Time: {state['game_time']:.2f} seconds")
        logger.warning(f"Food Position: {state['food']}")
        
        # Snake 1 details
        logger.warning(f"Snake 1:")
        logger.warning(f"  - Position: {state['snake1']}")
        logger.warning(f"  - Direction: {state['directions'][0]}")
        logger.warning(f"  - Score: {state['scores'][0]}")
        
        # Snake 2 details
        logger.warning(f"Snake 2:")
        logger.warning(f"  - Position: {state['snake2']}")
        logger.warning(f"  - Direction: {state['directions'][1]}")
        logger.warning(f"  - Score: {state['scores'][1]}")
        
        logger.warning("=" * 50)

    def _handle_client_disconnect(self, player_id):
        """Handle client disconnect
        
        Args:
            player_id: ID of disconnected client
        """
        if not player_id or player_id not in self.clients:
            logger.warning(f"Cannot handle disconnect for unknown player: {player_id}")
            return
            
        logger.warning(f"Player {player_id} disconnected")
        
        # 从客户端列表中移除
        if player_id in self.clients:
            del self.clients[player_id]
            
        # 从等待队列中移除
        if player_id in self.waiting_players:
            self.waiting_players.remove(player_id)
            logger.warning(f"Player {player_id} removed from waiting queue")
            
        # 检查玩家是否在游戏中
        for game_id, game in list(self.games.items()):
            if player_id in game['players']:
                # 获取对手ID (另一个玩家)
                opponent_idx = 1 - game['players'].index(player_id)
                opponent_id = game['players'][opponent_idx]
                
                logger.warning(f"Player {player_id} left game {game_id}, opponent {opponent_id} wins")
                
                # 通知对手，他胜利了
                if opponent_id in self.clients:
                    try:
                        conn = self.clients[opponent_id][0]
                        self._send_message(conn, GameMessage(
                            GameMessage.GAME_END,
                            {
                                'result': 'win',
                                'message': f'Player {player_id} disconnected. You win!',
                                'final_state': game['state']
                            },
                            opponent_id
                        ))
                        logger.warning(f"Victory notification sent to player {opponent_id}")
                    except Exception as e:
                        logger.error(f"Error sending victory notification to {opponent_id}: {e}")
                
                # 结束游戏
                if game_id in self.games:
                    del self.games[game_id]
                    logger.warning(f"Game {game_id} removed due to player disconnect") 