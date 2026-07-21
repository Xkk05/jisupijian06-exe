"""
主题管理系统
支持深色/浅色主题、自定义色彩方案、主题保存加载
"""
from dataclasses import dataclass, asdict
from typing import Dict, Optional
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ColorScheme:
    """颜色方案"""
    # 背景色
    window_bg: str = "#2d2d30"
    window_text: str = "#c8c8c8"
    base_bg: str = "#1e1e1e"
    base_text: str = "#c8c8c8"
    button_bg: str = "#3e3e42"
    button_text: str = "#c8c8c8"
    
    # 强调色
    highlight: str = "#007acc"
    highlight_text: str = "#ffffff"
    
    # 边框和分隔
    border: str = "#3e3e42"
    separator: str = "#3e3e42"
    
    # 状态色
    success: str = "#4ec9b0"
    warning: str = "#dcdcaa"
    error: str = "#f48771"
    info: str = "#569cd6"
    
    # 特殊
    scrollbar_bg: str = "#3e3e42"
    scrollbar_handle: str = "#686868"
    disabled_text: str = "#808080"


@dataclass
class ThemeConfig:
    """主题配置"""
    name: str
    colors: ColorScheme
    font_family: str = "微软雅黑"
    font_size_base: int = 10
    font_size_title: int = 14
    font_size_small: int = 8
    border_radius: int = 4
    spacing: int = 5


