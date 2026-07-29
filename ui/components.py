import os
import sys
from enum import Enum
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QRect, QByteArray, QTimer, QLocale
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QIcon, QPixmap, QFontMetrics
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox, QGraphicsDropShadowEffect,
    QHBoxLayout, QFrame, QAbstractSpinBox, QScrollArea, QColorDialog,
    QProgressBar, QDialog, QGridLayout, QSizePolicy
)
from PyQt6.QtSvg import QSvgRenderer
from ui.theme import Theme
from ui.i18n import get_language_manager, t
from ui.window_controls import TitleBar
from utils.icon_utils import load_logo_pixmap

class ModernCard(QWidget):
    """现代风格卡片容器：白底、圆角、微阴影"""
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)
        
        # 阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 10))  # 极淡的阴影
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        # 背景和边框
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ModernCard {{
                background-color: {Theme.Surface};
                border-radius: 12px;
                border: 1px solid {Theme.Border};
            }}
        """)
        
        # 标题 (可选)
        if title:
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet(f"""
                font-size: 14px; 
                font-weight: bold; 
                color: {Theme.TextPrimary};
                border: none;
                margin-bottom: 5px;
            """)
            self.layout.addWidget(self.title_label)

    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def addLayout(self, layout):
        self.layout.addLayout(layout)

    def setTitle(self, title: str):
        """兼容QGroupBox风格接口，便于旧代码平滑迁移。"""
        if not hasattr(self, "title_label"):
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet(f"""
                font-size: 14px; 
                font-weight: bold; 
                color: {Theme.TextPrimary};
                border: none;
                margin-bottom: 5px;
            """)
            self.layout.insertWidget(0, self.title_label)
            return
        self.title_label.setText(title)


def _load_svg_icon(name: str, size: int, color: str) -> QIcon:
    icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icons", f"{name}.svg")
    if not os.path.exists(icon_path):
        return QIcon()
    with open(icon_path, "r", encoding="utf-8") as f:
        svg_data = f.read()
    if "currentColor" in svg_data:
        svg_data = svg_data.replace("currentColor", color)
    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def load_svg_icon(name: str, size: int = 16, color: str = Theme.TextPrimary) -> QIcon:
    return _load_svg_icon(name, size, color)


def _resource_path(*parts: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *parts).replace("\\", "/")


def open_color_dialog(initial: QColor | None = None, parent: QWidget | None = None, title: str | None = None) -> QColor | None:
    initial_color = initial or QColor("#000000")
    if initial_color.red() == 0 and initial_color.green() == 0 and initial_color.blue() == 0:
        initial_color = QColor("#808080")
    dialog = QColorDialog(initial_color, parent)
    dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
    if title:
        dialog.setWindowTitle(title)
    if dialog.exec():
        color = dialog.currentColor()
        if color.isValid():
            return color
    return None


class ProgressStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"


class ModernProgressBar(QProgressBar):
    """现代风格进度条，支持多种状态颜色"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)  # 稍微加高一点
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status = ProgressStatus.IDLE
        self.update_style()

    def set_status(self, status: ProgressStatus):
        if self._status != status:
            self._status = status
            self.update_style()

    def update_style(self):
        # Base style
        base_style = f"""
            QProgressBar {{
                border: none;
                border-radius: 7px;
                background-color: #F1F5F9; /* Theme.Divider/Slate-100 - 更轻盈的背景 */
                text-align: center;
                color: {Theme.TextSecondary};
                font-size: 11px;
                font-weight: 600;
            }}
        """

        # Chunk style based on status
        chunk_bg = ""

        if self._status == ProgressStatus.PROCESSING:
             # Blue - Matching ModernButton Primary
             chunk_bg = f"background-color: {Theme.Primary};"
        elif self._status == ProgressStatus.SUCCESS:
            # Green - Matching Theme.Success exactly
            chunk_bg = f"background-color: {Theme.Success};"
        elif self._status == ProgressStatus.ERROR:
            # Red
            chunk_bg = f"background-color: {Theme.Error};"
        elif self._status == ProgressStatus.WARNING:
            # Orange
            chunk_bg = f"background-color: {Theme.Warning};"
        else: # IDLE
             chunk_bg = f"background-color: {Theme.TextSecondary};"

        chunk_style = f"""
            QProgressBar::chunk {{
                {chunk_bg}
                border-radius: 7px;
            }}
        """

        self.setStyleSheet(base_style + chunk_style)


