#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snake Game - Offline Mode (Local Two-Player)
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, Color, Line
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.config import Config
from kivy.uix.label import Label
from kivy.core.audio import SoundLoader
import random
import os

# Try to import the configuration manager
try:
    from config_manager import ConfigManager
    config_manager = ConfigManager()  # No file path parameter needed
    SETTINGS = {
        'window_width': config_manager.WINDOW_WIDTH,
        'window_height': config_manager.WINDOW_HEIGHT,
        'snake_size': config_manager.GRID_SIZE,
        'snake_speed': config_manager.FPS
    }
except ImportError:
    # Use default configuration
    SETTINGS = {
        'window_width': 800,
        'window_height': 600,
        'snake_size': 20,
        'snake_speed': 15
    }

# Game configuration
Config.set('graphics', 'width', SETTINGS['window_width'])
Config.set('graphics', 'height', SETTINGS['window_height'])
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

# Constant definitions
SNAKE_SIZE = SETTINGS['snake_size']
GRID_WIDTH = SETTINGS['window_width'] // SNAKE_SIZE
GRID_HEIGHT = SETTINGS['window_height'] // SNAKE_SIZE
UPDATE_INTERVAL = 1.0 / SETTINGS['snake_speed']  # Refresh interval (seconds)

# Direction definitions
UP = (0, 1)
DOWN = (0, -1)
LEFT = (-1, 0)
RIGHT = (1, 0)

# Player controls
PLAYER1_CONTROLS = {
    'w': UP,
    's': DOWN,
    'a': LEFT,
    'd': RIGHT
}

PLAYER2_CONTROLS = {
    'up': UP,
    'down': DOWN,
    'left': LEFT,
    'right': RIGHT
}

class Snake:
    def __init__(self, pos, color, controls):
        self.body = pos if isinstance(pos, list) else [pos]  # 确保body是列表
        self.color = color
        self.direction = (1, 0)  # 默认向右移动
        self.grow_pending = 3  # 初始长度增加
        self.score = 0
        self.alive = True
        self.controls = controls
    
    def move(self):
        """移动蛇，检测碰撞"""
        if not self.alive:
            return
        
        # 计算新的头部位置
        head_x, head_y = self.body[0]
        dir_x, dir_y = self.direction
        new_head = (head_x + dir_x, head_y + dir_y)
        
        # 边界检查（允许穿越边界）
        new_head = (new_head[0] % GRID_WIDTH, new_head[1] % GRID_HEIGHT)
        
        # 自己身体碰撞检测
        if new_head in self.body:
            self.alive = False
            return
        
        # 添加新头部
        self.body.insert(0, new_head)
        
        # 如果没有待增长段，移除尾部
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.body.pop()
    
    def change_direction(self, new_dir):
        # Prevent 180-degree turns
        if (new_dir[0] * -1, new_dir[1] * -1) != self.direction:
            self.direction = new_dir
    
    def grow(self):
        self.grow_pending += 1
        self.score += 1

