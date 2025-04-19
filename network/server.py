#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Server Module - Handles network server operations for Snake Game
"""

import socket
import threading
import time
import uuid
import logging
from network.message import GameMessage
from game.state import GameState
from game.logic import GameLogic

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Snake.Network.Server')

# Default network settings
DEFAULT_HOST = '0.0.0.0'  # Server listens on all network interfaces
DEFAULT_PORT = 7004
BUFFER_SIZE = 4096
HEARTBEAT_INTERVAL = 5  # Heartbeat interval (seconds)
MOVE_INTERVAL = 0.2  # Snake movement interval (seconds)

class GameServer:
    """Game server class, handles client connections and game logic"""
    
    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.clients = {}  # {player_id: (conn, addr)}
        self.games = {}    # {game_id: GameLogic}
        self.waiting_players = []  # List of player IDs waiting for matching
        self.thread = None
        
    def start(self):
        """Start the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)  # Maximum of 5 connections waiting in queue
            self.running = True
            
            logger.info(f"Server started, listening on {self.host}:{self.port}")
            
            # Start accepting clients
            self._accept_clients()
        except Exception as e:
            logger.error(f"Server startup failed: {e}")
            self.stop()
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        # Close connections to all clients
        for client_id, (conn, _) in list(self.clients.items()):
            try:
                conn.close()
            except:
                pass
        
        # Close server socket
        if self.socket:
            self.socket.close()
            self.socket = None
            
        logger.info("Server has stopped")
    
    def _accept_clients(self):
        """Accept client connections"""
        while self.running:
            try:
                conn, addr = self.socket.accept()
                logger.info(f"New connection: {addr}")
                
                # Start a new thread to handle this client
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
                
            except Exception as e:
                if self.running:  # Only log if not intentionally stopped
                    logger.error(f"Error accepting connection: {e}")
    
    def _handle_client(self, conn, addr):
        """Handle client connection"""
        player_id = None
        
        try:
            # Receive initial message
            data = conn.recv(BUFFER_SIZE)
            if not data:
                logger.warning(f"Empty data received from {addr}")
                conn.close()
                return
            
            raw_data = data.decode('utf-8')
            logger.debug(f"Raw data received from client: {raw_data}")
            message = GameMessage.from_json(raw_data)
            
            # Process initial connection
            if message.type == GameMessage.CONNECT:
                # Assign client ID
                player_id = str(uuid.uuid4())
                self.clients[player_id] = (conn, addr)
                
                # Send connection acknowledgment
                self._send_message(conn, GameMessage(
                    GameMessage.CONNECT_ACK,
                    {'player_id': player_id, 'status': 'connected'},
                    player_id
                ))
                
                logger.info(f"Player {player_id} connected from {addr}")
                
                # Add player to waiting queue
                if player_id not in self.waiting_players:
                    self.waiting_players.append(player_id)
                    logger.info(f"Player {player_id} added to waiting queue")
                
                # Try to match players
                self._match_players()
                
                # Listen for further messages
                while self.running:
                    try:
                        data = conn.recv(BUFFER_SIZE)
                        if not data:
                            logger.warning(f"Client {player_id} disconnected (empty data)")
                            break
                        
                        message = GameMessage.from_json(data.decode('utf-8'))
                        self._process_message(message, conn)
                    except ConnectionResetError:
                        logger.warning(f"Client {player_id} connection reset")
                        break
                    except Exception as e:
                        logger.error(f"Error handling message from {player_id}: {e}")
                        logger.exception(e)
            else:
                logger.warning(f"Unexpected initial message type {message.type} from {addr}")
        
        except ConnectionResetError:
            logger.warning(f"Client disconnected during handshake: {addr}")
        except Exception as e:
            logger.error(f"Error handling client connection: {e}")
            logger.exception(e)
        
        # Clean up when client disconnects
        if player_id:
            self._handle_client_disconnect(player_id)
        
        try:
            conn.close()
        except:
            pass
        
        logger.info(f"Connection with {addr} closed")
    
    def _send_message(self, conn, message):
        """Send message to client"""
        try:
            json_data = message.to_json()
            # Add newline as message boundary
            json_data += '\n'
            conn.sendall(json_data.encode('utf-8'))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    def _process_message(self, message, conn):
        """Process incoming message"""
        try:
            player_id = message.client_id
            
            logger.debug(f"Processing message: {message.type} from {player_id}")
            
            # Check if client exists
            if player_id not in self.clients:
                logger.warning(f"Message from unknown player: {player_id}")
                return
            
            # Handle message based on type
            if message.type == GameMessage.CONNECT:
                # New client connection - this should have been handled in _handle_client
                player_id = str(uuid.uuid4())
                self.clients[player_id] = (conn, conn.getpeername())
                logger.info(f"New client connected, assigned ID: {player_id}")
                
                # Send connection acknowledgment
                self._send_message(conn, GameMessage(
                    GameMessage.CONNECT_ACK,
                    {'player_id': player_id},
                    player_id
                ))
                
                # Add to waiting queue
                self.waiting_players.append(player_id)
                logger.info(f"Player {player_id} added to waiting queue")
                
                # Try to match players
                self._match_players()
                
            elif message.type == GameMessage.MATCH:
                # Client requesting match
                if player_id not in self.waiting_players:
                    self.waiting_players.append(player_id)
                    logger.info(f"Player {player_id} requested match, added to waiting queue")
                    
                    # Try to match players
                    self._match_players()
                    
            elif message.type == GameMessage.COMMAND:
                # Command from client
                command_data = message.data
                command_type = command_data.get('command_type')
                game_id = command_data.get('game_id')
                
                logger.debug(f"Received {command_type} command from player {player_id} for game {game_id}")
                
                # Process different command types
                if game_id not in self.games:
                    logger.warning(f"Command for non-existent game: {game_id}")
                    return
                    
                game_logic = self.games[game_id]
                game_state = game_logic.state
                
                if player_id not in game_state.players:
                    logger.warning(f"Player {player_id} not in game {game_id}")
                    return
                
                # Get player index
                player_idx = game_state.players.index(player_id)
                
                result = False
                if command_type == 'direction':
                    direction = command_data.get('direction')
                    logger.debug(f"Direction command from player {player_id} (idx {player_idx}): {direction}")
                    
                    if direction and len(direction) == 2:
                        # Update direction in game state
                        result = game_state.update_direction(player_idx, direction)
                
                # Send command acknowledgment
                self._send_message(conn, GameMessage(
                    GameMessage.COMMAND_ACK,
                    {
                        'command_type': command_type,
                        'result': result
                    },
                    player_id
                ))
                
                logger.debug(f"Command {command_type} processed, result: {result}")
                
            elif message.type == GameMessage.DISCONNECT:
                # Client disconnecting
                self._handle_client_disconnect(player_id)
                
            elif message.type == GameMessage.HEARTBEAT:
                # Heartbeat response
                self._send_message(conn, GameMessage(
                    GameMessage.HEARTBEAT,
                    {},
                    player_id
                ))
                
            else:
                logger.warning(f"Unhandled message type: {message.type}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.exception(e)
    
    def _match_players(self):
        """Match waiting players"""
        with threading.Lock():
            # Need at least two players to make a match
            if len(self.waiting_players) < 2:
                logger.debug(f"Not enough players to match: {len(self.waiting_players)} waiting")
                return
                
            # Take the first two waiting players
            player1_id = self.waiting_players.pop(0)
            player2_id = self.waiting_players.pop(0)
            
            # Make sure both players are still connected
            if player1_id not in self.clients or player2_id not in self.clients:
                # Put any connected player back in the queue
                if player1_id in self.clients:
                    self.waiting_players.append(player1_id)
                if player2_id in self.clients:
                    self.waiting_players.append(player2_id)
                logger.warning("Player disconnected during matching, returning available player to queue")
                return
                
            # Create a new game
            game_id = str(uuid.uuid4())
            logger.info(f"Matching players {player1_id} and {player2_id} in game {game_id}")
            
            # Initialize game state
            game_state = GameState([player1_id, player2_id])
            game_logic = GameLogic(game_state)
            
            # Save game
            self.games[game_id] = game_logic
            
            # Send match acknowledgment to both players
            for i, player_id in enumerate([player1_id, player2_id]):
                conn = self.clients[player_id][0]
                self._send_message(conn, GameMessage(
                    GameMessage.MATCH_ACK,
                    {
                        'game_id': game_id,
                        'player_idx': i,
                        'opponent_id': player2_id if i == 0 else player1_id
                    },
                    player_id
                ))
                logger.debug(f"Match confirmation sent to player {player_id}")
                
            # Wait briefly to ensure match acknowledgments are processed
            time.sleep(0.5)
                
            # Send game start message to both players
            for i, player_id in enumerate([player1_id, player2_id]):
                conn = self.clients[player_id][0]
                self._send_message(conn, GameMessage(
                    GameMessage.GAME_START,
                    {
                        'game_id': game_id,
                        'player_idx': i,
                        'state': game_state.get_serializable_state()
                    },
                    player_id
                ))
                logger.debug(f"Game start message sent to player {player_id}")
            
            # Start game loop
            threading.Thread(target=self._game_loop, args=(game_id,), daemon=True).start()
            logger.info(f"Game loop started for game {game_id}")
    
    def _game_loop(self, game_id):
        """Game main loop for a single game"""
        game_logic = self.games.get(game_id)
        if not game_logic:
            return
            
        game_state = game_logic.state
        game_state.status = 'running'
        
        last_update = time.time()
        move_interval = 0.2  # Move interval in seconds
        
        logger.info(f"Starting game loop for game {game_id}")
        
        # Log initial state
        game_state.log_state()
        
        try:
            while self.running and game_id in self.games:
                now = time.time()
                dt = now - last_update
                
                # Only move snakes at fixed intervals
                if dt >= move_interval:
                    last_update = now
                    
                    # Update game state
                    result = game_logic.update()
                    
                    # Check if game is over
                    if result['game_over']:
                        self._end_game(game_id, result['winner'])
                        return
                    
                    # Send updated state to both players
                    for player_id in game_state.players:
                        if player_id in self.clients:
                            conn = self.clients[player_id][0]
                            self._send_message(conn, GameMessage(
                                GameMessage.GAME_STATE,
                                game_state.get_serializable_state(),
                                player_id
                            ))
                
                # Sleep briefly to reduce CPU usage
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in game loop: {e}")
            logger.exception(e)
            
            # End game with no winner if there's an error
            self._end_game(game_id)
    
    def _heartbeat_checker(self):
        """Check client heartbeats periodically"""
        while self.running:
            try:
                now = time.time()
                
                # Check each client for responsiveness
                for player_id, (conn, _) in list(self.clients.items()):
                    try:
                        # Send heartbeat message
                        self._send_message(conn, GameMessage(
                            GameMessage.HEARTBEAT,
                            {'timestamp': now},
                            player_id
                        ))
                    except:
                        # If sending fails, remove client
                        logger.warning(f"Player {player_id} heartbeat detection failed, removed")
                        self._handle_client_disconnect(player_id)
            except Exception as e:
                logger.error(f"Heartbeat checking error: {e}")
                
            # Sleep for the heartbeat interval
            time.sleep(HEARTBEAT_INTERVAL)
    
    def _end_game(self, game_id, winner_idx=None):
        """End game and notify players
        
        Args:
            game_id: ID of the game to end
            winner_idx: Index of the winner (0 or 1) or None for a draw
        """
        try:
            if game_id not in self.games:
                logger.warning(f"Tried to end non-existent game: {game_id}")
                return
                
            game_logic = self.games[game_id]
            game_state = game_logic.state
            
            # Log game end with detailed results
            logger.info("=" * 50)
            logger.info(f"GAME ENDED - Game ID: {game_id}")
            
            result_msg = ""
            if winner_idx is None:
                result_msg = "Game ended in a draw!"
                logger.info("Result: DRAW")
            else:
                winner_id = game_state.players[winner_idx]
                loser_id = game_state.players[1 - winner_idx]
                winner_score = game_state.scores[winner_idx]
                loser_score = game_state.scores[1 - winner_idx]
                
                result_msg = f"Player {winner_id} wins with score {winner_score} against {loser_score}!"
                logger.info(f"Result: Player {winner_id} WINS")
                logger.info(f"Final Score: {winner_score} - {loser_score}")
            
            # Record game duration
            duration = game_state.game_time
            logger.info(f"Game Duration: {duration:.2f} seconds")
            
            # Log final positions
            logger.debug(f"Final Snake 1 Position: {game_state.snake1}")
            logger.debug(f"Final Snake 2 Position: {game_state.snake2}")
            logger.info("=" * 50)
            
            # Notify players about game end
            for i, player_id in enumerate(game_state.players):
                if player_id in self.clients:
                    conn = self.clients[player_id][0]
                    self._send_message(conn, GameMessage(
                        GameMessage.GAME_END,
                        {
                            'result': 'win' if i == winner_idx else ('draw' if winner_idx is None else 'lose'),
                            'winner': game_state.players[winner_idx] if winner_idx is not None else None,
                            'reason': 'normal',
                            'message': result_msg,
                            'final_state': game_state.get_serializable_state()
                        },
                        player_id
                    ))
                    logger.debug(f"Game end notification sent to player {player_id}")
                    
                    # Add player back to waiting queue
                    if player_id not in self.waiting_players:
                        self.waiting_players.append(player_id)
                        logger.info(f"Player {player_id} added back to waiting queue")
            
            # Remove game
            del self.games[game_id]
            logger.info(f"Game {game_id} removed from active games")
            
            # Try to match players again
            self._match_players()
            
        except Exception as e:
            logger.error(f"Error ending game {game_id}: {e}")
            logger.exception(e)
    
    def _handle_client_disconnect(self, player_id):
        """Handle client disconnect"""
        if not player_id or player_id not in self.clients:
            return
            
        logger.info(f"Player {player_id} disconnected")
        
        # Remove from clients dictionary
        if player_id in self.clients:
            del self.clients[player_id]
            
        # Remove from waiting queue
        if player_id in self.waiting_players:
            self.waiting_players.remove(player_id)
            logger.info(f"Player {player_id} removed from waiting queue")
            
        # Check if player is in a game and end it
        for game_id, game_logic in list(self.games.items()):
            game_state = game_logic.state
            
            if player_id in game_state.players:
                # Get other player index
                player_idx = game_state.players.index(player_id)
                opponent_idx = 1 - player_idx
                opponent_id = game_state.players[opponent_idx]
                
                logger.warning(f"Player {player_id} left game {game_id}, opponent {opponent_id} wins")
                
                # Notify opponent of victory
                if opponent_id in self.clients:
                    conn = self.clients[opponent_id][0]
                    self._send_message(conn, GameMessage(
                        GameMessage.GAME_END,
                        {
                            'result': 'win',
                            'winner': opponent_id,
                            'reason': 'opponent_disconnected',
                            'message': f"Player {player_id} disconnected. You win!",
                            'final_state': game_state.get_serializable_state()
                        },
                        opponent_id
                    ))
                    logger.info(f"Victory notification sent to player {opponent_id}")
                
                # End game
                del self.games[game_id]
                logger.info(f"Game {game_id} removed due to player disconnect")

# Run server if executed directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Snake Game Server')
    parser.add_argument('--host', default=DEFAULT_HOST, help='Server host address')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Server port')
    
    args = parser.parse_args()
    
    server = GameServer(host=args.host, port=args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("Server stopped by user")
        server.stop()
