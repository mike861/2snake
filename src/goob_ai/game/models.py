#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Game Models for Snake Game
"""

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