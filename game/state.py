#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game State Module - Manages the state of a snake game
"""

import random
import logging
import uuid
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Snake.Game.State')

# Game constants
GRID_SIZE = 20
INITIAL_SNAKE_LENGTH = 3
WIN_SCORE = 10

class GameState:
    """Represents the state of a snake game"""
    
    def __init__(self, player_ids):
        """Initialize game state
        
        Args:
            player_ids: List of player IDs [player1_id, player2_id]
        """
        if len(player_ids) != 2:
            raise ValueError("Game requires exactly 2 players")
            
        self.id = str(uuid.uuid4())
        self.players = player_ids
        self.status = 'waiting'  # waiting, running, finished
        self.created_at = time.time()
        self.game_time = 0
        
        # Initialize game state
        # Snake 1 starts from left side, moving right
        self.snake1 = [[5, 10], [4, 10], [3, 10]]
        self.directions = [[1, 0], [-1, 0]]  # Snake directions
        
        # Snake 2 starts from right side, moving left
        self.snake2 = [[15, 10], [16, 10], [17, 10]]
        
        # Food position in the middle
        self.food = [10, 10]
        
        # Player scores
        self.scores = [0, 0]
        
        # If snake just ate food
        self.just_ate = [False, False]
        
        # Log initial state
        self.log_state()
    
    def to_dict(self):
        """Convert game state to dictionary for serialization"""
        return {
            'id': self.id,
            'players': self.players,
            'status': self.status,
            'created_at': self.created_at,
            'state': {
                'snake1': self.snake1,
                'snake2': self.snake2,
                'directions': self.directions,
                'food': self.food,
                'scores': self.scores,
                'game_time': self.game_time,
                'just_ate': self.just_ate
            }
        }
    
    def get_serializable_state(self):
        """Get game state in a format suitable for network transmission"""
        return {
            'snake1': self.snake1,
            'snake2': self.snake2,
            'directions': self.directions,
            'food': self.food,
            'scores': self.scores,
            'game_time': self.game_time,
            'just_ate': self.just_ate
        }
    
    def update_direction(self, player_idx, new_direction):
        """Update snake direction
        
        Args:
            player_idx: Player index (0 or 1)
            new_direction: New direction [dx, dy]
            
        Returns:
            bool: True if direction was successfully updated
        """
        if player_idx not in [0, 1]:
            logger.error(f"Invalid player index: {player_idx}")
            return False
            
        dx, dy = new_direction
        
        # Validate direction values
        if dx not in [-1, 0, 1] or dy not in [-1, 0, 1] or (abs(dx) + abs(dy) != 1):
            logger.error(f"Invalid direction values: {new_direction}")
            return False
            
        # Get current direction
        current_dx, current_dy = self.directions[player_idx]
        
        # Prevent 180-degree turns (direct opposite direction)
        if (dx == -current_dx and dy == -current_dy):
            logger.warning(f"Cannot turn 180 degrees from {[current_dx, current_dy]} to {[dx, dy]}")
            return False
            
        # Get snake position
        snake_key = 'snake1' if player_idx == 0 else 'snake2'
        snake = getattr(self, snake_key)
        head_x, head_y = snake[0]
        
        # Calculate new head position
        new_head_x = head_x + dx
        new_head_y = head_y + dy
        
        # Check if new direction would cause immediate collision
        for segment in snake[:-1]:  # Exclude tail which will move
            if new_head_x == segment[0] and new_head_y == segment[1]:
                logger.warning(f"New direction would cause immediate collision at [{new_head_x},{new_head_y}]")
                return False
            
        old_direction = self.directions[player_idx]
        self.directions[player_idx] = new_direction
        logger.debug(f"Player {player_idx} direction updated from {old_direction} to {new_direction}")
        return True
    
    def spawn_food(self):
        """Spawn new food at random position"""
        while True:
            new_x = random.randint(0, GRID_SIZE - 1)
            new_y = random.randint(0, GRID_SIZE - 1)
            
            # Ensure food doesn't spawn on a snake
            collision = False
            for segment in self.snake1 + self.snake2:
                if new_x == segment[0] and new_y == segment[1]:
                    collision = True
                    break
                    
            if not collision:
                self.food = [new_x, new_y]
                logger.debug(f"New food spawned at [{new_x},{new_y}]")
                break
    
    def log_state(self):
        """Log detailed game state for debugging"""
        logger.debug("=" * 50)
        logger.debug(f"GAME STATE - Game ID: {self.id}")
        logger.debug(f"Status: {self.status}")
        logger.debug(f"Players: {self.players}")
        logger.debug(f"Game Time: {self.game_time:.2f} seconds")
        logger.debug(f"Food Position: {self.food}")
        
        # Snake 1 details
        logger.debug(f"Snake 1:")
        logger.debug(f"  - Position: {self.snake1}")
        logger.debug(f"  - Direction: {self.directions[0]}")
        logger.debug(f"  - Score: {self.scores[0]}")
        
        # Snake 2 details
        logger.debug(f"Snake 2:")
        logger.debug(f"  - Position: {self.snake2}")
        logger.debug(f"  - Direction: {self.directions[1]}")
        logger.debug(f"  - Score: {self.scores[1]}")
        
        logger.debug("=" * 50)
