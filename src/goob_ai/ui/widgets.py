#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Widgets for Snake Game
"""

import threading
import logging

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock

# 设置日志记录器
logger = logging.getLogger('Snake.UI.Widgets')

# Assuming DEFAULT_PORT is defined elsewhere, possibly in network.protocol
# If not, define it here or import appropriately.
# from ...network.protocol import DEFAULT_PORT
DEFAULT_PORT = 7004 # Placeholder if not imported

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
        logger.warning(f"Attempting to connect with host: {self.server_input.text.strip()}, port: {self.port_input.text.strip()}")
        
        try:
            host = self.server_input.text.strip()
            port = int(self.port_input.text.strip())
            
            # Start connection in a separate thread to avoid blocking UI
            threading.Thread(target=self._connect_thread, args=(host, port), daemon=True).start()
            
        except ValueError:
            self.status_label.text = "Invalid port number"
            instance.disabled = False
            logger.warning("Invalid port number entered")
        except Exception as e:
            self.status_label.text = f"Error: {str(e)}"
            instance.disabled = False
            logger.error(f"Connection error: {str(e)}")
    
    def _connect_thread(self, host, port):
        """Connection thread to avoid blocking UI"""
        logger.warning(f"Connecting to server at {host}:{port}")
        success = self.connect_callback(host, port)
        
        # Update UI in the main thread
        Clock.schedule_once(lambda dt: self._update_status(success), 0)
    
    def _update_status(self, success):
        if success:
            logger.warning("Connection successful")
            self.dismiss()
        else:
            logger.warning("Connection failed")
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