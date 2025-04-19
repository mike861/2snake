#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for game logic module
"""

import unittest
from game.state import GameState
from game.logic import GameLogic

class TestGameState(unittest.TestCase):
    """Test cases for GameState class"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.player_ids = ['player1', 'player2']
        self.state = GameState(self.player_ids)
    
    def test_initialization(self):
        """Test state initialization"""
        self.assertEqual(self.state.players, self.player_ids)
        self.assertEqual(self.state.status, 'waiting')
        self.assertEqual(self.state.game_time, 0)
        
        # Test snake positions
        self.assertEqual(len(self.state.snake1), 3)
        self.assertEqual(len(self.state.snake2), 3)
        
        # Test scores
        self.assertEqual(self.state.scores, [0, 0])
        
        # Test food position
        self.assertEqual(len(self.state.food), 2)
    
    def test_update_direction(self):
        """Test direction update"""
        # Valid direction update
        result = self.state.update_direction(0, [0, 1])
        self.assertTrue(result)
        self.assertEqual(self.state.directions[0], [0, 1])
        
        # Invalid direction (diagonal)
        result = self.state.update_direction(1, [1, 1])
        self.assertFalse(result)
        self.assertEqual(self.state.directions[1], [-1, 0])  # Unchanged
        
        # Invalid direction (zero vector)
        result = self.state.update_direction(0, [0, 0])
        self.assertFalse(result)
        self.assertEqual(self.state.directions[0], [0, 1])  # Unchanged
        
        # Invalid player index
        result = self.state.update_direction(2, [1, 0])
        self.assertFalse(result)
    
    def test_spawn_food(self):
        """Test food spawning"""
        original_food = self.state.food.copy()
        
        # Place snakes on most of the grid to limit food placement options
        big_snake = [[x, 0] for x in range(19)]
        self.state.snake1 = big_snake
        
        # Spawn new food
        self.state.spawn_food()
        
        # Check that food position changed
        self.assertNotEqual(self.state.food, original_food)
        
        # Check that food is not on a snake
        for segment in self.state.snake1 + self.state.snake2:
            self.assertNotEqual(self.state.food, segment)
    
    def test_serialization(self):
        """Test state serialization"""
        serialized = self.state.get_serializable_state()
        
        # Check that serialized state contains all required fields
        self.assertIn('snake1', serialized)
        self.assertIn('snake2', serialized)
        self.assertIn('directions', serialized)
        self.assertIn('food', serialized)
        self.assertIn('scores', serialized)
        self.assertIn('game_time', serialized)


class TestGameLogic(unittest.TestCase):
    """Test cases for GameLogic class"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.player_ids = ['player1', 'player2']
        self.state = GameState(self.player_ids)
        self.logic = GameLogic(self.state)
    
    def test_move_snake(self):
        """Test snake movement"""
        # Initial positions
        initial_snake1 = self.state.snake1.copy()
        
        # Move snake 1 to the right
        self.state.directions[0] = [1, 0]
        result = self.logic._move_snake(0)
        
        # Check result
        self.assertFalse(result['collision'])
        
        # Check new position
        new_head = self.state.snake1[0]
        expected_head = [initial_snake1[0][0] + 1, initial_snake1[0][1]]
        self.assertEqual(new_head, expected_head)
        
        # Check snake length
        self.assertEqual(len(self.state.snake1), len(initial_snake1))
    
    def test_snake_growth(self):
        """Test snake growth when eating food"""
        # Position snake head next to food
        food_pos = self.state.food
        self.state.snake1[0] = [food_pos[0] - 1, food_pos[1]]
        self.state.directions[0] = [1, 0]  # Moving right toward food
        
        # Initial length
        initial_length = len(self.state.snake1)
        initial_score = self.state.scores[0]
        
        # Move snake
        self.logic._move_snake(0)
        
        # Check snake grew
        self.assertEqual(len(self.state.snake1), initial_length + 1)
        
        # Check score increased
        self.assertEqual(self.state.scores[0], initial_score + 1)
        
        # Check "just ate" flag
        self.assertTrue(self.state.just_ate[0])
        
        # Check food respawned
        self.assertNotEqual(self.state.food, food_pos)
    
    def test_wall_collision(self):
        """Test wall collision detection"""
        # Position snake head at edge
        self.state.snake1[0] = [0, 5]
        self.state.directions[0] = [-1, 0]  # Moving left toward wall
        
        # Move snake
        result = self.logic._move_snake(0)
        
        # Check collision detected
        self.assertTrue(result['collision'])
        self.assertEqual(result['reason'], 'wall_collision')
    
    def test_self_collision(self):
        """Test self collision detection"""
        # Create a situation where snake will collide with itself
        self.state.snake1 = [[5, 5], [6, 5], [6, 6], [5, 6], [4, 6]]
        self.state.directions[0] = [0, 1]  # Moving down toward its body
        
        # Move snake
        result = self.logic._move_snake(0)
        
        # Check collision detected
        self.assertTrue(result['collision'])
        self.assertEqual(result['reason'], 'self_collision')
    
    def test_snake_collision(self):
        """Test collision with other snake"""
        # Position snake1 head next to snake2
        self.state.snake1[0] = [8, 5]
        self.state.snake2[0] = [9, 5]
        self.state.directions[0] = [1, 0]  # Moving right toward snake2
        
        # Move snake
        result = self.logic._move_snake(0)
        
        # Check collision detected
        self.assertTrue(result['collision'])
        self.assertEqual(result['reason'], 'snake_collision')
    
    def test_game_over_by_collision(self):
        """Test game over by collision"""
        # Set up collision
        self.state.snake1[0] = [0, 5]
        self.state.directions[0] = [-1, 0]  # Moving left toward wall
        
        # Update game
        result = self.logic.update()
        
        # Check game over
        self.assertTrue(result['game_over'])
        self.assertEqual(result['winner'], 1)  # Player 2 wins
    
    def test_game_over_by_score(self):
        """Test game over by reaching score limit"""
        # Set high score for player 1
        self.state.scores[0] = 9
        
        # Position snake1 to eat food
        food_pos = self.state.food
        self.state.snake1[0] = [food_pos[0] - 1, food_pos[1]]
        self.state.directions[0] = [1, 0]  # Moving right toward food
        
        # Update game
        result = self.logic.update()
        
        # Check game over by score
        self.assertTrue(result['game_over'])
        self.assertEqual(result['winner'], 0)  # Player 1 wins
        self.assertEqual(result['reason'], 'score_limit_reached')


if __name__ == '__main__':
    unittest.main()
