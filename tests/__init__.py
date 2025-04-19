#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests Package - Unit tests for Snake Game
"""

import logging
import sys

# Configure logging for tests
logging.basicConfig(level=logging.WARNING, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)

# Disable noisy loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('kivy').setLevel(logging.WARNING)

# Import test modules
from . import test_game_logic
from . import test_network

# This file makes the tests directory a Python package 