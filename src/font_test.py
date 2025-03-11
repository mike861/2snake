#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kivy字体渲染测试工具 - 专为Mac环境设计
此工具用于诊断Kivy在Mac上的字体渲染问题
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
import os
import sys
import platform
import subprocess

class FontTestApp(App):
    def build(self):
        # 设置窗口大小
        Window.size = (800, 600)
        self.title = 'Kivy字体渲染测试工具'
        
        # 创建主布局
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 添加系统信息标签
        system_info = self.get_system_info()
        info_label = Label(
            text=system_info,
            size_hint_y=None,
            height=100,
            halign='left',
            valign='top',
            text_size=(780, 100)
        )
        main_layout.add_widget(info_label)
        
        # 创建字体测试区域
        test_layout = BoxLayout(orientation='horizontal')
        
        # 左侧 - 字体列表
        left_panel = BoxLayout(orientation='vertical', size_hint_x=0.4)
        left_panel.add_widget(Label(text='系统字体列表', size_hint_y=None, height=40))
        
        # 字体列表滚动视图
        scroll_view = ScrollView()
        self.font_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.font_layout.bind(minimum_height=self.font_layout.setter('height'))
        scroll_view.add_widget(self.font_layout)
        left_panel.add_widget(scroll_view)
        
        # 添加刷新按钮
        refresh_btn = Button(text='刷新字体列表', size_hint_y=None, height=50)
        refresh_btn.bind(on_press=self.load_system_fonts)
        left_panel.add_widget(refresh_btn)
        
        # 右侧 - 字体渲染测试
        right_panel = BoxLayout(orientation='vertical', size_hint_x=0.6, spacing=10)
        right_panel.add_widget(Label(text='字体渲染测试', size_hint_y=None, height=40))
        
        # 添加Kivy默认字体信息
        self.kivy_font_info = Label(
            text='Kivy默认字体: 加载中...',
            size_hint_y=None,
            height=60,
            halign='left',
            valign='top',
            text_size=(400, 60)
        )
        right_panel.add_widget(self.kivy_font_info)
        
        # 添加测试文本区域
        self.test_label = Label(
            text='测试文本 - Test Text - 123456789',
            font_size=24,
            size_hint_y=None,
            height=100
        )
        right_panel.add_widget(self.test_label)
        
        # 添加字体选择器
        self.font_input = Label(
            text='当前选择: 默认字体',
            size_hint_y=None,
            height=40
        )
        right_panel.add_widget(self.font_input)
        
        # 添加测试按钮
        test_btn = Button(text='测试Canvas文本渲染', size_hint_y=None, height=50)
        test_btn.bind(on_press=self.test_canvas_text)
        right_panel.add_widget(test_btn)
        
        # 添加Canvas测试区域
        self.canvas_area = BoxLayout(size_hint_y=None, height=150)
        with self.canvas_area.canvas:
            Color(0.2, 0.2, 0.2, 1)
            Rectangle(pos=(0, 0), size=(400, 150))
        right_panel.add_widget(self.canvas_area)
        
        # 添加调试输出区域
        self.debug_label = Label(
            text='调试输出将显示在这里',
            size_hint_y=None,
            height=100,
            halign='left',
            valign='top',
            text_size=(400, 100)
        )
        right_panel.add_widget(self.debug_label)
        
        # 将左右面板添加到测试布局
        test_layout.add_widget(left_panel)
        test_layout.add_widget(right_panel)
        
        # 将测试布局添加到主布局
        main_layout.add_widget(test_layout)
        
        # 延迟加载字体信息
        Clock.schedule_once(self.load_kivy_font_info, 0.5)
        Clock.schedule_once(lambda dt: self.load_system_fonts(None), 1)
        
        return main_layout
    
    def get_system_info(self):
        """获取系统信息"""
        info = f"操作系统: {platform.system()} {platform.release()} ({platform.version()})\n"
        info += f"Python版本: {sys.version.split()[0]}\n"
        info += f"Kivy版本: {self.get_kivy_version()}\n"
        info += f"处理器: {platform.processor() or '未知'}"
        return info
    
    def get_kivy_version(self):
        """获取Kivy版本"""
        try:
            import kivy
            return kivy.__version__
        except:
            return "未知"
    
    def load_kivy_font_info(self, dt):
        """加载Kivy字体信息"""
        try:
            info = f"Kivy默认字体: {DEFAULT_FONT}\n"
            
            # 尝试获取字体路径
            try:
                font_path = LabelBase.get_system_fonts_dir()
                info += f"字体目录: {font_path}\n"
            except:
                info += "字体目录: 无法获取\n"
            
            # 检查默认字体是否存在
            try:
                from kivy.core.text import Label as CoreLabel
                test_label = CoreLabel(text="Test")
                test_label.refresh()
                if test_label.texture:
                    info += "默认字体测试: 成功"
                else:
                    info += "默认字体测试: 失败 (无纹理)"
            except Exception as e:
                info += f"默认字体测试: 失败 ({str(e)})"
            
            self.kivy_font_info.text = info
        except Exception as e:
            self.kivy_font_info.text = f"加载字体信息失败: {str(e)}"
    
    def load_system_fonts(self, instance):
        """加载系统字体列表"""
        self.font_layout.clear_widgets()
        self.font_layout.add_widget(Label(text="正在加载字体列表...", size_hint_y=None, height=40))
        
        # 使用子线程加载字体以避免UI冻结
        Clock.schedule_once(self._load_system_fonts_thread, 0.1)
    
    def _load_system_fonts_thread(self, dt):
        """在子线程中加载系统字体"""
        try:
            self.font_layout.clear_widgets()
            
            # 获取Mac系统字体
            if platform.system() == 'Darwin':  # macOS
                fonts = self.get_mac_fonts()
            else:
                fonts = ["系统不支持字体列表"]
            
            # 添加字体按钮
            for font in fonts:
                btn = Button(
                    text=font,
                    size_hint_y=None,
                    height=40,
                    halign='left',
                    valign='middle',
                    text_size=(300, 40)
                )
                btn.bind(on_press=lambda instance, f=font: self.select_font(f))
                self.font_layout.add_widget(btn)
            
            # 如果没有找到字体
            if not fonts:
                self.font_layout.add_widget(Label(
                    text="未找到系统字体",
                    size_hint_y=None,
                    height=40
                ))
        except Exception as e:
            self.font_layout.clear_widgets()
            self.font_layout.add_widget(Label(
                text=f"加载字体失败: {str(e)}",
                size_hint_y=None,
                height=40
            ))
    
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
            return [
                "Arial", "Helvetica", "Times New Roman", "Courier New",
                "Verdana", "Georgia", "Palatino", "Garamond", "Bookman",
                "Trebuchet MS", "Arial Black", "Impact", "Tahoma",
                "San Francisco", "Menlo", "Monaco", "Andale Mono"
            ]
        except Exception as e:
            self.debug_label.text = f"获取字体列表失败: {str(e)}"
            return ["获取字体失败"]
    
    def select_font(self, font_name):
        """选择字体进行测试"""
        self.font_input.text = f"当前选择: {font_name}"
        
        try:
            # 尝试更改标签字体
            self.test_label.font_name = font_name
            self.debug_label.text = f"已应用字体: {font_name}"
        except Exception as e:
            self.debug_label.text = f"应用字体失败: {str(e)}"
    
    def test_canvas_text(self, instance):
        """测试Canvas文本渲染"""
        try:
            # 清除之前的Canvas
            self.canvas_area.canvas.clear()
            
            # 重新绘制背景
            with self.canvas_area.canvas:
                Color(0.2, 0.2, 0.2, 1)
                Rectangle(pos=self.canvas_area.pos, size=self.canvas_area.size)
            
            # 获取当前选择的字体
            font_name = self.font_input.text.replace("当前选择: ", "")
            
            # 尝试使用CoreLabel渲染文本
            from kivy.core.text import Label as CoreLabel
            
            # 记录调试信息
            debug_info = ""
            
            # 尝试不同的字体大小
            for font_size in [24, 36]:
                try:
                    # 创建CoreLabel
                    label = CoreLabel(
                        text=f"测试 {font_size}px",
                        font_name=font_name if font_name != "默认字体" else DEFAULT_FONT,
                        font_size=font_size
                    )
                    
                    # 刷新标签以生成纹理
                    label.refresh()
                    
                    # 检查纹理是否创建成功
                    if label.texture:
                        debug_info += f"{font_size}px 纹理大小: {label.texture.size}\n"
                        
                        # 在Canvas上绘制文本
                        with self.canvas_area.canvas:
                            Color(1, 1, 1, 1)
                            y_pos = self.canvas_area.height - font_size - 10 if font_size == 24 else 10
                            Rectangle(
                                texture=label.texture,
                                pos=(10, y_pos),
                                size=label.texture.size
                            )
                    else:
                        debug_info += f"{font_size}px 纹理创建失败\n"
                except Exception as e:
                    debug_info += f"{font_size}px 渲染错误: {str(e)}\n"
            
            # 更新调试信息
            self.debug_label.text = debug_info
            
        except Exception as e:
            self.debug_label.text = f"Canvas测试失败: {str(e)}"

if __name__ == '__main__':
    FontTestApp().run() 