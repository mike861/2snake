#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game Logic Module - Core game mechanics for Snake Game
"""

import logging
import time
from game.state import GameState, GRID_SIZE, WIN_SCORE

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Snake.Game.Logic')

class GameLogic:
    """Handles snake game logic and rules"""
    
    def __init__(self, game_state):
        """Initialize game logic with a game state
        
        Args:
            game_state: GameState instance
        """
        self.state = game_state
        self.last_update_time = time.time()
    
    def update(self, dt=None):
        """Update game state for one step
        
        Args:
            dt: Time delta in seconds, or None to calculate from last update
            
        Returns:
            dict: Result of the update with keys:
                - game_over: True if game ended
                - winner: Index of winner (0 or 1) or None for draw
                - reason: Reason for game over
        """
        # Calculate time delta if not provided
        if dt is None:
            now = time.time()
            dt = now - self.last_update_time
            self.last_update_time = now
        
        # Update game time
        self.state.game_time += dt
        
        # Reset "just ate" flags
        self.state.just_ate = [False, False]
        
        result = {
            'game_over': False,
            'winner': None,
            'reason': None
        }
        
        # Move both snakes
        for i in range(2):
            snake_move_result = self._move_snake(i)
            
            if snake_move_result.get('collision'):
                # Snake collision - other player wins
                result['game_over'] = True
                result['winner'] = 1 - i
                result['reason'] = snake_move_result.get('reason', 'collision')
                return result
        
        # Check win condition - if a player reaches the score limit
        for i in range(2):
            if self.state.scores[i] >= WIN_SCORE:
                result['game_over'] = True
                result['winner'] = i
                result['reason'] = 'score_limit_reached'
                return result
                
        return result
    
    def _move_snake(self, snake_idx):
        """Move a snake one step
        
        Args:
            snake_idx: Index of snake to move (0 or 1)
            
        Returns:
            dict: Result of the move with keys:
                - collision: True if collision occurred
                - reason: Reason for collision
        """
        result = {
            'collision': False,
            'reason': None
        }
        
        # Get the snake and direction
        snake_key = 'snake1' if snake_idx == 0 else 'snake2'
        snake = getattr(self.state, snake_key)
        direction = self.state.directions[snake_idx]
        
        # Skip if snake doesn't exist
        if not snake:
            return result
        
        # Get head position
        head_x, head_y = snake[0]
        
        # Calculate new head position
        new_head_x = head_x + direction[0]
        new_head_y = head_y + direction[1]
        new_head = [new_head_x, new_head_y]
        
        logger.warning(f"Snake {snake_idx+1} moving from [{head_x},{head_y}] to [{new_head_x},{new_head_y}]")
        
        # Check for wall collision
        if (new_head_x < 0 or new_head_x >= GRID_SIZE or 
            new_head_y < 0 or new_head_y >= GRID_SIZE):
            result['collision'] = True
            result['reason'] = 'wall_collision'
            logger.warning(f"Snake {snake_idx+1} hit wall at [{new_head_x},{new_head_y}]")
            return result
        
        # Check for self collision
        for segment in snake[:-1]:  # Exclude tail which will move
            if new_head_x == segment[0] and new_head_y == segment[1]:
                result['collision'] = True
                result['reason'] = 'self_collision'
                logger.warning(f"Snake {snake_idx+1} collided with itself at [{new_head_x},{new_head_y}]")
                return result
        
        # Check for collision with other snake
        other_snake_key = 'snake2' if snake_idx == 0 else 'snake1'
        other_snake = getattr(self.state, other_snake_key)
        
        for segment in other_snake:
            if new_head_x == segment[0] and new_head_y == segment[1]:
                result['collision'] = True
                result['reason'] = 'snake_collision'
                logger.warning(f"Snake {snake_idx+1} collided with other snake at [{new_head_x},{new_head_y}]")
                return result
        
        # Check if snake eats food
        food_x, food_y = self.state.food
        if new_head_x == food_x and new_head_y == food_y:
            self.state.just_ate[snake_idx] = True
            self.state.scores[snake_idx] += 1
            logger.warning(f"Snake {snake_idx+1} ate food at [{food_x},{food_y}], new score: {self.state.scores[snake_idx]}")
            
            # Spawn new food
            self.state.spawn_food()
        
        # Move snake: add new head
        snake.insert(0, new_head)
        
        # If snake didn't eat food, remove tail
        if not self.state.just_ate[snake_idx]:
            snake.pop()
        
        # Update snake in state
        setattr(self.state, snake_key, snake)
        
        return result
