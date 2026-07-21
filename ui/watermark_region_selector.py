"""
水印区域选择器 - 可视化选择水印区域
"""
import cv2
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QMouseEvent, QBrush
from ui.components import load_svg_icon, ModernButton
from ui.theme import Theme
from ui.i18n import t


class VideoFrameLabel(QLabel):
    """可以绘制矩形选区的Label"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_point = QPoint()  # 初始化为空点
        self.end_point = QPoint()    # 初始化为空点
        self.current_rect = None
        self.is_drawing = False
        self.is_resizing = False
        self.is_moving = False
        self.resize_corner = None
        self.move_start_pos = QPoint()  # 初始化为空点
        self.pixmap_offset_x = 0
        self.pixmap_offset_y = 0
        self.pixmap_width = 0
        self.pixmap_height = 0
        self.corner_size = 15
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet(f"QLabel {{ border: 2px solid {Theme.Border}; background-color: #000; }}")
    
    def _pixmap_rect(self) -> QRect:
        return QRect(
            self.pixmap_offset_x,
            self.pixmap_offset_y,
            self.pixmap_width,
            self.pixmap_height
        )
    
    def _clamp_point_to_pixmap(self, pos: QPoint) -> QPoint:
        rect = self._pixmap_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return pos
        x = max(rect.left(), min(pos.x(), rect.right()))
        y = max(rect.top(), min(pos.y(), rect.bottom()))
        return QPoint(x, y)
    
    def _clamp_rect_to_pixmap(self, rect: QRect) -> QRect:
        pix_rect = self._pixmap_rect()
        if pix_rect.width() <= 0 or pix_rect.height() <= 0:
            return rect
        
        if rect.width() > pix_rect.width():
            rect.setWidth(pix_rect.width())
        if rect.height() > pix_rect.height():
            rect.setHeight(pix_rect.height())
        
        if rect.left() < pix_rect.left():
            rect.moveLeft(pix_rect.left())
        if rect.top() < pix_rect.top():
            rect.moveTop(pix_rect.top())
        if rect.right() > pix_rect.right():
            rect.moveRight(pix_rect.right())
        if rect.bottom() > pix_rect.bottom():
            rect.moveBottom(pix_rect.bottom())
        return rect
    
    def set_initial_rect(self, rect: tuple, frame_size: tuple, pixmap_size: tuple):
        """设置初始矩形区域 (x, y, w, h)"""
        if rect and rect[2] > 0 and rect[3] > 0:
            frame_w, frame_h = frame_size
            pixmap_w, pixmap_h = pixmap_size
            
            scale_x = pixmap_w / frame_w
            scale_y = pixmap_h / frame_h
            
            x, y, w, h = rect
            x = int(x * scale_x) + self.pixmap_offset_x
            y = int(y * scale_y) + self.pixmap_offset_y
            w = int(w * scale_x)
            h = int(h * scale_y)
            
            start = self._clamp_point_to_pixmap(QPoint(x, y))
            end = self._clamp_point_to_pixmap(QPoint(x + w, y + h))
            self.start_point = start
            self.end_point = end
            self.update()
    
    def get_corner_at_pos(self, pos: QPoint):
        """检测鼠标是否在矩形的二二角或边中点上"""
        if self.start_point.isNull() or self.end_point.isNull():
            return None
        
        rect = QRect(self.start_point, self.end_point).normalized()
        corner_size = 12
        
        # 检测四个角
        if (abs(pos.x() - rect.left()) < corner_size and 
            abs(pos.y() - rect.top()) < corner_size):
            return 'top_left'
        elif (abs(pos.x() - rect.right()) < corner_size and 
              abs(pos.y() - rect.top()) < corner_size):
            return 'top_right'
        elif (abs(pos.x() - rect.left()) < corner_size and 
              abs(pos.y() - rect.bottom()) < corner_size):
            return 'bottom_left'
        elif (abs(pos.x() - rect.right()) < corner_size and 
              abs(pos.y() - rect.bottom()) < corner_size):
            return 'bottom_right'
        
        # 检测四条边的中点
        # 上边中点
        elif (abs(pos.x() - (rect.left() + rect.right()) // 2) < corner_size and
              abs(pos.y() - rect.top()) < corner_size):
            return 'top_mid'
        # 下边中点
        elif (abs(pos.x() - (rect.left() + rect.right()) // 2) < corner_size and
              abs(pos.y() - rect.bottom()) < corner_size):
            return 'bottom_mid'
        # 左边中点
        elif (abs(pos.x() - rect.left()) < corner_size and
              abs(pos.y() - (rect.top() + rect.bottom()) // 2) < corner_size):
            return 'left_mid'
        # 右边中点
        elif (abs(pos.x() - rect.right()) < corner_size and
              abs(pos.y() - (rect.top() + rect.bottom()) // 2) < corner_size):
            return 'right_mid'
        
        return None
    
    def is_inside_rect(self, pos: QPoint) -> bool:
        """检测鼠标是否在矩形内部"""
        if self.start_point.isNull() or self.end_point.isNull():
            return False
        
        rect = QRect(self.start_point, self.end_point).normalized()
        return rect.contains(pos)
    
    def keyPressEvent(self, ev):
        """键盘事件 - 支持方向键微调"""
        if self.start_point.isNull() or self.end_point.isNull():
            return
        
        step = 1
        from PyQt6.QtCore import Qt as QtCore
        
        dx, dy = 0, 0
        if ev.key() == QtCore.Key.Key_Left:
            dx = -step
        elif ev.key() == QtCore.Key.Key_Right:
            dx = step
        elif ev.key() == QtCore.Key.Key_Up:
            dy = -step
        elif ev.key() == QtCore.Key.Key_Down:
            dy = step
        else:
            super().keyPressEvent(ev)
            return
        
        self.start_point = QPoint(self.start_point.x() + dx, self.start_point.y() + dy)
        self.end_point = QPoint(self.end_point.x() + dx, self.end_point.y() + dy)
        self.update()
    
    def mousePressEvent(self, ev: QMouseEvent):
        """鼠标按下事件"""
        if ev.button() == Qt.MouseButton.LeftButton:
            corner = self.get_corner_at_pos(ev.pos())
            if corner:
                self.is_resizing = True
                self.resize_corner = corner
            elif self.is_inside_rect(ev.pos()):
                self.is_moving = True
                self.move_start_pos = ev.pos()
            else:
                pos = self._clamp_point_to_pixmap(ev.pos())
                self.start_point = pos
                self.end_point = pos
                self.is_drawing = True
            self.update()
    
    def mouseMoveEvent(self, ev: QMouseEvent):
        """鼠标移动事件"""
        corner = self.get_corner_at_pos(ev.pos())
        if corner:
            if corner in ['top_left', 'bottom_right']:
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif corner in ['top_right', 'bottom_left']:
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif corner in ['top_mid', 'bottom_mid']:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif corner in ['left_mid', 'right_mid']:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif self.is_inside_rect(ev.pos()):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)
        
        if self.is_drawing:
            self.end_point = self._clamp_point_to_pixmap(ev.pos())
            self.update()
        elif self.is_resizing and self.resize_corner:
            rect = QRect(self.start_point, self.end_point).normalized()
            
            if self.resize_corner == 'top_left':
                self.start_point = self._clamp_point_to_pixmap(QPoint(ev.pos().x(), ev.pos().y()))
            elif self.resize_corner == 'top_right':
                self.start_point = self._clamp_point_to_pixmap(QPoint(rect.left(), ev.pos().y()))
                self.end_point = self._clamp_point_to_pixmap(QPoint(ev.pos().x(), rect.bottom()))
            elif self.resize_corner == 'bottom_left':
                self.start_point = self._clamp_point_to_pixmap(QPoint(ev.pos().x(), rect.top()))
                self.end_point = self._clamp_point_to_pixmap(QPoint(rect.right(), ev.pos().y()))
            elif self.resize_corner == 'bottom_right':
                self.end_point = self._clamp_point_to_pixmap(ev.pos())
            elif self.resize_corner == 'top_mid':
                self.start_point = self._clamp_point_to_pixmap(QPoint(rect.left(), ev.pos().y()))
            elif self.resize_corner == 'bottom_mid':
                self.end_point = self._clamp_point_to_pixmap(QPoint(rect.right(), ev.pos().y()))
            elif self.resize_corner == 'left_mid':
                self.start_point = self._clamp_point_to_pixmap(QPoint(ev.pos().x(), rect.top()))
            elif self.resize_corner == 'right_mid':
                self.end_point = self._clamp_point_to_pixmap(QPoint(ev.pos().x(), rect.bottom()))
            
            self.update()
        elif self.is_moving and not self.move_start_pos.isNull():
            dx = ev.pos().x() - self.move_start_pos.x()
            dy = ev.pos().y() - self.move_start_pos.y()
            
            rect = QRect(self.start_point, self.end_point).normalized()
            rect.translate(dx, dy)
            rect = self._clamp_rect_to_pixmap(rect)
            self.start_point = rect.topLeft()
            self.end_point = rect.bottomRight()
            self.move_start_pos = ev.pos()
            self.update()
    
    def mouseReleaseEvent(self, ev: QMouseEvent):
        """鼠标释放事件"""
        if ev.button() == Qt.MouseButton.LeftButton:
            if self.is_drawing:
                self.is_drawing = False
                self.end_point = ev.pos()
            elif self.is_resizing:
                self.is_resizing = False
                self.resize_corner = None
            elif self.is_moving:
                self.is_moving = False
                self.move_start_pos = QPoint()  # 重置为空点
            self.update()
    
    def paintEvent(self, event):
        """绘制事件"""
        super().paintEvent(event)
        
        if not self.start_point.isNull() and not self.end_point.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # 绘制选框边框和半透明填充
            pen = QPen(QColor(Theme.Primary), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            primary_color = QColor(Theme.Primary)
            primary_color.setAlpha(50)
            painter.setBrush(primary_color)
            
            rect = QRect(self.start_point, self.end_point).normalized()
            painter.drawRect(rect)
            
            # 绘制圆形手柄
            handle_radius = 6
            painter.setBrush(QBrush(QColor(Theme.Surface)))
            painter.setPen(QPen(QColor(Theme.Primary), 2))
            
            # 绘制四个角的圆形手柄
            painter.drawEllipse(QPoint(rect.left(), rect.top()), handle_radius, handle_radius)
            painter.drawEllipse(QPoint(rect.right(), rect.top()), handle_radius, handle_radius)
            painter.drawEllipse(QPoint(rect.left(), rect.bottom()), handle_radius, handle_radius)
            painter.drawEllipse(QPoint(rect.right(), rect.bottom()), handle_radius, handle_radius)
            
            # 绘制四条边中点的圆形手柄
            painter.drawEllipse(QPoint((rect.left() + rect.right()) // 2, rect.top()), handle_radius, handle_radius)
            painter.drawEllipse(QPoint((rect.left() + rect.right()) // 2, rect.bottom()), handle_radius, handle_radius)
            painter.drawEllipse(QPoint(rect.left(), (rect.top() + rect.bottom()) // 2), handle_radius, handle_radius)
            painter.drawEllipse(QPoint(rect.right(), (rect.top() + rect.bottom()) // 2), handle_radius, handle_radius)
    
    def get_rect(self) -> tuple:
        """获取选中的矩形区域"""
        if self.start_point.isNull() or self.end_point.isNull():
            return (0, 0, 0, 0)
        
        rect = QRect(self.start_point, self.end_point).normalized()
        return (rect.x(), rect.y(), rect.width(), rect.height())


class WatermarkRegionSelector(QDialog):
    """水印区域选择对话框"""
    
    def __init__(self, video_path: str, initial_rect: tuple = None, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.initial_rect = initial_rect or (0, 0, 0, 0)
        self.cap = None
        self.current_frame = None
        self.total_frames = 0
        self.fps = 30
        self.current_frame_index = 0
        
        self.setWindowTitle(t("watermark_region_selector.title", "选择水印区域"))
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(f"QDialog {{ background-color: {Theme.Background}; }}")
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.init_ui()
        self.load_video()
        self.show_frame(0)
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        tip_label = QLabel(t("watermark_region_selector.tip", "使用鼠标拖动选择水印区域，拖动进度条切换帧"))
        tip_label.setStyleSheet(
            f"QLabel {{ "
            f"font-size: 14px; "
            f"font-weight: 600; "
            f"color: {Theme.Primary}; "
            f"padding: 12px; "
            f"background-color: {Theme.PrimaryLight}; "
            f"border-radius: 8px; "
            f"}}"
        )
        layout.addWidget(tip_label)
        
        self.frame_label = VideoFrameLabel()
        self.frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.frame_label.setMinimumSize(240, 180)
        layout.addWidget(self.frame_label, 1)
        
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)
        
        self.frame_info_label = QLabel(t("watermark_region_selector.time.initial", "时间: 00:00 / 00:00"))
        self.frame_info_label.setStyleSheet(f"QLabel {{ font-size: 13px; font-weight: 600; color: {Theme.TextPrimary}; }}")
        self.frame_info_label.setMinimumWidth(150)
        progress_layout.addWidget(self.frame_info_label)
        
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(0)
        self.frame_slider.setValue(0)
        self.frame_slider.setStyleSheet(
            f"QSlider::groove:horizontal {{ "
            f"border: 1px solid {Theme.Border}; "
            f"height: 8px; "
            f"background: {Theme.Background}; "
            f"border-radius: 4px; "
            f"}} "
            f"QSlider::handle:horizontal {{ "
            f"background: {Theme.Primary}; "
            f"border: 2px solid {Theme.PrimaryHover}; "
            f"width: 18px; "
            f"height: 18px; "
            f"margin: -6px 0; "
            f"border-radius: 9px; "
            f"}}"
        )
        self.frame_slider.valueChanged.connect(self.on_slider_changed)
        progress_layout.addWidget(self.frame_slider, 1)
        
        layout.addLayout(progress_layout)
        
        coord_layout = QHBoxLayout()
        coord_layout.setSpacing(15)
        
        self.coord_label = QLabel(t("watermark_region_selector.coord.initial", "当前选区: X=0, Y=0, 宽度=0, 高度=0"))
        self.coord_label.setStyleSheet(
            f"QLabel {{ "
            f"font-size: 13px; "
            f"padding: 10px; "
            f"color: {Theme.TextSecondary}; "
            f"background-color: {Theme.Surface}; "
            f"border: 1px solid {Theme.Border}; "
            f"border-radius: 6px; "
            f"}}"
        )
        coord_layout.addWidget(self.coord_label, 1)
        
        layout.addLayout(coord_layout)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        reset_btn = ModernButton(t("watermark_region_selector.btn.reset", "重置选区"), style=ModernButton.Style.Secondary, icon_name="refresh")
        reset_btn.setMinimumWidth(120)
        reset_btn.clicked.connect(self.reset_selection)
        button_layout.addWidget(reset_btn)
        
        cancel_btn = ModernButton(t("common.btn.cancel", "取消"), style=ModernButton.Style.Outline, icon_name="cross")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = ModernButton(t("common.btn.ok", "确定"), style=ModernButton.Style.Primary, icon_name="check")
        confirm_btn.setMinimumWidth(120)
        confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_coord_display)
        self.update_timer.start(100)
    
    def _format_time(self, seconds: float) -> str:
        """将秒数转换为 MM:SS 格式"""
        mins = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{mins:02d}:{secs:02d}"
    
    def load_video(self):
        """加载视频"""
        if not os.path.exists(self.video_path):
            QMessageBox.critical(
                self,
                t("common.error", "错误"),
                t("watermark_region_selector.error.file_not_found", "视频文件不存在"),
            )
            self.reject()
            return
        
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QMessageBox.critical(
                self,
                t("common.error", "错误"),
                t("watermark_region_selector.error.open_failed", "无法打开视频文件"),
            )
            self.reject()
            return
        
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps == 0:
            self.fps = 30
        
        self.frame_slider.setMaximum(max(0, self.total_frames - 1))
        
        total_seconds = self.total_frames / self.fps
        self.frame_info_label.setText(
            t("watermark_region_selector.time.initial_with_total", "时间: 00:00 / {total}").format(
                total=self._format_time(total_seconds)
            )
        )
    
    def show_frame(self, frame_index: int):
        """显示指定帧"""
        if not self.cap:
            return
        
        self.current_frame_index = frame_index
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.cap.read()
        
        if not ret:
            return
        
        self.current_frame = frame
        frame_h, frame_w = frame.shape[:2]
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * frame_w
        qt_image = QImage(frame_rgb.data, frame_w, frame_h, bytes_per_line, QImage.Format.Format_RGB888)
        
        available_width = self.frame_label.width()
        available_height = self.frame_label.height()
        if available_width <= 0 or available_height <= 0:
            available_width = 800
            available_height = 600
        
        scale_w = available_width / frame_w
        scale_h = available_height / frame_h
        scale = min(scale_w, scale_h)
        
        display_width = int(frame_w * scale)
        display_height = int(frame_h * scale)
        
        offset_x = max(0, int((available_width - display_width) / 2))
        offset_y = max(0, int((available_height - display_height) / 2))
        
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            display_width,
            display_height,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.frame_label.pixmap_offset_x = offset_x
        self.frame_label.pixmap_offset_y = offset_y
        self.frame_label.pixmap_width = display_width
        self.frame_label.pixmap_height = display_height
        
        self.frame_label.setPixmap(scaled_pixmap)
        
        if frame_index == 0 and self.initial_rect:
            self.frame_label.set_initial_rect(
                self.initial_rect,
                (frame_w, frame_h),
                (display_width, display_height)
            )
        
        current_seconds = frame_index / self.fps
        total_seconds = self.total_frames / self.fps
        self.frame_info_label.setText(
            t("watermark_region_selector.time.current", "时间: {current} / {total}").format(
                current=self._format_time(current_seconds),
                total=self._format_time(total_seconds),
            )
        )
    
    def on_slider_changed(self, value: int):
        """进度条改变"""
        self.show_frame(value)
    
    def update_coord_display(self):
        """更新坐标显示"""
        x, y, w, h = self.get_region()
        self.coord_label.setText(
            t(
                "watermark_region_selector.coord.current",
                "当前选区 (原始视频坐标): X={x}, Y={y}, 宽度={w}, 高度={h}",
            ).format(x=x, y=y, w=w, h=h)
        )
    
    def reset_selection(self):
        """重置选区"""
        self.frame_label.start_point = QPoint()
        self.frame_label.end_point = QPoint()
        self.frame_label.update()
    
    def get_region(self) -> tuple:
        """获取选中的区域 (原始视频坐标 x, y, w, h)"""
        display_x, display_y, display_w, display_h = self.frame_label.get_rect()
        
        if display_w == 0 or display_h == 0:
            return self.initial_rect
        
        if self.current_frame is None:
            return self.initial_rect
        
        frame_h, frame_w = self.current_frame.shape[:2]
        
        display_width = self.frame_label.pixmap_width
        display_height = self.frame_label.pixmap_height
        offset_x = self.frame_label.pixmap_offset_x
        offset_y = self.frame_label.pixmap_offset_y
        
        if display_width == 0 or display_height == 0:
            return self.initial_rect
        
        adj_x = max(0, min(display_x - offset_x, display_width))
        adj_y = max(0, min(display_y - offset_y, display_height))
        adj_w = max(0, min(display_w, display_width - adj_x))
        adj_h = max(0, min(display_h, display_height - adj_y))
        
        scale_x = frame_w / display_width
        scale_y = frame_h / display_height
        
        video_x = int(adj_x * scale_x)
        video_y = int(adj_y * scale_y)
        video_w = int(adj_w * scale_x)
        video_h = int(adj_h * scale_y)
        
        video_x = max(0, min(video_x, frame_w - 1))
        video_y = max(0, min(video_y, frame_h - 1))
        video_w = min(video_w, frame_w - video_x)
        video_h = min(video_h, frame_h - video_y)
        
        return (video_x, video_y, video_w, video_h)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.cap:
            self.show_frame(self.current_frame_index)
    
    def showEvent(self, event):
        super().showEvent(event)
        if self.cap:
            self.show_frame(self.current_frame_index)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.cap:
            self.cap.release()
        super().closeEvent(event)
