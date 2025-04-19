#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests specifically for the communication protocol as documented in COMMUNICATION_PROTOCOL.md
"""

import unittest
import json
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.network import GameMessage

class TestCommunicationProtocol(unittest.TestCase):
    """
    Tests to ensure the implementation matches the protocol definition
    in COMMUNICATION_PROTOCOL.md
    """
    
    def test_join_message_format(self):
        """Test JOIN message format matches protocol specification"""
        # Create a JOIN message
        player_id = "player-uuid"
        data = {"player_name": "Player1"}
        msg = GameMessage(GameMessage.JOIN, data, player_id)
        
        # Convert to JSON and parse back
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        # Verify against protocol definition
        self.assertEqual(parsed["type"], "join")
        self.assertEqual(parsed["player_id"], player_id)
        self.assertEqual(parsed["data"]["player_name"], "Player1")
    
    def test_leave_message_format(self):
        """Test LEAVE message format matches protocol specification"""
        # Create a LEAVE message
        player_id = "player-uuid"
        msg = GameMessage(GameMessage.LEAVE, {}, player_id)
        
        # Convert to JSON and parse back
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        # Verify against protocol definition
        self.assertEqual(parsed["type"], "leave")
        self.assertEqual(parsed["player_id"], player_id)
    
    def test_game_state_message_format(self):
        """Test GAME_STATE message format matches protocol specification"""
        # Create a game state
        state = {
            "players": [
                {"id": "player-uuid", "position": [5, 5], "score": 10},
                {"id": "another-player-uuid", "position": [3, 4], "score": 15}
            ],
            "food": {"position": [7, 8]},
            "status": "running"
        }
        
        # Create a GAME_STATE message
        msg = GameMessage(GameMessage.GAME_STATE, state)
        
        # Convert to JSON and parse back
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        # Verify against protocol definition
        self.assertEqual(parsed["type"], "state")
        self.assertEqual(parsed["data"], state)
    
    def test_move_message_format(self):
        """Test MOVE message format matches protocol specification"""
        # Create a MOVE message
        player_id = "player-uuid"
        direction = [1, 0]  # Right direction
        msg = GameMessage(GameMessage.MOVE, {"direction": direction}, player_id)
        
        # Convert to JSON and parse back
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        # Verify against protocol definition
        self.assertEqual(parsed["type"], "move")
        self.assertEqual(parsed["player_id"], player_id)
        self.assertEqual(parsed["data"]["direction"], direction)
    
    def test_start_message_format(self):
        """Test START message format matches protocol specification"""
        # Create a START message
        game_id = "game-uuid"
        msg = GameMessage(GameMessage.START, {"game_id": game_id})
        
        # Convert to JSON and parse back
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        # Verify against protocol definition
        self.assertEqual(parsed["type"], "start")
        self.assertEqual(parsed["data"]["game_id"], game_id)
    
    def test_end_message_format(self):
        """Test END message format matches protocol specification"""
        # Create an END message
        end_data = {
            "winner_id": "player-uuid",
            "final_scores": {"player-uuid": 20, "another-player-uuid": 15}
        }
        msg = GameMessage(GameMessage.END, end_data)
        
        # Convert to JSON and parse back
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        # Verify against protocol definition
        self.assertEqual(parsed["type"], "end")
        self.assertEqual(parsed["data"]["winner_id"], "player-uuid")
        self.assertEqual(parsed["data"]["final_scores"]["player-uuid"], 20)
        self.assertEqual(parsed["data"]["final_scores"]["another-player-uuid"], 15)
    
    def test_heartbeat_message_format(self):
        """Test HEARTBEAT message format matches protocol specification"""
        # Create a HEARTBEAT message
        player_id = "player-uuid"
        msg = GameMessage(GameMessage.HEARTBEAT, {}, player_id)
        
        # Convert to JSON and parse back
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        # Verify against protocol definition
        self.assertEqual(parsed["type"], "heartbeat")
        self.assertEqual(parsed["player_id"], player_id)
    
    def test_error_message_format(self):
        """Test ERROR message format matches protocol specification"""
        # Create an ERROR message
        error_message = "Player not found"
        msg = GameMessage(GameMessage.ERROR, {"message": error_message})
        
        # Convert to JSON and parse back
        json_str = msg.to_json()
        parsed = json.loads(json_str)
        
        # Verify against protocol definition
        self.assertEqual(parsed["type"], "error")
        self.assertEqual(parsed["data"]["message"], error_message)
    
    def test_message_from_json_protocol_compliance(self):
        """Test creating messages from JSON strings according to protocol"""
        # Test all message types from protocol examples
        
        # JOIN message
        join_json = '{"type": "JOIN", "player_id": "player-uuid", "player_name": "Player1"}'
        join_msg = GameMessage.from_json(join_json)
        self.assertEqual(join_msg.type, "JOIN")
        self.assertEqual(join_msg.player_id, "player-uuid")
        
        # MOVE message
        move_json = '{"type": "MOVE", "player_id": "player-uuid", "direction": [1, 0]}'
        move_msg = GameMessage.from_json(move_json)
        self.assertEqual(move_msg.type, "MOVE")
        self.assertEqual(move_msg.player_id, "player-uuid")
        
        # ERROR message
        error_json = '{"type": "ERROR", "message": "Player not found"}'
        error_msg = GameMessage.from_json(error_json)
        self.assertEqual(error_msg.type, "ERROR")


if __name__ == '__main__':
    unittest.main() 