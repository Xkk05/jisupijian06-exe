"""
视频预览播放器
支持10秒视频预览、播放控制、进度条
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt6.QtGui import QImage, QPixmap
from ui.components import load_svg_icon
from ui.i18n import apply_language_to_widget, get_language_manager, t
import cv2
import numpy as np
from typing import Optional, List, Tuple
import os
import random
from pathlib import Path
from utils.enum_codes import (
    normalize_text_animation_type,
    normalize_text_arrange,
    normalize_text_position,
    normalize_video_ref,
)


class VideoPreviewPlayer(QDialog):
    """视频预览播放器对话框"""
    
    def __init__(self, video_path: str, watermark_configs: list = None, duration: int = 10, parent=None, description: str = None):
        """
        Args:
            video_path: 视频文件路径
            watermark_configs: 水印配置列表
            duration: 预览时长（秒）
            parent: 父窗口
            description: 预览描述HTML文本，如果提供将优先显示
        """
        super().__init__(parent)
        self.video_path = video_path
        self.watermark_configs = watermark_configs or []
        self.duration = duration
        self.description = description
        
        self.cap = None
        self.timer = QTimer()
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self.frame_buffer = []  # 缓存帧
        self._language_manager = get_language_manager()
        
        self.init_ui()
        self._language_manager.language_changed.connect(self._on_language_changed)
        self._on_language_changed(self._language_manager.language)
        self._prepare_preview_watermarks()
        self.load_video()

    def _on_language_changed(self, _lang: str) -> None:
        apply_language_to_widget(self)
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(t("video_preview_player.title", "视频预览播放器"))
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: #1E1E1E;")
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 视频容器 (使用GridLayout实现Overlay效果)
        from PyQt6.QtWidgets import QGridLayout, QFrame
        self.video_container = QFrame()
        self.video_container.setStyleSheet("background-color: #000000;")
        video_layout = QGridLayout(self.video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.setSpacing(0)
        
        # 视频显示区域
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background: transparent;")
        self.video_label.setMinimumHeight(400)
        # 允许鼠标点击
        self.video_label.setMouseTracking(True)
        self.video_label.installEventFilter(self)
        
        # 信息浮层 (Overlay)
        self.info_label = QLabel()
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150);
                color: rgba(255, 255, 255, 200);
                padding: 8px;
                border-bottom-right-radius: 8px;
                font-family: 'Consolas', 'Microsoft YaHei';
                font-size: 12px;
            }
        """)
        self.info_label.setVisible(False)  # 默认隐藏，悬停显示（计划中提到“仅在鼠标悬停在窗口内时显示”或作为水印，这里先实现为Overlay）
        # 既然Plan说"仅在鼠标悬停...时显示"，我们先默认显示或者一直显示？
        # Plan: "将“分辨率、帧率、时长”等技术参数...显示在视频左上角（仅在鼠标悬停时显示）"
        # 为了简单体验，我可以先设置为一直显示，或者实现enterEvent/leaveEvent控制。
        # 这里先设置为一直显示比较稳妥，用户随时能看到参数。
        self.info_label.setVisible(True)
        
        # 将控件加入Grid，实现堆叠
        # addWidget(widget, row, col, rowSpan, colSpan, alignment)
        video_layout.addWidget(self.video_label, 0, 0)
        video_layout.addWidget(self.info_label, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(self.video_container, 1)  # 视频区域占据主要空间
        
        # 底部控制栏
        control_panel = QFrame()
        control_panel.setFixedHeight(60)
        control_panel.setStyleSheet("""
            QFrame {
                background-color: #2D2D30;
                border-top: 1px solid #3E3E42;
            }
        """)
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(20, 0, 20, 0)
        control_layout.setSpacing(15)
        
        # 播放/暂停按钮 (图标)
        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(32, 32)
        self.play_btn.setIcon(load_svg_icon("play", 20, "#FFFFFF"))
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 30);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 50);
            }
        """)
        self.play_btn.clicked.connect(self.toggle_play)
        control_layout.addWidget(self.play_btn)
        
        # 当前时间
        self.time_label = QLabel("00:00")
        self.time_label.setStyleSheet("QLabel { font-size: 12px; color: #E0E0E0; font-family: 'Consolas'; }")
        control_layout.addWidget(self.time_label)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setMinimum(0)
        self.progress_slider.setMaximum(100)
        self.progress_slider.setValue(0)
        self.progress_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.progress_slider.setStyleSheet("""
            QSlider {
                background: transparent;
                height: 30px;
            }
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #4A4A4A;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #6366F1;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: none;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::handle:horizontal:hover {
                background: #FFFFFF;
                width: 14px;
                height: 14px;
            }
        """)
        self.progress_slider.sliderPressed.connect(self.on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_slider_released)
        control_layout.addWidget(self.progress_slider, 1)
        
        # 总时长
        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("QLabel { font-size: 12px; color: #E0E0E0; font-family: 'Consolas'; }")
        control_layout.addWidget(self.duration_label)
        
        layout.addWidget(control_panel)
        
        # 定时器
        self.timer.timeout.connect(self.update_frame)

    def eventFilter(self, obj, event):
        """事件过滤器：处理视频区域点击"""
        if obj == self.video_label and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.toggle_play()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """键盘快捷键"""
        key = event.key()
        if key == Qt.Key.Key_Space:
            self.toggle_play()
        elif key == Qt.Key.Key_Left:
            # 快退 1秒
            self._seek_relative(-1.0)
        elif key == Qt.Key.Key_Right:
            # 快进 1秒
            self._seek_relative(1.0)
        elif key == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def _seek_relative(self, seconds):
        """相对跳转"""
        if not self.frame_buffer:
            return
            
        frames_to_move = int(seconds * self.fps)
        new_frame = self.current_frame + frames_to_move
        new_frame = max(0, min(new_frame, len(self.frame_buffer) - 1))
        
        self.current_frame = new_frame
        self.display_frame(self.frame_buffer[self.current_frame])
        self.update_progress()


    
    def _prepare_preview_watermarks(self):
        """预处理水印配置，解析预览所需资源"""
        for config in self.watermark_configs:
            if config.get('type') == 'image':
                candidates = config.get('file_candidates') or []
                if not candidates and config.get('file_path'):
                    candidates = [config['file_path']]
                
                candidates = [
                    os.path.abspath(path)
                    for path in candidates
                    if path and os.path.exists(path)
                ]
                
                if not candidates:
                    config['_preview_source'] = None
                    continue
                
                if config.get('random_select') and len(candidates) > 1:
                    config['_preview_source'] = random.choice(candidates)
                else:
                    config['_preview_source'] = candidates[0]
            else:
                config['_preview_source'] = None
    
    def _compute_image_size(self, config: dict, watermark: np.ndarray, frame_w: int, frame_h: int) -> Tuple[int, int]:
        """根据配置计算水印尺寸"""
        wm_h, wm_w = watermark.shape[:2]
        
        if config.get('custom_width') and config.get('custom_height'):
            return max(1, int(config['custom_width'])), max(1, int(config['custom_height']))
        
        style = config.get('style_config', {})
        size_cfg = style.get('size', {}) if style else {}
        mode = size_cfg.get('mode')
        
        if mode == 'custom':
            width = size_cfg.get('width', wm_w)
            height = size_cfg.get('height', wm_h)
            return max(1, int(width)), max(1, int(height))
        elif mode == 'ratio':
            scale = size_cfg.get('scale', 100) / 100.0
            return max(1, int(wm_w * scale)), max(1, int(wm_h * scale))
        elif mode == 'video':
            ratio = size_cfg.get('video_ratio', 15) / 100.0
            ref = normalize_video_ref(size_cfg.get('video_ref', 'height'))
            if ref == 'height':
                target_h = frame_h * ratio
                scale = target_h / max(1, wm_h)
            elif ref == 'width':
                target_w = frame_w * ratio
                scale = target_w / max(1, wm_w)
            else:  # 对角
                diag_video = (frame_w ** 2 + frame_h ** 2) ** 0.5
                diag_wm = (wm_w ** 2 + wm_h ** 2) ** 0.5
                scale = (diag_video * ratio) / max(1, diag_wm)
            return max(1, int(wm_w * scale)), max(1, int(wm_h * scale))
        
        return wm_w, wm_h
    
    def _calculate_watermark_positions(
        self,
        config: dict,
        frame_w: int,
        frame_h: int,
        wm_w: int,
        wm_h: int,
        frame_index: int
    ) -> List[Tuple[int, int]]:
        """计算水印绘制位置，支持滚动与对角铺设"""
        preset = normalize_text_position(config.get('position', 'top_right'))
        offset_x = config.get('offset_x', 0)
        offset_y = config.get('offset_y', 0)
        custom_pos = config.get('custom_position')
        
        if preset == 'custom' and custom_pos:
            base_x, base_y = custom_pos
        else:
            mapping = {
                'top_left': (offset_x, offset_y),
                'top_right': (frame_w - wm_w - offset_x, offset_y),
                'bottom_left': (offset_x, frame_h - wm_h - offset_y),
                'bottom_right': (frame_w - wm_w - offset_x, frame_h - wm_h - offset_y),
                'center': ((frame_w - wm_w) // 2 + offset_x, (frame_h - wm_h) // 2 + offset_y),
            }
            base_x, base_y = mapping.get(preset, mapping['top_right'])
        
        # 滚动效果 （默认水平方向）
        if config.get('scroll'):
            style = config.get('style_config', {})
            speed = style.get('scroll_speed', 40)
            direction = style.get('scroll_direction', 'horizontal')
            elapsed = frame_index / max(self.fps, 1)
            distance = int(elapsed * speed)
            if direction == 'vertical':
                base_y = (base_y + distance) % (frame_h + wm_h) - wm_h
            else:  # horizontal
                base_x = (base_x + distance) % (frame_w + wm_w) - wm_w
        
        positions = [(base_x, base_y)]
        
        if config.get('diagonal'):
            step = max(wm_w, wm_h)
            diag_positions = []
            for delta in range(-3, 4):
                if delta == 0:
                    continue
                nx = base_x + delta * step
                ny = base_y + delta * step
                diag_positions.append((nx, ny))
            positions.extend(diag_positions)
        
        clamped_positions = []
        for x, y in positions:
            x = max(-wm_w, min(frame_w, int(x)))
            y = max(-wm_h, min(frame_h, int(y)))
            if x >= frame_w or y >= frame_h or x + wm_w <= 0 or y + wm_h <= 0:
                continue
            clamped_positions.append((x, y))
        
        return clamped_positions or [(max(0, min(frame_w - wm_w, base_x)), max(0, min(frame_h - wm_h, base_y)))]
    
    def _overlay_image(
        self,
        frame: np.ndarray,
        watermark: np.ndarray,
        x: int,
        y: int,
        opacity: float
    ) -> np.ndarray:
        """在指定位置叠加图片水印"""
        wm_h, wm_w = watermark.shape[:2]
        frame_h, frame_w = frame.shape[:2]
        
        start_x = max(0, x)
        start_y = max(0, y)
        end_x = min(frame_w, x + wm_w)
        end_y = min(frame_h, y + wm_h)
        
        wm_start_x = max(0, -x)
        wm_start_y = max(0, -y)
        wm_end_x = wm_start_x + (end_x - start_x)
        wm_end_y = wm_start_y + (end_y - start_y)
        
        if start_x >= end_x or start_y >= end_y:
            return frame
        
        overlay = watermark[wm_start_y:wm_end_y, wm_start_x:wm_end_x]
        
        if overlay.shape[2] == 4:
            alpha = overlay[:, :, 3].astype(np.float32) / 255.0
            overlay_rgb = overlay[:, :, :3]
        else:
            alpha = np.ones((overlay.shape[0], overlay.shape[1]), dtype=np.float32)
            overlay_rgb = overlay[:, :, :3]
        
        alpha = np.clip(alpha * opacity, 0.0, 1.0)
        alpha_stack = np.dstack([alpha] * 3)
        
        roi = frame[start_y:end_y, start_x:end_x].astype(np.float32)
        blended = roi * (1 - alpha_stack) + overlay_rgb.astype(np.float32) * alpha_stack
        frame[start_y:end_y, start_x:end_x] = blended.astype(np.uint8)
        return frame
    
    def _get_font(self, font_config: dict, font_size: int):
        """根据配置获取字体（优先使用明确路径）"""
        from PIL import ImageFont
        
        # 优先使用明确的字体文件路径
        font_path = font_config.get('path')
        if font_path and os.path.isfile(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception:
                pass
        
        # 回退到字体族名解析
        family = font_config.get('family', 'Microsoft YaHei')
        bold = font_config.get('bold', False)
        italic = font_config.get('italic', False)
        
        font_paths = []
        system_root = Path(os.environ.get("WINDIR", "C:\\Windows"))
        fonts_dir = system_root / "Fonts"
        
        if 'YaHei' in family or '微软雅黑' in family:
            font_paths.append(fonts_dir / "msyh.ttc")
            font_paths.append(fonts_dir / "msyhbd.ttc")
        candidate_name = family.replace(" ", "")
        font_paths.append(fonts_dir / f"{candidate_name}.ttf")
        font_paths.append(fonts_dir / f"{candidate_name}.ttc")
        font_paths.append(fonts_dir / "arial.ttf")
        
        for path in font_paths:
            try:
                if path.exists():
                    return ImageFont.truetype(str(path), font_size)
            except Exception:
                continue
        
        return ImageFont.load_default()
    
    def _hex_to_rgba(self, color: str, opacity: float) -> Tuple[int, int, int, int]:
        """将十六进制颜色转换为RGBA"""
        color = (color or "#FFFFFF").lstrip('#')
        if len(color) == 3:
            color = ''.join(ch * 2 for ch in color)
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
        except ValueError:
            r, g, b = 255, 255, 255
        a = int(max(0.0, min(1.0, opacity)) * 255)
        return (r, g, b, a)
    
    def load_video(self):
        """加载视频"""
        try:
            if not os.path.exists(self.video_path):
                QMessageBox.critical(
                    self,
                    t("common.error", "错误"),
                    t("video_preview_player.error.file_not_found", "视频文件不存在！"),
                )
                return
            
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                QMessageBox.critical(
                    self,
                    t("common.error", "错误"),
                    t("video_preview_player.error.open_failed", "无法打开视频文件！"),
                )
                return
            
            # 获取视频信息
            self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
            if self.fps <= 0:
                self.fps = 30
            
            total_frames_in_video = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            max_frames = self.fps * self.duration
            self.total_frames = min(total_frames_in_video, max_frames)
            
            video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 更新信息标签
            
            # 如果有传入的描述，优先显示描述
            if self.description:
                details_html = self.description
            else:
                watermark_count = len(self.watermark_configs)
                
                # 生成预览详情文本
                preview_details = []
                
                # 1. 检查水印配置
                if self.watermark_configs:
                    for idx, cfg in enumerate(self.watermark_configs[:3]):  # 最多显示前3个
                        w_type = (
                            t("video_preview_player.detail.type.image", "图片")
                            if cfg.get('type') == 'image'
                            else t("video_preview_player.detail.type.text", "文字")
                        )
                        w_content = ""
                        if cfg.get('type') == 'text':
                            content = cfg.get('text_content', '')
                            w_content = f": {content[:10]}..." if len(content) > 10 else f": {content}"
                        elif cfg.get('type') == 'image':
                            path = cfg.get('file_path', '')
                            filename = os.path.basename(path)
                            w_content = f": {filename}"
                        preview_details.append(
                            t(
                                "video_preview_player.detail.watermark_item",
                                "• 水印{index} [{type}]{content}",
                            ).format(index=idx + 1, type=w_type, content=w_content)
                        )
                    
                    if len(self.watermark_configs) > 3:
                        preview_details.append(
                            t(
                                "video_preview_player.detail.more_count",
                                "...等共{count}个水印",
                            ).format(count=watermark_count)
                        )
                else:
                    preview_details.append(t("video_preview_player.detail.original_preview", "• 原画预览"))

                # 2. 检查是否有裁剪等其他效果 (预留接口，目前根据水印判断)
                # if hasattr(self, 'crop_config'): ...
                
                details_html = "<br>".join(preview_details)
            
            self.info_label.setText(
                f"""
                <div style='line-height: 1.5;'>
                    <span style='font-size: 14px; font-weight: bold; color: white;'>{t("common.btn.preview", "预览效果")}</span> 
                    <span style='color: #AAA; font-size: 11px;'>@ {self.fps}fps</span><br>
                    <span style='color: #CCC; font-size: 11px;'>{video_width}×{video_height} | {self.duration}s</span><br>
                    <div style='margin-top: 4px; padding-top: 4px; border-top: 1px solid rgba(255,255,255,50); font-size: 11px; color: #DDD;'>
                        {details_html}
                    </div>
                </div>
                """
            )
            
            # 更新时长标签
            duration_str = self.format_time(self.total_frames / self.fps)
            self.duration_label.setText(duration_str)
            
            # 预加载帧（带水印）
            self.preload_frames()
            
            # 显示第一帧
            if self.frame_buffer:
                self.display_frame(self.frame_buffer[0])
            
        except Exception as e:
            QMessageBox.critical(
                self,
                t("common.error", "错误"),
                t("video_preview_player.error.load_failed", "加载视频失败：{error}").format(error=str(e)),
            )
            import traceback
            traceback.print_exc()
    
    def preload_frames(self):
        """预加载帧并应用水印"""
        from PyQt6.QtWidgets import QProgressDialog
        
        progress = QProgressDialog(
            t("video_preview_player.progress.generating", "正在生成预览..."),
            t("common.btn.cancel", "取消"),
            0,
            self.total_frames,
            self,
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(500)
        
        self.frame_buffer = []
        
        for i in range(self.total_frames):
            if progress.wasCanceled():
                break
            
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # 应用水印
            if self.watermark_configs:
                frame = self.apply_watermarks(frame, i)
            
            self.frame_buffer.append(frame)
            progress.setValue(i + 1)
        
        progress.close()
        
        # 重置cap到开始
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    def apply_watermarks(self, frame, frame_index: int):
        """应用所有水印到帧"""
        for config in self.watermark_configs:
            try:
                if config.get('type') == 'image':
                    frame = self.apply_image_watermark(frame, config, frame_index)
                elif config.get('type') == 'text':
                    frame = self.apply_text_watermark(frame, config, frame_index)
            except Exception as e:
                print(f"应用水印失败: {e}")
        
        return frame
    
    def _imread_unicode(self, filepath: str):
        """安全读取包含Unicode路径的图片"""
        try:
            with open(filepath, 'rb') as f:
                file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
            return cv2.imdecode(file_bytes, cv2.IMREAD_UNCHANGED)
        except Exception as e:
            print(f"读取图片失败 {filepath}: {e}")
            return None
    
    def apply_image_watermark(self, frame, config, frame_index: int):
        """应用图片水印"""
        source_path = config.get('_preview_source') or config.get('file_path', '')
        if not source_path or not os.path.exists(source_path):
            return frame
        
        watermark = self._imread_unicode(source_path)
        if watermark is None:
            return frame
        
        frame_h, frame_w = frame.shape[:2]
        target_w, target_h = self._compute_image_size(config, watermark, frame_w, frame_h)
        if (target_w, target_h) != (watermark.shape[1], watermark.shape[0]):
            watermark = cv2.resize(watermark, (target_w, target_h), interpolation=cv2.INTER_AREA)
        
        positions = self._calculate_watermark_positions(
            config,
            frame_w,
            frame_h,
            watermark.shape[1],
            watermark.shape[0],
            frame_index
        )
        
        opacity = float(config.get('opacity', 1.0))
        for x, y in positions:
            frame = self._overlay_image(frame, watermark, x, y, opacity)
        
        return frame
    
    def apply_text_watermark(self, frame, config, frame_index: int = 0):
        """应用文字水印（支持样式配置）"""
        from PIL import Image, ImageDraw
        
        text = config.get('text_content', '')
        if not text.strip():
            return frame
        
        style = config.get('style_config', {})
        dynamic = style.get('dynamic', {})
        text = self._compose_dynamic_text(text, dynamic, frame_index)
        text = self._apply_text_arrange(text, style)

        font_cfg = style.get('font', {})
        font_size = font_cfg.get('size', 36)
        font = self._get_font(font_cfg, font_size)
        
        stroke_cfg = style.get('stroke', {})
        shadow_cfg = style.get('shadow', {})
        background_cfg = style.get('background', {})
        
        stroke_enabled = stroke_cfg.get('enabled', stroke_cfg.get('width', 0) > 0)
        stroke_width = int(stroke_cfg.get('width', 0)) if stroke_enabled else 0
        stroke_color = self._hex_to_rgba(stroke_cfg.get('color', '#000000'), 1.0)
        
        base_opacity = config.get('text_opacity', style.get('opacity', 1.0))
        fill_color = self._hex_to_rgba(style.get('color', '#FFFFFF'), base_opacity)
        shadow_enabled = shadow_cfg.get('enabled', (shadow_cfg.get('x', 0) != 0 or shadow_cfg.get('y', 0) != 0))
        shadow_color = self._hex_to_rgba(shadow_cfg.get('color', '#000000'), base_opacity * 0.6) if shadow_enabled else (0, 0, 0, 0)
        shadow_x = int(shadow_cfg.get('x', 0)) if shadow_enabled else 0
        shadow_y = int(shadow_cfg.get('y', 0)) if shadow_enabled else 0
        
        padding = int(background_cfg.get('padding', 8))
        background_enabled = background_cfg.get('enabled', background_cfg.get('color') not in (None, '', '#00000000'))
        box_color = self._hex_to_rgba(background_cfg.get('color', '#000000'), base_opacity * 0.3)
        draw_box = background_enabled and background_cfg.get('color') not in (None, '', '#00000000')
        
        # 计算文字尺寸（textbbox 返回实际边界）
        dummy_img = Image.new('RGBA', (10, 10))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        # bbox[1] 为负数时表示文字顶部超出基线，需额外空间
        top_offset = max(0, -bbox[1])
        
        overlay_width = text_w + padding * 2 + abs(shadow_x) + stroke_width * 2
        overlay_height = text_h + padding * 2 + abs(shadow_y) + stroke_width * 2 + top_offset
        
        overlay_img = Image.new('RGBA', (overlay_width, overlay_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay_img)
        
        if draw_box and box_color[3] > 0:
            overlay_draw.rectangle(
                [0, 0, overlay_width, overlay_height],
                fill=box_color
            )
        
        # 调整文字绘制位置：考虑 bbox top offset 和 padding
        text_x = padding + stroke_width
        text_y = padding + stroke_width + top_offset
        
        # 阴影
        if (shadow_x != 0 or shadow_y != 0) and shadow_color[3] > 0:
            overlay_draw.text(
                (text_x + max(0, shadow_x), text_y + max(0, shadow_y)),
                text,
                font=font,
                fill=shadow_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color
            )
        
        # 主文字
        overlay_draw.text(
            (text_x, text_y),
            text,
            font=font,
            fill=fill_color,
            stroke_width=stroke_width,
            stroke_fill=stroke_color
        )
        
        angle = style.get('angle', 0)
        if normalize_text_arrange(style.get('arrange')) == 'slanted' and not angle:
            angle = -15
        if angle:
            overlay_img = overlay_img.rotate(angle, expand=True, resample=Image.BICUBIC)
        
        overlay_np = cv2.cvtColor(np.array(overlay_img), cv2.COLOR_RGBA2BGRA)
        frame_h, frame_w = frame.shape[:2]
        
        temp_config = {
            'position': config.get('text_position', config.get('position', 'top_right')),
            'offset_x': 0,
            'offset_y': 0,
            'custom_position': config.get('custom_position'),
            'scroll': False,
            'diagonal': False
        }
        animation_cfg = style.get('animation', {})
        if normalize_text_animation_type(animation_cfg.get('type')) == 'scroll':
            temp_config['scroll'] = True
            speed = float(animation_cfg.get('speed', 1.0))
            style['scroll_speed'] = max(10.0, 40.0 * speed)
            if normalize_text_arrange(style.get('arrange')) == 'vertical':
                style['scroll_direction'] = 'vertical'
        
        positions = self._calculate_watermark_positions(
            temp_config,
            frame_w,
            frame_h,
            overlay_np.shape[1],
            overlay_np.shape[0],
            0
        )
        
        overlay_np[:, :, 3] = np.clip(overlay_np[:, :, 3].astype(np.float32), 0, 255).astype(np.uint8)

        # 淡入淡出动画（预览）
        if normalize_text_animation_type(animation_cfg.get('type')) == 'fade_in_out':
            speed = float(animation_cfg.get('speed', 1.0))
            fade_duration = max(0.5, min(3.0, 1.0 * speed))
            total_duration = max(1.0, self.total_frames / max(self.fps, 1))
            t = frame_index / max(self.fps, 1)
            if t < fade_duration:
                alpha_factor = t / fade_duration
            elif t > total_duration - fade_duration:
                alpha_factor = max(0.0, (total_duration - t) / fade_duration)
            else:
                alpha_factor = 1.0
            overlay_np[:, :, 3] = (overlay_np[:, :, 3].astype(np.float32) * alpha_factor).astype(np.uint8)
        
        for x, y in positions:
            frame = self._overlay_image(frame, overlay_np, x, y, 1.0)
        
        return frame

    def _compose_dynamic_text(self, base_text: str, dynamic_cfg: dict, frame_index: int) -> str:
        """拼接动态文字（时间戳/文件名/帧号）"""
        parts = [base_text] if base_text else []
        if dynamic_cfg.get('timestamp'):
            from datetime import datetime, timedelta
            t = frame_index / max(self.fps, 1)
            parts.append((datetime.now() + timedelta(seconds=t)).strftime("%Y-%m-%d %H:%M:%S"))
        if dynamic_cfg.get('filename') and self.video_path:
            parts.append(os.path.basename(self.video_path))
        if dynamic_cfg.get('frame_number'):
            parts.append(str(frame_index))
        return " ".join(p for p in parts if p)

    def _apply_text_arrange(self, text: str, style: dict) -> str:
        """应用文字排列（水平/垂直/倾斜）"""
        arrange = style.get('arrange')
        if arrange == '垂直':
            return "\n".join(list(text))
        return text
    
    def display_frame(self, frame):
        """显示帧"""
        if frame is None:
            return
        
        # 转换为QPixmap
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        q_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        # 缩放到合适大小
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        """窗口大小改变时重绘当前帧"""
        if self.frame_buffer and self.current_frame < len(self.frame_buffer):
            self.display_frame(self.frame_buffer[self.current_frame])
        super().resizeEvent(event)

    def toggle_play(self):
        """切换播放/暂停"""
        if self.is_playing:
            self.pause()
        else:
            # 如果播放结束，重置到开头
            if self.frame_buffer and self.current_frame >= len(self.frame_buffer) - 1:
                self.current_frame = 0
                self.display_frame(self.frame_buffer[0])
                self.update_progress()
            self.play()
    
    def play(self):
        """播放"""
        if not self.frame_buffer:
            return
        
        self.is_playing = True
        self.play_btn.setIcon(load_svg_icon("pause", 20, "#FFFFFF"))
        self.play_btn.setToolTip(t("video_preview_player.tooltip.pause", "暂停 (Space)"))
        
        interval = int(1000 / self.fps)
        self.timer.start(interval)
    
    def pause(self):
        """暂停"""
        self.is_playing = False
        self.play_btn.setIcon(load_svg_icon("play", 20, "#FFFFFF"))
        self.play_btn.setToolTip(t("video_preview_player.tooltip.play", "播放 (Space)"))
        self.timer.stop()
    
    def restart(self):
        """重新播放"""
        self.current_frame = 0
        if self.frame_buffer:
            self.display_frame(self.frame_buffer[0])
        self.update_progress()
        self.play()
    
    def update_frame(self):
        """更新帧"""
        if not self.frame_buffer:
            return
        
        if self.current_frame < len(self.frame_buffer) - 1:
            self.current_frame += 1
            self.display_frame(self.frame_buffer[self.current_frame])
            self.update_progress()
        else:
            # 播放结束
            self.pause()
            self.play_btn.setIcon(load_svg_icon("refresh", 20, "#FFFFFF"))
            self.play_btn.setToolTip(t("video_preview_player.tooltip.replay", "重新播放 (Space)"))

    
    def update_progress(self):
        """更新进度"""
        if self.total_frames > 0:
            progress = int((self.current_frame / self.total_frames) * 100)
            self.progress_slider.blockSignals(True)
            self.progress_slider.setValue(progress)
            self.progress_slider.blockSignals(False)
            
            current_time = self.current_frame / self.fps
            self.time_label.setText(self.format_time(current_time))
    
    def on_slider_pressed(self):
        """进度条按下"""
        if self.is_playing:
            self.timer.stop()
    
    def on_slider_released(self):
        """进度条释放"""
        if not self.frame_buffer:
            return
        
        progress = self.progress_slider.value()
        self.current_frame = int((progress / 100) * self.total_frames)
        self.current_frame = max(0, min(self.current_frame, len(self.frame_buffer) - 1))
        
        if self.current_frame < len(self.frame_buffer):
            self.display_frame(self.frame_buffer[self.current_frame])
        
        if self.is_playing:
            interval = int(1000 / self.fps)
            self.timer.start(interval)
    
    def format_time(self, seconds: float) -> str:
        """格式化时间"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def closeEvent(self, event):
        """关闭事件"""
        self.timer.stop()
        if self.cap:
            self.cap.release()
        event.accept()
