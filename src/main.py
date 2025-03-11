from kivy.app import App
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.properties import NumericProperty, BooleanProperty, StringProperty
from kivy.vector import Vector
from kivy.graphics import Color, Rectangle, Line
import os
import random

# 字体设置
from kivy.core.text import Label as CoreLabel
# 不重置默认字体，直接使用系统字体
print("使用系统默认字体")

class Snake:
    def __init__(self, color, start_pos, is_player_one=True):
        self.color = color
        self.body = [start_pos]
        self.direction = Vector(1, 0)
        self.grow = False
        self.is_player_one = is_player_one
        self.base_speed = 6
        self.head_scale = 1.0
        self.is_animating = False
        self.animation_time = 0
    
    def get_speed(self):
        return self.base_speed + (len(self.body) - 1) * 0.5
    
    def move(self, grid_width, grid_height):
        new_head = [
            (self.body[0][0] + self.direction[0]) % grid_width,
            (self.body[0][1] + self.direction[1]) % grid_height
        ]
        
        if self.grow:
            self.body = [new_head] + self.body
            self.grow = False
        else:
            self.body = [new_head] + self.body[:-1]
    
    def update_animation(self, dt):
        if not self.is_animating:
            return
        
        self.animation_time += dt * 1000
        total_animation_time = 300
        
        if self.animation_time <= total_animation_time / 2:
            progress = self.animation_time / (total_animation_time / 2)
            self.head_scale = 1.0 + (0.5 * progress)
        else:
            progress = (self.animation_time - total_animation_time / 2) / (total_animation_time / 2)
            self.head_scale = 1.5 - (0.5 * progress)
        
        if self.animation_time >= total_animation_time:
            self.is_animating = False
            self.head_scale = 1.0
    
    def start_eat_animation(self):
        self.is_animating = True
        self.animation_time = 0
        self.head_scale = 1.0

