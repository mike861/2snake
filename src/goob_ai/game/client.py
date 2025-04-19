import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)


from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivy.properties import (
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from loguru import logger

from src.goob_ai.game.models import Snake
from src.goob_ai.network.client import GameClient
from src.goob_ai.network.protocol import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    GameMessage,
)
from src.goob_ai.ui.widgets import GameOverScreen, ServerInputPopup, WaitingScreen

# Constants
GRID_SIZE = 20  # Size of the grid cells
SNAKE_INITIAL_LENGTH = 3
SNAKE_SPEED = 0.1  # Time interval for snake movement in seconds


class OnlineSnakeGame(Widget):
    """
    Represents the main game widget for the online snake game.

    This class handles the game logic, rendering, and interaction with the network client.
    """

    snakes = ListProperty([])
    food_pos = ListProperty([-1, -1])  # Position of the food
    grid_width = NumericProperty(0)
    grid_height = NumericProperty(0)
    cell_size = NumericProperty(0)
    game_client: Optional[GameClient] = ObjectProperty(None, allownone=True)
    client_id = StringProperty("")
    game_id = StringProperty("")
    player_id = NumericProperty(-1)  # 0 or 1
    game_over = False
    winner = NumericProperty(-1)  # 0 or 1, or -1 if no winner yet
    status_message = StringProperty("Connecting...")

    # Reference to the main App instance
    app_instance = ObjectProperty(None)

    def __init__(self, app_instance: App, **kwargs: Any):
        """
        Initializes the OnlineSnakeGame widget.

        Args:
            app_instance: The main application instance.
            **kwargs: Additional keyword arguments for the Widget class.
        """
        super().__init__(**kwargs)
        self.app_instance = app_instance
        self.snakes = []
        self.food_pos = [-1, -1]
        Window.bind(size=self.update_layout)
        Window.bind(on_keyboard=self.on_key_down)
        self.waiting_screen: Optional[WaitingScreen] = None
        self.game_over_screen: Optional[GameOverScreen] = None
        self.popup: Optional[ServerInputPopup] = None

        Clock.schedule_once(self.show_connection_popup, 0.5)
        logger.info("OnlineSnakeGame initialized.")

    def show_connection_popup(self, _dt: float) -> None:
        """
        Displays the popup for entering server connection details.

        Args:
            _dt: The time delta since the last frame (unused).
        """
        if self.popup:
            self.popup.dismiss()

        logger.info("Showing connection popup.")
        self.popup = ServerInputPopup(
            title="Connect to Server",
            size_hint=(0.8, 0.5),
            auto_dismiss=False,
        )
        self.popup.bind(on_connect=self.connect_to_server)
        self.popup.bind(on_cancel=self.stop_game) # type: ignore
        self.popup.open()

    def connect_to_server(
        self, instance: ServerInputPopup, host: str, port: str
    ) -> None:
        """
        Attempts to connect to the game server.

        Args:
            instance: The popup instance triggering the connection.
            host: The server hostname or IP address.
            port: The server port number.
        """
        logger.info(f"Attempting to connect to server at {host}:{port}")
        self.status_message = f"Connecting to {host}:{port}..."
        try:
            port_int = int(port)
            if self.game_client:
                self.game_client.disconnect()

            self.game_client = GameClient(host=host, port=port_int)
            self.game_client.on_connected = self.on_connected
            self.game_client.on_disconnected = self.on_disconnected
            self.game_client.on_game_start = self.on_game_start
            self.game_client.on_game_state = self.on_game_state
            self.game_client.on_game_over = self.on_game_over
            self.game_client.on_error = self.on_error
            self.game_client.on_waiting = self.on_waiting

            threading.Thread(target=self.game_client.connect, daemon=True).start()

            if instance:
                instance.dismiss()
                self.popup = None

        except ValueError:
            logger.error(f"Invalid port number: {port}")
            self.status_message = "Invalid port number. Please enter a number."
            # Re-open the popup or show an error message
            self.show_error_popup("Invalid Port", "Port must be a number.")
            self.show_connection_popup(0) # Show connection popup again
        except Exception as e:
            logger.exception("Error connecting to server:")
            self.status_message = f"Connection failed: {e}"
            self.show_error_popup("Connection Failed", str(e))
            self.show_connection_popup(0) # Show connection popup again

    def show_error_popup(self, title: str, message: str) -> None:
        """
        Displays an error popup message.

        Args:
            title: The title of the popup window.
            message: The error message to display.
        """
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text=message, size_hint_y=None, height=dp(40)))
        close_button = Button(text='OK', size_hint_y=None, height=dp(40))
        content.add_widget(close_button)
        popup = Popup(title=title, content=content, size_hint=(0.6, 0.3), auto_dismiss=False)
        close_button.bind(on_release=popup.dismiss)
        popup.open()


    def on_connected(self, client_id: str) -> None:
        """
        Callback function executed when the client successfully connects to the server.

        Args:
            client_id: The unique identifier assigned by the server.
        """
        logger.info(f"Connected to server. Client ID: {client_id}")
        self.client_id = client_id
        self.status_message = "Connected. Waiting for opponent..."
        Clock.schedule_once(lambda _dt: self.show_waiting_screen())

    def on_disconnected(self) -> None:
        """
        Callback function executed when the client disconnects from the server.
        """
        logger.warning("Disconnected from server.")
        self.status_message = "Disconnected. Please reconnect."
        self.game_over = True # Treat disconnect as game over
        if not self.game_over_screen or not self.game_over_screen.parent:
            Clock.schedule_once(lambda _dt: self._show_game_over_screen(message="Disconnected from server."), 0)
        if self.waiting_screen:
            self.waiting_screen.dismiss()
            self.waiting_screen = None
        Clock.schedule_once(self.show_connection_popup, 1.0) # Show connect popup after a delay


    def on_waiting(self) -> None:
        """Callback function executed when the server indicates the client is waiting for another player."""
        logger.warning("Waiting for another player.")
        self.status_message = "Waiting for an opponent..."
        Clock.schedule_once(lambda _dt: self.show_waiting_screen())


    def show_waiting_screen(self) -> None:
        """Displays the waiting screen."""
        if self.game_over_screen and self.game_over_screen.parent:
             self.game_over_screen.dismiss()
             self.game_over_screen = None

        if not self.waiting_screen or not self.waiting_screen.parent:
            logger.warning("Showing waiting screen.")
            self.waiting_screen = WaitingScreen(
                size_hint=(0.6, 0.4), auto_dismiss=False
            )
            self.waiting_screen.open()

    def on_game_start(
        self, game_id: str, player_id: int, initial_state: Dict[str, Any]
    ) -> None:
        """
        Callback function executed when the game starts.

        Args:
            game_id: The unique identifier for the game session.
            player_id: The player ID assigned to this client (0 or 1).
            initial_state: The initial state of the game.
        """
        logger.warning(
            f"Game starting! Game ID: {game_id}, Player ID: {player_id}"
        )
        self.game_id = game_id
        self.player_id = player_id
        self.game_over = False
        self.winner = -1
        self.status_message = f"Game started! You are Player {player_id + 1}"

        # Dismiss waiting screen if it exists
        if self.waiting_screen:
            self.waiting_screen.dismiss()
            self.waiting_screen = None
        # Dismiss game over screen if it exists
        if self.game_over_screen:
            self.game_over_screen.dismiss()
            self.game_over_screen = None


        # Process initial state
        self.update_game_state(initial_state)
        Clock.schedule_once(self.update_layout, 0) # Schedule layout update

        # Request focus to capture key events
        Window.request_keyboard(self._keyboard_closed, self)
        Window.bind(on_key_down=self.on_key_down)


    def _keyboard_closed(self) -> None:
        """Handles keyboard closing."""
        logger.warning("Keyboard closed.")
        Window.unbind(on_key_down=self.on_key_down)
        # You might want to re-request keyboard if needed, e.g., when game restarts
        # Window.request_keyboard(self._keyboard_closed, self)


    def on_game_state(self, state: Dict[str, Any]) -> None:
        """
        Callback function executed when a new game state is received from the server.

        Args:
            state: The dictionary representing the current game state.
        """
        if not self.game_over:
            # logger.debug(f"Received game state: {state}")
            Clock.schedule_once(lambda _dt: self.update_game_state(state))

    def on_game_over(self, winner: int, state: Dict[str, Any]) -> None:
        """
        Callback function executed when the game ends.

        Args:
            winner: The player ID of the winner (0 or 1), or -1 for a draw/error.
            state: The final game state.
        """
        logger.warning(f"Game over! Winner: Player {winner + 1}")
        self.game_over = True
        self.winner = winner
        self.update_game_state(state) # Update to final state

        # Determine win/loss/draw message
        if winner == -1:
            message = "Game Over! It's a draw or error."
        elif winner == self.player_id:
            message = "Game Over! You Win!"
        else:
            message = "Game Over! You Lose."

        self.status_message = message
        Clock.schedule_once(lambda _dt, m=message: self._show_game_over_screen(m), 0.5) # Delay slightly

    def _show_game_over_screen(self, message: str) -> None:
        """Shows the game over screen popup."""
        if self.game_over_screen and self.game_over_screen.parent:
            return # Avoid showing multiple popups

        logger.warning("Showing Game Over screen.")
        self.game_over_screen = GameOverScreen(
             title="Game Over",
             message=message,
             size_hint=(0.7, 0.5),
             auto_dismiss=False
         )
        self.game_over_screen.bind(on_play_again=self.play_again)
        self.game_over_screen.bind(on_quit=self.stop_game) # type: ignore
        self.game_over_screen.open()


    def on_error(self, error_message: str) -> None:
        """
        Callback function executed when an error message is received from the server.

        Args:
            error_message: The error message string.
        """
        logger.error(f"Received error from server: {error_message}")
        self.status_message = f"Error: {error_message}"
        # Optionally show an error popup to the user
        self.show_error_popup("Server Error", error_message)
        # Consider if the game should end or attempt recovery
        if "already connected" in error_message.lower():
             # If trying to connect again with the same ID, maybe just ignore or log
             pass
        else:
             # For other errors, maybe treat as disconnect
             self.on_disconnected()


    def update_layout(self, *args: Any) -> None:
        """
        Updates the game layout based on the window size.

        Recalculates grid dimensions and cell size.
        """
        # logger.debug(f"Window resized to: {Window.size}")
        window_width, window_height = Window.size
        # Leave some padding
        padding = dp(20)
        effective_width = window_width - 2 * padding
        effective_height = window_height - 2 * padding - dp(50) # Subtract status bar height

        # Calculate cell size based on the smaller dimension to fit the grid
        cell_size_w = effective_width / GRID_SIZE
        cell_size_h = effective_height / GRID_SIZE
        self.cell_size = min(cell_size_w, cell_size_h)

        if self.cell_size <= 0:
            logger.warning("Calculated zero or negative cell size. Using default.")
            self.cell_size = dp(10) # Fallback cell size

        # Recalculate grid dimensions based on the chosen cell size
        self.grid_width = GRID_SIZE # Keep logical grid size fixed
        self.grid_height = GRID_SIZE

        # Center the game area
        self.canvas_width = self.grid_width * self.cell_size
        self.canvas_height = self.grid_height * self.cell_size
        self.canvas_x = padding + (effective_width - self.canvas_width) / 2
        # Adjust Y position considering the status bar at the top
        self.canvas_y = padding + (effective_height - self.canvas_height) / 2

        # logger.debug(f"Recalculated layout: Grid ({self.grid_width}x{self.grid_height}), Cell Size: {self.cell_size:.2f}, Canvas Pos ({self.canvas_x:.2f}, {self.canvas_y:.2f}), Canvas Size ({self.canvas_width:.2f}x{self.canvas_height:.2f})")

        self.draw_game()

    def transform_coordinates(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """
        Converts grid coordinates to canvas coordinates for drawing.
        Corrects for Kivy's inverted Y-axis if necessary (depends on drawing method).
        Currently assumes standard Kivy coordinates (origin bottom-left).

        Args:
            grid_x: The grid column index.
            grid_y: The grid row index.

        Returns:
            A tuple (canvas_x, canvas_y) representing the bottom-left corner
            of the grid cell on the canvas.
        """
        canvas_x = self.canvas_x + grid_x * self.cell_size
        # Kivy's origin is bottom-left. Grid origin is top-left (typical for 2D arrays).
        # To draw correctly, invert the Y grid coordinate.
        canvas_y = self.canvas_y + (self.grid_height - 1 - grid_y) * self.cell_size
        # logger.warning(f"Transform coordinates: ({grid_x}, {grid_y}) -> ({canvas_x:.1f}, {canvas_y:.1f})")
        return canvas_x, canvas_y


    def draw_game(self) -> None:
        """
        Clears the canvas and redraws all game elements (grid, snakes, food).
        """
        self.canvas.before.clear()
        self.canvas.clear()

        # Set background color
        with self.canvas.before:
            Color(0.1, 0.1, 0.1, 1) # Dark grey background
            Rectangle(pos=self.pos, size=Window.size) # Draw background covering the whole window

        # Log the game center point
        center_x = self.canvas_x + self.canvas_width / 2
        center_y = self.canvas_y + self.canvas_height / 2
        logger.warning(f"Game center point: ({center_x:.1f}, {center_y:.1f})")

        # Draw Game Area Border (optional, for debugging)
        # with self.canvas:
        #     Color(0.5, 0.5, 0.5, 1) # Grey border
        #     Line(rectangle=(self.canvas_x, self.canvas_y, self.canvas_width, self.canvas_height), width=1)

        # Draw Grid Lines (optional)
        # with self.canvas:
        #     Color(0.2, 0.2, 0.2, 1) # Darker grid lines
        #     for i in range(self.grid_width + 1):
        #         x = self.canvas_x + i * self.cell_size
        #         Line(points=[x, self.canvas_y, x, self.canvas_y + self.canvas_height], width=1)
        #     for i in range(self.grid_height + 1):
        #         y = self.canvas_y + i * self.cell_size
        #         Line(points=[self.canvas_x, y, self.canvas_x + self.canvas_width, y], width=1)

        # Draw Snakes
        if not self.game_over or (self.game_over and self.winner != -1): # Draw snakes unless game over screen is up due to disconnect/error
            for snake_index, snake_data in enumerate(self.snakes):
                color = snake_data.color
                logger.warning(f"Drawing snake: {color}, position: {snake_data.body}")
                with self.canvas:
                    Color(*color)
                    for segment in snake_data.body:
                        if isinstance(segment, tuple) and len(segment) == 2:
                           col, row = segment
                           logger.warning(f"Coordinate transform: server({col}, {row}) -> screen coordinates")
                           canvas_x, canvas_y = self.transform_coordinates(col, row)
                           Rectangle(pos=(canvas_x, canvas_y), size=(self.cell_size, self.cell_size))
                        # else:
                        #     logger.warning(f"Invalid snake segment format: {segment}")

        # Draw Food
        if self.food_pos != [-1, -1] and (not self.game_over or (self.game_over and self.winner != -1)):
            with self.canvas:
                Color(1, 0, 0, 1)  # Red food
                logger.warning(f"Drawing food at: ({self.food_pos[0]}, {self.food_pos[1]})")
                canvas_x, canvas_y = self.transform_coordinates(self.food_pos[0], self.food_pos[1])
                Rectangle(pos=(canvas_x, canvas_y), size=(self.cell_size, self.cell_size))

        # Draw Status Message Bar
        with self.canvas:
            Color(0.2, 0.2, 0.2, 0.8) # Semi-transparent dark bar
            status_bar_height = dp(50)
            Rectangle(pos=(0, Window.height - status_bar_height), size=(Window.width, status_bar_height))


    def update_game_state(self, state: Dict[str, Any]) -> None:
        """
        Updates the game state based on data received from the server.

        Args:
            state: A dictionary containing the current game state ('snakes', 'food').
        """
        # logger.debug(f"Updating game state: {state}")
        server_snakes = state.get("snakes", [])
        self.food_pos = state.get("food", [-1, -1])

        # Ensure we have Snake objects for each snake from the server
        while len(self.snakes) < len(server_snakes):
            self.snakes.append(Snake(color=(0,0,0), body=[])) # Placeholder, color updated below
        while len(self.snakes) > len(server_snakes):
            self.snakes.pop()

        # Update snake properties
        for i, server_snake_data in enumerate(server_snakes):
            if isinstance(server_snake_data, dict):
                body = server_snake_data.get("body", [])
                color = server_snake_data.get("color", (0, 1, 0) if i == 0 else (0, 0, 1)) # Default colors
                # Ensure color is a tuple/list of 3 or 4 numbers
                if isinstance(color, (list, tuple)) and len(color) >= 3:
                    self.snakes[i].color = color[:3] # Take RGB
                else:
                    logger.warning(f"Received invalid color format for snake {i}: {color}. Using default.")
                    self.snakes[i].color = (0, 1, 0) if i == 0 else (0, 0, 1)

                # Validate body segments
                valid_body = []
                if isinstance(body, list):
                    for seg in body:
                        if isinstance(seg, (list, tuple)) and len(seg) == 2 and all(isinstance(coord, int) for coord in seg):
                            valid_body.append(tuple(seg))
                        # else:
                        #     logger.warning(f"Invalid segment format in snake {i} body: {seg}")
                else:
                    logger.warning(f"Received invalid body format for snake {i}: {body}")

                self.snakes[i].body = valid_body
                # logger.debug(f"Updated snake {i}: color={self.snakes[i].color}, body_len={len(self.snakes[i].body)}, head={self.snakes[i].body[0] if self.snakes[i].body else 'N/A'}")

            else:
                 logger.warning(f"Received invalid data structure for snake {i}: {server_snake_data}")


        # Update status message based on game state
        if not self.game_over:
             player_scores = [len(s.body) for s in self.snakes]
             score_text = f"Scores: Player 1: {player_scores[0]} | Player 2: {player_scores[1]}" if len(player_scores) == 2 else "Waiting for players..."
             self.status_message = f"Game ID: {self.game_id} | You: P{self.player_id + 1} | {score_text}"
        elif self.winner != -1:
             win_status = "You Win!" if self.winner == self.player_id else "You Lose."
             self.status_message = f"Game Over! {win_status}"
        # else: # Game over but no winner (disconnect/error) - message set in on_disconnected/on_error


        self.draw_game()

        # Update the status label text
        status_label = self.get_status_label()
        if status_label:
            status_label.text = self.status_message

    def get_status_label(self) -> Optional[Label]:
        """Finds the status label widget within the app's root widget."""
        if self.app_instance and self.app_instance.root:
            for widget in self.app_instance.root.walk(restrict=True):
                if isinstance(widget, Label) and hasattr(widget, 'id') and widget.id == 'status_label':
                    return widget
        return None

    def on_key_down(
        self, window: Any, key: int, scancode: int, codepoint: str, modifiers: List[str]
    ) -> bool:
        """
        Handles key press events for controlling the snake.

        Args:
            window: The window instance.
            key: The key code.
            scancode: The hardware scancode.
            codepoint: The character representation of the key.
            modifiers: A list of modifier keys pressed (e.g., 'shift', 'ctrl').

        Returns:
            True if the key event was handled, False otherwise.
        """
        if self.game_over or not self.game_client or not self.game_client.is_connected:
            logger.warning(f"Key press ignored: Game over or not connected. Key: {key}")
            return False # Ignore input if game is over or not connected

        direction = None
        # logger.warning(f"Key down event: key={key}, codepoint='{codepoint}'")
        if key == 273 or codepoint == 'w':  # Up arrow or W
            direction = "UP"
        elif key == 274 or codepoint == 's':  # Down arrow or S
            direction = "DOWN"
        elif key == 276 or codepoint == 'a':  # Left arrow or A
            direction = "LEFT"
        elif key == 275 or codepoint == 'd':  # Right arrow or D
            direction = "RIGHT"
        elif key == 27: # ESC key
             self.stop_game()
             return True

        if direction:
            logger.warning(f"Sending direction command: {direction}")
            command = GameMessage.create_command(self.client_id, self.game_id, direction)
            self.game_client.send_message(command)
            return True # Indicate that the key event has been handled

        return False # Indicate that the key event was not handled here

    def play_again(self, instance: Optional[Any] = None) -> None:
        """
        Handles the "Play Again" action, attempting to reconnect or start a new game.
        """
        logger.warning("Play Again requested.")
        if self.game_over_screen:
            self.game_over_screen.dismiss()
            self.game_over_screen = None

        # Reset game state variables
        self.snakes = []
        self.food_pos = [-1, -1]
        self.game_over = False
        self.winner = -1
        self.game_id = ""
        # Keep client_id, player_id might be reassigned by server
        self.status_message = "Reconnecting..."
        self.draw_game() # Clear the old game state visually


        # If client exists and is disconnected, try reconnecting with existing details
        if self.game_client and not self.game_client.is_connected:
             logger.warning("Client disconnected, attempting to reconnect...")
             host = self.game_client.host
             port = self.game_client.port
             # Disconnect cleanly first if needed, though GameClient likely handles this
             # self.game_client.disconnect()
             self.game_client = None # Clear old client instance
             Clock.schedule_once(lambda _dt: self.connect_to_server(None, host, str(port)), 0.1)


        # If client exists and is connected, send a 'play_again' or 'find_game' message
        # NOTE: This requires server-side support for re-queuing
        elif self.game_client and self.game_client.is_connected:
            logger.warning("Client connected, sending request to find new game.")
            # We reuse the CONNECT message logic server-side to find/create game
            connect_message = GameMessage.create_connect(self.client_id)
            self.game_client.send_message(connect_message)
            self.status_message = "Finding new game..."
            Clock.schedule_once(lambda _dt: self.show_waiting_screen())


        # If no client exists (e.g., initial start or after full stop), show connection popup
        else:
             logger.warning("No active client, showing connection popup.")
             Clock.schedule_once(self.show_connection_popup, 0.1)

    def stop_game(self, instance: Optional[Any] = None) -> None:
        """
        Stops the game client, disconnects, and exits the application.
        """
        logger.warning("Stop game requested.")
        if self.game_client:
            self.game_client.disconnect()
        if self.popup:
            self.popup.dismiss()
            self.popup = None
        if self.waiting_screen:
            self.waiting_screen.dismiss()
            self.waiting_screen = None
        if self.game_over_screen:
            self.game_over_screen.dismiss()
            self.game_over_screen = None

        # Unbind keyboard listener
        Window.unbind(on_key_down=self.on_key_down)

        # Stop the Kivy application
        if self.app_instance:
            self.app_instance.stop()
        else:
             # Fallback if app_instance is not set
             App.get_running_app().stop()


class SnakeApp(App):
    """
    The main Kivy application class for the online snake game.
    """
    game_widget: Optional[OnlineSnakeGame] = None
    status_label: Optional[Label] = None

    def build(self) -> FloatLayout:
        """
        Builds the Kivy application UI.

        Returns:
            The root widget of the application.
        """
        logger.warning("Building SnakeApp UI...")
        root = FloatLayout()

        # Create the game widget and pass the app instance
        self.game_widget = OnlineSnakeGame(app_instance=self, size_hint=(1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        root.add_widget(self.game_widget)

        # Create and add the status label dynamically
        self.status_label = Label(
            text="Initializing...",
            size_hint=(1, None),
            height=dp(50),
            pos_hint={'top': 1},
            halign='center',
            valign='middle',
            id='status_label' # Add an ID for easier lookup
        )
        # Ensure the label background (drawn in game_widget) is behind the text
        self.status_label.bind(size=self.status_label.setter('text_size')) # For text alignment
        root.add_widget(self.status_label) # Add status label on top

        # Set initial status message in the game widget
        if self.game_widget:
            self.game_widget.status_message = "Initializing connection..."
            # Update the label text initially
            Clock.schedule_once(lambda dt: self.update_status_label(self.game_widget.status_message), 0.1)


        logger.warning("SnakeApp UI built.")
        return root

    def update_status_label(self, text: str) -> None:
        """Updates the text of the status label."""
        if self.status_label:
            self.status_label.text = text
            # logger.warning(f"Status label updated: {text}")


    def on_start(self) -> None:
        """Called when the application starts."""
        logger.warning("SnakeApp started.")
        # You could potentially trigger the first connection attempt here
        # if self.game_widget:
        #     Clock.schedule_once(self.game_widget.show_connection_popup, 0.5)
        pass


    def on_stop(self) -> None:
        """
        Called when the application is stopped. Ensures clean disconnection.
        """
        logger.warning("SnakeApp stopping.")
        if self.game_widget:
            self.game_widget.stop_game()


# Main execution block
if __name__ == "__main__":
    # Configure Loguru
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.remove() # Remove default handler
     # Log WARNING and above to console
    logger.add(sys.stderr, level="WARNING", format=log_format)
    # Log DEBUG and above to file
    logger.add("logs/client_{time}.log", level="DEBUG", rotation="1 day", retention="7 days", format=log_format)

    # Configure Kivy logger to use WARNING level
    import kivy.logger
    kivy.logger.Logger.setLevel(kivy.logger.LOG_LEVELS["warning"])
    # Disable Kivy's default log handler to avoid duplicate logs
    kivy.logger.Logger.handlers = []
    # Add a custom handler that directs Kivy logs to our logger
    class LoguruHandler(logging.Handler):
        def emit(self, record):
            msg = self.format(record)
            logger.opt(depth=1).log("WARNING", msg)
    
    kivy_handler = LoguruHandler()
    kivy.logger.Logger.addHandler(kivy_handler)

    logger.warning("Starting SnakeApp...")
    try:
        SnakeApp().run()
    except Exception as e:
        logger.exception("Unhandled exception in SnakeApp:")
    finally:
        logger.warning("SnakeApp finished.") 