class ModernButton(QPushButton):
    """现代风格按钮：扁平、主色、悬停效果"""
    
    class Style(Enum):
        Primary = "primary"
        Secondary = "secondary"
        Danger = "danger"
        Outline = "outline"

    def __init__(self, text, style=Style.Primary, parent=None, icon_name=None, icon_size=16):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        
        # 基础样式
        base_style = f"""
            QPushButton {{
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                padding: 0 16px;
                border: none;
            }}
        """
        
        # 变体样式
        icon_color = Theme.TextPrimary
        if style == self.Style.Primary:
            icon_color = Theme.TextOnPrimary
            color_style = f"""
                QPushButton {{
                    background-color: {Theme.Primary};
                    color: {Theme.TextOnPrimary};
                }}
                QPushButton:hover {{
                    background-color: {Theme.PrimaryHover};
                }}
                QPushButton:pressed {{
                    background-color: {Theme.PrimaryPressed};
                }}
                QPushButton:disabled {{
                    background-color: {Theme.Border};
                    color: {Theme.TextDisabled};
                    border: none;
                }}
            """
        elif style == self.Style.Danger:
            icon_color = "#FFFFFF"
            color_style = f"""
                QPushButton {{
                    background-color: {Theme.Error};
                    color: white;
                }}
                QPushButton:hover {{
                    background-color: #DC2626;
                }}
                QPushButton:disabled {{
                    background-color: {Theme.Border};
                    color: {Theme.TextDisabled};
                    border: none;
                }}
            """
        elif style == self.Style.Outline:
            icon_color = Theme.TextPrimary
            color_style = f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1px solid {Theme.Border};
                    color: {Theme.TextPrimary};
                }}
                QPushButton:hover {{
                    background-color: {Theme.Background};
                    border-color: {Theme.TextSecondary};
                }}
                QPushButton:disabled {{
                    background-color: {Theme.Background};
                    border-color: {Theme.Border};
                    color: {Theme.TextDisabled};
                }}
            """
        else: # Secondary (Default grey)
            icon_color = Theme.TextPrimary
            color_style = f"""
                QPushButton {{
                    background-color: {Theme.Background};
                    color: {Theme.TextPrimary};
                    border: 1px solid {Theme.Border};
                }}
                QPushButton:hover {{
                    background-color: {Theme.Border};
                }}
                QPushButton:disabled {{
                    background-color: {Theme.Background};
                    border-color: {Theme.Border};
                    color: {Theme.TextDisabled};
                }}
            """
            
        self.setStyleSheet(base_style + color_style)
        if icon_name:
            self.setIcon(_load_svg_icon(icon_name, icon_size, icon_color))
            self.setIconSize(QSize(icon_size, icon_size))


class ToggleSwitch(QWidget):
    """iOS风格的开关控件"""
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._checked = False
        self._thumb_position = 2
        
        # 动画
        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            target = 22 if checked else 2
            self._anim.setStartValue(self._thumb_position)
            self._anim.setEndValue(target)
            self._anim.start()
            self.update()
            self.toggled.emit(checked)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    @pyqtProperty(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制轨道
        track_color = QColor(Theme.Primary) if self._checked else QColor(Theme.Border)
        if not self.isEnabled():
            track_color = QColor(Theme.Background)
            
        p.setBrush(QBrush(track_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 44, 24, 12, 12)
        
        # 绘制滑块
        p.setBrush(QBrush(QColor(Theme.Surface)))
        p.drawEllipse(int(self._thumb_position), 2, 20, 20)


class SegmentedControl(QWidget):
    """分段控制器 (Tab) - 带滑动动画"""
    valueChanged = pyqtSignal(int)
    
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = items
        self._control_height = 38
        self.setFixedHeight(self._control_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        # 容器样式
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SegmentedControl {{
                background-color: {Theme.Background};
                border-radius: 8px;
                border: 1px solid {Theme.Border};
            }}
        """)

        # 1. 外层布局 + 横向滚动容器（解决多语言长文本溢出）
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setFixedHeight(self._control_height)
        self.scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)
        self.layout.addWidget(self.scroll_area)

        self.track = QWidget()
        self.track.setFixedHeight(self._control_height)
        self.track.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.scroll_area.setWidget(self.track)

        # 2. 创建滑块指示器 (背景)
        self.indicator = QWidget(self.track)
        self.indicator.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)  # 让鼠标事件穿透
        self.indicator.setStyleSheet(f"""
            background-color: {Theme.Surface};
            border-radius: 6px;
        """)

        # 给滑块添加阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 3)
        self.indicator.setGraphicsEffect(shadow)

        # 动画对象
        self.anim = QPropertyAnimation(self.indicator, b"geometry")
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setDuration(300)  # 300ms 滑动

        # 3. 按钮布局
        self.buttons_layout = QHBoxLayout(self.track)
        self.buttons_layout.setContentsMargins(4, 4, 4, 4)
        self.buttons_layout.setSpacing(0)
        
        self.buttons = []
        self._current_index = 0
        
        for i, text in enumerate(items):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # 预设样式，避免在运行时反复 setStyleSheet
            # 利用 QButton 的 checked 状态来切换样式
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Theme.TextSecondary};
                    border: none;
                    border-radius: 6px;
                    font-weight: normal;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    color: {Theme.TextPrimary};
                }}
                QPushButton:checked {{
                    color: {Theme.Primary};
                    font-weight: bold;
                }}
            """)
            
            # 计算文字宽度
            font = btn.font()
            font.setBold(True)
            fm = QFontMetrics(font)
            btn.setMinimumWidth(fm.horizontalAdvance(text) + 20)
            
            btn.clicked.connect(lambda checked, idx=i: self.set_index(idx))
            self.buttons_layout.addWidget(btn)
            self.buttons.append(btn)
            
        # 确保指示器在按钮下方 (但因为是先addWidget后lower，其实Widget创建顺序决定层级，lower确保在最底)
        self.indicator.lower()
            
        self.update_styles()

    def set_index(self, index):
        if 0 <= index < len(self.items):
            self._current_index = index
            self.update_styles()
            self.animate_indicator()
            self.scroll_area.ensureWidgetVisible(self.buttons[index], 24, 0)
            self.valueChanged.emit(index)

    def update_styles(self):
        for i, btn in enumerate(self.buttons):
            # 仅切换状态，不重新解析样式表
            is_selected = (i == self._current_index)
            if btn.isChecked() != is_selected:
                btn.setChecked(is_selected)

    def retranslate_ui(self):
        manager = get_language_manager()
        for index, btn in enumerate(self.buttons):
            translated = manager.translate_source_text(btn.text())
            btn.setText(translated)
            if index < len(self.items):
                self.items[index] = translated
            font = btn.font()
            font.setBold(True)
            fm = QFontMetrics(font)
            btn.setMinimumWidth(fm.horizontalAdvance(translated) + 20)
        self.track.adjustSize()
        QTimer.singleShot(0, self.animate_indicator)
    
    def animate_indicator(self):
        if not self.buttons:
            return
            
        btn = self.buttons[self._current_index]
        # 获取按钮相对于父容器的几何位置
        rect = btn.geometry()
        
        if rect.isValid() and rect.width() > 0:
            self.anim.stop()
            self.anim.setEndValue(rect)
            self.anim.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口大小改变时，无动画跟随
        self.track.adjustSize()
        if self.buttons:
            btn = self.buttons[self._current_index]
            self.indicator.setGeometry(btn.geometry())
            
    def showEvent(self, event):
        super().showEvent(event)
        # 显示时延迟一帧校准位置，确保布局已完成
        QTimer.singleShot(0, self.animate_indicator)


class ModernInput:
    """输入框样式生成器"""
    @staticmethod
    def apply_style(widget):
        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            widget.setLocale(QLocale.c())
            widget.lineEdit().setLocale(QLocale.c())

        arrow_up = _resource_path("assets", "icons", "spin_up.svg")
        arrow_down = _resource_path("assets", "icons", "spin_down.svg")
        arrow_up_disabled = _resource_path("assets", "icons", "spin_up_disabled.svg")
        arrow_down_disabled = _resource_path("assets", "icons", "spin_down_disabled.svg")
        style = f"""
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
                background-color: {Theme.Surface};
                border: 1px solid {Theme.Border};
                border-radius: 6px;
                padding: 6px 10px;
                color: {Theme.TextPrimary};
                font-size: 13px;
                selection-background-color: {Theme.Primary};
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 1px solid {Theme.Primary};
                background-color: {Theme.Surface};
            }}
            QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
                background-color: {Theme.Background};
                color: {Theme.TextDisabled};
            }}
            
            /* SpinBox Buttons */
            QSpinBox::up-button, QDoubleSpinBox::up-button {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 16px;
                border-left: 1px solid {Theme.Border};
                border-bottom: 1px solid {Theme.Border};
                background: transparent; /* 确保背景透明，透出 Surface 颜色 */
                margin-top: 1px;
                margin-right: 1px;
            }}
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
                background-color: {Theme.PrimaryLight};
            }}
            QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {{
                background-color: {Theme.Divider};
            }}
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 16px;
                border-left: 1px solid {Theme.Border};
                background: transparent;
                margin-bottom: 1px;
                margin-right: 1px;
            }}
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
                background-color: {Theme.PrimaryLight};
            }}
            QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
                background-color: {Theme.Divider};
            }}
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
                width: 10px;
                height: 10px;
                image: url("{arrow_up}");
                margin-right: 3px;
                margin-top: 3px;
            }}
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
                width: 10px;
                height: 10px;
                image: url("{arrow_down}");
                margin-right: 3px;
                margin-bottom: 3px;
            }}
            QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{
                image: url("{arrow_up_disabled}");
            }}
            QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{
                image: url("{arrow_down_disabled}");
            }}
            
            /* ComboBox Arrow */
            QComboBox {{
                border-radius: 8px;
                padding-right: 30px;
                min-height: 24px;
            }}
            QComboBox:focus {{
                border: 2px solid {Theme.Primary};
                padding: 5px 11px;
                padding-right: 29px;
                border-radius: 8px;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left-width: 0px;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                background: transparent;
                border-left: 1px solid {Theme.Divider};
            }}
            QComboBox::down-arrow {{
                image: url("{arrow_down}");
                width: 10px;
                height: 10px;
                border: none;
                background: transparent;
                margin-right: 6px;
            }}
            QComboBox::down-arrow:hover {{
                image: url("{arrow_down}");
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow:disabled {{
                image: url("{arrow_down_disabled}");
                border: none;
                background: transparent;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Theme.Surface};
                color: {Theme.TextPrimary};
                border: 1px solid {Theme.Border};
                border-radius: 8px;
                padding: 4px;
                selection-background-color: {Theme.PrimaryLight};
                selection-color: {Theme.Primary};
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                border-radius: 4px;
                min-height: 24px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {Theme.PrimaryLight};
                color: {Theme.Primary};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {Theme.Primary};
                color: {Theme.Surface};
            }}
        """
        widget.setStyleSheet(style)


def create_section_header(text, switch_widget=None):
    """辅助函数：创建分节标题行 (标签 + 开关)"""
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    label = QLabel(text)
    label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Theme.TextPrimary};")
    layout.addWidget(label)

    layout.addStretch()

    if switch_widget:
        layout.addWidget(switch_widget)

    return container


def create_param_row(label_text, widget, unit_text=None):
    """辅助函数：创建参数行"""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    lbl = QLabel(label_text)
    lbl.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px;")
    layout.addWidget(lbl)

    # 允许传入 QLayout，自动包一层容器
    if isinstance(widget, QHBoxLayout) or isinstance(widget, QVBoxLayout):
        container = QWidget()
        container.setLayout(widget)
        layout.addWidget(container)
    else:
        layout.addWidget(widget)

    if unit_text:
        unit = QLabel(unit_text)
        unit.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 12px;")
        layout.addWidget(unit)

    layout.addStretch() # 让控件靠左
    return row


def create_modern_scroll_area(content_widget):
    """辅助函数：创建现代风格的 ScrollArea"""
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll_area.setStyleSheet("""
        QScrollArea {
            background: transparent;
            border: none;
        }
        QScrollBar:vertical {
            background: transparent;
            width: 8px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #CBD5E1;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical:hover {
            background: #94A3B8;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            background: transparent;
            height: 8px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #CBD5E1;
            min-width: 20px;
            border-radius: 4px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #94A3B8;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
    """)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll_area.setWidget(content_widget)
    return scroll_area


class ModernDialog(QDialog):
    """现代风格基础对话框"""
    def __init__(
        self,
        title,
        parent=None,
        width=400,
        height=None,
        use_custom_titlebar=False,
        compact_titlebar=False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)

        if use_custom_titlebar:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setStyleSheet("background: transparent;")

            outer_layout = QVBoxLayout(self)
            outer_layout.setContentsMargins(10, 10, 10, 10)
            outer_layout.setSpacing(0)

            self.main_container = QFrame()
            self.main_container.setObjectName("DialogContainer")
            self.main_container.setStyleSheet(f"""
                QFrame#DialogContainer {{
                    background-color: {Theme.Background};
                    border-radius: 12px;
                    border: 1px solid {Theme.Border};
                }}
            """)

            self._shadow_effect = QGraphicsDropShadowEffect(self)
            self._shadow_effect.setBlurRadius(20)
            self._shadow_effect.setColor(QColor(0, 0, 0, 35))
            self._shadow_effect.setOffset(0, 4)
            self.main_container.setGraphicsEffect(self._shadow_effect)

            outer_layout.addWidget(self.main_container)

            container_layout = QVBoxLayout(self.main_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)

            self.title_bar = TitleBar(
                self,
                title,
                show_minimize=False,
                show_maximize=False,
                show_close=True,
                compact=compact_titlebar,
            )
            logo_pixmap = load_logo_pixmap()
            if not logo_pixmap.isNull():
                self.title_bar.set_logo(logo_pixmap)
            self.title_bar.window_closed.connect(self.reject)
            self.title_bar.window_moved.connect(self._handle_window_drag)

            container_layout.addWidget(self.title_bar)

            content_widget = QWidget()
            content_widget.setStyleSheet("background: transparent;")
            container_layout.addWidget(content_widget)

            self.layout = QVBoxLayout(content_widget)
            self.layout.setContentsMargins(20, 12, 20, 20)
            self.layout.setSpacing(16)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setStyleSheet(f"""
                QDialog {{
                    background-color: {Theme.Background};
                }}
            """)
            # 移除标题栏的"?"帮助按钮
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
            self.layout = QVBoxLayout(self)
            self.layout.setContentsMargins(24, 24, 24, 24)
            self.layout.setSpacing(20)

        if width and height:
            self.setFixedSize(width, height)
        elif width:
            self.setFixedWidth(width)

    def _handle_window_drag(self, delta):
        """处理窗口拖拽移动"""
        self.move(self.pos() + delta)
        
    def add_widget(self, widget):
        self.layout.addWidget(widget)

    def add_layout(self, layout):
        self.layout.addLayout(layout)


class ModernMessageBox(ModernDialog):
    """现代风格消息提示框"""
    def __init__(self, title, message, icon_name=None, icon_color=None, parent=None):
        metrics, body_text = ModernMessageBox._parse_summary_metrics(message)
        has_metrics = metrics is not None
        is_short_notice = (
            not has_metrics
            and body_text
            and "\n" not in body_text
            and len(body_text) <= 20
        )
        dialog_width = 520 if (has_metrics or is_short_notice) else 460

        super().__init__(
            title,
            parent,
            width=dialog_width,
            use_custom_titlebar=True,
            compact_titlebar=True,
        )

        accent_color = icon_color or Theme.Primary
        # 头部区域（图标徽章 + 标题 + 副文本）
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(14)

        if icon_name:
            badge = QFrame()
            badge.setObjectName("icon_badge")
            badge.setFixedSize(40, 40)
            badge.setStyleSheet(f"""
                QFrame#icon_badge {{
                    background-color: {self._rgba(accent_color, 0.12)};
                    border: 1px solid {self._rgba(accent_color, 0.28)};
                    border-radius: 20px;
                }}
                QLabel {{
                    background: transparent;
                    border: none;
                }}
            """)
            badge_layout = QVBoxLayout(badge)
            badge_layout.setContentsMargins(0, 0, 0, 0)
            icon_label = QLabel()
            icon = load_svg_icon(icon_name, 20, accent_color)
            icon_label.setPixmap(icon.pixmap(20, 20))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)
            header_layout.addWidget(badge)

        title_block = QVBoxLayout()
        title_block.setSpacing(4)
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700;
            color: {Theme.TextPrimary};
        """)
        title_block.addWidget(title_label)

        if has_metrics and body_text:
            subtitle_label = QLabel(body_text)
            subtitle_label.setWordWrap(True)
            subtitle_label.setStyleSheet(f"""
                font-size: 12px;
                color: {Theme.TextSecondary};
                line-height: 1.4;
            """)
            title_block.addWidget(subtitle_label)

        header_layout.addLayout(title_block, 1)
        self.layout.addWidget(header_widget)

        # 正文区域（仅非统计类弹窗显示）
        if not has_metrics:
            message_panel = QFrame()
            if is_short_notice:
                message_panel.setStyleSheet("background: transparent; border: none;")
            else:
                message_panel.setStyleSheet(f"""
                    QFrame {{
                        background-color: {Theme.Surface};
                        border: 1px solid {Theme.Border};
                        border-radius: 12px;
                    }}
                """)
            panel_layout = QVBoxLayout(message_panel)
            panel_layout.setContentsMargins(0 if is_short_notice else 16, 16, 0 if is_short_notice else 16, 16)
            panel_layout.setSpacing(8)

            msg_label = QLabel(body_text)
            msg_label.setWordWrap(True)
            if is_short_notice:
                msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                msg_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                msg_label.setMinimumWidth(320)
                msg_label.setStyleSheet(f"""
                    font-size: 13px;
                    font-weight: 600;
                    color: {Theme.TextPrimary};
                    line-height: 1.5;
                    background-color: {self._rgba(accent_color, 0.12)};
                    border: 1px solid {self._rgba(accent_color, 0.26)};
                    border-radius: 16px;
                    padding: 7px 18px;
                """)
                shadow = QGraphicsDropShadowEffect(msg_label)
                shadow.setBlurRadius(16)
                shadow.setColor(QColor(0, 0, 0, 25))
                shadow.setOffset(0, 3)
                msg_label.setGraphicsEffect(shadow)
            else:
                msg_label.setStyleSheet(f"""
                    font-size: 14px;
                    color: {Theme.TextSecondary};
                    line-height: 1.5;
                """)
            msg_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.LinksAccessibleByMouse |
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            if is_short_notice:
                panel_layout.addWidget(msg_label, 0, Qt.AlignmentFlag.AlignCenter)
            else:
                panel_layout.addWidget(msg_label)
            self.layout.addWidget(message_panel)

        # 统计区域（完成类弹窗）
        if has_metrics:
            stats_frame = QFrame()
            # 移除 stats_frame 的背景和边框，改为透明容器，让内部卡片自带样式
            stats_frame.setStyleSheet("background: transparent; border: none;")
            
            stats_layout = QGridLayout(stats_frame)
            stats_layout.setContentsMargins(0, 6, 0, 6)  # 稍收紧，提升通知感
            stats_layout.setHorizontalSpacing(16)
            stats_layout.setVerticalSpacing(12)

            lang = get_language_manager().language
            order = ["success", "failed", "skipped", "total"]
            title_map = {
                "success": {"zh_CN": "成功", "en": "Success"},
                "failed": {"zh_CN": "失败", "en": "Failed"},
                "skipped": {"zh_CN": "跳过", "en": "Skipped"},
                "total": {"zh_CN": "总数", "en": "Total"},
            }
            color_map = {
                "success": Theme.Success,
                "failed": Theme.Error,
                "skipped": Theme.Warning,
                "total": Theme.Primary,
            }
            for idx, key in enumerate(order):
                value = metrics.get(key, "0")
                # 只有当失败数大于0时才认为是"highlight"（但在新设计中我们统一风格）
                is_failure = key == "failed" and self._is_positive_number(value)
                title = title_map.get(key, {}).get(lang, title_map.get(key, {}).get("zh_CN", key))
                card = self._build_metric_card(title, value, color_map.get(key, Theme.Primary), is_failure)
                stats_layout.addWidget(card, idx // 2, idx % 2)

            self.layout.addWidget(stats_frame)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.ok_btn = ModernButton(t("common.btn.ok", "确定"), ModernButton.Style.Primary)
        self.ok_btn.setMinimumWidth(90)
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)
        
        self.layout.addLayout(btn_layout)

    @staticmethod
    def _parse_summary_metrics(message: str):
        lines = [line.strip() for line in str(message).splitlines()]
        metric_alias = {
            "成功": "success",
            "success": "success",
            "Success": "success",
            "失败": "failed",
            "failed": "failed",
            "Failed": "failed",
            "跳过": "skipped",
            "skipped": "skipped",
            "Skipped": "skipped",
            "总数": "total",
            "total": "total",
            "Total": "total",
        }
        required_keys = ("success", "failed", "skipped", "total")
        metrics = {}
        metric_line_idx = set()
        for idx, line in enumerate(lines):
            if not line:
                continue
            if ":" in line:
                key_raw, value = line.split(":", 1)
            elif "：" in line:
                key_raw, value = line.split("：", 1)
            else:
                continue
            canonical = metric_alias.get(key_raw.strip())
            if canonical:
                metrics[canonical] = value.strip()
                metric_line_idx.add(idx)

        if all(k in metrics for k in required_keys):
            body_lines = [lines[i] for i in range(len(lines)) if i not in metric_line_idx and lines[i]]
            body_text = "\n".join(body_lines).strip()
            return metrics, body_text

        return None, str(message).strip()

    def _is_positive_number(self, value: str) -> bool:
        try:
            return int(value) > 0
        except Exception:
            return False

    def _rgba(self, color: str, alpha: float) -> str:
        base = QColor(color)
        base.setAlphaF(alpha)
        return f"rgba({base.red()}, {base.green()}, {base.blue()}, {base.alpha()})"

    def _build_metric_card(self, title: str, value: str, accent: str, highlight: bool = False) -> QWidget:
        card = QFrame()
        card.setObjectName("metric_card")
        
        # 新设计：白色卡片 + 阴影 + 顶部彩色条/文字颜色
        card.setStyleSheet(f"""
            QFrame#metric_card {{
                background-color: {Theme.Surface};
                border: 1px solid {Theme.Border};
                border-radius: 12px;
            }}
            QLabel {{
                background: transparent;
                border: none;
            }}
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(16)
        shadow.setColor(QColor(0, 0, 0, 12)) # 柔和阴影
        shadow.setOffset(0, 4)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        # 标题
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: {Theme.TextSecondary};
        """)
        
        # 数值
        value_label = QLabel(str(value))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # 数值使用强调色，加大字号
        value_label.setStyleSheet(f"""
            font-size: 26px;
            font-weight: 800;
            color: {accent};
            font-family: 'Segoe UI', sans-serif;
        """)
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        
        return card

    @staticmethod
    def information(parent, title, message):
        dlg = ModernMessageBox(title, message, "check", Theme.Success, parent)
        return dlg.exec()

    @staticmethod
    def warning(parent, title, message):
        dlg = ModernMessageBox(title, message, "activity", Theme.Warning, parent)
        return dlg.exec()
        
    @staticmethod
    def error(parent, title, message):
        dlg = ModernMessageBox(title, message, "cross", Theme.Error, parent)
        return dlg.exec()
