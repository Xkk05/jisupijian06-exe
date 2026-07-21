"""
去水印时间段选择器 - 可视化选择去水印的时间段
"""
import cv2
import os
import numpy as np
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QSlider, QMessageBox, QTimeEdit, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QTime
from PyQt6.QtGui import QImage, QPixmap
from ui.components import load_svg_icon
from ui.i18n import t


class WatermarkTimeSelector(QDialog):
    """去水印时间段选择对话框"""
    
    def __init__(self, video_path: str, initial_start: float = 0.0, initial_end: float = 0.0, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.initial_start = initial_start
        self.initial_end = initial_end if initial_end > 0 else 0.0
        self.cap = None
        self.total_frames = 0
        self.fps = 30
        self.total_duration = 0.0
        self.current_frame = 0
        self.current_setting = None  # None, "start", "end"
        self.is_playing = False
        self.playback_timer = None
        
        self.setWindowTitle(t("watermark_time_selector.title", "选择去水印时间段"))
        self.setMinimumSize(1000, 700)  # 增大最小尺寸
        self.resize(1200, 800)  # 增大默认尺寸
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.init_ui()
        self.load_video()
        self.setup_initial_selection()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        tip_label = QLabel(
            t(
                "watermark_time_selector.tip",
                "拖动进度条选择去水印的开始和结束时间，空格键播放/暂停，使用键盘左右键可精细化获得时间段",
            )
        )
        tip_label.setStyleSheet(
            "QLabel { "
            "font-size: 14px; "
            "font-weight: bold; "
            "color: #2196F3; "
            "padding: 10px; "
            "background-color: #E3F2FD; "
            "border-radius: 5px; "
            "}"
        )
        layout.addWidget(tip_label)
        
        # 视频预览区域
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(400)  # 增加最小高度
        self.preview_label.setStyleSheet("QLabel { border: 2px solid #999; background-color: #000; }")
        layout.addWidget(self.preview_label, 1)
        
        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)
        
        self.time_info_label = QLabel(
            t("watermark_time_selector.time.initial", "时间: 00:00 / 00:00")
        )
        self.time_info_label.setStyleSheet("QLabel { font-size: 13px; font-weight: bold; }")
        self.time_info_label.setMinimumWidth(150)
        progress_layout.addWidget(self.time_info_label)
        
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(0)
        self.frame_slider.setValue(0)
        self.frame_slider.setStyleSheet(
            "QSlider::groove:horizontal { "
            "border: 1px solid #999; "
            "height: 10px; "
            "background: #E0E0E0; "
            "border-radius: 5px; "
            "} "
            "QSlider::handle:horizontal { "
            "background: #2196F3; "
            "border: 1px solid #1976D2; "
            "width: 20px; "
            "height: 20px; "
            "margin: -5px 0; "
            "border-radius: 10px; "
            "}"
        )
        self.frame_slider.valueChanged.connect(self.on_slider_changed)
        progress_layout.addWidget(self.frame_slider, 1)
        
        layout.addLayout(progress_layout)
        
        # 时间设置控制按钮
        time_control_layout = QHBoxLayout()
        time_control_layout.setSpacing(15)
        
        self.set_start_btn = QPushButton(
            t("watermark_time_selector.btn.set_start", "⏺ 设置开始时间")
        )
        self.set_start_btn.setMinimumHeight(35)
        self.set_start_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 13px; "
            "font-weight: bold; "
            "background-color: #2196F3; "
            "color: white; "
            "border: none; "
            "border-radius: 5px; "
            "padding: 8px 16px; "
            "} "
            "QPushButton:hover { background-color: #1976D2; } "
            "QPushButton:pressed { background-color: #0D47A1; }"
            "QPushButton:disabled { background-color: #CCCCCC; color: #666666; }"
        )
        self.set_start_btn.clicked.connect(self.on_set_start_time)
        time_control_layout.addWidget(self.set_start_btn)
        
        self.set_end_btn = QPushButton(
            t("watermark_time_selector.btn.set_end", "⏹ 设置结束时间")
        )
        self.set_end_btn.setMinimumHeight(35)
        self.set_end_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 13px; "
            "font-weight: bold; "
            "background-color: #4CAF50; "
            "color: white; "
            "border: none; "
            "border-radius: 5px; "
            "padding: 8px 16px; "
            "} "
            "QPushButton:hover { background-color: #45a049; } "
            "QPushButton:pressed { background-color: #3d8b40; }"
            "QPushButton:disabled { background-color: #CCCCCC; color: #666666; }"
        )
        self.set_end_btn.clicked.connect(self.on_set_end_time)
        time_control_layout.addWidget(self.set_end_btn)
        
        self.current_setting_label = QLabel(
            t("watermark_time_selector.current.none", "当前设置: 无")
        )
        self.current_setting_label.setStyleSheet(
            "QLabel { "
            "font-size: 13px; "
            "font-weight: bold; "
            "color: #FF9800; "
            "padding: 5px 10px; "
            "background-color: #FFF3E0; "
            "border-radius: 3px; "
            "}"
        )
        time_control_layout.addWidget(self.current_setting_label)
        time_control_layout.addStretch()
        
        layout.addLayout(time_control_layout)
        
        # 时间输入控件
        time_layout = QHBoxLayout()
        time_layout.setSpacing(15)
        
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm:ss.zzz")
        self.start_time_edit.setAccelerated(True)  # 启用加速滚动
        self.start_time_edit.timeChanged.connect(self.on_start_time_changed)
        time_layout.addWidget(QLabel(t("watermark_time_selector.start_time", "开始时间:")))
        time_layout.addWidget(self.start_time_edit)
        
        time_layout.addSpacing(20)
        
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm:ss.zzz")
        self.end_time_edit.setAccelerated(True)  # 启用加速滚动
        self.end_time_edit.timeChanged.connect(self.on_end_time_changed)
        time_layout.addWidget(QLabel(t("watermark_time_selector.end_time", "结束时间:")))
        time_layout.addWidget(self.end_time_edit)
        
        time_layout.addStretch()
        layout.addLayout(time_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        self.enable_checkbox = QCheckBox(
            t("watermark_time_selector.enable", "启用时间段去水印")
        )
        self.enable_checkbox.setChecked(True)
        button_layout.addWidget(self.enable_checkbox)
        
        button_layout.addSpacing(20)
        
        reset_btn = QPushButton(t("common.reset", "重置"))
        reset_btn.setMinimumHeight(40)
        reset_btn.setMinimumWidth(120)
        reset_btn.setIcon(load_svg_icon("refresh", 16, "#FFFFFF"))
        reset_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 13px; "
            "font-weight: bold; "
            "background-color: #FF9800; "
            "color: white; "
            "border: none; "
            "border-radius: 5px; "
            "padding: 8px 16px; "
            "} "
            "QPushButton:hover { background-color: #F57C00; } "
            "QPushButton:pressed { background-color: #E65100; }"
        )
        reset_btn.clicked.connect(self.reset_selection)
        button_layout.addWidget(reset_btn)
        
        cancel_btn = QPushButton(t("watermark_time_selector.btn.cancel", "❌ 取消"))
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 13px; "
            "font-weight: bold; "
            "background-color: #9E9E9E; "
            "color: white; "
            "border: none; "
            "border-radius: 5px; "
            "padding: 8px 16px; "
            "} "
            "QPushButton:hover { background-color: #757575; } "
            "QPushButton:pressed { background-color: #616161; }"
        )
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        confirm_btn = QPushButton(t("watermark_time_selector.btn.confirm", "✅ 确认"))
        confirm_btn.setMinimumHeight(40)
        confirm_btn.setMinimumWidth(120)
        confirm_btn.setStyleSheet(
            "QPushButton { "
            "font-size: 13px; "
            "font-weight: bold; "
            "background-color: #4CAF50; "
            "color: white; "
            "border: none; "
            "border-radius: 5px; "
            "padding: 8px 16px; "
            "} "
            "QPushButton:hover { background-color: #45a049; } "
            "QPushButton:pressed { background-color: #3d8b40; }"
        )
        confirm_btn.clicked.connect(self.accept)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
    
    def _format_time(self, seconds: float) -> str:
        """将秒数转换为 HH:MM:SS 格式，支持小数点后两位"""
        # 支持更精细的时间显示（到0.01秒）
        hours = int(seconds) // 3600
        mins = (int(seconds) % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:05.2f}"
        else:
            return f"{mins:02d}:{secs:05.2f}"
    
    def load_video(self):
        """加载视频"""
        if not os.path.exists(self.video_path):
            QMessageBox.critical(
                self,
                t("common.error", "错误"),
                t("watermark_time_selector.error.file_not_found", "视频文件不存在"),
            )
            self.reject()
            return
        
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            QMessageBox.critical(
                self,
                t("common.error", "错误"),
                t("watermark_time_selector.error.open_failed", "无法打开视频文件"),
            )
            self.reject()
            return
        
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps == 0:
            self.fps = 30
        
        self.total_duration = self.total_frames / self.fps
        self.frame_slider.setMaximum(max(0, self.total_frames - 1))
        
        total_time_text = self._format_time(self.total_duration)
        self.time_info_label.setText(
            t(
                "watermark_time_selector.time.initial_with_total",
                "时间: 00:00 / {total}",
                total=total_time_text,
            )
        )
        
        # 设置时间编辑器的最大值
        max_time = QTime(23, 59, 59)  # 设置一个较大的最大时间
        self.start_time_edit.setMaximumTime(max_time)
        self.end_time_edit.setMaximumTime(max_time)
        
        # 显示第一帧
        self.show_frame(0)
    
    def setup_initial_selection(self):
        """设置初始选择"""
        if self.initial_start > 0 or self.initial_end > 0:
            start_time = self.initial_start
            end_time = self.initial_end if self.initial_end > 0 else self.total_duration
            
            # 直接更新时间编辑器
            self.update_time_edits(start_time, end_time)
    
    def update_time_edits(self, start_time: float, end_time: float):
        """更新时间编辑器，支持小数秒"""
        # 转换为QTime，支持毫秒精度
        start_qtime = QTime(0, 0, 0).addMSecs(int(start_time * 1000))
        end_qtime = QTime(0, 0, 0).addMSecs(int(end_time * 1000))
        
        self.start_time_edit.setTime(start_qtime)
        self.end_time_edit.setTime(end_qtime)
    
    def show_frame(self, frame_index: int):
        """显示指定帧"""
        if not self.cap:
            return
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self.cap.read()
        
        if not ret:
            return
        
        self.current_frame = frame
        frame_h, frame_w = frame.shape[:2]
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        bytes_per_line = 3 * frame_w
        # 转换为bytes类型
        frame_data = np.ascontiguousarray(frame_rgb).tobytes()
        qt_image = QImage(frame_data, frame_w, frame_h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # 增大视频显示尺寸
        max_width = 1000
        max_height = 500
        
        scale_w = max_width / frame_w
        scale_h = max_height / frame_h
        scale = min(scale_w, scale_h)
        
        display_width = int(frame_w * scale)
        display_height = int(frame_h * scale)
        
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            display_width,
            display_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.preview_label.setPixmap(scaled_pixmap)
        
        current_seconds = frame_index / self.fps
        total_seconds = self.total_frames / self.fps
        self.time_info_label.setText(
            t(
                "watermark_time_selector.time.current",
                "时间: {current} / {total}",
                current=self._format_time(current_seconds),
                total=self._format_time(total_seconds),
            )
        )
    
    def on_slider_changed(self, value: int):
        """进度条改变"""
        self.show_frame(value)
        
        # 计算精确的时间（支持小数秒）
        current_time = value / self.fps
        
        # 如果正在设置时间，更新对应的时间
        if self.current_setting == "start":
            end_time = (self.end_time_edit.time().hour() * 3600 + 
                       self.end_time_edit.time().minute() * 60 + 
                       self.end_time_edit.time().second() + 
                       self.end_time_edit.time().msec() / 1000.0)
            self.update_time_edits(current_time, end_time)
        elif self.current_setting == "end":
            start_time = (self.start_time_edit.time().hour() * 3600 + 
                         self.start_time_edit.time().minute() * 60 + 
                         self.start_time_edit.time().second() + 
                         self.start_time_edit.time().msec() / 1000.0)
            self.update_time_edits(start_time, current_time)
    
    def on_start_time_changed(self, time: QTime):
        """开始时间改变"""
        # 计算精确的时间（支持小数秒）
        seconds = (time.hour() * 3600 + 
                  time.minute() * 60 + 
                  time.second() + 
                  time.msec() / 1000.0)
        
        if seconds > self.total_duration:
            seconds = self.total_duration
        
        # 直接更新结束时间编辑器（如果需要）
        end_time = (self.end_time_edit.time().hour() * 3600 + 
                   self.end_time_edit.time().minute() * 60 + 
                   self.end_time_edit.time().second() + 
                   self.end_time_edit.time().msec() / 1000.0)
        
        if seconds > end_time and end_time > 0:
            # 如果开始时间大于结束时间，调整结束时间
            end_qtime = QTime(0, 0, 0).addMSecs(int((seconds + 1) * 1000))
            self.end_time_edit.setTime(end_qtime)
    
    def on_end_time_changed(self, time: QTime):
        """结束时间改变"""
        # 计算精确的时间（支持小数秒）
        seconds = (time.hour() * 3600 + 
                  time.minute() * 60 + 
                  time.second() + 
                  time.msec() / 1000.0)
        
        if seconds > self.total_duration:
            seconds = self.total_duration
        
        # 直接更新开始时间编辑器（如果需要）
        start_time = (self.start_time_edit.time().hour() * 3600 + 
                     self.start_time_edit.time().minute() * 60 + 
                     self.start_time_edit.time().second() + 
                     self.start_time_edit.time().msec() / 1000.0)
        
        if seconds < start_time and start_time > 0:
            # 如果结束时间小于开始时间，调整开始时间
            start_qtime = QTime(0, 0, 0).addMSecs(int(max(0, (seconds - 1)) * 1000))
            self.start_time_edit.setTime(start_qtime)
    
    def on_set_start_time(self):
        """设置开始时间按钮点击"""
        self.current_setting = "start"
        self.update_setting_buttons()
        self.current_setting_label.setText(
            t("watermark_time_selector.current.start", "当前设置: 开始时间")
        )
        
        # 计算精确的时间（支持小数秒）
        current_time = self.frame_slider.value() / self.fps
        end_time = (self.end_time_edit.time().hour() * 3600 + 
                   self.end_time_edit.time().minute() * 60 + 
                   self.end_time_edit.time().second() + 
                   self.end_time_edit.time().msec() / 1000.0)
        self.update_time_edits(current_time, end_time)
        
        # 将焦点设置到进度条上，提升用户体验
        self.frame_slider.setFocus()
    
    def on_set_end_time(self):
        """设置结束时间按钮点击"""
        self.current_setting = "end"
        self.update_setting_buttons()
        self.current_setting_label.setText(
            t("watermark_time_selector.current.end", "当前设置: 结束时间")
        )
        
        # 计算精确的时间（支持小数秒）
        current_time = self.frame_slider.value() / self.fps
        start_time = (self.start_time_edit.time().hour() * 3600 + 
                     self.start_time_edit.time().minute() * 60 + 
                     self.start_time_edit.time().second() + 
                     self.start_time_edit.time().msec() / 1000.0)
        self.update_time_edits(start_time, current_time)
        
        # 将焦点设置到进度条上，提升用户体验
        self.frame_slider.setFocus()
    
    def update_setting_buttons(self):
        """更新设置按钮状态"""
        if self.current_setting == "start":
            self.set_start_btn.setEnabled(False)
            self.set_end_btn.setEnabled(True)
        elif self.current_setting == "end":
            self.set_start_btn.setEnabled(True)
            self.set_end_btn.setEnabled(False)
        else:
            self.set_start_btn.setEnabled(True)
            self.set_end_btn.setEnabled(True)
    
    def toggle_play_pause(self):
        """切换播放/暂停"""
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
    
    def start_playback(self):
        """开始播放"""
        if not self.playback_timer:
            from PyQt6.QtCore import QTimer
            self.playback_timer = QTimer(self)
            self.playback_timer.timeout.connect(self.play_next_frame)
        
        self.playback_timer.start(1000 // int(self.fps))  # 根据FPS设置间隔
        self.is_playing = True
    
    def pause_playback(self):
        """暂停播放"""
        if self.playback_timer:
            self.playback_timer.stop()
        
        self.is_playing = False

    def play_next_frame(self):
        """播放下一帧"""
        current_value = self.frame_slider.value()
        if current_value >= self.frame_slider.maximum():
            self.pause_playback()
            return
        
        self.frame_slider.setValue(current_value + 1)
        
        # 计算精确的时间（支持小数秒）
        current_time = self.frame_slider.value() / self.fps
        
        # 如果正在设置时间，更新对应的时间
        if self.current_setting == "start":
            end_time = (self.end_time_edit.time().hour() * 3600 + 
                       self.end_time_edit.time().minute() * 60 + 
                       self.end_time_edit.time().second() + 
                       self.end_time_edit.time().msec() / 1000.0)
            self.update_time_edits(current_time, end_time)
        elif self.current_setting == "end":
            start_time = (self.start_time_edit.time().hour() * 3600 + 
                         self.start_time_edit.time().minute() * 60 + 
                         self.start_time_edit.time().second() + 
                         self.start_time_edit.time().msec() / 1000.0)
            self.update_time_edits(start_time, current_time)
    
    def keyPressEvent(self, a0):
        """键盘事件处理"""
        if a0.key() == Qt.Key.Key_Space:
            self.toggle_play_pause()
            a0.accept()
        elif a0.key() == Qt.Key.Key_Left:
            # 后退一帧
            current_value = self.frame_slider.value()
            if current_value > 0:
                self.frame_slider.setValue(current_value - 1)
                # 计算精确的时间（支持小数秒）
                current_time = self.frame_slider.value() / self.fps
                # 如果正在设置时间，更新对应的时间
                if self.current_setting == "start":
                    end_time = (self.end_time_edit.time().hour() * 3600 + 
                               self.end_time_edit.time().minute() * 60 + 
                               self.end_time_edit.time().second() + 
                               self.end_time_edit.time().msec() / 1000.0)
                    self.update_time_edits(current_time, end_time)
                elif self.current_setting == "end":
                    start_time = (self.start_time_edit.time().hour() * 3600 + 
                                 self.start_time_edit.time().minute() * 60 + 
                                 self.start_time_edit.time().second() + 
                                 self.start_time_edit.time().msec() / 1000.0)
                    self.update_time_edits(start_time, current_time)
            a0.accept()
        elif a0.key() == Qt.Key.Key_Right:
            # 前进一帧
            current_value = self.frame_slider.value()
            if current_value < self.frame_slider.maximum():
                self.frame_slider.setValue(current_value + 1)
                # 计算精确的时间（支持小数秒）
                current_time = self.frame_slider.value() / self.fps
                # 如果正在设置时间，更新对应的时间
                if self.current_setting == "start":
                    end_time = (self.end_time_edit.time().hour() * 3600 + 
                               self.end_time_edit.time().minute() * 60 + 
                               self.end_time_edit.time().second() + 
                               self.end_time_edit.time().msec() / 1000.0)
                    self.update_time_edits(current_time, end_time)
                elif self.current_setting == "end":
                    start_time = (self.start_time_edit.time().hour() * 3600 + 
                                 self.start_time_edit.time().minute() * 60 + 
                                 self.start_time_edit.time().second() + 
                                 self.start_time_edit.time().msec() / 1000.0)
                    self.update_time_edits(start_time, current_time)
            a0.accept()
        else:
            super().keyPressEvent(a0)
    
    def reset_selection(self):
        """重置选区为0"""
        # 将开始和结束时间都重置为0
        start_qtime = QTime(0, 0, 0)
        end_qtime = QTime(0, 0, 0)
        self.start_time_edit.setTime(start_qtime)
        self.end_time_edit.setTime(end_qtime)
    
    def get_selection(self) -> tuple:
        """获取选择的时间段 (enabled, start_time, end_time)"""
        enabled = self.enable_checkbox.isChecked()
        
        # 直接从时间编辑器获取时间，支持毫秒精度
        start_time = (self.start_time_edit.time().hour() * 3600 + 
                     self.start_time_edit.time().minute() * 60 + 
                     self.start_time_edit.time().second() + 
                     self.start_time_edit.time().msec() / 1000.0)
        
        end_time = (self.end_time_edit.time().hour() * 3600 + 
                   self.end_time_edit.time().minute() * 60 + 
                   self.end_time_edit.time().second() + 
                   self.end_time_edit.time().msec() / 1000.0)
        
        # 如果没有选择或重置状态，开始和结束时间都为0
        # 移除此处的默认值设置，保持用户设置的值
        # if start_time == 0 and end_time == 0:
        #     start_time = 0.0
        #     end_time = self.total_duration
        
        return (enabled, start_time, end_time)
    
    def closeEvent(self, a0):
        """关闭事件"""
        if self.cap:
            self.cap.release()
        super().closeEvent(a0)
