#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snake Game - Multiplayer network-based snake game
"""

import argparse
import logging
from network.server import GameServer
from network.client import GameClient

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Snake.Main')

def main():
    """Main entry point for the application"""
    parser = argparse.ArgumentParser(description='Snake Game - Multiplayer')
    subparsers = parser.add_subparsers(dest='mode', help='Mode to run the game')
    
    # Server mode arguments
    server_parser = subparsers.add_parser('server', help='Run as server')
    server_parser.add_argument('--host', default='0.0.0.0', help='Host address to bind to')
    server_parser.add_argument('--port', type=int, default=7004, help='Port to listen on')
    
    # Client mode arguments
    client_parser = subparsers.add_parser('client', help='Run as client')
    client_parser.add_argument('--host', default='localhost', help='Server host address')
    client_parser.add_argument('--port', type=int, default=7004, help='Server port')
    
    # Test mode arguments
    test_parser = subparsers.add_parser('test', help='Run unit tests')
    
    args = parser.parse_args()
    
    # Run in the specified mode
    if args.mode == 'server':
        run_server(args.host, args.port)
    elif args.mode == 'client':
        run_client(args.host, args.port)
    elif args.mode == 'test':
        run_tests()
    else:
        parser.print_help()

def run_server(host, port):
    """Run the game server"""
    logger.warning(f"Starting Snake Game server on {host}:{port}")
    server = GameServer(host=host, port=port)
    try:
        server.start()
    except KeyboardInterrupt:
        logger.warning("Server stopped by user")
        server.stop()

def run_client(host, port):
    """Run the game client"""
    import random
    import time
    
    logger.warning(f"Starting Snake Game client, connecting to {host}:{port}")
    client = GameClient(host=host, port=port)
    
    # Set callback functions
    def on_connect(player_id):
        logger.warning(f"Connected as player {player_id}")
        # Request match after connection
        client.request_match()
    
    def on_match(game_id, player_idx, opponent_id):
        logger.warning(f"Matched in game {game_id} as player {player_idx+1} against {opponent_id}")
    
    def on_state_update(state):
        # Just print food position to avoid too much output
        logger.warning(f"Game state updated: food at {state['food']}")
        
        # Get my snake
        my_snake_key = f"snake{client.player_index+1}"
        if my_snake_key in state:
            snake = state[my_snake_key]
            if snake:
                logger.warning(f"My snake head: {snake[0]}, length: {len(snake)}")
    
    def on_game_start(state, player_idx):
        logger.warning(f"Game started, I am player {player_idx+1}")
    
    def on_game_end(data, game_id):
        result = data.get('result')
        logger.warning(f"Game {game_id} ended: {result}")
        
        # Request a new match
        client.request_match()
    
    def on_error(error):
        logger.error(f"Error: {error}")
    
    client.on_connect = on_connect
    client.on_match = on_match
    client.on_state_update = on_state_update
    client.on_game_start = on_game_start
    client.on_game_end = on_game_end
    client.on_error = on_error
    
    # Connect to server
    if client.connect():
        logger.warning("Connected to server, press Ctrl+C to exit")
        
        try:
            # Main loop to send random directions
            while client.is_connected():
                if client.game_id:
                    # Send random direction command every second
                    direction = random.choice([[1, 0], [-1, 0], [0, 1], [0, -1]])
                    client.send_direction(direction)
                    logger.warning(f"Sent direction: {direction}")
                time.sleep(1)
        except KeyboardInterrupt:
            logger.warning("Client stopped by user")
            client.disconnect()
    else:
        logger.error("Failed to connect to server")

def run_tests():
    """Run unit tests"""
    import unittest
    from tests import test_game_logic, test_network
    
    logger.warning("Running Snake Game unit tests")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_game_logic))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_network))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success/failure
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    main() 