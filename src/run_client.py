#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接运行在线客户端的脚本，便于测试
"""

import sys
import logging
from loguru import logger

# 自定义过滤器，只允许INFO及以上级别通过
class InfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno >= logging.INFO

# 设置标准库日志级别为INFO
logging.basicConfig(level=logging.INFO)

# 为根日志添加过滤器
root_logger = logging.getLogger()
root_logger.addFilter(InfoFilter())

# 拦截所有标准输出
original_stdout = sys.stdout
original_stderr = sys.stderr

class OutputFilter:
    def __init__(self, original_stream):
        self.original_stream = original_stream
    
    def write(self, text):
        # 只过滤掉DEBUG日志输出
        if "[DEBUG" in text:
            return
        self.original_stream.write(text)
    
    def flush(self):
        self.original_stream.flush()

# 替换标准输出
sys.stdout = OutputFilter(original_stdout)
sys.stderr = OutputFilter(original_stderr)

# 配置loguru
logger.remove()  # 移除默认处理器
# 添加INFO级别的控制台处理器
logger.add(sys.stderr, level="INFO", 
           format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")

# 设置Kivy日志级别
import kivy.logger
kivy.logger.Logger.setLevel(kivy.logger.LOG_LEVELS["info"])

from client_game import OnlineSnakeApp

if __name__ == '__main__':
    logger.info("直接启动在线游戏客户端...")
    OnlineSnakeApp().run() 