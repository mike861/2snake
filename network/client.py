#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Client Module - Handles network client operations for Snake Game
"""

import socket
import threading
import time
import logging
from network.message import GameMessage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Snake.Network.Client')

# Default network settings
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 7004
BUFFER_SIZE = 4096
HEARTBEAT_INTERVAL = 5  # Heartbeat interval (seconds)

class GameClient:
    """Game client class, handles communication with the server"""
    
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
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
        self.on_connect = None
        self.on_match = None
        
        # Receive thread
        self.receive_thread = None
        
        # Store latest game state
        self.game_state = None
        
        # Heartbeat thread
        self.heartbeat_thread = None
        self.last_heartbeat_time = 0
    
    def connect(self):
        """Connect to the server
        
        Returns:
            bool: True if connection was successful
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            # Send connect message
            self.send_message(GameMessage(GameMessage.CONNECT))
            
            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
            self.receive_thread.start()
            
            # Start heartbeat thread
            self.heartbeat_thread = threading.Thread(target=self._heartbeat, daemon=True)
            self.heartbeat_thread.start()
            
            logger.info(f"Connected to server at {self.host}:{self.port}")
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
            logger.info("Disconnected from server")
    
    def is_connected(self):
        """Check if client is connected to the server
        
        Returns:
            bool: True if connected
        """
        return self.connected
    
    def request_match(self):
        """Request a match with another player
        
        Returns:
            bool: True if request was sent successfully
        """
        if not self.connected:
            logger.error("Cannot request match: not connected to server")
            return False
            
        return self.send_message(GameMessage(GameMessage.MATCH, client_id=self.player_id))
    
    def send_direction(self, direction):
        """Send direction command to server
        
        Args:
            direction: Direction vector [dx, dy]
            
        Returns:
            bool: True if command was sent successfully
        """
        if not self.connected or not self.game_id:
            logger.error("Cannot send direction: not in a game")
            return False
            
        command_data = {
            'command_type': 'direction',
            'game_id': self.game_id,
            'direction': direction
        }
        
        return self.send_message(GameMessage(
            GameMessage.COMMAND,
            command_data,
            self.player_id
        ))
    
    def send_message(self, message):
        """Send message to server
        
        Args:
            message: GameMessage to send
            
        Returns:
            bool: True if message was sent successfully
        """
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
        buffer = ""
        
        while self.connected:
            try:
                data = self.socket.recv(BUFFER_SIZE)
                if not data:
                    logger.warning("Server closed connection (empty data received)")
                    self.connected = False
                    if self.on_error:
                        self.on_error("Server closed the connection")
                    break
                
                messages = data.decode('utf-8').strip().split('\n')
                for msg_json in messages:
                    if msg_json:
                        try:
                            message = GameMessage.from_json(msg_json)
                            self._process_message(message)
                        except Exception as e:
                            logger.error(f"Error parsing message: {e}")
            except ConnectionResetError:
                logger.warning("Server closed the connection (reset)")
                self.connected = False
                if self.on_error:
                    self.on_error("Server closed the connection")
                break
            except Exception as e:
                logger.error(f"Socket error: {e}")
                self.connected = False
                if self.on_error:
                    self.on_error(f"Network error: {e}")
                break
        
        logger.info("Receive loop ended, marking as disconnected")
        self.connected = False
        if self.on_error:
            self.on_error("Connection to server has been lost")
    
    def _process_message(self, message):
        """Process messages from server"""
        try:
            logger.debug(f"Processing message: {message.type}")
            
            if message.type == GameMessage.CONNECT_ACK:
                # Connection acknowledged
                self.player_id = message.data.get('player_id')
                logger.info(f"Connected to server, player ID: {self.player_id}")
                
                if self.on_connect:
                    self.on_connect(self.player_id)
                    
                # 自动请求匹配
                self.request_match()
            
            elif message.type == GameMessage.MATCH_ACK:
                # Match acknowledged
                self.game_id = message.data.get('game_id')
                self.player_index = message.data.get('player_idx')
                self.opponent_id = message.data.get('opponent_id')
                logger.info(f"Matched game {self.game_id}, player index: {self.player_index}")
                
                if self.on_match:
                    self.on_match(self.game_id, self.player_index, self.opponent_id)
            
            elif message.type == GameMessage.GAME_START:
                # Game start
                self.game_state = message.data.get('state')
                logger.info(f"Game {self.game_id} started")
                
                if self.on_game_start:
                    self.on_game_start(self.game_state, self.player_index)
            
            elif message.type == GameMessage.GAME_STATE:
                # Game state update
                self.game_state = message.data
                logger.debug(f"Game state updated for game {self.game_id}")
                
                if self.on_state_update:
                    self.on_state_update(self.game_state)
            
            elif message.type == GameMessage.GAME_END:
                # Game end
                logger.info(f"Game {self.game_id} ended")
                
                if self.on_game_end:
                    self.on_game_end(message.data, self.game_id)
                
                # Reset game state
                self.game_id = None
                self.player_index = None
                self.opponent_id = None
                self.game_state = None
            
            elif message.type == GameMessage.ERROR:
                # Error message
                error_msg = message.data.get('error', 'Unknown error')
                logger.error(f"Server error: {error_msg}")
                
                if self.on_error:
                    self.on_error(error_msg)
            
            elif message.type == GameMessage.HEARTBEAT:
                # Heartbeat message
                self.last_heartbeat_time = time.time()
                logger.debug("Received heartbeat from server")
            
            else:
                logger.warning(f"Unhandled message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            if self.on_error:
                self.on_error(f"Error processing message: {e}")
    
    def _heartbeat(self):
        """Send heartbeat messages to server"""
        while self.connected:
            try:
                self.send_message(GameMessage(GameMessage.HEARTBEAT, client_id=self.player_id))
                logger.debug("Sent heartbeat to server")
            except Exception as e:
                logger.error(f"Failed to send heartbeat: {e}")
                self.connected = False
                break
                
            time.sleep(HEARTBEAT_INTERVAL)

# Run test client if executed directly
if __name__ == "__main__":
    import argparse
    import random
    
    parser = argparse.ArgumentParser(description='Snake Game Client')
    parser.add_argument('--host', default=DEFAULT_HOST, help='Server host address')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Server port')
    
    args = parser.parse_args()
    
    # Create client
    client = GameClient(host=args.host, port=args.port)
    
    # Set callback functions
    def on_connect(player_id):
        print(f"Connected as player {player_id}")
        # Request match after connection
        client.request_match()
    
    def on_match(game_id, player_idx, opponent_id):
        print(f"Matched in game {game_id} as player {player_idx+1} against {opponent_id}")
    
    def on_state_update(state):
        print(f"Game state updated: food at {state['food']}")
        
        # Get my snake
        my_snake_key = f"snake{client.player_index+1}"
        if my_snake_key in state:
            snake = state[my_snake_key]
            if snake:
                print(f"My snake head: {snake[0]}, length: {len(snake)}")
    
    def on_game_start(state, player_idx):
        print(f"Game started, I am player {player_idx+1}")
    
    def on_game_end(data, game_id):
        result = data.get('result')
        message = data.get('message')
        print(f"Game {game_id} ended: {result}")
        print(f"Message: {message}")
        
        # Request a new match
        client.request_match()
    
    def on_error(error):
        print(f"Error: {error}")
    
    client.on_connect = on_connect
    client.on_match = on_match
    client.on_state_update = on_state_update
    client.on_game_start = on_game_start
    client.on_game_end = on_game_end
    client.on_error = on_error
    
    # Connect to server
    if client.connect():
        print("Connected to server, press Ctrl+C to exit")
        
        try:
            # Main loop to send random directions
            while client.is_connected():
                if client.game_id:
                    # Send random direction command every second
                    direction = random.choice([[1, 0], [-1, 0], [0, 1], [0, -1]])
                    client.send_direction(direction)
                    print(f"Sent direction: {direction}")
                time.sleep(1)
        except KeyboardInterrupt:
            print("Client stopped by user")
            client.disconnect()
    else:
        print("Failed to connect to server")
