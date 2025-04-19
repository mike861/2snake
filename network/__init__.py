#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Network Package - Provides multiplayer networking functionality for Snake Game
"""

from network.message import GameMessage
from network.client import GameClient
from network.server import GameServer

# Package constants
DEFAULT_HOST = '0.0.0.0'  # Server listens on all network interfaces
DEFAULT_PORT = 7004
