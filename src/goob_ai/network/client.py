#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snake Game Network Client Module
"""

import socket
import threading
import time
import logging

from .protocol import GameMessage, DEFAULT_PORT, BUFFER_SIZE, HEARTBEAT_INTERVAL

logger = logging.getLogger('Snake.Network.Client')

class GameClient:
    """Game client class, handles communication with the server"""
    
    def __init__(self, host='localhost', port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.player_id = None
        self.game_id = None
        self.player_index = None
        self.opponent_id = None
        
        # Callback functions for game state updates
        self.on_state_update = None
        self.on_game_start = None
        self.on_game_end = None
        self.on_error = None
        
        # Receive thread
        self.receive_thread = None
        
        # Store latest game state
        self.game_state = None
        
        # Heartbeat thread
        self.heartbeat_thread = None
        self.last_heartbeat_time = 0
    
    def connect(self):
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            # 发送连接消息 (使用新的CONNECT消息类型)
            self.send_message(GameMessage(GameMessage.CONNECT))
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            
            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(target=self._heartbeat, daemon=True)
            self.heartbeat_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            if self.on_error:
                self.on_error(f"Failed to connect to server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        if self.connected:
            try:
                # Send disconnect message
                self.send_message(GameMessage(GameMessage.DISCONNECT, client_id=self.player_id))
            except:
                pass
            
            self.connected = False
            
            try:
                self.socket.close()
            except:
                pass
            
            self.socket = None
    
    def is_connected(self):
        """Check if client is connected to the server"""
        return self.connected
    
    def send_message(self, message):
        """Send message to server"""
        if not self.connected:
            return False
        
        try:
            if not message.client_id and self.player_id:
                message.client_id = self.player_id
            
            json_data = message.to_json()
            # Add newline as message boundary
            json_data += '\n'
            self.socket.sendall(json_data.encode('utf-8'))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.connected = False
            if self.on_error:
                self.on_error(f"Failed to send message: {e}")
            return False
    
    def _receive_messages(self):
        """Receive messages from server"""
        while self.connected:
            try:
                data = self.socket.recv(BUFFER_SIZE)
                if not data:
                    logger.warning("Server closed connection (empty data received)")
                    break
                
                raw_data = data.decode('utf-8')
                #logger.warning(f"Received raw data: {raw_data}")
                message = GameMessage.from_json(raw_data)
                self._process_message(message)
            except ConnectionResetError:
                logger.warning("Server closed the connection (reset)")
                break
            except socket.error as e:
                logger.error(f"Socket error: {e}")
                break
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                break
        
        logger.warning("Receive loop ended, marking as disconnected")
        self.connected = False
        if self.on_error:
            self.on_error("Connection to server has been lost")
    
    def _process_message(self, message):
        """Process messages from server"""
        try:
            logger.warning(f"Processing message: {message.type}")
            
            if message.type == GameMessage.CONNECT_ACK:
                # 连接确认
                self.player_id = message.data.get('player_id')
                logger.warning(f"Connected to server, player ID: {self.player_id}")
                
                # 请求匹配
                self.send_message(GameMessage(GameMessage.MATCH, client_id=self.player_id))
            
            elif message.type == GameMessage.MATCH_ACK:
                # 匹配确认
                self.game_id = message.data.get('game_id')
                self.player_index = message.data.get('player_idx')
                self.opponent_id = message.data.get('opponent_id')
                logger.warning(f"Matched game {self.game_id}, player index: {self.player_index}")
            
            elif message.type == GameMessage.GAME_START:
                # 游戏开始
                self.game_state = message.data.get('state')
                logger.warning(f"Game {self.game_id} started")
                
                if self.on_game_start:
                    self.on_game_start(self.game_state, self.player_index)
            
            elif message.type == GameMessage.GAME_STATE:
                # 游戏状态更新
                self.game_state = message.data
                logger.warning(f"Game state updated")
                
                if self.on_state_update:
                    self.on_state_update(self.game_state)
            
            elif message.type == GameMessage.GAME_END:
                # 游戏结束
                result = message.data.get('result')
                logger.warning(f"Game ended, result: {result}")
                
                if self.on_game_end:
                    self.on_game_end(message.data)
            
            elif message.type == GameMessage.COMMAND_ACK:
                # 命令确认
                logger.warning(f"Command acknowledged: {message.data}")
            
            elif message.type == GameMessage.HEARTBEAT:
                # 心跳响应
                self.last_heartbeat_time = time.time()
            
            elif message.type == GameMessage.ERROR:
                # 错误消息
                error_msg = message.data.get('message', 'Unknown error')
                logger.error(f"Server error: {error_msg}")
                
                if self.on_error:
                    self.on_error(error_msg)
            
            else:
                logger.warning(f"Received unknown message type: {message.type}")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.exception(e)
    
    def _heartbeat(self):
        """Periodically send heartbeat packets to server"""
        while self.connected:
            try:
                self.send_message(GameMessage(GameMessage.HEARTBEAT, client_id=self.player_id))
                time.sleep(HEARTBEAT_INTERVAL)
            except:
                break 