#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kivy字体修复工具 - 专为Snake游戏设计
此工具用于修复游戏中的字体渲染问题
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.core.window import Window
import os
import sys
import platform
import subprocess
import logging

# 设置日志
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('Snake.FontFix')

# 常见的Mac系统字体
MAC_SYSTEM_FONTS = [
    "Arial", "Helvetica", "Times New Roman", "Courier New",
    "Verdana", "Georgia", "Palatino", "Garamond", "Bookman",
    "Trebuchet MS", "Arial Black", "Impact", "Tahoma",
    "San Francisco", "Menlo", "Monaco", "Andale Mono"
]

class FontFixApp(App):
    def build(self):
        # 设置窗口大小
        Window.size = (600, 500)
        self.title = 'Snake游戏字体修复工具'
        
        # 创建主布局
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 添加标题
        title_label = Label(
            text='Snake游戏字体修复工具',
            font_size=24,
            size_hint_y=None,
            height=50
        )
        main_layout.add_widget(title_label)
        
        # 添加说明
        info_label = Label(
            text='此工具将检测系统可用字体并修复游戏中的字体渲染问题。\n'
                 '点击"检测字体"按钮开始检测，然后点击"应用修复"将可用字体应用到游戏中。',
            size_hint_y=None,
            height=80,
            halign='left',
            valign='top',
            text_size=(580, 80)
        )
        main_layout.add_widget(info_label)
        
        # 添加系统信息
        system_info = self.get_system_info()
        sys_label = Label(
            text=system_info,
            size_hint_y=None,
            height=80,
            halign='left',
            valign='top',
            text_size=(580, 80)
        )
        main_layout.add_widget(sys_label)
        
        # 添加检测按钮
        detect_btn = Button(
            text='检测字体',
            size_hint_y=None,
            height=50
        )
        detect_btn.bind(on_press=self.detect_fonts)
        main_layout.add_widget(detect_btn)
        
        # 添加结果显示区域
        self.result_label = Label(
            text='点击上方按钮开始检测...',
            size_hint_y=None,
            height=150,
            halign='left',
            valign='top',
            text_size=(580, 150)
        )
        main_layout.add_widget(self.result_label)
        
        # 添加应用修复按钮
        fix_btn = Button(
            text='应用修复',
            size_hint_y=None,
            height=50
        )
        fix_btn.bind(on_press=self.apply_fix)
        main_layout.add_widget(fix_btn)
        
        # 添加修复结果显示区域
        self.fix_result_label = Label(
            text='',
            size_hint_y=None,
            height=80,
            halign='left',
            valign='top',
            text_size=(580, 80)
        )
        main_layout.add_widget(self.fix_result_label)
        
        return main_layout
    
    def get_system_info(self):
        """获取系统信息"""
        info = f"操作系统: {platform.system()} {platform.release()}\n"
        info += f"Python版本: {sys.version.split()[0]}\n"
        try:
            import kivy
            info += f"Kivy版本: {kivy.__version__}"
        except:
            info += "Kivy版本: 未知"
        return info
    
    def detect_fonts(self, instance):
        """检测系统可用字体"""
        self.result_label.text = "正在检测系统字体..."
        
        # 获取系统字体
        if platform.system() == 'Darwin':  # macOS
            fonts = self.get_mac_fonts()
        else:
            fonts = MAC_SYSTEM_FONTS  # 使用常见字体列表
        
        # 测试字体可用性
        available_fonts = []
        for font in fonts[:20]:  # 只测试前20个字体，避免过长
            if self.test_font(font):
                available_fonts.append(font)
        
        # 显示结果
        if available_fonts:
            self.result_label.text = f"找到 {len(available_fonts)} 个可用字体:\n"
            self.result_label.text += ", ".join(available_fonts[:10])
            if len(available_fonts) > 10:
                self.result_label.text += f"... 等 {len(available_fonts)} 个"
            
            # 保存可用字体列表
            self.available_fonts = available_fonts
        else:
            self.result_label.text = "未找到可用字体，将使用备用方案。"
            self.available_fonts = []
    
    def get_mac_fonts(self):
        """获取Mac系统字体列表"""
        try:
            # 使用系统命令获取字体列表
            cmd = "system_profiler SPFontsDataType | grep 'Full Name:' | awk -F': ' '{print $2}'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout:
                fonts = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                return sorted(fonts)
            
            # 备用方法 - 常见Mac字体
            return MAC_SYSTEM_FONTS
        except:
            return MAC_SYSTEM_FONTS
    
    def test_font(self, font_name):
        """测试字体是否可用"""
        try:
            from kivy.core.text import Label as CoreLabel
            
            # 创建测试标签
            label = CoreLabel(text="Test", font_name=font_name, font_size=24)
            label.refresh()
            
            # 检查纹理是否创建成功
            return label.texture is not None
        except:
            return False
    
    def apply_fix(self, instance):
        """应用字体修复"""
        try:
            # 检查是否已经检测过字体
            if not hasattr(self, 'available_fonts'):
                self.detect_fonts(None)
            
            # 获取游戏主文件路径
            main_py_path = self.find_main_py()
            
            if not main_py_path or not os.path.exists(main_py_path):
                self.fix_result_label.text = "错误: 无法找到游戏主文件 (main.py)"
                return
            
            # 读取main.py文件内容
            with open(main_py_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 创建备份
            backup_path = main_py_path + '.bak'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 修改文件内容
            modified_content = self.modify_main_py(content)
            
            # 写入修改后的内容
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            
            self.fix_result_label.text = f"修复已应用！\n原文件已备份为: {os.path.basename(backup_path)}"
            
        except Exception as e:
            self.fix_result_label.text = f"应用修复失败: {str(e)}"
    
    def find_main_py(self):
        """查找游戏主文件路径"""
        # 尝试在当前目录及上级目录查找
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 检查当前目录
        if os.path.exists(os.path.join(current_dir, 'main.py')):
            return os.path.join(current_dir, 'main.py')
        
        # 检查上级目录
        parent_dir = os.path.dirname(current_dir)
        if os.path.exists(os.path.join(parent_dir, 'main.py')):
            return os.path.join(parent_dir, 'main.py')
        
        # 检查src目录
        if os.path.exists(os.path.join(current_dir, 'src', 'main.py')):
            return os.path.join(current_dir, 'src', 'main.py')
        
        return None
    
    def modify_main_py(self, content):
        """修改main.py文件内容，添加字体支持"""
        # 选择一个可用字体
        font_to_use = None
        if hasattr(self, 'available_fonts') and self.available_fonts:
            # 优先选择常见字体
            preferred_fonts = ["Arial", "Helvetica", "Verdana", "Tahoma", "San Francisco"]
            for font in preferred_fonts:
                if font in self.available_fonts:
                    font_to_use = font
                    break
            
            # 如果没有找到优先字体，使用第一个可用字体
            if not font_to_use and self.available_fonts:
                font_to_use = self.available_fonts[0]
        
        # 如果没有可用字体，使用默认字体
        if not font_to_use:
            font_to_use = "Roboto"  # Kivy默认字体
        
        # 添加字体注册代码 - 修复：不使用None作为字体路径
        font_registration = f"""
# 字体设置
from kivy.core.text import LabelBase
try:
    # 使用可用字体: {font_to_use}
    logger.warning(f"使用字体: {font_to_use}")
    # 不重置默认字体，直接使用系统字体
except Exception as e:
    logger.warning(f"字体设置失败: {{e}}")
"""
        
        # 添加文本渲染方法
        text_rendering_method = """
    def render_text(self, text, x, y, color=(1,1,1,1), font_size=24):
        # 文本渲染方法，使用Canvas直接渲染
        try:
            from kivy.core.text import Label as CoreLabel
            
            # 创建标签
            label = CoreLabel(text=str(text), font_size=font_size)
            label.refresh()
            
            # 检查纹理是否创建成功
            if label.texture:
                with self.canvas:
                    Color(*color)
                    Rectangle(
                        texture=label.texture,
                        pos=(x - label.texture.width/2, y - label.texture.height/2),
                        size=label.texture.size
                    )
                return True
            return False
        except Exception as e:
            logger.warning(f"文本渲染失败: {e}")
            return False
"""
        
        # 修改draw方法中的分数显示部分
        modified_content = content
        if "draw_simple_scores" in content:
            # 已经使用图形方式显示分数，添加文本渲染选项
            modified_content = content.replace(
                "def draw_simple_scores(self):", 
                "def draw_simple_scores(self):\n        # 尝试使用文本渲染\n        if self.render_text(f'P1: {self.score1}', 100, Window.height - self.ui_height/2, (0,1,0,1), 24) and \\\n           self.render_text(f'Time: {self.game_time}s', Window.width/2, Window.height - self.ui_height/2, (1,1,1,1), 24) and \\\n           self.render_text(f'P2: {self.score2}', Window.width-100, Window.height - self.ui_height/2, (0,0,1,1), 24):\n            return  # 如果文本渲染成功，不再使用图形方式"
            )
        
        # 修改draw_simple_game_over方法
        if "draw_simple_game_over" in modified_content:
            # 已经使用图形方式显示游戏结束，添加文本渲染选项
            modified_content = modified_content.replace(
                "def draw_simple_game_over(self):", 
                "def draw_simple_game_over(self):\n        # 尝试使用文本渲染\n        if self.render_text(self.game_over_text, Window.width/2, Window.height/2 + 50, (1,1,1,1), 36) and \\\n           self.render_text(f'P1: {self.score1}  P2: {self.score2}  Time: {self.game_time}s', Window.width/2, Window.height/2, (1,1,1,1), 24) and \\\n           self.render_text('Press SPACE or tap to restart', Window.width/2, Window.height/4, (1,0.8,0.2,1), 24):\n            return  # 如果文本渲染成功，不再使用图形方式"
            )
        
        # 在导入部分后添加字体注册代码
        import_section_end = modified_content.find("class Snake:")
        if import_section_end > 0:
            modified_content = modified_content[:import_section_end] + font_registration + modified_content[import_section_end:]
        
        # 在SnakeGame类中添加文本渲染方法
        snake_game_end = modified_content.find("class SnakeApp(App):")
        if snake_game_end > 0:
            modified_content = modified_content[:snake_game_end] + text_rendering_method + modified_content[snake_game_end:]
        
        return modified_content

if __name__ == '__main__':
    FontFixApp().run() 