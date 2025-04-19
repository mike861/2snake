#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Message Module - Handles game message protocol for Snake Game multiplayer
"""

import json
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Snake.Network.Message')

class GameMessage:
    """Game message data structure"""
    
    # Message types
    CONNECT = 'connect'  # Connect to server
    CONNECT_ACK = 'connect_ack'  # Connection acknowledged
    DISCONNECT = 'disconnect'  # Disconnect from server
    MATCH = 'match'  # Match with another player
    MATCH_ACK = 'match_ack'  # Match acknowledged
    GAME_START = 'game_start'  # Game start
    GAME_STATE = 'game_state'  # Game state update
    GAME_END = 'game_end'  # Game end
    COMMAND = 'command'  # Game command
    COMMAND_ACK = 'command_ack'  # Command acknowledged
    ERROR = 'error'  # Error message
    HEARTBEAT = 'heartbeat'  # Heartbeat message
    
    def __init__(self, msg_type, data=None, client_id=None):
        """Initialize message"""
        self.type = msg_type
        self.data = data if data is not None else {}
        self.client_id = client_id
        self.timestamp = time.time()
        
    def to_json(self):
        """Convert message to JSON"""
        return json.dumps({
            'type': self.type,
            'data': self.data,
            'client_id': self.client_id,
            'timestamp': self.timestamp
        })
    
    @classmethod
    def from_json(cls, json_str):
        """Create message object from JSON string"""
        try:
            # Clean up the input string to prevent JSON parsing errors
            json_str = json_str.strip()
            
            # If there are multiple messages (split by newlines), take only the first one
            if '\n' in json_str:
                json_str = json_str.split('\n', 1)[0]
            
            # Try to find the end of the JSON object to handle any trailing data
            end_index = json_str.rfind('}') + 1
            if end_index > 0:
                json_str = json_str[:end_index]
            
            msg_dict = json.loads(json_str)
            return cls(
                msg_dict['type'],
                msg_dict.get('data', {}),
                msg_dict.get('client_id')
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse message: {e}, raw: {json_str[:100]}")
            return cls(GameMessage.ERROR, {'error': 'Invalid message format'})
