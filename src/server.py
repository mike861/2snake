#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Snake Game Server Startup Script
"""

import argparse
import socket
import sys
from loguru import logger
from network import GameServer, DEFAULT_PORT, DEFAULT_HOST

# 配置loguru
logger.remove()  # 移除默认处理器
# 添加INFO级别的控制台处理器
logger.add(sys.stderr, level="INFO", 
           format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

def find_available_port(start_port, max_attempts=10):
    """Try to find an available port"""
    for port_offset in range(max_attempts):
        port = start_port + port_offset
        try:
            # Try to bind the port to check availability
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port))
            s.close()
            return port
        except socket.error:
            continue
    return None

if __name__ == "__main__":
    # Configure command line arguments
    parser = argparse.ArgumentParser(description="Snake Game Multiplayer Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Server listening address (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server listening port (default: {DEFAULT_PORT})")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--auto-port", action="store_true", help="Automatically find available port if specified port is in use")
    
    args = parser.parse_args()
    
    # Handle host:port format
    host = args.host
    port = args.port
    
    if ':' in host:
        try:
            host, port_str = host.split(':', 1)
            port = int(port_str)
        except ValueError:
            logger.error(f"Error: Invalid address format '{host}', should be 'host' or 'host:port'")
            exit(1)
    
    # Configure logging level
    if args.debug:
        logger.configure(handlers=[{"sink": sys.stderr, "level": "DEBUG"}])
    
    # Check if port is available, try to find an available port if auto-port is enabled
    if args.auto_port:
        available_port = find_available_port(port)
        if available_port and available_port != port:
            logger.warning(f"Port {port} is in use, using available port {available_port}")
            port = available_port
        elif not available_port:
            logger.error(f"Could not find an available port. Please try specifying a different port manually.")
            exit(1)
    
    # Create and start server
    server = GameServer(host=host, port=port)
    
    logger.info(f"Starting Snake Game Multiplayer Server...")
    logger.info(f"Listening on: {host}:{port}")
    logger.info("Press Ctrl+C to stop the server")
    
    try:
        server.start()
    except socket.error as e:
        if e.errno == 48:  # Address already in use
            logger.error(f"\nError: Port {port} is already in use")
            logger.warning("Please try a different port, or add the --auto-port parameter to find an available port automatically")
        else:
            logger.error(f"\nSocket error: {e}")
        exit(1)
    except KeyboardInterrupt:
        logger.info("\nServer shutting down...")
        server.stop()
        logger.info("Server stopped")
    except Exception as e:
        logger.error(f"Server error: {e}")
        server.stop() 