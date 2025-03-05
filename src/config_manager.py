import os
import configparser
import pygame

class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        self.config.read(config_path)
        
        # Window settings
        self.WINDOW_WIDTH = self.config.getint('Window', 'width')
        self.WINDOW_HEIGHT = self.config.getint('Window', 'height')
        self.GRID_SIZE = self.config.getint('Window', 'grid_size')
        self.GRID_WIDTH = self.WINDOW_WIDTH // self.GRID_SIZE
        self.GRID_HEIGHT = self.WINDOW_HEIGHT // self.GRID_SIZE
        self.FPS = self.config.getint('Window', 'fps')
        
        # Colors
        self.BLACK = self._parse_color('Colors', 'black')
        self.WHITE = self._parse_color('Colors', 'white')
        self.RED = self._parse_color('Colors', 'red')
        self.GREEN = self._parse_color('Colors', 'green')
        self.BLUE = self._parse_color('Colors', 'blue')
        self.GRAY = self._parse_color('Colors', 'gray')
        
        # Game settings
        self.BASE_SPEED = self.config.getint('Game', 'base_speed')
        self.FOOD_SCORE = self.config.getint('Game', 'food_score')
        self.OBSTACLE_START_TIME = self.config.getint('Game', 'obstacle_start_time')
        self.OBSTACLE_INTERVAL = self.config.getint('Game', 'obstacle_interval')
        self.MAX_OBSTACLES = self.config.getint('Game', 'max_obstacles')
        self.GAME_OVER_REFRESH_RATE = self.config.getint('Game', 'game_over_refresh_rate')
        
        # Snake controls
        self.SNAKE1_CONTROLS = self._get_snake_controls('Snake1')
        self.SNAKE2_CONTROLS = self._get_snake_controls('Snake2')
    
    def _parse_color(self, section, key):
        """Parse color string from config file into RGB tuple"""
        color_str = self.config.get(section, key)
        return tuple(map(int, color_str.split(',')))
    
    def _get_snake_controls(self, section):
        """Get snake controls from config file and convert to pygame key constants"""
        controls = {}
        key_map = {
            'up': pygame.K_UP,
            'down': pygame.K_DOWN,
            'left': pygame.K_LEFT,
            'right': pygame.K_RIGHT,
            'w': pygame.K_w,
            's': pygame.K_s,
            'a': pygame.K_a,
            'd': pygame.K_d
        }
        
        for direction in ['up', 'down', 'left', 'right']:
            key = self.config.get(section, direction)
            controls[direction.upper()] = key_map[key]
        
        return controls 