class SnakeGame(Widget):
    def __init__(self, **kwargs):
        super(SnakeGame, self).__init__(**kwargs)
        
        # 添加游戏属性
        self.score1 = 0
        self.score2 = 0
        self.game_time = 0
        self.game_over = False
        self.game_over_text = "Game Over"
        
        # Load sound effects
        self.sound_eat = None
        self.sound_die = None
        
        sound_path = os.path.join(os.path.dirname(__file__), 'sounds')
        if os.path.exists(sound_path):
            self.sound_eat = SoundLoader.load(os.path.join(sound_path, 'eat.wav'))
            self.sound_die = SoundLoader.load(os.path.join(sound_path, 'die.wav'))
        
        self.reset_game()
        
        # Register keyboard events
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)
        
        # Set game update
        Clock.schedule_interval(self.update, UPDATE_INTERVAL)

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        
        # Player 1 controls
        if key in PLAYER1_CONTROLS and self.snake1.alive:
            self.snake1.change_direction(PLAYER1_CONTROLS[key])
        
        # Player 2 controls
        if key in PLAYER2_CONTROLS and self.snake2.alive:
            self.snake2.change_direction(PLAYER2_CONTROLS[key])
        
        # Reset game
        if key == 'r':
            self.reset_game()
        
        return True

    def reset_game(self):
        # Reset game state
        self.game_over = False
        self.game_over_text = "Game Over"
        self.game_time = 0
        self.score1 = 0
        self.score2 = 0
        
        # Create player 1 snake
        p1_start_pos = [(GRID_WIDTH // 4, GRID_HEIGHT // 2)]
        self.snake1 = Snake(p1_start_pos, (0, 1, 0), PLAYER1_CONTROLS)
        
        # Create player 2 snake
        p2_start_pos = [(GRID_WIDTH * 3 // 4, GRID_HEIGHT // 2)]
        self.snake2 = Snake(p2_start_pos, (0, 0, 1), PLAYER2_CONTROLS)
        
        # Generate first food
        self.generate_food()
    
    def generate_food(self):
        """Generate new food, ensuring it's not on a snake's body"""
        occupied = self.snake1.body + self.snake2.body
        while True:
            food = (random.randint(0, GRID_WIDTH - 1), random.randint(0, GRID_HEIGHT - 1))
            if food not in occupied:
                self.food = food
                return food
    
    def update(self, dt):
        # Check for game over
        all_dead = not self.snake1.alive and not self.snake2.alive
        
        if all_dead:
            self.game_over = True
            self.game_over_text = "Game Over!"
            if self.sound_die:
                self.sound_die.play()
            return  # Stop processing when game is over
        
        # Move snakes
        if self.snake1.alive:
            self.snake1.move()
        if self.snake2.alive:
            self.snake2.move()
        
        # 检测蛇之间的碰撞
        if self.snake1.alive and self.snake2.alive:
            # 蛇头碰到对方身体
            if self.snake1.body[0] in self.snake2.body:
                self.snake1.alive = False
                if self.sound_die:
                    self.sound_die.play()
            
            if self.snake2.body[0] in self.snake1.body:
                self.snake2.alive = False
                if self.sound_die:
                    self.sound_die.play()
        
        # Update scores
        self.score1 = self.snake1.score
        self.score2 = self.snake2.score
        
        # Update game time
        self.game_time += dt
        
        # Check for collisions with food
        if self.snake1.alive and self.snake1.body[0] == self.food:
            self.snake1.grow()
            self.food = self.generate_food()
            if self.sound_eat:
                self.sound_eat.play()
        
        if self.snake2.alive and self.snake2.body[0] == self.food:
            self.snake2.grow()
            self.food = self.generate_food()
            if self.sound_eat:
                self.sound_eat.play()
        
        # Redraw
        self.canvas.clear()
        self.draw_game()
    
    def draw_game(self):
        # Draw grid background
        with self.canvas:
            Color(0.1, 0.1, 0.1)
            Rectangle(pos=(0, 0), size=(Window.width, Window.height))
        
        # Draw food
        with self.canvas:
            Color(1, 0, 0)  # Red food
            Rectangle(pos=(self.food[0] * SNAKE_SIZE, self.food[1] * SNAKE_SIZE), 
                     size=(SNAKE_SIZE, SNAKE_SIZE))
        
        # Draw snake 1
        self.draw_snake(self.snake1)
        
        # Draw snake 2
        self.draw_snake(self.snake2)
        
        # Display scores
        with self.canvas:
            Color(1, 1, 1)
            Label(text=f"Player 1: {self.snake1.score}  Player 2: {self.snake2.score}", 
                  font_size=20, pos=(10, Window.height - 30))
        
        # Game over display
        if self.game_over:
            winner_text = "Tie!"
            if self.snake1.score > self.snake2.score:
                winner_text = "Player 1 wins!"
            elif self.snake2.score > self.snake1.score:
                winner_text = "Player 2 wins!"
            
            with self.canvas:
                Color(1, 1, 1)
                Label(text=f"Game Over! {winner_text}\nPress R to restart", 
                      font_size=30, pos=(Window.width // 2 - 100, Window.height // 2))
    
    def draw_snake(self, snake):
        if not snake.body:
            return
        
        with self.canvas:
            # Set snake color
            Color(*snake.color)
            
            # Draw snake body
            for segment in snake.body:
                Rectangle(pos=(segment[0] * SNAKE_SIZE, segment[1] * SNAKE_SIZE), 
                         size=(SNAKE_SIZE, SNAKE_SIZE))
            
            # If snake is dead, draw X mark
            if not snake.alive:
                head = snake.body[0]
                x, y = head[0] * SNAKE_SIZE, head[1] * SNAKE_SIZE
                Color(1, 0, 0)  # Red X
                Line(points=[x, y, x + SNAKE_SIZE, y + SNAKE_SIZE], width=2)
                Line(points=[x + SNAKE_SIZE, y, x, y + SNAKE_SIZE], width=2)

class SnakeApp(App):
    def build(self):
        return SnakeGame()

if __name__ == '__main__':
    SnakeApp().run() 