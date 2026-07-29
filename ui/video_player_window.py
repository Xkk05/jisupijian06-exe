"""
专业视频播放器窗口（使用OpenCV播放）
"""

import os
import cv2
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QFrame,
    QSizePolicy,
    QComboBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRect, QSize
from PyQt6.QtGui import QImage, QPixmap, QMouseEvent, QIcon, QColor, QPainter
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtSvg import QSvgRenderer
from ui.i18n import t


def load_svg_icon(icon_path: str, size: int = 24, color: str = "#FFFFFF") -> QIcon:
    """加载SVG图标并重新着色为白色"""
    if not os.path.exists(icon_path):
        return QIcon()

    # 加载SVG
    renderer = QSvgRenderer(icon_path)
    if not renderer.isValid():
        return QIcon()

    # 创建透明背景的pixmap
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    # 渲染SVG到pixmap
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    # 创建图标
    icon = QIcon(pixmap)
    return icon


class VideoLabel(QLabel):
    """自定义视频标签，支持双击事件"""

    video_double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.video_double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class SimpleVideoPlayer(QMainWindow):
    """简易视频播放器（使用OpenCV，极简设计）"""

    def __init__(self, video_path: str):
        super().__init__()
        self.video_path = video_path
        self.is_fullscreen = False
        self.is_playing = True
        self.is_seeking = False
        self.current_frame = 0
        self.playback_speed = 1.0
        self.normal_geometry = None

        print(f"\n[PLAYER] ========== 初始化播放器 (OpenCV) ==========")
        print(f"[PLAYER] 视频路径: {video_path}")
        print(f"[PLAYER] 文件存在: {os.path.exists(video_path)}")

        if not os.path.exists(video_path):
            print(f"[PLAYER ERROR] 文件不存在！")
            QMessageBox.critical(
                self,
                t("common.error", "错误"),
                t("video_player_window.error.file_not_found", "视频文件不存在:\n{path}").format(path=video_path),
            )
            return

        print(f"[PLAYER] 文件大小: {os.path.getsize(video_path) / 1024 / 1024:.2f} MB")

        self.setWindowTitle(
            t("video_player_window.title", "极速批剪播放器 - {name}").format(
                name=os.path.basename(video_path)
            )
        )
        self.setGeometry(100, 100, 1280, 720)
        self.setStyleSheet("background-color: #000000;")

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 视频显示区域（使用QLabel显示OpenCV帧）
        self.video_label = VideoLabel()
        self.video_label.setStyleSheet("background-color: #000000;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setScaledContents(False)  # 不拉伸，保持宽高比
        self.video_label.video_double_clicked.connect(self.toggle_fullscreen)
        main_layout.addWidget(self.video_label)

        # 悬浮控制栏（覆盖在视频上）
        overlay_layout = QVBoxLayout(self.video_label)
        overlay_layout.setContentsMargins(16, 16, 16, 20)
        overlay_layout.setSpacing(0)
        overlay_layout.addStretch(1)

        # 先创建 controls_bar
        self.controls_bar = QFrame(self.video_label)
        self.controls_bar.setObjectName("controls_bar")
        self.controls_bar.setFixedHeight(56)
        self.controls_bar.setMinimumWidth(320)
        self.controls_bar.setMaximumWidth(600)
        self.controls_bar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.controls_bar.setStyleSheet(
            "#controls_bar {"
            "background-color: rgba(28, 28, 32, 230);"
            "border-radius: 28px;"
            "border: 1px solid rgba(255, 255, 255, 18);"
            "}"
            "QPushButton {"
            "color: #FFFFFF;"
            "background-color: transparent;"
            "border: none;"
            "border-radius: 18px;"
            "padding: 0px;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(255, 255, 255, 15);"
            "}"
            "QPushButton:pressed {"
            "background-color: rgba(255, 255, 255, 25);"
            "}"
            "QLabel {"
            "color: rgba(255, 255, 255, 220);"
            "background: transparent;"
            "font-size: 12px;"
            "font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;"
            "}"
            "QSlider {"
            "background: transparent;"
            "}"
            "QSlider::groove:horizontal {"
            "height: 4px;"
            "background: rgba(255, 255, 255, 25);"
            "border-radius: 2px;"
            "}"
            "QSlider::sub-page:horizontal {"
            "background: #4FC3F7;"
            "border-radius: 2px;"
            "}"
            "QSlider::handle:horizontal {"
            "width: 12px;"
            "height: 12px;"
            "margin: -4px 0;"
            "background: #FFFFFF;"
            "border-radius: 6px;"
            "}"
            "QSlider::handle:horizontal:hover {"
            "background: #4FC3F7;"
            "width: 14px;"
            "height: 14px;"
            "margin: -5px 0;"
            "}"
            "QComboBox {"
            "color: rgba(255, 255, 255, 220);"
            "background-color: rgba(255, 255, 255, 10);"
            "border: 1px solid rgba(255, 255, 255, 15);"
            "border-radius: 12px;"
            "padding: 2px 8px;"
            "font-size: 11px;"
            "}"
            "QComboBox:hover {"
            "background-color: rgba(255, 255, 255, 18);"
            "border: 1px solid rgba(255, 255, 255, 28);"
            "}"
            "QComboBox::drop-down {"
            "border: none;"
            "width: 18px;"
            "}"
            "QComboBox QAbstractItemView {"
            "background-color: #2D2D35;"
            "color: #FFFFFF;"
            "selection-background-color: #4FC3F7;"
            "selection-color: #FFFFFF;"
            "border: 1px solid rgba(255, 255, 255, 20);"
            "border-radius: 6px;"
            "outline: none;"
            "}"
            "QComboBox QAbstractItemView::item {"
            "height: 28px;"
            "padding: 4px 10px;"
            "border-radius: 4px;"
            "}"
            "QComboBox QAbstractItemView::item:hover {"
            "background-color: rgba(79, 195, 247, 0.3);"
            "}"
            "QComboBox QAbstractItemView::item:selected {"
            "background-color: #4FC3F7;"
            "}"
        )

        # 主布局 - 使用水平布局
        controls_layout = QHBoxLayout(self.controls_bar)
        controls_layout.setContentsMargins(20, 0, 20, 0)
        controls_layout.setSpacing(0)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 获取图标路径
        icon_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "icons"
        )

        # 加载白色图标
        icon_play_path = os.path.join(icon_dir, "play.svg")
        icon_pause_path = os.path.join(icon_dir, "pause.svg")
        icon_fullscreen_path = os.path.join(icon_dir, "fullscreen.svg")

        self.icon_play = load_svg_icon(icon_play_path, 20, "#FFFFFF")
        self.icon_pause = load_svg_icon(icon_pause_path, 20, "#FFFFFF")
        self.icon_fullscreen = load_svg_icon(icon_fullscreen_path, 18, "#FFFFFF")

        # 播放/暂停按钮 - 高亮背景，醒目设计
        self.play_button = QPushButton()
        self.play_button.setFixedSize(36, 36)
        self.play_button.setIconSize(QSize(20, 20))
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.setStyleSheet(
            "QPushButton {"
            "background-color: #4FC3F7;"
            "border-radius: 18px;"
            "}"
            "QPushButton:hover {"
            "background-color: #29B6F6;"
            "}"
            "QPushButton:pressed {"
            "background-color: #039BE5;"
            "}"
        )
        controls_layout.addWidget(self.play_button, 0, Qt.AlignmentFlag.AlignVCenter)

        # 固定间距
        controls_layout.addSpacing(16)

        # 时间标签 - 紧凑样式
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setFixedWidth(100)
        self.time_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self.time_label.setStyleSheet(
            "color: rgba(255, 255, 255, 200); font-size: 12px;"
        )
        controls_layout.addWidget(self.time_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # 固定间距
        controls_layout.addSpacing(16)

        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.progress_slider.setFixedHeight(32)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(
            self.progress_slider, 1, Qt.AlignmentFlag.AlignVCenter
        )

        # 固定间距
        controls_layout.addSpacing(16)

        # 倍速下拉框 - 紧凑设计
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFixedSize(58, 30)
        self.speed_combo.view().setMinimumWidth(96)
        self.speed_combo.view().setTextElideMode(Qt.TextElideMode.ElideNone)
        self.speed_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.speed_combo, 0, Qt.AlignmentFlag.AlignVCenter)

        # 固定间距
        controls_layout.addSpacing(12)

        # 全屏按钮
        self.fullscreen_button = QPushButton()
        self.fullscreen_button.setFixedSize(32, 32)
        self.fullscreen_button.setIconSize(QSize(18, 18))
        self.fullscreen_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fullscreen_button.setIcon(self.icon_fullscreen)
        self.fullscreen_button.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(255, 255, 255, 10);"
            "border-radius: 16px;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(255, 255, 255, 20);"
            "}"
        )
        controls_layout.addWidget(
            self.fullscreen_button, 0, Qt.AlignmentFlag.AlignVCenter
        )

        # 水平居中容器 - 包装 controls_bar
        center_container = QWidget()
        center_container.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, False
        )
        center_container.setStyleSheet("background: transparent; border: none;")
        center_layout = QHBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addStretch(1)
        center_layout.addWidget(self.controls_bar, 0, Qt.AlignmentFlag.AlignHCenter)
        center_layout.addStretch(1)

        overlay_layout.addWidget(center_container)

        # 打开视频文件
        print(f"[PLAYER] 使用OpenCV打开视频...")
        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            print(f"[PLAYER ERROR] OpenCV无法打开视频")
            QMessageBox.critical(
                self,
                t("common.error", "错误"),
                t("video_player_window.error.open_failed", "无法打开视频文件:\n{path}").format(path=video_path),
            )
            return

        # 获取视频信息
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0:
            self.fps = 30
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"[PLAYER] 视频信息:")
        print(f"[PLAYER]   - 分辨率: {self.frame_width}x{self.frame_height}")
        print(f"[PLAYER]   - 帧率: {self.fps} FPS")
        print(f"[PLAYER]   - 总帧数: {self.total_frames}")
        print(f"[PLAYER]   - 时长: {self.total_frames / self.fps:.1f} 秒")

        # 调整窗口大小以适应视频
        self.adjust_window_size()

        # 创建定时器用于播放
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        # 根据帧率设置定时器间隔
        interval = int(1000 / self.fps) if self.fps > 0 else 33  # 默认30fps
        self.timer.start(interval)

        # 初始化控件状态
        self.progress_slider.setRange(0, max(self.total_frames - 1, 0))
        self.update_time_label()
        self.update_play_button()

        # 绑定控件事件
        self.play_button.clicked.connect(self.toggle_play)
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        self.progress_slider.sliderPressed.connect(self.on_seek_start)
        self.progress_slider.sliderReleased.connect(self.on_seek_end)
        self.progress_slider.valueChanged.connect(self.on_seek_change)
        self.speed_combo.currentTextChanged.connect(self.on_speed_change)

        print(f"[PLAYER] 播放器初始化完成，开始播放")
        print(f"[PLAYER] ==========================================\n")

    def adjust_window_size(self):
        """调整窗口大小以适应视频"""
        # 计算合适的窗口大小（保持宽高比）
        max_width = 1280
        max_height = 720

        aspect_ratio = (
            self.frame_width / self.frame_height if self.frame_height > 0 else 16 / 9
        )

        if aspect_ratio > max_width / max_height:
            # 横屏视频，以宽度为准
            window_width = min(self.frame_width, max_width)
            window_height = int(window_width / aspect_ratio)
        else:
            # 竖屏视频，以高度为准
            window_height = min(self.frame_height, max_height)
            window_width = int(window_height * aspect_ratio)

        self.setGeometry(100, 100, window_width, window_height)
        self.normal_geometry = self.geometry()
        print(f"[PLAYER] 窗口大小: {window_width}x{window_height}")

    def update_frame(self):
        """更新视频帧"""
        if not self.is_playing:
            return

        ret, frame = self.cap.read()

        if not ret:
            # 视频播放结束，循环播放
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

            if not ret:
                return

        self.current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

        # 转换BGR到RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 转换为QImage
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        # 修复：使用tobytes()转换numpy数组
        q_image = QImage(
            frame_rgb.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888
        )

        # 获取当前窗口大小
        window_size = self.video_label.size()

        # 缩放图像以适应窗口，保持宽高比
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            window_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 显示图像
        self.video_label.setPixmap(scaled_pixmap)

        if not self.is_seeking:
            self.progress_slider.setValue(self.current_frame)
        self.update_time_label()

    def toggle_play(self):
        """播放/暂停切换"""
        self.is_playing = not self.is_playing
        self.update_play_button()
        print(f"[PLAYER] {'播放' if self.is_playing else '暂停'}")

    def update_play_button(self):
        """更新播放按钮图标"""
        if self.is_playing:
            self.play_button.setIcon(self.icon_pause)
        else:
            self.play_button.setIcon(self.icon_play)

    def on_seek_start(self):
        self.is_seeking = True

    def on_seek_change(self, value: int):
        if self.is_seeking:
            self.current_frame = value
            self.update_time_label()

    def on_seek_end(self):
        self.is_seeking = False
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.progress_slider.value())

    def on_speed_change(self, speed_text: str):
        """倍速变化处理"""
        self.playback_speed = float(speed_text.replace("x", ""))
        interval = int(1000 / (self.fps * self.playback_speed)) if self.fps > 0 else 33
        self.timer.setInterval(interval)
        print(f"[PLAYER] 倍速设置为: {self.playback_speed}x")

    def update_time_label(self):
        total_seconds = self.total_frames / self.fps if self.fps > 0 else 0
        current_seconds = self.current_frame / self.fps if self.fps > 0 else 0
        self.time_label.setText(
            f"{self.format_time(current_seconds)} / {self.format_time(total_seconds)}"
        )

    @staticmethod
    def format_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def toggle_fullscreen(self):
        """切换全屏"""
        if self.is_fullscreen:
            self.showNormal()
            if self.normal_geometry:
                self.setGeometry(self.normal_geometry)
            self.is_fullscreen = False
            print(f"[PLAYER] 退出全屏")
        else:
            self.normal_geometry = self.geometry()
            self.showFullScreen()
            self.is_fullscreen = True
            print(f"[PLAYER] 进入全屏")

    def resizeEvent(self, event):
        """窗口大小改变时调整控件栏宽度"""
        super().resizeEvent(event)
        if hasattr(self, "controls_bar"):
            # 获取视频标签的宽度（实际显示区域）
            video_width = self.video_label.width()
            # 计算控件栏的合适宽度（减去边距）
            margin = 32
            target_width = max(320, min(video_width - margin, 600))
            self.controls_bar.setMaximumWidth(target_width)
            self.controls_bar.setMinimumWidth(min(320, target_width))

    def keyPressEvent(self, event):
        """键盘事件处理"""
        if event.key() == Qt.Key.Key_Escape and self.is_fullscreen:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_F or event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Space:
            # 空格键暂停/播放
            self.toggle_play()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """关闭事件"""
        print(f"[PLAYER] 关闭播放器")
        try:
            if hasattr(self, "timer"):
                self.timer.stop()
            if hasattr(self, "cap"):
                self.cap.release()
        except:
            pass
        event.accept()