class ThemeManager(QObject):
    """主题管理器"""
    
    theme_changed = pyqtSignal(str)  # 主题改变信号
    
    # 预定义主题
    DARK_THEME = ThemeConfig(
        name="Dark",
        colors=ColorScheme(
            window_bg="#2d2d30",
            window_text="#c8c8c8",
            base_bg="#1e1e1e",
            base_text="#c8c8c8",
            button_bg="#3e3e42",
            button_text="#c8c8c8",
            highlight="#007acc",
            highlight_text="#ffffff",
            border="#3e3e42",
            separator="#3e3e42",
            success="#4ec9b0",
            warning="#dcdcaa",
            error="#f48771",
            info="#569cd6",
            scrollbar_bg="#3e3e42",
            scrollbar_handle="#686868",
            disabled_text="#808080"
        )
    )
    
    LIGHT_THEME = ThemeConfig(
        name="Light",
        colors=ColorScheme(
            window_bg="#ffffff",
            window_text="#333333",
            base_bg="#f5f5f5",
            base_text="#333333",
            button_bg="#e8e8e8",
            button_text="#333333",
            highlight="#0078d7",
            highlight_text="#ffffff",
            border="#d0d0d0",
            separator="#d0d0d0",
            success="#107c10",
            warning="#ffb900",
            error="#e81123",
            info="#0078d4",
            scrollbar_bg="#e8e8e8",
            scrollbar_handle="#c0c0c0",
            disabled_text="#a0a0a0"
        )
    )
    
    HIGH_CONTRAST_THEME = ThemeConfig(
        name="HighContrast",
        colors=ColorScheme(
            window_bg="#000000",
            window_text="#ffff00",
            base_bg="#000000",
            base_text="#ffff00",
            button_bg="#ffff00",
            button_text="#000000",
            highlight="#ffff00",
            highlight_text="#000000",
            border="#ffff00",
            separator="#ffff00",
            success="#00ff00",
            warning="#ffff00",
            error="#ff0000",
            info="#00ffff",
            scrollbar_bg="#000000",
            scrollbar_handle="#ffff00",
            disabled_text="#808080"
        )
    )
    
    def __init__(self):
        super().__init__()
        self.current_theme = self.DARK_THEME
        self.themes: Dict[str, ThemeConfig] = {
            "Dark": self.DARK_THEME,
            "Light": self.LIGHT_THEME,
            "HighContrast": self.HIGH_CONTRAST_THEME
        }
    
    def apply_theme(self, theme: ThemeConfig):
        """应用主题"""
        self.current_theme = theme
        
        app = QApplication.instance()
        if app:
            palette = self._create_palette(theme)
            app.setPalette(palette)
            
            # 应用样式表
            stylesheet = self._create_stylesheet(theme)
            app.setStyle('Fusion')
            app.setStyleSheet(stylesheet)
        
        logger.info(f"应用主题: {theme.name}")
        self.theme_changed.emit(theme.name)
    
    def switch_theme(self, theme_name: str) -> bool:
        """切换主题"""
        if theme_name in self.themes:
            self.apply_theme(self.themes[theme_name])
            return True
        logger.warning(f"主题不存在: {theme_name}")
        return False
    
    def _create_palette(self, theme: ThemeConfig) -> QPalette:
        """创建调色板"""
        palette = QPalette()
        colors = theme.colors
        
        # 设置颜色角色
        palette.setColor(QPalette.ColorRole.Window, QColor(colors.window_bg))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.window_text))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors.base_bg))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors.base_text))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors.button_bg))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.button_text))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.highlight))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(colors.highlight_text))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors.base_bg))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors.base_text))
        palette.setColor(QPalette.ColorRole.Disabled, QColor(colors.disabled_text))
        
        return palette
    
    def _create_stylesheet(self, theme: ThemeConfig) -> str:
        """创建样式表"""
        colors = theme.colors
        
        return f"""
        QMainWindow, QDialog {{
            background-color: {colors.window_bg};
            color: {colors.window_text};
        }}
        
        QWidget {{
            background-color: {colors.window_bg};
            color: {colors.window_text};
        }}
        
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {colors.base_bg};
            color: {colors.base_text};
            border: 1px solid {colors.border};
            border-radius: {theme.border_radius}px;
            padding: 2px;
        }}
        
        QPushButton {{
            background-color: {colors.button_bg};
            color: {colors.button_text};
            border: 1px solid {colors.border};
            border-radius: {theme.border_radius}px;
            padding: 4px 12px;
            font-weight: bold;
        }}
        
        QPushButton:hover {{
            background-color: {colors.highlight};
            color: {colors.highlight_text};
        }}
        
        QPushButton:pressed {{
            background-color: {self._darken(colors.highlight, 0.8)};
        }}
        
        QComboBox {{
            background-color: {colors.base_bg};
            color: {colors.base_text};
            border: 1px solid {colors.border};
            border-radius: {theme.border_radius}px;
            padding: 2px;
        }}
        
        QComboBox::drop-down {{
            border: none;
        }}
        
        QSpinBox, QDoubleSpinBox {{
            background-color: {colors.base_bg};
            color: {colors.base_text};
            border: 1px solid {colors.border};
            border-radius: {theme.border_radius}px;
        }}
        
        QSlider::groove:horizontal {{
            background-color: {colors.separator};
            height: 4px;
            border-radius: 2px;
        }}
        
        QSlider::handle:horizontal {{
            background-color: {colors.highlight};
            border: 1px solid {colors.highlight};
            width: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background-color: {self._brighten(colors.highlight, 1.2)};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {colors.border};
        }}
        
        QTabBar::tab {{
            background-color: {colors.button_bg};
            color: {colors.button_text};
            padding: 4px 16px;
            margin-right: 2px;
            border: 1px solid {colors.border};
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors.highlight};
            color: {colors.highlight_text};
        }}
        
        QTabBar::tab:hover {{
            background-color: {self._brighten(colors.button_bg, 1.2)};
        }}
        
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0px;
            border: none;
        }}
        
        QScrollBar::handle:vertical {{
            background: #CBD5E1;
            border-radius: 4px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: #94A3B8;
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0px;
            border: none;
        }}
        
        QScrollBar::handle:horizontal {{
            background: #CBD5E1;
            border-radius: 4px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: #94A3B8;
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
        
        QCheckBox {{
            color: {colors.window_text};
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
        }}
        
        QCheckBox::indicator:unchecked {{
            background-color: {colors.base_bg};
            border: 1px solid {colors.border};
            border-radius: 2px;
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {colors.highlight};
            border: 1px solid {colors.highlight};
            image: url(:/check);
        }}
        
        QGroupBox {{
            color: {colors.window_text};
            border: 1px solid {colors.border};
            border-radius: {theme.border_radius}px;
            margin-top: 8px;
            padding-top: 8px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }}
        
        QMenuBar {{
            background-color: {colors.button_bg};
            color: {colors.button_text};
            border-bottom: 1px solid {colors.border};
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors.highlight};
            color: {colors.highlight_text};
        }}
        
        QMenu {{
            background-color: {colors.window_bg};
            color: {colors.window_text};
            border: 1px solid {colors.border};
        }}
        
        QMenu::item:selected {{
            background-color: {colors.highlight};
            color: {colors.highlight_text};
        }}
        
        QListWidget {{
            background-color: {colors.base_bg};
            color: {colors.base_text};
            border: 1px solid {colors.border};
            border-radius: {theme.border_radius}px;
        }}
        
        QListWidget::item:selected {{
            background-color: {colors.highlight};
            color: {colors.highlight_text};
        }}
        
        QListWidget::item:hover {{
            background-color: {self._brighten(colors.highlight, 0.8)};
        }}
        
        QTreeWidget {{
            background-color: {colors.base_bg};
            color: {colors.base_text};
            border: 1px solid {colors.border};
            border-radius: {theme.border_radius}px;
        }}
        
        QTreeWidget::item:selected {{
            background-color: {colors.highlight};
            color: {colors.highlight_text};
        }}
        
        QProgressBar {{
            background-color: {colors.button_bg};
            border: 1px solid {colors.border};
            border-radius: {theme.border_radius}px;
            color: {colors.button_text};
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {colors.highlight};
            border-radius: {theme.border_radius}px;
        }}
        
        QStatusBar {{
            background-color: {colors.button_bg};
            color: {colors.button_text};
            border-top: 1px solid {colors.border};
        }}
        """
    
    @staticmethod
    def _brighten(hex_color: str, factor: float = 1.2) -> str:
        """亮化颜色"""
        color = QColor(hex_color)
        h, s, v, a = color.getHsv()
        v = int(min(255, v * factor))
        color.setHsv(h, s, v, a)
        return color.name()
    
    @staticmethod
    def _darken(hex_color: str, factor: float = 0.8) -> str:
        """暗化颜色"""
        color = QColor(hex_color)
        h, s, v, a = color.getHsv()
        v = int(max(0, v * factor))
        color.setHsv(h, s, v, a)
        return color.name()
    
    def register_custom_theme(self, name: str, theme: ThemeConfig):
        """注册自定义主题"""
        self.themes[name] = theme
        logger.info(f"注册自定义主题: {name}")
    
    def save_theme(self, theme_name: str, file_path: str) -> bool:
        """保存主题到文件"""
        if theme_name not in self.themes:
            logger.warning(f"主题不存在: {theme_name}")
            return False
        
        try:
            theme = self.themes[theme_name]
            config = {
                'name': theme.name,
                'colors': asdict(theme.colors),
                'font_family': theme.font_family,
                'font_size_base': theme.font_size_base,
                'font_size_title': theme.font_size_title,
                'font_size_small': theme.font_size_small,
                'border_radius': theme.border_radius,
                'spacing': theme.spacing
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"主题已保存: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存主题失败: {e}")
            return False
    
    def load_theme(self, file_path: str) -> bool:
        """从文件加载主题"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            colors = ColorScheme(**config['colors'])
            theme = ThemeConfig(
                name=config['name'],
                colors=colors,
                font_family=config.get('font_family', '微软雅黑'),
                font_size_base=config.get('font_size_base', 10),
                font_size_title=config.get('font_size_title', 14),
                font_size_small=config.get('font_size_small', 8),
                border_radius=config.get('border_radius', 4),
                spacing=config.get('spacing', 5)
            )
            
            self.register_custom_theme(theme.name, theme)
            logger.info(f"主题已加载: {file_path}")
            return True
        except Exception as e:
            logger.error(f"加载主题失败: {e}")
            return False
    
    def get_color(self, color_name: str) -> Optional[str]:
        """获取当前主题的颜色"""
        colors = self.current_theme.colors
        return getattr(colors, color_name, None)
    
    def list_themes(self) -> list:
        """列出所有可用主题"""
        return list(self.themes.keys())
