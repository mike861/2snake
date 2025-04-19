#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
键盘输入测试程序 - 用于验证键盘事件是否正常工作
"""

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
import logging

# 设置日志
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Snake.KeyboardTest')

class KeyboardTestWidget(Widget):
    def __init__(self, **kwargs):
        super(KeyboardTestWidget, self).__init__(**kwargs)
        
        # 创建一个标签用于显示按键信息
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.key_label = Label(
            text="按下任意键...",
            font_size=24,
            halign='center',
            valign='middle',
            size_hint=(1, 0.5)
        )
        self.key_history = Label(
            text="按键历史:\n",
            font_size=18,
            halign='left',
            valign='top',
            size_hint=(1, 0.5)
        )
        self.layout.add_widget(self.key_label)
        self.layout.add_widget(self.key_history)
        self.add_widget(self.layout)
        
        # 注册键盘事件
        self._keyboard = Window.request_keyboard(self._on_keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        
        # 按键历史记录
        self.history = []
        
        # 背景颜色
        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 1)  # 深灰色背景
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_rect, size=self._update_rect)
    
    def _update_rect(self, instance, value):
        """更新背景矩形的位置和大小"""
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def _on_keyboard_closed(self):
        """处理键盘关闭事件"""
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None
        self.key_label.text = "键盘被关闭"
    
    def _on_key_down(self, keyboard, keycode, text, modifiers):
        """处理键盘按键事件"""
        # 显示按键信息
        key_info = f"按键: {keycode[1]} (代码: {keycode[0]})"
        if modifiers:
            key_info += f", 修饰键: {modifiers}"
        
        logger.warning(f"捕获到按键: {keycode[1]}, 代码: {keycode[0]}, 修饰键: {modifiers}")
        
        self.key_label.text = key_info
        
        # 更新历史记录
        self.history.append(keycode[1])
        if len(self.history) > 10:
            self.history.pop(0)
        
        self.key_history.text = "按键历史:\n" + ", ".join(self.history)
        
        # 如果按下ESC键，退出应用
        if keycode[1] == 'escape':
            App.get_running_app().stop()
        
        return True

class KeyboardTestApp(App):
    def build(self):
        # 设置窗口
        Window.size = (600, 400)
        self.title = "键盘测试程序"
        
        return KeyboardTestWidget()

if __name__ == '__main__':
    KeyboardTestApp().run() 