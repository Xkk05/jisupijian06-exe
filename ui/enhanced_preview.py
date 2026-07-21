"""
实时预览和监控面板
支持实时预览、视频播放、音频波形可视化、处理进度监控
"""
from typing import Optional, Dict, List, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider,
    QProgressBar, QComboBox, QSpinBox, QDoubleSpinBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap
from PyQt6.QtGui import QPaintEvent, QMouseEvent, QWheelEvent
from ui.i18n import t
import math
import logging

logger = logging.getLogger(__name__)


class AudioWaveformWidget(QWidget):
    """音频波形显示"""
    
    def __init__(self):
        super().__init__()
        self.waveform_data = []
        self.playback_position = 0.0
        self.duration = 0.0
        self.scale = 100
        
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
    
    def set_waveform(self, data: List[float], duration: float = 0.0):
        """设置波形数据"""
        self.waveform_data = data
        self.duration = duration
        self.update()
    
    def set_playback_position(self, position: float):
        """设置播放位置"""
        self.playback_position = max(0, min(position, self.duration))
        self.update()
    
    def paintEvent(self, a0: Any) -> None:
        """绘制波形"""
        event = a0
        painter = QPainter(self)
        
        # 背景
        painter.fillRect(event.rect(), QColor(40, 40, 40))
        
        # 绘制波形
        if self.waveform_data:
            painter.setPen(QPen(QColor(100, 200, 100), 1))
            
            height = self.height()
            center_y = height // 2
            
            # 计算每个采样点的X坐标
            num_samples = len(self.waveform_data)
            width = self.width()
            
            for i in range(num_samples - 1):
                x1 = int((i / num_samples) * width)
                x2 = int(((i + 1) / num_samples) * width)
                
                # 波形值映射到Y坐标
                y1 = center_y - int(self.waveform_data[i] * (height // 2 - 5))
                y2 = center_y - int(self.waveform_data[i + 1] * (height // 2 - 5))
                
                painter.drawLine(x1, y1, x2, y2)
        
        # 绘制播放位置指示器
        if self.duration > 0:
            play_x = int((self.playback_position / self.duration) * self.width())
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(play_x, 0, play_x, self.height())
    
    def mousePressEvent(self, a0: Any) -> None:
        """鼠标按下跳转"""
        event = a0
        if self.duration > 0:
            new_pos = (event.pos().x() / self.width()) * self.duration
            self.playback_position = max(0, min(new_pos, self.duration))
            self.update()


class SpectrumAnalyzer(QWidget):
    """频谱分析器"""
    
    def __init__(self):
        super().__init__()
        self.spectrum_data = []
        self.peak_hold = []
        
        self.setMinimumHeight(100)
        self.setMaximumHeight(150)
    
    def set_spectrum(self, data: List[float]):
        """设置频谱数据"""
        self.spectrum_data = data
        
        # 更新峰值保持
        if not self.peak_hold:
            self.peak_hold = data[:]
        else:
            for i in range(min(len(data), len(self.peak_hold))):
                self.peak_hold[i] = max(self.peak_hold[i], data[i])
        
        self.update()
    
    def clear_peak_hold(self):
        """清除峰值保持"""
        self.peak_hold.clear()
    
    def paintEvent(self, a0: Any) -> None:
        """绘制频谱"""
        event = a0
        painter = QPainter(self)
        
        # 背景
        painter.fillRect(event.rect(), QColor(30, 30, 30))
        
        if not self.spectrum_data:
            return
        
        # 绘制频谱柱
        num_bars = len(self.spectrum_data)
        bar_width = max(1, self.width() // num_bars)
        
        for i, value in enumerate(self.spectrum_data):
            x = i * bar_width
            # 归一化值到高度
            bar_height = int(value * self.height())
            
            # 颜色梯度（低音绿色，高音红色）
            hue = int((1 - value) * 120)  # 0-120 绿色到红色
            color = QColor.fromHsv(hue, 255, 255)
            
            painter.fillRect(
                QRect(x, self.height() - bar_height, bar_width - 1, bar_height),
                QBrush(color)
            )
            
            # 绘制峰值保持线
            if i < len(self.peak_hold):
                peak_y = self.height() - int(self.peak_hold[i] * self.height())
                painter.setPen(QPen(QColor(255, 255, 0), 1))
                painter.drawLine(x, peak_y, x + bar_width - 1, peak_y)


class VolumeMonitor(QWidget):
    """音量监控器"""
    
    def __init__(self):
        super().__init__()
        self.left_level = 0.0
        self.right_level = 0.0
        self.peak_left = 0.0
        self.peak_right = 0.0
        self.clipping = False
        
        self.setMinimumHeight(40)
        self.setMaximumHeight(60)
    
    def set_levels(self, left: float, right: float):
        """设置音量级别"""
        self.left_level = max(0, min(left, 1.0))
        self.right_level = max(0, min(right, 1.0))
        
        # 更新峰值
        self.peak_left = max(self.peak_left, left)
        self.peak_right = max(self.peak_right, right)
        
        # 检测削波
        self.clipping = (left > 1.0 or right > 1.0)
        
        self.update()
    
    def reset_peaks(self):
        """重置峰值"""
        self.peak_left = 0.0
        self.peak_right = 0.0
    
    def paintEvent(self, a0: Any) -> None:
        """绘制音量计"""
        event = a0
        painter = QPainter(self)
        
        # 背景
        painter.fillRect(event.rect(), QColor(45, 45, 48))
        
        margin = 5
        height = self.height() - 2 * margin
        width = (self.width() - 3 * margin) // 2
        
        # 左声道
        self._draw_level_bar(painter, margin, margin, width, height, 
                            self.left_level, self.peak_left, "L")
        
        # 右声道
        self._draw_level_bar(painter, 2 * margin + width, margin, width, height,
                            self.right_level, self.peak_right, "R")
        
        # 削波指示
        if self.clipping:
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawText(
                self.width() - 40,
                self.height() - 5,
                t("enhanced_preview.volume.clipping", "削波!"),
            )
    
    def _draw_level_bar(self, painter: QPainter, x: int, y: int, 
                       width: int, height: int, level: float, peak: float, label: str):
        """绘制单个音量条"""
        # 背景
        painter.fillRect(QRect(x, y, width, height), QBrush(QColor(30, 30, 30)))
        
        # 音量条
        bar_height = int(height * level)
        if level < 0.8:
            color = QColor(0, 200, 0)  # 绿色
        elif level < 1.0:
            color = QColor(255, 200, 0)  # 黄色
        else:
            color = QColor(255, 0, 0)  # 红色
        
        painter.fillRect(QRect(x, y + height - bar_height, width, bar_height),
                        QBrush(color))
        
        # 峰值线
        peak_y = y + height - int(height * min(peak, 1.0))
        painter.setPen(QPen(QColor(255, 255, 0), 1))
        painter.drawLine(x, peak_y, x + width, peak_y)
        
        # 标签
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawText(x + 2, y + height - 2, label)


class ProcessingMonitor(QWidget):
    """处理监控面板"""
    
    def __init__(self):
        super().__init__()
        
        self.progress = 0
        self.current_task = ""
        self.fps = 0
        self.memory_usage = 0
        self.cpu_usage = 0
        
        layout = QVBoxLayout()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(QLabel(t("enhanced_preview.monitor.progress", "处理进度:")))
        layout.addWidget(self.progress_bar)
        
        # 任务信息
        self.task_label = QLabel(t("enhanced_preview.monitor.ready", "准备就绪"))
        layout.addWidget(self.task_label)
        
        # 性能监控
        perf_layout = QHBoxLayout()
        self.fps_label = QLabel("FPS: 0")
        self.memory_label = QLabel(t("enhanced_preview.monitor.memory_initial", "内存: 0 MB"))
        self.cpu_label = QLabel("CPU: 0%")
        perf_layout.addWidget(self.fps_label)
        perf_layout.addWidget(self.memory_label)
        perf_layout.addWidget(self.cpu_label)
        layout.addLayout(perf_layout)
        
        self.setLayout(layout)
    
    def set_progress(self, progress: int, task_name: str = ""):
        """设置进度"""
        self.progress = max(0, min(progress, 100))
        self.current_task = task_name
        self.progress_bar.setValue(self.progress)
        
        if task_name:
            self.task_label.setText(
                t("enhanced_preview.monitor.task_progress", "任务: {name} ({progress}%)").format(
                    name=task_name, progress=self.progress
                )
            )
    
    def set_performance_metrics(self, fps: float, memory_mb: float, cpu_percent: float):
        """设置性能指标"""
        self.fps = fps
        self.memory_usage = memory_mb
        self.cpu_usage = cpu_percent
        
        self.fps_label.setText(f"FPS: {fps:.1f}")
        self.memory_label.setText(
            t("enhanced_preview.monitor.memory_value", "内存: {memory} MB").format(
                memory=f"{memory_mb:.0f}"
            )
        )
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")


class EnhancedPreviewPanel(QWidget):
    """增强预览面板"""
    
    preview_updated = pyqtSignal(QPixmap)
    
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        
        # 预览画布
        self.preview_canvas = PreviewCanvas()
        layout.addWidget(self.preview_canvas, 1)
        
        # 控制栏
        control_layout = QHBoxLayout()
        
        # 播放控制
        self.play_btn = QPushButton("▶")
        self.pause_btn = QPushButton("⏸")
        self.stop_btn = QPushButton("⏹")
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        
        # 音量控制
        control_layout.addWidget(QLabel(t("enhanced_preview.control.volume", "音量:")))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(100)
        control_layout.addWidget(self.volume_slider)
        
        # 缩放控制
        control_layout.addWidget(QLabel(t("enhanced_preview.control.zoom", "缩放:")))
        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["50%", "75%", "100%", "150%", "200%"])
        self.zoom_combo.setCurrentText("100%")
        control_layout.addWidget(self.zoom_combo)
        
        control_layout.addStretch()
        
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
    
    def set_preview_image(self, pixmap: QPixmap):
        """设置预览图像"""
        self.preview_canvas.set_image(pixmap)


class PreviewCanvas(QWidget):
    """预览画布"""
    
    def __init__(self):
        super().__init__()
        self.image: Optional[QPixmap] = None
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #1e1e1e;")
    
    def set_image(self, pixmap: QPixmap):
        """设置图像"""
        self.image = pixmap
        self.update()
    
    def set_zoom(self, zoom: float):
        """设置缩放"""
        self.zoom_level = max(0.1, min(zoom, 5.0))
        self.update()
    
    def paintEvent(self, a0: Any) -> None:
        """绘制"""
        event = a0
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor(30, 30, 30))
        
        if self.image:
            # 计算显示位置
            scaled = self.image.scaledToWidth(
                int(self.image.width() * self.zoom_level),
                Qt.TransformationMode.SmoothTransformation
            )
            
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            
            painter.drawPixmap(x + self.pan_x, y + self.pan_y, scaled)
    
    def wheelEvent(self, a0: Any) -> None:
        """鼠标滚轮缩放"""
        event = a0
        delta = event.angleDelta().y()
        if delta > 0:
            self.set_zoom(self.zoom_level * 1.1)
        else:
            self.set_zoom(self.zoom_level * 0.9)