class SnakeGame(Widget):
    score1 = NumericProperty(0)
    score2 = NumericProperty(0)
    game_time = NumericProperty(0)
    game_over = BooleanProperty(False)
    game_over_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # UI area height at top
        self.ui_height = 60
        
        # Game area dimensions
        self.grid_size = 20
        self.grid_width = Window.width // self.grid_size
        self.grid_height = (Window.height - self.ui_height) // self.grid_size
        
        # Initialize game state
        self.obstacles = []
        self.snake1 = None
        self.snake2 = None
        self.food = None
        self.last_obstacle_time = 0
        self.start_time = 0
        self.move_timers = {}
        self.final_time = 0
        
        # Load sounds
        self.load_sounds()
        
        # Initialize game
        self.reset_game()
        
        # Schedule updates
        Clock.schedule_interval(self.update, 1.0/60.0)
        
        # Touch controls for mobile
        self.touch_start_pos = None
        
        # Keyboard controls for desktop
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)

    def render_text(self, text, x, y, color=(1,1,1,1), font_size=24):
        # 文本渲染方法，使用Canvas直接渲染
        try:
            # 创建标签
            label = CoreLabel(text=str(text), font_size=font_size)
            label.refresh()
            
            # 检查纹理是否创建成功
            if label.texture:
                with self.canvas:
                    Color(*color)
                    Rectangle(
                        texture=label.texture,
                        pos=(x - label.texture.width/2, y - label.texture.height/2),
                        size=label.texture.size
                    )
                return True
            return False
        except Exception as e:
            print(f"文本渲染失败: {e}")
            return False

    def load_sounds(self):
        self.eat_sound = None
        self.collision_sound = None
        
        try:
            sounds_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds')
            
            eat_sound_path = os.path.join(sounds_dir, 'eat.wav')
            if os.path.exists(eat_sound_path):
                self.eat_sound = SoundLoader.load(eat_sound_path)
            
            collision_sound_path = os.path.join(sounds_dir, 'collision.wav')
            if os.path.exists(collision_sound_path):
                self.collision_sound = SoundLoader.load(collision_sound_path)
        except:
            # Silent fail if sounds can't be loaded
            pass

    def reset_game(self):
        # Define colors
        self.food_color = (1, 0, 0, 1)  # Red
        
        # Start positions adjusted for UI area
        p1_start_x = self.grid_width // 4
        p1_start_y = self.grid_height // 2
        p2_start_x = 3 * self.grid_width // 4
        p2_start_y = self.grid_height // 2
        
        self.snake1 = Snake((0, 1, 0, 1), [p1_start_x, p1_start_y], True)
        self.snake2 = Snake((0, 0, 1, 1), [p2_start_x, p2_start_y], False)
        self.food = self.spawn_food()
        self.obstacles = []
        self.last_obstacle_time = 0
        self.start_time = Clock.get_boottime()
        self.score1 = 0
        self.score2 = 0
        self.game_time = 0
        self.final_time = 0
        self.game_over = False
        self.move_timers = {self.snake1: 0, self.snake2: 0}
        
        # Initial draw
        self.draw()

    def spawn_food(self):
        while True:
            pos = [random.randint(0, self.grid_width-1), 
                  random.randint(0, self.grid_height-1)]
            
            # Check if position is free
            if (pos not in self.snake1.body and 
                pos not in self.snake2.body and 
                pos not in self.obstacles):
                return pos

    def spawn_obstacle(self):
        for _ in range(3):  # Try to spawn 3 obstacles
            for _ in range(10):  # Try 10 times max per obstacle
                pos = [random.randint(0, self.grid_width-1), 
                      random.randint(0, self.grid_height-1)]
                
                # Check if position is free
                if (pos not in self.snake1.body and 
                    pos not in self.snake2.body and 
                    pos != self.food and 
                    pos not in self.obstacles):
                    self.obstacles.append(pos)
                    break

    def handle_collisions(self):
        # Food collisions
        for snake, score_attr in [(self.snake1, 'score1'), (self.snake2, 'score2')]:
            if snake.body[0] == self.food:
                snake.grow = True
                snake.start_eat_animation()
                setattr(self, score_attr, getattr(self, score_attr) + 10)
                if self.eat_sound:
                    self.eat_sound.play()
                self.food = self.spawn_food()
        
        # Store final time when game ends
        if not self.game_over:
            self.final_time = self.game_time
        
        # Obstacle collisions
        if self.snake1.body[0] in self.obstacles:
            if self.collision_sound:
                self.collision_sound.play()
            self.game_over = True
            self.game_over_text = "Player 2 Wins! (P1 hit obstacle)"
            return True
            
        if self.snake2.body[0] in self.obstacles:
            if self.collision_sound:
                self.collision_sound.play()
            self.game_over = True
            self.game_over_text = "Player 1 Wins! (P2 hit obstacle)"
            return True
        
        # Snake collisions
        if (self.snake1.body[0] in self.snake1.body[1:] or 
            self.snake1.body[0] in self.snake2.body):
            if self.collision_sound:
                self.collision_sound.play()
            self.game_over = True
            self.game_over_text = "Player 2 Wins!"
            return True
            
        if (self.snake2.body[0] in self.snake2.body[1:] or 
            self.snake2.body[0] in self.snake1.body):
            if self.collision_sound:
                self.collision_sound.play()
            self.game_over = True
            self.game_over_text = "Player 1 Wins!"
            return True
        
        return False

    def draw(self, *args):
        self.canvas.clear()
        
        with self.canvas:
            # Draw UI background
            Color(0.2, 0.2, 0.2, 1)  # Dark gray
            Rectangle(pos=(0, Window.height - self.ui_height), 
                     size=(Window.width, self.ui_height))
            
            # Draw game area
            Color(0, 0, 0, 1)  # Black
            Rectangle(pos=(0, 0), 
                     size=(Window.width, Window.height - self.ui_height))
            
            # 尝试使用文本渲染
            if (self.render_text(f'P1: {self.score1}', 100, Window.height - self.ui_height/2, (0,1,0,1), 24) and 
                self.render_text(f'Time: {self.game_time}s', Window.width/2, Window.height - self.ui_height/2, (1,1,1,1), 24) and 
                self.render_text(f'P2: {self.score2}', Window.width-100, Window.height - self.ui_height/2, (0,0,1,1), 24)):
                pass  # 如果文本渲染成功，不再使用图形方式
            else:
                # 如果文本渲染失败，使用图形方式显示分数
                self.draw_simple_scores()
            
            # Draw food
            Color(*self.food_color)
            Rectangle(pos=(self.food[0]*self.grid_size, self.food[1]*self.grid_size),
                     size=(self.grid_size-2, self.grid_size-2))
            
            # Draw obstacles
            Color(0.5, 0.5, 0.5, 1)  # Gray
            for obstacle in self.obstacles:
                Rectangle(pos=(obstacle[0]*self.grid_size, obstacle[1]*self.grid_size),
                         size=(self.grid_size-2, self.grid_size-2))
            
            # Draw snake1
            Color(*self.snake1.color)
            for i, segment in enumerate(self.snake1.body):
                if i == 0 and self.snake1.is_animating:
                    size = int(self.grid_size * self.snake1.head_scale)
                    offset = (size - self.grid_size) // 2
                    Rectangle(pos=(segment[0]*self.grid_size - offset,
                                 segment[1]*self.grid_size - offset),
                            size=(size-2, size-2))
                else:
                    Rectangle(pos=(segment[0]*self.grid_size,
                                 segment[1]*self.grid_size),
                            size=(self.grid_size-2, self.grid_size-2))
            
            # Draw snake2
            Color(*self.snake2.color)
            for i, segment in enumerate(self.snake2.body):
                if i == 0 and self.snake2.is_animating:
                    size = int(self.grid_size * self.snake2.head_scale)
                    offset = (size - self.grid_size) // 2
                    Rectangle(pos=(segment[0]*self.grid_size - offset,
                                 segment[1]*self.grid_size - offset),
                            size=(size-2, size-2))
                else:
                    Rectangle(pos=(segment[0]*self.grid_size,
                                 segment[1]*self.grid_size),
                            size=(self.grid_size-2, self.grid_size-2))
            
            # Draw game over overlay if game is over
            if self.game_over:
                # Semi-transparent overlay
                Color(0, 0, 0, 0.7)
                Rectangle(pos=(0, 0), size=(Window.width, Window.height))
                
                # 尝试使用文本渲染游戏结束信息
                if (self.render_text(self.game_over_text, Window.width/2, Window.height/2 + 50, (1,1,1,1), 36) and 
                    self.render_text(f'P1: {self.score1}  P2: {self.score2}  Time: {self.game_time}s', Window.width/2, Window.height/2, (1,1,1,1), 24) and 
                    self.render_text('Press SPACE or tap to restart', Window.width/2, Window.height/4, (1,0.8,0.2,1), 24)):
                    pass  # 如果文本渲染成功，不再使用图形方式
                else:
                    # 如果文本渲染失败，使用图形方式显示游戏结束
                    self.draw_simple_game_over()

    def draw_simple_scores(self):
        # Draw P1 score - Green blocks
        Color(0, 1, 0, 1)
        for i in range(self.score1 // 10):
            if i < 10:  # Limit display to 10 blocks
                Rectangle(pos=(10 + i*20, Window.height - self.ui_height + 20), 
                         size=(15, 20))
        
        # Draw time - White blocks
        Color(1, 1, 1, 1)
        for i in range(min(10, self.game_time // 5)):
            Rectangle(pos=(Window.width/2 - 100 + i*20, Window.height - self.ui_height + 20), 
                     size=(15, 20))
        
        # Draw P2 score - Blue blocks
        Color(0, 0, 1, 1)
        for i in range(self.score2 // 10):
            if i < 10:  # Limit display to 10 blocks
                Rectangle(pos=(Window.width - 200 + i*20, Window.height - self.ui_height + 20), 
                         size=(15, 20))

    def draw_simple_game_over(self):
        # Choose color based on winner
        if "Player 1 Wins" in self.game_over_text:
            Color(0, 1, 0, 1)  # Green
        else:
            Color(0, 0, 1, 1)  # Blue
            
        # Draw winner indicator - big square in center
        Rectangle(pos=(Window.width/2 - 50, Window.height/2 - 50), 
                 size=(100, 100))
                 
        # Draw "restart" indicator - yellow bar at bottom
        Color(1, 1, 0, 1)
        Rectangle(pos=(Window.width/2 - 100, Window.height/4 - 25), 
                 size=(200, 50))

    def update(self, dt):
        # Update game time
        if not self.game_over:
            self.game_time = int(Clock.get_boottime() - self.start_time)
        else:
            self.game_time = self.final_time
        
        if self.game_over:
            self.draw()  # Keep drawing to show game over screen
            return
        
        # Update snake animations
        self.snake1.update_animation(dt)
        self.snake2.update_animation(dt)
        
        # Handle obstacle generation
        if (self.game_time >= 20 and 
            self.game_time - self.last_obstacle_time >= 10):
            self.spawn_obstacle()
            self.last_obstacle_time = self.game_time
        
        # Move snakes
        for snake in [self.snake1, self.snake2]:
            self.move_timers[snake] += dt
            if self.move_timers[snake] >= 1.0 / snake.get_speed():
                snake.move(self.grid_width, self.grid_height)
                self.move_timers[snake] = 0
        
        # Check collisions
        if self.handle_collisions():
            self.draw()  # Draw final state with overlay
            return
        
        # Update the display
        self.draw()

    def on_touch_down(self, touch):
        if self.game_over:
            self.reset_game()
            return True
            
        self.touch_start_pos = touch.pos
        return True

    def on_touch_up(self, touch):
        if not self.touch_start_pos:
            return True
            
        # Calculate direction
        dx = touch.x - self.touch_start_pos[0]
        dy = touch.y - self.touch_start_pos[1]
        
        # Determine which half of the screen was touched
        is_left_half = self.touch_start_pos[0] < Window.width / 2
        
        # Determine primary direction
        if abs(dx) > abs(dy):
            # Horizontal swipe
            direction = Vector(1, 0) if dx > 0 else Vector(-1, 0)
        else:
            # Vertical swipe
            direction = Vector(0, 1) if dy > 0 else Vector(0, -1)
        
        # Apply direction to the corresponding snake
        if is_left_half:
            # Don't allow reversing
            if direction[0] != -self.snake1.direction[0] or direction[1] != -self.snake1.direction[1]:
                self.snake1.direction = direction
        else:
            # Don't allow reversing
            if direction[0] != -self.snake2.direction[0] or direction[1] != -self.snake2.direction[1]:
                self.snake2.direction = direction
                
        return True

    def _on_keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        if self.game_over:
            if keycode[1] == 'spacebar':
                self.reset_game()
            return True
            
        # Player 1 controls (WASD)
        if keycode[1] == 'w' and self.snake1.direction[1] != -1:
            self.snake1.direction = Vector(0, 1)
        elif keycode[1] == 's' and self.snake1.direction[1] != 1:
            self.snake1.direction = Vector(0, -1)
        elif keycode[1] == 'a' and self.snake1.direction[0] != 1:
            self.snake1.direction = Vector(-1, 0)
        elif keycode[1] == 'd' and self.snake1.direction[0] != -1:
            self.snake1.direction = Vector(1, 0)
            
        # Player 2 controls (Arrow keys)
        elif keycode[1] == 'up' and self.snake2.direction[1] != -1:
            self.snake2.direction = Vector(0, 1)
        elif keycode[1] == 'down' and self.snake2.direction[1] != 1:
            self.snake2.direction = Vector(0, -1)
        elif keycode[1] == 'left' and self.snake2.direction[0] != 1:
            self.snake2.direction = Vector(-1, 0)
        elif keycode[1] == 'right' and self.snake2.direction[0] != -1:
            self.snake2.direction = Vector(1, 0)
            
        return True

class SnakeApp(App):
    def build(self):
        # Set window size
        Window.size = (800, 600)
        # Set window title
        self.title = 'Two Player Snake Game'
        # Create and return game instance
        return SnakeGame()
    
    def build_config(self, config):
        config.setdefaults('graphics', {
            'width': '800',
            'height': '600',
            'fullscreen': '0'
        })

if __name__ == '__main__':
    SnakeApp().run() 