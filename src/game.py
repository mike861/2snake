import pygame
import random
import sys
import os
from src.snake import Snake
from src.config_manager import ConfigManager

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()  # Initialize sound system
        self.config = ConfigManager()
        self.screen = pygame.display.set_mode((self.config.WINDOW_WIDTH, self.config.WINDOW_HEIGHT))
        pygame.display.set_caption('Two Player Snake Game')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)  # Use default font, size 36
        self.load_sounds()
        self.init_game()

    def load_sounds(self):
        # Load sound files
        sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
        try:
            self.eat_sound = pygame.mixer.Sound(os.path.join(sounds_dir, 'eat.wav'))
            self.collision_sound = pygame.mixer.Sound(os.path.join(sounds_dir, 'collision.wav'))
        except:
            print("Warning: Sound files not found. Creating game without sounds.")
            self.eat_sound = None
            self.collision_sound = None

    def init_game(self):
        self.game_time = 0  # Game time in seconds
        self.score1 = 0     # Player 1 score
        self.score2 = 0     # Player 2 score
        self.start_time = pygame.time.get_ticks()  # Game start time
        self.obstacles = []  # List of obstacles
        self.last_obstacle_time = 0  # Last time obstacles were generated
        
        self.snake1 = Snake(self.config.GREEN, 
                          [self.config.GRID_WIDTH//4, self.config.GRID_HEIGHT//2],
                          self.config.SNAKE1_CONTROLS,
                          self.config.BASE_SPEED)
        
        self.snake2 = Snake(self.config.BLUE, 
                          [3*self.config.GRID_WIDTH//4, self.config.GRID_HEIGHT//2],
                          self.config.SNAKE2_CONTROLS,
                          self.config.BASE_SPEED)
        
        self.food = self.spawn_food()

    def spawn_food(self):
        while True:
            pos = [random.randint(0, self.config.GRID_WIDTH-1), 
                  random.randint(0, self.config.GRID_HEIGHT-1)]
            if (pos not in self.obstacles and 
                pos not in self.snake1.body and 
                pos not in self.snake2.body):
                return pos

    def spawn_obstacle(self):
        if len(self.obstacles) >= self.config.MAX_OBSTACLES:
            return
        
        for _ in range(10):  # Try 10 times to find a suitable position
            pos = [random.randint(0, self.config.GRID_WIDTH-1), 
                  random.randint(0, self.config.GRID_HEIGHT-1)]
            if (pos != self.food and 
                pos not in self.obstacles and 
                pos not in self.snake1.body and 
                pos not in self.snake2.body):
                self.obstacles.append(pos)
                return

    def handle_collisions(self):
        # Check for food collision
        if self.snake1.body[0] == self.food:
            self.snake1.grow = True
            self.snake1.start_eat_animation()  # Start animation
            self.score1 += self.config.FOOD_SCORE
            if self.eat_sound:
                self.eat_sound.play()
            self.food = self.spawn_food()
        if self.snake2.body[0] == self.food:
            self.snake2.grow = True
            self.snake2.start_eat_animation()  # Start animation
            self.score2 += self.config.FOOD_SCORE
            if self.eat_sound:
                self.eat_sound.play()
            self.food = self.spawn_food()
            
        # Check for obstacle collisions
        if self.snake1.body[0] in self.obstacles:
            if self.collision_sound:
                self.collision_sound.play()
            return "Player 2 Wins! (P1 hit obstacle)"
        if self.snake2.body[0] in self.obstacles:
            if self.collision_sound:
                self.collision_sound.play()
            return "Player 1 Wins! (P2 hit obstacle)"
            
        # Check for snake collisions
        if self.snake1.body[0] in self.snake1.body[1:] or self.snake1.body[0] in self.snake2.body:
            if self.collision_sound:
                self.collision_sound.play()
            return "Player 2 Wins!"
        if self.snake2.body[0] in self.snake2.body[1:] or self.snake2.body[0] in self.snake1.body:
            if self.collision_sound:
                self.collision_sound.play()
            return "Player 1 Wins!"
        return None

    def draw_info(self):
        # Update game time
        current_time = pygame.time.get_ticks()
        self.game_time = (current_time - self.start_time) // 1000
        
        # Draw time
        time_text = f"Time: {self.game_time}s"
        time_surface = self.font.render(time_text, True, self.config.WHITE)
        self.screen.blit(time_surface, (self.config.WINDOW_WIDTH//2 - 50, 10))
        
        # Draw scores
        score1_text = f"P1: {self.score1}"
        score2_text = f"P2: {self.score2}"
        score1_surface = self.font.render(score1_text, True, self.config.GREEN)
        score2_surface = self.font.render(score2_text, True, self.config.BLUE)
        self.screen.blit(score1_surface, (10, 10))
        self.screen.blit(score2_surface, (self.config.WINDOW_WIDTH - 100, 10))

    def draw(self):
        self.screen.fill(self.config.BLACK)
        
        # Draw food
        pygame.draw.rect(self.screen, self.config.RED, 
                        (self.food[0]*self.config.GRID_SIZE, 
                         self.food[1]*self.config.GRID_SIZE, 
                         self.config.GRID_SIZE-2, self.config.GRID_SIZE-2))
        
        # Draw obstacles
        for obstacle in self.obstacles:
            pygame.draw.rect(self.screen, self.config.GRAY,
                           (obstacle[0]*self.config.GRID_SIZE, 
                            obstacle[1]*self.config.GRID_SIZE,
                            self.config.GRID_SIZE-2, self.config.GRID_SIZE-2))
        
        # Draw snake1
        for i, segment in enumerate(self.snake1.body):
            if i == 0 and self.snake1.is_animating:  # If it's the snake head and animating
                # Calculate enlarged size and position offset
                size = int(self.config.GRID_SIZE * self.snake1.head_scale)
                offset = (size - self.config.GRID_SIZE) // 2
                pygame.draw.rect(self.screen, self.snake1.color,
                               (segment[0]*self.config.GRID_SIZE - offset, 
                                segment[1]*self.config.GRID_SIZE - offset,
                                size-2, size-2))
            else:
                pygame.draw.rect(self.screen, self.snake1.color,
                               (segment[0]*self.config.GRID_SIZE, 
                                segment[1]*self.config.GRID_SIZE,
                                self.config.GRID_SIZE-2, self.config.GRID_SIZE-2))
        
        # Draw snake2
        for i, segment in enumerate(self.snake2.body):
            if i == 0 and self.snake2.is_animating:  # If it's the snake head and animating
                # Calculate enlarged size and position offset
                size = int(self.config.GRID_SIZE * self.snake2.head_scale)
                offset = (size - self.config.GRID_SIZE) // 2
                pygame.draw.rect(self.screen, self.snake2.color,
                               (segment[0]*self.config.GRID_SIZE - offset, 
                                segment[1]*self.config.GRID_SIZE - offset,
                                size-2, size-2))
            else:
                pygame.draw.rect(self.screen, self.snake2.color,
                               (segment[0]*self.config.GRID_SIZE, 
                                segment[1]*self.config.GRID_SIZE,
                                self.config.GRID_SIZE-2, self.config.GRID_SIZE-2))
        
        # Draw timer and scores
        self.draw_info()
        
        pygame.display.flip()

    def draw_game_over(self, result):
        # Create semi-transparent black overlay
        overlay = pygame.Surface((self.config.WINDOW_WIDTH, self.config.WINDOW_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(self.config.BLACK)
        self.screen.blit(overlay, (0, 0))
        
        # Display game over information
        game_over_text = f"{result}"
        score_text = f"Final Scores - P1: {self.score1}, P2: {self.score2}"
        time_text = f"Time: {self.game_time}s"
        press_esc_text = "Press ESC to exit"
        
        game_over_surface = self.font.render(game_over_text, True, self.config.WHITE)
        score_surface = self.font.render(score_text, True, self.config.WHITE)
        time_surface = self.font.render(time_text, True, self.config.WHITE)
        press_esc_surface = self.font.render(press_esc_text, True, self.config.WHITE)
        
        # Calculate text positions for center alignment
        center_y = self.config.WINDOW_HEIGHT // 2 - 80
        self.screen.blit(game_over_surface, 
                        (self.config.WINDOW_WIDTH//2 - game_over_surface.get_width()//2, center_y))
        self.screen.blit(score_surface, 
                        (self.config.WINDOW_WIDTH//2 - score_surface.get_width()//2, center_y + 40))
        self.screen.blit(time_surface, 
                        (self.config.WINDOW_WIDTH//2 - time_surface.get_width()//2, center_y + 80))
        self.screen.blit(press_esc_surface, 
                        (self.config.WINDOW_WIDTH//2 - press_esc_surface.get_width()//2, center_y + 140))
        
        pygame.display.flip()

    def run(self):
        game_over = False
        result = None
        last_draw_time = 0
        
        while True:
            current_time = pygame.time.get_ticks()
            dt = self.clock.tick(self.config.FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            
            if not game_over:
                self.game_time = (current_time - self.start_time) // 1000
                
                # Update snake animations
                self.snake1.update_animation(dt)
                self.snake2.update_animation(dt)
                
                # Handle obstacle generation
                if (self.game_time >= self.config.OBSTACLE_START_TIME and
                    self.game_time - self.last_obstacle_time >= self.config.OBSTACLE_INTERVAL):
                    self.spawn_obstacle()
                    self.last_obstacle_time = self.game_time
                
                # Handle input
                keys = pygame.key.get_pressed()
                self.snake1.handle_keys(keys)
                self.snake2.handle_keys(keys)
                
                # Move snakes independently based on their speed
                if self.snake1.should_move(dt):
                    self.snake1.move()
                if self.snake2.should_move(dt):
                    self.snake2.move()
                
                # Check collisions
                result = self.handle_collisions()
                if result:
                    game_over = True
                    self.draw()
                    self.draw_game_over(result)
                else:
                    self.draw()
            else:
                if current_time - last_draw_time >= self.config.GAME_OVER_REFRESH_RATE:
                    self.draw()
                    self.draw_game_over(result)
                    last_draw_time = current_time

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main() 