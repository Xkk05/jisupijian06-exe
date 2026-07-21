"""
裁切区域选取对话框
支持可拖拽的裁切框，实时显示边距和裁切后分辨率
"""
import cv2
import numpy as np
from typing import Optional, Callable, Dict
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QImage, QPixmap, QMouseEvent, QBrush
from ui.components import ModernButton
from ui.theme import Theme
from ui.i18n import t


class CropFrame:
    """裁切框模型"""
    def __init__(self, video_width: int, video_height: int, 
                 top: int = 0, bottom: int = 0, left: int = 0, right: int = 0):
        self.video_width = video_width
        self.video_height = video_height
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
    
    def get_crop_rect(self) -> QRect:
        """获取裁切矩形区域（相对于视频尺寸）"""
        x = self.left
        y = self.top
        w = self.video_width - self.left - self.right
        h = self.video_height - self.top - self.bottom
        return QRect(x, y, w, h)
    
    def get_cropped_size(self) -> tuple:
        """获取裁切后的分辨率"""
        w = self.video_width - self.left - self.right
        h = self.video_height - self.top - self.bottom
        return (max(1, w), max(1, h))


class CropVideoWidget(QWidget):
    """视频预览与裁切框交互组件"""
    margins_changed = pyqtSignal(dict)  # 边距变化信号
    
    def __init__(self, video_path: str, initial_margins: dict, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.video_frame = None
        self.video_width = 0
        self.video_height = 0
        self.scale_factor = 1.0
        
        # 裁切框模型
        self.crop_frame = None
        
        # 交互状态
        self.dragging = False
        self.drag_type = None  # 'top', 'bottom', 'left', 'right', 'topleft', 'topright', 'bottomleft', 'bottomright', 'move'
        self.drag_start_pos = None
        self.drag_start_margins = None
        
        # 边距拖拽检测阈值（像素）
        self.edge_threshold = 10
        
        # 加载视频首帧
        self._load_video_frame(initial_margins)
        
        # 启用鼠标跟踪
        self.setMouseTracking(True)
        self.setMinimumSize(640, 480)
    
    def _load_video_frame(self, initial_margins: dict):
        """加载视频首帧"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                raise Exception(t("crop_region_selector.error.read_frame_failed", "无法读取视频帧"))
            
            # 转换BGR到RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.video_frame = frame
            self.video_height, self.video_width = frame.shape[:2]
            
            # 初始化裁切框
            self.crop_frame = CropFrame(
                self.video_width, self.video_height,
                initial_margins.get('top', 0),
                initial_margins.get('bottom', 0),
                initial_margins.get('left', 0),
                initial_margins.get('right', 0)
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                t("common.error", "错误"),
                t("crop_region_selector.error.load_video_failed", "加载视频失败: {error}").format(error=str(e)),
            )
    
    def _get_display_rect(self) -> QRect:
        """获取视频在控件中的显示区域"""
        widget_w = self.width()
        widget_h = self.height()
        
        # 计算缩放比例（保持宽高比）
        scale_w = widget_w / self.video_width
        scale_h = widget_h / self.video_height
        self.scale_factor = min(scale_w, scale_h)
        
        # 计算显示尺寸
        display_w = int(self.video_width * self.scale_factor)
        display_h = int(self.video_height * self.scale_factor)
        
        # 居中显示
        x = (widget_w - display_w) // 2
        y = (widget_h - display_h) // 2
        
        return QRect(x, y, display_w, display_h)
    
    def _video_to_widget_coords(self, video_x: int, video_y: int) -> QPoint:
        """视频坐标转控件坐标"""
        display_rect = self._get_display_rect()
        x = display_rect.x() + int(video_x * self.scale_factor)
        y = display_rect.y() + int(video_y * self.scale_factor)
        return QPoint(x, y)
    
    def _widget_to_video_coords(self, widget_x: int, widget_y: int) -> QPoint:
        """控件坐标转视频坐标"""
        display_rect = self._get_display_rect()
        video_x = int((widget_x - display_rect.x()) / self.scale_factor)
        video_y = int((widget_y - display_rect.y()) / self.scale_factor)
        return QPoint(video_x, video_y)
    
    def paintEvent(self, event):
        """绘制视频帧和裁切框"""
        if self.video_frame is None:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制视频帧
        display_rect = self._get_display_rect()
        height, width, channel = self.video_frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(self.video_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(display_rect.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(display_rect, scaled_pixmap)
        
        # 绘制裁切框
        crop_rect = self.crop_frame.get_crop_rect()
        top_left = self._video_to_widget_coords(crop_rect.x(), crop_rect.y())
        bottom_right = self._video_to_widget_coords(crop_rect.x() + crop_rect.width(), crop_rect.y() + crop_rect.height())
        
        # 半透明蒙版（裁切区域外）
        mask_color = QColor(0, 0, 0, 120)
        painter.fillRect(display_rect.x(), display_rect.y(), 
                        display_rect.width(), top_left.y() - display_rect.y(), 
                        mask_color)  # 上
        painter.fillRect(display_rect.x(), bottom_right.y(), 
                        display_rect.width(), display_rect.bottom() - bottom_right.y(), 
                        mask_color)  # 下
        painter.fillRect(display_rect.x(), top_left.y(), 
                        top_left.x() - display_rect.x(), bottom_right.y() - top_left.y(), 
                        mask_color)  # 左
        painter.fillRect(bottom_right.x(), top_left.y(), 
                        display_rect.right() - bottom_right.x(), bottom_right.y() - top_left.y(), 
                        mask_color)  # 右
        
        # 裁切框边框
        pen = QPen(QColor(Theme.Primary), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        crop_display_rect = QRect(top_left, bottom_right)
        painter.drawRect(crop_display_rect)
        
        # 绘制九宫格辅助线（三分法）
        grid_pen = QPen(QColor(255, 255, 255, 120), 1, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        
        # 垂直线
        third_width = crop_display_rect.width() / 3
        painter.drawLine(
            int(top_left.x() + third_width), top_left.y(),
            int(top_left.x() + third_width), bottom_right.y()
        )
        painter.drawLine(
            int(top_left.x() + 2 * third_width), top_left.y(),
            int(top_left.x() + 2 * third_width), bottom_right.y()
        )
        
        # 水平线
        third_height = crop_display_rect.height() / 3
        painter.drawLine(
            top_left.x(), int(top_left.y() + third_height),
            bottom_right.x(), int(top_left.y() + third_height)
        )
        painter.drawLine(
            top_left.x(), int(top_left.y() + 2 * third_height),
            bottom_right.x(), int(top_left.y() + 2 * third_height)
        )
        
        # 绘制圆形手柄
        handle_radius = 6
        painter.setBrush(QBrush(QColor(Theme.Surface)))
        painter.setPen(QPen(QColor(Theme.Primary), 2))
        
        painter.drawEllipse(top_left, handle_radius, handle_radius)  # 左上
        painter.drawEllipse(QPoint(bottom_right.x(), top_left.y()), handle_radius, handle_radius)  # 右上
        painter.drawEllipse(QPoint(top_left.x(), bottom_right.y()), handle_radius, handle_radius)  # 左下
        painter.drawEllipse(bottom_right, handle_radius, handle_radius)  # 右下
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        if event.button() != Qt.MouseButton.LeftButton:
            return
        
        pos = event.position().toPoint()
        video_pos = self._widget_to_video_coords(pos.x(), pos.y())
        
        # 检测是否点击在裁切框边缘或角点
        crop_rect = self.crop_frame.get_crop_rect()
        
        # 检测阈值（视频坐标系）
        threshold = int(self.edge_threshold / self.scale_factor)
        
        # 判断拖拽类型
        near_left = abs(video_pos.x() - crop_rect.left()) < threshold
        near_right = abs(video_pos.x() - crop_rect.right()) < threshold
        near_top = abs(video_pos.y() - crop_rect.top()) < threshold
        near_bottom = abs(video_pos.y() - crop_rect.bottom()) < threshold
        
        if near_left and near_top:
            self.drag_type = 'topleft'
        elif near_right and near_top:
            self.drag_type = 'topright'
        elif near_left and near_bottom:
            self.drag_type = 'bottomleft'
        elif near_right and near_bottom:
            self.drag_type = 'bottomright'
        elif near_top:
            self.drag_type = 'top'
        elif near_bottom:
            self.drag_type = 'bottom'
        elif near_left:
            self.drag_type = 'left'
        elif near_right:
            self.drag_type = 'right'
        else:
            # 检测是否在裁剪框内部（支持整体移动）
            if crop_rect.contains(video_pos):
                self.drag_type = 'move'
            else:
                return
        
        # 开始拖拽
        self.dragging = True
        self.drag_start_pos = video_pos
        self.drag_start_margins = {
            'top': self.crop_frame.top,
            'bottom': self.crop_frame.bottom,
            'left': self.crop_frame.left,
            'right': self.crop_frame.right,
        }
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        if not self.dragging:
            # 改变鼠标样式
            pos = event.position().toPoint()
            video_pos = self._widget_to_video_coords(pos.x(), pos.y())
            crop_rect = self.crop_frame.get_crop_rect()
            threshold = int(self.edge_threshold / self.scale_factor)
            
            near_left = abs(video_pos.x() - crop_rect.left()) < threshold
            near_right = abs(video_pos.x() - crop_rect.right()) < threshold
            near_top = abs(video_pos.y() - crop_rect.top()) < threshold
            near_bottom = abs(video_pos.y() - crop_rect.bottom()) < threshold
            
            if (near_left and near_top) or (near_right and near_bottom):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif (near_right and near_top) or (near_left and near_bottom):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif near_left or near_right:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif near_top or near_bottom:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            elif crop_rect.contains(video_pos):
                # 在裁剪框内部，显示移动光标
                self.setCursor(Qt.CursorShape.SizeAllCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return
        
        # 拖拽中
        pos = event.position().toPoint()
        video_pos = self._widget_to_video_coords(pos.x(), pos.y())
        
        delta_x = video_pos.x() - self.drag_start_pos.x()
        delta_y = video_pos.y() - self.drag_start_pos.y()
        
        # 整体移动裁剪框
        if self.drag_type == 'move':
            # 计算新的边距，确保不超出视频边界
            new_left = self.drag_start_margins['left'] + delta_x
            new_right = self.drag_start_margins['right'] - delta_x
            new_top = self.drag_start_margins['top'] + delta_y
            new_bottom = self.drag_start_margins['bottom'] - delta_y
            
            # 限制边界
            if new_left < 0:
                new_right += new_left
                new_left = 0
            if new_right < 0:
                new_left += new_right
                new_right = 0
            if new_top < 0:
                new_bottom += new_top
                new_top = 0
            if new_bottom < 0:
                new_top += new_bottom
                new_bottom = 0
            
            self.crop_frame.left = int(new_left)
            self.crop_frame.right = int(new_right)
            self.crop_frame.top = int(new_top)
            self.crop_frame.bottom = int(new_bottom)
        else:
            # 调整边距（原有逻辑）
            if 'left' in self.drag_type:
                new_left = max(0, min(self.video_width - self.crop_frame.right - 10, 
                                      self.drag_start_margins['left'] + delta_x))
                self.crop_frame.left = new_left
            
            if 'right' in self.drag_type:
                new_right = max(0, min(self.video_width - self.crop_frame.left - 10, 
                                       self.drag_start_margins['right'] - delta_x))
                self.crop_frame.right = new_right
            
            if 'top' in self.drag_type:
                new_top = max(0, min(self.video_height - self.crop_frame.bottom - 10, 
                                     self.drag_start_margins['top'] + delta_y))
                self.crop_frame.top = new_top
            
            if 'bottom' in self.drag_type:
                new_bottom = max(0, min(self.video_height - self.crop_frame.top - 10, 
                                        self.drag_start_margins['bottom'] - delta_y))
                self.crop_frame.bottom = new_bottom
        
        # 发送边距变化信号
        self.margins_changed.emit(self.get_margins())
        
        # 重绘
        self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.drag_type = None
    
    def get_margins(self) -> dict:
        """获取当前边距"""
        return {
            'top': self.crop_frame.top,
            'bottom': self.crop_frame.bottom,
            'left': self.crop_frame.left,
            'right': self.crop_frame.right,
        }
    
    def get_cropped_size(self) -> tuple:
        """获取裁切后分辨率"""
        return self.crop_frame.get_cropped_size()


class CropRegionSelectorDialog(QDialog):
    """裁切区域选取对话框"""
    
    def __init__(
        self,
        video_path: str,
        initial_margins: dict,
        parent=None,
        video_info: Optional[Dict] = None,
        live_update_callback: Optional[Callable[[dict], None]] = None,
        preview_callback: Optional[Callable[[], None]] = None,
        mode_info: str = ""
    ):
        super().__init__(parent)
        self.video_path = video_path
        self.initial_margins = initial_margins
        self.video_info = video_info or {}
        self.live_update_callback = live_update_callback
        self.preview_callback = preview_callback
        self.mode_info = mode_info
        self._suppress_live_update = True
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(t("crop_region_selector.title", "设置裁切区域"))
        self.setModal(True)
        self.resize(1000, 700)
        self.setStyleSheet(f"QDialog {{ background-color: {Theme.Background}; }}")
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 信息提示栏
        self.info_label = QLabel()
        self.info_label.setStyleSheet(f"QLabel {{ font-size: 14px; font-weight: 600; color: {Theme.Primary}; padding: 12px; background: {Theme.PrimaryLight}; border-radius: 8px; }}")
        layout.addWidget(self.info_label)
        
        # 模式信息栏
        self.mode_label = QLabel()
        self.mode_label.setStyleSheet(f"QLabel {{ font-size: 13px; padding: 8px; color: {Theme.TextSecondary}; }}")
        layout.addWidget(self.mode_label)
        
        # 视频预览与裁切框
        self.crop_widget = CropVideoWidget(self.video_path, self.initial_margins, self)
        self.crop_widget.margins_changed.connect(self._on_margins_changed)
        layout.addWidget(self.crop_widget, 1)
        
        # 参数提示栏
        self.param_label = QLabel()
        self.param_label.setStyleSheet(f"QLabel {{ font-size: 13px; padding: 10px; color: {Theme.TextSecondary}; background: {Theme.Surface}; border: 1px solid {Theme.Border}; border-radius: 6px; }}")
        layout.addWidget(self.param_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        cancel_btn = ModernButton(t("common.btn.cancel", "取消"), style=ModernButton.Style.Outline, icon_name="cross")
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        if self.preview_callback is not None:
            preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Secondary, icon_name="eye")
            preview_btn.setMinimumWidth(120)
            preview_btn.clicked.connect(self._on_preview_clicked)
            button_layout.addWidget(preview_btn)
        
        confirm_btn = ModernButton(t("common.btn.ok", "确定"), style=ModernButton.Style.Primary, icon_name="check")
        confirm_btn.setMinimumWidth(120)
        confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        
        # 初始化显示
        self._update_info_label()
        self._update_mode_label()
        self._on_margins_changed(self.initial_margins)
        self._suppress_live_update = False
    
    def _update_info_label(self):
        """更新信息提示栏"""
        video_w = self.crop_widget.video_width
        video_h = self.crop_widget.video_height
        duration = self.video_info.get('duration', 0.0)
        duration_text = self._format_duration(duration)
        self.info_label.setText(
            t(
                "crop_region_selector.info",
                "设置裁切区域 - 分辨率：{width}×{height}，时长：{duration}",
            ).format(width=video_w, height=video_h, duration=duration_text)
        )
    
    def _update_mode_label(self):
        """更新模式信息栏"""
        if self.mode_info:
            self.mode_label.setText(self.mode_info)
        else:
            self.mode_label.setText("")
    
    def _on_margins_changed(self, margins: dict):
        """边距变化时更新参数提示栏"""
        cropped_w, cropped_h = self.crop_widget.get_cropped_size()
        param_text = t(
            "crop_region_selector.params",
            "边距：上：{top}，下：{bottom}，左：{left}，右：{right} | 裁切后分辨率：{width}×{height}",
        ).format(
            top=margins["top"],
            bottom=margins["bottom"],
            left=margins["left"],
            right=margins["right"],
            width=cropped_w,
            height=cropped_h,
        )
        self.param_label.setText(param_text)
        
        if self.live_update_callback is not None and not self._suppress_live_update:
            self.live_update_callback(margins)
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds <= 0:
            return "00:00:00.00"
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:05.2f}"
        return f"{minutes:02d}:{secs:05.2f}"
    
    def _on_preview_clicked(self):
        """点击预览按钮"""
        if self.preview_callback is not None:
            self.preview_callback()
    
    def get_margins(self) -> dict:
        """获取裁切边距"""
        return self.crop_widget.get_margins()
