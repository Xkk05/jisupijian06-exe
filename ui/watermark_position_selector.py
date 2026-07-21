"""水印位置选择器
支持拖动框定位水印位置，显示实际视频和水印
"""
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import cv2
import os

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QByteArray, QSize
from PyQt6.QtGui import (
    QPen, QColor, QPixmap, QPainter, QFont, QImage, QTransform,
    QBrush, QFontMetricsF, QPainterPath, QIcon
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QGraphicsTextItem, QSpinBox, QDoubleSpinBox, QComboBox,
    QFontDialog, QSlider, QLineEdit, QScrollArea,
    QGridLayout, QWidget, QCheckBox, QRadioButton, QButtonGroup,
    QGraphicsEllipseItem
)

from ui.theme import Theme
from ui.i18n import apply_language_to_widget, get_language_manager
from ui.components import (
    ModernCard, ModernButton, ModernInput,
    create_param_row, create_section_header, create_modern_scroll_area, open_color_dialog
)
from utils.enum_codes import normalize_text_arrange


def _ts(text: str) -> str:
    return get_language_manager().translate_source_text(text)


_SUPPORTED_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp'}


class ResizeHandle(QGraphicsEllipseItem):
    """调整手柄（不可移动，只用于调整父项大小）"""

    def __init__(self, handle_type: str, parent_item):
        """
        Args:
            handle_type: 手柄类型 ('tl', 'tr', 'bl', 'br', 't', 'b', 'l', 'r')
            parent_item: 父水印项
        """
        super().__init__(-5, -5, 10, 10)

        self.handle_type = handle_type
        self.parent_watermark = parent_item
        self.is_dragging = False
        self.drag_start_pos = None
        self.drag_start_rect = None
        self.drag_start_item_pos = None

        # 设置样式
        self.setBrush(QBrush(QColor(Theme.Surface)))
        self.setPen(QPen(QColor(Theme.Primary), 2))

        # 不设置 ItemIsMovable，手柄本身不移动
        self.setParentItem(parent_item)
        self.setZValue(100)
        self.setAcceptHoverEvents(True)

        # 设置光标
        cursor_map = {
            'tl': Qt.CursorShape.SizeFDiagCursor,
            'tr': Qt.CursorShape.SizeBDiagCursor,
            'bl': Qt.CursorShape.SizeBDiagCursor,
            'br': Qt.CursorShape.SizeFDiagCursor,
            't': Qt.CursorShape.SizeVerCursor,
            'b': Qt.CursorShape.SizeVerCursor,
            'l': Qt.CursorShape.SizeHorCursor,
            'r': Qt.CursorShape.SizeHorCursor
        }
        self.setCursor(cursor_map.get(handle_type, Qt.CursorShape.SizeAllCursor))

    def mousePressEvent(self, event):
        """鼠标按下 - 开始调整"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_start_pos = event.scenePos()
            if self.parent_watermark:
                self.drag_start_rect = self.parent_watermark.boundingRect()
                self.drag_start_item_pos = self.parent_watermark.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动 - 调整父项大小"""
        if self.is_dragging and self.parent_watermark:
            self.parent_watermark.handle_dragging(
                self.handle_type,
                self.drag_start_pos,
                event.scenePos(),
                self.drag_start_rect,
                self.drag_start_item_pos
            )
            event.accept()

    def mouseReleaseEvent(self, event):
        """鼠标释放 - 结束调整"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            event.accept()


class ResizableWatermarkItem(QGraphicsPixmapItem):
    """可拖动、可缩放的水印图片项（带调整手柄）"""

    def __init__(self, pixmap: QPixmap):
        super().__init__(pixmap)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsFocusable)

        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setOpacity(0.9)

        self.original_pixmap = pixmap
        self.current_scale = 1.0
        self.current_width = pixmap.width()
        self.current_height = pixmap.height()

        # 调整手柄
        self.handles = {}
        self.create_handles()

        # 调整标志
        self.is_resizing = False
        self.resize_start_pos = None
        self.resize_start_rect = None

    def create_handles(self):
        """创建8个调整手柄"""
        handle_types = ['tl', 'tr', 'bl', 'br', 't', 'b', 'l', 'r']
        for handle_type in handle_types:
            handle = ResizeHandle(handle_type, self)
            handle.setZValue(100)
            handle.setVisible(False)
            self.handles[handle_type] = handle

        self.update_handle_positions()

    def handle_dragging(self, handle_type: str, start_pos, current_pos, start_rect, start_item_pos):
        """手柄拖动中，实时调整水印大小"""
        delta_x = current_pos.x() - start_pos.x()
        delta_y = current_pos.y() - start_pos.y()

        min_size = 20

        new_w = start_rect.width()
        new_h = start_rect.height()
        new_x = start_item_pos.x()
        new_y = start_item_pos.y()

        if handle_type == 'tl':
            new_w = max(min_size, start_rect.width() - delta_x)
            new_h = max(min_size, start_rect.height() - delta_y)
            new_x = start_item_pos.x() + (start_rect.width() - new_w)
            new_y = start_item_pos.y() + (start_rect.height() - new_h)
        elif handle_type == 'tr':
            new_w = max(min_size, start_rect.width() + delta_x)
            new_h = max(min_size, start_rect.height() - delta_y)
            new_y = start_item_pos.y() + (start_rect.height() - new_h)
        elif handle_type == 'bl':
            new_w = max(min_size, start_rect.width() - delta_x)
            new_h = max(min_size, start_rect.height() + delta_y)
            new_x = start_item_pos.x() + (start_rect.width() - new_w)
        elif handle_type == 'br':
            new_w = max(min_size, start_rect.width() + delta_x)
            new_h = max(min_size, start_rect.height() + delta_y)
        elif handle_type == 't':
            new_h = max(min_size, start_rect.height() - delta_y)
            new_y = start_item_pos.y() + (start_rect.height() - new_h)
        elif handle_type == 'b':
            new_h = max(min_size, start_rect.height() + delta_y)
        elif handle_type == 'l':
            new_w = max(min_size, start_rect.width() - delta_x)
            new_x = start_item_pos.x() + (start_rect.width() - new_w)
        elif handle_type == 'r':
            new_w = max(min_size, start_rect.width() + delta_x)

        self.setPos(new_x, new_y)
        self.resize_to(int(new_w), int(new_h))

    def update_handle_positions(self):
        """更新手柄位置"""
        rect = self.boundingRect()
        w = rect.width()
        h = rect.height()

        self.handles['tl'].setPos(0, 0)
        self.handles['tr'].setPos(w, 0)
        self.handles['bl'].setPos(0, h)
        self.handles['br'].setPos(w, h)
        self.handles['t'].setPos(w / 2, 0)
        self.handles['b'].setPos(w / 2, h)
        self.handles['l'].setPos(0, h / 2)
        self.handles['r'].setPos(w, h / 2)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            pen = QPen(QColor(Theme.Primary), 2)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.boundingRect())
            for handle in self.handles.values():
                handle.setVisible(True)
        else:
            for handle in self.handles.values():
                handle.setVisible(False)

    def itemChange(self, change, value):
        if change == QGraphicsPixmapItem.GraphicsItemChange.ItemSelectedChange:
            self.update()
        return super().itemChange(change, value)

    def resize_to(self, width: int, height: int):
        self.current_width = width
        self.current_height = height
        scaled_pixmap = self.original_pixmap.scaled(
            width, height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)
        self.update_handle_positions()

    def scale_watermark(self, scale: float):
        self.current_scale = scale
        new_w = int(self.original_pixmap.width() * scale)
        new_h = int(self.original_pixmap.height() * scale)
        self.resize_to(new_w, new_h)

    def keyPressEvent(self, event):
        step = 10 if event.modifiers() == Qt.KeyboardModifier.ShiftModifier else 1
        current_pos = self.pos()
        new_pos = current_pos

        if event.key() == Qt.Key.Key_Left:
            new_pos.setX(current_pos.x() - step)
        elif event.key() == Qt.Key.Key_Right:
            new_pos.setX(current_pos.x() + step)
        elif event.key() == Qt.Key.Key_Up:
            new_pos.setY(current_pos.y() - step)
        elif event.key() == Qt.Key.Key_Down:
            new_pos.setY(current_pos.y() + step)
        else:
            super().keyPressEvent(event)
            return

        scene = self.scene()
        if scene:
            scene_rect = scene.sceneRect()
            item_rect = self.boundingRect()
            new_pos.setX(max(0, min(new_pos.x(), scene_rect.width() - item_rect.width())))
            new_pos.setY(max(0, min(new_pos.y(), scene_rect.height() - item_rect.height())))

        self.setPos(new_pos)
        event.accept()


class DraggablePixmapItem(QGraphicsPixmapItem):
    """可拖动的文字贴图项（不支持缩放）"""

    def __init__(self, pixmap: QPixmap):
        super().__init__(pixmap)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsFocusable)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            pen = QPen(QColor(Theme.Primary), 2)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.boundingRect())


class ResizableTextItem(QGraphicsTextItem):
    """可拖动、可调整的文字水印项"""

    def __init__(self, text: str, font: QFont, color: QColor):
        super().__init__(text)
        self.setFont(font)
        self.setDefaultTextColor(color)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsTextItem.GraphicsItemFlag.ItemIsFocusable)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        if self.isSelected():
            pen = QPen(QColor(Theme.Primary), 2)
            pen.setStyle(Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(self.boundingRect())

    def keyPressEvent(self, event):
        step = 10 if event.modifiers() == Qt.KeyboardModifier.ShiftModifier else 1
        current_pos = self.pos()
        new_pos = current_pos

        if event.key() == Qt.Key.Key_Left:
            new_pos.setX(current_pos.x() - step)
        elif event.key() == Qt.Key.Key_Right:
            new_pos.setX(current_pos.x() + step)
        elif event.key() == Qt.Key.Key_Up:
            new_pos.setY(current_pos.y() - step)
        elif event.key() == Qt.Key.Key_Down:
            new_pos.setY(current_pos.y() + step)
        else:
            super().keyPressEvent(event)
            return

        scene = self.scene()
        if scene:
            scene_rect = scene.sceneRect()
            item_rect = self.boundingRect()
            new_pos.setX(max(0, min(new_pos.x(), scene_rect.width() - item_rect.width())))
            new_pos.setY(max(0, min(new_pos.y(), scene_rect.height() - item_rect.height())))

        self.setPos(new_pos)
        event.accept()


class WatermarkPositionSelector(QDialog):
    """水印位置选择器对话框 - 支持实际视频和水印显示"""

    position_selected = pyqtSignal(int, int, int, int)

    def __init__(self, watermark_config: dict, video_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.watermark_config = watermark_config
        self.video_path = video_path
        self.video_frame = None
        self.watermark_item = None
        self.scale_factor = 1.0
        self.video_width = 1920
        self.video_height = 1080
        self.original_watermark_size = (200, 100)
        self._language_manager = get_language_manager()

        style_config = watermark_config.get('style_config', {})
        font_cfg = style_config.get('font', {})
        self.text_font = QFont(font_cfg.get('family', 'Microsoft YaHei'))
        self.text_font.setPixelSize(int(font_cfg.get('size', 36)))
        self.text_font.setBold(font_cfg.get('bold', False))
        self.text_font.setItalic(font_cfg.get('italic', False))
        self.text_color = QColor(style_config.get('color', '#FFFFFF'))
        
        # 初始化字体路径缓存（保留已有路径）
        self._font_path_cache = {}
        if 'path' in font_cfg and font_cfg['path']:
            self._font_path_cache[font_cfg.get('family', 'Microsoft YaHei')] = font_cfg['path']

        self.init_ui()
        self._language_manager.language_changed.connect(self._on_language_changed)
        self._on_language_changed(self._language_manager.language)

    def _on_language_changed(self, _lang: str) -> None:
        apply_language_to_widget(self)

    def init_ui(self):
        self.setWindowTitle(_ts("手动定位水印位置"))
        self.setMinimumSize(1500, 780)
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        # 设置整个对话框的背景为深色，以便右侧面板的圆角和背景能显现出来
        # 同时保持深色背景适合视频预览
        self.setStyleSheet("background-color: #f8fafc;")

        main_layout = QHBoxLayout(self)

        left_layout = QVBoxLayout()
        info_label = QLabel(_ts("拖动水印到目标位置，使用右侧控制面板调整尺寸和样式"))
        # 修复左侧文字颜色，使其在深色背景上可见
        info_label.setStyleSheet(
            f"color: {Theme.TextPrimary}; font-size: 13px; padding: 12px 16px; "
            f"background: {Theme.Surface}; "
            f"border: 1px solid {Theme.Border}; "  # 增加四周边框
            f"border-left: 4px solid {Theme.Primary}; "  # 保持左侧强调色（覆盖左侧细边框）
            f"border-radius: 4px; font-weight: 500;"
        )
        left_layout.addWidget(info_label)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        # 减小最小尺寸限制，允许更灵活的布局
        self.view.setMinimumSize(400, 225)
        # 设置 View 背景为黑色，边框
        self.view.setStyleSheet(f"border: 2px solid {Theme.Border}; background: #000;")
        # 隐藏滚动条
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        left_layout.addWidget(self.view)

        self.load_video_background()
        self.load_watermark()
        self.apply_config_to_controls()

        self.position_info = QLabel()
        self.position_info.setStyleSheet(
            f"color: {Theme.TextPrimary}; font-size: 11px; padding: 8px; "
            f"background: {Theme.Surface}; border-radius: 4px; border: 1px solid {Theme.Border};"
        )
        self.update_position_info()
        left_layout.addWidget(self.position_info)

        main_layout.addLayout(left_layout, 3)

        right_widget = self.create_control_panel()
        main_layout.addWidget(right_widget, 1)

        from PyQt6.QtCore import QTimer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_position_info)
        self.update_timer.start(100)

    def create_control_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(400)
        # 确保背景色为 Theme.Background (#F8FAFC)，无左边框，设置左上/下圆角
        panel.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.Background};
                border-left: none;
                border-top-left-radius: 20px;
                border-bottom-left-radius: 20px;
            }}
        """)

        main_layout = QVBoxLayout(panel)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        header_container = QWidget()
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(20, 20, 20, 10)
        title_label = QLabel(_ts("水印控制"))
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Theme.TextPrimary};")
        header_layout.addWidget(title_label)
        main_layout.addWidget(header_container)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 10, 20, 20)

        watermark_type = self.watermark_config.get('type', 'image')

        self.create_position_grid(content_layout)
        if watermark_type == 'image':
            self.create_image_controls(content_layout)
        else:
            self.create_text_controls(content_layout)

        self.create_advanced_style_panel(content_layout)
        content_layout.addStretch()

        scroll = create_modern_scroll_area(content_widget)
        main_layout.addWidget(scroll)

        button_container = QWidget()
        # 将其改为卡片样式：背景Surface, 边框Border, 圆角12px, 并通过margin设置与上方卡片等宽
        button_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Theme.Surface};
                border: 1px solid {Theme.Border};
                border-radius: 12px;
                margin: 5px 5px 0px 20px; /* 上 右 下 左，与上方内容区域对齐 */
            }}
        """)
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 15, 20, 15)
        button_layout.setSpacing(10)

        reset_btn = ModernButton(_ts("重置"), style=ModernButton.Style.Secondary)
        reset_btn.clicked.connect(self.reset_watermark)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        cancel_btn = ModernButton(_ts("取消"), style=ModernButton.Style.Secondary)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = ModernButton(_ts("确定"), style=ModernButton.Style.Primary)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept_position)
        button_layout.addWidget(ok_btn)

        main_layout.addWidget(button_container)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self.sync_style_to_preview)
        return panel

    def _create_svg_icon(self, svg_path: str, color: str = None) -> QIcon:
        if color is None:
            color = Theme.TextPrimary
        
        svg_content = f"""
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="{svg_path}" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        """
        
        renderer = QSvgRenderer(QByteArray(svg_content.encode("utf-8")))
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)

    def create_position_grid(self, layout: QVBoxLayout):
        card = ModernCard(_ts("快速定位"))
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # SVG Paths
        icons = {
            "tl": "M19 19L5 5M5 5V19M5 5H19", # Top-Left (actually pointing top-left: arrow head at 5,5) -> M19 19 L5 5 (line) M5 14 V5 (arrow part) ... let's use standard arrows
            "t": "M12 19V5M5 12L12 5L19 12",
            "tr": "M5 19L19 5M19 5V19M19 5H5", 
            "l": "M19 12H5M12 19L5 12L12 5",
            "center": "M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0", # Circle
            "r": "M5 12H19M12 5L19 12L12 19",
            "bl": "M19 5L5 19M5 19V5M5 19H19",
            "b": "M12 5V19M19 12L12 19L5 12",
            "br": "M5 5L19 19M19 19V5M19 19H5"
        }
        
        # Adjust paths to be correct arrows
        # TL: Arrow pointing to top left corner
        icons["tl"] = "M17 7H7V17M7 7L17 17" # Wait, M17 7H7V17 is a corner? No.
        # Let's use simple arrows:
        # TL: Top Left
        icons["tl"] = "M6 18L18 6M6 6H15M6 6V15" 
        icons["tr"] = "M6 6L18 18M18 6H9M18 6V15" # Pointing TR? No, this is pointing TR. M6 6 to 18 18 is diagonal down-right?
        # Coordinate system: 0,0 is top-left.
        # TL (NorthWest): Arrow should point to 0,0. From center to corner? Or just a corner symbol?
        # User wants "Quick Position". Usually these are arrows pointing to the position.
        
        icons = {
            "tl": "M15 15L6 6M6 6H15M6 6V15", # Arrow pointing to TL
            "t": "M12 21V3M5 10L12 3L19 10", # Arrow pointing Up
            "tr": "M9 15L18 6M18 6H9M18 6V15", # Arrow pointing TR
            "l": "M21 12H3M10 19L3 12L10 5", # Arrow pointing Left
            "center": "M12 12M12 8A4 4 0 1 1 12 16A4 4 0 1 1 12 8", # Bullseye/Target - adjusted path for circle
            "r": "M3 12H21M14 5L21 12L14 19", # Arrow pointing Right
            "bl": "M15 9L6 18M6 18H15M6 18V9", # Arrow pointing BL
            "b": "M12 3V21M19 14L12 21L5 14", # Arrow pointing Down
            "br": "M9 9L18 18M18 18H9M18 18V9"  # Arrow pointing BR
        }
        
        # Fix Center icon path (circle)
        # Using a crosshair or target
        icons["center"] = "M12 3V21M3 12H21M17 12A5 5 0 1 1 7 12A5 5 0 1 1 17 12"

        positions = [
            ("tl", 0, 0), ("t", 0, 1), ("tr", 0, 2),
            ("l", 1, 0), ("center", 1, 1), ("r", 1, 2),
            ("bl", 2, 0), ("b", 2, 1), ("br", 2, 2)
        ]

        for pos_code, row, col in positions:
            btn = ModernButton("", style=ModernButton.Style.Outline)
            btn.setFixedSize(40, 40)
            
            # Create Icon
            icon_color = Theme.TextPrimary
            btn.setIcon(self._create_svg_icon(icons[pos_code], icon_color))
            btn.setIconSize(QSize(20, 20))
            
            btn.clicked.connect(lambda checked, p=pos_code: self.set_preset_position(p))
            grid_layout.addWidget(btn, row, col)

        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(grid_container)
        h_layout.addStretch()

        card.addLayout(h_layout)
        layout.addWidget(card)

    def create_image_controls(self, layout: QVBoxLayout):
        card = ModernCard(_ts("尺寸与透明度"))

        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(10, 300)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)

        self.scale_label = QLabel("100%")
        self.scale_label.setFixedWidth(40)
        self.scale_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        scale_row = QHBoxLayout()
        scale_row.addWidget(self.scale_slider)
        scale_row.addWidget(self.scale_label)
        card.addWidget(create_param_row("缩放比例:", scale_row))

        size_layout = QHBoxLayout()
        size_layout.setSpacing(10)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 9999)
        self.width_spin.setValue(200)
        self.width_spin.setSuffix(" px")
        ModernInput.apply_style(self.width_spin)
        self.width_spin.valueChanged.connect(self.on_size_changed)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 9999)
        self.height_spin.setValue(100)
        self.height_spin.setSuffix(" px")
        ModernInput.apply_style(self.height_spin)
        self.height_spin.valueChanged.connect(self.on_size_changed)

        size_layout.addWidget(QLabel("W:"))
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("H:"))
        size_layout.addWidget(self.height_spin)
        size_layout.addStretch()

        card.addWidget(create_param_row("精确尺寸:", size_layout))

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(90)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)

        self.opacity_label = QLabel("90%")
        self.opacity_label.setFixedWidth(40)
        self.opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.opacity_slider)
        opacity_row.addWidget(self.opacity_label)

        card.addWidget(create_param_row("不透明度:", opacity_row))
        layout.addWidget(card)

    def create_text_controls(self, layout: QVBoxLayout):
        card = ModernCard(_ts("文字设置"))

        self.text_edit = QLineEdit()
        self.text_edit.setText(self.watermark_config.get('text_content', '水印文字'))
        self.text_edit.setPlaceholderText(_ts("请输入水印文字"))
        ModernInput.apply_style(self.text_edit)
        self.text_edit.textChanged.connect(self.on_text_changed)
        card.addWidget(create_param_row("文字内容:", self.text_edit))

        font_layout = QHBoxLayout()
        self.font_btn = ModernButton(
            f"{self.text_font.family()} {self.text_font.pixelSize()}px",
            style=ModernButton.Style.Outline
        )
        self.font_btn.clicked.connect(self.choose_font)
        font_layout.addWidget(self.font_btn)

        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(36, 36)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.setStyleSheet(
            f"background-color: {self.text_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;"
        )
        self.color_btn.clicked.connect(self.choose_color)
        font_layout.addWidget(self.color_btn)
        card.addWidget(create_param_row("字体样式:", font_layout))

        style_config = self.watermark_config.get('style_config', {})
        self.font_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_size_slider.setRange(12, 500)
        self.font_size_slider.setValue(int(self.text_font.pixelSize()))
        self.font_size_slider.valueChanged.connect(self.on_font_size_changed)

        self.font_size_label = QLabel(f"{self.text_font.pixelSize()}px")
        self.font_size_label.setFixedWidth(40)
        self.font_size_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        size_row = QHBoxLayout()
        size_row.addWidget(self.font_size_slider)
        size_row.addWidget(self.font_size_label)
        card.addWidget(create_param_row("字体大小:", size_row))

        text_opacity = float(style_config.get('opacity', 1.0))
        self.text_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_opacity_slider.setRange(0, 100)
        self.text_opacity_slider.setValue(int(text_opacity * 100))
        self.text_opacity_slider.valueChanged.connect(self.on_text_opacity_changed)

        self.text_opacity_label = QLabel(f"{int(text_opacity * 100)}%")
        self.text_opacity_label.setFixedWidth(40)
        self.text_opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.text_opacity_slider)
        opacity_row.addWidget(self.text_opacity_label)
        card.addWidget(create_param_row("不透明度:", opacity_row))

        layout.addWidget(card)

    def create_advanced_style_panel(self, layout: QVBoxLayout):
        watermark_type = self.watermark_config.get('type', 'image')

        effects_card = ModernCard(_ts("效果设置"))
        self.rotation_angle = QDoubleSpinBox()
        self.rotation_angle.setRange(-360, 360)
        self.rotation_angle.setSuffix(" °")
        self.rotation_angle.setValue(0)
        ModernInput.apply_style(self.rotation_angle)
        self.rotation_angle.valueChanged.connect(self.on_style_changed)
        effects_card.addWidget(create_param_row("旋转角度:", self.rotation_angle))

        if watermark_type == 'image':
            self.feather_value = QDoubleSpinBox()
            self.feather_value.setRange(0, 1)
            self.feather_value.setSingleStep(0.01)
            self.feather_value.setValue(0)
            ModernInput.apply_style(self.feather_value)
            self.feather_value.valueChanged.connect(self.on_style_changed)
            effects_card.addWidget(create_param_row("边缘羽化:", self.feather_value))

            checks_layout = QHBoxLayout()
            self.remove_black_edges = QCheckBox(_ts("去除黑边"))
            self.remove_black_edges.stateChanged.connect(self.on_style_changed)
            checks_layout.addWidget(self.remove_black_edges)
            self.circular_display = QCheckBox(_ts("圆形裁剪"))
            self.circular_display.stateChanged.connect(self.on_style_changed)
            checks_layout.addWidget(self.circular_display)
            effects_card.addWidget(create_param_row("裁剪模式:", checks_layout))

            layout.addWidget(effects_card)

            timing_card = ModernCard(_ts("时间控制"))
            time_grid = QGridLayout()
            time_grid.setSpacing(10)

            self.delay_time = QDoubleSpinBox()
            self.delay_time.setRange(0, 9999)
            self.delay_time.setSuffix(" s")
            ModernInput.apply_style(self.delay_time)
            self.delay_time.valueChanged.connect(self.on_style_changed)

            self.interval_time = QDoubleSpinBox()
            self.interval_time.setRange(0, 9999)
            self.interval_time.setSuffix(" s")
            ModernInput.apply_style(self.interval_time)
            self.interval_time.valueChanged.connect(self.on_style_changed)

            self.duration_time = QDoubleSpinBox()
            self.duration_time.setRange(0, 9999)
            self.duration_time.setSuffix(" s")
            ModernInput.apply_style(self.duration_time)
            self.duration_time.valueChanged.connect(self.on_style_changed)

            time_grid.addWidget(QLabel(_ts("延时:")), 0, 0)
            time_grid.addWidget(self.delay_time, 0, 1)
            time_grid.addWidget(QLabel(_ts("间隔:")), 0, 2)
            time_grid.addWidget(self.interval_time, 0, 3)
            time_grid.addWidget(QLabel(_ts("持续:")), 1, 0)
            time_grid.addWidget(self.duration_time, 1, 1)
            timing_card.addLayout(time_grid)

            fade_layout = QHBoxLayout()
            self.fade_in = QDoubleSpinBox()
            self.fade_in.setRange(0, 10)
            self.fade_in.setSuffix(" s")
            ModernInput.apply_style(self.fade_in)
            self.fade_in.valueChanged.connect(self.on_style_changed)

            self.fade_out = QDoubleSpinBox()
            self.fade_out.setRange(0, 10)
            self.fade_out.setSuffix(" s")
            ModernInput.apply_style(self.fade_out)
            self.fade_out.valueChanged.connect(self.on_style_changed)

            fade_layout.addWidget(QLabel(_ts("淡入:")))
            fade_layout.addWidget(self.fade_in)
            fade_layout.addWidget(QLabel(_ts("淡出:")))
            fade_layout.addWidget(self.fade_out)
            timing_card.addWidget(create_param_row("淡入淡出:", fade_layout))

            opts_layout = QVBoxLayout()
            self.loop_display = QCheckBox(_ts("循环显示"))
            self.loop_display.stateChanged.connect(self.on_style_changed)
            opts_layout.addWidget(self.loop_display)
            timing_card.addLayout(opts_layout)

            layout.addWidget(timing_card)

            adv_card = ModernCard(_ts("高级选项"))
            self.bg_remove_check = QCheckBox(_ts("背景色消除 (绿幕/蓝幕)"))
            self.bg_remove_check.stateChanged.connect(self.on_style_changed)
            adv_card.addWidget(create_param_row("", self.bg_remove_check))

            bg_settings = QWidget()
            bg_layout = QVBoxLayout(bg_settings)
            bg_layout.setContentsMargins(0, 0, 0, 0)

            sim_layout = QHBoxLayout()
            self.bg_similarity = QDoubleSpinBox()
            self.bg_similarity.setRange(0, 1)
            self.bg_similarity.setSingleStep(0.01)
            self.bg_similarity.setValue(0.1)
            ModernInput.apply_style(self.bg_similarity)
            self.bg_similarity.valueChanged.connect(self.on_style_changed)

            self.bg_opacity = QDoubleSpinBox()
            self.bg_opacity.setRange(0, 1)
            self.bg_opacity.setSingleStep(0.01)
            self.bg_opacity.setValue(0.3)
            ModernInput.apply_style(self.bg_opacity)
            self.bg_opacity.valueChanged.connect(self.on_style_changed)

            sim_layout.addWidget(QLabel(_ts("相似度:")))
            sim_layout.addWidget(self.bg_similarity)
            sim_layout.addWidget(QLabel(_ts("混合度:")))
            sim_layout.addWidget(self.bg_opacity)
            bg_layout.addLayout(sim_layout)

            adv_card.addWidget(bg_settings)
            layout.addWidget(adv_card)
        else:
            layout.addWidget(effects_card)

            style_card = ModernCard(_ts("描边与阴影"))
            stroke_layout = QHBoxLayout()
            self.stroke_check = QCheckBox(_ts("启用描边"))
            self.stroke_check.stateChanged.connect(self.on_style_changed)
            self.stroke_width = QSpinBox()
            self.stroke_width.setRange(0, 20)
            ModernInput.apply_style(self.stroke_width)
            self.stroke_width.valueChanged.connect(self.on_style_changed)
            self.stroke_color_btn = QPushButton()
            self.stroke_color_btn.setFixedSize(30, 20)
            self.stroke_color = QColor(0, 0, 0)
            self.stroke_color_btn.setStyleSheet(
                f"background-color: {self.stroke_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;"
            )
            self.stroke_color_btn.clicked.connect(self.choose_stroke_color)
            stroke_layout.addWidget(self.stroke_check)
            stroke_layout.addWidget(QLabel(_ts("宽度:")))
            stroke_layout.addWidget(self.stroke_width)
            stroke_layout.addWidget(self.stroke_color_btn)
            style_card.addWidget(create_param_row("文字描边:", stroke_layout))

            shadow_layout = QHBoxLayout()
            self.shadow_check = QCheckBox(_ts("启用阴影"))
            self.shadow_check.stateChanged.connect(self.on_style_changed)
            self.shadow_blur = QSpinBox()
            self.shadow_blur.setRange(0, 50)
            ModernInput.apply_style(self.shadow_blur)
            self.shadow_blur.valueChanged.connect(self.on_style_changed)
            self.shadow_color_btn = QPushButton()
            self.shadow_color_btn.setFixedSize(30, 20)
            self.shadow_color = QColor(0, 0, 0, 128)
            self.shadow_color_btn.setStyleSheet(
                f"background-color: {self.shadow_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;"
            )
            self.shadow_color_btn.clicked.connect(self.choose_shadow_color)
            shadow_layout.addWidget(self.shadow_check)
            shadow_layout.addWidget(QLabel(_ts("模糊:")))
            shadow_layout.addWidget(self.shadow_blur)
            shadow_layout.addWidget(self.shadow_color_btn)
            style_card.addWidget(create_param_row("文字阴影:", shadow_layout))

            offset_layout = QHBoxLayout()
            self.shadow_x = QSpinBox()
            self.shadow_x.setRange(-50, 50)
            ModernInput.apply_style(self.shadow_x)
            self.shadow_x.valueChanged.connect(self.on_style_changed)
            self.shadow_y = QSpinBox()
            self.shadow_y.setRange(-50, 50)
            ModernInput.apply_style(self.shadow_y)
            self.shadow_y.valueChanged.connect(self.on_style_changed)
            offset_layout.addWidget(QLabel(_ts("偏移 X:")))
            offset_layout.addWidget(self.shadow_x)
            offset_layout.addWidget(QLabel("Y:"))
            offset_layout.addWidget(self.shadow_y)
            style_card.addWidget(create_param_row("阴影位置:", offset_layout))
            layout.addWidget(style_card)

            bg_card = ModernCard(_ts("文字背景"))
            bg_layout = QHBoxLayout()
            self.bg_check = QCheckBox(_ts("启用背景"))
            self.bg_check.stateChanged.connect(self.on_style_changed)
            self.bg_padding = QSpinBox()
            self.bg_padding.setRange(0, 50)
            ModernInput.apply_style(self.bg_padding)
            self.bg_padding.valueChanged.connect(self.on_style_changed)
            self.bg_radius = QSpinBox()
            self.bg_radius.setRange(0, 50)
            ModernInput.apply_style(self.bg_radius)
            self.bg_radius.valueChanged.connect(self.on_style_changed)
            self.text_bg_color_btn = QPushButton()
            self.text_bg_color_btn.setFixedSize(30, 20)
            self.text_bg_color = QColor(0, 0, 0, 128)
            self.text_bg_color_btn.setStyleSheet(
                f"background-color: {self.text_bg_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;"
            )
            self.text_bg_color_btn.clicked.connect(self.choose_text_bg_color)
            bg_layout.addWidget(self.bg_check)
            bg_layout.addWidget(self.text_bg_color_btn)
            bg_card.addWidget(create_param_row("背景设置:", bg_layout))
            pad_layout = QHBoxLayout()
            pad_layout.addWidget(QLabel(_ts("边距:")))
            pad_layout.addWidget(self.bg_padding)
            pad_layout.addWidget(QLabel(_ts("圆角:")))
            pad_layout.addWidget(self.bg_radius)
            bg_card.addWidget(create_param_row("背景样式:", pad_layout))
            layout.addWidget(bg_card)

            dyn_card = ModernCard(_ts("动态内容"))
            dyn_layout = QVBoxLayout()
            self.add_timestamp = QCheckBox(_ts("添加时间戳"))
            self.add_timestamp.stateChanged.connect(self.on_style_changed)
            dyn_layout.addWidget(self.add_timestamp)
            self.add_filename = QCheckBox(_ts("添加文件名"))
            self.add_filename.stateChanged.connect(self.on_style_changed)
            dyn_layout.addWidget(self.add_filename)
            self.add_frame = QCheckBox(_ts("添加帧编号"))
            self.add_frame.stateChanged.connect(self.on_style_changed)
            dyn_layout.addWidget(self.add_frame)
            dyn_card.addLayout(dyn_layout)
            layout.addWidget(dyn_card)

        self.load_advanced_settings()

    def load_advanced_settings(self):
        """加载高级设置"""
        style = self.watermark_config.get('style_config', {})
        watermark_type = self.watermark_config.get('type', 'image')
        
        # 通用效果
        effects = style.get('effects', {})
        if hasattr(self, 'rotation_angle'):
            angle = style.get('angle', effects.get('rotation', 0))
            self.rotation_angle.setValue(angle)
            
        if watermark_type == 'image':
            # 图片特有
            if hasattr(self, 'feather_value'):
                self.feather_value.setValue(effects.get('feather', 0))
            if hasattr(self, 'remove_black_edges'):
                self.remove_black_edges.setChecked(effects.get('remove_black_edges', False))
            if hasattr(self, 'circular_display'):
                self.circular_display.setChecked(effects.get('circular', False))
                
            timing = style.get('timing', {})
            if hasattr(self, 'delay_time'): self.delay_time.setValue(timing.get('delay', 0))
            if hasattr(self, 'interval_time'): self.interval_time.setValue(timing.get('interval', 0))
            if hasattr(self, 'duration_time'): self.duration_time.setValue(timing.get('duration', 5))
            if hasattr(self, 'loop_display'): self.loop_display.setChecked(timing.get('loop', False))
            
            fade = style.get('fade', {})
            if hasattr(self, 'fade_in'): self.fade_in.setValue(fade.get('fade_in', 0))
            if hasattr(self, 'fade_out'): self.fade_out.setValue(fade.get('fade_out', 0))
            
            bg = style.get('background_removal', {})
            if hasattr(self, 'bg_remove_check'): 
                self.bg_remove_check.setChecked(bool(bg)) # 简单判断
            if hasattr(self, 'bg_similarity'): self.bg_similarity.setValue(bg.get('similarity', 0.1))
            if hasattr(self, 'bg_opacity'): self.bg_opacity.setValue(bg.get('opacity', 0.3))
            
        else:
            # 文字特有
            stroke = style.get('stroke', {})
            if hasattr(self, 'stroke_check'): self.stroke_check.setChecked(stroke.get('enabled', False))
            if hasattr(self, 'stroke_width'): self.stroke_width.setValue(stroke.get('width', 0))
            if hasattr(self, 'stroke_color') and 'color' in stroke:
                self.stroke_color = QColor(stroke['color'])
                self.stroke_color_btn.setStyleSheet(f"background-color: {self.stroke_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
                
            shadow = style.get('shadow', {})
            if hasattr(self, 'shadow_check'): self.shadow_check.setChecked(shadow.get('enabled', False))
            if hasattr(self, 'shadow_blur'): self.shadow_blur.setValue(shadow.get('blur', 0))
            if hasattr(self, 'shadow_x'): self.shadow_x.setValue(shadow.get('x', 2))
            if hasattr(self, 'shadow_y'): self.shadow_y.setValue(shadow.get('y', 2))
            if hasattr(self, 'shadow_color') and 'color' in shadow:
                self.shadow_color = QColor(shadow['color'])
                self.shadow_color_btn.setStyleSheet(f"background-color: {self.shadow_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
                
            bg = style.get('background', {})
            if hasattr(self, 'bg_check'): self.bg_check.setChecked(bg.get('enabled', False))
            if hasattr(self, 'bg_padding'): self.bg_padding.setValue(bg.get('padding', 10))
            if hasattr(self, 'bg_radius'): self.bg_radius.setValue(bg.get('radius', 5))
            if hasattr(self, 'text_bg_color') and 'color' in bg:
                self.text_bg_color = QColor(bg['color'])
                self.text_bg_color_btn.setStyleSheet(f"background-color: {self.text_bg_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
                
            dyn = style.get('dynamic', {})
            if hasattr(self, 'add_timestamp'): self.add_timestamp.setChecked(dyn.get('timestamp', False))
            if hasattr(self, 'add_filename'): self.add_filename.setChecked(dyn.get('filename', False))
            if hasattr(self, 'add_frame'): self.add_frame.setChecked(dyn.get('frame_number', False))

    def choose_stroke_color(self):
        color = open_color_dialog(self.stroke_color, self)
        if color:
            self.stroke_color = color
            self.stroke_color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
            self.on_style_changed()

    def choose_shadow_color(self):
        color = open_color_dialog(self.shadow_color, self)
        if color:
            self.shadow_color = color
            self.shadow_color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
            self.on_style_changed()

    def choose_text_bg_color(self):
        color = open_color_dialog(self.text_bg_color, self)
        if color:
            self.text_bg_color = color
            self.text_bg_color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
            self.on_style_changed()

    def get_style_config(self) -> Dict[str, Any]:
        """获取样式配置（从新面板控件）"""
        watermark_type = self.watermark_config.get('type', 'image')
        config = {
            'effects': {},
            'timing': {},
            'fade': {},
            'background_removal': {},
            'stroke': {},
            'shadow': {},
            'background': {},
            'dynamic': {}
        }
        
        # 通用
        if hasattr(self, 'rotation_angle'):
            config['angle'] = self.rotation_angle.value()
            config['effects']['rotation'] = self.rotation_angle.value()
            
        if watermark_type == 'image':
            if hasattr(self, 'feather_value'): config['effects']['feather'] = self.feather_value.value()
            if hasattr(self, 'remove_black_edges'): config['effects']['remove_black_edges'] = self.remove_black_edges.isChecked()
            if hasattr(self, 'circular_display'): config['effects']['circular'] = self.circular_display.isChecked()
            
            if hasattr(self, 'delay_time'): config['timing']['delay'] = self.delay_time.value()
            if hasattr(self, 'interval_time'): config['timing']['interval'] = self.interval_time.value()
            if hasattr(self, 'duration_time'): config['timing']['duration'] = self.duration_time.value()
            if hasattr(self, 'loop_display'): config['timing']['loop'] = self.loop_display.isChecked()
            
            if hasattr(self, 'fade_in'): config['fade']['fade_in'] = self.fade_in.value()
            if hasattr(self, 'fade_out'): config['fade']['fade_out'] = self.fade_out.value()
            
            if hasattr(self, 'bg_remove_check') and self.bg_remove_check.isChecked():
                config['background_removal'] = {
                    'enabled': True,
                    'similarity': self.bg_similarity.value(),
                    'opacity': self.bg_opacity.value()
                }
                
        else:
            # 文字特有
            # 基础样式 (Font/Color) 已由 create_text_controls 处理并保存到 self.text_font/color
            if hasattr(self, 'text_edit'):
                config['content'] = self.text_edit.text()
            config['arrange'] = '水平'
            config['angle'] = 0
            # 计算有效字体大小：如果用户通过拖拽手柄缩放了文字水印，
            # 需要按缩放比例调整字体大小，使处理器/预览器输出与视觉一致
            effective_font_size = self.text_font.pixelSize()
            if (self.watermark_item
                    and isinstance(self.watermark_item, ResizableWatermarkItem)):
                orig_w, orig_h = self.original_watermark_size
                current_h = self.watermark_item.boundingRect().height()
                if orig_h > 0 and current_h > 0:
                    scale = current_h / orig_h
                    if abs(scale - 1.0) > 0.05:
                        effective_font_size = max(12, int(round(
                            effective_font_size * scale)))

            config['font'] = {
                'family': self.text_font.family(),
                'size': effective_font_size,
                'bold': self.text_font.bold(),
                'italic': self.text_font.italic()
            }
            
            # 持久化字体文件路径（若缓存中无，尝试实时查询）
            if hasattr(self, '_font_path_cache'):
                if self.text_font.family() in self._font_path_cache:
                    config['font']['path'] = self._font_path_cache[self.text_font.family()]
                else:
                    font_path = self._query_font_file_path(self.text_font.family())
                    if font_path:
                        self._font_path_cache[self.text_font.family()] = font_path
                        config['font']['path'] = font_path
            config['color'] = self.text_color.name()
            if hasattr(self, 'text_opacity_slider'):
                config['opacity'] = self.text_opacity_slider.value() / 100.0
            
            if hasattr(self, 'stroke_check'):
                config['stroke'] = {
                    'enabled': self.stroke_check.isChecked(),
                    'width': self.stroke_width.value(),
                    'color': self.stroke_color.name()
                }
                
            if hasattr(self, 'shadow_check'):
                config['shadow'] = {
                    'enabled': self.shadow_check.isChecked(),
                    'blur': self.shadow_blur.value(),
                    'x': self.shadow_x.value(),
                    'y': self.shadow_y.value(),
                    'color': self.shadow_color.name()
                }
                
            if hasattr(self, 'bg_check'):
                config['background'] = {
                    'enabled': self.bg_check.isChecked(),
                    'padding': self.bg_padding.value(),
                    'radius': self.bg_radius.value(),
                    'color': self.text_bg_color.name()
                }
                
            if hasattr(self, 'add_timestamp'):
                config['dynamic'] = {
                    'timestamp': self.add_timestamp.isChecked(),
                    'filename': self.add_filename.isChecked(),
                    'frame_number': self.add_frame.isChecked()
                }
                
        return config

    def load_video_background(self):
        """加载视频作为背景"""
        if self.video_path and os.path.exists(self.video_path):
            try:
                cap = cv2.VideoCapture(self.video_path)
                ret, frame = cap.read()
                cap.release()

                if ret:
                    self.video_frame = frame
                    self.video_height, self.video_width = frame.shape[:2]

                    # 使用较高的基准宽度，保证清晰度 (最大1920，或者视频原始宽度)
                    target_width = min(self.video_width, 1920)
                    # 如果视频特别小，至少保证有 800
                    target_width = max(target_width, 800)
                    
                    self.scale_factor = target_width / self.video_width
                    target_height = int(target_width * self.video_height / self.video_width)

                    self.scene.setSceneRect(0, 0, target_width, target_height)

                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = frame_rgb.shape
                    bytes_per_line = ch * w
                    q_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_image)

                    scaled_pixmap = pixmap.scaled(
                        target_width, target_height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )

                    bg_item = QGraphicsPixmapItem(scaled_pixmap)
                    bg_item.setZValue(-1)
                    self.scene.addItem(bg_item)
                    
                    # 立即适应视图
                    self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
                    return
            except Exception as e:
                print(f"加载视频失败: {e}")

        self.add_default_background()

    def resizeEvent(self, event):
        """窗口大小改变时，自动调整视频视图大小"""
        super().resizeEvent(event)
        if self.scene:
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def showEvent(self, event):
        """窗口显示时，自动调整视频视图大小"""
        super().showEvent(event)
        if self.scene:
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def add_default_background(self):
        """添加默认背景"""
        view_width = 800
        view_height = int(view_width * self.video_height / self.video_width)
        self.scale_factor = view_width / self.video_width

        self.scene.setSceneRect(0, 0, view_width, view_height)

        from PyQt6.QtWidgets import QGraphicsRectItem
        bg_rect = QGraphicsRectItem(0, 0, view_width, view_height)
        bg_rect.setBrush(QBrush(QColor(30, 30, 30)))
        bg_rect.setPen(QPen(Qt.PenStyle.NoPen))
        bg_rect.setZValue(-1)
        self.scene.addItem(bg_rect)

        grid_pen = QPen(QColor(60, 60, 60), 1, Qt.PenStyle.DotLine)
        for x in range(0, int(view_width), 100):
            self.scene.addLine(x, 0, x, view_height, grid_pen)
        for y in range(0, int(view_height), 100):
            self.scene.addLine(0, y, view_width, y, grid_pen)

        text = QGraphicsTextItem("视频预览区域\n(未选择视频)")
        text.setDefaultTextColor(QColor(150, 150, 150))
        text.setFont(QFont("Arial", 20))
        text.setPos(view_width / 2 - 100, view_height / 2 - 30)
        text.setOpacity(0.5)
        text.setZValue(-0.5)
        self.scene.addItem(text)
        
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def load_watermark(self):
        """加载水印（图片或文字）"""
        if self.watermark_item:
            self.scene.removeItem(self.watermark_item)
            self.watermark_item = None

        watermark_type = self.watermark_config.get('type', 'image')
        if watermark_type == 'image':
            self.load_image_watermark()
        else:
            self.load_text_watermark()

    def _normalize_image_candidates(self, candidates):
        normalized = []
        for path in candidates:
            if not path:
                continue
            abs_path = os.path.abspath(path)
            ext = os.path.splitext(abs_path)[1].lower()
            if os.path.exists(abs_path) and ext in _SUPPORTED_IMAGE_EXTS:
                normalized.append(abs_path)
        return normalized

    def _scan_image_folder(self, folder_path: str):
        if not folder_path or not os.path.isdir(folder_path):
            return []
        files = []
        try:
            for name in sorted(os.listdir(folder_path)):
                path = os.path.join(folder_path, name)
                if not os.path.isfile(path):
                    continue
                ext = os.path.splitext(path)[1].lower()
                if ext in _SUPPORTED_IMAGE_EXTS:
                    files.append(path)
        except Exception:
            return []
        return files

    def _resolve_image_source(self) -> str:
        file_path = (self.watermark_config.get('file_path') or '').strip()
        file_mode = self.watermark_config.get('file_mode', 'file')
        candidates = self.watermark_config.get('file_candidates') or []
        normalized_candidates = self._normalize_image_candidates(candidates)

        if file_path:
            abs_path = os.path.abspath(file_path)
            is_folder = os.path.isdir(abs_path)
            if is_folder or file_mode == 'folder':
                folder_path = abs_path if is_folder else ""
                folder_candidates = normalized_candidates
                if not folder_candidates and folder_path:
                    folder_candidates = self._scan_image_folder(folder_path)
                if not folder_candidates and file_mode == 'folder' and not is_folder:
                    parent_dir = os.path.dirname(abs_path)
                    folder_candidates = self._scan_image_folder(parent_dir)
                return folder_candidates[0] if folder_candidates else ""

            ext = os.path.splitext(abs_path)[1].lower()
            if os.path.isfile(abs_path) and ext in _SUPPORTED_IMAGE_EXTS:
                return abs_path

        if normalized_candidates:
            return normalized_candidates[0]
        return ""

    def _apply_saved_position_and_size(self, default_x: float, default_y: float):
        """应用已保存的位置和尺寸（如果有）"""
        if not self.watermark_item:
            return

        custom_pos = self.watermark_config.get('custom_position')
        if custom_pos and isinstance(custom_pos, (tuple, list)) and len(custom_pos) == 2:
            scene_x = custom_pos[0] * self.scale_factor
            scene_y = custom_pos[1] * self.scale_factor
            self.watermark_item.setPos(scene_x, scene_y)
        else:
            self.watermark_item.setPos(default_x, default_y)

        custom_w = self.watermark_config.get('custom_width')
        custom_h = self.watermark_config.get('custom_height')
        if isinstance(self.watermark_item, ResizableWatermarkItem) and custom_w and custom_h:
            scene_w = int(custom_w * self.scale_factor)
            scene_h = int(custom_h * self.scale_factor)
            self.watermark_item.resize_to(scene_w, scene_h)

    def load_image_watermark(self):
        """加载图片水印"""
        source_path = self._resolve_image_source()

        if source_path and os.path.exists(source_path):
            try:
                pixmap = QPixmap(source_path)
                if not pixmap.isNull():
                    max_size = 300
                    if pixmap.width() > max_size or pixmap.height() > max_size:
                        pixmap = pixmap.scaled(
                            max_size, max_size,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )

                    self.original_watermark_size = (pixmap.width(), pixmap.height())
                    self.watermark_item = ResizableWatermarkItem(pixmap)
                    self.watermark_item.setSelected(True)

                    scene_rect = self.scene.sceneRect()
                    default_x = scene_rect.width() - pixmap.width() - 20
                    default_y = 20
                    self._apply_saved_position_and_size(default_x, default_y)

                    self.scene.addItem(self.watermark_item)
                    return
            except Exception as e:
                print(f"加载水印图片失败: {e}")

        self.create_default_watermark()

    def apply_config_to_controls(self):
        """根据配置同步控件和水印显示状态"""
        if not self.watermark_item:
            return

        watermark_type = self.watermark_config.get('type', 'image')
        if watermark_type == 'image':
            if not isinstance(self.watermark_item, ResizableWatermarkItem):
                return

            opacity = self.watermark_config.get('opacity')
            if opacity is None:
                opacity = self.watermark_item.opacity()
            opacity = max(0.0, min(1.0, float(opacity)))
            self.watermark_item.setOpacity(opacity)
            if hasattr(self, 'opacity_slider'):
                self.opacity_slider.blockSignals(True)
                self.opacity_slider.setValue(int(opacity * 100))
                self.opacity_label.setText(f"{int(opacity * 100)}%")
                self.opacity_slider.blockSignals(False)

            custom_w = self.watermark_config.get('custom_width')
            custom_h = self.watermark_config.get('custom_height')
            orig_w, orig_h = self.original_watermark_size

            if custom_w and custom_h:
                scene_w = custom_w * self.scale_factor
                scene_h = custom_h * self.scale_factor
            else:
                scene_w = orig_w
                scene_h = orig_h

            if hasattr(self, 'width_spin') and hasattr(self, 'height_spin'):
                self.width_spin.blockSignals(True)
                self.height_spin.blockSignals(True)
                self.width_spin.setValue(int(max(1, scene_w)))
                self.height_spin.setValue(int(max(1, scene_h)))
                self.width_spin.blockSignals(False)
                self.height_spin.blockSignals(False)

            if hasattr(self, 'scale_slider') and orig_w > 0:
                scale = scene_w / max(1, orig_w)
                self.scale_slider.blockSignals(True)
                self.scale_slider.setValue(int(scale * 100))
                self.scale_label.setText(f"{int(scale * 100)}%")
                self.scale_slider.blockSignals(False)
        else:
            style_config = self.watermark_config.get('style_config', {})
            text_opacity = max(0.0, min(1.0, float(style_config.get('opacity', 1.0))))
            self.watermark_item.setOpacity(text_opacity)
            if hasattr(self, 'text_opacity_slider'):
                self.text_opacity_slider.blockSignals(True)
                self.text_opacity_slider.setValue(int(text_opacity * 100))
                self.text_opacity_label.setText(f"{int(text_opacity * 100)}%")
                self.text_opacity_slider.blockSignals(False)

            # 同步字体大小滑块和按钮文本
            font_size = self.text_font.pixelSize()
            if hasattr(self, 'font_size_slider'):
                self.font_size_slider.blockSignals(True)
                self.font_size_slider.setValue(min(font_size, self.font_size_slider.maximum()))
                self.font_size_label.setText(f"{font_size}px")
                self.font_size_slider.blockSignals(False)
            if hasattr(self, 'font_btn'):
                self.font_btn.setText(f"{self.text_font.family()} - {font_size}px")

    def load_text_watermark(self):
        """加载文字水印"""
        text = self.watermark_config.get('text_content', '水印文字')
        style = self.watermark_config.get('style_config', {})

        rendered_text = self._compose_text_content(text, style)
        pixmap = self._render_text_pixmap(rendered_text, style)
        if pixmap is None:
            return

        self.original_watermark_size = (pixmap.width(), pixmap.height())
        self.watermark_item = ResizableWatermarkItem(pixmap)
        self.watermark_item.setSelected(True)

        scene_rect = self.scene.sceneRect()
        default_x = scene_rect.width() - pixmap.width() - 20
        default_y = 20
        self._apply_saved_position_and_size(default_x, default_y)

        self.scene.addItem(self.watermark_item)

    def _compose_text_content(self, base_text: str, style: Dict[str, Any]) -> str:
        text = base_text or ""
        dynamic = style.get('dynamic', {})

        parts = [text] if text else []
        if dynamic.get('timestamp'):
            parts.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        if dynamic.get('filename') and self.video_path:
            parts.append(os.path.basename(self.video_path))
        if dynamic.get('frame_number'):
            parts.append("1")

        combined = " ".join(p for p in parts if p)
        arrange = normalize_text_arrange(style.get('arrange'))
        if arrange == 'vertical':
            combined = "\n".join(list(combined))
        return combined

    def _resolve_font_path(self, font_cfg: Dict[str, Any]) -> Optional[str]:
        family = font_cfg.get('family', 'Microsoft YaHei')
        fonts_dir = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
        candidates = []
        if 'YaHei' in family or '微软雅黑' in family:
            candidates.append(os.path.join(fonts_dir, "msyh.ttc"))
            candidates.append(os.path.join(fonts_dir, "msyhbd.ttc"))
        name = family.replace(" ", "")
        candidates.append(os.path.join(fonts_dir, f"{name}.ttf"))
        candidates.append(os.path.join(fonts_dir, f"{name}.ttc"))
        candidates.append(os.path.join(fonts_dir, "arial.ttf"))
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def _render_text_pixmap(self, text: str, style: Dict[str, Any]) -> Optional[QPixmap]:
        if not text.strip():
            return None

        font_cfg = style.get('font', {})
        font = QFont(font_cfg.get('family', 'Microsoft YaHei'))
        font.setPixelSize(int(font_cfg.get('size', 36)))
        font.setBold(bool(font_cfg.get('bold', False)))
        font.setItalic(bool(font_cfg.get('italic', False)))

        stroke_cfg = style.get('stroke', {})
        shadow_cfg = style.get('shadow', {})
        background_cfg = style.get('background', {})

        stroke_enabled = bool(stroke_cfg.get('enabled', False))
        shadow_enabled = bool(shadow_cfg.get('enabled', False))
        background_enabled = bool(background_cfg.get('enabled', False))

        stroke_width = int(stroke_cfg.get('width', 0)) if stroke_enabled else 0
        shadow_x = int(shadow_cfg.get('x', 0)) if shadow_enabled else 0
        shadow_y = int(shadow_cfg.get('y', 0)) if shadow_enabled else 0
        padding = int(background_cfg.get('padding', 8))
        radius = int(background_cfg.get('radius', 0))

        opacity = float(style.get('opacity', 1.0))
        text_color = QColor(style.get('color', '#FFFFFF'))
        text_color.setAlpha(int(255 * opacity))

        stroke_color = QColor(stroke_cfg.get('color', '#000000'))
        shadow_color = QColor(shadow_cfg.get('color', '#000000'))
        shadow_color.setAlpha(int(200 * opacity))

        bg_color = QColor(background_cfg.get('color', '#00000000'))
        bg_color.setAlpha(int(80 * opacity))

        lines = text.split("\n")
        metrics = QFontMetricsF(font)
        line_height = metrics.lineSpacing()
        text_w = 0
        for line in lines:
            text_w = max(text_w, metrics.horizontalAdvance(line))
        text_h = line_height * max(1, len(lines))
        
        # 增加额外边距以容纳下降部（descender）
        descent_margin = max(4, int(metrics.descent()))

        overlay_width = int(text_w + padding * 2 + abs(shadow_x) + stroke_width * 2)
        overlay_height = int(text_h + padding * 2 + abs(shadow_y) + stroke_width * 2 + descent_margin)

        image = QImage(overlay_width, overlay_height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setFont(font)

        if background_enabled and bg_color.alpha() > 0:
            rect = QRectF(0, 0, overlay_width, overlay_height)
            painter.setBrush(bg_color)
            painter.setPen(Qt.PenStyle.NoPen)
            if radius > 0:
                painter.drawRoundedRect(rect, radius, radius)
            else:
                painter.drawRect(rect)

        base_x = padding + stroke_width
        base_y = padding + stroke_width + metrics.ascent()

        def draw_path(offset_x: int, offset_y: int, color: QColor, stroke: bool):
            path = QPainterPath()
            y = base_y + offset_y
            for line in lines:
                path.addText(base_x + offset_x, y, font, line)
                y += line_height
            if stroke and stroke_width > 0:
                pen = QPen(color, stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
            else:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(color)
                painter.drawPath(path)

        if shadow_enabled and (shadow_x != 0 or shadow_y != 0):
            blur = int(shadow_cfg.get('blur', 0))
            if blur > 0:
                step = max(1, blur // 2)
                offsets = [
                    (-step, -step), (0, -step), (step, -step),
                    (-step, 0), (0, 0), (step, 0),
                    (-step, step), (0, step), (step, step)
                ]
                per_alpha = max(10, shadow_color.alpha() // len(offsets))
                for dx, dy in offsets:
                    tmp_color = QColor(shadow_color)
                    tmp_color.setAlpha(per_alpha)
                    draw_path(shadow_x + dx, shadow_y + dy, tmp_color, False)
            else:
                draw_path(shadow_x, shadow_y, shadow_color, False)

        if stroke_width > 0:
            draw_path(0, 0, stroke_color, True)

        draw_path(0, 0, text_color, False)
        painter.end()

        angle = style.get('angle', 0)
        if normalize_text_arrange(style.get('arrange')) == 'slanted' and not angle:
            angle = -15
        if angle:
            transform = QTransform()
            transform.rotate(angle)
            image = image.transformed(transform, Qt.TransformationMode.SmoothTransformation)

        return QPixmap.fromImage(image)

    def create_default_watermark(self):
        pixmap = QPixmap(200, 100)
        pixmap.fill(QColor(255, 0, 0, 100))

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 16))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "水印区域")
        painter.end()

        self.original_watermark_size = (pixmap.width(), pixmap.height())
        self.watermark_item = ResizableWatermarkItem(pixmap)
        self.watermark_item.setSelected(True)

        scene_rect = self.scene.sceneRect()
        default_x = scene_rect.width() - 220
        default_y = 20
        self.watermark_item.setPos(default_x, default_y)
        self.scene.addItem(self.watermark_item)

    def on_scale_changed(self, value: int):
        if not self.watermark_item or not isinstance(self.watermark_item, ResizableWatermarkItem):
            return
        scale = value / 100.0
        self.scale_label.setText(f"{value}%")
        self.watermark_item.scale_watermark(scale)
        self._sync_custom_size_from_item()
        if hasattr(self, 'width_spin'):
            orig_w, orig_h = self.original_watermark_size
            self.width_spin.blockSignals(True)
            self.height_spin.blockSignals(True)
            self.width_spin.setValue(int(orig_w * scale))
            self.height_spin.setValue(int(orig_h * scale))
            self.width_spin.blockSignals(False)
            self.height_spin.blockSignals(False)
        self.update_position_info()

    def on_size_changed(self):
        if not self.watermark_item or not isinstance(self.watermark_item, ResizableWatermarkItem):
            return
        w = self.width_spin.value()
        h = self.height_spin.value()
        orig_w, orig_h = self.original_watermark_size
        scale = w / orig_w if orig_w > 0 else 1.0
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(int(scale * 100))
        self.scale_label.setText(f"{int(scale * 100)}%")
        self.scale_slider.blockSignals(False)
        self.watermark_item.scale_watermark(scale)
        self._sync_custom_size_from_item()
        self.update_position_info()

    def on_opacity_changed(self, value: int):
        if self.watermark_item:
            opacity = value / 100.0
            self.opacity_label.setText(f"{value}%")
            self.watermark_item.setOpacity(opacity)
            self.watermark_config['opacity'] = opacity

    def _sync_custom_size_from_item(self):
        if not self.watermark_item or not isinstance(self.watermark_item, ResizableWatermarkItem):
            return
        rect = self.watermark_item.boundingRect()
        scene_w = rect.width()
        scene_h = rect.height()
        self.watermark_config['custom_width'] = int(scene_w / self.scale_factor)
        self.watermark_config['custom_height'] = int(scene_h / self.scale_factor)

    def on_text_changed(self, text: str):
        if not self.watermark_item:
            return
        if isinstance(self.watermark_item, ResizableTextItem):
            self.watermark_item.setPlainText(text)
            self.update_position_info()
        else:
            self.sync_style_to_preview()

    def on_font_size_changed(self, value: int):
        self.font_size_label.setText(f"{value}px")
        self.text_font.setPixelSize(value)
        if not self.watermark_item:
            return
        if isinstance(self.watermark_item, ResizableTextItem):
            self.watermark_item.setFont(self.text_font)
            self.update_position_info()
        else:
            self.sync_style_to_preview()

    def on_text_opacity_changed(self, value: int):
        if self.watermark_item:
            opacity = value / 100.0
            self.text_opacity_label.setText(f"{value}%")
            self.watermark_item.setOpacity(opacity)

    def choose_font(self):
        font, ok = QFontDialog.getFont(self.text_font, self)
        if ok:
            # QFontDialog 返回点(pt)大小，转为像素(px)以匹配 FFmpeg/PIL
            pt_size = font.pointSize()
            self.text_font = font
            if pt_size > 0:
                px_size = max(12, int(round(pt_size * 96.0 / 72.0)))
                self.text_font.setPixelSize(px_size)
            self.font_btn.setText(f"{font.family()} - {self.text_font.pixelSize()}px")
            
            # 查询字体文件路径
            font_path = self._query_font_file_path(font.family())
            if font_path:
                if not hasattr(self, '_font_path_cache'):
                    self._font_path_cache = {}
                self._font_path_cache[font.family()] = font_path
            
            if hasattr(self, 'font_size_slider'):
                self.font_size_slider.blockSignals(True)
                self.font_size_slider.setValue(min(self.text_font.pixelSize(),
                                                   self.font_size_slider.maximum()))
                self.font_size_label.setText(f"{self.text_font.pixelSize()}px")
                self.font_size_slider.blockSignals(False)
            if not self.watermark_item:
                return
            if isinstance(self.watermark_item, ResizableTextItem):
                self.watermark_item.setFont(self.text_font)
                self.update_position_info()
            else:
                self.sync_style_to_preview()
    
    def _query_font_file_path(self, family_name: str) -> Optional[str]:
        """从 Windows 注册表查询字体文件路径"""
        try:
            import winreg
        except ImportError:
            return None
        
        normalized = family_name.strip().lower().replace(" ", "")
        fonts_dir = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"
        
        for root_key in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                key = winreg.OpenKey(root_key, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")
                idx = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, idx)
                        idx += 1
                        
                        display_name = name
                        for suffix in [" (TrueType)", " (OpenType)", " (TTC)", " (OTF)"]:
                            display_name = display_name.replace(suffix, "")
                        
                        norm_display = display_name.strip().lower().replace(" ", "")
                        if normalized in norm_display or norm_display in normalized:
                            if os.path.isabs(value):
                                font_path = value
                            else:
                                font_path = str(fonts_dir / value)
                            
                            if os.path.isfile(font_path):
                                winreg.CloseKey(key)
                                return font_path
                    except OSError:
                        break
                winreg.CloseKey(key)
            except Exception:
                continue
        
        return None

    def choose_color(self):
        color = open_color_dialog(self.text_color, self)
        if color:
            self.text_color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
            if not self.watermark_item:
                return
            if isinstance(self.watermark_item, ResizableTextItem):
                self.watermark_item.setDefaultTextColor(color)
            else:
                self.sync_style_to_preview()

    def update_position_info(self):
        if not self.watermark_item:
            return
        pos = self.watermark_item.pos()
        rect = self.watermark_item.boundingRect()
        actual_x = int(pos.x() / self.scale_factor)
        actual_y = int(pos.y() / self.scale_factor)
        actual_w = int(rect.width() / self.scale_factor)
        actual_h = int(rect.height() / self.scale_factor)
        self.position_info.setText(
            _ts(
                f"位置: X={actual_x}px, Y={actual_y}px | "
                f"尺寸: {actual_w}×{actual_h}px | "
                f"视频: {self.video_width}×{self.video_height}px"
            )
        )

    def set_preset_position(self, position: str):
        if not self.watermark_item:
            return
        rect = self.watermark_item.boundingRect()
        w = rect.width()
        h = rect.height()
        scene_w = self.scene.width()
        scene_h = self.scene.height()
        margin = 20
        if position == "tl":
            x, y = margin, margin
        elif position == "t":
            x, y = (scene_w - w) / 2, margin
        elif position == "tr":
            x, y = scene_w - w - margin, margin
        elif position == "l":
            x, y = margin, (scene_h - h) / 2
        elif position == "center":
            x, y = (scene_w - w) / 2, (scene_h - h) / 2
        elif position == "r":
            x, y = scene_w - w - margin, (scene_h - h) / 2
        elif position == "bl":
            x, y = margin, scene_h - h - margin
        elif position == "b":
            x, y = (scene_w - w) / 2, scene_h - h - margin
        elif position == "br":
            x, y = scene_w - w - margin, scene_h - h - margin
        else:
            x, y = margin, margin
        self.watermark_item.setPos(x, y)
        self.update_position_info()

    def reset_watermark(self):
        self.set_preset_position("tr")
        if hasattr(self, 'scale_slider'):
            self.scale_slider.setValue(100)
        if hasattr(self, 'opacity_slider'):
            self.opacity_slider.setValue(90)
        if hasattr(self, 'text_opacity_slider'):
            self.text_opacity_slider.setValue(100)

    def accept_position(self):
        if not self.watermark_item:
            self.reject()
            return
        pos = self.watermark_item.pos()
        rect = self.watermark_item.boundingRect()
        actual_x = int(pos.x() / self.scale_factor)
        actual_y = int(pos.y() / self.scale_factor)
        actual_w = int(rect.width() / self.scale_factor)
        actual_h = int(rect.height() / self.scale_factor)
        self.position_selected.emit(actual_x, actual_y, actual_w, actual_h)
        self.accept()

    def get_position(self) -> Tuple[int, int, int, int]:
        if not self.watermark_item:
            return 0, 0, 200, 100
        pos = self.watermark_item.pos()
        rect = self.watermark_item.boundingRect()
        actual_x = int(pos.x() / self.scale_factor)
        actual_y = int(pos.y() / self.scale_factor)
        actual_w = int(rect.width() / self.scale_factor)
        actual_h = int(rect.height() / self.scale_factor)
        return actual_x, actual_y, actual_w, actual_h

    def get_text_style(self) -> dict:
        if self.watermark_config.get('type') != 'text':
            return {}
        return {
            'font_family': self.text_font.family(),
            'font_size': self.text_font.pixelSize(),
            'font_bold': self.text_font.bold(),
            'font_italic': self.text_font.italic(),
            'color': self.text_color.name(),
            'opacity': self.text_opacity_slider.value() / 100.0 if hasattr(self, 'text_opacity_slider') else 1.0
        }

    def sync_style_to_preview(self):
        config = self.get_style_config()
        if self.watermark_config.get('type') == 'text':
            self.watermark_config['style_config'] = config
            if 'content' in config:
                self.watermark_config['text_content'] = config['content']
            if 'font' in config:
                font_info = config['font']
                self.text_font = QFont(font_info.get('family', 'Arial'))
                self.text_font.setPixelSize(int(font_info.get('size', 36)))
                self.text_font.setBold(font_info.get('bold', False))
                self.text_font.setItalic(font_info.get('italic', False))
            if 'color' in config:
                self.text_color = QColor(config['color'])
        else:
            self.watermark_config['style_config'] = config

        if self.watermark_item:
            pos = self.watermark_item.pos()
            rect = self.watermark_item.boundingRect()
            self.watermark_config['custom_position'] = (
                int(pos.x() / self.scale_factor),
                int(pos.y() / self.scale_factor)
            )
            if self.watermark_config.get('type') == 'text':
                # 文字水印：get_style_config 已将视觉缩放换算到 font_size 中，
                # 清除 custom 尺寸，让 load_watermark 以新字号自然渲染
                self.watermark_config.pop('custom_width', None)
                self.watermark_config.pop('custom_height', None)
            elif isinstance(self.watermark_item, ResizableWatermarkItem):
                self.watermark_config['custom_width'] = int(rect.width() / self.scale_factor)
                self.watermark_config['custom_height'] = int(rect.height() / self.scale_factor)

        self.load_watermark()
        self.apply_config_to_controls()

    def on_style_changed(self):
        self.sync_style_to_preview()
