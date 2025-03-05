import pygame
from src.config_manager import ConfigManager

class Snake:
    def __init__(self, color, start_pos, control_keys, base_speed):
        self.config = ConfigManager()
        self.color = color
        self.body = [start_pos]
        self.direction = [1, 0]
        self.grow = False
        self.control_keys = control_keys
        self.base_speed = base_speed  # Get base speed from config
        self.move_timer = 0  # Movement timer
        # Animation-related attributes
        self.head_scale = 1.0  # Snake head scale
        self.animation_time = 0  # Animation timer
        self.is_animating = False  # Whether animation is playing
        
    def get_speed(self):
        # Calculate speed based on snake length, increase by 0.5 for each segment
        return self.base_speed + (len(self.body) - 1) * 0.5
        
    def should_move(self, dt):
        # Calculate movement interval based on speed
        move_interval = 1000 / self.get_speed()  # Convert speed to milliseconds interval
        self.move_timer += dt
        
        if self.move_timer >= move_interval:
            self.move_timer = 0  # Reset timer
            return True
        return False
        
    def move(self):
        new_head = [self.body[0][0] + self.direction[0],
                   self.body[0][1] + self.direction[1]]
        
        # Wrap around screen
        new_head[0] %= self.config.GRID_WIDTH
        new_head[1] %= self.config.GRID_HEIGHT
        
        self.body.insert(0, new_head)
        if not self.grow:
            self.body.pop()
        self.grow = False
        
    def handle_keys(self, keys):
        if keys[self.control_keys['UP']] and self.direction != [0, 1]:
            self.direction = [0, -1]
        elif keys[self.control_keys['DOWN']] and self.direction != [0, -1]:
            self.direction = [0, 1]
        elif keys[self.control_keys['LEFT']] and self.direction != [1, 0]:
            self.direction = [-1, 0]
        elif keys[self.control_keys['RIGHT']] and self.direction != [-1, 0]:
            self.direction = [1, 0]

    def start_eat_animation(self):
        self.is_animating = True
        self.animation_time = 0
        self.head_scale = 1.0

    def update_animation(self, dt):
        if not self.is_animating:
            return
        
        self.animation_time += dt
        total_animation_time = 300  # Total animation duration in milliseconds
        
        if self.animation_time <= total_animation_time / 2:
            # First half: scale up
            progress = self.animation_time / (total_animation_time / 2)
            self.head_scale = 1.0 + (0.5 * progress)  # Scale up to 1.5x
        else:
            # Second half: scale down
            progress = (self.animation_time - total_animation_time / 2) / (total_animation_time / 2)
            self.head_scale = 1.5 - (0.5 * progress)  # Scale down from 1.5x to 1.0x
            
        if self.animation_time >= total_animation_time:
            self.is_animating = False
            self.head_scale = 1.0 