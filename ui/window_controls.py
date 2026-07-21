import sys
from PyQt6.QtWidgets import (
    QWidget, QPushButton, QHBoxLayout, QLabel, QApplication,
    QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QRectF
from PyQt6.QtGui import QIcon, QPainter, QColor, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from ui.theme import Theme


class WindowButton(QPushButton):
    """自定义窗口控制按钮（最小化、最大化、关闭）"""

    def __init__(self, icon_name, parent=None, is_close=False):
        super().__init__(parent)
        self.setFixedSize(46, 32)
        self.icon_name = icon_name
        self.is_close = is_close
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # SVG 图标数据 - 圆角风格
        self.icons = {
            "minimize": """
                <svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                    <line x1="4" y1="9" x2="12" y2="9" stroke="{color}" stroke-width="1.6" stroke-linecap="round"/>
                </svg>
            """,
            "maximize": """
                <svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                    <rect x="4.5" y="4.5" width="7" height="7" rx="1.4" stroke="{color}" stroke-width="1.6" fill="none"/>
                </svg>
            """,
            "restore": """
                <svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                    <rect x="6" y="3.5" width="6.5" height="6.5" rx="1.2" stroke="{color}" stroke-width="1.4" fill="none" opacity="0.6"/>
                    <rect x="3.5" y="6" width="6.5" height="6.5" rx="1.2" stroke="{color}" stroke-width="1.6" fill="none"/>
                </svg>
            """,
            "close": """
                <svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
                    <path d="M4.5 4.5 L11.5 11.5 M11.5 4.5 L4.5 11.5" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
            """
        }

        self.setStyleSheet("background-color: transparent; border: none;")
        self.base_bg_color = "#F1F5F9"  # Slate-100 default background
        self.hover_color = Theme.Error if is_close else "#E2E8F0"  # fallback
        self.default_icon_color = "#475569"  # Slate-600

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景（默认圆角矩形）
        if self.underMouse():
            if self.is_close:
                bg_color = "#F9E8E8"
            elif self.icon_name == "minimize":
                bg_color = "#EAEFF9"
            elif self.icon_name in ("maximize", "restore"):
                bg_color = "#E5F6EC"
            else:
                bg_color = self.hover_color
        else:
            bg_color = self.base_bg_color
        painter.setBrush(QColor(bg_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(3, 3, self.width() - 6, self.height() - 6, 7, 7)

        if self.underMouse():
            icon_color = "#1E293B"
        else:
            icon_color = self.default_icon_color

        # 绘制图标
        svg_xml = self.icons.get(self.icon_name, "").replace("{color}", icon_color)
        renderer = QSvgRenderer(svg_xml.encode("utf-8"))
        icon_size = 20
        icon_rect = QRectF(
            (self.width() - icon_size) / 2,
            (self.height() - icon_size) / 2,
            icon_size,
            icon_size,
        )
        renderer.render(painter, icon_rect)


class TitleBar(QWidget):
    """自定义无边框窗口标题栏"""

    # 信号：最小化、最大化/还原、关闭
    window_minimized = pyqtSignal()
    window_maximized = pyqtSignal()
    window_restored = pyqtSignal()
    window_closed = pyqtSignal()
    window_moved = pyqtSignal(QPoint)

    def __init__(
        self,
        parent=None,
        title="Application",
        show_minimize=True,
        show_maximize=True,
        show_close=True,
        compact=False,
    ):
        super().__init__(parent)
        self.setFixedHeight(52 if compact else 60)  # 缩小标题栏高度
        self.is_maximized = False
        self._show_minimize = show_minimize
        self._show_maximize = show_maximize
        self._show_close = show_close

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16 if compact else 20, 0, 8 if compact else 10, 0)  # 顶部贴边
        layout.setSpacing(15)

        # 1. Logo
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(72 if compact else 90, 44 if compact else 55)
        self.logo_label.setScaledContents(False)

        # 2. 标题
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            font-family: 'Microsoft YaHei UI', sans-serif;
            font-size: {"13px" if compact else "14px"};
            font-weight: bold;
            color: {Theme.TextPrimary};
        """)

        # 3. 窗口控制按钮组
        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(2)
        self.controls_layout.setContentsMargins(0, 0, 0, 0)
        self.controls_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_minimize = WindowButton("minimize") if show_minimize else None
        self.btn_maximize = WindowButton("maximize") if show_maximize else None
        self.btn_close = WindowButton("close", is_close=True) if show_close else None

        if self.btn_minimize:
            self.btn_minimize.clicked.connect(self.window_minimized.emit)
        if self.btn_maximize:
            self.btn_maximize.clicked.connect(self.toggle_maximize)
        if self.btn_close:
            self.btn_close.clicked.connect(self.window_closed.emit)

        if self.btn_minimize:
            self.controls_layout.addWidget(self.btn_minimize, 0, Qt.AlignmentFlag.AlignVCenter)
        if self.btn_maximize:
            self.controls_layout.addWidget(self.btn_maximize, 0, Qt.AlignmentFlag.AlignVCenter)
        if self.btn_close:
            self.controls_layout.addWidget(self.btn_close, 0, Qt.AlignmentFlag.AlignVCenter)

        # 4. 广告位和登录组件的占位布局（在控制按钮左侧）
        self.extra_widgets_layout = QHBoxLayout()
        self.extra_widgets_layout.setSpacing(8)
        self.extra_widgets_layout.setContentsMargins(0, 0, 0, 0)
        self.extra_widgets_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 布局组装
        # logo靠顶部对齐
        layout.addWidget(self.logo_label)
        layout.addWidget(self.title_label)
        layout.setAlignment(self.logo_label, Qt.AlignmentFlag.AlignTop)
        layout.setAlignment(self.title_label, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()  # 弹簧，把控制按钮推到右边
        layout.addLayout(self.extra_widgets_layout)
        layout.addLayout(self.controls_layout)

        # 拖拽相关
        self.start_pos = None
        self.is_dragging = False

    def toggle_maximize(self):
        if not self._show_maximize:
            return
        if self.is_maximized:
            self.window_restored.emit()
        else:
            self.window_maximized.emit()

    def set_maximized(self, is_maximized: bool):
        self.is_maximized = is_maximized
        if self.btn_maximize:
            self.btn_maximize.icon_name = "restore" if is_maximized else "maximize"
            self.btn_maximize.update()

    def set_title(self, title):
        self.title_label.setText(title)

    def set_logo(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            target_size = self.logo_label.size()
            scaled = pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.logo_label.setPixmap(scaled)

    def set_ad_widget(self, widget):
        """设置广告组件（插入到控制按钮左侧）"""
        self.extra_widgets_layout.insertWidget(0, widget, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_login_widget(self, widget):
        """设置登录组件（插入到控制按钮左侧，广告右侧）"""
        self.extra_widgets_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.start_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.window_moved.emit(delta)
            self.start_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

    def mouseDoubleClickEvent(self, event):
        # 双击标题栏切换最大化
        if event.button() == Qt.MouseButton.LeftButton and self._show_maximize:
            self.toggle_maximize()
