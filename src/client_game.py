#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snake Game Client - Multiplayer Online Version
"""

import sys
import os
import time
import json
import threading
import random
from typing import Dict, List, Tuple, Optional, Any
import logging

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.properties import NumericProperty, BooleanProperty, StringProperty, ObjectProperty
from kivy.vector import Vector
from kivy.graphics import Color, Rectangle, Line
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
# Add a console handler with WARNING level
logger.add(sys.stderr, level="WARNING", 
           format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
# Add a file handler for DEBUG and above
logger.add("logs/game_{time}.log", level="DEBUG", rotation="1 day", retention="7 days")

# Configure Kivy logger to use WARNING level
import kivy.logger
# Set Kivy logger level to WARNING
kivy.logger.Logger.setLevel(kivy.logger.LOG_LEVELS["warning"])

# Import custom modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from network import GameClient, GameMessage, DEFAULT_PORT

# Font settings
from kivy.core.text import Label as CoreLabel
logger.warning("Using system default font")

class Snake:
    """Snake data model class"""
    def __init__(self, color, start_pos):
        self.color = color
        self.body = start_pos
        self.head_scale = 1.0
        self.is_animating = False
        self.animation_time = 0
    
    def update_animation(self, dt):
        """Update food eating animation effect"""
        if not self.is_animating:
            return
        
        self.animation_time += dt * 1000
        total_animation_time = 300
        
        # Animation completion
        if self.animation_time >= total_animation_time:
            self.is_animating = False
            self.head_scale = 1.0
            self.animation_time = 0
        else:
            # Scale calculation (1.0 -> 1.5 -> 1.0)
            progress = self.animation_time / total_animation_time
            if progress < 0.5:
                self.head_scale = 1.0 + progress * 1.0  # Expand
            else:
                self.head_scale = 2.0 - progress * 1.0  # Contract
    
    def start_eat_animation(self):
        """Start eating animation"""
        self.is_animating = True
        self.animation_time = 0

class ServerInputPopup(Popup):
    """Server connection popup dialog"""
    def __init__(self, connect_callback, **kwargs):
        super(ServerInputPopup, self).__init__(**kwargs)
        self.connect_callback = connect_callback
        self.size_hint = (0.8, 0.6)
        self.title = "Connect to Server"
        self.auto_dismiss = False
        
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Server address input
        server_layout = BoxLayout(size_hint_y=None, height=40)
        server_layout.add_widget(Label(text="Server:", size_hint_x=0.3))
        self.server_input = TextInput(text="localhost", multiline=False, size_hint_x=0.7, font_size=16)
        server_layout.add_widget(self.server_input)
        layout.add_widget(server_layout)
        
        # Port input
        port_layout = BoxLayout(size_hint_y=None, height=40)
        port_layout.add_widget(Label(text="Port:", size_hint_x=0.3))
        self.port_input = TextInput(text=str(DEFAULT_PORT), multiline=False, size_hint_x=0.7, font_size=16)
        port_layout.add_widget(self.port_input)
        layout.add_widget(port_layout)
        
        # Status message
        self.status_label = Label(text="Enter server address and port", size_hint_y=None, height=40, font_size=16)
        layout.add_widget(self.status_label)
        
        # Add spacer
        layout.add_widget(Label(size_hint_y=1))  # Flexible spacer
        
        # Button layout
        btn_layout = BoxLayout(size_hint_y=None, height=60, spacing=20)
        
        # Connect button
        self.connect_btn = Button(text="Connect", font_size=16)
        self.connect_btn.bind(on_press=self._on_connect)
        btn_layout.add_widget(self.connect_btn)
        
        # Cancel button
        cancel_btn = Button(text="Cancel", font_size=16)
        cancel_btn.bind(on_press=self.dismiss)
        btn_layout.add_widget(cancel_btn)
        
        layout.add_widget(btn_layout)
        self.add_widget(layout)
    
    def _on_connect(self, instance):
        """Handle connection button press"""
        # Disable button to prevent multiple clicks
        instance.disabled = True
        self.status_label.text = "Connecting..."
        
        try:
            host = self.server_input.text.strip()
            port = int(self.port_input.text.strip())
            
            # Start connection in a separate thread to avoid blocking UI
            threading.Thread(target=self._connect_thread, args=(host, port), daemon=True).start()
            
        except ValueError:
            self.status_label.text = "Invalid port number"
            instance.disabled = False
        except Exception as e:
            self.status_label.text = f"Error: {str(e)}"
            instance.disabled = False
    
    def _connect_thread(self, host, port):
        """Connection thread to avoid blocking UI"""
        success = self.connect_callback(host, port)
        
        # Update UI in the main thread
        Clock.schedule_once(lambda dt: self._update_status(success), 0)
    
    def _update_status(self, success):
        if success:
            self.dismiss()
        else:
            self.status_label.text = "Connection failed. Please try again."
            self.connect_btn.disabled = False

class WaitingScreen(BoxLayout):
    """Waiting screen shown while connecting or waiting for opponent"""
    def __init__(self, **kwargs):
        super(WaitingScreen, self).__init__(orientation='vertical', **kwargs)
        
        self.opacity = 0.9
        self.padding = [20, 20]
        with self.canvas.before:
            Color(0, 0, 0, 0.7)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        self.status_text = "Waiting for opponent"
        self.label = Label(text=self.status_text, font_size=24)
        self.dots = ""
        self.add_widget(self.label)
        
        # Animated dots
        Clock.schedule_interval(self._update_dots, 0.5)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def _update_dots(self, dt):
        self.dots = self.dots + "." if len(self.dots) < 3 else ""
        self.label.text = f"{self.status_text}{self.dots}"
    
    def update_status(self, text):
        """Update status message"""
        self.status_text = text
        self.label.text = f"{text}{self.dots}"

class GameOverScreen(BoxLayout):
    """Game over screen"""
    def __init__(self, on_restart, **kwargs):
        super(GameOverScreen, self).__init__(orientation='vertical', **kwargs)
        
        self.opacity = 0.9
        with self.canvas.before:
            Color(0, 0, 0, 0.8)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # Result label
        self.result_label = Label(text="Game Over", font_size=32)
        self.add_widget(self.result_label)
        
        # Score label
        self.score_label = Label(text="", font_size=24)
        self.add_widget(self.score_label)
        
        # Restart button
        restart_btn = Button(text="Play Again", size_hint=(None, None), size=(200, 50))
        restart_btn.bind(on_press=on_restart)
        
        btn_layout = BoxLayout(size_hint_y=None, height=100)
        btn_layout.add_widget(Label())  # Spacer
        btn_layout.add_widget(restart_btn)
        btn_layout.add_widget(Label())  # Spacer
        
        self.add_widget(btn_layout)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def update(self, result, score1, score2):
        """Update game over screen with result and scores"""
        self.result_label.text = result
        self.score_label.text = f"Your score: {score1}   Opponent score: {score2}"

class OnlineSnakeGame(Widget):
    """Online Snake Game Main Class"""
    
    score = NumericProperty(0)
    opponent_score = NumericProperty(0)
    game_time = NumericProperty(0)
    game_over = BooleanProperty(False)
    status_text = StringProperty("Waiting for connection...")
    
    def __init__(self, **kwargs):
        super(OnlineSnakeGame, self).__init__(**kwargs)
        
        # Game state variables
        self.grid_size = 30  # 增加网格大小以便更好地显示游戏内容
        self.game_started = False
        self.game_ended = False  # 新增游戏结束标志
        self.player_id = None
        self.player_idx = None  # 使用idx而非index保持一致性
        self._game_id = None  # 使用私有变量，添加getter/setter
        self.state_lock = threading.RLock()  # 添加状态锁
        self.scores = [0, 0]  # 玩家得分
        self.touch_start_pos = None
        self.swipe_direction = None
        self.last_direction_sent = None
        self.game_client = None
        self.snake1 = []  # 玩家1蛇身
        self.snake2 = []  # 玩家2蛇身
        self.keyboard_handler = None  # 键盘处理器引用
        self.log_counter = 0  # 添加日志计数器控制输出频率
        
        # Initialize game objects
        self.player_snake = Snake(color=(0, 1, 0), start_pos=[])
        self.opponent_snake = Snake(color=(0, 0, 1), start_pos=[])
        self.food_pos = None
        
        # Create UI components
        self.waiting_screen = WaitingScreen()
        self.game_over_screen = GameOverScreen(on_restart=self._restart_game)
        self.add_widget(self.waiting_screen)
        
        # Load game sounds
        self.load_sounds()
        
        # Start drawing the game
        Clock.schedule_interval(self.update, 1/30.0)  # 30 FPS
        Clock.schedule_interval(self.draw, 1/30.0)
        
        # 启动后清除键盘并重新绑定，确保正确设置
        Clock.schedule_once(self._setup_keyboard, 1)
        
        # Show server connection popup
        Clock.schedule_once(lambda dt: self.show_server_popup(), 0.5)
    
    def _setup_keyboard(self, dt):
        """确保正确设置键盘处理，避免初始化时的潜在问题"""
        # 如果已经有键盘绑定，先取消
        try:
            if hasattr(self, '_keyboard') and self._keyboard:
                self._keyboard.unbind(on_key_down=self._on_key_down)
                self._keyboard = None
            
            # 重新注册键盘处理器
            self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
            if self._keyboard:
                self._keyboard.bind(on_key_down=self._on_key_down)
                logger.warning("键盘处理器已重新设置")
        except Exception as e:
            logger.warning(f"键盘设置错误: {str(e)}")
    
    def render_text(self, text, x, y, color=(1,1,1,1), font_size=24):
        """Render text on the canvas"""
        with self.canvas:
            Color(*color)
            
            # Use CoreLabel to render text
            label = CoreLabel(text=text, font_size=font_size)
            label.refresh()
            texture = label.texture
            
            # Draw the text texture
            Rectangle(
                pos=(x - texture.width/2, y - texture.height/2),
                size=texture.size,
                texture=texture
            )
    
    def load_sounds(self):
        """Load game sound effects"""
        self.sounds = {}
        sound_path = os.path.join(os.path.dirname(__file__), 'sounds')
        
        if os.path.exists(sound_path):
            sound_files = {
                'eat': 'eat.wav',
                'die': 'die.wav',
                'win': 'win.wav',
                'lose': 'lose.wav',
                'start': 'start.wav'
            }
            
            for sound_name, file_name in sound_files.items():
                file_path = os.path.join(sound_path, file_name)
                if os.path.exists(file_path):
                    self.sounds[sound_name] = SoundLoader.load(file_path)
    
    def show_server_popup(self):
        """Show server connection popup"""
        popup = ServerInputPopup(connect_callback=self.connect_to_server)
        popup.open()
    
    def connect_to_server(self, host, port):
        """Connect to game server"""
        try:
            self.waiting_screen.update_status("Connecting to server")
            
            # Create game client
            self.game_client = GameClient(host, port)
            
            # Set event handlers
            self.game_client.on_state_update = self._on_state_update
            self.game_client.on_game_start = self._on_game_start
            self.game_client.on_game_end = self._on_game_end
            self.game_client.on_error = self._on_error
            
            # Connect to server (the GameClient class has connect method, not start)
            if self.game_client.connect():
                self.waiting_screen.update_status("Waiting for opponent")
                return True
            return False
        except Exception as e:
            logger.warning(f"Connection error: {e}")
            return False
    
    def _on_state_update(self, state):
        """Handle game state update from server"""
        try:
            if not self.game_started:
                return
                
            # 保存状态引用
            self.game_state = state
            
            # 更新蛇的位置
            if self.player_idx == 0:
                self.player_snake.body = state.get('snake1', [])
                self.opponent_snake.body = state.get('snake2', [])
            else:
                self.player_snake.body = state.get('snake2', [])
                self.opponent_snake.body = state.get('snake1', [])
                
            # 更新分数
            if 'scores' in state:
                self.score = state['scores'][self.player_idx]
                self.opponent_score = state['scores'][1 if self.player_idx == 0 else 0]
            
            # 更新食物位置
            if 'food' in state:
                self.food_pos = state['food']
                
            # 如果刚刚吃到食物，播放声音和动画效果
            if 'just_ate' in state and state['just_ate'][self.player_idx]:
                self.play_sound('eat')
                self.player_snake.start_eat_animation()
                
            # 如果对手刚刚吃到食物，播放对手吃食物声音
            if 'just_ate' in state and state['just_ate'][1 if self.player_idx == 0 else 0]:
                self.opponent_snake.start_eat_animation()
                
            # 更新成功
            logger.warning("Game state updated")
            
        except Exception as e:
            logger.warning("游戏状态更新失败")
            logger.exception(e)
    
    def _on_game_start(self, state, player_index):
        """Handle game start event from server"""
        logger.warning(f"Game started! You are player {player_index+1}")
        
        self.player_idx = player_index
        self.game_started = True
        self.game_over = False
        self.score = 0
        self.opponent_score = 0
        self.last_direction_sent = None
        self.game_state = state  # Store initial state
        self.player_id = self.game_client.player_id  # 保存玩家ID
        
        # 确保game_id被正确设置
        if hasattr(self.game_client, 'game_id') and self.game_client.game_id:
            self._game_id = self.game_client.game_id
            logger.warning(f"Game ID set from client: {self._game_id}")
        
        # 如果state中包含game_id，也保存它
        if 'game_id' in state:
            self._game_id = state['game_id']
            logger.warning(f"Game ID set from state: {self._game_id}")
            
        # 调试game_id设置
        logger.warning(f"Final game_id after setup: {self._game_id}")
        
        logger.warning(f"Game state initialized: started={self.game_started}, over={self.game_over}, player_index={self.player_idx}, player_id={self.player_id}")
        
        # 确保键盘输入正常工作
        Clock.schedule_once(self._setup_keyboard, 0.5)
        
        # Use Clock to update UI from the main Kivy thread
        Clock.schedule_once(lambda dt: self._update_game_ui(), 0)
    
    def _update_game_ui(self):
        """Update UI from the main Kivy thread"""
        try:
            state = self.game_state
            player_index = self.player_idx
            
            # Get initial snake positions - Check if players is a list or dict
            if isinstance(state['players'], list):
                # In this case, players is a list of player IDs
                # We need to use snake1 and snake2 instead
                if player_index == 0:
                    self.player_snake.body = state.get('snake1', [])
                    self.opponent_snake.body = state.get('snake2', [])
                else:
                    self.player_snake.body = state.get('snake2', [])
                    self.opponent_snake.body = state.get('snake1', [])
            else:
                # Original case where players is a dict with player data
                self.player_snake.body = state['players'][player_index]['body']
                opponent_index = 1 if player_index == 0 else 0
                self.opponent_snake.body = state['players'][opponent_index]['body']
            
            # Get initial food position
            self.food_pos = state['food']
            
            # Adjust snake colors based on player index
            if player_index == 0:
                self.player_snake.color = (0, 1, 0)  # Green for player 1
                self.opponent_snake.color = (0, 0, 1)  # Blue for player 2
            else:
                self.player_snake.color = (0, 0, 1)  # Blue for player 2
                self.opponent_snake.color = (0, 1, 0)  # Green for player 1
                
            # Hide waiting screen
            self.remove_widget(self.waiting_screen)
            
            # Play start sound
            self.play_sound('start')
            
            # Start game clock
            self.game_time = 0
            Clock.schedule_interval(self._update_game_time, 1.0)
                
        except Exception as e:
            logger.warning(f"Error initializing game UI: {e}")
    
    def _on_game_end(self, data):
        """Handle game end event from server"""
        logger.warning(f"Game ended, result: {data.get('result', 'unknown')}")
        logger.warning("Game ended!")
        
        self.game_started = False
        self.game_over = True
        
        # Unschedule game time updates
        Clock.unschedule(self._update_game_time)
        
        # 重置键盘绑定，以便在结束后仍能捕获按键
        Clock.schedule_once(self._setup_keyboard, 1)
        
        # Determine winner and show game over screen
        reason = data.get('reason', 'Unknown')
        winner = data.get('winner')
        
        result_text = "Game Over"
        if reason == 'disconnected':
            result_text = "Opponent Disconnected"
            self.play_sound('win')
        elif winner == self.player_id:
            result_text = "You Win!"
            self.play_sound('win')
        else:
            result_text = "You Lose!"
            self.play_sound('lose')
        
        # Store the game over data to use in the main thread
        self._game_over_data = {
            'result_text': result_text,
            'score': self.score,
            'opponent_score': self.opponent_score
        }
        
        # Use Clock to update UI from the main Kivy thread to avoid thread-related errors
        Clock.schedule_once(self._show_game_over_screen, 0.1)
    
    def _show_game_over_screen(self, dt):
        """Show game over screen from the main thread"""
        try:
            if hasattr(self, '_game_over_data'):
                data = self._game_over_data
                self.game_over_screen.update(data['result_text'], data['score'], data['opponent_score'])
                self.add_widget(self.game_over_screen)
        except Exception as e:
            logger.warning(f"Error showing game over screen: {e}")
    
    def _on_error(self, error):
        """Handle error from server"""
        logger.warning(f"Error: {error}")
        # Translate the connection error message to English
        if error == "与服务器的连接已断开":
            error = "Connection to server has been lost"
        self.waiting_screen.update_status(f"Error: {error}")
    
    def play_sound(self, sound_name):
        """Play a sound effect"""
        if sound_name in self.sounds and self.sounds[sound_name]:
            self.sounds[sound_name].play()
    
    def draw(self, *args):
        """Draw game elements on the canvas"""
        self.canvas.before.clear()
        
        # Draw background
        with self.canvas.before:
            Color(0.1, 0.1, 0.1)  # Dark gray background
            Rectangle(pos=(0, 0), size=self.size)
        
        if not self.game_started and not self.game_over:
            # Only draw waiting screen
            return
            
        # 游戏区域
        server_grid_size = 40  # 服务器网格大小
            
        # Draw grid (lighter colored lines)
        with self.canvas.before:
            Color(0.2, 0.2, 0.2)  # Grid lines color
            
            # 绘制网格线 - 水平和垂直
            for i in range(server_grid_size + 1):
                # 垂直线
                x = i * self.grid_size
                Line(points=[x, 0, x, server_grid_size * self.grid_size], width=1)
                
                # 水平线
                y = i * self.grid_size
                Line(points=[0, y, server_grid_size * self.grid_size, y], width=1)
            
            # 绘制游戏边界
            Color(0.5, 0.5, 0.5)  # 边界颜色
            border_size = server_grid_size * self.grid_size
            Line(rectangle=(0, 0, border_size, border_size), width=2)
        
        # Draw debug center indicator
        self._draw_center_indicator()
        
        # Draw food
        if self.food_pos:
            with self.canvas.before:
                Color(1, 0, 0)  # Red food
                food_x, food_y = self.food_pos
                # 将服务器坐标转换为屏幕坐标
                screen_food_x, screen_food_y = self._convert_to_screen_coordinates(food_x, food_y)
                
                # 绘制食物
                Rectangle(
                    pos=(screen_food_x * self.grid_size, screen_food_y * self.grid_size),
                    size=(self.grid_size * 0.95, self.grid_size * 0.95)  # 略小于网格
                )
        
        # Draw player snake
        self._draw_snake(self.player_snake)
        
        # Draw opponent snake
        self._draw_snake(self.opponent_snake)
        
        # Draw scores
        self.draw_simple_scores()
        
        # Draw game time
        minutes = int(self.game_time) // 60
        seconds = int(self.game_time) % 60
        time_text = f"Time: {minutes:02d}:{seconds:02d}"
        
        with self.canvas.before:
            Color(1, 1, 1)
            Label(
                text=time_text,
                font_size=18,
                pos=(self.width - 100, self.height - 30),
                size=(100, 30)
            )
    
    def _draw_snake(self, snake):
        """Draw a snake on the canvas"""
        if not snake.body:
            logger.warning("蛇体为空，无法绘制")
            return
            
        # 记录绘制时的蛇体位置 - 使用计数器控制输出频率
        self.log_counter += 1
        if self.log_counter % 10 == 0:  # 每10次绘制输出一次日志
            logger.warning(f"绘制蛇: {snake.color}, 位置: {snake.body}")
            
        with self.canvas.before:
            Color(*snake.color)
            
            # Draw body segments
            for i, (x, y) in enumerate(snake.body):
                # 将服务器坐标转换为屏幕坐标
                screen_x, screen_y = self._convert_to_screen_coordinates(x, y)
                
                # The head segment might be scaled during animation
                if i == 0 and snake.is_animating:
                    # Calculate center point for scaling
                    center_x = screen_x * self.grid_size + self.grid_size / 2
                    center_y = screen_y * self.grid_size + self.grid_size / 2
                    
                    # Calculate scaled size and position
                    scaled_size = self.grid_size * snake.head_scale
                    scaled_pos_x = center_x - scaled_size / 2
                    scaled_pos_y = center_y - scaled_size / 2
                    
                    # Draw the scaled head
                    Rectangle(
                        pos=(scaled_pos_x, scaled_pos_y),
                        size=(scaled_size, scaled_size)
                    )
                else:
                    # Draw normal body segment
                    Rectangle(
                        pos=(screen_x * self.grid_size, screen_y * self.grid_size),
                        size=(self.grid_size * 0.95, self.grid_size * 0.95)  # 略小于单元格，使显示更美观
                    )
    
    def draw_simple_scores(self):
        """Draw player scores at the top of the screen"""
        with self.canvas.before:
            # Player score
            Color(0, 1, 0)  # Green
            Label(
                text=f"You: {self.score}",
                font_size=18,
                pos=(10, self.height - 30),
                size=(100, 30)
            )
            
            # Opponent score
            Color(0, 0, 1)  # Blue
            Label(
                text=f"Opponent: {self.opponent_score}",
                font_size=18,
                pos=(150, self.height - 30),
                size=(150, 30)
            )
    
    def _update_game_time(self, dt):
        """Update game timer"""
        if self.game_started and not self.game_over:
            self.game_time += dt
    
    def update(self, dt):
        """Update game state"""
        if not self.game_started or self.game_over:
            return
            
        # Update snake animations
        self.player_snake.update_animation(dt)
        self.opponent_snake.update_animation(dt)
        
        # Debug: Print the game id directly from instance variable
        logger.warning(f"DEBUG: Direct access to game_id in update: '{self._game_id}'")
        
        # Add debug info about current swipe direction
        if self.swipe_direction:
            logger.warning(f"Current swipe direction: {self.swipe_direction}, Last sent: {self.last_direction_sent}")
            
        # 如果方向已更改，在主线程中安全地发送命令
        if self.swipe_direction and self.swipe_direction != self.last_direction_sent:
            # 确认游戏ID不是None
            if self._game_id is None:
                logger.warning("Cannot send direction - game_id is None")
            else:
                logger.warning(f"Direction changed! Sending new direction: {self.swipe_direction}")
                self._send_direction_safe(self.swipe_direction)
    
    def send_direction(self):
        """Send direction to server - 作为兼容性保留，但不再使用"""
        logger.warning("send_direction called (deprecated method)")
        if self.swipe_direction:
            # 在主线程中安全地发送方向命令
            Clock.schedule_once(lambda dt: self._send_direction_safe(self.swipe_direction), 0)
    
    def on_touch_down(self, touch):
        """Handle touch down event for swipe controls"""
        if not self.game_started or self.game_over:
            return super(OnlineSnakeGame, self).on_touch_down(touch)
            
        self.touch_start_pos = Vector(touch.pos)
        return True
    
    def on_touch_up(self, touch):
        """Handle touch up event for swipe controls"""
        if not self.game_started or self.game_over or not self.touch_start_pos:
            return super(OnlineSnakeGame, self).on_touch_up(touch)
            
        # Calculate swipe distance and direction
        swipe_vector = Vector(touch.pos) - self.touch_start_pos
        
        # Ignore very short swipes
        if swipe_vector.length() < 30:
            return True
            
        # Determine direction based on swipe angle
        angle = swipe_vector.angle((1, 0))
        
        # 打印滑动角度调试信息
        logger.warning(f"Swipe angle: {angle}, vector: {swipe_vector}")
        
        # 方向映射 - 确保与服务器坐标系统一致
        # 服务器坐标系：[0,-1]=上, [0,1]=下, [-1,0]=左, [1,0]=右
        direction_map = {
            'UP': [0, -1],      # 向上移动 (y减小)
            'DOWN': [0, 1],     # 向下移动 (y增加)
            'LEFT': [-1, 0],    # 向左移动 (x减小)
            'RIGHT': [1, 0]     # 向右移动 (x增加)
        }
        
        # Assign direction based on angle
        direction_key = None
        if 45 <= angle < 135:
            direction_key = 'UP'
        elif 135 <= angle < 225:
            direction_key = 'LEFT'
        elif 225 <= angle < 315:
            direction_key = 'DOWN'
        else:
            direction_key = 'RIGHT'
            
        # 打印方向键映射调试信息
        logger.warning(f"Angle {angle} mapped to direction key: {direction_key}")
        
        # 直接设置为方向数组
        self.swipe_direction = direction_map[direction_key]
        logger.warning(f"Touch swipe direction: {direction_key} -> {self.swipe_direction}")
        
        # 在主线程中安全地发送方向命令
        Clock.schedule_once(lambda dt: self._send_direction_safe(self.swipe_direction), 0)
        
        return True
    
    def _on_keyboard_closed(self):
        """Handle keyboard being closed"""
        if hasattr(self, '_keyboard') and self._keyboard:
            self._keyboard.unbind(on_key_down=self._on_key_down)
            self._keyboard = None
    
    def _on_key_down(self, keyboard, keycode, text, modifiers):
        """Handle keyboard input"""
        # 使用logger确保日志正确输出
        logger.warning(f"Key pressed: {keycode[1]}")
        
        if not self.game_started or self.game_over:
            logger.warning(f"Game not active: started={self.game_started}, over={self.game_over}")
            return False
            
        key = keycode[1]
        
        # 方向映射 - 确保与服务器坐标系统一致
        # 服务器坐标系：[0,-1]=上, [0,1]=下, [-1,0]=左, [1,0]=右
        direction_map = {
            'up': [0, -1],    # 向上移动 (y减小)
            'down': [0, 1],   # 向下移动 (y增加)
            'left': [-1, 0],  # 向左移动 (x减小)
            'right': [1, 0],  # 向右移动 (x增加)
            'w': [0, -1],     # 向上移动 (y减小)
            's': [0, 1],      # 向下移动 (y增加)
            'a': [-1, 0],     # 向左移动 (x减小)
            'd': [1, 0]       # 向右移动 (x增加)
        }
        
        # 检查按键是否在映射中
        if key in direction_map:
            # 记录当前的方向和准备设置的新方向
            old_direction = self.swipe_direction
            new_direction = direction_map[key]
            
            # 记录按键和方向的映射详情
            logger.warning(f"Key '{key}' mapped to direction {new_direction}")
            
            # 直接将swipe_direction设置为方向数组
            self.swipe_direction = new_direction
            logger.warning(f"Direction set to {new_direction} from key {key} (old direction: {old_direction})")
            
            # 立即发送方向命令
            self._send_direction_safe(new_direction)
            logger.warning(f"Direction command sent immediately")
        else:
            logger.warning(f"Key {key} not mapped to any direction")
            
        return True
    
    def _send_direction_safe(self, direction):
        """Safely send the direction command to the server"""
        # 检查游戏客户端是否存在
        if self.game_client is None:
            logger.warning(f"Cannot send direction - game_client is None")
            return False
            
        # 检查游戏状态
        if not self.game_started:
            logger.warning(f"Cannot send direction - game not started")
            return False
            
        if self.game_ended:
            logger.warning(f"Cannot send direction - game ended")
            return False
            
        try:
            # 始终使用实例的game_id
            game_id = self._game_id
            
            # 确保方向与服务器预期一致 (服务器坐标系: 上=[0,-1], 下=[0,1], 左=[-1,0], 右=[1,0])
            # Mac坐标系可能与服务器不同，确保转换正确
            server_direction = direction.copy()  # 复制以避免修改原始值
            
            # 调试信息：原始方向和平台信息
            import platform
            logger.warning(f"Platform: {platform.system()}, Original direction: {direction}")
            
            # 记录最终发送的方向
            logger.warning(f"Sending direction {server_direction} for game_id={game_id}")
            
            # 创建命令数据
            command_data = {
                'command_type': 'direction',
                'direction': [int(server_direction[0]), int(server_direction[1])],  # 确保方向是整数
                'game_id': game_id
            }
            
            logger.warning(f"Command data: {command_data}")
            
            # 创建消息对象
            message = GameMessage(
                GameMessage.COMMAND,
                command_data,
                self.player_id
            )
            
            logger.warning(f"Sending message: type={message.type}, player_id={self.player_id}")
            
            # 发送消息
            result = self.game_client.send_message(message)
            
            if result:
                self.last_direction_sent = direction
                logger.warning(f"Direction {direction} sent successfully, updated last_direction_sent")
            else:
                logger.warning(f"Failed to send direction {direction}")
                
            return result
        except Exception as e:
            import traceback
            logger.warning(f"Exception while sending direction: {str(e)}")
            logger.exception(e)
            return False
    
    def _restart_game(self, instance):
        """Handle restart game button press"""
        logger.warning("尝试重新开始游戏...")
        
        # 重置游戏状态
        self.game_over = False
        self.game_started = False
        self.game_ended = False
        self.score = 0
        self.opponent_score = 0
        
        # 清除蛇的数据
        self.player_snake.body = []
        self.opponent_snake.body = []
        
        # 移除游戏结束屏幕
        if self.game_over_screen in self.children:
            self.remove_widget(self.game_over_screen)
        
        # 显示等待屏幕
        if self.waiting_screen not in self.children:
            self.add_widget(self.waiting_screen)
        self.waiting_screen.update_status("Preparing to reconnect...")
        
        # 断开旧连接，创建新连接
        if self.game_client:
            try:
                # 尝试断开旧连接
                if hasattr(self.game_client, 'disconnect'):
                    self.game_client.disconnect()
                    logger.warning("已断开旧连接")
            except Exception as e:
                logger.warning(f"断开连接时出错: {str(e)}")
        
        # 使用Clock调度重新连接，确保UI更新
        Clock.schedule_once(self._reconnect_to_server, 1.0)
    
    def _reconnect_to_server(self, dt):
        """重新连接到服务器"""
        # 显示服务器连接对话框
        self.show_server_popup()
    
    def update_game_state(self, game_state):
        """Update game state from server"""
        with self.state_lock:
            # Store the game state
            self.game_state = game_state
            
            # Update the snake positions
            if 'snake1' in game_state:
                self.snake1 = game_state['snake1']
            if 'snake2' in game_state:
                self.snake2 = game_state['snake2']
                
            # Update food position
            if 'food' in game_state:
                self.food_pos = game_state['food']
                
            # Record scores
            if 'scores' in game_state:
                self.scores = game_state['scores']
                
            # Update game time
            if 'game_time' in game_state:
                self.game_time = game_state['game_time']
                
            # Check if any snake just ate food
            self.just_ate = game_state.get('just_ate', [False, False])
            
    def handle_game_end(self, end_data):
        """Handle game end notification from server"""
        result = end_data.get('result', 'unknown')
        message = end_data.get('message', 'Game ended.')
        final_state = end_data.get('final_state', {})
        
        # Update final game state
        if final_state:
            self.update_game_state(final_state)
        
        # Log game end
        logger.warning("=" * 50)
        logger.warning("GAME ENDED")
        logger.warning(f"Result: {result.upper()}")
        logger.warning(f"Message: {message}")
        logger.warning(f"Final scores: {self.scores}")
        logger.warning(f"Game duration: {self.game_time:.2f} seconds")
        logger.warning("=" * 50)
        
        # Display game end on screen
        self.game_ended = True
        self.end_result = result
        self.end_message = message
        
        # Stop accepting keyboard input
        if self.keyboard_handler:
            self._unbind_keyboard()
            
        logger.warning("Game end handled successfully")

    def _process_message(self, message):
        """Process incoming messages from server"""
        try:
            logger.warning(f"Processing message: {message.type}")
            
            if message.type == GameMessage.CONNECT_ACK:
                # Connection acknowledged
                player_id = message.data.get('player_id')
                logger.warning(f"Connected to server, assigned player ID: {player_id}")
                self.player_id = player_id
                
            elif message.type == GameMessage.MATCH_ACK:
                # Match found
                match_info = message.data
                self._game_id = match_info.get('game_id')
                self.player_idx = match_info.get('player_idx')  # 0 or 1
                logger.warning(f"Matched game {self._game_id} as player {self.player_idx+1}")
                logger.warning(f"Game ID received: {self._game_id}")
                
            elif message.type == GameMessage.GAME_START:
                # Game starting
                self.game_started = True
                start_data = message.data
                # Check if the game_id is also in the start data
                if 'game_id' in start_data and not self._game_id:
                    self._game_id = start_data.get('game_id')
                    logger.warning(f"Game ID set from GAME_START: {self._game_id}")
                
                # Initialize game state
                self.update_game_state(start_data.get('state', {}))
                
                # Bind keyboard once game starts
                if not self.keyboard_handler:
                    self._bind_keyboard()
                    
                logger.warning("Game started, keyboard bound for input")
                logger.warning(f"Game started with ID: {self._game_id}")
                
            elif message.type == GameMessage.GAME_STATE:
                # Game state update
                self.update_game_state(message.data)
                
            elif message.type == GameMessage.GAME_END:
                # Game ended
                self.handle_game_end(message.data)
                
            elif message.type == GameMessage.COMMAND_ACK:
                # Command acknowledged
                cmd_result = message.data.get('result', False)
                cmd_type = message.data.get('command_type')
                logger.warning(f"Command {cmd_type} result: {cmd_result}")
                
            elif message.type == GameMessage.ERROR:
                # Error from server
                error_msg = message.data.get('message', 'Unknown error')
                logger.error(f"Server error: {error_msg}")
                
            elif message.type == GameMessage.HEARTBEAT:
                # Heartbeat - just update last message time
                pass
                
            else:
                logger.warning(f"Unhandled message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.exception(e)

    def _send_direction(self, direction):
        """Send direction command to server
        
        Args:
            direction: Direction vector [dx, dy]
        """
        if not self.game_client or not self.game_started or self.game_ended:
            logger.warning(f"Not sending direction {direction}: game not ready")
            return False
            
        logger.warning(f"Sending direction {direction}")
        
        # 创建方向命令消息
        command_data = {
            'command_type': 'direction',
            'direction': direction,
            'game_id': self._game_id
        }
        
        # 发送命令消息
        try:
            result = self.game_client.send_message(GameMessage(
                GameMessage.COMMAND,
                command_data,
                self.player_id
            ))
            return result
        except Exception as e:
            logger.error(f"Error sending direction: {e}")
            return False

    def _bind_keyboard(self):
        """绑定键盘事件处理"""
        try:
            if hasattr(self, '_keyboard') and self._keyboard:
                self._keyboard.unbind(on_key_down=self._on_key_down)
                
            self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
            if self._keyboard:
                self._keyboard.bind(on_key_down=self._on_key_down)
                self.keyboard_handler = True
                logger.warning("键盘处理器已绑定")
            else:
                logger.warning("无法获取键盘处理器")
        except Exception as e:
            logger.warning(f"键盘绑定错误: {str(e)}")
            
    def _unbind_keyboard(self):
        """解绑键盘事件处理"""
        try:
            if hasattr(self, '_keyboard') and self._keyboard:
                self._keyboard.unbind(on_key_down=self._on_key_down)
                self._keyboard = None
                self.keyboard_handler = False
                logger.warning("键盘处理器已解绑")
        except Exception as e:
            logger.warning(f"键盘解绑错误: {str(e)}")

    @property
    def game_id(self):
        """Getter for game_id"""
        logger.warning(f"Accessing game_id: {self._game_id}")
        return self._game_id
        
    @game_id.setter
    def game_id(self, value):
        """Setter for game_id"""
        logger.warning(f"Setting game_id to: {value}")
        self._game_id = value

    def _convert_to_screen_coordinates(self, server_x, server_y):
        """将服务器坐标转换为屏幕绘制坐标
        服务器坐标系: 游戏区域是40x40
        屏幕坐标系: 仅校准方向，不做缩放
        """
        # 服务器坐标直接映射到屏幕坐标，仅校准方向
        import platform
        
        # 调试日志
        if self.log_counter % 100 == 0:  # 降低日志频率
            logger.warning(f"坐标转换: 服务器({server_x}, {server_y}) -> 屏幕坐标")
            
        # Y轴方向校准（Mac系统需要反转Y轴）
        if platform.system() == 'Darwin':  # Mac系统
            # 服务器坐标的Y轴向下为正，需要反转
            server_grid_size = 40
            server_y = server_grid_size - server_y - 1  # 反转Y轴
            
        return server_x, server_y
    
    def _convert_from_screen_coordinates(self, screen_x, screen_y):
        """将屏幕坐标转换为服务器坐标
        逆向转换，仅校准方向
        """
        import platform
        
        # 调试日志
        if self.log_counter % 100 == 0:  # 降低日志频率
            logger.warning(f"坐标逆转换: 屏幕({screen_x}, {screen_y}) -> 服务器坐标")
            
        # Y轴方向校准（Mac系统需要反转Y轴）
        if platform.system() == 'Darwin':  # Mac系统
            server_grid_size = 40
            screen_y = server_grid_size - screen_y - 1  # 反转Y轴
        
        return int(screen_x), int(screen_y)

    def _draw_center_indicator(self):
        """绘制中心点指示器，帮助调试坐标系统"""
        # 服务器网格大小
        server_grid_size = 100
        
        # 计算游戏中心
        center_x = server_grid_size * self.grid_size / 2
        center_y = server_grid_size * self.grid_size / 2
        
        # 绘制中心点
        with self.canvas.before:
            # 绘制游戏中心点
            Color(1, 0, 0)  # 红色
            Rectangle(
                pos=(center_x - 5, center_y - 5),
                size=(10, 10)
            )
        
        # 每10帧输出一次调试信息
        self.log_counter += 1
        if self.log_counter % 10 == 0:
            logger.warning(f"游戏中心点: ({center_x:.1f}, {center_y:.1f})")

class OnlineSnakeApp(App):
    """Online Snake Game App"""
    def build(self):
        # Set window size to be bigger for better viewing
        Window.size = (800, 600)
        self.title = "Online Snake Battle"
        
        # Set Kivy logger level to WARNING
        import kivy.logger
        kivy.logger.Logger.setLevel(kivy.logger.LOG_LEVELS["warning"])
        logger.warning("Kivy logger level set to WARNING")
        
        # Create game instance
        game = OnlineSnakeGame()
        return game
    
    def build_config(self, config):
        """Configure the app"""
        config.setdefaults('snake', {
            'server': 'localhost',
            'port': DEFAULT_PORT
        })
    
    def on_stop(self):
        """Handle app closing"""
        game = self.root
        if game and game.game_client:
            # Since GameClient doesn't have a stop method, gracefully disconnect 
            # instead of calling a non-existent method
            if hasattr(game.game_client, 'disconnect'):
                game.game_client.disconnect()

if __name__ == '__main__':
    OnlineSnakeApp().run() 