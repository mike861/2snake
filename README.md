# Goob AI - Multiplayer Snake Game

This project implements a multiplayer snake game using Python, Kivy for the client GUI, and a custom network protocol for communication between the client and server.

## Project Structure

Current project structure:

```
.
├── .gitignore
├── LICENSE
├── README.md
├── main.py               # Main entry point (Server/Test-Client/Tests)
├── logs/                 # Log files (generated at runtime)
├── assets/               # Game assets
├── config/               # Configuration files
├── network/              # Network related code
├── game/                 # Game related code
├── docs/                 # Documentation files
├── src/
│   ├── __init__.py
│   ├── main.py           # Alternative entry point
│   ├── server.py         # Server implementation
│   ├── run_client.py     # Client launcher
│   ├── client_game.py    # GUI client implementation
│   ├── offline_game.py   # Offline game mode
│   ├── network.py        # Network utilities
│   ├── config_manager.py # Configuration manager
│   ├── snake.py          # Snake game logic
│   ├── snake.kv          # Kivy UI definitions
│   ├── sounds/           # Sound assets
│   └── goob_ai/          # Core package structure
│       ├── __init__.py
│       ├── game/
│       │   ├── __init__.py
│       │   ├── client.py  # Kivy GUI Client application
│       │   └── models.py  # Game object models
│       ├── network/
│       │   ├── __init__.py
│       │   ├── client.py  # Core network client logic
│       │   ├── protocol.py # Network message protocol definition
│       │   └── server.py  # Game server logic
│       └── ui/            # UI components
└── tests/
    ├── __init__.py
    ├── test_game_logic.py # Game logic tests
    ├── test_network.py    # Network tests
    └── test_protocol.py   # Protocol tests
```

## Features

*   **Multiplayer:** Supports two players competing in real-time.
*   **Client-Server Architecture:** Decoupled client and server components.
*   **GUI Client:** Interactive graphical user interface built with Kivy.
*   **Network Communication:** Uses sockets and a simple JSON-based protocol for game state synchronization.
*   **Basic Game Logic:** Snakes grow by eating food, game ends on collision with walls or other snakes.
*   **Offline Mode:** Play locally without network connectivity.
*   **Sound Effects:** Audio feedback during gameplay.
*   **Configuration Management:** Customizable settings through config files.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```
2.  **Create a virtual environment:**
    ```bash
    # Using venv (standard Python)
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`

    # Or using uv (recommended)
    uv venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    # Using pip (if using venv)
    pip install kivy
    pip install other-dependencies # Replace with actual dependencies

    # Or using uv (recommended)
    uv pip install kivy
    uv pip install other-dependencies # Replace with actual dependencies
    ```

## Running the Game

### Online Mode

1.  **Start the Server:**
    Open a terminal and run:
    ```bash
    python main.py server --host 0.0.0.0 --port 7004
    ```
    You can change the host and port if needed.

2.  **Start the GUI Client:**
    Open one or two *separate* terminals (for one or two players) and run:
    ```bash
    python src/run_client.py
    ```
    The client application will launch, prompting you to enter the server's host and port (e.g., `localhost` and `7004` if running on the same machine).

### Offline Mode

Run the offline version of the game with:
```bash
python src/offline_game.py
```

### Controls

Use the **W/A/S/D** keys or **Arrow Keys** to control your snake.

## Development

*   **Code Style:** Use Ruff for formatting and linting to ensure consistency.
*   **Testing:** Write tests in the `./tests` directory using pytest.
*   **Dependencies:** Manage dependencies with `uv` and update them as needed.
*   **Configuration:** Use the configuration files in the `config/` directory and environment variables.
*   **Logging:** Use structured logging with output to the `./logs` directory.

## Testing

Run the test suite with:
```bash
python main.py test
```

Or use pytest directly:
```bash
pytest tests/
```

## Documentation

The game protocol and architecture are documented in the UML diagram below:

@startuml Server Data Flow

actor Client
participant Server as S
participant "Client Handler Thread" as CHT
participant "Game Loop Thread" as GLT
database "Game State" as GS

autonumber

Client -> S: Establishes TCP Connection
activate S
S -> CHT: Spawns new thread (_handle_client)
deactivate S
activate CHT

CHT -> Client: Requests Identification (Implicitly waits for CONNECT)
Client -> CHT: Sends CONNECT message (Type: 0) \n (player_id may be new or existing)
CHT -> CHT: _process_message(CONNECT)
CHT -> CHT: _handle_connect(client_id)
note right CHT: Assigns unique client_id if new,\n adds client to `self.clients`,\n adds client to `self.waiting_players`.
CHT -> Client: Sends CONNECT_ACK message (Type: 1) \n with assigned client_id
CHT -> CHT: _find_or_create_game()

alt Game Can Start (2 players waiting)
    CHT -> CHT: Creates new game_id, initial state
    CHT -> GS: Stores initial game state in `self.games[game_id]`
    CHT -> GLT: Spawns new thread (_game_loop)
    activate GLT
    note right CHT: Removes players from `self.waiting_players`
    CHT -> Client: Sends GAME_START message (Type: 2) \n (to both players) \n includes game_id, player index, initial state
else Player Waits
    CHT -> Client: Sends WAITING message (Type: 6)
end

deactivate CHT

loop Game Running
    GLT -> GS: Reads current directions, snake positions, food
    GLT -> GLT: Calculates next snake positions based on directions
    note right GLT: Checks wall collisions,\n self-collisions, \n opponent collisions.
    alt Collision Detected
        GLT -> S: Calls _end_game(game_id, winner_idx)
        activate S
        S -> Client: Sends GAME_OVER message (Type: 4) \n (to both players) \n includes winner, final state
        S -> GS: Removes game from `self.games`
        deactivate S
        GLT -> GLT: Exits loop
        break
    end

    GLT -> GLT: Checks if food is eaten
    opt Food Eaten
        GLT -> GS: Updates score, snake length
        GLT -> GS: Generates new food position
    end

    GLT -> GS: Updates snake positions in game state
    GLT -> Client: Sends GAME_STATE message (Type: 3) \n (to both players) \n contains current snakes, food, scores
    GLT -> GLT: Sleeps briefly (move_interval)
end
deactivate GLT

Client -> CHT: Sends COMMAND message (Type: 5) \n (e.g., direction change)
activate CHT
CHT -> CHT: _process_message(COMMAND)
CHT -> CHT: _handle_command(client_id, game_id, command_data)
CHT -> GS: Updates player's direction in `self.games[game_id]['state']['directions']`
deactivate CHT

Client -> S: Disconnects (TCP FIN/RST)
activate CHT
CHT -> CHT: Detects disconnection in recv loop
CHT -> CHT: _handle_disconnect(client_id)
note right CHT: Removes client from `self.clients`, \n `self.waiting_players`.
opt Client was in a game
    CHT -> S: Calls _end_game(game_id, other_player_idx)
    activate S
    S -> Client: Sends GAME_OVER message (Type: 4) \n (to remaining player)
    S -> GS: Removes game from `self.games`
    deactivate S
end
deactivate CHT

@enduml

## TODO / Future Improvements

*   Set up comprehensive CI/CD pipeline using GitHub Actions
*   Implement proper dependency management with requirements.txt
*   Add more robust error handling and logging
*   Create more comprehensive tests with pytest
*   Refactor code to follow the modular structure in src/goob_ai
*   Implement a scoring system display
*   Refine the network protocol for efficiency
*   Add AI opponents
*   Improve UI/UX (e.g., start screen, settings)
*   Package the application for easier distribution