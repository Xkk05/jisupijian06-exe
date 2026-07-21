"""
现代化UI主题系统 - 集成UIverse设计语言
支持毛玻璃、渐变、微动画、深色/浅色主题
"""

import logging
from enum import Enum
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class ThemeMode(Enum):
    """主题模式"""
    LIGHT = "浅色"
    DARK = "深色"
    SYSTEM = "系统"


class Theme:
    """主题配置类"""
    
    # 颜色定义
    PRIMARY_COLOR = "#6366F1"  # 靛蓝
    SECONDARY_COLOR = "#EC4899"  # 粉红
    SUCCESS_COLOR = "#10B981"  # 绿色
    WARNING_COLOR = "#F59E0B"  # 橙色
    ERROR_COLOR = "#EF4444"  # 红色
    
    # 深色主题
    DARK_BG_PRIMARY = "#0F172A"  # 深蓝黑
    DARK_BG_SECONDARY = "#1E293B"  # 灰蓝
    DARK_BG_TERTIARY = "#334155"  # 浅灰蓝
    DARK_TEXT_PRIMARY = "#F1F5F9"  # 亮白
    DARK_TEXT_SECONDARY = "#CBD5E1"  # 灰白
    
    # 浅色主题
    LIGHT_BG_PRIMARY = "#FFFFFF"  # 白色
    LIGHT_BG_SECONDARY = "#F8FAFC"  # 浅灰
    LIGHT_BG_TERTIARY = "#E2E8F0"  # 深灰
    LIGHT_TEXT_PRIMARY = "#0F172A"  # 深蓝黑
    LIGHT_TEXT_SECONDARY = "#475569"  # 中灰
    
    @staticmethod
    def get_qss_stylesheet(mode: ThemeMode = ThemeMode.DARK) -> str:
        """获取QSS样式表"""
        
        if mode == ThemeMode.DARK:
            return Theme._get_dark_stylesheet()
        else:
            return Theme._get_light_stylesheet()
    
    @staticmethod
    def _get_dark_stylesheet() -> str:
        """获取深色主题样式表"""
        return f"""
            QMainWindow {{
                background-color: {Theme.DARK_BG_PRIMARY};
                color: {Theme.DARK_TEXT_PRIMARY};
            }}
            
            QWidget {{
                background-color: {Theme.DARK_BG_PRIMARY};
                color: {Theme.DARK_TEXT_PRIMARY};
            }}
            
            /* 玻璃态效果 - 毛玻璃背景 */
            QFrame#GlassFrame {{
                background-color: rgba(30, 41, 59, 0.7);
                border-radius: 12px;
                border: 1px solid rgba(148, 163, 184, 0.2);
                backdrop-filter: blur(10px);
            }}
            
            /* 主按钮 - 渐变背景 */
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Theme.PRIMARY_COLOR},
                    stop:1 {Theme.SECONDARY_COLOR}
                );
                color: {Theme.DARK_TEXT_PRIMARY};
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
                transition: all 0.3s ease;
            }}
            
            QPushButton:hover {{
                box-shadow: 0 8px 16px rgba(99, 102, 241, 0.3);
            }}
            
            QPushButton:pressed {{
                box-shadow: 0 4px 8px rgba(99, 102, 241, 0.2);
            }}
            
            QPushButton:disabled {{
                background-color: {Theme.DARK_BG_TERTIARY};
                color: {Theme.DARK_TEXT_SECONDARY};
            }}
            
            /* 输入框 */
            QLineEdit, QTextEdit {{
                background-color: {Theme.DARK_BG_SECONDARY};
                color: {Theme.DARK_TEXT_PRIMARY};
                border: 1px solid {Theme.DARK_BG_TERTIARY};
                border-radius: 6px;
                padding: 8px;
                selection-background-color: {Theme.PRIMARY_COLOR};
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {Theme.PRIMARY_COLOR};
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
            }}
            
            /* 标签页 */
            QTabWidget::pane {{
                border: 1px solid {Theme.DARK_BG_TERTIARY};
            }}
            
            QTabBar::tab {{
                background-color: {Theme.DARK_BG_SECONDARY};
                color: {Theme.DARK_TEXT_SECONDARY};
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 6px 6px 0px 0px;
            }}
            
            QTabBar::tab:selected {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {Theme.PRIMARY_COLOR},
                    stop:1 {Theme.SECONDARY_COLOR}
                );
                color: {Theme.DARK_TEXT_PRIMARY};
                border: 1px solid {Theme.PRIMARY_COLOR};
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {Theme.DARK_BG_TERTIARY};
            }}
            
            /* 菜单 */
            QMenu {{
                background-color: {Theme.DARK_BG_SECONDARY};
                color: {Theme.DARK_TEXT_PRIMARY};
                border: 1px solid {Theme.DARK_BG_TERTIARY};
                border-radius: 8px;
                padding: 4px 0px;
            }}
            
            QMenu::item:selected {{
                background-color: {Theme.PRIMARY_COLOR};
                color: {Theme.DARK_TEXT_PRIMARY};
                border-radius: 4px;
            }}
            
            /* 滚动条 */
            QScrollBar:vertical {{
                background-color: {Theme.DARK_BG_SECONDARY};
                width: 10px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:vertical {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Theme.PRIMARY_COLOR},
                    stop:1 {Theme.SECONDARY_COLOR}
                );
                border-radius: 5px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Theme.SECONDARY_COLOR},
                    stop:1 {Theme.PRIMARY_COLOR}
                );
            }}
            
            /* 组框 */
            QGroupBox {{
                color: {Theme.DARK_TEXT_PRIMARY};
                border: 1px solid {Theme.DARK_BG_TERTIARY};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }}
            
            /* 复选框和单选框 */
            QCheckBox, QRadioButton {{
                color: {Theme.DARK_TEXT_PRIMARY};
                spacing: 5px;
            }}
            
            QCheckBox::indicator, QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 3px;
                background-color: {Theme.DARK_BG_SECONDARY};
                border: 1px solid {Theme.DARK_BG_TERTIARY};
            }}
            
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Theme.PRIMARY_COLOR},
                    stop:1 {Theme.SECONDARY_COLOR}
                );
                border: 1px solid {Theme.PRIMARY_COLOR};
            }}
            
            /* 进度条 */
            QProgressBar {{
                background-color: {Theme.DARK_BG_SECONDARY};
                border: 1px solid {Theme.DARK_BG_TERTIARY};
                border-radius: 6px;
                text-align: center;
                color: {Theme.DARK_TEXT_PRIMARY};
            }}
            
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Theme.PRIMARY_COLOR},
                    stop:1 {Theme.SECONDARY_COLOR}
                );
                border-radius: 5px;
            }}
            
            /* 滑块 */
            QSlider::groove:horizontal {{
                background-color: {Theme.DARK_BG_SECONDARY};
                border-radius: 5px;
                height: 6px;
            }}
            
            QSlider::handle:horizontal {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {Theme.PRIMARY_COLOR},
                    stop:1 {Theme.SECONDARY_COLOR}
                );
                border-radius: 10px;
                width: 18px;
                margin: -6px 0;
            }}
            
            QSlider::handle:horizontal:hover {{
                width: 20px;
                margin: -7px 0;
                box-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
            }}
            
            /* 对话框 */
            QDialog {{
                background-color: {Theme.DARK_BG_PRIMARY};
                color: {Theme.DARK_TEXT_PRIMARY};
            }}
            
            /* 工具栏 */
            QToolBar {{
                background-color: {Theme.DARK_BG_SECONDARY};
                border: 1px solid {Theme.DARK_BG_TERTIARY};
                border-radius: 8px;
                padding: 4px;
                spacing: 4px;
            }}
            
            /* 组合框 */
            QComboBox {{
                background-color: {Theme.DARK_BG_SECONDARY};
                color: {Theme.DARK_TEXT_PRIMARY};
                border: 1px solid {Theme.DARK_BG_TERTIARY};
                border-radius: 6px;
                padding: 6px;
                selection-background-color: {Theme.PRIMARY_COLOR};
            }}
            
            QComboBox:focus {{
                border: 2px solid {Theme.PRIMARY_COLOR};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox::down-arrow {{
                image: url(icons/arrow-down.svg);
                width: 12px;
                height: 12px;
            }}
        """
    
    @staticmethod
    def _get_light_stylesheet() -> str:
        """获取浅色主题样式表"""
        return f"""
            QMainWindow {{
                background-color: {Theme.LIGHT_BG_PRIMARY};
                color: {Theme.LIGHT_TEXT_PRIMARY};
            }}
            
            QWidget {{
                background-color: {Theme.LIGHT_BG_PRIMARY};
                color: {Theme.LIGHT_TEXT_PRIMARY};
            }}
            
            /* 玻璃态效果 */
            QFrame#GlassFrame {{
                background-color: rgba(248, 250, 252, 0.7);
                border-radius: 12px;
                border: 1px solid rgba(226, 232, 240, 0.5);
            }}
            
            /* 主按钮 */
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {Theme.PRIMARY_COLOR},
                    stop:1 {Theme.SECONDARY_COLOR}
                );
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            
            QPushButton:hover {{
                box-shadow: 0 8px 16px rgba(99, 102, 241, 0.2);
            }}
            
            QPushButton:disabled {{
                background-color: {Theme.LIGHT_BG_TERTIARY};
                color: {Theme.LIGHT_TEXT_SECONDARY};
            }}
            
            /* 输入框 */
            QLineEdit, QTextEdit {{
                background-color: {Theme.LIGHT_BG_PRIMARY};
                color: {Theme.LIGHT_TEXT_PRIMARY};
                border: 1px solid {Theme.LIGHT_BG_TERTIARY};
                border-radius: 6px;
                padding: 8px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 2px solid {Theme.PRIMARY_COLOR};
            }}
        """


# 微动画定义
class AnimationConfig:
    """动画配置"""
    
    # 淡入淡出
    FADE_IN_DURATION = 300  # 毫秒
    FADE_OUT_DURATION = 300
    
    # 滑动
    SLIDE_DURATION = 400
    SLIDE_DISTANCE = 20  # 像素
    
    # 缩放
    SCALE_DURATION = 300
    SCALE_FACTOR = 0.95  # 最小缩放因子
    
    # 旋转
    ROTATE_DURATION = 600
    ROTATE_ANGLE = 360  # 度数
    
    # 弹性
    BOUNCE_DURATION = 500
    BOUNCE_FACTOR = 1.1  # 弹性因子


logger.info("现代化UI主题系统已初始化")

__all__ = [
    'Theme',
    'ThemeMode',
    'AnimationConfig',
]
