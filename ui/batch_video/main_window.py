"""
极速批剪 - 批量视频批量处理窗口
完整还原CR VideoMate批处理界面
"""

import sys
import os
import copy
import re

# ==================== UI显示优化配置 ====================
# 设置高DPI支持（解决UI模糊问题）
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR"] = "1"

# 添加项目根目录到Python路径
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.theme import Theme
from ui.i18n import apply_language_to_widget, get_language_manager, t
from ui.components import (
    load_svg_icon,
    ModernButton,
    ProgressStatus,
    ModernMessageBox,
    ModernInput,
)
from ui.window_controls import TitleBar
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QRadioButton,
    QTextEdit,
    QFileDialog,
    QTabWidget,
    QGridLayout,
    QButtonGroup,
    QProgressBar,
    QMessageBox,
    QSlider,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QGraphicsDropShadowEffect,
    QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QRect, QEvent
from PyQt6.QtGui import (
    QFont,
    QAction,
    QIcon,
    QPixmap,
    QPalette,
    QBrush,
    QCursor,
    QColor,
)
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set


from ui.border_style_dialog import BorderStyleDialog
from utils.unified_logger import logger
from utils.icon_utils import load_logo_pixmap
from utils.enum_codes import (
    CROP_MODE_LABELS,
    CROP_PERCENT_POSITION_LABELS,
    LANG_EN,
    LANG_ZH,
    RESOLUTION_PRESET_LABELS,
    STATUS_LABELS,
    TEXT_SOURCE_MODE_LABELS,
    TRIM_MODE_LABELS,
    GRID_DIRECTION_LABELS,
    WATERMARK_PRESET_LABELS,
    enum_label,
    normalize_crop_mode,
    normalize_crop_percent_position,
    normalize_grid_direction,
    normalize_resolution_preset,
    normalize_status_code,
    normalize_text_source_mode,
    normalize_trim_mode,
    normalize_watermark_preset,
)


class VideoProcessThread(QThread):
    """视频批量处理线程"""

    progress_updated = pyqtSignal(int, str)  # (进度, 消息)
    video_status_updated = pyqtSignal(int, str)  # (行号, 状态)
    finished = pyqtSignal()

    def __init__(self, video_list: List[Dict], config: Dict):
        super().__init__()
        self.video_list = video_list
        self.config = config
        self.is_running = True
        self.batch_output_dir = None
        self.batch_folder_name = None

    def run(self):
        """执行批量处理"""
        import os
        import copy
        import threading
        from datetime import datetime
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from processor.batch_params_processor import BatchParamsProcessor

        total = len(self.video_list)
        if total == 0:
            self.progress_updated.emit(100, t("batch.progress.all_done", "全部处理完成"))
            self.finished.emit()
            return

        global_options = self.config.get("global_options", {})
        parallel_tasks = int(global_options.get("parallel_tasks", 1) or 1)
        parallel_tasks = max(1, parallel_tasks)

        output_config = self.config.get("output", {})
        output_dir = output_config.get("path", "")
        if global_options.get("output_to_folder"):
            self.batch_folder_name = datetime.now().strftime("batch_%Y%m%d_%H%M%S")
            self.batch_output_dir = os.path.join(output_dir, self.batch_folder_name)
        else:
            self.batch_output_dir = output_dir

        progress_lock = threading.Lock()
        progress_map = {idx: 0 for idx in range(total)}

        def update_overall(message: str):
            with progress_lock:
                total_progress = sum(progress_map.values()) / total
            self.progress_updated.emit(int(total_progress), message)

        def handle_progress(idx: int, progress: float, message: str):
            with progress_lock:
                progress_map[idx] = progress
            update_overall(message)

        def process_single(idx: int, video_info: Dict):
            if not self.is_running:
                return
            video_path = video_info["path"]
            self.video_status_updated.emit(idx, "processing")
            update_overall(
                t(
                    "batch.progress.processing_file",
                    "正在处理: {name}",
                    name=os.path.basename(video_path),
                )
            )

            try:
                output_path, skip = self._build_output_path(video_info, idx)
                video_info["output_path"] = output_path
                if skip:
                    self.video_status_updated.emit(idx, "skipped")
                    handle_progress(
                        idx,
                        100,
                        t(
                            "batch.progress.skipped_file",
                            "已跳过: {name}",
                            name=os.path.basename(video_path),
                        ),
                    )
                    return

                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                processor = BatchParamsProcessor(copy.deepcopy(self.config))
                success = processor.process_video(
                    video_path,
                    output_path,
                    variant=idx,
                    progress_callback=lambda p, m: handle_progress(idx, p, m),
                )

                if success:
                    self.video_status_updated.emit(idx, "done")
                    handle_progress(
                        idx,
                        100,
                        t(
                            "batch.progress.done_file",
                            "完成: {name}",
                            name=os.path.basename(video_path),
                        ),
                    )
                else:
                    self.video_status_updated.emit(idx, "failed")
                    handle_progress(
                        idx,
                        100,
                        t(
                            "batch.progress.failed_file",
                            "失败: {name}",
                            name=os.path.basename(video_path),
                        ),
                    )
            except Exception as e:
                logger.error(f"处理视频失败: {e}")
                self.video_status_updated.emit(idx, f"error:{str(e)}")
                handle_progress(
                    idx,
                    100,
                    t(
                        "batch.progress.error_file",
                        "错误: {name}",
                        name=os.path.basename(video_path),
                    ),
                )

        with ThreadPoolExecutor(max_workers=parallel_tasks) as executor:
            futures = [
                executor.submit(process_single, idx, video_info)
                for idx, video_info in enumerate(self.video_list)
            ]
            for _ in as_completed(futures):
                if not self.is_running:
                    break

        self.progress_updated.emit(100, t("batch.progress.all_done", "全部处理完成"))
        self.finished.emit()

    def stop(self):
        """停止处理"""
        self.is_running = False

    def _get_output_filename(self, video_path: str, index: int) -> str:
        import os
        import re

        global_options = self.config.get("global_options", {})
        base_name, ext = os.path.splitext(os.path.basename(video_path))
        target_format = global_options.get("target_format", "mp4")
        if target_format == "mp4":
            ext = ".mp4"

        if global_options.get("filename_remove_enabled"):
            pattern = global_options.get("filename_remove_text", "")
            if global_options.get("filename_remove_regex"):
                try:
                    compiled = self._get_compiled_pattern(pattern)
                    base_name = compiled.sub("", base_name)
                except re.error:
                    base_name = base_name
            else:
                for token in pattern.split("|"):
                    token = token.strip()
                    if token:
                        base_name = base_name.replace(token, "")
            base_name = base_name.strip() or "video"

        if global_options.get("filename_add_number"):
            base_name = f"{index + 1:03d}_{base_name}"

        return f"{base_name}{ext}"

    def _ensure_unique_path(self, output_path: str) -> str:
        import os

        base, ext = os.path.splitext(output_path)
        counter = 1
        unique_path = output_path
        while os.path.exists(unique_path):
            unique_path = f"{base}_{counter}{ext}"
            counter += 1
        return unique_path

    def _build_output_path(self, video_info: Dict, index: int) -> Tuple[str, bool]:
        import os

        output_config = self.config.get("output", {})
        global_options = self.config.get("global_options", {})
        ignore_completed = global_options.get("ignore_completed", False)

        video_path = video_info["path"]

        output_dir = output_config.get("path", "")
        output_filename = self._get_output_filename(video_path, index)
        output_name_no_ext = os.path.splitext(output_filename)[0]

        base_dir = output_dir
        if global_options.get("output_to_folder"):
            base_dir = os.path.join(output_dir, self.batch_folder_name or "batch")
        elif global_options.get("output_to_video_folder"):
            base_dir = os.path.join(output_dir, output_name_no_ext)

        keep_structure = output_config.get("keep_structure", False)
        subdir_support = global_options.get("subdir_support", False)
        root_dir = video_info.get("root_dir")
        if (keep_structure or subdir_support) and root_dir:
            relative_dir = os.path.relpath(os.path.dirname(video_path), root_dir)
            if relative_dir not in (".", ""):
                base_dir = os.path.join(base_dir, relative_dir)

        output_path = os.path.join(base_dir, output_filename)

        if ignore_completed and os.path.exists(output_path):
            return output_path, True

        file_exists_action = global_options.get("file_exists_action", "rename")
        if file_exists_action == "rename" and os.path.exists(output_path):
            output_path = self._ensure_unique_path(output_path)

        return output_path, False


class VideoInfoWorker(QThread):
    """后台线程：批量获取视频文件的详细信息（ffprobe），避免阻塞 UI"""

    info_ready = pyqtSignal(int, str, str)  # (row, file_path, info_text)

    def __init__(self, tasks: list):
        """tasks: list of (row, file_path)"""
        super().__init__()
        self.tasks = tasks

    def run(self):
        import os
        import subprocess
        import json

        # 查找 ffprobe 路径（只查一次）
        ffprobe_path = self._find_ffprobe()

        for row, file_path in self.tasks:
            info_text = self._probe_single(file_path, ffprobe_path)
            self.info_ready.emit(row, file_path, info_text)

    # ------ 内部工具方法 ------
    @staticmethod
    def _find_ffprobe():
        import os, subprocess

        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for rel in ("ffmpeg/ffprobe.exe", "processor/ffprobe.exe"):
            p = os.path.join(app_dir, rel)
            if os.path.exists(p):
                return p
        try:
            creation_flags = 0
            if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creation_flags = subprocess.CREATE_NO_WINDOW
            r = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True,
                timeout=3,
                creationflags=creation_flags,
            )
            if r.returncode == 0:
                return "ffprobe"
        except Exception:
            pass
        return None

    @staticmethod
    def _probe_single(file_path: str, ffprobe_path) -> str:
        import os, subprocess, json

        try:
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
        except Exception:
            return "未知"

        if not ffprobe_path:
            return f"{size_mb:.1f}MB"

        try:
            creation_flags = 0
            if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                creation_flags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                [
                    ffprobe_path,
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                creationflags=creation_flags,
            )
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                video_stream = next(
                    (
                        s
                        for s in data.get("streams", [])
                        if s.get("codec_type") == "video"
                    ),
                    None,
                )
                if video_stream:
                    duration = float(data.get("format", {}).get("duration", 0))
                    h, m, s = (
                        int(duration // 3600),
                        int((duration % 3600) // 60),
                        int(duration % 60),
                    )
                    w = video_stream.get("width", 0)
                    ht = video_stream.get("height", 0)
                    return f"{size_mb:.1f}MB | {h:02d}:{m:02d}:{s:02d} | {w}x{ht}"
        except Exception:
            pass
        return f"{size_mb:.1f}MB"


class BatchVideoProcessorWindow(QMainWindow):
    """批量视频批量处理主窗口"""

    _SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
    _SUPPORTED_VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    MAX_WATERMARKS = 5
    COL_CHECK = 0
    COL_NO = 1
    COL_NAME = 2
    COL_INFO = 3
    COL_STATUS = 4

    # 正则表达式编译缓存
    _pattern_cache = {}

    def __init__(self):
        super().__init__()
        self.video_list = []  # 视频文件列表
        self.process_thread = None
        self.output_mode = "new_location"  # 输出模式: "overwrite", "new_location"
        self.keep_folder_structure = True  # 是否保持文件夹结构

        # 初始化配置（使用默认配置）
        from processor.options_manager import OptionsConfigManager

        self.config = OptionsConfigManager().get_batch_options()
        self._language_manager = get_language_manager()
        self._language_manager.set_language(self.config.get("ui_language", LANG_ZH))

        # 对话框配置
        self.color_tone_config = {}
        self.lut_filter_config = {}
        self.more_effects_config = {}
        self.dynamic_zoom_advanced_config = {}

        # 时间段去水印配置
        self.time_period_enabled = False
        self.time_period_start = 0.0
        self.time_period_end = 0.0

        # 添加水印配置
        self.watermark_configs = []  # 存储所有水印配置
        self.current_watermark_index = -1  # 当前选中的水印索引
        self.file_mode = "file"  # 文件/文件夹模式

        # 文本轨道配置存储
        self.text_configs = [None, None, None]  # 三个文本轨道配置
        self.text_preview_lines = [[], [], []]  # 每个轨道的多行文本预览
        self.text_preview_offsets = [0, 0, 0]  # 当前预览滚动偏移

        # 批量参数应用与每视频配置
        self.current_video_index = None
        self.apply_params_to_all = False
        self._live_invalid_widgets = set()
        self._is_processing = False  # 是否正在处理中

        # 窗口调整相关
        self._resize_margin = 6
        self._resize_edges = 0  # 0: None, 1: Left, 2: Top, 4: Right, 8: Bottom
        self._is_resizing = False
        self._drag_pos = None

        self.init_ui()
        self._language_manager.language_changed.connect(self._on_language_changed)
        self._on_language_changed(self._language_manager.language)
        # 缓存默认参数快照，避免后续变更影响对比
        self._cached_default_params = self.collect_config()

    def _on_language_changed(self, _lang: str):
        apply_language_to_widget(self)
        self._refresh_status_column_language()

    def _ts(self, text: str) -> str:
        return self._language_manager.translate_source_text(text)

    def _warn(self, title: str, message: str):
        return QMessageBox.warning(self, self._ts(title), self._ts(message))

    def _info(self, title: str, message: str):
        return QMessageBox.information(self, self._ts(title), self._ts(message))

    def _error(self, title: str, message: str):
        return QMessageBox.critical(self, self._ts(title), self._ts(message))

    def _confirm(self, title: str, message: str):
        return QMessageBox.question(self, self._ts(title), self._ts(message))

    def _refresh_status_column_language(self) -> None:
        for row in range(self.video_table.rowCount()):
            self._update_video_status_indicator(row)

    def init_ui(self):
        """初始化UI - 无边框沉浸式设计"""
        self.setWindowTitle(self._ts("极速批剪 - 视频批量处理"))
        self.resize(1400, 850)  # 稍微加大一点因为有阴影留白
        # 约束最小宽度，避免右侧参数区被过度挤压导致布局错位
        self.setMinimumSize(1200, 750)

        # 1. 设置无边框和透明背景
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 2. 创建最外层透明容器 (用于容纳阴影)
        outer_widget = QWidget()
        outer_widget.setStyleSheet("background: transparent;")
        self.setCentralWidget(outer_widget)

        outer_layout = QVBoxLayout(outer_widget)
        outer_layout.setContentsMargins(10, 10, 10, 10)  # 留出阴影空间

        # 3. 创建主内容容器 (圆角 + 白底 + 阴影)
        self.main_container = QFrame()
        self.main_container.setObjectName("MainContainer")

        # 预缓存样式表字符串（避免每次最大化/还原时重复拼接）
        self._style_normal = f"""
            QFrame#MainContainer {{
                background-color: {Theme.Background};
                border-radius: 12px;
                border: 1px solid {Theme.Border};
            }}
        """
        self._style_maximized = f"""
            QFrame#MainContainer {{
                background-color: {Theme.Background};
                border-radius: 0px;
                border: none;
            }}
        """
        self.main_container.setStyleSheet(self._style_normal)

        # 添加阴影效果（保存引用，最大化时禁用以提升性能）
        self._shadow_effect = QGraphicsDropShadowEffect(self)
        self._shadow_effect.setBlurRadius(20)
        self._shadow_effect.setColor(QColor(0, 0, 0, 40))
        self._shadow_effect.setOffset(0, 4)
        self.main_container.setGraphicsEffect(self._shadow_effect)

        outer_layout.addWidget(self.main_container)

        # 4. 主容器布局
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 5. 添加自定义标题栏
        self.title_bar = TitleBar(self, self._ts("极速批剪 - 视频批量处理"))
        logo_pixmap = load_logo_pixmap()
        if not logo_pixmap.isNull():
            self.title_bar.set_logo(logo_pixmap)
        self.title_bar.window_minimized.connect(self.showMinimized)
        self.title_bar.window_maximized.connect(self._toggle_maximize)
        self.title_bar.window_restored.connect(self._toggle_maximize)
        self.title_bar.window_closed.connect(self.close)
        self.title_bar.window_moved.connect(self._handle_window_drag)

        container_layout.addWidget(self.title_bar)

        # 6. 内容区域 (原有的界面逻辑)
        content_widget = QWidget()
        content_widget.setStyleSheet(
            "background: transparent;"
        )  # 透明以便透出 main_container 的圆角背景

        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(20, 0, 20, 20)
        main_layout.setSpacing(15)

        # 左右分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：视频列表
        left_panel = self.create_left_panel()

        # 右侧：功能设置
        right_panel = self.create_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setChildrenCollapsible(False)
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setStretchFactor(0, 45)  # 左侧45%
        splitter.setStretchFactor(1, 55)  # 右侧55%

        # 样式化 Splitter handle
        splitter.setHandleWidth(10)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: transparent;
            }}
        """)

        main_layout.addWidget(splitter, 1)

        container_layout.addWidget(content_widget)

        # 7. 布局完成后设置固定列宽（必须在 addWidget 之后，否则会被布局系统重置）
        self.header_view.resizeSection(0, 35)  # 勾选框列
        self.header_view.resizeSection(1, 35)  # 序号列
        self.header_view.resizeSection(4, 90)  # 状态列

        # 8. 鼠标跟踪与事件过滤（用于无边框缩放）
        self.setMouseTracking(True)
        for widget in (
            outer_widget,
            self.main_container,
            content_widget,
            self.title_bar,
        ):
            widget.setMouseTracking(True)
            widget.installEventFilter(self)

        # 输入时即时校验反馈
        self._setup_live_input_validation()

        # ====== 集成：广告、登录、更新 ======
        self._init_services()

    def _init_services(self):
        """初始化广告、登录、更新三大服务"""
        from ui.ad_widget import AdBanner
        from ui.login_widget import LoginWidget
        from utils.auth_service import AuthService
        from utils.auth_code_service import AuthCodeService
        from utils.update_service import UpdateService

        # --- 更新服务 ---
        self._update_service = UpdateService(self)
        self._update_service.update_available.connect(self._on_update_available)
        self._has_update = False

        # --- 登录服务 ---
        self._auth_service = AuthService(self)
        self._login_widget = LoginWidget(self)
        self._login_widget.login_clicked.connect(self._on_login_clicked)
        self._login_widget.logout_clicked.connect(self._on_logout_clicked)
        self._auth_service.login_success.connect(self._on_login_success)
        self._auth_service.login_failed.connect(self._on_login_failed)
        self._auth_service.login_timeout.connect(self._on_login_timeout)
        self._auth_service.logout_done.connect(self._on_logout_done)
        self.title_bar.set_login_widget(self._login_widget)
        # 有缓存的登录信息时先秒显，再异步校验 token
        if self._auth_service.user_info:
            cached_user = self._auth_service.user_info
            self._login_widget.set_user_info(cached_user.nickname, cached_user.avatar)

        # --- 授权码服务 ---
        self._auth_code_service = AuthCodeService()

        # --- 广告组件 ---
        self._ad_banner = AdBanner(self, height=44)
        self.title_bar.set_ad_widget(self._ad_banner)

        # 启动时异步操作：检查登录、检查更新、加载广告
        QTimer.singleShot(500, self._startup_async_tasks)

    def _startup_async_tasks(self):
        """启动时的异步任务"""
        # 检查登录状态
        if self._auth_service.is_logged_in:
            self._auth_service.check_login_async()

        # 检查更新
        self._update_service.check_update()

        # 加载广告
        try:
            self._ad_banner.load_ad("adv_position_01")
        except Exception as e:
            logger.warning(f"[MainWindow] 加载广告失败: {e}")

    def _on_update_available(self, info):
        """更新可用回调 - 设置红点"""
        self._has_update = True
        # 更新 setting_btn 的红点显示
        self._update_setting_btn_badge()

    def _update_setting_btn_badge(self):
        """更新选项按钮的红点状态"""
        if hasattr(self, "setting_btn") and self._has_update:
            self._add_red_dot(self.setting_btn, "_kq_update_dot")

    def _add_red_dot(self, widget, attr_name="_kq_red_dot"):
        """在指定控件右上角添加红点"""
        if hasattr(widget, attr_name):
            dot = getattr(widget, attr_name)
            if dot:
                dot.show()
                dot.raise_()
                return
        dot = QLabel(widget)
        dot.setFixedSize(8, 8)
        dot.setStyleSheet("""
            background-color: #EF4444;
            border-radius: 4px;
            border: none;
        """)
        dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # 定位到右上角
        dot.move(widget.width() - 10, 2)
        dot.show()
        dot.raise_()
        setattr(widget, attr_name, dot)

    def _on_login_clicked(self):
        """点击登录"""
        self._auth_service.start_login()

    def _on_logout_clicked(self):
        """点击退出登录"""
        self._auth_service.logout()

    def _on_login_success(self, user_info):
        """登录成功"""
        self._login_widget.set_user_info(user_info.nickname, user_info.avatar)

    def _on_login_failed(self, error: str):
        """登录失败"""
        logger.warning(f"[MainWindow] 登录失败: {error}")
        if not self._auth_service.is_logged_in:
            self._login_widget.clear_user_info()

    def _on_login_timeout(self):
        """登录超时"""
        logger.warning("[MainWindow] 登录超时")

    def _on_logout_done(self):
        """退出登录完成"""
        self._login_widget.clear_user_info()

    def _ensure_auth_code_before_processing(self) -> bool:
        """开始处理前检查并完成授权码验证。"""
        service = getattr(self, "_auth_code_service", None)
        if service is None:
            from utils.auth_code_service import AuthCodeService

            service = AuthCodeService()
            self._auth_code_service = service

        check_result = service.check_need_auth_code()
        if not check_result.success:
            logger.warning(f"[MainWindow] 授权码预检查失败，按参考项目逻辑放行: {check_result.message}")
            return True

        if not check_result.need_auth_code:
            return True

        stored_result = service.validate_stored_auth_code()
        if stored_result.success and stored_result.is_valid:
            return True

        from ui.auth_code_dialog import AuthCodeDialog

        dialog = AuthCodeDialog(service, check_result.auth_code_url, self)
        return dialog.exec() == QDialog.DialogCode.Accepted

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            # 使用预缓存的样式表
            self.main_container.setStyleSheet(self._style_normal)
            # 恢复边距以显示阴影
            self.centralWidget().layout().setContentsMargins(10, 10, 10, 10)
            # 恢复阴影效果
            self._shadow_effect.setEnabled(True)
        else:
            # 先禁用阴影效果（最大化不需要，且大幅减少重绘开销）
            self._shadow_effect.setEnabled(False)
            self.showMaximized()
            # 使用预缓存的样式表
            self.main_container.setStyleSheet(self._style_maximized)
            self.centralWidget().layout().setContentsMargins(0, 0, 0, 0)
        self.title_bar.set_maximized(self.isMaximized())

    def _handle_window_drag(self, delta):
        """处理窗口拖拽移动"""
        if not self.isMaximized():
            self.move(self.pos() + delta)

    # ================== 窗口调整大小逻辑 ==================
    def eventFilter(self, obj, event):
        event_type = event.type()
        if event_type == QEvent.Type.Leave:
            if not self._is_resizing:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return super().eventFilter(obj, event)

        if event_type in (
            QEvent.Type.MouseMove,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
        ):
            # 将事件坐标统一映射到主窗口坐标（仅鼠标事件才有位置）
            if hasattr(event, "position"):
                local_pos = event.position().toPoint()
            elif hasattr(event, "pos"):
                local_pos = event.pos()
            else:
                return super().eventFilter(obj, event)

            if obj is self:
                window_pos = local_pos
            else:
                window_pos = obj.mapTo(self, local_pos)

            if event_type == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    global_pos = (
                        event.globalPosition().toPoint()
                        if hasattr(event, "globalPosition")
                        else QCursor.pos()
                    )
                    if self._start_resize(window_pos, global_pos):
                        return True
            elif event_type == QEvent.Type.MouseMove:
                if self._is_resizing:
                    global_pos = (
                        event.globalPosition().toPoint()
                        if hasattr(event, "globalPosition")
                        else QCursor.pos()
                    )
                    self._handle_resize(global_pos)
                    return True
                self._update_cursor_shape(window_pos)
            elif event_type == QEvent.Type.MouseButtonRelease:
                if self._is_resizing:
                    self._stop_resize()
                    return True

        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._start_resize(event.pos(), event.globalPosition().toPoint()):
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._stop_resize()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        # 如果正在调整大小
        if self._is_resizing:
            self._handle_resize(event.globalPosition().toPoint())
            return

        # 更新鼠标形状
        self._update_cursor_shape(event.pos())
        super().mouseMoveEvent(event)

    def _start_resize(self, window_pos, global_pos):
        if self.isMaximized():
            return False
        self._update_resize_edges(window_pos)
        if self._resize_edges != 0:
            self._is_resizing = True
            self._drag_pos = global_pos
            return True
        return False

    def _stop_resize(self):
        self._is_resizing = False
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _update_resize_edges(self, pos):
        """计算当前鼠标在哪个边缘"""
        self._resize_edges = 0
        rect = self.rect()
        m = self._resize_margin

        x, y, w, h = pos.x(), pos.y(), rect.width(), rect.height()

        if x < m:
            self._resize_edges |= 1  # Left
        if x > w - m:
            self._resize_edges |= 4  # Right
        if y < m:
            self._resize_edges |= 2  # Top
        if y > h - m:
            self._resize_edges |= 8  # Bottom

    def _update_cursor_shape(self, pos):
        """根据鼠标位置更新光标形状"""
        self._update_resize_edges(pos)
        e = self._resize_edges

        if e == 1 or e == 4:  # Left or Right
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif e == 2 or e == 8:  # Top or Bottom
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif e == 3 or e == 12:  # Top-Left or Bottom-Right (Wait, 1|2=3, 4|8=12)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif (
            e == 5 or e == 10
        ):  # Top-Right or Bottom-Left (4|2=6? No, Right|Top=4|2=6. Left|Bottom=1|8=9)
            # 修正逻辑
            pass

        # 重新精确判断
        if e in (3, 12):  # Top-Left (1|2), Bottom-Right (4|8)
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif e in (6, 9):  # Top-Right (2|4), Bottom-Left (1|8)
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif e in (1, 4):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif e in (2, 8):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _handle_resize(self, global_pos):
        """处理窗口大小调整"""
        if not self._is_resizing:
            return

        diff = global_pos - self._drag_pos

        geo = self.geometry()
        new_geo = QRect(geo)

        e = self._resize_edges
        dx = diff.x()
        dy = diff.y()

        # 处理各个方向的调整
        if e & 1:  # Left
            new_geo.setLeft(geo.left() + dx)
        if e & 4:  # Right
            new_geo.setRight(geo.right() + dx)
        if e & 2:  # Top
            new_geo.setTop(geo.top() + dy)
        if e & 8:  # Bottom
            new_geo.setBottom(geo.bottom() + dy)

        min_w = self.minimumWidth()
        min_h = self.minimumHeight()

        # 最小尺寸限制（使用窗口真实最小尺寸，避免与 setMinimumSize 不一致）
        if new_geo.width() < min_w:
            if e & 1:
                new_geo.setLeft(geo.left())  # 撤销
            else:
                new_geo.setRight(geo.right())

        if new_geo.height() < min_h:
            if e & 2:
                new_geo.setTop(geo.top())
            else:
                new_geo.setBottom(geo.bottom())

        self.setGeometry(new_geo)
        actual_geo = self.geometry()

        # 使用实际生效的位移更新拖拽锚点，避免左边缘到最小宽度后继续“跟着鼠标跑”
        effective_dx = diff.x()
        effective_dy = diff.y()
        if e & 1:
            effective_dx = actual_geo.left() - geo.left()
        elif e & 4:
            effective_dx = actual_geo.right() - geo.right()
        if e & 2:
            effective_dy = actual_geo.top() - geo.top()
        elif e & 8:
            effective_dy = actual_geo.bottom() - geo.bottom()
        self._drag_pos = self._drag_pos + QPoint(effective_dx, effective_dy)

    def create_left_panel(self) -> QWidget:
        """创建左侧视频列表面板"""
        from ui.batch_video.left_panel import create_left_panel

        return create_left_panel(self)

    def create_right_panel(self) -> QWidget:
        """创建右侧功能设置面板"""
        from ui.batch_video.right_panel import create_right_panel

        return create_right_panel(self)

    def create_function_tabs(self) -> QWidget:
        """创建功能标签栏"""
        from ui.batch_video.right_panel import create_function_tabs

        return create_function_tabs(self)

    def switch_tab(self, index: int):
        """切换标签页"""
        for i, page in enumerate(self.tab_pages):
            page.setVisible(i == index)

    def create_remove_watermark_tab(self) -> QWidget:
        from ui.batch_video.tabs.remove_watermark_tab import create_remove_watermark_tab

        return create_remove_watermark_tab(self)

    def create_add_watermark_tab(self) -> QWidget:
        from ui.batch_video.tabs.add_watermark_tab import create_add_watermark_tab

        return create_add_watermark_tab(self)

    def create_watermark_config_widget(self, index: int):
        from ui.batch_video.tabs.add_watermark_tab import create_watermark_config_widget

        return create_watermark_config_widget(self, index)

    def _default_watermark_config(self, index: int) -> dict:
        """生成水印默认配置"""
        return {
            "id": index,
            "type": "image",
            "file_path": "",
            "file_mode": "file",
            "random_select": False,
            "scroll": False,
            "diagonal": False,
            "image_position": "top_right",
            "offset_x": 6,
            "offset_y": 6,
            "opacity": 1.0,
            "text_content": "",
            "text_position": "top_right",
            "text_opacity": 1.0,
            "position": "top_right",
            "custom_position": None,
            "custom_width": None,
            "custom_height": None,
            "style_config": {},
            "file_candidates": [],
        }

    def _ensure_watermark_config(self, index: int) -> dict:
        """确保指定索引的水印配置存在"""
        while len(self.watermark_configs) <= index:
            self.watermark_configs.append(
                self._default_watermark_config(len(self.watermark_configs))
            )
        config = self.watermark_configs[index]
        if config.get("id") != index:
            config["id"] = index
        if "style_config" not in config:
            config["style_config"] = {}
        if "file_candidates" not in config:
            config["file_candidates"] = []
        return config

    def _connect_watermark_widget_signals(self, widget_dict: dict):
        """绑定水印控件的信号，用于同步配置"""

        def handler():
            self._sync_watermark_config_from_widget(widget_dict)
            self._refresh_live_validation_feedback()

        widget_dict["type_combo"].currentIndexChanged.connect(lambda _: handler())
        widget_dict["file_path"].editingFinished.connect(handler)
        widget_dict["position_combo"].currentIndexChanged.connect(lambda _: handler())
        if "scroll_check" in widget_dict:
            widget_dict["scroll_check"].toggled.connect(lambda _: handler())
        if "diagonal_check" in widget_dict:
            widget_dict["diagonal_check"].toggled.connect(lambda _: handler())
        widget_dict["random_check"].toggled.connect(lambda _: handler())
        widget_dict["offset_x"].valueChanged.connect(lambda _: handler())
        widget_dict["offset_y"].valueChanged.connect(lambda _: handler())
        widget_dict["opacity"].valueChanged.connect(lambda _: handler())
        widget_dict["text_content"].textChanged.connect(lambda _: handler())
        widget_dict["text_position"].currentIndexChanged.connect(lambda _: handler())
        widget_dict["text_opacity"].valueChanged.connect(lambda _: handler())

    def _sync_watermark_config_from_widget(self, widget_dict: dict) -> dict:
        """从控件状态同步水印配置"""
        index = widget_dict.get("index", 0)
        existing_snapshot = copy.deepcopy(self._ensure_watermark_config(index))
        config = self._ensure_watermark_config(index)

        watermark_type = widget_dict["type_combo"].currentData()
        if watermark_type not in {"image", "text"}:
            watermark_type = (
                "image" if widget_dict["type_combo"].currentIndex() == 0 else "text"
            )
        file_path_edit: QLineEdit = widget_dict["file_path"]
        config["type"] = watermark_type
        config["file_mode"] = widget_dict.get("file_mode", "file")
        config["file_path"] = file_path_edit.text().strip()
        config["random_select"] = (
            widget_dict["random_check"].isChecked() and config["file_mode"] == "folder"
        )
        scroll_check = widget_dict.get("scroll_check")
        diagonal_check = widget_dict.get("diagonal_check")
        config["scroll"] = scroll_check.isChecked() if scroll_check else False
        config["diagonal"] = diagonal_check.isChecked() if diagonal_check else False
        config["image_position"] = (
            widget_dict["position_combo"].currentData()
            or normalize_text_position(widget_dict["position_combo"].currentText())
        )
        config["offset_x"] = widget_dict["offset_x"].value()
        config["offset_y"] = widget_dict["offset_y"].value()
        config["opacity"] = widget_dict["opacity"].value()
        config["text_content"] = widget_dict["text_content"].text()
        config["text_position"] = (
            widget_dict["text_position"].currentData()
            or normalize_text_position(widget_dict["text_position"].currentText())
        )
        config["text_opacity"] = widget_dict["text_opacity"].value()
        config["position"] = (
            config["image_position"]
            if watermark_type == "image"
            else config["text_position"]
        )
        config["id"] = index

        # 清理文件候选缓存，待验证时重新计算
        config["file_candidates"] = []

        # 保留已有的样式和自定义位置信息
        for key in ["custom_position", "custom_width", "custom_height", "style_config"]:
            if (
                key in existing_snapshot
                and existing_snapshot[key]
                and not config.get(key)
            ):
                config[key] = existing_snapshot[key]

        self.watermark_configs[index] = config
        return config

    def create_crop_tab(self) -> QWidget:
        from ui.batch_video.tabs.crop_tab import create_crop_tab

        return create_crop_tab(self)

    def create_pip_tab(self) -> QWidget:
        from ui.batch_video.tabs.pip_tab import create_pip_tab

        return create_pip_tab(self)

    def on_pip_check_changed(self, checked):
        """画中画开关改变"""
        self.pip_mode_video.setEnabled(checked)
        self.pip_mode_background.setEnabled(checked)
        if checked:
            # 根据当前模式启用对应区域
            if self.pip_mode_video.isChecked():
                self.pip_video_widget.setEnabled(True)
                self.pip_bg_widget.setEnabled(False)
            else:
                self.pip_video_widget.setEnabled(False)
                self.pip_bg_widget.setEnabled(True)
        else:
            self.pip_video_widget.setEnabled(False)
            self.pip_bg_widget.setEnabled(False)

        # 更新预览按钮状态
        self._update_pip_preview_button()

    def on_pip_mode_changed(self):
        """画中画模式改变"""
        if not self.pip_check.isChecked():
            return

        if self.pip_mode_video.isChecked():
            self.pip_video_widget.setVisible(True)
            self.pip_video_widget.setEnabled(True)
            self.pip_bg_widget.setVisible(False)
            self.pip_bg_widget.setEnabled(False)
        else:
            self.pip_video_widget.setVisible(False)
            self.pip_video_widget.setEnabled(False)
            self.pip_bg_widget.setVisible(True)
            self.pip_bg_widget.setEnabled(True)

        # 更新预览按钮状态
        self._update_pip_preview_button()

    def on_pip_bg_browse_clicked(self):
        """选择背景文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("batch.main_window.auto.001", "选择背景文件"),
            "",
            t(
                "batch.main_window.auto.002",
                "媒体文件 (*.jpg *.jpeg *.png *.bmp *.mp4 *.mov *.avi *.mkv);;所有文件 (*.*)",
            ),
        )
        if file_path:
            self.pip_bg_path.setText(file_path)
            # 更新预览按钮状态
            if self.pip_check.isChecked():
                self._update_pip_preview_button()

    def preview_pip_effect(self):
        """预览画中画效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "画中画预览")

    def _update_pip_preview_button(self):
        """更新画中画预览按钮状态"""
        if not self.pip_check.isChecked():
            # 画中画开关未启用，禁用预览
            self.pip_preview_btn.setEnabled(False)
            return

        # 视频模式：开关启用即可预览
        if self.pip_mode_video.isChecked():
            self.pip_preview_btn.setEnabled(True)
            return

        # 背景模式：需要背景文件存在
        bg_path = self.pip_bg_path.text()
        if bg_path and os.path.exists(bg_path):
            self.pip_preview_btn.setEnabled(True)
        else:
            self.pip_preview_btn.setEnabled(False)

    def create_trim_tab(self) -> QWidget:
        from ui.batch_video.tabs.trim_tab import create_trim_tab

        return create_trim_tab(self)

    def create_add_intro_outro_tab(self) -> QWidget:
        from ui.batch_video.tabs.add_intro_outro_tab import create_add_intro_outro_tab

        return create_add_intro_outro_tab(self)

    def create_speed_tab(self) -> QWidget:
        from ui.batch_video.tabs.speed_tab import create_speed_tab

        return create_speed_tab(self)

    def create_text_tab(self) -> QWidget:
        from ui.batch_video.tabs.text_tab import create_text_tab

        return create_text_tab(self)

    def _create_text_track(self, track_num: int) -> QHBoxLayout:
        """创建单个文本轨道控件组"""
        track_layout = QHBoxLayout()
        track_layout.setSpacing(6)

        # 左侧：复选框
        check = QCheckBox(self._ts(f"文本{track_num}:"))
        check.setMinimumWidth(60)
        check.toggled.connect(
            lambda checked, num=track_num: self._on_text_check_changed(num, checked)
        )
        setattr(self, f"text{track_num}_check", check)
        track_layout.addWidget(check)

        # 中间：文本输入框（与截图一致）
        preview = QLineEdit()
        preview.setPlaceholderText(self._ts("未配置"))
        preview.setEnabled(False)
        preview.setMinimumWidth(280)
        preview.textChanged.connect(
            lambda text, num=track_num: self._on_text_inline_changed(num, text)
        )
        setattr(self, f"text{track_num}_preview", preview)
        track_layout.addWidget(preview, 1)

        # 右侧：设置 + 预览
        settings_btn = QPushButton(self._ts("设置"))
        settings_btn.setMinimumWidth(50)
        settings_btn.setEnabled(False)
        settings_btn.setStyleSheet("QPushButton { color: #FF8C00; font-weight: bold; }")
        settings_btn.clicked.connect(
            lambda checked, num=track_num: self._on_text_settings(num)
        )
        setattr(self, f"text{track_num}_settings_btn", settings_btn)
        track_layout.addWidget(settings_btn)

        preview_btn = ModernButton(
            self._ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye"
        )
        preview_btn.setEnabled(False)
        preview_btn.clicked.connect(
            lambda checked, num=track_num: self._on_text_preview(num)
        )
        setattr(self, f"text{track_num}_preview_btn", preview_btn)
        track_layout.addWidget(preview_btn)

        return track_layout

    def create_audio_tab(self) -> QWidget:
        from ui.batch_video.tabs.audio_tab import create_audio_tab

        return create_audio_tab(self)

    def create_image_adjust_tab(self) -> QWidget:
        from ui.batch_video.tabs.image_adjust_tab import create_image_adjust_tab

        return create_image_adjust_tab(self)

    def create_common_params(self) -> QWidget:
        """创建通用参数设置区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(2)  # 极度紧凑的垂直间距
        layout.setContentsMargins(3, 3, 3, 3)  # 极小边距

        # 画面调整（不同视频画面随机微调）
        frame_group = QGroupBox()
        self.frame_adjust_check = QCheckBox(self._ts("画面调整（不同视频画面随机微调）"))
        frame_group_layout = QVBoxLayout(frame_group)
        frame_group_layout.setSpacing(2)  # 紧凑间距
        frame_group_layout.setContentsMargins(5, 3, 5, 3)  # 紧凑边距
        frame_group_layout.addWidget(self.frame_adjust_check)

        frame_layout = QGridLayout()
        frame_layout.setSpacing(2)  # 网格间距2px
        frame_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        frame_layout.setHorizontalSpacing(2)  # 水平间距2px
        frame_layout.setVerticalSpacing(3)  # 垂直间距3px

        # 亮度 -1.0到1.0，默认0，默认区间-0.05到0.05，步长0.01
        frame_layout.addWidget(QLabel(self._ts("亮度:")), 0, 0)
        self.brightness_min = QDoubleSpinBox()
        self.brightness_min.setRange(-1.0, 1.0)
        self.brightness_min.setSingleStep(0.01)
        self.brightness_min.setValue(-0.05)
        self.brightness_min.setDecimals(2)
        self.brightness_min.setMaximumWidth(80)
        frame_layout.addWidget(self.brightness_min, 0, 1)

        frame_layout.addWidget(QLabel("~"), 0, 2)

        self.brightness_max = QDoubleSpinBox()
        self.brightness_max.setRange(-1.0, 1.0)
        self.brightness_max.setSingleStep(0.01)
        self.brightness_max.setValue(0.05)
        self.brightness_max.setDecimals(2)
        self.brightness_max.setMaximumWidth(80)
        frame_layout.addWidget(self.brightness_max, 0, 3)

        # 锐化 -2.0到5.0，默认1.0，负数为模糊，默认区间1.0到1.2，步长0.1
        frame_layout.addWidget(QLabel(self._ts("锐化:")), 0, 4)
        self.sharpness_min = QDoubleSpinBox()
        self.sharpness_min.setRange(-2.0, 5.0)
        self.sharpness_min.setSingleStep(0.1)
        self.sharpness_min.setValue(1.0)
        self.sharpness_min.setDecimals(1)
        self.sharpness_min.setMaximumWidth(80)
        frame_layout.addWidget(self.sharpness_min, 0, 5)

        frame_layout.addWidget(QLabel("~"), 0, 6)

        self.sharpness_max = QDoubleSpinBox()
        self.sharpness_max.setRange(-2.0, 5.0)
        self.sharpness_max.setSingleStep(0.1)
        self.sharpness_max.setValue(1.2)
        self.sharpness_max.setDecimals(1)
        self.sharpness_max.setMaximumWidth(80)
        frame_layout.addWidget(self.sharpness_max, 0, 7)

        # 对比度 -2.0到2.0，默认1.0，默认区间0.95到1.05，步长0.01
        frame_layout.addWidget(QLabel(self._ts("对比度:")), 1, 0)
        self.contrast_min = QDoubleSpinBox()
        self.contrast_min.setRange(-2.0, 2.0)
        self.contrast_min.setSingleStep(0.01)
        self.contrast_min.setValue(0.95)
        self.contrast_min.setDecimals(2)
        self.contrast_min.setMaximumWidth(80)
        frame_layout.addWidget(self.contrast_min, 1, 1)

        frame_layout.addWidget(QLabel("~"), 1, 2)

        self.contrast_max = QDoubleSpinBox()
        self.contrast_max.setRange(-2.0, 2.0)
        self.contrast_max.setSingleStep(0.01)
        self.contrast_max.setValue(1.05)
        self.contrast_max.setDecimals(2)
        self.contrast_max.setMaximumWidth(80)
        frame_layout.addWidget(self.contrast_max, 1, 3)

        # 降噪 0到10，默认3-5，步长1 （根据视频处理经验，合理范围）
        frame_layout.addWidget(QLabel(self._ts("降噪:")), 1, 4)
        self.denoise_min = QSpinBox()
        self.denoise_min.setRange(0, 10)
        self.denoise_min.setSingleStep(1)
        self.denoise_min.setValue(3)
        self.denoise_min.setMaximumWidth(80)
        frame_layout.addWidget(self.denoise_min, 1, 5)

        frame_layout.addWidget(QLabel("~"), 1, 6)

        self.denoise_max = QSpinBox()
        self.denoise_max.setRange(0, 10)
        self.denoise_max.setSingleStep(1)
        self.denoise_max.setValue(5)
        self.denoise_max.setMaximumWidth(80)
        frame_layout.addWidget(self.denoise_max, 1, 7)

        # 饱和度 0到3.0，默认1.0，默认区间0.95到1.05，步长0.01
        frame_layout.addWidget(QLabel(self._ts("饱和度:")), 2, 0)
        self.saturation_min = QDoubleSpinBox()
        self.saturation_min.setRange(0.0, 3.0)
        self.saturation_min.setSingleStep(0.01)
        self.saturation_min.setValue(0.95)
        self.saturation_min.setDecimals(2)
        self.saturation_min.setMaximumWidth(80)
        frame_layout.addWidget(self.saturation_min, 2, 1)

        frame_layout.addWidget(QLabel("~"), 2, 2)

        self.saturation_max = QDoubleSpinBox()
        self.saturation_max.setRange(0.0, 3.0)
        self.saturation_max.setSingleStep(0.01)
        self.saturation_max.setValue(1.05)
        self.saturation_max.setDecimals(2)
        self.saturation_max.setMaximumWidth(80)
        frame_layout.addWidget(self.saturation_max, 2, 3)

        # 按钮：色调、LUT滤镜、更多效果
        self.color_tone_btn = QPushButton(self._ts("色调"))
        self.color_tone_btn.clicked.connect(self.show_color_tone_dialog)
        frame_layout.addWidget(self.color_tone_btn, 2, 4)

        self.lut_filter_btn = QPushButton(self._ts("LUT滤镜"))
        self.lut_filter_btn.clicked.connect(self.show_lut_filter_dialog)
        frame_layout.addWidget(self.lut_filter_btn, 2, 5, 1, 2)

        self.more_effects_btn = QPushButton(self._ts("更多效果"))
        self.more_effects_btn.clicked.connect(self.show_more_effects_dialog)
        frame_layout.addWidget(self.more_effects_btn, 2, 7)

        # 画面调整预览按钮
        self.frame_adjust_preview_btn = ModernButton(
            self._ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye"
        )
        self.frame_adjust_preview_btn.setEnabled(False)  # 默认禁用
        self.frame_adjust_preview_btn.clicked.connect(self.preview_frame_adjust_effect)
        frame_layout.addWidget(self.frame_adjust_preview_btn, 2, 8)

        frame_group_layout.addLayout(frame_layout)

        # 启用/禁用控制
        self.frame_adjust_check.toggled.connect(self.on_frame_adjust_check_changed)
        # 默认禁用所有控件
        self.brightness_min.setEnabled(False)
        self.brightness_max.setEnabled(False)
        self.sharpness_min.setEnabled(False)
        self.sharpness_max.setEnabled(False)
        self.contrast_min.setEnabled(False)
        self.contrast_max.setEnabled(False)
        self.denoise_min.setEnabled(False)
        self.denoise_max.setEnabled(False)
        self.saturation_min.setEnabled(False)
        self.saturation_max.setEnabled(False)
        self.color_tone_btn.setEnabled(False)
        self.lut_filter_btn.setEnabled(False)
        self.more_effects_btn.setEnabled(False)
        self.frame_adjust_preview_btn.setEnabled(False)

        layout.addWidget(frame_group)

        # 宫格分屏
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(2)  # 紧凑间距

        self.grid_split_check = QCheckBox("")
        self.grid_split_check.toggled.connect(self.on_grid_split_check_changed)
        grid_layout.addWidget(self.grid_split_check)

        self.grid_count = QSpinBox()
        self.grid_count.setRange(1, 9)
        self.grid_count.setSingleStep(1)
        self.grid_count.setValue(3)
        self.grid_count.setEnabled(False)  # 默认禁用
        grid_layout.addWidget(self.grid_count)

        grid_layout.addWidget(QLabel(self._ts("宫格分屏")))

        grid_layout.addWidget(QLabel(self._ts("方向:")))
        self.grid_direction = QComboBox()
        for code in ("auto", "vertical", "horizontal"):
            self.grid_direction.addItem(
                enum_label(GRID_DIRECTION_LABELS, code, LANG_ZH), code
            )
        self.grid_direction.setEnabled(False)  # 默认禁用
        grid_layout.addWidget(self.grid_direction)

        self.grid_blur_check = QCheckBox(self._ts("两端虚化"))
        self.grid_blur_check.setEnabled(False)  # 默认禁用
        grid_layout.addWidget(self.grid_blur_check)

        self.grid_preview_btn = ModernButton(
            self._ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye"
        )
        self.grid_preview_btn.setEnabled(False)  # 默认禁用
        self.grid_preview_btn.clicked.connect(self.preview_grid_effect)
        grid_layout.addWidget(self.grid_preview_btn)

        grid_layout.addStretch()
        layout.addLayout(grid_layout)

        # 分辨率
        resolution_layout = QHBoxLayout()
        resolution_layout.setSpacing(2)  # 紧凑间距
        self.resolution_check = QCheckBox(self._ts("分辨率"))
        self.resolution_check.toggled.connect(self.on_resolution_check_changed)
        resolution_layout.addWidget(self.resolution_check)

        self.resolution_preset = QComboBox()
        for code in ("custom", "swap", "p360", "p480", "p720", "p1080"):
            self.resolution_preset.addItem(
                enum_label(RESOLUTION_PRESET_LABELS, code, LANG_ZH), code
            )
        self.resolution_preset.currentTextChanged.connect(
            self.on_resolution_preset_changed
        )
        self.resolution_preset.setEnabled(False)  # 默认禁用
        resolution_layout.addWidget(self.resolution_preset)

        self.resolution_width = QSpinBox()
        self.resolution_width.setRange(0, 9999)
        self.resolution_width.setValue(1920)
        self.resolution_width.setEnabled(False)  # 默认禁用
        resolution_layout.addWidget(self.resolution_width)

        resolution_layout.addWidget(QLabel("*"))

        self.resolution_height = QSpinBox()
        self.resolution_height.setRange(0, 9999)
        self.resolution_height.setValue(1080)
        self.resolution_height.setEnabled(False)  # 默认禁用
        resolution_layout.addWidget(self.resolution_height)

        self.resolution_swap_btn = QPushButton("↔")
        self.resolution_swap_btn.clicked.connect(self.swap_resolution)
        self.resolution_swap_btn.setEnabled(False)  # 默认禁用
        resolution_layout.addWidget(self.resolution_swap_btn)

        resolution_layout.addStretch()
        layout.addLayout(resolution_layout)

        # 模式选择
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(2)  # 紧凑间距
        mode_layout.addWidget(QLabel(self._ts("模式:")))

        self.mode_stretch = QRadioButton(self._ts("拉伸"))
        self.mode_crop = QRadioButton(self._ts("裁切"))
        self.mode_original = QRadioButton(self._ts("原比例"))
        self.mode_original.setChecked(True)

        # 默认禁用所有模式选项
        self.mode_stretch.setEnabled(False)
        self.mode_crop.setEnabled(False)
        self.mode_original.setEnabled(False)

        mode_group = QButtonGroup(self)
        mode_group.addButton(self.mode_stretch)
        mode_group.addButton(self.mode_crop)
        mode_group.addButton(self.mode_original)
        # 连接模式改变信号
        mode_group.buttonToggled.connect(self.on_resolution_mode_changed)

        mode_layout.addWidget(self.mode_stretch)
        mode_layout.addWidget(self.mode_crop)
        mode_layout.addWidget(self.mode_original)

        self.background_blur_check = QCheckBox(self._ts("背景"))
        self.background_blur_check.setEnabled(False)  # 默认禁用
        mode_layout.addWidget(self.background_blur_check)

        self.reflection_check = QCheckBox(self._ts("倒影"))
        self.reflection_check.setEnabled(False)  # 默认禁用
        mode_layout.addWidget(self.reflection_check)

        self.reflection_opacity = QDoubleSpinBox()
        self.reflection_opacity.setRange(0.0, 1.0)
        self.reflection_opacity.setSingleStep(0.1)
        self.reflection_opacity.setValue(0.5)
        self.reflection_opacity.setDecimals(1)
        self.reflection_opacity.setEnabled(False)  # 默认禁用
        mode_layout.addWidget(self.reflection_opacity)

        self.resolution_preview_btn = ModernButton(
            self._ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye"
        )
        self.resolution_preview_btn.setEnabled(False)  # 默认禁用
        self.resolution_preview_btn.clicked.connect(self.preview_resolution_effect)
        mode_layout.addWidget(self.resolution_preview_btn)

        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 旋转&翻转
        rotate_layout = QHBoxLayout()
        rotate_layout.setSpacing(2)  # 紧凑间距
        self.rotate_check = QCheckBox(self._ts("旋转&翻转"))
        self.rotate_check.toggled.connect(self.on_rotate_check_changed)
        rotate_layout.addWidget(self.rotate_check)

        self.flip_left90 = QRadioButton(self._ts("左转90度"))
        self.flip_right90 = QRadioButton(self._ts("右转90度"))
        self.flip_horizontal = QRadioButton(self._ts("水平翻转"))
        self.flip_vertical = QRadioButton(self._ts("垂直翻转"))
        self.flip_random_direction = QRadioButton(self._ts("随机方向"))
        self.flip_random = QRadioButton(self._ts("随机角度"))

        # 默认禁用所有旋转选项
        self.flip_left90.setEnabled(False)
        self.flip_right90.setEnabled(False)
        self.flip_horizontal.setEnabled(False)
        self.flip_vertical.setEnabled(False)
        self.flip_random_direction.setEnabled(False)
        self.flip_random.setEnabled(False)

        self.flip_group = QButtonGroup(self)
        self.flip_group.addButton(self.flip_left90)
        self.flip_group.addButton(self.flip_right90)
        self.flip_group.addButton(self.flip_horizontal)
        self.flip_group.addButton(self.flip_vertical)
        self.flip_group.addButton(self.flip_random_direction)
        self.flip_group.addButton(self.flip_random)

        rotate_layout.addWidget(self.flip_left90)
        rotate_layout.addWidget(self.flip_right90)
        rotate_layout.addWidget(self.flip_horizontal)
        rotate_layout.addWidget(self.flip_vertical)
        rotate_layout.addWidget(self.flip_random_direction)
        rotate_layout.addWidget(self.flip_random)

        self.flip_random_angle = QDoubleSpinBox()
        self.flip_random_angle.setRange(-180.0, 180.0)
        self.flip_random_angle.setSingleStep(0.1)
        self.flip_random_angle.setValue(-1.0)
        self.flip_random_angle.setDecimals(1)
        self.flip_random_angle.setEnabled(False)  # 默认禁用
        rotate_layout.addWidget(self.flip_random_angle)

        rotate_layout.addWidget(QLabel("~"))

        self.flip_random_angle_max = QDoubleSpinBox()
        self.flip_random_angle_max.setRange(-180.0, 180.0)
        self.flip_random_angle_max.setSingleStep(0.1)
        self.flip_random_angle_max.setValue(1.0)
        self.flip_random_angle_max.setDecimals(1)
        self.flip_random_angle_max.setEnabled(False)  # 默认禁用
        rotate_layout.addWidget(self.flip_random_angle_max)

        self.flip_complete_check = QCheckBox(self._ts("完全显示"))
        self.flip_complete_check.setEnabled(False)
        rotate_layout.addWidget(self.flip_complete_check)

        self.flip_black_edge_check = QCheckBox(self._ts("黑边去除"))
        self.flip_black_edge_check.setEnabled(False)
        rotate_layout.addWidget(self.flip_black_edge_check)

        # 旋转&翻转预览按钮
        self.rotate_preview_btn = ModernButton(
            self._ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye"
        )
        self.rotate_preview_btn.setEnabled(False)  # 默认禁用
        self.rotate_preview_btn.clicked.connect(self.preview_rotate_effect)
        self.flip_random.toggled.connect(self._update_rotate_random_controls)
        rotate_layout.addWidget(self.rotate_preview_btn)

        rotate_layout.addStretch()
        layout.addLayout(rotate_layout)

        # 帧率设置
        fps_layout = QHBoxLayout()
        fps_layout.setSpacing(2)  # 紧凑间距
        self.fps_check = QCheckBox(self._ts("帧率设置"))
        self.fps_check.toggled.connect(self.on_fps_check_changed)
        fps_layout.addWidget(self.fps_check)

        fps_layout.addWidget(QLabel(self._ts("帧率:")))

        self.fps_min = QDoubleSpinBox()
        self.fps_min.setRange(12.0, 120.0)
        self.fps_min.setSingleStep(0.1)
        self.fps_min.setValue(24.0)
        self.fps_min.setDecimals(1)
        self.fps_min.setEnabled(False)  # 默认禁用
        fps_layout.addWidget(self.fps_min)

        fps_layout.addWidget(QLabel("~"))

        self.fps_max = QDoubleSpinBox()
        self.fps_max.setRange(12.0, 120.0)
        self.fps_max.setSingleStep(0.1)
        self.fps_max.setValue(30.0)
        self.fps_max.setDecimals(1)
        self.fps_max.setEnabled(False)  # 默认禁用
        fps_layout.addWidget(self.fps_max)

        fps_layout.addWidget(QLabel("(12~120)"))

        self.remove_duplicate_frames_check = QCheckBox(self._ts("重复帧去除"))
        self.remove_duplicate_frames_check.setEnabled(False)  # 默认禁用
        fps_layout.addWidget(self.remove_duplicate_frames_check)

        # 帧率预览按钮
        self.fps_preview_btn = ModernButton(
            self._ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye"
        )
        self.fps_preview_btn.setEnabled(False)  # 默认禁用
        self.fps_preview_btn.clicked.connect(self.preview_fps_effect)
        fps_layout.addWidget(self.fps_preview_btn)

        fps_layout.addStretch()
        layout.addLayout(fps_layout)

        # 抽帧
        frame_extract_layout = QHBoxLayout()
        frame_extract_layout.setSpacing(2)  # 紧凑间距
        self.frame_extract_check = QCheckBox(self._ts("抽帧"))
        self.frame_extract_check.toggled.connect(self.on_frame_extract_check_changed)
        frame_extract_layout.addWidget(self.frame_extract_check)

        frame_extract_layout.addWidget(QLabel(self._ts("每")))

        self.frame_extract_min = QSpinBox()
        self.frame_extract_min.setRange(2, 999)
        self.frame_extract_min.setSingleStep(1)
        self.frame_extract_min.setValue(25)
        self.frame_extract_min.setEnabled(False)  # 默认禁用
        frame_extract_layout.addWidget(self.frame_extract_min)

        frame_extract_layout.addWidget(QLabel("~"))

        self.frame_extract_max = QSpinBox()
        self.frame_extract_max.setRange(2, 999)
        self.frame_extract_max.setSingleStep(1)
        self.frame_extract_max.setValue(30)
        self.frame_extract_max.setEnabled(False)  # 默认禁用
        frame_extract_layout.addWidget(self.frame_extract_max)

        frame_extract_layout.addWidget(QLabel(self._ts("帧抽一帧")))

        self.audio_speed_check = QCheckBox(self._ts("声音变速"))
        self.audio_speed_check.setEnabled(False)
        frame_extract_layout.addWidget(self.audio_speed_check)

        self.frame_extract_preview_btn = ModernButton(
            self._ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye"
        )
        self.frame_extract_preview_btn.setEnabled(False)  # 默认禁用
        self.frame_extract_preview_btn.clicked.connect(
            self.preview_frame_extract_effect
        )
        frame_extract_layout.addWidget(self.frame_extract_preview_btn)

        frame_extract_layout.addStretch()
        layout.addLayout(frame_extract_layout)

        # 动态缩放
        dynamic_zoom_layout = QHBoxLayout()
        dynamic_zoom_layout.setSpacing(2)  # 紧凑间距
        self.dynamic_zoom_check = QCheckBox(self._ts("动态缩放"))
        self.dynamic_zoom_check.toggled.connect(self.on_dynamic_zoom_check_changed)
        dynamic_zoom_layout.addWidget(self.dynamic_zoom_check)

        self.dynamic_zoom_min = QDoubleSpinBox()
        self.dynamic_zoom_min.setRange(0.5, 2.0)  # 0.5倒缩到50%,2.0放大到200%
        self.dynamic_zoom_min.setSingleStep(0.01)
        self.dynamic_zoom_min.setValue(1.0)  # 1.0表示不缩放
        self.dynamic_zoom_min.setDecimals(2)
        self.dynamic_zoom_min.setEnabled(False)  # 默认禁用
        dynamic_zoom_layout.addWidget(self.dynamic_zoom_min)

        dynamic_zoom_layout.addWidget(QLabel("~"))

        self.dynamic_zoom_max = QDoubleSpinBox()
        self.dynamic_zoom_max.setRange(0.5, 2.0)
        self.dynamic_zoom_max.setSingleStep(0.01)
        self.dynamic_zoom_max.setValue(1.15)  # 默认放大到15%
        self.dynamic_zoom_max.setDecimals(2)
        self.dynamic_zoom_max.setEnabled(False)  # 默认禁用
        dynamic_zoom_layout.addWidget(self.dynamic_zoom_max)

        dynamic_zoom_layout.addWidget(QLabel("(0.5~2.0)"))

        self.dynamic_zoom_settings_btn = QPushButton(self._ts("设置"))
        self.dynamic_zoom_settings_btn.setEnabled(False)
        self.dynamic_zoom_settings_btn.clicked.connect(
            self.show_dynamic_zoom_settings_dialog
        )
        dynamic_zoom_layout.addWidget(self.dynamic_zoom_settings_btn)

        self.dynamic_zoom_preview_btn = ModernButton(
            self._ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye"
        )
        self.dynamic_zoom_preview_btn.setEnabled(False)  # 默认禁用
        self.dynamic_zoom_preview_btn.clicked.connect(self.preview_dynamic_zoom_effect)
        dynamic_zoom_layout.addWidget(self.dynamic_zoom_preview_btn)

        dynamic_zoom_layout.addStretch()
        layout.addLayout(dynamic_zoom_layout)

        # 码率调整（默认不选中）
        bitrate_layout = QHBoxLayout()
        bitrate_layout.setSpacing(2)  # 紧凑间距
        self.bitrate_check = QCheckBox(self._ts("码率调整 - 决定视频文件体积与清晰度"))
        self.bitrate_check.setChecked(False)  # 默认不选中
        self.bitrate_check.toggled.connect(self.on_bitrate_check_changed)
        bitrate_layout.addWidget(self.bitrate_check)
        bitrate_layout.addStretch()
        layout.addLayout(bitrate_layout)

        # 动态/定值选项（单独一行）
        bitrate_mode_layout = QHBoxLayout()
        bitrate_mode_layout.setSpacing(2)  # 紧凑间距
        bitrate_mode_layout.addWidget(QLabel("          "))  # 缩进

        self.bitrate_mode_dynamic = QRadioButton(self._ts("动态"))
        self.bitrate_mode_fixed = QRadioButton(self._ts("定值"))
        self.bitrate_mode_dynamic.setChecked(True)

        bitrate_mode_group = QButtonGroup(self)
        bitrate_mode_group.addButton(self.bitrate_mode_dynamic)
        bitrate_mode_group.addButton(self.bitrate_mode_fixed)

        bitrate_mode_layout.addWidget(self.bitrate_mode_dynamic)

        self.bitrate_dynamic_value = QSpinBox()
        self.bitrate_dynamic_value.setRange(0, 51)
        self.bitrate_dynamic_value.setSingleStep(1)
        self.bitrate_dynamic_value.setValue(23)
        self.bitrate_dynamic_value.setEnabled(False)  # 默认禁用
        bitrate_mode_layout.addWidget(self.bitrate_dynamic_value)

        bitrate_mode_layout.addWidget(QLabel("(0~51)"))

        bitrate_mode_layout.addWidget(self.bitrate_mode_fixed)

        self.bitrate_fixed_preset = QComboBox()
        self.bitrate_fixed_preset.addItems(
            [
                self._ts("保持原值"),
                "51",
                "768",
                "1000",
                "1500",
                "2000",
                "3000",
                "4000",
                "5000",
                "6000",
            ]
        )
        self.bitrate_fixed_preset.setCurrentText("3000")  # 默认选中3000
        self.bitrate_fixed_preset.setEnabled(False)  # 默认禁用
        bitrate_mode_layout.addWidget(self.bitrate_fixed_preset)

        bitrate_mode_layout.addWidget(QLabel("kb/s"))

        # 倍率放在同一行
        bitrate_mode_layout.addWidget(QLabel(self._ts("  倍率:")))

        self.bitrate_ratio_min = QDoubleSpinBox()
        self.bitrate_ratio_min.setRange(0.2, 8.0)
        self.bitrate_ratio_min.setSingleStep(0.1)
        self.bitrate_ratio_min.setValue(0.8)  # 改为0.8,压缩20%
        self.bitrate_ratio_min.setDecimals(2)
        self.bitrate_ratio_min.setEnabled(False)  # 默认禁用
        bitrate_mode_layout.addWidget(self.bitrate_ratio_min)

        bitrate_mode_layout.addWidget(QLabel("~"))

        self.bitrate_ratio_max = QDoubleSpinBox()
        self.bitrate_ratio_max.setRange(0.2, 8.0)
        self.bitrate_ratio_max.setSingleStep(0.1)
        self.bitrate_ratio_max.setValue(1.2)  # 改为1.2,增加20%
        self.bitrate_ratio_max.setDecimals(2)
        self.bitrate_ratio_max.setEnabled(False)  # 默认禁用
        bitrate_mode_layout.addWidget(self.bitrate_ratio_max)

        bitrate_mode_layout.addWidget(QLabel("(0.2~8.0)"))

        bitrate_mode_layout.addStretch()
        layout.addLayout(bitrate_mode_layout)

        # 重置参数按钮
        reset_layout = QHBoxLayout()
        reset_layout.setSpacing(2)  # 紧凑间距
        reset_layout.addStretch()

        self.reset_params_btn = QPushButton(self._ts("重置参数"))
        self.reset_params_btn.clicked.connect(self.reset_all_parameters)
        reset_layout.addWidget(self.reset_params_btn)

        layout.addLayout(reset_layout)

        return widget

    def create_bottom_panel(self) -> QWidget:
        """创建底部控制面板"""
        from ui.batch_video.bottom_panel import create_bottom_panel

        return create_bottom_panel(self)

    def show_load_menu(self):
        """显示加载视频菜单"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        from ui.components import load_svg_icon

        menu = QMenu(self)

        # 导入文件
        import_files_action = QAction(load_svg_icon("import", 16), self._ts("导入文件"), self)
        import_files_action.triggered.connect(self.import_video_files)
        menu.addAction(import_files_action)

        # 导入目录
        import_folder_action = QAction(load_svg_icon("folder", 16), self._ts("导入文件夹"), self)
        import_folder_action.triggered.connect(self.import_video_folder)
        menu.addAction(import_folder_action)

        # 在按钮下方显示菜单
        menu.exec(
            self.load_video_btn.mapToGlobal(self.load_video_btn.rect().bottomLeft())
        )

    def import_video_files(self):
        """导入视频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            t("batch.main_window.auto.003", "选择视频文件"),
            "",
            t(
                "batch.main_window.auto.004",
                "视频文件 (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.m4v *.mpg *.mpeg);;所有文件 (*.*)",
            ),
        )
        if files:
            self.add_videos(files)

    def import_video_folder(self):
        """导入目录（递归搜索所有视频）"""
        folder = QFileDialog.getExistingDirectory(
            self, t("batch.main_window.auto.005", "选择视频目录"), ""
        )
        if folder:
            # 递归搜索目录下的所有视频文件
            video_extensions = [
                ".mp4",
                ".avi",
                ".mov",
                ".mkv",
                ".flv",
                ".wmv",
                ".m4v",
                ".mpg",
                ".mpeg",
            ]
            video_files = []

            import os

            for root, dirs, files in os.walk(folder):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        video_files.append(os.path.join(root, file))

            if video_files:
                self.add_videos(video_files, root_dir=folder)
                self.process_log.append(
                    f"从目录 {folder} 导入了 {len(video_files)} 个视频"
                )
            else:
                QMessageBox.information(
                    self,
                    t("batch.main_window.auto.006", "提示"),
                    t(
                        "batch.main_window.auto.061",
                        "在目录 {folder} 中未找到视频文件",
                        folder=folder,
                    ),
                )

    def add_videos(self, file_paths: List[str], root_dir: Optional[str] = None):
        """添加视频到列表（先立即显示，再异步获取视频信息）"""
        import os

        # 过滤掉已存在的文件
        existing_paths = {v["path"] for v in self.video_list}
        new_files = [f for f in file_paths if f not in existing_paths]

        if not new_files:
            return

        # 收集需要异步获取信息的 (row, file_path) 列表
        pending_info_tasks = []

        # 暂停表格更新以加速批量插入
        self.video_table.setUpdatesEnabled(False)
        try:
            # 预分配所有行
            current_count = self.video_table.rowCount()
            self.video_table.setRowCount(current_count + len(new_files))

            for idx, file_path in enumerate(new_files):
                # 立即获取文件大小（极快，不阻塞）
                try:
                    file_size = os.path.getsize(file_path)
                    size_mb = file_size / (1024 * 1024)
                    placeholder_text = f"{size_mb:.1f}MB | 读取中..."
                except Exception:
                    placeholder_text = "读取中..."

                video_info = {
                    "path": file_path,
                    "info": placeholder_text,
                    "status": "pending",
                    "root_dir": root_dir,
                    "params": None,
                }
                self.video_list.append(video_info)

                # 添加到表格（立即显示）
                row = current_count + idx
                self.video_table.setItem(
                    row, self.COL_CHECK, self._create_check_item(checked=True)
                )

                no_item = QTableWidgetItem(str(row + 1))
                no_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.video_table.setItem(row, self.COL_NO, no_item)

                # 文件名列，同时在UserRole中存储完整路径
                file_name_item = QTableWidgetItem(os.path.basename(file_path))
                file_name_item.setData(
                    Qt.ItemDataRole.UserRole, file_path
                )  # 存储完整路径
                self.video_table.setItem(row, self.COL_NAME, file_name_item)

                self.video_table.setItem(
                    row, self.COL_INFO, QTableWidgetItem(placeholder_text)
                )

                # 状态列使用组合控件（圆点 + 文字）
                self._update_video_status_indicator(row, "pending")

                # 记录需要异步获取信息的任务
                pending_info_tasks.append((row, file_path))
        finally:
            self.video_table.setUpdatesEnabled(True)

        self.update_queue_count()
        self.update_empty_state()
        self.update_header_checkbox_state()

        # 如果之前没有选中视频，自动选中第一行
        if self.current_video_index is None and self.video_list:
            self.video_table.selectRow(0)

        # 异步获取视频详细信息（ffprobe），不阻塞 UI
        if pending_info_tasks:
            worker = VideoInfoWorker(pending_info_tasks)
            worker.info_ready.connect(self._on_video_info_ready)
            worker.finished.connect(lambda: self._cleanup_video_info_worker(worker))
            # 保持引用防止被 GC 回收
            if not hasattr(self, "_video_info_workers"):
                self._video_info_workers = []
            self._video_info_workers.append(worker)
            worker.start()

    def _on_video_info_ready(self, row: int, file_path: str, info_text: str):
        """后台线程返回视频信息时更新 UI"""
        # 校验行号和路径是否仍然匹配（防止用户在加载期间删除了行）
        if row < len(self.video_list) and self.video_list[row]["path"] == file_path:
            self.video_list[row]["info"] = info_text
            info_item = self.video_table.item(row, self.COL_INFO)
            if info_item:
                info_item.setText(info_text)

    def _cleanup_video_info_worker(self, worker):
        """清理已完成的后台 worker"""
        if hasattr(self, "_video_info_workers"):
            try:
                self._video_info_workers.remove(worker)
            except ValueError:
                pass
        worker.deleteLater()

    def get_video_info(self, file_path: str) -> str:
        """获取视频信息（文件大小、时长、分辨率）"""
        try:
            import os
            import subprocess
            import json

            # 获取文件大小
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)

            # 查找ffprobe路径（多种方式）
            ffprobe_path = None

            # 1. 检查app/ffmpeg目录下的ffprobe.exe（打包时会一起打包）
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            bundled_ffprobe = os.path.join(app_dir, "ffmpeg", "ffprobe.exe")
            if os.path.exists(bundled_ffprobe):
                ffprobe_path = bundled_ffprobe

            # 2. 检查processor目录下是否有ffprobe.exe
            if not ffprobe_path:
                processor_ffprobe = os.path.join(app_dir, "processor", "ffprobe.exe")
                if os.path.exists(processor_ffprobe):
                    ffprobe_path = processor_ffprobe

            # 3. 尝试系统PATH中的ffprobe
            if not ffprobe_path:
                try:
                    result = subprocess.run(
                        ["ffprobe", "-version"], capture_output=True, timeout=3
                    )
                    if result.returncode == 0:
                        ffprobe_path = "ffprobe"
                except:
                    pass

            # 使用ffprobe获取视频信息
            if ffprobe_path:
                try:
                    cmd = [
                        ffprobe_path,
                        "-v",
                        "quiet",
                        "-print_format",
                        "json",
                        "-show_format",
                        "-show_streams",
                        file_path,
                    ]

                    # 设置 creationflags 以避免弹出窗口（仅Windows）
                    creation_flags = 0
                    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                        creation_flags = subprocess.CREATE_NO_WINDOW

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10,
                        encoding="utf-8",
                        creationflags=creation_flags,
                    )

                    if result.returncode == 0 and result.stdout:
                        data = json.loads(result.stdout)

                        # 获取视频流
                        video_stream = next(
                            (
                                s
                                for s in data.get("streams", [])
                                if s.get("codec_type") == "video"
                            ),
                            None,
                        )

                        if video_stream:
                            # 获取时长（格式为 HH:MM:SS）
                            duration = float(data.get("format", {}).get("duration", 0))
                            hours = int(duration // 3600)
                            minutes = int((duration % 3600) // 60)
                            seconds = int(duration % 60)
                            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

                            # 获取分辨率
                            width = video_stream.get("width", 0)
                            height = video_stream.get("height", 0)
                            resolution = f"{width}x{height}"

                            # 返回格式: 大小 | 时长 | 分辨率
                            return f"{size_mb:.1f}MB | {duration_str} | {resolution}"

                except (
                    subprocess.TimeoutExpired,
                    FileNotFoundError,
                    json.JSONDecodeError,
                    ValueError,
                ) as e:
                    # ffprobe执行失败，只显示文件大小
                    pass

            # 如果ffprobe失败或不存在，只显示文件大小
            return f"{size_mb:.1f}MB"

        except Exception as e:
            return "未知"

    def clear_queue(self):
        """清空队列"""
        if not self.video_list:
            return

        # 弹出确认对话框（使用中文按钮）
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(t("batch.main_window.auto.007", "确认清空"))
        msg_box.setText(t("batch.main_window.auto.008", "确定要清空所有视频吗？"))
        msg_box.setIcon(QMessageBox.Icon.Question)

        # 添加中文按钮
        yes_btn = msg_box.addButton(
            t("batch.main_window.auto.009", "确定"), QMessageBox.ButtonRole.YesRole
        )
        no_btn = msg_box.addButton(
            t("batch.main_window.auto.010", "取消"), QMessageBox.ButtonRole.NoRole
        )
        msg_box.setDefaultButton(no_btn)

        msg_box.exec()

        if msg_box.clickedButton() == yes_btn:
            self.video_list.clear()
            self.video_table.setRowCount(0)
            self.current_video_index = None
            self.update_queue_count()
            self.update_empty_state()
            self.update_header_checkbox_state()

            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> 已清空所有视频")

    def update_queue_count(self):
        """更新队列计数"""
        self.update_queue_status()

    def update_queue_status(self):
        """更新队列状态与按钮可用性"""
        total_count = len(self.video_list)
        checked_count = (
            len(self.get_checked_rows()) if hasattr(self, "video_table") else 0
        )
        selected_count = (
            len(self.get_selected_rows()) if hasattr(self, "video_table") else 0
        )
        if hasattr(self, "queue_label"):
            self.queue_label.setText(
                t(
                    "batch.main_window.auto.062",
                    "总数: {total} | 已勾选: {checked}",
                    total=total_count,
                    checked=checked_count,
                )
            )

        if hasattr(self, "clear_btn"):
            self.clear_btn.setEnabled(total_count > 0)
        if hasattr(self, "remove_btn"):
            self.remove_btn.setEnabled(checked_count > 0)

    def _has_any_processing_feature(self) -> bool:
        """是否已选择任一处理功能或参数"""
        feature_checks = [
            self.remove_watermark_check.isChecked(),
            self.add_watermark_check.isChecked(),
            self.crop_check.isChecked(),
            self.pip_check.isChecked(),
            self.trim_check.isChecked(),
            self.head_check.isChecked(),
            self.tail_check.isChecked(),
            self.border_check.isChecked(),
            self.speed_check.isChecked(),
            self.text1_check.isChecked(),
            self.text2_check.isChecked(),
            self.text3_check.isChecked(),
            self.bgm_check.isChecked(),
            self.original_volume_check.isChecked(),
            self.frame_adjust_check.isChecked(),
            self.grid_split_check.isChecked(),
            self.resolution_check.isChecked(),
            self.rotate_check.isChecked(),
            self.fps_check.isChecked() if hasattr(self, "fps_check") else False,
            self.frame_extract_check.isChecked()
            if hasattr(self, "frame_extract_check")
            else False,
            self.dynamic_zoom_check.isChecked()
            if hasattr(self, "dynamic_zoom_check")
            else False,
            self.bitrate_check.isChecked() if hasattr(self, "bitrate_check") else False,
        ]

        if self.more_effects_config and any(
            bool(value)
            for key, value in self.more_effects_config.items()
            if key.endswith("_enabled")
        ):
            return True

        if self.lut_filter_config and self.lut_filter_config.get("apply"):
            return True

        return any(feature_checks)

    def _validate_text_source_config(
        self, track_num: int, config: Optional[Dict]
    ) -> bool:
        """校验文本来源输入是否完整"""
        if not config:
            self._warn("提示", f"请先配置文本{track_num}的参数")
            return False

        mode = normalize_text_source_mode(config.get("source_mode", "plain"))
        if mode == "plain":
            text = config.get("text_content", "").strip()
            if not text:
                self._warn("提示", f"文本{track_num}未输入内容，请先填写")
                return False
        elif mode == "folder":
            folder_path = config.get("folder_path", "").strip()
            if not folder_path:
                self._warn("提示", f"文本{track_num}请选择文本文件夹")
                return False
            if not os.path.exists(folder_path):
                self._warn("提示", f"文本{track_num}的文本文件夹不存在")
                return False

        return True

    def _validate_text_inputs_before_processing(self) -> bool:
        """开始处理前校验文本输入"""
        text_tracks = [
            (1, self.text1_check.isChecked()),
            (2, self.text2_check.isChecked()),
            (3, self.text3_check.isChecked()),
        ]
        for track_num, enabled in text_tracks:
            if not enabled:
                continue
            if not self._validate_text_source_config(
                track_num, self.text_configs[track_num - 1]
            ):
                return False
        return True

    def _collect_manual_input_issue_details(self) -> List[Tuple[str, List[QWidget]]]:
        """汇总所有手动输入问题，并返回对应控件用于字段级高亮。"""
        issues: List[Tuple[str, List[QWidget]]] = []

        def _add_issue(message: str, widgets: Optional[List[QWidget]] = None) -> None:
            issues.append((message, [w for w in (widgets or []) if w is not None]))

        def _append_range_issue(
            enabled: bool,
            label: str,
            min_value: float,
            max_value: float,
            min_widget: QWidget,
            max_widget: QWidget,
        ) -> None:
            if enabled and min_value > max_value:
                _add_issue(
                    f"{label}区间无效：最小值 {min_value:g} 不能大于最大值 {max_value:g}",
                    [min_widget, max_widget],
                )

        # 分辨率：自定义模式必须大于0
        if (
            self.resolution_check.isChecked()
            and normalize_resolution_preset(self.resolution_preset.currentText()) == "custom"
        ):
            if (
                self.resolution_width.value() <= 0
                or self.resolution_height.value() <= 0
            ):
                _add_issue(
                    "分辨率自定义宽高必须都大于 0",
                    [self.resolution_width, self.resolution_height],
                )

        # 画中画：背景模式必须提供有效文件
        if self.pip_check.isChecked() and self.pip_mode_background.isChecked():
            bg_path = self.pip_bg_path.text().strip()
            if not bg_path:
                _add_issue("画中画背景模式未选择背景文件", [self.pip_bg_path])
            elif not os.path.exists(bg_path):
                _add_issue("画中画背景文件不存在，请重新选择", [self.pip_bg_path])

        # 旋转随机角度区间
        _append_range_issue(
            self.rotate_check.isChecked() and self.flip_random.isChecked(),
            "随机角度",
            self.flip_random_angle.value(),
            self.flip_random_angle_max.value(),
            self.flip_random_angle,
            self.flip_random_angle_max,
        )

        # 画面微调区间
        _append_range_issue(
            self.frame_adjust_check.isChecked(),
            "亮度",
            self.brightness_min.value(),
            self.brightness_max.value(),
            self.brightness_min,
            self.brightness_max,
        )
        _append_range_issue(
            self.frame_adjust_check.isChecked(),
            "对比度",
            self.contrast_min.value(),
            self.contrast_max.value(),
            self.contrast_min,
            self.contrast_max,
        )
        _append_range_issue(
            self.frame_adjust_check.isChecked(),
            "饱和度",
            self.saturation_min.value(),
            self.saturation_max.value(),
            self.saturation_min,
            self.saturation_max,
        )
        _append_range_issue(
            self.frame_adjust_check.isChecked(),
            "锐化",
            self.sharpness_min.value(),
            self.sharpness_max.value(),
            self.sharpness_min,
            self.sharpness_max,
        )
        _append_range_issue(
            self.frame_adjust_check.isChecked(),
            "降噪",
            self.denoise_min.value(),
            self.denoise_max.value(),
            self.denoise_min,
            self.denoise_max,
        )

        # 帧率、抽帧、动态缩放、码率区间
        if hasattr(self, "fps_check"):
            _append_range_issue(
                self.fps_check.isChecked(),
                "帧率",
                self.fps_min.value(),
                self.fps_max.value(),
                self.fps_min,
                self.fps_max,
            )
        if hasattr(self, "frame_extract_check"):
            _append_range_issue(
                self.frame_extract_check.isChecked(),
                "抽帧",
                self.frame_extract_min.value(),
                self.frame_extract_max.value(),
                self.frame_extract_min,
                self.frame_extract_max,
            )
        if hasattr(self, "dynamic_zoom_check"):
            _append_range_issue(
                self.dynamic_zoom_check.isChecked(),
                "动态缩放",
                self.dynamic_zoom_min.value(),
                self.dynamic_zoom_max.value(),
                self.dynamic_zoom_min,
                self.dynamic_zoom_max,
            )
        if (
            hasattr(self, "bitrate_check")
            and self.bitrate_check.isChecked()
            and self.bitrate_mode_dynamic.isChecked()
        ):
            _append_range_issue(
                True,
                "码率倍率",
                self.bitrate_ratio_min.value(),
                self.bitrate_ratio_max.value(),
                self.bitrate_ratio_min,
                self.bitrate_ratio_max,
            )

        # 动态缩放高级参数区间
        if (
            hasattr(self, "dynamic_zoom_check")
            and self.dynamic_zoom_check.isChecked()
            and isinstance(self.dynamic_zoom_advanced_config, dict)
            and self.dynamic_zoom_advanced_config
        ):
            advanced = self.dynamic_zoom_advanced_config
            if advanced.get("start_min", 0.0) > advanced.get("start_max", 0.0):
                _add_issue(
                    "动态缩放高级参数「始于」区间无效：最小值不能大于最大值",
                    [self.dynamic_zoom_settings_btn],
                )
            if advanced.get("duration_min", 0.0) > advanced.get("duration_max", 0.0):
                _add_issue(
                    "动态缩放高级参数「历时」区间无效：最小值不能大于最大值",
                    [self.dynamic_zoom_settings_btn],
                )
            if advanced.get("loop", False) and advanced.get(
                "pause_min", 0.0
            ) > advanced.get("pause_max", 0.0):
                _add_issue(
                    "动态缩放高级参数「停留」区间无效：最小值不能大于最大值",
                    [self.dynamic_zoom_settings_btn],
                )

        # 去水印 API Key 校验（仅在 API 模式下要求）
        if self.remove_watermark_check.isChecked():
            try:
                method_key = self._get_watermark_method_key(
                    self.watermark_method_combo.currentIndex()
                )
            except Exception:
                method_key = ""
            if method_key == "api" and not self.api_key.text().strip():
                _add_issue("去水印选择了 API 模式，但未填写 API Key", [self.api_key])

        # 片头/片尾/边框：根据模式检查路径有效性
        def _check_path_mode(
            enabled: bool,
            mode_btn,
            path_text: str,
            title: str,
            exts: Set[str],
            path_widget: QWidget,
        ) -> None:
            if not enabled:
                return
            path = path_text.strip()
            mode = mode_btn.property("mode") if mode_btn else "file"
            if not path:
                _add_issue(f"{title}未选择文件或文件夹", [path_widget])
                return
            if mode == "folder":
                if not os.path.isdir(path):
                    _add_issue(f"{title}文件夹不存在或不可用", [path_widget])
                    return
                has_valid_file = any(
                    os.path.splitext(name)[1].lower() in exts
                    for name in os.listdir(path)
                    if os.path.isfile(os.path.join(path, name))
                )
                if not has_valid_file:
                    _add_issue(f"{title}文件夹内没有可用素材", [path_widget])
            else:
                if not os.path.isfile(path):
                    _add_issue(f"{title}文件不存在或不可用", [path_widget])
                elif os.path.splitext(path)[1].lower() not in exts:
                    _add_issue(f"{title}文件格式不支持", [path_widget])

        _check_path_mode(
            self.head_check.isChecked(),
            self.head_mode_btn if hasattr(self, "head_mode_btn") else None,
            self.head_file.text(),
            "片头",
            self._SUPPORTED_VIDEO_EXTS,
            self.head_file,
        )
        _check_path_mode(
            self.tail_check.isChecked(),
            self.tail_mode_btn if hasattr(self, "tail_mode_btn") else None,
            self.tail_file.text(),
            "片尾",
            self._SUPPORTED_VIDEO_EXTS,
            self.tail_file,
        )
        _check_path_mode(
            self.border_check.isChecked(),
            self.border_mode_btn if hasattr(self, "border_mode_btn") else None,
            self.border_file.text(),
            "边框",
            self._SUPPORTED_IMAGE_EXTS | self._SUPPORTED_VIDEO_EXTS,
            self.border_file,
        )

        # 输出目录如果已存在且不是目录，给出明确提示
        output_dir = self.output_path.text().strip()
        if output_dir and os.path.exists(output_dir) and not os.path.isdir(output_dir):
            _add_issue("输出位置指向了一个文件，请改为目录路径", [self.output_path])

        return issues

    def _collect_manual_input_issues(self) -> List[str]:
        """兼容旧调用：仅返回问题文本列表。"""
        return [message for message, _ in self._collect_manual_input_issue_details()]

    def _set_live_widget_invalid(self, widget: QWidget, invalid: bool) -> None:
        """设置单个控件的实时错误高亮样式。"""
        if widget is None:
            return
        if not isinstance(
            widget, (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton)
        ):
            return

        if invalid:
            if not hasattr(widget, "_live_prev_style"):
                widget._live_prev_style = widget.styleSheet()
            widget.setStyleSheet(
                (widget.styleSheet() or "")
                + "\n/* live-invalid */\nborder: 1px solid #EF4444;"
            )
            return

        prev_style = getattr(widget, "_live_prev_style", None)
        if prev_style is not None:
            widget.setStyleSheet(prev_style)
            delattr(widget, "_live_prev_style")
        else:
            # 输入控件兜底恢复
            if isinstance(widget, (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox)):
                ModernInput.apply_style(widget)

    def _clear_live_invalid_widgets(self) -> None:
        for widget in list(self._live_invalid_widgets):
            self._set_live_widget_invalid(widget, False)
        self._live_invalid_widgets.clear()

    def _register_live_validation_signal(self, widget, signal_name: str) -> None:
        """安全注册实时校验信号。"""
        if widget is None:
            return
        signal = getattr(widget, signal_name, None)
        if signal is None:
            return
        signal.connect(lambda *args: self._refresh_live_validation_feedback())

    def _setup_live_input_validation(self) -> None:
        """绑定关键输入控件，实现输入时即时反馈。"""
        watched_signals = [
            (getattr(self, "output_path", None), "textChanged"),
            (getattr(self, "pip_bg_path", None), "textChanged"),
            (getattr(self, "head_file", None), "textChanged"),
            (getattr(self, "tail_file", None), "textChanged"),
            (getattr(self, "border_file", None), "textChanged"),
            (getattr(self, "api_key", None), "textChanged"),
            (getattr(self, "watermark_method_combo", None), "currentIndexChanged"),
            (getattr(self, "resolution_check", None), "toggled"),
            (getattr(self, "resolution_preset", None), "currentTextChanged"),
            (getattr(self, "resolution_width", None), "valueChanged"),
            (getattr(self, "resolution_height", None), "valueChanged"),
            (getattr(self, "pip_check", None), "toggled"),
            (getattr(self, "pip_mode_background", None), "toggled"),
            (getattr(self, "rotate_check", None), "toggled"),
            (getattr(self, "flip_random", None), "toggled"),
            (getattr(self, "flip_random_angle", None), "valueChanged"),
            (getattr(self, "flip_random_angle_max", None), "valueChanged"),
            (getattr(self, "frame_adjust_check", None), "toggled"),
            (getattr(self, "brightness_min", None), "valueChanged"),
            (getattr(self, "brightness_max", None), "valueChanged"),
            (getattr(self, "contrast_min", None), "valueChanged"),
            (getattr(self, "contrast_max", None), "valueChanged"),
            (getattr(self, "saturation_min", None), "valueChanged"),
            (getattr(self, "saturation_max", None), "valueChanged"),
            (getattr(self, "sharpness_min", None), "valueChanged"),
            (getattr(self, "sharpness_max", None), "valueChanged"),
            (getattr(self, "denoise_min", None), "valueChanged"),
            (getattr(self, "denoise_max", None), "valueChanged"),
            (getattr(self, "fps_check", None), "toggled"),
            (getattr(self, "fps_min", None), "valueChanged"),
            (getattr(self, "fps_max", None), "valueChanged"),
            (getattr(self, "frame_extract_check", None), "toggled"),
            (getattr(self, "frame_extract_min", None), "valueChanged"),
            (getattr(self, "frame_extract_max", None), "valueChanged"),
            (getattr(self, "dynamic_zoom_check", None), "toggled"),
            (getattr(self, "dynamic_zoom_min", None), "valueChanged"),
            (getattr(self, "dynamic_zoom_max", None), "valueChanged"),
            (getattr(self, "bitrate_check", None), "toggled"),
            (getattr(self, "bitrate_mode_dynamic", None), "toggled"),
            (getattr(self, "bitrate_ratio_min", None), "valueChanged"),
            (getattr(self, "bitrate_ratio_max", None), "valueChanged"),
            (getattr(self, "remove_watermark_check", None), "toggled"),
            (getattr(self, "head_check", None), "toggled"),
            (getattr(self, "tail_check", None), "toggled"),
            (getattr(self, "border_check", None), "toggled"),
        ]
        for widget, signal_name in watched_signals:
            self._register_live_validation_signal(widget, signal_name)

        QTimer.singleShot(0, self._refresh_live_validation_feedback)

    def _refresh_live_validation_feedback(self) -> None:
        """即时刷新输入校验反馈（不弹窗）。"""
        if self.process_thread and self.process_thread.isRunning():
            return

        issue_details = self._collect_manual_input_issue_details()
        issues = [message for message, _ in issue_details]
        has_issues = bool(issues)
        invalid_widgets = {widget for _, widgets in issue_details for widget in widgets}

        self._clear_live_invalid_widgets()
        for widget in invalid_widgets:
            self._set_live_widget_invalid(widget, True)
        self._live_invalid_widgets = invalid_widgets

        if hasattr(self, "start_btn"):
            self.start_btn.setEnabled(not has_issues)
            self.start_btn.setToolTip(issues[0] if has_issues else "")

        if hasattr(self, "status_label"):
            self.status_label.setVisible(True)
            if has_issues:
                self.status_label.setStyleSheet(
                    f"color: {Theme.Warning}; font-size: 12px;"
                )
                self.status_label.setText(self._ts(f"参数待修正：{issues[0]}"))
            else:
                self.status_label.setStyleSheet(
                    f"color: {Theme.TextSecondary}; font-size: 12px;"
                )
                self.status_label.setText(self._ts("参数校验通过，可开始处理"))

    def _validate_manual_inputs_before_processing(self) -> bool:
        """处理前执行统一输入参数校验。"""
        issues = self._collect_manual_input_issues()
        if not issues:
            return True

        max_show = 8
        shown = issues[:max_show]
        remain = len(issues) - len(shown)
        detail = "\n".join(f"• {item}" for item in shown)
        if remain > 0:
            detail += f"\n• 其余 {remain} 项问题请修正后重试"
        self._warn("参数校验未通过", f"请先修正以下问题：\n{detail}")
        return False

    def _set_all_controls_enabled(self, enabled: bool) -> None:
        """处理中禁用/启用全部功能控件（start_btn 除外）"""
        self._is_processing = not enabled

        # 功能标签栏和所有标签页
        if hasattr(self, "tab_control"):
            self.tab_control.setEnabled(enabled)
        for page in getattr(self, "tab_pages", []):
            page.setEnabled(enabled)

        # 左侧面板按钮
        for attr in (
            "load_video_btn",
            "remove_btn",
            "clear_btn",
            "apply_params_to_all_check",
        ):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setEnabled(enabled)

        # 底部面板控件（start_btn 保持可用）
        for attr in (
            "output_path",
            "browse_btn",
            "folder_btn",
            "unified_output_check",
            "keep_structure",
            "setting_btn",
        ):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.setEnabled(enabled)

    def _update_controls_by_selection(self) -> None:
        """根据视频列表选中状态更新提示信息"""
        # 处理中不做选择联动（由 _set_all_controls_enabled 管理）
        if self._is_processing:
            return

        has_videos = bool(self.video_list)

        # 状态标签提示
        if hasattr(self, "status_label"):
            if not has_videos:
                self.status_label.setStyleSheet(
                    f"color: {Theme.TextSecondary}; font-size: 12px;"
                )
                self.status_label.setText(self._ts("请先导入视频文件"))
            else:
                # 有视频时由 _refresh_live_validation_feedback 管理
                self._refresh_live_validation_feedback()

    def _ensure_video_selected(self) -> None:
        """确保始终有一个视频被选中（列表不为空时）"""
        if not self.video_list:
            self.current_video_index = None
            return
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            # 尝试选中之前的索引，或第一行
            target = 0
            if self.current_video_index is not None:
                target = min(self.current_video_index, len(self.video_list) - 1)
            self.video_table.selectRow(target)

    def browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, self._ts("选择输出目录"), self.output_path.text()
        )
        if dir_path:
            self.output_path.setText(dir_path)

    def start_processing(self):
        """开始批量处理"""
        if not self.video_list:
            self._warn("警告", "请先添加视频文件")
            return

        # 必须选中视频才能开始处理
        if self.current_video_index is None:
            ModernMessageBox.warning(
                self, self._ts("提示"), self._ts("请先在左侧视频列表中选择一个视频后再进行操作")
            )
            return

        if self.process_thread and self.process_thread.isRunning():
            # 停止处理
            self.process_thread.stop()
            self.start_btn.setText(self._ts("正在停止..."))
            self.start_btn.setEnabled(False)
            self.progress_bar.setFormat(self._ts("%p% - 正在停止"))
            self.progress_bar.set_status(ProgressStatus.WARNING)

            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(self._ts(f"{timestamp} -> 已请求停止处理"))
            return

        checked_rows = self.get_checked_rows()
        if not checked_rows:
            self._warn("提示", "请先勾选需要处理的视频")
            return

        # 至少选择一个功能或参数
        if not self._has_any_processing_feature():
            QMessageBox.warning(
                self,
                t("batch.main_window.auto.006", "提示"),
                t("batch.main_window.auto.011", "请至少选择一个处理功能或参数后再开始处理"),
            )
            return

        # 文本输入校验
        if not self._validate_text_inputs_before_processing():
            return

        # 手动输入参数统一校验
        if not self._validate_manual_inputs_before_processing():
            return

        # 校验音频处理设置（仅在开启背景乐时检查路径）
        bgm_enabled = self.bgm_check.isChecked()
        if bgm_enabled:
            bgm_path = self.bgm_path.text().strip()
            if not bgm_path or not os.path.exists(bgm_path):
                self._warn("警告", "请选择有效的背景音乐文件或文件夹")
                return
            if os.path.isdir(bgm_path):
                audio_extensions = (".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg")
                has_audio = any(
                    os.path.splitext(f)[1].lower() in audio_extensions
                    for f in os.listdir(bgm_path)
                )
                if not has_audio:
                    self._warn("警告", "背景音乐文件夹中未找到可用音频文件")
                    return

        # 验证输出目录（可为空，默认同目录）
        output_dir = self.output_path.text().strip()
        if output_dir:
            # 如果目录不存在，尝试创建
            if not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                    from datetime import datetime

                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.process_log.append(
                        f"{timestamp} -> 已创建输出目录: {output_dir}"
                    )
                except Exception as e:
                    self._warn("错误", f"无法创建输出目录: {str(e)}")
                    return

        # 验证水印配置
        valid, _ = self._validate_watermark_settings()
        if not valid:
            return

        # 验证片头片尾文件
        if self.head_check.isChecked():
            head_file = self.head_file.text()
            if not head_file or not os.path.exists(head_file):
                self._warn("警告", "请选择有效的片头文件")
                return

        if self.tail_check.isChecked():
            tail_file = self.tail_file.text()
            if not tail_file or not os.path.exists(tail_file):
                self._warn("警告", "请选择有效的片尾文件")
                return

        if self.border_check.isChecked():
            border_file = self.border_file.text()
            if not border_file or not os.path.exists(border_file):
                self._warn("警告", "请选择有效的边框文件")
                return

        if not self._ensure_auth_code_before_processing():
            return

        # 保存当前参数（必要时同步到全部）
        self._persist_current_params()

        # 收集配置
        config = self.collect_config()

        # 根据勾选的视频构建处理队列（保留原始行号）
        selected_video_list = []
        for row in checked_rows:
            if row < len(self.video_list):
                video_info = self.video_list[row]
                video_info["row_index"] = row
                selected_video_list.append(video_info)

        # 创建处理线程
        self.process_thread = VideoProcessThread(selected_video_list, config)
        self.process_thread.progress_updated.connect(self.on_progress_updated)
        self.process_thread.video_status_updated.connect(self.on_video_status_updated)
        self.process_thread.finished.connect(self.on_processing_finished)

        # 启动处理
        self.process_thread.start()
        self.start_btn.setText(self._ts("停止处理"))
        self.start_btn.setEnabled(True)
        # 收起進度条中的文本（开始处理時）
        self.progress_bar.setFormat("%p%")
        self.progress_bar.set_status(ProgressStatus.PROCESSING)

        # 处理中禁用全部功能控件
        self._set_all_controls_enabled(False)

        # 记录日志
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.process_log.append(
            self._ts(f"{timestamp} -> 开始批量处理，共{len(selected_video_list)}个视频")
        )

    def show_options_dialog(self):
        """显示选项对话框"""
        import traceback

        try:
            root_dir = Path(__file__).resolve().parents[2]
            app_info_path = root_dir / "config" / "app_info.py"
            options_ini_path = root_dir / "config" / "options.ini"
            logger.info(
                "[Options] show_options_dialog start "
                f"cwd={os.getcwd()} exe={sys.executable} "
                f"app_info_exists={app_info_path.exists()} "
                f"options_ini_exists={options_ini_path.exists()}"
            )

            from ui.options_dialog import OptionsDialog

            update_svc = getattr(self, "_update_service", None)
            dialog = OptionsDialog(self, self.config, update_service=update_svc)
            dialog.config_updated.connect(self.on_config_updated)
            dialog.language_changed.connect(self._on_language_changed)
            dialog.exec()
        except Exception:
            error_detail = traceback.format_exc()
            logger.error(f"[Options] show_options_dialog failed:\n{error_detail}")
            raise

    def on_config_updated(self, config: dict):
        """配置更新时的回调"""
        self.config = config
        self._language_manager.set_language(self.config.get("ui_language", LANG_ZH))

        # 记录日志
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.process_log.append(f"{timestamp} -> 配置已更新")

    def _validate_watermark_settings(self) -> Tuple[bool, List[dict]]:
        """验证水印配置是否完整有效"""
        if not self.add_watermark_check.isChecked():
            return True, []

        configs, errors = self._collect_watermark_configs(collect_errors=True)
        if not configs:
            message = "\n".join(errors) if errors else "请至少配置一个有效的水印"
            self._warn("警告", message)
            return False, []

        if errors:
            QMessageBox.warning(
                self,
                t("batch.main_window.auto.006", "提示"),
                t("batch.main_window.auto.012", "部分水印将被忽略：\n") + "\n".join(errors),
            )

        return True, configs

    def collect_config(self) -> Dict:
        """收集所有配置参数"""
        config = {
            # 去水印参数
            "remove_watermark": {
                "enabled": self.remove_watermark_check.isChecked(),
                "method": self._get_watermark_method_key(
                    self.watermark_method_combo.currentIndex()
                ),
                "region_count": self.region_count_combo.currentIndex(),
                "regions": self._get_watermark_regions(),
                "watermark_preset": normalize_watermark_preset(
                    self.watermark_preset.currentData()
                    if self.watermark_preset.currentData() is not None
                    else self.watermark_preset.currentText()
                )
                if hasattr(self, "watermark_preset")
                else "custom",  # 收集预设平台信息
                "ffmpeg_crf": self.ffmpeg_crf.value(),
                "ffmpeg_preset": self.ffmpeg_preset.currentText(),
                "api_provider": self.api_provider.currentText(),
                "api_key": self.api_key.text(),
                # 时间段去水印设置
                "time_period_enabled": self.time_period_enabled,
                "time_period_start": self.time_period_start,
                "time_period_end": self.time_period_end,
                # TEXT-REMOVER参数（手动框选字幕）
                "textremover": {
                    "method": "copy"
                    if (
                        self.textremover_method.currentIndex() == 0
                        if hasattr(self, "textremover_method")
                        else True
                    )
                    else "blur",
                    "blur_strength": self.textremover_blur_strength.value()
                    if hasattr(self, "textremover_blur_strength")
                    else 3,
                }
                if hasattr(self, "textremover_method")
                else {},
                # OpenCV参数
                "opencv": {
                    "method": "copy"
                    if (
                        self.opencv_method.currentIndex() == 0
                        if hasattr(self, "opencv_method")
                        else True
                    )
                    else "blur",
                    "blur_strength": self.opencv_blur_strength.value()
                    if hasattr(self, "opencv_blur_strength")
                    else 3,
                }
                if hasattr(self, "opencv_method")
                else {},
                # 兼容旧的region1/region2格式
                "region1": {
                    "w": self.region1_w.value(),
                    "h": self.region1_h.value(),
                    "x": self.region1_x.value(),
                    "y": self.region1_y.value(),
                },
                "region2": {
                    "w": self.region2_w.value(),
                    "h": self.region2_h.value(),
                    "x": self.region2_x.value(),
                    "y": self.region2_y.value(),
                },
            },
            # 加水印参数
            "add_watermark": {
                "enabled": self.add_watermark_check.isChecked(),
                "watermarks": self._collect_watermark_configs(collect_errors=False)[0],
            },
            # 裁剪参数
            "crop": {
                "enabled": self.crop_check.isChecked(),
                "mode": self._get_crop_mode(),
                "pixel_top": self.crop_pixel_top.value(),
                "pixel_bottom": self.crop_pixel_bottom.value(),
                "pixel_left": self.crop_pixel_left.value(),
                "pixel_right": self.crop_pixel_right.value(),
                "aspect_ratio": self.crop_middle_ratio.currentText(),
                "percent_value": self.crop_percent_value.value(),
                "percent_crop_mode": normalize_crop_percent_position(
                    self.crop_percent_mode.currentText()
                ),
                "random_crop": False,  # 暂不支持随机
            },
            # 画中画参数
            "pip": {
                "enabled": self.pip_check.isChecked(),
                "mode": "video" if self.pip_mode_video.isChecked() else "background",
                # 视频模式参数
                "video_margin_top": self.pip_margin_top.value(),
                "video_margin_left": self.pip_margin_left.value(),
                "video_blur_enabled": self.pip_video_blur_check.isChecked(),
                "video_blur_strength": self.pip_video_blur.value(),
                "video_opacity": self.pip_video_opacity.value(),
                "video_size_percent": self.pip_video_size.value(),
                # 背景模式参数
                "background_path": self.pip_bg_path.text(),
                "background_offset_x": self.pip_bg_offset_x.value(),
                "background_offset_y": self.pip_bg_offset_y.value(),
                "background_opacity": self.pip_bg_opacity.value(),
                "background_size_percent": self.pip_bg_size.value(),
            },
            # 去头尾参数
            "trim": {
                "enabled": self.trim_check.isChecked(),
                "mode": "trim_edges" if self.trim_mode1_radio.isChecked() else "clip_range",
                "head": self.trim_head.value(),
                "tail": self.trim_tail.value(),
                "start": self.trim_start.value(),
                "duration": self.trim_duration.value(),
            },
            # 加头尾参数
            "add_head_tail": {
                # 片头配置
                "head_enabled": self.head_check.isChecked(),
                "head_file": self.head_file.text(),
                "head_mode": self.head_mode_btn.property("mode"),
                "head_random": (
                    self.head_random_check.isChecked()
                    and self.head_check.isChecked()
                    and self.head_mode_btn.property("mode") == "folder"
                ),
                # 片尾配置
                "tail_enabled": self.tail_check.isChecked(),
                "tail_file": self.tail_file.text(),
                "tail_mode": self.tail_mode_btn.property("mode"),
                "tail_random": (
                    self.tail_random_check.isChecked()
                    and self.tail_check.isChecked()
                    and self.tail_mode_btn.property("mode") == "folder"
                ),
                # 边框配置
                "border_enabled": self.border_check.isChecked(),
                "border_file": self.border_file.text(),
                "border_mode": self.border_mode_btn.property("mode"),
                "border_random": self.border_style_config.get("border_random", False),
                # 边框样式
                "border_opacity_min": self.border_style_config.get("opacity_min", 1.0),
                "border_opacity_max": self.border_style_config.get("opacity_max", 1.0),
                "border_margin_x": self.border_style_config.get("margin_x", 0),
                "border_margin_y": self.border_style_config.get("margin_y", 0),
                "border_remove_bg": self.border_style_config.get("remove_bg", False),
                "border_bg_method": self.border_style_config.get(
                    "bg_method", "video_color"
                ),
                "border_bg_x": self.border_style_config.get("bg_x", 0),
                "border_bg_y": self.border_style_config.get("bg_y", 0),
                "border_bg_time": self.border_style_config.get("bg_time", 0.0),
                "border_bg_color": self.border_style_config.get("bg_color", "#00FF00"),
                "border_bg_similarity": self.border_style_config.get(
                    "bg_similarity", 0.10
                ),
                "border_bg_blend": self.border_style_config.get("bg_blend", 0.30),
            },
            # 变速参数
            "speed": {
                "enabled": self.speed_check.isChecked(),
                "min": self.speed_min.value(),
                "max": self.speed_max.value(),
                "segment_enabled": self.speed_segment_check.isChecked(),
                "segment_duration": self.speed_segment_duration.value(),
                "pitch_enabled": self.speed_pitch_check.isChecked(),
                "min_duration_enabled": self.speed_min_duration_check.isChecked(),
                "min_duration": self.speed_min_duration.value(),
            },
            # 文本参数
            "text": {
                "text1_enabled": self.text1_check.isChecked(),
                "text1_config": self.text_configs[0],
                "text2_enabled": self.text2_check.isChecked(),
                "text2_config": self.text_configs[1],
                "text3_enabled": self.text3_check.isChecked(),
                "text3_config": self.text_configs[2],
            },
            # 背景音参数
            "audio": {
                "bgm_enabled": self.bgm_check.isChecked(),
                "bgm_mode": self.bgm_mode,  # 'file' or 'dir'
                "bgm_path": self.bgm_path.text(),
                "bgm_volume": self.bgm_volume.value(),
                "bgm_fade_enabled": self.bgm_fadein_check.isChecked(),
                "bgm_fade_duration": self.bgm_fadein_duration.value(),
                "bgm_delay_enabled": self.bgm_delay_check.isChecked(),
                "bgm_delay": self.bgm_delay.value(),
                "original_volume_enabled": self.original_volume_check.isChecked(),
                "original_volume": self.original_volume.value(),
                "original_fade_sync": self.original_fade_sync_check.isChecked(),
                "enable_loop": self.bgm_loop_check.isChecked(),
                "enable_random": (
                    self.bgm_random_check.isChecked()
                    and self.bgm_check.isChecked()
                    and self.bgm_mode == "dir"
                ),
            },
            # 画面调整参数
            "frame_adjust": {
                "enabled": self.frame_adjust_check.isChecked(),
                "brightness_min": self.brightness_min.value(),
                "brightness_max": self.brightness_max.value(),
                "sharpness_min": self.sharpness_min.value(),
                "sharpness_max": self.sharpness_max.value(),
                "contrast_min": self.contrast_min.value(),
                "contrast_max": self.contrast_max.value(),
                "denoise_min": self.denoise_min.value(),
                "denoise_max": self.denoise_max.value(),
                "saturation_min": self.saturation_min.value(),
                "saturation_max": self.saturation_max.value(),
            },
            # 几宫格分屏参数
            "grid_split": {
                "enabled": self.grid_split_check.isChecked(),
                "count": self.grid_count.value(),
                "direction": normalize_grid_direction(self.grid_direction.currentText()),
                "blur": self.grid_blur_check.isChecked(),
            },
            # 分辨率参数
            "resolution": {
                "enabled": self.resolution_check.isChecked(),
                "preset": normalize_resolution_preset(
                    self.resolution_preset.currentText()
                ),
                "width": self.resolution_width.value(),
                "height": self.resolution_height.value(),
            },
            # 模式参数
            "mode": {
                "stretch": self.mode_stretch.isChecked(),
                "crop": self.mode_crop.isChecked(),
                "original": self.mode_original.isChecked(),
                "background_blur": self.background_blur_check.isChecked(),
                "reflection": self.reflection_check.isChecked(),
                "reflection_opacity": self.reflection_opacity.value(),
            },
            # 旋转&翻转参数
            "rotate_flip": {
                "enabled": self.rotate_check.isChecked(),
                "left90": self.flip_left90.isChecked(),
                "right90": self.flip_right90.isChecked(),
                "horizontal": self.flip_horizontal.isChecked(),
                "vertical": self.flip_vertical.isChecked(),
                "random_direction": self.flip_random_direction.isChecked(),
                "random_angle": self.flip_random.isChecked(),
                "random_angle_min": self.flip_random_angle.value(),
                "random_angle_max": self.flip_random_angle_max.value(),
                "complete_display": self.flip_complete_check.isChecked(),
                "black_edge_remove": self.flip_black_edge_check.isChecked(),
            },
            # 帧率参数
            "fps": {
                "enabled": self.fps_check.isChecked()
                if hasattr(self, "fps_check")
                else False,
                "min": self.fps_min.value() if hasattr(self, "fps_min") else 24.0,
                "max": self.fps_max.value() if hasattr(self, "fps_max") else 30.0,
                "remove_duplicate": self.remove_duplicate_frames_check.isChecked()
                if hasattr(self, "remove_duplicate_frames_check")
                else False,
            },
            # 抽帧参数
            "frame_extract": {
                "enabled": self.frame_extract_check.isChecked()
                if hasattr(self, "frame_extract_check")
                else False,
                "min": self.frame_extract_min.value()
                if hasattr(self, "frame_extract_min")
                else 25,
                "max": self.frame_extract_max.value()
                if hasattr(self, "frame_extract_max")
                else 30,
                "audio_speed": self.audio_speed_check.isChecked()
                if hasattr(self, "audio_speed_check")
                else False,
            },
            # 动态缩放参数
            "dynamic_zoom": {
                "enabled": self.dynamic_zoom_check.isChecked()
                if hasattr(self, "dynamic_zoom_check")
                else False,
                "min": self.dynamic_zoom_min.value()
                if hasattr(self, "dynamic_zoom_min")
                else 1.0,
                "max": self.dynamic_zoom_max.value()
                if hasattr(self, "dynamic_zoom_max")
                else 1.15,
                "advanced": self.dynamic_zoom_advanced_config,  # 高级设置对话框
            },
            # 码率参数
            "bitrate": {
                "enabled": self.bitrate_check.isChecked()
                if hasattr(self, "bitrate_check")
                else False,
                "mode_dynamic": self.bitrate_mode_dynamic.isChecked()
                if hasattr(self, "bitrate_mode_dynamic")
                else True,
                "mode_fixed": self.bitrate_mode_fixed.isChecked()
                if hasattr(self, "bitrate_mode_fixed")
                else False,
                "dynamic_value": self.bitrate_dynamic_value.value()
                if hasattr(self, "bitrate_dynamic_value")
                else 23,
                "fixed_value": self.bitrate_fixed_preset.currentText()
                if hasattr(self, "bitrate_fixed_preset")
                else "3000",  # 使用下拉框文本
                "ratio_min": self.bitrate_ratio_min.value()
                if hasattr(self, "bitrate_ratio_min")
                else 0.8,
                "ratio_max": self.bitrate_ratio_max.value()
                if hasattr(self, "bitrate_ratio_max")
                else 1.2,
            },
            # 色调调整（对话框参数）
            "color_tone": self.color_tone_config,
            # LUT滤镜（对话框参数）
            "lut_filter": self.lut_filter_config,
            # 更多效果（对话框参数）
            "more_effects": self.more_effects_config,
            # 输出参数
            "output": {
                "path": self.output_path.text(),
                "overwrite_original": False,
                "keep_structure": self.keep_structure.isChecked(),
            },
            # 全局配置（从选项对话框）
            "global_options": self.config,
        }
        return config

    def _snapshot_current_params(self) -> Dict:
        """获取当前参数快照"""
        return copy.deepcopy(self.collect_config())

    def _save_params_to_video(self, index: Optional[int], config: Dict) -> None:
        """保存参数到指定视频条目"""
        if index is None:
            return
        if 0 <= index < len(self.video_list):
            self.video_list[index]["params"] = copy.deepcopy(config)
            self._update_video_status_indicator(index)

    def _sync_params_to_all(self, config: Dict) -> None:
        """同步参数到全部视频"""
        for i in range(len(self.video_list)):
            self.video_list[i]["params"] = copy.deepcopy(config)
        # 更新所有视频的状态指示器
        for row in range(self.video_table.rowCount()):
            self._update_video_status_indicator(row)

    def _persist_current_params(self) -> None:
        """保存当前参数（必要时同步到全部）"""
        if not self.video_list:
            return
        if self.current_video_index is None:
            selected_rows = self.get_selected_rows()
            if not selected_rows:
                return
            self.current_video_index = selected_rows[0]
        snapshot = self._snapshot_current_params()
        self._save_params_to_video(self.current_video_index, snapshot)
        if self.apply_params_to_all:
            self._sync_params_to_all(snapshot)

    # ========== 视频状态指示器 ==========

    def _get_default_params(self) -> Dict:
        """获取默认参数快照（用于对比是否修改了参数）"""
        if not hasattr(self, "_cached_default_params"):
            self._cached_default_params = self.collect_config()
        return self._cached_default_params

    def _has_custom_params(self, index: int) -> bool:
        """判断指定视频是否有自定义（非默认）参数"""
        if index < 0 or index >= len(self.video_list):
            return False
        params = self.video_list[index].get("params")
        if params is None:
            return False
        # 比较关键的 enabled 开关即可，避免深度比较的性能开销
        default = self._get_default_params()
        for key in params:
            if isinstance(params[key], dict) and "enabled" in params[key]:
                if params[key].get("enabled") != default.get(key, {}).get("enabled"):
                    return True
            elif isinstance(params[key], dict):
                for sub_key, sub_val in params[key].items():
                    default_sub = default.get(key, {}).get(sub_key)
                    if sub_val != default_sub:
                        return True
            else:
                if params[key] != default.get(key):
                    return True
        return False

    def _split_status(self, status_text: str) -> Tuple[str, str]:
        raw = (status_text or "").strip()
        if raw.startswith("error:"):
            return "failed", raw.split(":", 1)[1].strip()
        return normalize_status_code(raw, default_code="pending"), ""

    def _status_display_text(self, status_text: str) -> str:
        status_code, detail = self._split_status(status_text)
        label = enum_label(STATUS_LABELS, status_code, self._language_manager.language)
        if detail:
            return f"{label}: {detail}"
        return label

    def _create_status_widget(
        self, status_text: str = "pending", has_custom_params: bool = False
    ) -> QWidget:
        """创建状态列的组合控件（圆点 + 状态文字）"""
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 圆点指示器
        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setObjectName("status_dot")

        # 状态文字
        label = QLabel(self._status_display_text(status_text))
        label.setObjectName("status_text")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"font-size: 12px; color: {Theme.TextSecondary}; background: transparent;"
        )

        layout.addWidget(dot)
        layout.addWidget(label)

        # 根据状态设置圆点颜色
        self._apply_dot_style(dot, label, status_text, has_custom_params)

        return widget

    def _apply_dot_style(
        self, dot: QLabel, label: QLabel, status_text: str, has_custom_params: bool
    ) -> None:
        """根据状态设置圆点样式和提示"""
        # 处理状态优先级：处理中 > 完成 > 失败 > 已修改参数 > 无
        status, _detail = self._split_status(status_text)
        if status == "processing":
            dot.setVisible(True)
            dot.setStyleSheet(f"background-color: {Theme.Warning}; border-radius: 4px;")
            dot.setToolTip(self._status_display_text("processing"))
        elif status == "done":
            dot.setVisible(True)
            dot.setStyleSheet(f"background-color: {Theme.Success}; border-radius: 4px;")
            dot.setToolTip(self._status_display_text("done"))
        elif status == "failed":
            dot.setVisible(True)
            dot.setStyleSheet(f"background-color: {Theme.Error}; border-radius: 4px;")
            dot.setToolTip(self._status_display_text("failed"))
        elif status == "skipped":
            dot.setVisible(True)
            dot.setStyleSheet(
                f"background-color: {Theme.TextDisabled}; border-radius: 4px;"
            )
            dot.setToolTip(self._status_display_text("skipped"))
        elif has_custom_params:
            dot.setVisible(True)
            dot.setStyleSheet(f"background-color: {Theme.Primary}; border-radius: 4px;")
            dot.setToolTip(t("batch.main_window.auto.013", "已自定义参数"))
        else:
            dot.setVisible(False)
            dot.setToolTip("")

    def _update_video_status_indicator(self, row: int, status_text: str = None) -> None:
        """更新指定行的状态指示器"""
        if row < 0 or row >= self.video_table.rowCount():
            return

        # 获取当前状态文字
        if status_text is None:
            existing_widget = self.video_table.cellWidget(row, self.COL_STATUS)
            if existing_widget:
                item = self.video_table.item(row, self.COL_STATUS)
                status_text = (
                    str(item.data(Qt.ItemDataRole.UserRole)).strip()
                    if item and item.data(Qt.ItemDataRole.UserRole)
                    else "pending"
                )
            else:
                item = self.video_table.item(row, self.COL_STATUS)
                status_text = (
                    str(item.data(Qt.ItemDataRole.UserRole)).strip()
                    if item and item.data(Qt.ItemDataRole.UserRole)
                    else "pending"
                )

        # 判断是否有自定义参数
        has_custom = (
            self._has_custom_params(row) if row < len(self.video_list) else False
        )

        # 创建或更新状态控件
        existing_widget = self.video_table.cellWidget(row, self.COL_STATUS)
        if existing_widget:
            dot = existing_widget.findChild(QLabel, "status_dot")
            label = existing_widget.findChild(QLabel, "status_text")
            if dot and label:
                label.setText(self._status_display_text(status_text))
                self._apply_dot_style(dot, label, status_text, has_custom)
                # 同步更新底层 item 的状态数据（但不设置文本，防止重影）
                item = self.video_table.item(row, self.COL_STATUS)
                if item:
                    item.setText("")  # 设为空防止重影
                    item.setData(Qt.ItemDataRole.UserRole, status_text.strip())
                return

        # 没有现有控件，创建新的
        widget = self._create_status_widget(status_text, has_custom)
        self.video_table.setCellWidget(row, self.COL_STATUS, widget)
        # 同时保留一个 item 用于数据读取（文本设为空，防止重影）
        item = QTableWidgetItem("")
        item.setData(Qt.ItemDataRole.UserRole, status_text.strip())
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_table.setItem(row, self.COL_STATUS, item)

    def _get_status_text(self, row: int) -> str:
        """从状态列获取状态文字（兼容 cellWidget 和 item）"""
        # 1. 优先尝试从 item UserRole 读取（内部状态 code）
        item = self.video_table.item(row, self.COL_STATUS)
        if item:
            user_data = item.data(Qt.ItemDataRole.UserRole)
            if user_data:
                return str(user_data).strip()

        # 1. 优先尝试从 widget 读取
        widget = self.video_table.cellWidget(row, self.COL_STATUS)
        if widget:
            label = widget.findChild(QLabel, "status_text")
            if label:
                return label.text().strip()

        return ""

    def _set_combo_by_code(self, combo: QComboBox, code: str, labels: Dict[str, Dict[str, str]]) -> None:
        """按 code 设置下拉框显示值（兼容文本项和 userData）。"""
        if combo is None:
            return

        data_index = combo.findData(code)
        if data_index >= 0:
            combo.setCurrentIndex(data_index)
            return

        for candidate in (
            enum_label(labels, code, LANG_ZH),
            enum_label(labels, code, LANG_EN),
            code,
        ):
            text_index = combo.findText(candidate)
            if text_index >= 0:
                combo.setCurrentIndex(text_index)
                return

    def _apply_params_to_ui(self, config: Dict) -> None:
        """将配置应用到界面控件"""
        if not config:
            return

        remove = config.get("remove_watermark", {})
        if hasattr(self, "remove_watermark_check"):
            self.remove_watermark_check.setChecked(bool(remove.get("enabled", False)))
        if hasattr(self, "watermark_method_combo"):
            method_key = remove.get("method")
            method_index = 1 if method_key == "ffmpeg" else 0
            self.watermark_method_combo.setCurrentIndex(method_index)
        if hasattr(self, "region_count_combo"):
            self.region_count_combo.setCurrentIndex(
                int(remove.get("region_count", 0) or 0)
            )
        if hasattr(self, "watermark_preset") and remove.get("watermark_preset"):
            preset_code = normalize_watermark_preset(remove.get("watermark_preset"))
            self._set_combo_by_code(self.watermark_preset, preset_code, WATERMARK_PRESET_LABELS)
        if hasattr(self, "ffmpeg_crf"):
            self.ffmpeg_crf.setValue(remove.get("ffmpeg_crf", self.ffmpeg_crf.value()))
        if hasattr(self, "ffmpeg_preset") and remove.get("ffmpeg_preset"):
            self.ffmpeg_preset.setCurrentText(remove.get("ffmpeg_preset"))
        if hasattr(self, "api_provider") and remove.get("api_provider"):
            self.api_provider.setCurrentText(remove.get("api_provider"))
        if hasattr(self, "api_key"):
            self.api_key.setText(remove.get("api_key", ""))
        self.time_period_enabled = bool(remove.get("time_period_enabled", False))
        self.time_period_start = float(remove.get("time_period_start", 0.0))
        self.time_period_end = float(remove.get("time_period_end", 0.0))

        textremover = remove.get("textremover", {})
        if hasattr(self, "textremover_method"):
            method_index = 0 if textremover.get("method", "copy") == "copy" else 1
            self.textremover_method.setCurrentIndex(method_index)
        if hasattr(self, "textremover_blur_strength"):
            self.textremover_blur_strength.setValue(
                textremover.get("blur_strength", self.textremover_blur_strength.value())
            )

        opencv = remove.get("opencv", {})
        if hasattr(self, "opencv_method"):
            method_index = 0 if opencv.get("method", "copy") == "copy" else 1
            self.opencv_method.setCurrentIndex(method_index)
        if hasattr(self, "opencv_blur_strength"):
            self.opencv_blur_strength.setValue(
                opencv.get("blur_strength", self.opencv_blur_strength.value())
            )

        region1 = remove.get("region1", {})
        if hasattr(self, "region1_w"):
            self.region1_w.setValue(region1.get("w", self.region1_w.value()))
            self.region1_h.setValue(region1.get("h", self.region1_h.value()))
            self.region1_x.setValue(region1.get("x", self.region1_x.value()))
            self.region1_y.setValue(region1.get("y", self.region1_y.value()))
        region2 = remove.get("region2", {})
        if hasattr(self, "region2_w"):
            self.region2_w.setValue(region2.get("w", self.region2_w.value()))
            self.region2_h.setValue(region2.get("h", self.region2_h.value()))
            self.region2_x.setValue(region2.get("x", self.region2_x.value()))
            self.region2_y.setValue(region2.get("y", self.region2_y.value()))

        add_wm = config.get("add_watermark", {})
        if hasattr(self, "add_watermark_check"):
            self.add_watermark_check.setChecked(bool(add_wm.get("enabled", False)))
        watermark_list = add_wm.get("watermarks", []) or []
        if len(watermark_list) > self.MAX_WATERMARKS:
            if hasattr(self, "process_log"):
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(
                    f"{timestamp} -> 加水印配置超过上限，仅保留前{self.MAX_WATERMARKS}个"
                )
            watermark_list = watermark_list[: self.MAX_WATERMARKS]
        if hasattr(self, "watermark_widgets"):
            while len(self.watermark_widgets) < len(watermark_list):
                self.create_watermark_config_widget(len(self.watermark_widgets))
            while len(self.watermark_widgets) > max(1, len(watermark_list)):
                self._remove_watermark_widget_silent(len(self.watermark_widgets) - 1)
            for idx, wm in enumerate(watermark_list):
                if idx >= len(self.watermark_widgets):
                    break
                widget_dict = self.watermark_widgets[idx]
                wm_type = wm.get("type", "image")
                type_index = widget_dict["type_combo"].findData(wm_type)
                if type_index < 0:
                    type_index = 0 if wm_type == "image" else 1
                widget_dict["type_combo"].setCurrentIndex(type_index)
                self.on_single_watermark_type_changed(idx, type_index)
                file_mode = wm.get("file_mode", "file")
                if widget_dict.get("file_mode") != file_mode:
                    self.toggle_single_file_mode(idx)
                widget_dict["file_path"].setText(wm.get("file_path", ""))
                if file_mode == "folder":
                    widget_dict["random_check"].setEnabled(True)
                    widget_dict["random_check"].setChecked(
                        bool(wm.get("random_select", False))
                    )
                else:
                    widget_dict["random_check"].setEnabled(False)
                    widget_dict["random_check"].setChecked(False)
                if "scroll_check" in widget_dict:
                    widget_dict["scroll_check"].setChecked(
                        bool(wm.get("scroll", False))
                    )
                if "diagonal_check" in widget_dict:
                    widget_dict["diagonal_check"].setChecked(
                        bool(wm.get("diagonal", False))
                    )
                position = (
                    wm.get("image_position")
                    if wm_type == "image"
                    else wm.get("text_position")
                )
                if wm_type == "image":
                    if position:
                        self._set_combo_by_code(
                            widget_dict["position_combo"],
                            normalize_text_position(position),
                            TEXT_POSITION_LABELS,
                        )
                    widget_dict["offset_x"].setValue(
                        wm.get("offset_x", widget_dict["offset_x"].value())
                    )
                    widget_dict["offset_y"].setValue(
                        wm.get("offset_y", widget_dict["offset_y"].value())
                    )
                    widget_dict["opacity"].setValue(
                        wm.get("opacity", widget_dict["opacity"].value())
                    )
                else:
                    if position:
                        self._set_combo_by_code(
                            widget_dict["text_position"],
                            normalize_text_position(position),
                            TEXT_POSITION_LABELS,
                        )
                    widget_dict["text_content"].setText(wm.get("text_content", ""))
                    widget_dict["text_opacity"].setValue(
                        wm.get("text_opacity", widget_dict["text_opacity"].value())
                    )
                if idx < len(self.watermark_configs):
                    self.watermark_configs[idx] = copy.deepcopy(wm)
                self._sync_watermark_config_from_widget(widget_dict)
            self._update_watermark_add_button_state()

        crop = config.get("crop", {})
        if hasattr(self, "crop_check"):
            self.crop_check.setChecked(bool(crop.get("enabled", False)))
        crop_mode = normalize_crop_mode(crop.get("mode", "pixel"))
        if hasattr(self, "crop_method_pixel") and crop_mode == "pixel":
            self.crop_method_pixel.setChecked(True)
        if hasattr(self, "crop_method_middle") and crop_mode == "center":
            self.crop_method_middle.setChecked(True)
        if hasattr(self, "crop_method_percent") and crop_mode == "percent":
            self.crop_method_percent.setChecked(True)
        if hasattr(self, "crop_pixel_top"):
            self.crop_pixel_top.setValue(
                crop.get("pixel_top", self.crop_pixel_top.value())
            )
            self.crop_pixel_bottom.setValue(
                crop.get("pixel_bottom", self.crop_pixel_bottom.value())
            )
            self.crop_pixel_left.setValue(
                crop.get("pixel_left", self.crop_pixel_left.value())
            )
            self.crop_pixel_right.setValue(
                crop.get("pixel_right", self.crop_pixel_right.value())
            )
        if hasattr(self, "crop_middle_ratio") and crop.get("aspect_ratio"):
            self.crop_middle_ratio.setCurrentText(crop.get("aspect_ratio"))
        if hasattr(self, "crop_percent_value"):
            self.crop_percent_value.setValue(
                crop.get("percent_value", self.crop_percent_value.value())
            )
        if hasattr(self, "crop_percent_mode") and crop.get("percent_crop_mode"):
            percent_code = normalize_crop_percent_position(crop.get("percent_crop_mode"))
            self._set_combo_by_code(
                self.crop_percent_mode,
                percent_code,
                CROP_PERCENT_POSITION_LABELS,
            )

        pip = config.get("pip", {})
        if hasattr(self, "pip_check"):
            self.pip_check.setChecked(bool(pip.get("enabled", False)))
        if hasattr(self, "pip_mode_video") and hasattr(self, "pip_mode_bg"):
            if pip.get("mode", "video") == "video":
                self.pip_mode_video.setChecked(True)
            else:
                self.pip_mode_bg.setChecked(True)
        if hasattr(self, "pip_margin_top"):
            self.pip_margin_top.setValue(
                pip.get("video_margin_top", self.pip_margin_top.value())
            )
            self.pip_margin_left.setValue(
                pip.get("video_margin_left", self.pip_margin_left.value())
            )
            self.pip_video_blur_check.setChecked(
                bool(pip.get("video_blur_enabled", False))
            )
            self.pip_video_blur.setValue(
                pip.get("video_blur_strength", self.pip_video_blur.value())
            )
            self.pip_video_opacity.setValue(
                pip.get("video_opacity", self.pip_video_opacity.value())
            )
            self.pip_video_size.setValue(
                pip.get("video_size_percent", self.pip_video_size.value())
            )
        if hasattr(self, "pip_bg_path"):
            self.pip_bg_path.setText(pip.get("background_path", ""))
            self.pip_bg_offset_x.setValue(
                pip.get("background_offset_x", self.pip_bg_offset_x.value())
            )
            self.pip_bg_offset_y.setValue(
                pip.get("background_offset_y", self.pip_bg_offset_y.value())
            )
            self.pip_bg_opacity.setValue(
                pip.get("background_opacity", self.pip_bg_opacity.value())
            )
            self.pip_bg_size.setValue(
                pip.get("background_size_percent", self.pip_bg_size.value())
            )

        trim = config.get("trim", {})
        if hasattr(self, "trim_check"):
            self.trim_check.setChecked(bool(trim.get("enabled", False)))
        if hasattr(self, "trim_mode1_radio") and hasattr(self, "trim_mode2_radio"):
            if normalize_trim_mode(trim.get("mode", "trim_edges")) == "trim_edges":
                self.trim_mode1_radio.setChecked(True)
            else:
                self.trim_mode2_radio.setChecked(True)
        if hasattr(self, "trim_head"):
            self.trim_head.setValue(trim.get("head", self.trim_head.value()))
            self.trim_tail.setValue(trim.get("tail", self.trim_tail.value()))
            self.trim_start.setValue(trim.get("start", self.trim_start.value()))
            self.trim_duration.setValue(
                trim.get("duration", self.trim_duration.value())
            )

        head_tail = config.get("add_head_tail", {})
        if hasattr(self, "head_check"):
            self.head_check.setChecked(bool(head_tail.get("head_enabled", False)))
        if hasattr(self, "head_file"):
            self.head_file.setText(head_tail.get("head_file", ""))
        if hasattr(self, "head_mode_btn"):
            head_mode = head_tail.get("head_mode", "file")
            if head_mode == "folder":
                self.head_mode_btn.setIcon(load_svg_icon("folder", 14, "#64748B"))
                self.head_mode_btn.setProperty("mode", "folder")
                self.head_mode_btn.setText(t("batch.main_window.auto.014", "文件夹"))
                self.head_mode_btn.setToolTip(
                    t(
                        "batch.main_window.auto.015",
                        "当前：文件夹模式（可随机选取，点击切换到文件模式）",
                    )
                )
                if hasattr(self, "head_browse_btn"):
                    self.head_browse_btn.setText(t("batch.main_window.auto.016", "选择目录"))
                if hasattr(self, "head_file"):
                    self.head_file.setPlaceholderText(
                        t("batch.main_window.auto.017", "未选择片头目录")
                    )
            else:
                self.head_mode_btn.setIcon(load_svg_icon("file", 14, "#64748B"))
                self.head_mode_btn.setProperty("mode", "file")
                self.head_mode_btn.setText(t("batch.main_window.auto.018", "文件"))
                self.head_mode_btn.setToolTip(
                    t("batch.main_window.auto.019", "当前：文件模式（点击切换到文件夹模式）")
                )
                if hasattr(self, "head_browse_btn"):
                    self.head_browse_btn.setText(t("batch.main_window.auto.020", "选择文件"))
                if hasattr(self, "head_file"):
                    self.head_file.setPlaceholderText(
                        t("batch.main_window.auto.021", "未选择片头文件")
                    )
            if hasattr(self, "head_random_check"):
                head_random = (
                    bool(head_tail.get("head_random", False))
                    if head_mode == "folder"
                    else False
                )
                self.head_random_check.setEnabled(
                    self.head_check.isChecked() and head_mode == "folder"
                )
                self.head_random_check.setChecked(head_random)

        if hasattr(self, "tail_check"):
            self.tail_check.setChecked(bool(head_tail.get("tail_enabled", False)))
        if hasattr(self, "tail_file"):
            self.tail_file.setText(head_tail.get("tail_file", ""))
        if hasattr(self, "tail_mode_btn"):
            tail_mode = head_tail.get("tail_mode", "file")
            if tail_mode == "folder":
                self.tail_mode_btn.setIcon(load_svg_icon("folder", 14, "#64748B"))
                self.tail_mode_btn.setProperty("mode", "folder")
                self.tail_mode_btn.setText(t("batch.main_window.auto.014", "文件夹"))
                self.tail_mode_btn.setToolTip(
                    t(
                        "batch.main_window.auto.015",
                        "当前：文件夹模式（可随机选取，点击切换到文件模式）",
                    )
                )
                if hasattr(self, "tail_browse_btn"):
                    self.tail_browse_btn.setText(t("batch.main_window.auto.016", "选择目录"))
                if hasattr(self, "tail_file"):
                    self.tail_file.setPlaceholderText(
                        t("batch.main_window.auto.022", "未选择片尾目录")
                    )
            else:
                self.tail_mode_btn.setIcon(load_svg_icon("file", 14, "#64748B"))
                self.tail_mode_btn.setProperty("mode", "file")
                self.tail_mode_btn.setText(t("batch.main_window.auto.018", "文件"))
                self.tail_mode_btn.setToolTip(
                    t("batch.main_window.auto.019", "当前：文件模式（点击切换到文件夹模式）")
                )
                if hasattr(self, "tail_browse_btn"):
                    self.tail_browse_btn.setText(t("batch.main_window.auto.020", "选择文件"))
                if hasattr(self, "tail_file"):
                    self.tail_file.setPlaceholderText(
                        t("batch.main_window.auto.023", "未选择片尾文件")
                    )
            if hasattr(self, "tail_random_check"):
                tail_random = (
                    bool(head_tail.get("tail_random", False))
                    if tail_mode == "folder"
                    else False
                )
                self.tail_random_check.setEnabled(
                    self.tail_check.isChecked() and tail_mode == "folder"
                )
                self.tail_random_check.setChecked(tail_random)

        if hasattr(self, "border_check"):
            self.border_check.setChecked(bool(head_tail.get("border_enabled", False)))
        if hasattr(self, "border_file"):
            self.border_file.setText(head_tail.get("border_file", ""))
        if hasattr(self, "border_mode_btn"):
            border_mode = head_tail.get("border_mode", "file")
            if border_mode == "folder":
                self.border_mode_btn.setIcon(load_svg_icon("folder", 14, "#64748B"))
                self.border_mode_btn.setProperty("mode", "folder")
                self.border_mode_btn.setText(t("batch.main_window.auto.014", "文件夹"))
                self.border_mode_btn.setToolTip(
                    t("batch.main_window.auto.024", "当前：文件夹模式（随机选取，点击切换到文件模式）")
                )
                if hasattr(self, "border_browse_btn"):
                    self.border_browse_btn.setText(t("batch.main_window.auto.016", "选择目录"))
                if hasattr(self, "border_file"):
                    self.border_file.setPlaceholderText(
                        t("batch.main_window.auto.025", "未选择边框目录（png, jpg, gif）")
                    )
            else:
                self.border_mode_btn.setIcon(load_svg_icon("file", 14, "#64748B"))
                self.border_mode_btn.setProperty("mode", "file")
                self.border_mode_btn.setText(t("batch.main_window.auto.018", "文件"))
                self.border_mode_btn.setToolTip(
                    t("batch.main_window.auto.019", "当前：文件模式（点击切换到文件夹模式）")
                )
                if hasattr(self, "border_browse_btn"):
                    self.border_browse_btn.setText(t("batch.main_window.auto.020", "选择文件"))
                if hasattr(self, "border_file"):
                    self.border_file.setPlaceholderText(
                        t("batch.main_window.auto.026", "未选择边框文件（png, jpg, gif）")
                    )
            if "border_random" in head_tail:
                self.border_style_config["border_random"] = bool(
                    head_tail.get("border_random", False)
                )
        for key in [
            "border_opacity_min",
            "border_opacity_max",
            "border_margin_x",
            "border_margin_y",
            "border_remove_bg",
            "border_bg_method",
            "border_bg_x",
            "border_bg_y",
            "border_bg_time",
            "border_bg_color",
            "border_bg_similarity",
            "border_bg_blend",
        ]:
            if key in head_tail:
                self.border_style_config[key.replace("border_", "")] = head_tail.get(
                    key
                )

        speed = config.get("speed", {})
        if hasattr(self, "speed_check"):
            self.speed_check.setChecked(bool(speed.get("enabled", False)))
        if hasattr(self, "speed_min"):
            self.speed_min.setValue(speed.get("min", self.speed_min.value()))
            self.speed_max.setValue(speed.get("max", self.speed_max.value()))
            self.speed_segment_check.setChecked(
                bool(speed.get("segment_enabled", False))
            )
            self.speed_segment_duration.setValue(
                speed.get("segment_duration", self.speed_segment_duration.value())
            )
            self.speed_pitch_check.setChecked(bool(speed.get("pitch_enabled", False)))
            self.speed_min_duration_check.setChecked(
                bool(speed.get("min_duration_enabled", False))
            )
            self.speed_min_duration.setValue(
                speed.get("min_duration", self.speed_min_duration.value())
            )

        text = config.get("text", {})
        for i in range(1, 4):
            check = getattr(self, f"text{i}_check", None)
            if check:
                check.setChecked(bool(text.get(f"text{i}_enabled", False)))
        self.text_configs = [
            text.get("text1_config"),
            text.get("text2_config"),
            text.get("text3_config"),
        ]
        for i in range(1, 4):
            preview = getattr(self, f"text{i}_preview", None)
            cfg = self.text_configs[i - 1]
            if preview:
                if cfg and normalize_text_source_mode(cfg.get("source_mode")) == "plain":
                    preview.setText(cfg.get("text_content", ""))
                else:
                    preview.setText("")
            self._update_text_preview_summary(i)

        audio = config.get("audio", {})
        if hasattr(self, "bgm_check"):
            self.bgm_check.setChecked(bool(audio.get("bgm_enabled", False)))
        if "bgm_mode" in audio:
            self.bgm_mode = audio.get("bgm_mode", "file")
            if hasattr(self, "bgm_mode_btn"):
                if self.bgm_mode == "dir":
                    self.bgm_mode_btn.setIcon(load_svg_icon("folder", 14, "#64748B"))
                    self.bgm_mode_btn.setText(t("batch.main_window.auto.014", "文件夹"))
                    self.bgm_mode_btn.setToolTip(
                        t(
                            "batch.main_window.auto.015",
                            "当前：文件夹模式（可随机选取，点击切换到文件模式）",
                        )
                    )
                    if hasattr(self, "bgm_path"):
                        self.bgm_path.setPlaceholderText(
                            t("batch.main_window.auto.027", "未选择音频文件夹")
                        )
                else:
                    self.bgm_mode_btn.setIcon(load_svg_icon("file", 14, "#64748B"))
                    self.bgm_mode_btn.setText(t("batch.main_window.auto.018", "文件"))
                    self.bgm_mode_btn.setToolTip(
                        t("batch.main_window.auto.019", "当前：文件模式（点击切换到文件夹模式）")
                    )
                    if hasattr(self, "bgm_path"):
                        self.bgm_path.setPlaceholderText(
                            t("batch.main_window.auto.028", "未选择音频文件")
                        )
        if hasattr(self, "bgm_path"):
            self.bgm_path.setText(audio.get("bgm_path", ""))
        if hasattr(self, "bgm_volume"):
            self.bgm_volume.setValue(audio.get("bgm_volume", self.bgm_volume.value()))
        if hasattr(self, "bgm_fadein_check"):
            self.bgm_fadein_check.setChecked(bool(audio.get("bgm_fade_enabled", False)))
            self.bgm_fadein_duration.setValue(
                audio.get("bgm_fade_duration", self.bgm_fadein_duration.value())
            )
        if hasattr(self, "bgm_delay_check"):
            self.bgm_delay_check.setChecked(bool(audio.get("bgm_delay_enabled", False)))
            self.bgm_delay.setValue(audio.get("bgm_delay", self.bgm_delay.value()))
        if hasattr(self, "original_volume_check"):
            self.original_volume_check.setChecked(
                bool(audio.get("original_volume_enabled", False))
            )
            self.original_volume.setValue(
                audio.get("original_volume", self.original_volume.value())
            )
        if hasattr(self, "original_fade_sync_check"):
            self.original_fade_sync_check.setChecked(
                bool(audio.get("original_fade_sync", False))
            )
        if hasattr(self, "bgm_loop_check"):
            self.bgm_loop_check.setChecked(bool(audio.get("enable_loop", False)))
        if hasattr(self, "bgm_random_check"):
            enable_random = (
                bool(audio.get("enable_random", False))
                if self.bgm_mode == "dir"
                else False
            )
            self.bgm_random_check.setChecked(enable_random)

        frame_adjust = config.get("frame_adjust", {})
        if hasattr(self, "frame_adjust_check"):
            self.frame_adjust_check.setChecked(bool(frame_adjust.get("enabled", False)))
        if hasattr(self, "brightness_min"):
            self.brightness_min.setValue(
                frame_adjust.get("brightness_min", self.brightness_min.value())
            )
            self.brightness_max.setValue(
                frame_adjust.get("brightness_max", self.brightness_max.value())
            )
            self.sharpness_min.setValue(
                frame_adjust.get("sharpness_min", self.sharpness_min.value())
            )
            self.sharpness_max.setValue(
                frame_adjust.get("sharpness_max", self.sharpness_max.value())
            )
            self.contrast_min.setValue(
                frame_adjust.get("contrast_min", self.contrast_min.value())
            )
            self.contrast_max.setValue(
                frame_adjust.get("contrast_max", self.contrast_max.value())
            )
            self.denoise_min.setValue(
                frame_adjust.get("denoise_min", self.denoise_min.value())
            )
            self.denoise_max.setValue(
                frame_adjust.get("denoise_max", self.denoise_max.value())
            )
            self.saturation_min.setValue(
                frame_adjust.get("saturation_min", self.saturation_min.value())
            )
            self.saturation_max.setValue(
                frame_adjust.get("saturation_max", self.saturation_max.value())
            )

        grid = config.get("grid_split", {})
        if hasattr(self, "grid_split_check"):
            self.grid_split_check.setChecked(bool(grid.get("enabled", False)))
        if hasattr(self, "grid_count"):
            self.grid_count.setValue(grid.get("count", self.grid_count.value()))
            if grid.get("direction"):
                self._set_combo_by_code(
                    self.grid_direction,
                    normalize_grid_direction(grid.get("direction")),
                    GRID_DIRECTION_LABELS,
                )
            self.grid_blur_check.setChecked(bool(grid.get("blur", False)))

        resolution = config.get("resolution", {})
        if hasattr(self, "resolution_check"):
            self.resolution_check.setChecked(bool(resolution.get("enabled", False)))
        if hasattr(self, "resolution_preset") and resolution.get("preset"):
            self._set_combo_by_code(
                self.resolution_preset,
                normalize_resolution_preset(resolution.get("preset")),
                RESOLUTION_PRESET_LABELS,
            )
        if hasattr(self, "resolution_width"):
            self.resolution_width.setValue(
                resolution.get("width", self.resolution_width.value())
            )
            self.resolution_height.setValue(
                resolution.get("height", self.resolution_height.value())
            )

        mode = config.get("mode", {})
        if hasattr(self, "mode_stretch"):
            self.mode_stretch.setChecked(bool(mode.get("stretch", False)))
            self.mode_crop.setChecked(bool(mode.get("crop", False)))
            self.mode_original.setChecked(bool(mode.get("original", False)))
            self.background_blur_check.setChecked(
                bool(mode.get("background_blur", False))
            )
            self.reflection_check.setChecked(bool(mode.get("reflection", False)))
            self.reflection_opacity.setValue(
                mode.get("reflection_opacity", self.reflection_opacity.value())
            )

        rotate = config.get("rotate_flip", {})
        if hasattr(self, "rotate_check"):
            self.rotate_check.setChecked(bool(rotate.get("enabled", False)))
        if hasattr(self, "flip_left90"):
            self.flip_left90.setChecked(bool(rotate.get("left90", False)))
            self.flip_right90.setChecked(bool(rotate.get("right90", False)))
            self.flip_horizontal.setChecked(bool(rotate.get("horizontal", False)))
            self.flip_vertical.setChecked(bool(rotate.get("vertical", False)))
            random_direction = bool(rotate.get("random_direction", False))
            random_angle = bool(rotate.get("random_angle", rotate.get("random", False)))
            if random_direction:
                self.flip_random_direction.setChecked(True)
            elif random_angle:
                self.flip_random.setChecked(True)
            self.flip_random_angle.setValue(
                rotate.get("random_angle_min", self.flip_random_angle.value())
            )
            self.flip_random_angle_max.setValue(
                rotate.get("random_angle_max", self.flip_random_angle_max.value())
            )
            self.flip_complete_check.setChecked(
                bool(rotate.get("complete_display", False))
            )
            self.flip_black_edge_check.setChecked(
                bool(rotate.get("black_edge_remove", False))
            )
            self._update_rotate_random_controls()

        fps = config.get("fps", {})
        if hasattr(self, "fps_check"):
            self.fps_check.setChecked(bool(fps.get("enabled", False)))
            self.fps_min.setValue(fps.get("min", self.fps_min.value()))
            self.fps_max.setValue(fps.get("max", self.fps_max.value()))
            self.remove_duplicate_frames_check.setChecked(
                bool(fps.get("remove_duplicate", False))
            )

        frame_extract = config.get("frame_extract", {})
        if hasattr(self, "frame_extract_check"):
            self.frame_extract_check.setChecked(
                bool(frame_extract.get("enabled", False))
            )
            self.frame_extract_min.setValue(
                frame_extract.get("min", self.frame_extract_min.value())
            )
            self.frame_extract_max.setValue(
                frame_extract.get("max", self.frame_extract_max.value())
            )
            self.audio_speed_check.setChecked(
                bool(frame_extract.get("audio_speed", False))
            )

        dynamic_zoom = config.get("dynamic_zoom", {})
        if hasattr(self, "dynamic_zoom_check"):
            self.dynamic_zoom_check.setChecked(bool(dynamic_zoom.get("enabled", False)))
            self.dynamic_zoom_min.setValue(
                dynamic_zoom.get("min", self.dynamic_zoom_min.value())
            )
            self.dynamic_zoom_max.setValue(
                dynamic_zoom.get("max", self.dynamic_zoom_max.value())
            )
        if "advanced" in dynamic_zoom:
            self.dynamic_zoom_advanced_config = dynamic_zoom.get("advanced") or {}

        bitrate = config.get("bitrate", {})
        if hasattr(self, "bitrate_check"):
            self.bitrate_check.setChecked(bool(bitrate.get("enabled", False)))
            self.bitrate_mode_dynamic.setChecked(
                bool(bitrate.get("mode_dynamic", True))
            )
            self.bitrate_mode_fixed.setChecked(bool(bitrate.get("mode_fixed", False)))
            self.bitrate_dynamic_value.setValue(
                bitrate.get("dynamic_value", self.bitrate_dynamic_value.value())
            )
            if bitrate.get("fixed_value"):
                self.bitrate_fixed_preset.setCurrentText(
                    str(bitrate.get("fixed_value"))
                )
            self.bitrate_ratio_min.setValue(
                bitrate.get("ratio_min", self.bitrate_ratio_min.value())
            )
            self.bitrate_ratio_max.setValue(
                bitrate.get("ratio_max", self.bitrate_ratio_max.value())
            )

        if "color_tone" in config:
            self.color_tone_config = config.get("color_tone") or {}
        if "lut_filter" in config:
            self.lut_filter_config = config.get("lut_filter") or {}
        if "more_effects" in config:
            self.more_effects_config = config.get("more_effects") or {}

        output = config.get("output", {})
        # 「统一输出位置」勾选时，切换视频不改变输出路径和结构选项
        unified = getattr(self, "unified_output_check", None)
        if not (unified and unified.isChecked()):
            if hasattr(self, "output_path"):
                self.output_path.setText(output.get("path", self.output_path.text()))
            if hasattr(self, "keep_structure"):
                self.keep_structure.setChecked(
                    bool(output.get("keep_structure", False))
                )
        self._update_crop_remove_watermark_conflict_hint()

    def on_progress_updated(self, progress: int, message: str):
        """更新进度"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def on_video_status_updated(self, row: int, status: str):
        """更新视频状态"""
        if row < self.video_table.rowCount():
            self._update_video_status_indicator(row, status)

    def on_processing_finished(self):
        """处理完成"""
        # 恢复全部功能控件
        self._set_all_controls_enabled(True)
        self.start_btn.setText(t("batch.main_window.auto.029", "开始处理"))
        self.start_btn.setEnabled(True)
        stopped = bool(
            self.process_thread and getattr(self.process_thread, "was_stopped", False)
        )

        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        total_rows = self.video_table.rowCount()
        success_count = 0
        failed_count = 0
        skipped_count = 0
        for row in range(total_rows):
            status = self._get_status_text(row)
            if status == "done":
                success_count += 1
            elif status == "skipped":
                skipped_count += 1
            elif status == "failed" or status.startswith("error:"):
                failed_count += 1

        if stopped:
            self.progress_bar.setFormat(t("batch.main_window.auto.030", "%p% - 已停止"))
            self.progress_bar.set_status(ProgressStatus.WARNING)
            self.process_log.append(
                f"{timestamp} -> 批量处理已停止 | 成功:{success_count} 失败:{failed_count} 跳过:{skipped_count} 总数:{total_rows}"
            )
        else:
            # 恢复進度条中的文本
            self.progress_bar.setFormat(t("batch.main_window.auto.031", "%p% - 处理完成"))
            self.progress_bar.setValue(100)
            if failed_count > 0:
                self.progress_bar.set_status(ProgressStatus.WARNING)
            else:
                self.progress_bar.set_status(ProgressStatus.SUCCESS)

            self.process_log.append(
                f"{timestamp} -> 批量处理完成 | 成功:{success_count} 失败:{failed_count} 跳过:{skipped_count} 总数:{total_rows}"
            )

        global_options = self.config or {}
        output_dir = self.output_path.text()
        if self.process_thread and self.process_thread.batch_output_dir:
            output_dir = self.process_thread.batch_output_dir

        overwrite_original_widget = getattr(self, "overwrite_original", None)
        overwrite_original = (
            bool(overwrite_original_widget.isChecked())
            if overwrite_original_widget
            else False
        )
        output_file_to_reveal = None
        success_rows = []
        for row in range(total_rows):
            status = self._get_status_text(row)
            if status == "done":
                success_rows.append(row)

        if success_rows:
            import shutil

            try:
                from send2trash import send2trash
            except Exception:
                send2trash = None

            def ensure_unique_path(path: str) -> str:
                base, ext = os.path.splitext(path)
                counter = 1
                unique_path = path
                while os.path.exists(unique_path):
                    unique_path = f"{base}_{counter}{ext}"
                    counter += 1
                return unique_path

            for row in success_rows:
                if row >= len(self.video_list):
                    continue
                video_info = self.video_list[row]
                original_path = video_info.get("path")
                output_path = video_info.get("output_path")

                if (
                    not overwrite_original
                    and global_options.get("move_to_original")
                    and original_path
                    and output_path
                ):
                    if os.path.exists(output_path):
                        origin_dir = os.path.dirname(original_path)
                        output_dirname = os.path.dirname(output_path)
                        if origin_dir and os.path.normcase(
                            output_dirname
                        ) != os.path.normcase(origin_dir):
                            target_path = os.path.join(
                                origin_dir, os.path.basename(output_path)
                            )
                            target_path = ensure_unique_path(target_path)
                            try:
                                shutil.move(output_path, target_path)
                                video_info["output_path"] = target_path
                            except Exception as e:
                                self.process_log.append(
                                    f"{timestamp} -> 移动失败: {os.path.basename(output_path)} ({e})"
                                )

                if (
                    not overwrite_original
                    and global_options.get("delete_original")
                    and original_path
                ):
                    if os.path.exists(original_path) and original_path != output_path:
                        try:
                            if global_options.get("to_recycle") and send2trash:
                                send2trash(original_path)
                            else:
                                os.remove(original_path)
                        except Exception as e:
                            self.process_log.append(
                                f"{timestamp} -> 删除失败: {os.path.basename(original_path)} ({e})"
                            )

                final_output_path = video_info.get("output_path")
                if final_output_path and os.path.exists(final_output_path):
                    output_file_to_reveal = final_output_path

        if global_options.get("open_folder_after_complete"):
            self._open_output_folder(output_dir, output_file_to_reveal)

        if global_options.get("sound_alert"):
            QApplication.beep()

        summary_message = (
            f"success: {success_count}\n"
            f"failed: {failed_count}\n"
            f"skipped: {skipped_count}\n"
            f"total: {total_rows}"
        )
        if failed_count > 0:
            ModernMessageBox.warning(
                self, t("batch.main_window.auto.032", "处理结果"), summary_message
            )
        else:
            ModernMessageBox.information(
                self,
                t("batch.main_window.auto.032", "处理结果"),
                t("batch.main_window.auto.033", "批量处理已完成！\n") + summary_message,
            )

        if global_options.get("remove_task_after_complete") and success_rows:
            for row in reversed(success_rows):
                if row < len(self.video_list):
                    del self.video_list[row]
                    self.video_table.removeRow(row)
            self.refresh_table_numbers()
            self.update_queue_count()
            self.update_empty_state()
            self.update_header_checkbox_state()

        self._refresh_live_validation_feedback()
        self._update_controls_by_selection()
        # 确保始终有视频被选中
        self._ensure_video_selected()

        if global_options.get("complete_action") == "exit":
            self.close()

    def _open_output_folder(self, output_dir: str, output_file: str = None):
        import os
        import sys
        import subprocess

        if output_file and os.path.exists(output_file) and os.path.isfile(output_file):
            output_file = os.path.normpath(output_file)
            if sys.platform.startswith("win"):
                subprocess.run(["explorer", "/select,", output_file], check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", output_file], check=False)
            else:
                subprocess.run(["xdg-open", os.path.dirname(output_file)], check=False)
            return

        if not output_dir:
            return
        output_dir = os.path.normpath(output_dir)
        if not os.path.exists(output_dir):
            return
        if sys.platform.startswith("win"):
            os.startfile(output_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", output_dir])
        else:
            subprocess.Popen(["xdg-open", output_dir])

    def on_apply_params_to_all_changed(self, checked: bool):
        """是否将当前参数同步到全部视频"""
        if checked and self.video_list and len(self.video_list) > 1:
            # 弹出确认对话框
            count = len(self.video_list)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(t("batch.main_window.auto.034", "应用参数到全部"))
            msg_box.setText(
                t(
                    "batch.main_window.auto.063",
                    "确认将当前视频的参数应用到列表中全部 {count} 个视频吗？\n这将覆盖各视频的独立参数设置。",
                    count=count,
                )
            )
            msg_box.setIcon(QMessageBox.Icon.Question)
            yes_btn = msg_box.addButton(
                t("batch.main_window.auto.009", "确定"), QMessageBox.ButtonRole.YesRole
            )
            no_btn = msg_box.addButton(
                t("batch.main_window.auto.010", "取消"), QMessageBox.ButtonRole.NoRole
            )
            msg_box.setDefaultButton(no_btn)
            msg_box.exec()

            if msg_box.clickedButton() != yes_btn:
                # 用户取消，恢复未勾选状态
                self.apply_params_to_all_check.blockSignals(True)
                self.apply_params_to_all_check.setChecked(False)
                self.apply_params_to_all_check.blockSignals(False)
                return

        self.apply_params_to_all = bool(checked)
        if self.apply_params_to_all:
            self._persist_current_params()
            # 更新所有视频的状态指示器
            for row in range(self.video_table.rowCount()):
                self._update_video_status_indicator(row)
            # 反馈提示
            if hasattr(self, "status_label") and self.video_list:
                count = len(self.video_list)
                self.status_label.setStyleSheet(
                    f"color: {Theme.Success}; font-size: 12px;"
                )
                self.status_label.setText(self._ts(f"已将参数应用到全部 {count} 个视频"))
        else:
            if hasattr(self, "status_label"):
                self.status_label.setStyleSheet(
                    f"color: {Theme.TextSecondary}; font-size: 12px;"
                )
                self.status_label.setText(self._ts("已关闭参数全局同步，各视频可独立调节参数"))

    def create_empty_state_widget(self, parent_layout):
        """创建空状态提示界面"""
        from ui.batch_video.left_panel import create_empty_state_widget

        return create_empty_state_widget(self, parent_layout)

    def update_empty_state(self):
        """更新空状态显示"""
        if len(self.video_list) == 0:
            self.empty_state_widget.setVisible(True)
            self.video_table.setVisible(False)
        else:
            self.empty_state_widget.setVisible(False)
            self.video_table.setVisible(True)
        self.update_queue_status()
        self._update_controls_by_selection()

    def show_table_context_menu(self, position):
        """显示表格右键菜单（完整功能）"""
        menu = QMenu(self)

        selected_rows = self.get_selected_rows()
        has_selection = len(selected_rows) > 0

        # 1. 播放
        play_action = QAction(self._ts("播放"), self)
        play_action.triggered.connect(self.play_selected_video)
        play_action.setEnabled(has_selection)
        menu.addAction(play_action)

        # 2. 打开文件夹
        open_folder_action = QAction(self._ts("打开文件夹"), self)
        open_folder_action.triggered.connect(self.open_selected_video_folder)
        open_folder_action.setEnabled(has_selection)
        menu.addAction(open_folder_action)

        menu.addSeparator()

        # 3. 全选 Ctrl+A
        select_all_action = QAction(self._ts("全选\tCtrl+A"), self)
        select_all_action.triggered.connect(self.select_all_videos)
        menu.addAction(select_all_action)

        # 4. 反选
        invert_selection_action = QAction(self._ts("反选"), self)
        invert_selection_action.triggered.connect(self.invert_selection)
        menu.addAction(invert_selection_action)

        menu.addSeparator()

        # 5. 移除 Delete
        remove_action = QAction(self._ts("移除\tDelete"), self)
        remove_action.triggered.connect(self.remove_selected_videos)
        remove_action.setEnabled(has_selection)
        menu.addAction(remove_action)

        # 6. 清空
        clear_action = QAction(self._ts("清空"), self)
        clear_action.triggered.connect(self.clear_all_videos)
        menu.addAction(clear_action)

        # 7. 清除无效文件
        remove_invalid_action = QAction(self._ts("清除无效文件"), self)
        remove_invalid_action.triggered.connect(self.remove_invalid_videos)
        menu.addAction(remove_invalid_action)

        menu.addSeparator()

        # 8. 往上排
        move_up_action = QAction(self._ts("往上排"), self)
        move_up_action.triggered.connect(self.move_video_up)
        can_move_up = has_selection and len(selected_rows) == 1 and selected_rows[0] > 0
        move_up_action.setEnabled(can_move_up)
        menu.addAction(move_up_action)

        # 9. 往下排
        move_down_action = QAction(self._ts("往下排"), self)
        move_down_action.triggered.connect(self.move_video_down)
        can_move_down = (
            has_selection
            and len(selected_rows) == 1
            and selected_rows[0] < len(self.video_list) - 1
        )
        move_down_action.setEnabled(can_move_down)
        menu.addAction(move_down_action)

        menu.addSeparator()

        # 10. 排序（二级菜单）
        sort_menu = menu.addMenu(self._ts("排序"))
        sort_options = [
            (self._ts("名称"), "name"),
            (self._ts("大小"), "size"),
            (self._ts("长度"), "duration"),
            (self._ts("日期"), "date"),
            (self._ts("类型"), "type"),
            (self._ts("分辨率"), "resolution"),
        ]
        for label, key in sort_options:
            action = QAction(label, self)
            action.triggered.connect(lambda checked, k=key: self.sort_videos_by(k))
            sort_menu.addAction(action)

        menu.addSeparator()

        # 11. 媒体信息
        media_info_action = QAction(self._ts("媒体信息"), self)
        media_info_action.triggered.connect(self.show_media_info)
        media_info_action.setEnabled(has_selection and len(selected_rows) == 1)
        menu.addAction(media_info_action)

        # 显示菜单
        menu.exec(self.video_table.viewport().mapToGlobal(position))

    def remove_selected_video(self, row: int):
        """移除选中的视频"""
        if 0 <= row < len(self.video_list):
            video_name = os.path.basename(self.video_list[row]["path"])
            global_options = self.config or {}
            if global_options.get("remove_confirm", True):
                reply = self._confirm("确认移除", f"确定要移除视频 '{video_name}' 吗？")
                if reply != QMessageBox.StandardButton.Yes:
                    return

            # 从列表中移除
            del self.video_list[row]
            self.video_table.removeRow(row)

            # 更新编号
            for i in range(row, self.video_table.rowCount()):
                no_item = QTableWidgetItem(str(i + 1))
                no_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.video_table.setItem(i, self.COL_NO, no_item)

            self.update_queue_count()
            self.update_empty_state()

            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> 已移除: {video_name}")

            # 自动选中下一个可用行
            if self.video_list:
                next_row = min(row, len(self.video_list) - 1)
                self.video_table.selectRow(next_row)

    def on_video_double_clicked(self, row: int, column: int):
        """双击视频行时预览"""
        self.preview_video(row)

    def preview_video(self, row: int):
        """预览视频"""
        if 0 <= row < len(self.video_list):
            video_path = self.video_list[row]["path"]

            # 使用OpenCV播放器
            try:
                from ui.video_player_window import SimpleVideoPlayer

                self.player_window = SimpleVideoPlayer(video_path)
                self.player_window.show()

                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(
                    f"{timestamp} -> 打开预览: {os.path.basename(video_path)}"
                )
            except Exception as e:
                import traceback

                error_msg = traceback.format_exc()
                self._warn("错误", f"无法打开视频:\n{str(e)}\n\n{error_msg}")

    def clear_process_log(self):
        """清理所有处理记录"""
        self.process_log.clear()
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.process_log.append(f"{timestamp} -> 记录已清理")

    def open_output_folder(self):
        """打开输出文件夹"""
        output_dir = self.output_path.text().strip()

        if not output_dir:
            ModernMessageBox.warning(
                self,
                t("batch.main_window.auto.006", "提示"),
                t("batch.main_window.auto.035", "请先选择输出目录！"),
            )
            return

        # 如果目录不存在，自动创建
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(f"{timestamp} -> 已创建输出目录: {output_dir}")
            except Exception as e:
                ModernMessageBox.error(
                    self,
                    t("batch.main_window.auto.036", "错误"),
                    t(
                        "batch.main_window.auto.064",
                        "无法创建目录: {error}",
                        error=str(e),
                    ),
                )
                return

        # 打开文件夹
        import subprocess
        import platform

        try:
            if platform.system() == "Windows":
                os.startfile(output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            else:  # Linux
                subprocess.run(["xdg-open", output_dir])
        except Exception as e:
            ModernMessageBox.error(
                self,
                t("batch.main_window.auto.036", "错误"),
                t(
                    "batch.main_window.auto.065",
                    "无法打开文件夹: {error}",
                    error=str(e),
                ),
            )

    def on_output_mode_changed(self, checked: bool):
        """输出模式变化"""
        self.output_mode = "new_location"
        self.output_path.setEnabled(True)
        self.keep_structure.setEnabled(True)

    def on_keep_structure_changed(self, checked: bool):
        """保持文件夹结构选项变化"""
        self.keep_folder_structure = checked

    def get_output_path_for_video(self, video_path: str) -> str:
        """获取视频的输出路径"""
        output_dir = self.output_path.text()
        video_filename = os.path.basename(video_path)

        if self.keep_folder_structure:
            # 按原路径输出
            # TODO: 需要实现相对路径逻辑
            output_path = os.path.join(output_dir, video_filename)
        else:
            # 全部放在输出目录下
            output_path = os.path.join(output_dir, video_filename)

        # 如果文件已存在，提示替换或自动命名
        if os.path.exists(output_path):
            reply = self._confirm(
                "文件已存在", f"文件 '{video_filename}' 已存在，是否替换？"
            )

            if reply == QMessageBox.StandardButton.No:
                # 自动命名
                base_name, ext = os.path.splitext(video_filename)
                counter = 1
                while os.path.exists(output_path):
                    new_filename = f"{base_name}({counter}){ext}"
                    output_path = os.path.join(output_dir, new_filename)
                    counter += 1

        return output_path

    # ========== 右键菜单功能方法 ==========

    def on_selection_changed(self):
        """选择状态变化时更新移除按钮和清空按钮"""
        selected_rows = self.get_selected_rows()
        new_index = selected_rows[0] if selected_rows else None

        # 防止取消选中：如果列表有视频但没有选中行，自动恢复选中
        if new_index is None and self.video_list:
            self._ensure_video_selected()
            return  # selectRow 会重新触发本方法

        if (
            self.current_video_index is not None
            and self.current_video_index != new_index
        ):
            snapshot = self._snapshot_current_params()
            self._save_params_to_video(self.current_video_index, snapshot)
            if self.apply_params_to_all:
                self._sync_params_to_all(snapshot)
        self.current_video_index = new_index
        if self.current_video_index is not None:
            params = self.video_list[self.current_video_index].get("params")
            if params:
                self._apply_params_to_ui(params)
        self.update_queue_status()
        self._update_controls_by_selection()

    def get_selected_rows(self) -> List[int]:
        """获取选中的行号列表"""
        selected = self.video_table.selectionModel().selectedRows()
        return sorted([index.row() for index in selected])

    def get_checked_rows(self) -> List[int]:
        """获取勾选的行号列表"""
        checked_rows = []
        for row in range(self.video_table.rowCount()):
            item = self.video_table.item(row, self.COL_CHECK)
            if item and item.checkState() == Qt.CheckState.Checked:
                checked_rows.append(row)
        return checked_rows

    @classmethod
    def _get_compiled_pattern(cls, pattern: str):
        """获取编译后的正则表达式（带缓存）"""
        if pattern not in cls._pattern_cache:
            cls._pattern_cache[pattern] = re.compile(pattern)
        return cls._pattern_cache[pattern]

    def _create_check_item(self, checked: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem()
        item.setFlags(
            Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
        )
        item.setCheckState(
            Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        )
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def on_header_checkbox_changed(self, state):
        """表头复选框状态改变时同步所有行"""
        if self.video_table.rowCount() == 0:
            return

        new_state = (
            Qt.CheckState.Checked
            if state == Qt.CheckState.Checked
            else Qt.CheckState.Unchecked
        )

        # 阻止 itemChanged 信号在批量更新时触发
        self.video_table.blockSignals(True)
        for row in range(self.video_table.rowCount()):
            item = self.video_table.item(row, self.COL_CHECK)
            if item:
                item.setCheckState(new_state)
        self.video_table.blockSignals(False)
        self.update_queue_status()

    def update_header_checkbox_state(self):
        """根据当前行的勾选状态更新表头复选框"""
        if not hasattr(self, "header_view"):
            return

        total_rows = self.video_table.rowCount()
        if total_rows == 0:
            self.header_view.set_check_state(Qt.CheckState.Unchecked)
            return

        checked_count = 0
        for row in range(total_rows):
            item = self.video_table.item(row, self.COL_CHECK)
            if item and item.checkState() == Qt.CheckState.Checked:
                checked_count += 1

        if checked_count == 0:
            self.header_view.set_check_state(Qt.CheckState.Unchecked)
        elif checked_count == total_rows:
            self.header_view.set_check_state(Qt.CheckState.Checked)
        else:
            self.header_view.set_check_state(Qt.CheckState.PartiallyChecked)

    def on_table_item_changed(self, item):
        """表格项改变时更新表头复选框状态"""
        if item and item.column() == self.COL_CHECK:
            self.update_header_checkbox_state()
            self.update_queue_status()

    def play_selected_video(self):
        """播放选中的视频"""
        selected_rows = self.get_selected_rows()
        if selected_rows:
            self.preview_video(selected_rows[0])

    def open_selected_video_folder(self):
        """打开选中视频所在文件夹并选中文件"""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return

        video_path = self.video_list[selected_rows[0]]["path"]
        folder_path = os.path.dirname(video_path)

        try:
            if os.path.exists(video_path):
                import platform

                if platform.system() == "Windows":
                    # Windows: 使用 explorer /select, 打开文件夹并选中文件
                    subprocess.run(["explorer", "/select,", video_path])
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", "-R", video_path])
                else:  # Linux
                    # Linux 只打开文件夹
                    subprocess.run(["xdg-open", folder_path])
            else:
                self._warn("错误", f"文件不存在: {video_path}")
        except Exception as e:
            self._warn("错误", f"无法打开文件夹: {str(e)}")

    def select_all_videos(self):
        """全选所有视频"""
        self.video_table.selectAll()

    def invert_selection(self):
        """反选"""
        selected_rows = set(self.get_selected_rows())
        total_rows = self.video_table.rowCount()

        # 如果没有选中任何行，反选就是全选
        if not selected_rows:
            self.video_table.selectAll()
            return

        # 清除当前选择
        self.video_table.clearSelection()

        # 选中未选中的行
        for row in range(total_rows):
            if row not in selected_rows:
                self.video_table.selectRow(row)

    def remove_selected_videos(self):
        """移除选中的视频"""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return

        global_options = self.config or {}
        if global_options.get("remove_confirm", True):
            reply = self._confirm(
                "确认移除", f"确定要移除选中的 {len(selected_rows)} 个视频吗？"
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        first_removed = selected_rows[0]

        # 从后往前删除，避免索引变化
        for row in reversed(selected_rows):
            if row < 0 or row >= len(self.video_list):
                continue
            try:
                video_name = os.path.basename(self.video_list[row]["path"])
                del self.video_list[row]
                if row < self.video_table.rowCount():
                    self.video_table.removeRow(row)

                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(f"{timestamp} -> 已移除: {video_name}")
            except Exception as e:
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(f"{timestamp} -> 移除失败(行{row}): {e}")

        # 更新编号
        self.refresh_table_numbers()
        self.update_queue_count()
        self.update_empty_state()
        self.update_header_checkbox_state()

        # 自动选中下一个可用行
        if self.video_list:
            next_row = min(first_removed, len(self.video_list) - 1)
            self.video_table.selectRow(next_row)

    def remove_checked_videos(self):
        """移除勾选的视频"""
        checked_rows = self.get_checked_rows()
        if not checked_rows:
            return

        global_options = self.config or {}
        if global_options.get("remove_confirm", True):
            reply = self._confirm(
                "确认移除", f"确定要移除已勾选的 {len(checked_rows)} 个视频吗？"
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # 从后往前删除，避免索引变化
        for row in reversed(checked_rows):
            if row < 0 or row >= len(self.video_list):
                continue
            try:
                video_name = os.path.basename(self.video_list[row]["path"])
                del self.video_list[row]
                if row < self.video_table.rowCount():
                    self.video_table.removeRow(row)

                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(f"{timestamp} -> 已移除: {video_name}")
            except Exception as e:
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(f"{timestamp} -> 移除失败(行{row}): {e}")

        first_removed = checked_rows[0]

        # 更新编号与状态
        self.refresh_table_numbers()
        self.update_queue_count()
        self.update_empty_state()
        self.update_header_checkbox_state()

        # 自动选中下一个可用行
        if self.video_list:
            next_row = min(first_removed, len(self.video_list) - 1)
            self.video_table.selectRow(next_row)

    def clear_all_videos(self):
        """清空所有视频"""
        if not self.video_list:
            return

        global_options = self.config or {}
        if global_options.get("remove_confirm", True):
            reply = self._confirm("确认清空", "确定要清空所有视频吗？")
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.video_list.clear()
        self.video_table.setRowCount(0)
        self.current_video_index = None
        self.update_queue_count()
        self.update_empty_state()

        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.process_log.append(f"{timestamp} -> 已清空所有视频")

    def remove_invalid_videos(self):
        """清除无效文件"""
        invalid_rows = []

        # 查找无效文件
        for i, video_info in enumerate(self.video_list):
            if not os.path.exists(video_info["path"]):
                invalid_rows.append(i)

        if not invalid_rows:
            self._info("提示", "没有发现无效文件")
            return

        global_options = self.config or {}
        if global_options.get("remove_confirm", True):
            reply = self._confirm(
                "确认清除", f"发现 {len(invalid_rows)} 个无效文件，确定要清除吗？"
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # 从后往前删除
        for row in reversed(invalid_rows):
            video_name = os.path.basename(self.video_list[row]["path"])
            del self.video_list[row]
            self.video_table.removeRow(row)

            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> 已清除无效文件: {video_name}")

        self.refresh_table_numbers()
        self.update_queue_count()
        self.update_empty_state()

        # 自动选中可用行
        if self.video_list:
            self._ensure_video_selected()

    def move_video_up(self):
        """往上移动视频"""
        selected_rows = self.get_selected_rows()
        if not selected_rows or selected_rows[0] == 0:
            return

        row = selected_rows[0]
        # 交换视频列表位置
        self.video_list[row], self.video_list[row - 1] = (
            self.video_list[row - 1],
            self.video_list[row],
        )

        # 刷新表格
        self.refresh_table()

        # 重新选中
        self.video_table.selectRow(row - 1)

    def move_video_down(self):
        """往下移动视频"""
        selected_rows = self.get_selected_rows()
        if not selected_rows or selected_rows[0] >= len(self.video_list) - 1:
            return

        row = selected_rows[0]
        # 交换视频列表位置
        self.video_list[row], self.video_list[row + 1] = (
            self.video_list[row + 1],
            self.video_list[row],
        )

        # 刷新表格
        self.refresh_table()

        # 重新选中
        self.video_table.selectRow(row + 1)

    def sort_videos_by(self, sort_key: str):
        """按指定条件排序视频"""
        if not self.video_list:
            return

        # 中文名称映射
        sort_name_map = {
            "name": "名称",
            "size": "大小",
            "duration": "长度",
            "date": "日期",
            "type": "类型",
            "resolution": "分辨率",
        }

        # 检查是否已按此条件排序，如果是则反转
        if hasattr(self, "last_sort_key") and self.last_sort_key == sort_key:
            self.video_list.reverse()
            self.last_sort_key = None
        else:
            # 按新条件排序
            if sort_key == "name":
                self.video_list.sort(key=lambda x: os.path.basename(x["path"]).lower())
            elif sort_key == "size":
                self.video_list.sort(
                    key=lambda x: os.path.getsize(x["path"])
                    if os.path.exists(x["path"])
                    else 0
                )
            elif sort_key == "duration":
                self.video_list.sort(key=lambda x: x.get("duration", 0))
            elif sort_key == "date":
                self.video_list.sort(
                    key=lambda x: os.path.getmtime(x["path"])
                    if os.path.exists(x["path"])
                    else 0
                )
            elif sort_key == "type":
                self.video_list.sort(
                    key=lambda x: os.path.splitext(x["path"])[1].lower()
                )
            elif sort_key == "resolution":
                self.video_list.sort(key=lambda x: x.get("resolution", "0x0"))

            self.last_sort_key = sort_key

        # 刷新表格
        self.refresh_table()

        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        sort_name = sort_name_map.get(sort_key, sort_key)
        self.process_log.append(f"{timestamp} -> 已按 {sort_name} 排序")

    def show_media_info(self):
        """显示媒体信息"""
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            return

        video_path = self.video_list[selected_rows[0]]["path"]

        try:
            # 使用FFprobe获取媒体信息
            import subprocess
            import json

            # 查找ffprobe路径（多种方式尝试）
            ffprobe_path = None

            # 1. 检查app/ffmpeg目录下的ffprobe.exe（打包时会一起打包）
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            bundled_ffprobe = os.path.join(app_dir, "ffmpeg", "ffprobe.exe")
            if os.path.exists(bundled_ffprobe):
                ffprobe_path = bundled_ffprobe
            else:
                # 2. 检查processor目录下是否有ffprobe.exe
                processor_ffprobe = os.path.join(app_dir, "processor", "ffprobe.exe")
                if os.path.exists(processor_ffprobe):
                    ffprobe_path = processor_ffprobe
                else:
                    # 3. 检查当前目录下的processor目录
                    local_ffprobe = os.path.join(
                        os.getcwd(), "processor", "ffprobe.exe"
                    )
                    if os.path.exists(local_ffprobe):
                        ffprobe_path = local_ffprobe
                    else:
                        # 4. 检查系统PATH中是否有ffprobe
                        import shutil

                        system_ffprobe = shutil.which("ffprobe")
                        if system_ffprobe:
                            ffprobe_path = system_ffprobe

            if not ffprobe_path:
                raise Exception(
                    "找不到 ffprobe.exe。\n\n请确保：\n1. ffmpeg 目录下存在 ffprobe.exe\n2. 或者 FFmpeg 已正确安装并添加到系统 PATH"
                )

            cmd = [
                ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore"
            )
            if result.returncode != 0:
                raise Exception(f"FFprobe返回错误: {result.stderr}")

            if not result.stdout or result.stdout.strip() == "":
                raise Exception("FFprobe返回为空")

            data = json.loads(result.stdout)

            # 构建信息文本
            info_text = f"""文件名：{os.path.basename(video_path)}

路径：{video_path}

"""

            # 文件大小
            if os.path.exists(video_path):
                size_bytes = os.path.getsize(video_path)
                size_mb = size_bytes / (1024 * 1024)
                info_text += f"大小：{size_mb:.2f} MB\n\n"

            # 格式信息
            if "format" in data:
                fmt = data["format"]
                if "duration" in fmt:
                    duration = float(fmt["duration"])
                    hours = int(duration // 3600)
                    minutes = int((duration % 3600) // 60)
                    seconds = duration % 60
                    info_text += f"时长：{hours:02d}:{minutes:02d}:{seconds:06.3f}\n\n"

                if "bit_rate" in fmt:
                    bitrate_kbps = int(fmt["bit_rate"]) // 1000
                    info_text += f"码率：{bitrate_kbps} kb/s\n\n"

                if "tags" in fmt and "encoder" in fmt["tags"]:
                    info_text += f"编码器：{fmt['tags']['encoder']}\n\n"

            # 视频流信息
            for stream in data.get("streams", []):
                if stream["codec_type"] == "video":
                    codec = stream.get("codec_name", "unknown")
                    profile = stream.get("profile", "")
                    codec_tag = stream.get("codec_tag_string", "")
                    pix_fmt = stream.get("pix_fmt", "")
                    width = stream.get("width", 0)
                    height = stream.get("height", 0)
                    sar = stream.get("sample_aspect_ratio", "1:1")
                    dar = stream.get("display_aspect_ratio", "")
                    bitrate = (
                        int(stream.get("bit_rate", 0)) // 1000
                        if "bit_rate" in stream
                        else 0
                    )
                    fps = (
                        eval(stream.get("r_frame_rate", "0/1"))
                        if "/" in stream.get("r_frame_rate", "")
                        else 0
                    )

                    info_text += f"视频：{codec}"
                    if profile:
                        info_text += f" ({profile})"
                    if codec_tag:
                        info_text += f" ({codec_tag})"
                    info_text += f", {pix_fmt}, {width}x{height}"
                    if sar != "0:1":
                        info_text += f" [SAR {sar}"
                    if dar:
                        info_text += f" DAR {dar}]"
                    if bitrate > 0:
                        info_text += f", {bitrate} kb/s"
                    if fps > 0:
                        info_text += f", {fps:.0f} fps"
                    info_text += "\n\n"
                    break

            # 音频流信息
            for stream in data.get("streams", []):
                if stream["codec_type"] == "audio":
                    codec = stream.get("codec_name", "unknown")
                    profile = stream.get("profile", "")
                    codec_tag = stream.get("codec_tag_string", "")
                    sample_rate = stream.get("sample_rate", 0)
                    channels = stream.get("channels", 0)
                    channel_layout = stream.get("channel_layout", "")
                    bitrate = (
                        int(stream.get("bit_rate", 0)) // 1000
                        if "bit_rate" in stream
                        else 0
                    )

                    info_text += f"音频：{codec}"
                    if profile:
                        info_text += f" ({profile})"
                    if codec_tag:
                        info_text += f" ({codec_tag})"
                    info_text += f", {sample_rate} Hz"
                    if channel_layout:
                        info_text += f", {channel_layout}"
                    elif channels == 2:
                        info_text += ", stereo"
                    elif channels == 1:
                        info_text += ", mono"
                    if bitrate > 0:
                        info_text += f", {bitrate} kb/s"
                    info_text += "\n"
                    break

            # 显示对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(t("batch.main_window.auto.037", "媒体信息"))
            msg_box.setText(info_text)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            msg_box.exec()

        except Exception as e:
            import traceback

            error_detail = traceback.format_exc()
            QMessageBox.warning(
                self,
                t("batch.main_window.auto.036", "错误"),
                t(
                    "batch.main_window.auto.066",
                    "无法获取媒体信息:\n{error}\n\n详细信息：\n{detail}",
                    error=str(e),
                    detail=error_detail,
                ),
            )

    def refresh_table_numbers(self):
        """刷新表格编号"""
        for i in range(self.video_table.rowCount()):
            no_item = QTableWidgetItem(str(i + 1))
            no_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_table.setItem(i, self.COL_NO, no_item)

    def refresh_table(self):
        """刷新整个表格"""
        self.video_table.setRowCount(0)
        for i, video_info in enumerate(self.video_list):
            row = self.video_table.rowCount()
            self.video_table.insertRow(row)
            self.video_table.setItem(row, self.COL_CHECK, self._create_check_item())

            no_item = QTableWidgetItem(str(i + 1))
            no_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.video_table.setItem(row, self.COL_NO, no_item)

            file_name_item = QTableWidgetItem(os.path.basename(video_info["path"]))
            file_name_item.setData(Qt.ItemDataRole.UserRole, video_info["path"])
            self.video_table.setItem(row, self.COL_NAME, file_name_item)
            self.video_table.setItem(
                row, self.COL_INFO, QTableWidgetItem(video_info.get("info", ""))
            )

            # 状态列使用组合控件（圆点 + 文字）
            self._update_video_status_indicator(row, video_info.get("status", "pending"))

    def keyPressEvent(self, a0):
        """键盘事件处理"""
        # Ctrl+A 全选
        if (
            a0.key() == Qt.Key.Key_A
            and a0.modifiers() == Qt.KeyboardModifier.ControlModifier
        ):
            self.select_all_videos()
            a0.accept()
        # Delete 删除
        elif a0.key() == Qt.Key.Key_Delete:
            self.remove_selected_videos()
            a0.accept()
        else:
            super().keyPressEvent(a0)

    # ================== 对话框和功能方法 ==================

    def show_color_tone_dialog(self):
        """显示色调设置对话框"""
        from ui.color_tone_dialog import ColorToneDialog

        # 获取第一个视频路径用于预览
        first_video = None
        if self.video_list:
            selected_rows = self.get_selected_rows()
            if selected_rows:
                first_video = self.video_list[selected_rows[0]]["path"]
            else:
                first_video = self.video_list[0]["path"]

        dialog = ColorToneDialog(self, first_video)

        # 关键修复：恢复之前保存的配置
        if self.color_tone_config:
            dialog.set_config(self.color_tone_config)

        if dialog.exec():
            # 保存配置
            self.color_tone_config = dialog.get_config()
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> 色调设置已更新")

    def show_lut_filter_dialog(self):
        """显示LUT滤镜对话框"""
        from ui.lut_filter_dialog import LUTFilterDialog

        dialog = LUTFilterDialog(self)

        # 关键修复：恢复之前保存的配置
        if self.lut_filter_config:
            dialog.set_config(self.lut_filter_config)

        if dialog.exec():
            # 保存配置
            self.lut_filter_config = dialog.get_config()
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> LUT滤镜设置已更新")

    def show_more_effects_dialog(self):
        """显示更多效果对话框"""
        from ui.more_effects_dialog import MoreEffectsDialog

        # 获取第一个视频路径用于预览
        first_video = None
        if self.video_list:
            selected_rows = self.get_selected_rows()
            if selected_rows:
                first_video = self.video_list[selected_rows[0]]["path"]
            else:
                first_video = self.video_list[0]["path"]

        dialog = MoreEffectsDialog(self, first_video)

        # 关键修复：恢复之前保存的配置
        if self.more_effects_config:
            dialog.set_config(self.more_effects_config)

        if dialog.exec():
            # 保存配置
            self.more_effects_config = dialog.get_config()
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> 更多效果设置已更新")

    def show_dynamic_zoom_settings_dialog(self):
        """显示动态缩放设置对话框"""
        from ui.dynamic_zoom_dialog import DynamicZoomDialog

        # 获取第一个视频路径用于预览
        first_video = None
        if self.video_list:
            selected_rows = self.get_selected_rows()
            if selected_rows:
                first_video = self.video_list[selected_rows[0]]["path"]
            else:
                first_video = self.video_list[0]["path"]

        dialog = DynamicZoomDialog(self, first_video)

        # 关键修复：恢复之前保存的配置
        if self.dynamic_zoom_advanced_config:
            dialog.set_config(self.dynamic_zoom_advanced_config)

        if dialog.exec():
            # 保存配置
            self.dynamic_zoom_advanced_config = dialog.get_config()
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> 动态缩放设置已更新")
            self._refresh_live_validation_feedback()

    def on_resolution_check_changed(self, checked: bool):
        """分辨率复选框状态改变"""
        # 启用/禁用相关控件
        self.resolution_preset.setEnabled(checked)
        self.resolution_width.setEnabled(checked)
        self.resolution_height.setEnabled(checked)
        self.resolution_swap_btn.setEnabled(checked)
        self.mode_stretch.setEnabled(checked)
        self.mode_crop.setEnabled(checked)
        self.mode_original.setEnabled(checked)
        # 背景和倒影只在原比例模式下启用
        if checked and self.mode_original.isChecked():
            self.background_blur_check.setEnabled(True)
            self.reflection_check.setEnabled(True)
            self.reflection_opacity.setEnabled(True)
        else:
            self.background_blur_check.setEnabled(False)
            self.reflection_check.setEnabled(False)
            self.reflection_opacity.setEnabled(False)
        self.resolution_preview_btn.setEnabled(checked)

    def on_resolution_mode_changed(self, button, checked: bool):
        """分辨率模式改变，只有原比例时背景和倒影才可用"""
        if not checked:
            return

        # 检查分辨率调整是否启用
        if not self.resolution_check.isChecked():
            return

        # 只有选中“原比例”时，背景和倒影才可用
        if button == self.mode_original:
            self.background_blur_check.setEnabled(True)
            self.reflection_check.setEnabled(True)
            self.reflection_opacity.setEnabled(True)
        else:
            self.background_blur_check.setEnabled(False)
            self.reflection_check.setEnabled(False)
            self.reflection_opacity.setEnabled(False)

    def on_frame_adjust_check_changed(self, checked: bool):
        """画面调整复选框状态改变"""
        self.brightness_min.setEnabled(checked)
        self.brightness_max.setEnabled(checked)
        self.sharpness_min.setEnabled(checked)
        self.sharpness_max.setEnabled(checked)
        self.contrast_min.setEnabled(checked)
        self.contrast_max.setEnabled(checked)
        self.denoise_min.setEnabled(checked)
        self.denoise_max.setEnabled(checked)
        self.saturation_min.setEnabled(checked)
        self.saturation_max.setEnabled(checked)
        self.color_tone_btn.setEnabled(checked)
        self.lut_filter_btn.setEnabled(checked)
        self.more_effects_btn.setEnabled(checked)
        self.frame_adjust_preview_btn.setEnabled(checked)

    def on_bitrate_check_changed(self, checked: bool):
        """码率调整复选框状态改变"""
        self.bitrate_mode_dynamic.setEnabled(checked)
        self.bitrate_mode_fixed.setEnabled(checked)
        self.bitrate_dynamic_value.setEnabled(checked)
        self.bitrate_fixed_preset.setEnabled(checked)
        self.bitrate_ratio_min.setEnabled(checked)
        self.bitrate_ratio_max.setEnabled(checked)

    def on_grid_split_check_changed(self, checked: bool):
        """几宫格分屏复选框状态改变"""
        self.grid_count.setEnabled(checked)
        self.grid_direction.setEnabled(checked)
        self.grid_blur_check.setEnabled(checked)
        self.grid_preview_btn.setEnabled(checked)

    def on_resolution_preset_changed(self, text: str):
        """分辨率预设改变"""
        preset_code = normalize_resolution_preset(text)
        if preset_code == "p360":
            self.resolution_width.setValue(640)
            self.resolution_height.setValue(360)
        elif preset_code == "p480":
            self.resolution_width.setValue(854)
            self.resolution_height.setValue(480)
        elif preset_code == "p720":
            self.resolution_width.setValue(1280)
            self.resolution_height.setValue(720)
        elif preset_code == "p1080":
            self.resolution_width.setValue(1920)
            self.resolution_height.setValue(1080)
        elif preset_code == "swap":
            # 自动交换当前宽高
            w = self.resolution_width.value()
            h = self.resolution_height.value()
            self.resolution_width.setValue(h)
            self.resolution_height.setValue(w)
            # 恢复为自定义
            self._set_combo_by_code(
                self.resolution_preset, "custom", RESOLUTION_PRESET_LABELS
            )

    def swap_resolution(self):
        """交换分辨率宽高"""
        w = self.resolution_width.value()
        h = self.resolution_height.value()
        self.resolution_width.setValue(h)
        self.resolution_height.setValue(w)

    def on_rotate_check_changed(self, checked: bool):
        """旋转&翻转复选框状态改变"""
        self.flip_left90.setEnabled(checked)
        self.flip_right90.setEnabled(checked)
        self.flip_horizontal.setEnabled(checked)
        self.flip_vertical.setEnabled(checked)
        self.flip_random_direction.setEnabled(checked)
        self.flip_random.setEnabled(checked)
        self._update_rotate_random_controls()
        self.rotate_preview_btn.setEnabled(checked)

    def _update_rotate_random_controls(self):
        """根据随机角度选项更新相关控件"""
        enabled = (
            self.rotate_check.isChecked() if hasattr(self, "rotate_check") else False
        )
        use_random_angle = enabled and self.flip_random.isChecked()
        self.flip_random_angle.setEnabled(use_random_angle)
        self.flip_random_angle_max.setEnabled(use_random_angle)
        self.flip_complete_check.setEnabled(use_random_angle)
        self.flip_black_edge_check.setEnabled(use_random_angle)

    def on_fps_check_changed(self, checked: bool):
        """帧率设置复选框状态改变"""
        self.fps_min.setEnabled(checked)
        self.fps_max.setEnabled(checked)
        self.remove_duplicate_frames_check.setEnabled(checked)
        self.fps_preview_btn.setEnabled(checked)

    def on_frame_extract_check_changed(self, checked: bool):
        """抽帧复选框状态改变"""
        self.frame_extract_min.setEnabled(checked)
        self.frame_extract_max.setEnabled(checked)
        self.audio_speed_check.setEnabled(checked)
        self.frame_extract_preview_btn.setEnabled(checked)

    def on_dynamic_zoom_check_changed(self, checked: bool):
        """动态缩放复选框状态改变"""
        self.dynamic_zoom_min.setEnabled(checked)
        self.dynamic_zoom_max.setEnabled(checked)
        self.dynamic_zoom_settings_btn.setEnabled(checked)
        self.dynamic_zoom_preview_btn.setEnabled(checked)

    def on_trim_check_changed(self, checked: bool):
        """视频长度裁剪复选框状态改变"""
        self.trim_mode1_radio.setEnabled(checked)
        self.trim_mode2_radio.setEnabled(checked)
        self.on_trim_mode_changed()
        self.trim_preview_btn.setEnabled(checked)

    def on_trim_mode_changed(self):
        """去头尾/截取模式切换，启用对应输入"""
        enabled = self.trim_check.isChecked()
        if not enabled:
            self.trim_head.setEnabled(False)
            self.trim_tail.setEnabled(False)
            self.trim_start.setEnabled(False)
            self.trim_duration.setEnabled(False)
            return

        if self.trim_mode1_radio.isChecked():
            self.trim_head.setEnabled(True)
            self.trim_tail.setEnabled(True)
            self.trim_start.setEnabled(False)
            self.trim_duration.setEnabled(False)
        else:
            self.trim_head.setEnabled(False)
            self.trim_tail.setEnabled(False)
            self.trim_start.setEnabled(True)
            self.trim_duration.setEnabled(True)

    def on_speed_check_changed(self, checked: bool):
        """音视频变速复选框状态改变"""
        self.speed_min.setEnabled(checked)
        self.speed_max.setEnabled(checked)
        self.speed_min_duration_check.setEnabled(checked)
        self.speed_min_duration.setEnabled(checked)
        self.speed_segment_check.setEnabled(checked)
        self.speed_segment_duration.setEnabled(checked)
        self.speed_pitch_check.setEnabled(checked)
        self.speed_preview_btn.setEnabled(checked)

    def _on_text_check_changed(self, track_num: int, checked: bool):
        """文本轨道复选框状态改变（统一处理1/2/3）"""
        preview = getattr(self, f"text{track_num}_preview", None)
        settings_btn = getattr(self, f"text{track_num}_settings_btn", None)
        preview_btn = getattr(self, f"text{track_num}_preview_btn", None)

        if not all([preview, settings_btn, preview_btn]):
            return

        preview.setEnabled(checked)
        settings_btn.setEnabled(checked)
        preview_btn.setEnabled(checked)

    def _on_text_settings(self, track_num: int):
        """打开文本设置对话框"""
        from ui.text_config_dialog import TextConfigDialog

        # 获取当前配置
        current_config = self.text_configs[track_num - 1]

        # 打开对话框
        dialog = TextConfigDialog(self, track_num, current_config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 保存配置
            self.text_configs[track_num - 1] = dialog.get_config()
            # 更新预览摘要
            self._update_text_preview_summary(track_num)

    def _on_text_preview(self, track_num: int):
        """预览文本效果（不打开设置窗口）"""
        config = self.text_configs[track_num - 1]
        if not self._validate_text_source_config(track_num, config):
            return

        # 选择视频
        selected_rows = self.get_selected_rows()
        if not selected_rows:
            if not self.video_list:
                self._warn("提示", "请先导入视频")
                return
            video_path = self.video_list[0]["path"]
        else:
            video_path = self.video_list[selected_rows[0]]["path"]

        # 构建临时配置（只启用当前文本轨道）
        temp_config = self.collect_config()
        temp_config["text"] = {
            "text1_enabled": track_num == 1,
            "text1_config": self.text_configs[0] if track_num == 1 else None,
            "text2_enabled": track_num == 2,
            "text2_config": self.text_configs[1] if track_num == 2 else None,
            "text3_enabled": track_num == 3,
            "text3_config": self.text_configs[2] if track_num == 3 else None,
        }

        self._show_preview_with_config(video_path, f"文本{track_num}预览", temp_config)

    def _on_text_inline_changed(self, track_num: int, text: str):
        """文本框直接编辑内容（仅作用于文本模式）"""
        config = self.text_configs[track_num - 1]
        if not config:
            config = self._get_default_text_config()
            self.text_configs[track_num - 1] = config
        if normalize_text_source_mode(config.get("source_mode")) != "plain":
            return
        config["text_content"] = text
        self._update_text_preview_summary(track_num)

    def _get_default_text_config(self) -> Dict:
        """默认文本配置（对齐对话框默认值）"""
        return {
            "source_mode": "plain",
            "text_content": "",
            "position": "center",
            "margin_x": 0,
            "margin_y": 0,
            "line_spacing": 10,
            "unit": "p",
            "font_enabled": True,
            "font_family": "微软雅黑",
            "font_size": 24,
            "font_color": "#FFFFFF",
            "font_opacity": 0.80,
            "shadow_enabled": False,
            "shadow_color": "#000000",
            "shadow_depth": 2,
            "stroke_enabled": False,
            "stroke_color": "#FFFFFF",
            "stroke_width": 1,
            "bg_enabled": False,
            "bg_color": "#808080",
            "bg_opacity": 0.8,
            "bg_style": "default",
            "bg_fit": False,
            "bg_padding": 5,
            "scroll_enabled": False,
            "scroll_direction": "right",
            "scroll_speed": 1.0,
            "random_speed": False,
            "diagonal": False,
            "delay": 0,
            "interval": 1,
            "duration": 5,
            "line_display": False,
            "loop": False,
        }

    def _on_text_scroll(self, track_num: int, direction: int):
        """文本预览上下滚动"""
        lines = self.text_preview_lines[track_num - 1]
        if not lines:
            return

        offset = self.text_preview_offsets[track_num - 1]
        offset += direction
        offset = max(0, min(len(lines) - 1, offset))
        self.text_preview_offsets[track_num - 1] = offset

        # 更新显示
        preview = getattr(self, f"text{track_num}_preview", None)
        if not preview:
            return
        if offset < len(lines):
            preview.setText(lines[offset])

    def _update_text_preview_summary(self, track_num: int):
        """更新文本预览摘要"""
        config = self.text_configs[track_num - 1]
        preview = getattr(self, f"text{track_num}_preview", None)
        if not preview:
            return

        if not config:
            preview.setText("")
            preview.setPlaceholderText(t("batch.main_window.auto.038", "未配置"))
            self.text_preview_lines[track_num - 1] = []
            return

        mode = normalize_text_source_mode(config.get("source_mode", "plain"))
        if mode == "plain":
            text = config.get("text_content", "")
            preview.setText(text)
        else:
            # 文件名/文件夹模式仅显示提示，不覆盖用户输入
            if not preview.text().strip():
                preview_label = enum_label(
                    TEXT_SOURCE_MODE_LABELS, mode, self._language_manager.language
                )
                preview.setText(f"[{preview_label}]")
        preview.setPlaceholderText(t("batch.main_window.auto.039", "已配置"))

    # 保留旧接口兼容性
    def on_text1_check_changed(self, checked: bool):
        """文本1复选框状态改变（兼容旧接口）"""
        self._on_text_check_changed(1, checked)

    def on_text2_check_changed(self, checked: bool):
        """文本2复选框状态改变（兼容旧接口）"""
        self._on_text_check_changed(2, checked)

    def on_text3_check_changed(self, checked: bool):
        """文本3复选框状态改变（兼容旧接口）"""
        self._on_text_check_changed(3, checked)

    def on_bgm_check_changed(self, checked: bool):
        """背景音乐复选框状态改变"""
        self.bgm_path.setEnabled(checked)
        self.bgm_import_btn.setEnabled(checked)
        self.bgm_mode_btn.setEnabled(checked)
        self.bgm_volume.setEnabled(checked)
        self.bgm_fadein_check.setEnabled(checked)
        self.bgm_delay_check.setEnabled(checked)
        self.original_volume_check.setEnabled(checked)
        self.original_fade_sync_check.setEnabled(checked)
        self.bgm_loop_check.setEnabled(checked)
        # 随机应用仅在目录模式下启用
        if checked and self.bgm_mode == "dir":
            self.bgm_random_check.setEnabled(True)
        else:
            self.bgm_random_check.setEnabled(False)

    def on_bgm_import_clicked(self):
        """导入背景音乐文件/目录"""
        if self.bgm_mode == "file":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t("batch.main_window.auto.040", "选择音频文件"),
                "",
                t(
                    "batch.main_window.auto.041",
                    "音频文件 (*.mp3 *.wav *.aac *.m4a *.flac *.ogg);;所有文件 (*.*)",
                ),
            )
            if file_path:
                self.bgm_path.setText(file_path)
        else:  # directory mode
            dir_path = QFileDialog.getExistingDirectory(
                self, t("batch.main_window.auto.042", "选择音频文件夹")
            )
            if dir_path:
                self.bgm_path.setText(dir_path)

    def on_bgm_mode_toggle(self):
        """切换文件/目录模式"""
        if self.bgm_mode == "file":
            self.bgm_mode = "dir"
            self.bgm_mode_btn.setIcon(load_svg_icon("folder", 14, "#64748B"))
            self.bgm_mode_btn.setText(self._ts("文件夹"))
            self.bgm_mode_btn.setToolTip(
                self._ts("当前：文件夹模式（可随机选取，点击切换到文件模式）")
            )
            self.bgm_random_check.setEnabled(self.bgm_check.isChecked())
            self.bgm_path.setPlaceholderText(self._ts("未选择音频文件夹"))
        else:
            self.bgm_mode = "file"
            self.bgm_mode_btn.setIcon(load_svg_icon("file", 14, "#64748B"))
            self.bgm_mode_btn.setText(self._ts("文件"))
            self.bgm_mode_btn.setToolTip(self._ts("当前：文件模式（点击切换到文件夹模式）"))
            self.bgm_random_check.setChecked(False)
            self.bgm_random_check.setEnabled(False)
            self.bgm_path.setPlaceholderText(self._ts("未选择音频文件"))
        # 清空路径
        self.bgm_path.clear()

    def on_bgm_fadein_check_changed(self, checked: bool):
        """淡入淡出复选框状态改变"""
        self.bgm_fadein_duration.setEnabled(checked)

    def on_bgm_delay_check_changed(self, checked: bool):
        """延迟复选框状态改变"""
        self.bgm_delay.setEnabled(checked)

    def on_original_volume_check_changed(self, checked: bool):
        """原音音量复选框状态改变"""
        self.original_volume.setEnabled(checked)

    # ==================== 加头尾相关方法 ====================

    def on_head_check_changed(self, checked: bool):
        """片头复选框状态改变"""
        self.head_file.setEnabled(checked)
        self.head_browse_btn.setEnabled(checked)
        self.head_mode_btn.setEnabled(checked)
        # 随机应用仅在目录模式下可用
        mode = self.head_mode_btn.property("mode")
        enable_random = checked and mode == "folder"
        self.head_random_check.setEnabled(enable_random)
        if not enable_random:
            self.head_random_check.setChecked(False)
        self._refresh_live_validation_feedback()

    def on_head_browse_clicked(self):
        """选择片头文件/目录"""
        mode = self.head_mode_btn.property("mode")
        if mode == "file":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t("batch.main_window.auto.043", "选择片头视频"),
                "",
                t(
                    "batch.main_window.auto.044",
                    "视频文件 (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;所有文件 (*.*)",
                ),
            )
            if file_path:
                self.head_file.setText(file_path)
        else:  # folder mode
            dir_path = QFileDialog.getExistingDirectory(
                self, t("batch.main_window.auto.045", "选择片头视频目录")
            )
            if dir_path:
                self.head_file.setText(dir_path)

    def on_head_mode_clicked(self):
        """切换片头文件/目录模式"""
        current_mode = self.head_mode_btn.property("mode")
        if current_mode == "file":
            # 切换到目录模式
            self.head_mode_btn.setIcon(load_svg_icon("folder", 14, "#64748B"))
            self.head_mode_btn.setProperty("mode", "folder")
            self.head_mode_btn.setText(self._ts("文件夹"))
            self.head_mode_btn.setToolTip(
                self._ts("当前：文件夹模式（可随机选取，点击切换到文件模式）")
            )
            self.head_random_check.setEnabled(self.head_check.isChecked())
            self.head_browse_btn.setText(self._ts("选择目录"))
            self.head_file.setPlaceholderText(self._ts("未选择片头目录"))
        else:
            # 切换到文件模式
            self.head_mode_btn.setIcon(load_svg_icon("file", 14, "#64748B"))
            self.head_mode_btn.setProperty("mode", "file")
            self.head_mode_btn.setText(self._ts("文件"))
            self.head_mode_btn.setToolTip(self._ts("当前：文件模式（点击切换到文件夹模式）"))
            self.head_random_check.setChecked(False)
            self.head_random_check.setEnabled(False)
            self.head_browse_btn.setText(self._ts("选择文件"))
            self.head_file.setPlaceholderText(self._ts("未选择片头文件"))
        # 清空路径
        self.head_file.clear()
        self._refresh_live_validation_feedback()

    def on_tail_check_changed(self, checked: bool):
        """片尾复选框状态改变"""
        self.tail_file.setEnabled(checked)
        self.tail_browse_btn.setEnabled(checked)
        self.tail_mode_btn.setEnabled(checked)
        # 随机应用仅在目录模式下可用
        mode = self.tail_mode_btn.property("mode")
        enable_random = checked and mode == "folder"
        self.tail_random_check.setEnabled(enable_random)
        if not enable_random:
            self.tail_random_check.setChecked(False)
        self._refresh_live_validation_feedback()

    def on_tail_browse_clicked(self):
        """选择片尾文件/目录"""
        mode = self.tail_mode_btn.property("mode")
        if mode == "file":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t("batch.main_window.auto.046", "选择片尾视频"),
                "",
                t(
                    "batch.main_window.auto.044",
                    "视频文件 (*.mp4 *.mov *.avi *.mkv *.webm *.m4v);;所有文件 (*.*)",
                ),
            )
            if file_path:
                self.tail_file.setText(file_path)
        else:  # folder mode
            dir_path = QFileDialog.getExistingDirectory(
                self, t("batch.main_window.auto.047", "选择片尾视频目录")
            )
            if dir_path:
                self.tail_file.setText(dir_path)

    def on_tail_mode_clicked(self):
        """切换片尾文件/目录模式"""
        current_mode = self.tail_mode_btn.property("mode")
        if current_mode == "file":
            # 切换到目录模式
            self.tail_mode_btn.setIcon(load_svg_icon("folder", 14, "#64748B"))
            self.tail_mode_btn.setProperty("mode", "folder")
            self.tail_mode_btn.setText(self._ts("文件夹"))
            self.tail_mode_btn.setToolTip(
                self._ts("当前：文件夹模式（可随机选取，点击切换到文件模式）")
            )
            self.tail_random_check.setEnabled(self.tail_check.isChecked())
            self.tail_browse_btn.setText(self._ts("选择目录"))
            self.tail_file.setPlaceholderText(self._ts("未选择片尾目录"))
        else:
            # 切换到文件模式
            self.tail_mode_btn.setIcon(load_svg_icon("file", 14, "#64748B"))
            self.tail_mode_btn.setProperty("mode", "file")
            self.tail_mode_btn.setText(self._ts("文件"))
            self.tail_mode_btn.setToolTip(self._ts("当前：文件模式（点击切换到文件夹模式）"))
            self.tail_random_check.setChecked(False)
            self.tail_random_check.setEnabled(False)
            self.tail_browse_btn.setText(self._ts("选择文件"))
            self.tail_file.setPlaceholderText(self._ts("未选择片尾文件"))
        # 清空路径
        self.tail_file.clear()
        self._refresh_live_validation_feedback()

    def on_border_check_changed(self, checked: bool):
        """边框复选框状态改变"""
        self.border_file.setEnabled(checked)
        self.border_browse_btn.setEnabled(checked)
        self.border_mode_btn.setEnabled(checked)
        self.border_style_label.setEnabled(checked)
        self.border_style_label.setStyleSheet(
            f"color: {Theme.Primary if checked else Theme.TextDisabled}; font-size: 13px; font-weight: normal;"
        )
        self.border_style_label.setCursor(
            Qt.CursorShape.PointingHandCursor if checked else Qt.CursorShape.ArrowCursor
        )
        # 预览需要边框文件存在
        has_file = bool(self.border_file.text())
        self.border_preview_btn.setEnabled(checked and has_file)
        self._refresh_live_validation_feedback()

    def on_border_browse_clicked(self):
        """选择边框文件/目录"""
        mode = self.border_mode_btn.property("mode")
        if mode == "file":
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t("batch.main_window.auto.048", "选择边框图片"),
                "",
                t(
                    "batch.main_window.auto.049",
                    "图片文件 (*.png *.jpg *.jpeg *.gif);;所有文件 (*.*)",
                ),
            )
            if file_path:
                self.border_file.setText(file_path)
                # 启用预览
                if self.border_check.isChecked():
                    self.border_preview_btn.setEnabled(True)
        else:  # folder mode
            dir_path = QFileDialog.getExistingDirectory(
                self, t("batch.main_window.auto.050", "选择边框图片目录")
            )
            if dir_path:
                self.border_file.setText(dir_path)
                # 启用预览
                if self.border_check.isChecked():
                    self.border_preview_btn.setEnabled(True)

    def on_border_mode_clicked(self):
        """切换边框文件/目录模式"""
        current_mode = self.border_mode_btn.property("mode")
        if current_mode == "file":
            # 切换到目录模式（目录模式默认随机）
            self.border_mode_btn.setIcon(load_svg_icon("folder", 14, "#64748B"))
            self.border_mode_btn.setProperty("mode", "folder")
            self.border_mode_btn.setText(self._ts("文件夹"))
            self.border_mode_btn.setToolTip(
                self._ts("当前：文件夹模式（随机选取，点击切换到文件模式）")
            )
            self.border_browse_btn.setText(self._ts("选择目录"))
            self.border_file.setPlaceholderText(self._ts("未选择边框目录（png, jpg, gif）"))
        else:
            # 切换到文件模式
            self.border_mode_btn.setIcon(load_svg_icon("file", 14, "#64748B"))
            self.border_mode_btn.setProperty("mode", "file")
            self.border_mode_btn.setText(self._ts("文件"))
            self.border_mode_btn.setToolTip(self._ts("当前：文件模式（点击切换到文件夹模式）"))
            self.border_browse_btn.setText(self._ts("选择文件"))
            self.border_file.setPlaceholderText(self._ts("未选择边框文件（png, jpg, gif）"))
            # 文件模式禁用随机应用
            self.border_style_config["border_random"] = False
        # 清空路径
        self.border_file.clear()
        self.border_preview_btn.setEnabled(False)
        self._refresh_live_validation_feedback()

    def on_border_style_clicked(self):
        """打开边框样式设置对话框"""
        dialog = BorderStyleDialog(self, self.border_style_config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.border_style_config = dialog.get_config()
            print(f"边框样式配置已更新: {self.border_style_config}")

    def on_border_preview_clicked(self):
        """预览边框效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        if not self.border_check.isChecked():
            self._warn("提示", "请先启用边框功能")
            return

        if not self.border_file.text():
            self._warn("提示", "请先选择边框文件或目录")
            return

        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "加头尾预览")

    # ==================== 去水印相关方法 ====================

    def on_remove_watermark_check_changed(self, checked: bool):
        """去水印复选框状态改变"""
        # 启用/禁用方法选择下拉框
        self.watermark_method_combo.setEnabled(checked)

        # 固定选择默认方法（FFmpeg）
        self.watermark_method_combo.blockSignals(True)
        self.watermark_method_combo.setCurrentIndex(1)
        self.watermark_method_combo.blockSignals(False)

        if hasattr(self, "watermark_method_display"):
            display_color = Theme.TextPrimary if checked else Theme.TextDisabled
            self.watermark_method_display.setStyleSheet(
                f"background: {Theme.Surface}; border: 1px solid {Theme.Border}; border-radius: 6px; "
                f"padding: 6px 10px; color: {display_color}; font-size: 13px;"
            )
            self.watermark_method_display.setText(
                self.watermark_method_combo.currentText()
            )

        # 同步可见性（不隐藏）
        method_index = self.watermark_method_combo.currentIndex()
        if hasattr(self, "ffmpeg_group"):
            self.ffmpeg_group.setVisible(method_index == 1)
        if hasattr(self, "region_group"):
            self.region_group.setVisible(method_index in [1, 2, 6, 8])
        if hasattr(self, "time_period_group"):
            self.time_period_group.setVisible(method_index in [1, 2])
        if hasattr(self, "iopaint_group"):
            self.iopaint_group.setVisible(method_index == 4)
        if hasattr(self, "ai_group"):
            self.ai_group.setVisible(method_index == 3)
        if hasattr(self, "opencv_group"):
            self.opencv_group.setVisible(method_index == 2)
        if hasattr(self, "api_group"):
            self.api_group.setVisible(method_index == 9)
        if hasattr(self, "textremover_group"):
            self.textremover_group.setVisible(method_index == 8)

        # 预览按钮始终可见，按启用状态置灰
        self.watermark_preview_btn.setVisible(True)
        self.watermark_preview_btn.setEnabled(checked)

        if not checked:
            # 仅置灰，不隐藏
            if hasattr(self, "ffmpeg_group"):
                self._set_ffmpeg_group_enabled(False)
            if hasattr(self, "region_group"):
                self._set_region_group_enabled(False)
            if hasattr(self, "opencv_group"):
                self._set_opencv_group_enabled(False)
            if hasattr(self, "api_group"):
                self._set_api_group_enabled(False)
            if hasattr(self, "textremover_group"):
                self._set_textremover_group_enabled(False)
            if hasattr(self, "time_period_enable_check"):
                self.time_period_enable_check.setEnabled(False)
            if hasattr(self, "time_period_select_btn"):
                self.time_period_select_btn.setEnabled(False)
            if hasattr(self, "time_period_display"):
                self.time_period_display.setEnabled(False)
            self._update_crop_remove_watermark_conflict_hint()
            return

        # 启用时：按方法刷新显示与可用状态
        if hasattr(self, "time_period_enable_check"):
            self.time_period_enable_check.setEnabled(True)
        self.on_watermark_method_changed(1)
        self._update_crop_remove_watermark_conflict_hint()

    def on_watermark_method_changed(self, index: int):
        """去水印方法改变时的联动"""
        if not self.remove_watermark_check.isChecked():
            return

        # 检查属性是否已初始化（避免初始化时调用报错）
        if not hasattr(self, "ffmpeg_group"):
            return

        # index 是当前下拉框的索引
        # 1-4: 静态水印 (FFmpeg, OpenCV, LaMa, IOPaint)
        # 5-6: 移动水印 (ProPainter, multi-delogo)
        # 7: 字幕去除-OCR-AI方式 (自动检测，不需要区域设置)
        # 8: 字幕去除-手动框选处理 (需要手动指定区域)
        # 9: 商业API

        # FFmpeg高级设置: 仅在FFmpeg方法时显示 (index == 1)
        self.ffmpeg_group.setVisible(index == 1)
        self._set_ffmpeg_group_enabled(index == 1)

        # 水印区域设置: 仅在确实需要区域坐标的场景显示
        # 需要区域的场景：1=FFmpeg delogo, 2=OpenCV inpaint, 6=multi-delogo(移动多标志), 8=文字移除器
        # 不需要区域：3=LaMa AI, 4=IOPaint, 5=ProPainter, 7=OCR-AI字幕去除, 9=商业API
        region_enabled = index in [1, 2, 6, 8]
        self.region_group.setVisible(region_enabled)
        self._set_region_group_enabled(region_enabled)

        # 时间段设置: 仅在FFmpeg(1)和OpenCV(2)方法时显示，并且需要启用
        time_period_enabled = index in [1, 2]  # FFMPEG DELOGO和OPENCV方式
        if hasattr(self, "time_period_group"):
            self.time_period_group.setVisible(time_period_enabled)
            # 同步复选框状态与按钮/显示的状态
            if hasattr(self, "time_period_enable_check"):
                self.time_period_select_btn.setEnabled(
                    self.time_period_enable_check.isChecked()
                )
                self.time_period_display.setEnabled(
                    self.time_period_enable_check.isChecked()
                )

        # 更新水印预设显示状态：仅在静态平台预设有意义的方法显示（FFmpeg/OpenCV）
        if hasattr(self, "watermark_preset"):
            show_preset = index in [1, 2]
            self.watermark_preset.setVisible(show_preset)
            if hasattr(self, "preset_hint_label"):
                # 预设提示与预设显示保持一致
                self.preset_hint_label.setVisible(
                    False if not show_preset else self.preset_hint_label.isVisible()
                )

        # OpenCV设置: 仅在OpenCV方法时显示 (index == 2)
        if hasattr(self, "opencv_group"):
            self.opencv_group.setVisible(index == 2)
            self._set_opencv_group_enabled(index == 2)

        # 商业API设置: 仅在API方法时显示 (index == 9)
        if hasattr(self, "api_group"):
            self.api_group.setVisible(index == 9)
            self._set_api_group_enabled(index == 9)

        # TEXT-REMOVER设置: 仅在文字移除器方法时显示 (index == 8)
        if hasattr(self, "textremover_group"):
            self.textremover_group.setVisible(index == 8)
            self._set_textremover_group_enabled(index == 8)

        # 显示预览按钮
        self.watermark_preview_btn.setVisible(True)
        self.watermark_preview_btn.setEnabled(True)
        self._update_crop_remove_watermark_conflict_hint()

    def _set_ffmpeg_group_enabled(self, enabled: bool):
        """启用/禁用FFmpeg设置组内的所有控件"""
        if hasattr(self, "ffmpeg_crf"):
            self.ffmpeg_crf.setEnabled(enabled)
        if hasattr(self, "ffmpeg_preset"):
            self.ffmpeg_preset.setEnabled(enabled)

    def _set_region_group_enabled(self, enabled: bool):
        """启用/禁用水印区域设置组内的所有控件"""
        if hasattr(self, "region_count_combo"):
            self.region_count_combo.setEnabled(enabled)

        # 仅FFmpeg/OpenCV场景显示平台预设
        method_index = self.watermark_method_combo.currentIndex()
        show_preset = enabled and method_index in [1, 2]

        if hasattr(self, "preset_widget"):
            self.preset_widget.setVisible(show_preset)

        if hasattr(self, "watermark_preset"):
            self.watermark_preset.setEnabled(show_preset)
        if hasattr(self, "preset_hint_label"):
            self.preset_hint_label.setVisible(False)
        self._update_crop_remove_watermark_conflict_hint()

        # 触发区域数量改变，更新区域控件的状态
        if enabled and hasattr(self, "region_count_combo"):
            self.on_region_count_changed(self.region_count_combo.currentIndex())
        else:
            # 禁用所有区域控件
            self._disable_all_regions()

    def _disable_all_regions(self):
        """禁用所有区域控件"""
        for i in range(1, 4):
            for attr in ["_x", "_y", "_w", "_h", "_select_btn"]:
                widget_name = f"region{i}{attr}"
                if hasattr(self, widget_name):
                    getattr(self, widget_name).setEnabled(False)

    def _set_api_group_enabled(self, enabled: bool):
        """启用/禁用API设置组内的所有控件"""
        if hasattr(self, "api_provider"):
            self.api_provider.setEnabled(enabled)
        if hasattr(self, "api_key"):
            self.api_key.setEnabled(enabled)

    def _set_textremover_group_enabled(self, enabled: bool):
        """启用/禁用TEXT-REMOVER设置组内的所有控件"""
        if hasattr(self, "textremover_method"):
            self.textremover_method.setEnabled(enabled)
        if hasattr(self, "textremover_sensitivity"):
            self.textremover_sensitivity.setEnabled(enabled)
        if hasattr(self, "textremover_blur_strength"):
            self.textremover_blur_strength.setEnabled(enabled)
        if hasattr(self, "textremover_blur_strength_label"):
            self.textremover_blur_strength_label.setEnabled(enabled)
        if hasattr(self, "textremover_auto_detect"):
            self.textremover_auto_detect.setEnabled(enabled)
            # 连接自动检测复选框的信号，以便动态启用/禁用检测方式下拉框
            if not hasattr(self, "_textremover_auto_detect_connected"):
                self.textremover_auto_detect.toggled.connect(
                    self._on_textremover_auto_detect_changed
                )
                self._textremover_auto_detect_connected = True
        if hasattr(self, "textremover_detect_method"):
            # 检测方式下拉框只有在启用自动检测时才启用
            auto_detect_checked = (
                hasattr(self, "textremover_auto_detect")
                and self.textremover_auto_detect.isChecked()
            )
            self.textremover_detect_method.setEnabled(enabled and auto_detect_checked)

        # 更新模糊强度的可见性（根据当前选择的处理方式）
        self._update_blur_strength_visibility()

    def _update_blur_strength_visibility(self):
        """根据处理方式更新模糊强度控件的可见性"""
        if hasattr(self, "textremover_method") and hasattr(
            self, "textremover_blur_strength"
        ):
            # 获取处理方式索引：0=背景复制，1=高斯模糊
            method_index = self.textremover_method.currentIndex()
            # 只有选择高斯模糊时才显示模糊强度
            self.textremover_blur_strength.setVisible(method_index == 1)
            # 同时更新模糊强度标签的可见性
            # 找到模糊强度标签并设置可见性
            if hasattr(self, "textremover_blur_strength_label"):
                self.textremover_blur_strength_label.setVisible(method_index == 1)

    def _on_textremover_method_changed(self, index: int):
        """处理方式改变时的事件处理"""
        # 根据选择的处理方式显示/隐藏模糊强度控件
        if hasattr(self, "textremover_blur_strength") and hasattr(
            self, "textremover_blur_strength_label"
        ):
            # index: 0=背景复制，1=高斯模糊
            blur_visible = index == 1
            self.textremover_blur_strength.setVisible(blur_visible)
            self.textremover_blur_strength_label.setVisible(blur_visible)

    def _on_opencv_method_changed(self, index: int):
        """OpenCV处理方式改变时的事件处理"""
        # 根据选择的处理方式显示/隐藏模糊强度控件
        if hasattr(self, "opencv_blur_strength") and hasattr(
            self, "opencv_blur_strength_label"
        ):
            # index: 0=背景复制，1=高斯模糊
            blur_visible = index == 1
            self.opencv_blur_strength.setVisible(blur_visible)
            self.opencv_blur_strength_label.setVisible(blur_visible)

    def _set_opencv_group_enabled(self, enabled: bool):
        """启用/禁用OpenCV设置组内的所有控件"""
        if hasattr(self, "opencv_method"):
            self.opencv_method.setEnabled(enabled)
        if hasattr(self, "opencv_blur_strength"):
            self.opencv_blur_strength.setEnabled(enabled)
        if hasattr(self, "opencv_blur_strength_label"):
            self.opencv_blur_strength_label.setEnabled(enabled)

        # 更新模糊强度的可见性
        if enabled and hasattr(self, "opencv_method"):
            method_index = self.opencv_method.currentIndex()
            if hasattr(self, "opencv_blur_strength") and hasattr(
                self, "opencv_blur_strength_label"
            ):
                blur_visible = method_index == 1
                self.opencv_blur_strength.setVisible(blur_visible)
                self.opencv_blur_strength_label.setVisible(blur_visible)

    def on_region_count_changed(self, index: int):
        """区域数量改变"""
        if not self.remove_watermark_check.isChecked():
            return

        # 检查属性是否已初始化
        if not hasattr(self, "region1_widget"):
            return

        # 0=1个区域, 1=2个区域, 2=3个区域
        # 根据数量显示/隐藏对应区域
        self.region1_widget.setVisible(index >= 0)  # 1个或3个区域都显示
        self.region2_widget.setVisible(index >= 1)  # 2个或3个区域显示
        self.region3_widget.setVisible(index >= 2)  # 3个区域显示

        # 同时控制标签的显示/隐藏
        if hasattr(self, "region1_label"):
            self.region1_label.setVisible(index >= 0)
        if hasattr(self, "region2_label"):
            self.region2_label.setVisible(index >= 1)
        if hasattr(self, "region3_label"):
            self.region3_label.setVisible(index >= 2)

        # 启用对应的输入框和按钮
        enable_region1 = True
        self.region1_x.setEnabled(enable_region1)
        self.region1_y.setEnabled(enable_region1)
        self.region1_w.setEnabled(enable_region1)
        self.region1_h.setEnabled(enable_region1)
        self.region1_select_btn.setEnabled(enable_region1)

        enable_region2 = index >= 1
        self.region2_x.setEnabled(enable_region2)
        self.region2_y.setEnabled(enable_region2)
        self.region2_w.setEnabled(enable_region2)
        self.region2_h.setEnabled(enable_region2)
        self.region2_select_btn.setEnabled(enable_region2)

        enable_region3 = index >= 2
        self.region3_x.setEnabled(enable_region3)
        self.region3_y.setEnabled(enable_region3)
        self.region3_w.setEnabled(enable_region3)
        self.region3_h.setEnabled(enable_region3)
        self.region3_select_btn.setEnabled(enable_region3)

        # 仅FFmpeg/OpenCV场景显示平台预设
        method_index = self.watermark_method_combo.currentIndex()
        show_preset = method_index in [1, 2]
        if hasattr(self, "preset_widget"):
            self.preset_widget.setVisible(show_preset)
        self.watermark_preset.setEnabled(show_preset)
        if hasattr(self, "preset_hint_label"):
            self.preset_hint_label.setVisible(False)
        self._update_crop_remove_watermark_conflict_hint()

    def apply_watermark_preset(self, index: int):
        """应用水印预设（主流平台8个预设）"""
        # 说明文字：仅在选择具体平台时显示
        if hasattr(self, "preset_hint_label"):
            self.preset_hint_label.setVisible(index > 0)
        if index == 0:  # 自定义
            return

        preset_code = normalize_watermark_preset(
            self.watermark_preset.currentData()
            if self.watermark_preset.currentData() is not None
            else self.watermark_preset.currentText()
        )

        # 获取视频分辨率用于动态计算（如果有视频则使用实际分辨率，否则使用1920x1080作为默认）
        video_width = 1920
        video_height = 1080

        if self.video_list:
            # 获取第一个视频的分辨率
            first_video = self.video_list[0]
            video_path = (
                first_video
                if isinstance(first_video, str)
                else first_video.get("path", "")
            )
            if video_path and os.path.exists(video_path):
                try:
                    import subprocess
                    import json

                    # 查找ffprobe路径
                    app_dir = os.path.dirname(
                        os.path.dirname(os.path.abspath(__file__))
                    )
                    ffprobe_path = None
                    for check_path in [
                        os.path.join(app_dir, "ffmpeg", "ffprobe.exe"),
                        os.path.join(app_dir, "processor", "ffprobe.exe"),
                        "ffprobe",
                    ]:
                        if check_path == "ffprobe" or os.path.exists(check_path):
                            ffprobe_path = check_path
                            break

                    if ffprobe_path:
                        cmd = [
                            ffprobe_path,
                            "-v",
                            "quiet",
                            "-print_format",
                            "json",
                            "-show_streams",
                            video_path,
                        ]
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=10,
                            encoding="utf-8",
                            creationflags=subprocess.CREATE_NO_WINDOW
                            if os.name == "nt"
                            else 0,
                        )
                        if result.returncode == 0 and result.stdout:
                            data = json.loads(result.stdout)
                            video_stream = next(
                                (
                                    s
                                    for s in data.get("streams", [])
                                    if s.get("codec_type") == "video"
                                ),
                                None,
                            )
                            if video_stream:
                                video_width = video_stream.get("width", 1920)
                                video_height = video_stream.get("height", 1080)
                except Exception as e:
                    logger.warning(f"获取视频分辨率失败，使用默认值1920x1080: {e}")

        # 基于视频宽高的动态计算变量
        W = video_width
        H = video_height
        Margin = int(W * 0.05)
        Watermark_W = int(W * 0.30)
        Watermark_H = int(Watermark_W / 3)
        if preset_code == "bilibili_top_right":
            # B站水印：右上角 - 动态计算
            x = int(W - Watermark_W - Margin)
            y = int(Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "douyin_bottom_right":
            # 抖音水印：右下角 - 动态计算
            x = int(W - Watermark_W - Margin)
            y = int(H - Watermark_H - Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "xiaohongshu_bottom_right":
            # 小红书水印：右下角 - 动态计算
            x = int(W - Watermark_W - Margin)
            y = int(H - Watermark_H - Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "iqiyi_top_right":
            # 爱奇艺水印：右上角 - 动态计算
            x = int(W - Watermark_W - Margin)
            y = int(Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "youtube_bottom_left":
            # YouTube水印：左下角 - 动态计算
            x = int(Margin)
            y = int(H - Watermark_H - Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "tiktok_bottom_right":
            # TikTok水印：右下角 - 动态计算
            x = int(W - Watermark_W - Margin)
            y = int(H - Watermark_H - Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "weibo_bottom_right":
            # 微博水印：右下角 - 动态计算
            x = int(W - Watermark_W - Margin)
            y = int(H - Watermark_H - Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "tencent_video_top_right":
            # 腾讯视频水印：右上角 - 动态计算
            x = int(W - Watermark_W - Margin)
            y = int(Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "kuaishou_bottom_right":
            # 快手水印：右下角 - 动态计算
            x = int(W - Watermark_W - Margin)
            y = int(H - Watermark_H - Margin)
            w = int(Watermark_W)
            h = int(Watermark_H)
            self.region1_x.setValue(x)
            self.region1_y.setValue(y)
            self.region1_w.setValue(w)
            self.region1_h.setValue(h)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "xigua_top_right":
            # 西瓜视频水印：右上角，约100x50px
            self.region1_x.setValue(1820)  # 1920-100
            self.region1_y.setValue(10)
            self.region1_w.setValue(100)
            self.region1_h.setValue(50)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "toutiao_bottom_right":
            # 今日头条水印：右下角，约80x80px
            self.region1_x.setValue(1840)  # 1920-80
            self.region1_y.setValue(1000)  # 1080-80
            self.region1_w.setValue(80)
            self.region1_h.setValue(80)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "netease_music_bottom_left":
            # 网易云音乐水印：左下角，约100x40px
            self.region1_x.setValue(10)
            self.region1_y.setValue(1040)  # 1080-40
            self.region1_w.setValue(100)
            self.region1_h.setValue(40)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "youku_top_right":
            # 优酷水印：右上角，约120x50px
            self.region1_x.setValue(1800)  # 1920-120
            self.region1_y.setValue(10)
            self.region1_w.setValue(120)
            self.region1_h.setValue(50)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "sohu_bottom_right":
            # 搜狐视频水印：右下角，约80x80px
            self.region1_x.setValue(1840)  # 1920-80
            self.region1_y.setValue(1000)  # 1080-80
            self.region1_w.setValue(80)
            self.region1_h.setValue(80)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "letv_top_right":
            # 乐视视频水印：右上角，约100x50px
            self.region1_x.setValue(1820)  # 1920-100
            self.region1_y.setValue(10)
            self.region1_w.setValue(100)
            self.region1_h.setValue(50)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "migu_bottom_right":
            # 咪咕视频水印：右下角，约80x80px
            self.region1_x.setValue(1840)  # 1920-80
            self.region1_y.setValue(1000)  # 1080-80
            self.region1_w.setValue(80)
            self.region1_h.setValue(80)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "acfun_top_right":
            # AcFun水印：右上角，约60x60px
            self.region1_x.setValue(1860)  # 1920-60
            self.region1_y.setValue(10)
            self.region1_w.setValue(60)
            self.region1_h.setValue(60)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "bilibili_bottom_left":
            # 哔哩哔哩水印：左下角，约100x40px
            self.region1_x.setValue(10)
            self.region1_y.setValue(1040)  # 1080-40
            self.region1_w.setValue(100)
            self.region1_h.setValue(40)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "zhihu_bottom_right":
            # 知乎水印：右下角，约60x60px
            self.region1_x.setValue(1860)  # 1920-60
            self.region1_y.setValue(1020)  # 1080-60
            self.region1_w.setValue(60)
            self.region1_h.setValue(60)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        elif preset_code == "douban_top_right":
            # 豆瓣水印：右上角，约80x40px
            self.region1_x.setValue(1840)  # 1920-80
            self.region1_y.setValue(10)
            self.region1_w.setValue(80)
            self.region1_h.setValue(40)
            self.region_count_combo.setCurrentIndex(0)  # 1个区域

        self._update_crop_remove_watermark_conflict_hint()

    def preview_watermark_removal(self):
        """预览去水印效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "去水印预览")

    def open_time_period_selector(self):
        """打开时间段选择器"""
        # 检查功能是否启用
        if not self.time_period_enabled:
            self._warn("提示", "请先启用时间段去水印功能")
            return

        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        # 打开时间段选择对话框
        from ui.watermark_time_selector import WatermarkTimeSelector

        # 获取当前时间段设置
        dialog = WatermarkTimeSelector(
            video_path, self.time_period_start, self.time_period_end, self
        )
        if dialog.exec() == 1:  # 用户点击了确认
            enabled, start_time, end_time = dialog.get_selection()

            # 更新时间段配置
            self.time_period_enabled = enabled
            self.time_period_start = start_time
            self.time_period_end = end_time

            # 更新显示
            if enabled:
                self.time_period_display.setText(
                    f"{self._format_time(start_time)} - {self._format_time(end_time)}"
                )
            else:
                self.time_period_display.setText(
                    t("batch.main_window.auto.051", "未启用时间段")
                )

    def on_time_period_enable_changed(self, checked: bool):
        """时间段去水印启用状态改变"""
        self.time_period_enabled = checked
        self.time_period_select_btn.setEnabled(checked)
        self.time_period_display.setEnabled(checked)

        # 更新显示文本
        if checked:
            if self.time_period_start == 0 and self.time_period_end == 0:
                self.time_period_display.setText(
                    t("batch.main_window.auto.052", "未设置时间段")
                )
            else:
                self.time_period_display.setText(
                    f"{self._format_time(self.time_period_start)} - {self._format_time(self.time_period_end)}"
                )
        else:
            self.time_period_display.setText(
                t("batch.main_window.auto.052", "未设置时间段")
            )

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

    def open_region_selector(self, region_num: int):
        """打开区域选择器"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        # 打开区域选择对话框
        from ui.watermark_region_selector import WatermarkRegionSelector

        # 获取当前区域的坐标
        if region_num == 1:
            current_rect = (
                self.region1_x.value(),
                self.region1_y.value(),
                self.region1_w.value(),
                self.region1_h.value(),
            )
        elif region_num == 2:
            current_rect = (
                self.region2_x.value(),
                self.region2_y.value(),
                self.region2_w.value(),
                self.region2_h.value(),
            )
        else:  # region_num == 3
            current_rect = (
                self.region3_x.value(),
                self.region3_y.value(),
                self.region3_w.value(),
                self.region3_h.value(),
            )

        dialog = WatermarkRegionSelector(video_path, current_rect, self)
        if dialog.exec() == 1:  # 用户点击了确认
            x, y, w, h = dialog.get_region()

            # 更新对应区域的坐标
            if region_num == 1:
                self.region1_x.setValue(x)
                self.region1_y.setValue(y)
                self.region1_w.setValue(w)
                self.region1_h.setValue(h)
            elif region_num == 2:
                self.region2_x.setValue(x)
                self.region2_y.setValue(y)
                self.region2_w.setValue(w)
                self.region2_h.setValue(h)
            else:  # region_num == 3
                self.region3_x.setValue(x)
                self.region3_y.setValue(y)
                self.region3_w.setValue(w)
                self.region3_h.setValue(h)

    def _collect_watermark_config(self) -> Dict:
        """收集去水印配置"""
        # 0=FFmpeg, 1=AI, 2=API
        method = ["ffmpeg", "ai", "api"][self.watermark_method_combo.currentIndex()]

        return {
            "processing_method": method,
            "ffmpeg_crf": self.ffmpeg_crf.value(),
            "ffmpeg_preset": self.ffmpeg_preset.currentText(),
            "ai_strength": self.ai_strength.value() / 100.0,  # 转换为0-1范围
            "api_provider": self.api_provider.currentText(),
            "api_key": self.api_key.text(),
            "threads": 4,
            "skip_existing": True,
        }

    def _get_watermark_method_key(self, index: int) -> str:
        """获取方法键名"""
        # 下拉框的索引映射：
        # 0: "请选择" (提示，此时不应选择）
        # 1: "静态水印-FFMPEG-DELOGO" -> ffmpeg
        method_mapping = {
            0: None,  # 提示选项，不是真实方法
            1: "ffmpeg",  # FFMPEG delogo（唯一支持的方法）
        }
        return method_mapping.get(index, "ffmpeg")

    def _get_crop_mode(self) -> str:
        """获取当前选中的裁剪模式"""
        if self.crop_method_pixel.isChecked():
            return "pixel"
        elif self.crop_method_middle.isChecked():
            return "center"
        elif self.crop_method_percent.isChecked():
            return "percent"
        return "pixel"

    def _on_crop_enabled_changed(self, state):
        """裁剪总开关状态变化"""
        # ToggleSwitch的toggled信号发送bool值，而非Qt.CheckState
        enabled = (
            bool(state)
            if isinstance(state, bool)
            else (state == Qt.CheckState.Checked.value)
        )
        self.crop_methods_widget.setEnabled(enabled)
        self.crop_preview_btn.setEnabled(enabled)
        # 选取按钮仅在像素模式下启用
        self.crop_select_btn.setEnabled(enabled and self.crop_method_pixel.isChecked())
        self._update_crop_remove_watermark_conflict_hint()

    def _on_crop_method_changed(self):
        """裁剪方法切换"""
        is_pixel_mode = self.crop_method_pixel.isChecked()
        enabled = self.crop_check.isChecked()
        # 选取按钮仅在像素模式且总开关启用时可用
        self.crop_select_btn.setEnabled(enabled and is_pixel_mode)
        self._update_crop_remove_watermark_conflict_hint()

    def _on_crop_preview(self):
        """裁剪预览"""
        video_path = self._get_crop_preview_video_path()
        if not video_path:
            return

        if not self.crop_check.isChecked():
            self.crop_check.setChecked(True)

        # 直接生成并播放10秒预览视频
        self._show_crop_preview_video(video_path)

    def _on_crop_select(self):
        """打开裁切区域选取页"""
        video_path = self._get_crop_preview_video_path()
        if not video_path:
            return

        # 打开裁切区域选取对话框
        from ui.crop_region_selector import CropRegionSelectorDialog

        dialog = CropRegionSelectorDialog(
            video_path=video_path,
            initial_margins={
                "top": self.crop_pixel_top.value(),
                "bottom": self.crop_pixel_bottom.value(),
                "left": self.crop_pixel_left.value(),
                "right": self.crop_pixel_right.value(),
            },
            parent=self,
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取选取结果并更新UI
            margins = dialog.get_margins()
            self.crop_pixel_top.setValue(margins["top"])
            self.crop_pixel_bottom.setValue(margins["bottom"])
            self.crop_pixel_left.setValue(margins["left"])
            self.crop_pixel_right.setValue(margins["right"])

    def _get_crop_preview_video_path(self) -> str:
        """获取裁剪预览使用的视频路径"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return ""

        selected_rows = self.get_selected_rows()
        if selected_rows:
            return self.video_list[selected_rows[0]]["path"]
        return self.video_list[0]["path"]

    def _apply_crop_margins_from_preview(self, margins: dict):
        """预览窗口拖拽时同步裁剪参数"""
        if not self.crop_method_pixel.isChecked():
            self.crop_method_pixel.setChecked(True)

        self.crop_pixel_top.blockSignals(True)
        self.crop_pixel_bottom.blockSignals(True)
        self.crop_pixel_left.blockSignals(True)
        self.crop_pixel_right.blockSignals(True)

        self.crop_pixel_top.setValue(margins["top"])
        self.crop_pixel_bottom.setValue(margins["bottom"])
        self.crop_pixel_left.setValue(margins["left"])
        self.crop_pixel_right.setValue(margins["right"])

        self.crop_pixel_top.blockSignals(False)
        self.crop_pixel_bottom.blockSignals(False)
        self.crop_pixel_left.blockSignals(False)
        self.crop_pixel_right.blockSignals(False)
        self._update_crop_remove_watermark_conflict_hint()

    def _show_crop_preview_video(self, video_path: str):
        """生成10秒裁剪预览视频"""
        config = self.collect_config()
        self._show_preview_with_config(video_path, "裁剪预览", config)

    def _get_crop_mode_info_text(self) -> str:
        """获取裁剪模式说明文本"""
        mode = self._get_crop_mode()
        if mode == "pixel":
            return (
                f"当前模式：{enum_label(CROP_MODE_LABELS, 'pixel', self._language_manager.language)} | "
                f"上:{self.crop_pixel_top.value()} 下:{self.crop_pixel_bottom.value()} "
                f"左:{self.crop_pixel_left.value()} 右:{self.crop_pixel_right.value()}"
            )
        if mode == "center":
            return (
                f"当前模式：{enum_label(CROP_MODE_LABELS, 'center', self._language_manager.language)} | "
                f"比例:{self.crop_middle_ratio.currentText()}"
            )
        pos_code = normalize_crop_percent_position(self.crop_percent_mode.currentText())
        return (
            f"当前模式：{enum_label(CROP_MODE_LABELS, 'percent', self._language_manager.language)} | "
            f"比例:{self.crop_percent_value.value()}% "
            f"位置:{enum_label(CROP_PERCENT_POSITION_LABELS, pos_code, self._language_manager.language)}"
        )

    def _get_current_crop_margins(self, video_info: dict) -> dict:
        """根据当前裁剪模式计算初始边距"""
        mode = self._get_crop_mode()
        video_w = int(video_info.get("width", 0) or 0)
        video_h = int(video_info.get("height", 0) or 0)

        if mode == "pixel" or video_w <= 0 or video_h <= 0:
            return {
                "top": self.crop_pixel_top.value(),
                "bottom": self.crop_pixel_bottom.value(),
                "left": self.crop_pixel_left.value(),
                "right": self.crop_pixel_right.value(),
            }

        if mode == "center":
            return self._calculate_middle_margins(
                video_w, video_h, self.crop_middle_ratio.currentText()
            )

        return self._calculate_percent_margins(
            video_w,
            video_h,
            self.crop_percent_value.value(),
            normalize_crop_percent_position(self.crop_percent_mode.currentText()),
        )

    def _get_crop_conflict_reference_video_size(self) -> Optional[Tuple[int, int]]:
        """获取裁剪冲突检测所需的视频尺寸（优先当前选中视频）。"""
        if not self.video_list:
            return None

        target_index = 0
        selected_rows = self.get_selected_rows()
        if selected_rows:
            target_index = selected_rows[0]
        elif self.current_video_index is not None:
            target_index = min(self.current_video_index, len(self.video_list) - 1)

        entry = self.video_list[target_index]
        if not isinstance(entry, dict):
            return None

        width = int(entry.get("width", 0) or 0)
        height = int(entry.get("height", 0) or 0)
        if width <= 0 or height <= 0:
            return None
        return width, height

    @staticmethod
    def _rect_intersection_area(
        a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]
    ) -> int:
        """计算两个矩形交集面积。"""
        ax1, ay1, aw, ah = a
        bx1, by1, bw, bh = b
        ax2, ay2 = ax1 + aw, ay1 + ah
        bx2, by2 = bx1 + bw, by1 + bh
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0
        return (ix2 - ix1) * (iy2 - iy1)

    def _set_crop_remove_watermark_conflict_text(self, text: str) -> None:
        """统一更新去水印页冲突提示文本。"""
        label = getattr(self, "crop_rm_conflict_label", None)
        if label is None:
            return
        if text:
            label.setText(text)
            label.setVisible(True)
        else:
            label.setText("")
            label.setVisible(False)

    def _update_crop_remove_watermark_conflict_hint(self) -> None:
        """检查裁剪与去水印区域冲突，给出实时UI提示。"""
        if not hasattr(self, "remove_watermark_check") or not hasattr(
            self, "crop_check"
        ):
            return
        if (
            not self.remove_watermark_check.isChecked()
            or not self.crop_check.isChecked()
        ):
            self._set_crop_remove_watermark_conflict_text("")
            return

        method_index = (
            self.watermark_method_combo.currentIndex()
            if hasattr(self, "watermark_method_combo")
            else -1
        )
        if method_index not in [1, 2, 6, 8]:
            self._set_crop_remove_watermark_conflict_text("")
            return

        regions = self._get_watermark_regions()
        if not regions:
            self._set_crop_remove_watermark_conflict_text("")
            return

        mode = self._get_crop_mode()
        video_size = self._get_crop_conflict_reference_video_size()
        if not video_size:
            if mode == "pixel":
                self._set_crop_remove_watermark_conflict_text("")
            else:
                self._set_crop_remove_watermark_conflict_text(
                    "提示：当前为比例/百分比裁剪，未获取到视频分辨率，无法判断去水印区域是否会被裁剪覆盖。"
                )
            return

        video_w, video_h = video_size
        margins = self._get_current_crop_margins({"width": video_w, "height": video_h})
        keep_x = max(0, int(margins.get("left", 0) or 0))
        keep_y = max(0, int(margins.get("top", 0) or 0))
        keep_w = max(
            1,
            video_w
            - int(margins.get("left", 0) or 0)
            - int(margins.get("right", 0) or 0),
        )
        keep_h = max(
            1,
            video_h
            - int(margins.get("top", 0) or 0)
            - int(margins.get("bottom", 0) or 0),
        )
        keep_rect = (keep_x, keep_y, keep_w, keep_h)

        fully_covered = 0
        partially_covered = 0
        for x, y, w, h in regions:
            region_rect = (int(x), int(y), int(w), int(h))
            region_area = max(0, int(w)) * max(0, int(h))
            if region_area <= 0:
                continue
            overlap = self._rect_intersection_area(region_rect, keep_rect)
            if overlap <= 0:
                fully_covered += 1
            elif overlap < region_area:
                partially_covered += 1

        if fully_covered == 0 and partially_covered == 0:
            self._set_crop_remove_watermark_conflict_text("")
            return

        self._set_crop_remove_watermark_conflict_text(
            f"提示：当前裁剪会影响去水印区域（完全裁掉 {fully_covered} 个，部分覆盖 {partially_covered} 个）。"
            "处理可继续，但这些区域的去水印结果可能不可见。"
        )

    def _calculate_middle_margins(
        self, video_w: int, video_h: int, ratio_str: str
    ) -> dict:
        """计算中间比例裁剪边距"""
        try:
            if ":" in ratio_str:
                w_ratio, h_ratio = map(float, ratio_str.split(":"))
                aspect_ratio = w_ratio / h_ratio
            else:
                aspect_ratio = 1.0
        except:
            aspect_ratio = 1.0

        current_ratio = video_w / video_h if video_h > 0 else 1.0
        if current_ratio > aspect_ratio:
            crop_w = int(video_h * aspect_ratio)
            left = (video_w - crop_w) // 2
            right = video_w - crop_w - left
            return {"top": 0, "bottom": 0, "left": left, "right": right}

        crop_h = int(video_w / aspect_ratio) if aspect_ratio > 0 else video_h
        top = (video_h - crop_h) // 2
        bottom = video_h - crop_h - top
        return {"top": top, "bottom": bottom, "left": 0, "right": 0}

    def _calculate_percent_margins(
        self, video_w: int, video_h: int, percent_value: int, position: str
    ) -> dict:
        """计算百分比裁剪边距（与ffmpeg_builder一致）"""
        percent = min(99.99, max(1.0, float(percent_value)))
        position_code = normalize_crop_percent_position(position)

        if position_code == "all":
            crop_w = int(video_w * (100 - percent / 2) / 100)
            crop_h = int(video_h * (100 - percent / 2) / 100)
            left = (video_w - crop_w) // 2
            right = video_w - crop_w - left
            top = (video_h - crop_h) // 2
            bottom = video_h - crop_h - top
            return {"top": top, "bottom": bottom, "left": left, "right": right}
        if position_code == "top_left":
            crop_w = int(video_w * percent / 200)
            crop_h = int(video_h * percent / 200)
            return {
                "top": 0,
                "bottom": video_h - crop_h,
                "left": 0,
                "right": video_w - crop_w,
            }
        if position_code == "top_right":
            crop_w = int(video_w * percent / 200)
            crop_h = int(video_h * percent / 200)
            return {
                "top": 0,
                "bottom": video_h - crop_h,
                "left": video_w - crop_w,
                "right": 0,
            }
        if position_code == "bottom_left":
            crop_w = int(video_w * percent / 200)
            crop_h = int(video_h * percent / 200)
            return {
                "top": video_h - crop_h,
                "bottom": 0,
                "left": 0,
                "right": video_w - crop_w,
            }
        if position_code == "bottom_right":
            crop_w = int(video_w * percent / 200)
            crop_h = int(video_h * percent / 200)
            return {
                "top": video_h - crop_h,
                "bottom": 0,
                "left": video_w - crop_w,
                "right": 0,
            }
        if position_code == "top":
            crop_h = int(video_h * percent / 200)
            return {"top": 0, "bottom": video_h - crop_h, "left": 0, "right": 0}
        if position_code == "bottom":
            crop_h = int(video_h * percent / 200)
            return {"top": video_h - crop_h, "bottom": 0, "left": 0, "right": 0}
        if position_code == "left":
            crop_w = int(video_w * percent / 200)
            return {"top": 0, "bottom": 0, "left": 0, "right": video_w - crop_w}
        if position_code == "right":
            crop_w = int(video_w * percent / 200)
            return {"top": 0, "bottom": 0, "left": video_w - crop_w, "right": 0}
        if position_code == "vertical":
            crop_h = int(video_h * (100 - percent / 2) / 100)
            top = (video_h - crop_h) // 2
            bottom = video_h - crop_h - top
            return {"top": top, "bottom": bottom, "left": 0, "right": 0}
        if position_code == "horizontal":
            crop_w = int(video_w * (100 - percent / 2) / 100)
            left = (video_w - crop_w) // 2
            right = video_w - crop_w - left
            return {"top": 0, "bottom": 0, "left": left, "right": right}
        if position_code == "random":
            crop_w = int(video_w * percent / 200)
            crop_h = int(video_h * percent / 200)
            left = (video_w - crop_w) // 2
            top = (video_h - crop_h) // 2
            return {
                "top": top,
                "bottom": video_h - crop_h - top,
                "left": left,
                "right": video_w - crop_w - left,
            }

        return {"top": 0, "bottom": 0, "left": 0, "right": 0}

    def _get_watermark_regions(self) -> List[Tuple[int, int, int, int]]:
        """获取水印区域列表"""
        regions = []

        # 区域1
        if self.region1_w.value() > 0 and self.region1_h.value() > 0:
            regions.append(
                (
                    self.region1_x.value(),
                    self.region1_y.value(),
                    self.region1_w.value(),
                    self.region1_h.value(),
                )
            )

        # 区域2
        if (
            self.region_count_combo.currentIndex() >= 1
            and self.region_count_combo.currentIndex() != 3
        ):
            if self.region2_w.value() > 0 and self.region2_h.value() > 0:
                regions.append(
                    (
                        self.region2_x.value(),
                        self.region2_y.value(),
                        self.region2_w.value(),
                        self.region2_h.value(),
                    )
                )

        # 区域3
        if (
            self.region_count_combo.currentIndex() >= 2
            and self.region_count_combo.currentIndex() != 3
        ):
            if self.region3_w.value() > 0 and self.region3_h.value() > 0:
                regions.append(
                    (
                        self.region3_x.value(),
                        self.region3_y.value(),
                        self.region3_w.value(),
                        self.region3_h.value(),
                    )
                )

        return regions

    def on_bitrate_preset_changed(self, text: str):
        """码率预设改变（不再需要，已直接使用下拉框值）"""
        # 不再需要设置到另一个输入框，因为已经移除了bitrate_fixed_value
        pass

    def preview_grid_effect(self):
        """预览几宫格效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "宫格分屏预览")

    def preview_frame_adjust_effect(self):
        """预览画面调整效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "画面调整预览")

    def preview_rotate_effect(self):
        """预览旋转&翻转效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "旋转&翻转预览")

    def preview_fps_effect(self):
        """预览帧率设置效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "帧率设置预览")

    def preview_resolution_effect(self):
        """预览分辨率效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "分辨率调整预览")

    def preview_frame_extract_effect(self):
        """预览抽帧效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "抽帧效果预览")

    def preview_dynamic_zoom_effect(self):
        """预览动态缩放效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        # 获取首个视频
        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        self._show_preview(video_path, "动态缩放预览")

    def preview_speed_effect(self):
        """预览变速效果（仅预览基础变速，不含分段变速）"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        # 收集配置，但强制禁用分段变速（预览仅对基础倍数/最短时长/变调生效）
        config = self.collect_config()
        if "speed" in config and config["speed"].get("segment_enabled"):
            config["speed"]["segment_enabled"] = False
            print("预览模式：已禁用分段变速，仅预览基础倍数效果")

        self._show_preview_with_config(video_path, "变速预览", config)

    def preview_trim_effect(self):
        """预览去头尾/截取效果"""
        if not self.video_list:
            self._warn("提示", "请先添加视频文件")
            return

        selected_rows = self.get_selected_rows()
        if selected_rows:
            video_path = self.video_list[selected_rows[0]]["path"]
        else:
            video_path = self.video_list[0]["path"]

        config = self.collect_config()
        self._show_preview_with_config(video_path, "去头尾预览", config)

    def _show_preview(self, video_path: str, title: str):
        """显示预览窗口"""
        from processor.batch_params_processor import BatchParamsProcessor
        import tempfile

        # 收集当前配置
        config = self.collect_config()
        self._show_preview_with_config(video_path, title, config)

    def _show_preview_with_config(self, video_path: str, title: str, config: Dict):
        """使用指定配置显示预览（用于对话框预览）"""
        from processor.batch_params_processor import BatchParamsProcessor
        from PyQt6.QtCore import QThread, pyqtSignal
        import tempfile

        # 创建后台处理线程，避免卡死
        class PreviewThread(QThread):
            finished = pyqtSignal(bool, str)  # (success, preview_file or error_message)

            def __init__(self, processor, video_path, preview_file):
                super().__init__()
                self.processor = processor
                self.video_path = video_path
                self.preview_file = preview_file

            def run(self):
                try:
                    success = self.processor.generate_preview(
                        self.video_path, self.preview_file, variant=0
                    )
                    if success and os.path.exists(self.preview_file):
                        self.finished.emit(True, self.preview_file)
                    else:
                        self.finished.emit(False, "生成预览失败")
                except Exception as e:
                    self.finished.emit(False, str(e))

        # 关键修复：获取视频信息并传递给processor
        logger.info(f"[Preview] start title={title} video_path={video_path}")
        processor = BatchParamsProcessor(config)
        video_info = processor.get_video_info(video_path)
        if video_info:
            # 将视频信息添加到配置中，供智能判断使用
            config["_current_video_info"] = video_info
            width = video_info.get("width", 0)
            height = video_info.get("height", 0)
            aspect_ratio = width / height if height > 0 else 0
            duration = video_info.get("duration", 0)
            logger.info(
                f"[Preview] info width={width} height={height} "
                f"aspect={aspect_ratio:.2f} duration={duration:.1f}"
            )
            processor = BatchParamsProcessor(config)  # 重新创建processor
        else:
            logger.warning("[Preview] failed to get video info")

        # 生成预览文件(临时目录)
        preview_file = os.path.join(tempfile.gettempdir(), "kq_video_preview.mp4")
        logger.info(f"[Preview] output={preview_file}")

        # 显示进度对话框 - 关键修复：不设置父窗口，避免阻塞
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import Qt

        progress = QProgressDialog(
            t("batch.main_window.auto.053", "正在处理视频预览...\n\n请注意：仅提供10秒预览"),
            t("batch.main_window.auto.010", "取消"),
            0,
            0,
            None,
        )  # 父窗口设为None，移除取消按钮
        progress.setWindowTitle(title)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)  # 应用级模态
        progress.setWindowFlags(Qt.WindowType.Window)  # 独立窗口
        progress.setMinimumDuration(0)  # 立即显示
        progress.show()

        # 创建并启动线程
        thread = PreviewThread(processor, video_path, preview_file)

        def on_finished(success, result):
            progress.close()
            # 清理线程引用
            if hasattr(self, "_preview_thread") and self._preview_thread is not None:
                try:
                    self._preview_thread.deleteLater()
                except:
                    pass
                self._preview_thread = None

            # 简化逻辑：直接执行，不检查取消标志
            if success:
                logger.info(f"[Preview] success title={title} file={result}")
                self._play_preview_video(result, title)
            else:
                logger.error(f"[Preview] failed title={title} reason={result}")
                self._warn("错误", f"预览失败: {result}")

        thread.finished.connect(on_finished)
        thread.start()

        # 保存线程引用，防止被垃圾回收
        self._preview_thread = thread

    def _play_preview_video(self, video_file: str, title: str):
        """播放预览视频（统一播放器）"""
        import os

        if not os.path.exists(video_file):
            return

        from ui.video_preview_player import VideoPreviewPlayer

        player = VideoPreviewPlayer(
            video_path=video_file,
            duration=10,
            parent=self,
            description=f"• {title}<br>预览前10秒效果",
        )
        player.setWindowTitle(title)
        player.exec()

    def reset_all_parameters(self):
        """重置所有参数到默认值"""
        reply = self._confirm("确认重置", "确定要将所有参数重置为默认值吗？")

        if reply == QMessageBox.StandardButton.Yes:
            # 画面调整
            self.frame_adjust_check.setChecked(False)
            self.brightness_min.setValue(-0.05)
            self.brightness_max.setValue(0.05)
            self.sharpness_min.setValue(1.0)
            self.sharpness_max.setValue(1.2)
            self.contrast_min.setValue(0.95)
            self.contrast_max.setValue(1.05)
            self.denoise_min.setValue(3)
            self.denoise_max.setValue(5)
            self.saturation_min.setValue(0.95)
            self.saturation_max.setValue(1.05)

            # 几宫格分屏
            self.grid_split_check.setChecked(False)
            self.grid_count.setValue(3)
            self._set_combo_by_code(self.grid_direction, "auto", GRID_DIRECTION_LABELS)
            self.grid_blur_check.setChecked(False)

            # 分辨率
            self.resolution_check.setChecked(False)
            self._set_combo_by_code(
                self.resolution_preset, "custom", RESOLUTION_PRESET_LABELS
            )
            self.resolution_width.setValue(1920)
            self.resolution_height.setValue(1080)
            self.mode_original.setChecked(True)
            self.background_blur_check.setChecked(False)
            self.reflection_check.setChecked(False)
            self.reflection_opacity.setValue(0.5)

            # 旋转&翻转
            self.rotate_check.setChecked(False)
            self.flip_random_direction.setChecked(False)
            self.flip_random.setChecked(False)
            self.flip_random_angle.setValue(-1.0)
            self.flip_random_angle_max.setValue(1.0)
            self.flip_complete_check.setChecked(False)
            self.flip_black_edge_check.setChecked(False)

            # 帧率
            self.fps_check.setChecked(False)
            self.fps_min.setValue(24.0)
            self.fps_max.setValue(30.0)
            self.remove_duplicate_frames_check.setChecked(False)

            # 抽帧
            self.frame_extract_check.setChecked(False)
            self.frame_extract_min.setValue(25)
            self.frame_extract_max.setValue(30)
            self.audio_speed_check.setChecked(False)

            # 动态缩放
            self.dynamic_zoom_check.setChecked(False)
            self.dynamic_zoom_min.setValue(1.01)
            self.dynamic_zoom_max.setValue(1.10)

            # 码率（保持选中）
            self.bitrate_check.setChecked(True)
            self.bitrate_mode_dynamic.setChecked(True)
            self.bitrate_dynamic_value.setValue(23)
            self.bitrate_fixed_preset.setCurrentText("3000")  # 设置为默认3000
            self.bitrate_ratio_min.setValue(1.05)
            self.bitrate_ratio_max.setValue(1.95)

            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> 参数已重置为默认值")

    # ==================== 添加水印功能相关方法 ====================

    def _update_watermark_add_button_state(self):
        """根据当前水印数量更新新增按钮状态"""
        if not hasattr(self, "add_new_watermark_btn"):
            return
        watermark_enabled = bool(
            getattr(self, "add_watermark_check", None)
            and self.add_watermark_check.isChecked()
        )
        can_add = (
            len(self.watermark_widgets) < self.MAX_WATERMARKS and watermark_enabled
        )
        self.add_new_watermark_btn.setEnabled(can_add)
        if not watermark_enabled:
            self.add_new_watermark_btn.setToolTip(self._ts("请先启用加水印功能"))
        elif can_add:
            self.add_new_watermark_btn.setToolTip(
                self._ts(f"最多支持{self.MAX_WATERMARKS}个水印")
            )
        else:
            self.add_new_watermark_btn.setToolTip(
                self._ts(f"已达到上限（{self.MAX_WATERMARKS}个）")
            )

    def add_new_watermark_widget(self):
        """动态添加一个新的水印配置区域"""
        if hasattr(self, "watermark_tab_container"):
            self.watermark_tab_container.setUpdatesEnabled(False)
        current_count = len(self.watermark_widgets)
        if current_count >= self.MAX_WATERMARKS:
            self._warn("提示", f"最多只能添加{self.MAX_WATERMARKS}个水印")
            if hasattr(self, "process_log"):
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(
                    f"{timestamp} -> 已达到水印数量上限({self.MAX_WATERMARKS})"
                )
            self._update_watermark_add_button_state()
            if hasattr(self, "watermark_tab_container"):
                self.watermark_tab_container.setUpdatesEnabled(True)
            return
        new_index = current_count
        try:
            self.create_watermark_config_widget(new_index)
        finally:
            if hasattr(self, "watermark_tab_container"):
                self.watermark_tab_container.setUpdatesEnabled(True)
            QApplication.processEvents()
        self._update_watermark_add_button_state()

        if new_index + 1 == self.MAX_WATERMARKS:
            QMessageBox.information(
                self, self._ts("提示"), self._ts(f"已添加到第{self.MAX_WATERMARKS}个水印，达到上限")
            )

        # 记录日志
        if hasattr(self, "process_log"):
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.process_log.append(f"{timestamp} -> 已添加水印 #{new_index + 1}")

    def _remove_watermark_widget_silent(self, index: int):
        """静默删除指定索引的水印（不弹确认框）"""
        if len(self.watermark_widgets) <= 1:
            return
        if index < 0 or index >= len(self.watermark_widgets):
            return

        widget_dict = self.watermark_widgets[index]
        group_widget = widget_dict["group"]
        self.watermark_container_layout.removeWidget(group_widget)
        group_widget.deleteLater()

        self.watermark_widgets.pop(index)
        self.watermark_configs.pop(index)

        for i, item in enumerate(self.watermark_widgets):
            item["index"] = i
            title_label = item.get("title_label")
            if title_label:
                title_label.setText(self._ts(f"水印 #{i + 1}"))
            preview_btn = item.get("preview_btn")
            if preview_btn:
                preview_btn.setText(self._ts("预览效果"))
            delete_btn = item.get("delete_btn")
            if delete_btn:
                delete_btn.setVisible(i > 0)
            self._sync_watermark_config_from_widget(item)
        for i, cfg in enumerate(self.watermark_configs):
            cfg["id"] = i
        self._update_watermark_add_button_state()

    def delete_single_watermark(self, index: int):
        """删除指定索引的水印

        Args:
            index: 要删除的水印索引
        """
        # 最少保留一个水印
        if len(self.watermark_widgets) <= 1:
            self._warn("提示", "至少需要保留一个水印配置")
            return

        reply = self._confirm("确认删除", f"确定要删除水印 #{index + 1} 吗？")

        if reply == QMessageBox.StandardButton.Yes:
            # 找到对应的控件
            widget_dict = self.watermark_widgets[index]
            group_widget = widget_dict["group"]

            # 从布局中移除
            self.watermark_container_layout.removeWidget(group_widget)
            group_widget.deleteLater()

            # 从列表中删除
            self.watermark_widgets.pop(index)
            self.watermark_configs.pop(index)

            # 更新所有水印的索引和标题
            for i, widget_dict in enumerate(self.watermark_widgets):
                widget_dict["index"] = i
                title_label = widget_dict.get("title_label")
                if title_label:
                    title_label.setText(self._ts(f"水印 #{i + 1}"))
                preview_btn = widget_dict.get("preview_btn")
                if preview_btn:
                    preview_btn.setText(self._ts("预览效果"))
                delete_btn = widget_dict.get("delete_btn")
                if delete_btn:
                    delete_btn.setVisible(i > 0)
                self._sync_watermark_config_from_widget(widget_dict)

            # 同步配置ID
            for i, config in enumerate(self.watermark_configs):
                config["id"] = i

            self._update_watermark_add_button_state()

            # 记录日志
            if hasattr(self, "process_log"):
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.process_log.append(f"{timestamp} -> 已删除水印 #{index + 1}")

    def on_single_watermark_type_changed(self, index: int, type_index: int):
        """单个水印的类型改变

        Args:
            index: 水印索引
            type_index: 类型索引（0=图片，1=文字）
        """
        if index >= len(self.watermark_widgets):
            return

        widget_dict = self.watermark_widgets[index]
        is_image = type_index == 0

        # 切换显示
        widget_dict["image_widget"].setVisible(is_image)
        widget_dict["text_widget"].setVisible(not is_image)

        # 更新配置
        if index < len(self.watermark_configs):
            self.watermark_configs[index]["type"] = "image" if is_image else "text"
            self._sync_watermark_config_from_widget(widget_dict)
        self._refresh_live_validation_feedback()

    def toggle_single_file_mode(self, index: int):
        """切换单个水印的文件/文件夹模式

        Args:
            index: 水印索引
        """
        if index >= len(self.watermark_widgets):
            return

        widget_dict = self.watermark_widgets[index]
        current_mode = widget_dict.get("file_mode", "file")

        if current_mode == "file":
            widget_dict["file_mode"] = "folder"
            widget_dict["file_mode_btn"].setIcon(load_svg_icon("folder", 14, "#64748B"))
            widget_dict["file_mode_btn"].setText(self._ts("文件夹"))
            widget_dict["file_mode_btn"].setToolTip(
                self._ts("当前：文件夹模式（可随机选取，点击切换到文件模式）")
            )
            widget_dict["random_check"].setEnabled(True)
            widget_dict["file_path"].setPlaceholderText(self._ts("选择包含水印文件的文件夹..."))
        else:
            widget_dict["file_mode"] = "file"
            widget_dict["file_mode_btn"].setIcon(load_svg_icon("file", 14, "#64748B"))
            widget_dict["file_mode_btn"].setText(self._ts("文件"))
            widget_dict["file_mode_btn"].setToolTip(
                self._ts("当前：文件模式（点击切换到文件夹模式）")
            )
            widget_dict["random_check"].setEnabled(False)
            widget_dict["file_path"].setPlaceholderText(self._ts("选择水印文件..."))
            if widget_dict["random_check"].isChecked():
                widget_dict["random_check"].setChecked(False)

        # 更新配置
        if index < len(self.watermark_configs):
            self.watermark_configs[index]["file_mode"] = widget_dict["file_mode"]
            self._sync_watermark_config_from_widget(widget_dict)
        self._refresh_live_validation_feedback()

    def browse_single_watermark_source(self, index: int):
        """浏览单个水印的文件或文件夹

        Args:
            index: 水印索引
        """
        if index >= len(self.watermark_widgets):
            return

        widget_dict = self.watermark_widgets[index]
        file_mode = widget_dict.get("file_mode", "file")

        if file_mode == "file":
            # 选择文件
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t("batch.main_window.auto.054", "选择水印文件"),
                "",
                t(
                    "batch.main_window.auto.055",
                    "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;视频文件 (*.mp4 *.mov *.avi);;所有文件 (*.*)",
                ),
            )
            if file_path:
                widget_dict["file_path"].setText(file_path)
                if index < len(self.watermark_configs):
                    self.watermark_configs[index]["file_path"] = file_path
                    self._sync_watermark_config_from_widget(widget_dict)
        else:
            # 选择文件夹
            folder_path = QFileDialog.getExistingDirectory(
                self, t("batch.main_window.auto.056", "选择水印文件夹")
            )
            if folder_path:
                widget_dict["file_path"].setText(folder_path)
                if index < len(self.watermark_configs):
                    self.watermark_configs[index]["file_path"] = folder_path
                    self._sync_watermark_config_from_widget(widget_dict)

    def open_single_watermark_style(self, index: int):
        """打开单个水印的样式设置对话框（统一使用位置选择器）

        Args:
            index: 水印索引
        """
        # 现在统一调用位置选择器，它已经集成了样式设置
        self.open_single_position_selector(index)

    def open_single_position_selector(self, index: int):
        """打开单个水印的位置选择器

        Args:
            index: 水印索引
        """
        if index >= len(self.watermark_configs):
            return

        try:
            from ui.watermark_position_selector import WatermarkPositionSelector

            # 获取当前水印配置
            config = self.watermark_configs[index]

            # 获取当前选中的视频路径（如果有）
            video_path = None
            if self.video_list and len(self.video_list) > 0:
                # 尝试获取当前选中的视频
                selected_rows = self.video_table.selectedIndexes()
                if selected_rows:
                    row = selected_rows[0].row()
                    video_path = self.video_list[row]["path"]
                else:
                    # 默认使用第一个视频
                    video_path = self.video_list[0]["path"]

            dialog = WatermarkPositionSelector(
                watermark_config=config, video_path=video_path, parent=self
            )

            if dialog.exec():
                x, y, w, h = dialog.get_position()

                # 获取样式配置
                style_config = dialog.get_style_config()

                # 保存位置和尺寸
                if index < len(self.watermark_widgets):
                    widget_dict = self.watermark_widgets[index]
                    widget_dict["offset_x"].setValue(x)
                    widget_dict["offset_y"].setValue(y)
                    # 位置下拉框区分图片/文字
                    if config.get("type") == "text":
                        self._set_combo_by_code(
                            widget_dict["text_position"], "custom", TEXT_POSITION_LABELS
                        )
                    else:
                        self._set_combo_by_code(
                            widget_dict["position_combo"], "custom", TEXT_POSITION_LABELS
                        )

                    # 保存位置和尺寸到widget_dict（用于预览）
                    widget_dict["position"] = (x, y)
                    widget_dict["size"] = (w, h)

                    # 保存样式配置
                    widget_dict["style_config"] = style_config
                    # 同步文字内容到主窗口文本框
                    if config.get("type") == "text":
                        text_content = style_config.get("content", "")
                        if text_content:
                            widget_dict["text_content"].setText(text_content)
                    elif config.get("type") == "image" and "opacity" in widget_dict:
                        widget_dict["opacity"].setValue(
                            float(self.watermark_configs[index].get("opacity", 1.0))
                        )
                    self._sync_watermark_config_from_widget(widget_dict)

                # 更新配置
                self.watermark_configs[index]["custom_position"] = (x, y)
                self.watermark_configs[index]["offset_x"] = x
                self.watermark_configs[index]["offset_y"] = y
                self.watermark_configs[index]["custom_width"] = w
                self.watermark_configs[index]["custom_height"] = h
                self.watermark_configs[index]["style_config"] = style_config
                if config.get("type") == "text" and style_config.get("content"):
                    self.watermark_configs[index]["text_content"] = style_config[
                        "content"
                    ]

                # 如果是文字水印，保存样式
                if config.get("type") == "text":
                    text_style = dialog.get_text_style()
                    self.watermark_configs[index].update(text_style)

                self._sync_watermark_config_from_widget(self.watermark_widgets[index])

                QMessageBox.information(
                    self,
                    t("batch.main_window.auto.006", "提示"),
                    t(
                        "batch.main_window.auto.067",
                        "水印 #{index} 已设置\n位置: ({x}, {y})\n尺寸: {w}×{h}",
                        index=index + 1,
                        x=x,
                        y=y,
                        w=w,
                        h=h,
                    ),
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                t("batch.main_window.auto.036", "错误"),
                t(
                    "batch.main_window.auto.068",
                    "打开位置选择器失败:\n{error}\n\n请确保已选择视频文件",
                    error=str(e),
                ),
            )

    def preview_cumulative_watermark(self, index: int):
        """累积预览水印效果（叠加前N个水印）

        Args:
            index: 预览到第几个水印（包含0到index的所有水印）
        """
        # 检查是否有视频
        if self.video_table.rowCount() == 0:
            self._warn("警告", "请先添加视频文件！")
            return

        # 获取选中的视频，如果没有选中，默认使用第一个
        selected_rows = self.video_table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
        else:
            row = 0
            # 自动选中第一行
            self.video_table.selectRow(0)

        # 获取视频路径
        video_item = self.video_table.item(row, self.COL_NAME)
        if not video_item:
            QMessageBox.warning(
                self,
                t("batch.main_window.auto.057", "警告"),
                t("batch.main_window.auto.058", "无法获取视频信息！\n请确保已正确添加视频。"),
            )
            return
        video_path = video_item.data(Qt.ItemDataRole.UserRole)
        if not video_path:
            # 尝试从 video_list 获取
            if row < len(self.video_list):
                video_path = self.video_list[row]["path"]
            else:
                QMessageBox.warning(
                    self,
                    t("batch.main_window.auto.057", "警告"),
                    t("batch.main_window.auto.059", "无法获取视频路径！\n请重新添加视频文件。"),
                )
                return
        if not os.path.exists(video_path):
            QMessageBox.warning(
                self,
                t("batch.main_window.auto.057", "警告"),
                t(
                    "batch.main_window.auto.069",
                    "视频文件不存在！\n\n路径：{video_path}\n\n请检查文件是否已被移动或删除。",
                    video_path=video_path,
                ),
            )
            return

        # 收集前 index+1 个水印配置
        watermark_configs = self.get_all_watermark_configs(limit=index + 1)

        if not watermark_configs:
            self._warn("警告", "没有有效的水印配置！")
            return

        # 生成预览
        try:
            from processor.batch_params_processor import BatchParamsProcessor

            # 创建临时预览参数
            preview_params = {
                "add_watermark": {"enabled": True, "watermarks": watermark_configs}
            }

            # 显示预览窗口
            self.show_preview_window(video_path, preview_params, index + 1)

        except Exception as e:
            self._error("错误", f"预览失败：{str(e)}")
            import traceback

            traceback.print_exc()

    def get_watermark_config_from_widget(self, index: int) -> dict:
        """从UI控件获取水印配置

        Args:
            index: 水印索引

        Returns:
            水印配置字典
        """
        if index >= len(self.watermark_widgets):
            return None

        widget_dict = self.watermark_widgets[index]
        config = self._sync_watermark_config_from_widget(widget_dict)

        # 校验基本有效性
        if config["type"] == "image" and not config["file_path"]:
            return None
        if config["type"] == "text" and not config["text_content"].strip():
            return None

        return copy.deepcopy(config)

    def get_all_watermark_configs(self, limit: Optional[int] = None) -> List[dict]:
        """获取所有有效的水印配置"""
        configs, _ = self._collect_watermark_configs(limit=limit, collect_errors=False)
        return configs

    def _scan_watermark_folder(self, folder_path: str) -> List[str]:
        """扫描水印文件夹，返回所有可用文件列表"""
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            return []

        allowed_exts = self._SUPPORTED_IMAGE_EXTS | self._SUPPORTED_VIDEO_EXTS
        candidates = [
            str(p.resolve())
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in allowed_exts
        ]
        return sorted(candidates)

    def _collect_watermark_configs(
        self, limit: Optional[int] = None, collect_errors: bool = False
    ) -> Tuple[List[dict], List[str]]:
        """收集水印配置，同时返回错误信息

        Args:
            limit: 限制收集数量（用于预览）
            collect_errors: 是否收集错误信息
        """
        configs: List[dict] = []
        errors: List[str] = []
        allowed_exts = self._SUPPORTED_IMAGE_EXTS | self._SUPPORTED_VIDEO_EXTS

        for idx, widget_dict in enumerate(self.watermark_widgets):
            if limit is not None and idx >= limit:
                break

            config = self._sync_watermark_config_from_widget(widget_dict)
            is_valid = True
            message = ""

            if config["type"] == "image":
                file_path = config["file_path"]
                if not file_path:
                    is_valid = False
                    message = f"水印 #{idx + 1} 未选择文件"
                else:
                    normalized_path = os.path.abspath(file_path)
                    if config["file_mode"] == "file":
                        if not os.path.exists(normalized_path):
                            is_valid = False
                            message = f"水印 #{idx + 1} 文件不存在：{normalized_path}"
                        elif Path(normalized_path).suffix.lower() not in allowed_exts:
                            is_valid = False
                            message = f"水印 #{idx + 1} 文件格式不受支持"
                        else:
                            config["file_path"] = normalized_path
                            config["file_candidates"] = [normalized_path]
                    else:
                        candidates = self._scan_watermark_folder(normalized_path)
                        if not candidates:
                            is_valid = False
                            message = f"水印 #{idx + 1} 文件夹中没有可用的水印文件"
                        else:
                            config["file_path"] = normalized_path
                            config["file_candidates"] = candidates
            else:
                # 文字水印校验
                if not config["text_content"].strip():
                    is_valid = False
                    message = f"水印 #{idx + 1} 文字内容为空"

            if not is_valid:
                if collect_errors and message:
                    errors.append(message)
                continue

            configs.append(copy.deepcopy(config))
            self.watermark_configs[idx] = config

        return configs, errors

    def show_preview_window(self, video_path: str, params: dict, watermark_count: int):
        """显示视频预览播放窗口（10秒预览）

        Args:
            video_path: 视频路径
            params: 处理参数
            watermark_count: 水印数量
        """
        try:
            from ui.video_preview_player import VideoPreviewPlayer

            watermark_section = params.get("add_watermark", {})
            watermark_configs = (
                watermark_section.get("watermarks", []) if watermark_section else []
            )

            # 生成描述
            desc_parts = ["• 批量处理预览"]
            if watermark_configs:
                desc_parts.append(f"包含 {len(watermark_configs)} 个处理效果")

            # 创建并显示视频播放器
            player = VideoPreviewPlayer(
                video_path=video_path,
                watermark_configs=watermark_configs,
                duration=10,  # 10秒预览
                parent=self,
                description="<br>".join(desc_parts),
            )
            player.exec()

        except Exception as e:
            QMessageBox.critical(
                self,
                t("batch.main_window.auto.060", "预览错误"),
                t(
                    "batch.main_window.auto.070",
                    "生成预览失败：{error}\n\n请确保视频文件有效且可以正常播放",
                    error=str(e),
                ),
            )
            import traceback

            traceback.print_exc()

    def apply_watermark_to_frame_old(self, frame, config: dict):
        """在帧上应用水印

        Args:
            frame: OpenCV图像帧
            config: 水印配置

        Returns:
            应用水印后的帧
        """
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont

        frame_h, frame_w = frame.shape[:2]

        if config["type"] == "image":
            # 图片水印
            watermark_path = config.get("file_path", "")
            if not watermark_path or not os.path.exists(watermark_path):
                return frame

            # 加载水印图片
            watermark = cv2.imread(watermark_path, cv2.IMREAD_UNCHANGED)
            if watermark is None:
                return frame

            # 获取位置和尺寸
            if "size" in config and config["size"]:
                wm_w, wm_h = config["size"]
                watermark = cv2.resize(watermark, (wm_w, wm_h))
            else:
                wm_h, wm_w = watermark.shape[:2]

            # 计算位置
            position = config.get("position", "top_right")
            if isinstance(position, tuple) and len(position) >= 2:
                x, y = position[0], position[1]
            else:
                # 预设位置
                margin = 20
                if position == "top_left":
                    x, y = margin, margin
                elif position == "top_right":
                    x, y = frame_w - wm_w - margin, margin
                elif position == "bottom_left":
                    x, y = margin, frame_h - wm_h - margin
                elif position == "bottom_right":
                    x, y = frame_w - wm_w - margin, frame_h - wm_h - margin
                elif position == "center":
                    x, y = (frame_w - wm_w) // 2, (frame_h - wm_h) // 2
                else:
                    x, y = frame_w - wm_w - margin, margin

            # 确保位置有效
            x = max(0, min(x, frame_w - wm_w))
            y = max(0, min(y, frame_h - wm_h))

            # 叠加水印
            if watermark.shape[2] == 4:  # 有Alpha通道
                # 分离Alpha通道
                alpha = watermark[:, :, 3] / 255.0
                for c in range(3):
                    frame[y : y + wm_h, x : x + wm_w, c] = (
                        frame[y : y + wm_h, x : x + wm_w, c] * (1 - alpha)
                        + watermark[:, :, c] * alpha
                    )
            else:
                # 没有Alpha通道，直接覆盖
                frame[y : y + wm_h, x : x + wm_w] = watermark[:, :, :3]

        elif config["type"] == "text":
            # 文字水印
            text = config.get("text", "水印文字")

            # 转换为PIL图像
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_img)

            # 字体设置
            font_size = config.get("font_size", 36)
            try:
                font = ImageFont.truetype("msyh.ttc", font_size)  # 微软雅黑
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()

            # 获取文字尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]

            # 计算位置
            position = config.get("position", "top_right")
            if isinstance(position, tuple) and len(position) >= 2:
                x, y = position[0], position[1]
            else:
                margin = 20
                if position == "top_left":
                    x, y = margin, margin
                elif position == "top_right":
                    x, y = frame_w - text_w - margin, margin
                elif position == "bottom_left":
                    x, y = margin, frame_h - text_h - margin
                elif position == "bottom_right":
                    x, y = frame_w - text_w - margin, frame_h - text_h - margin
                elif position == "center":
                    x, y = (frame_w - text_w) // 2, (frame_h - text_h) // 2
                else:
                    x, y = frame_w - text_w - margin, margin

            # 绘制文字（白色，半透明）
            color = config.get("color", (255, 255, 255, 200))
            if len(color) == 3:
                color = (*color, 200)

            draw.text((x, y), text, font=font, fill=color)

            # 转回OpenCV格式
            frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

        return frame

    def on_add_watermark_check_changed(self, checked: bool):
        """加水印复选框状态改变"""
        # 控制所有水印配置区域的启用状态
        for widget_dict in self.watermark_widgets:
            if "group" in widget_dict:
                widget_dict["group"].setEnabled(checked)
        self._update_watermark_add_button_state()

        # 记录日志
        if hasattr(self, "process_log"):
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            status = "启用" if checked else "禁用"
            self.process_log.append(f"{timestamp} -> {status}加水印功能")


# 使用拆分后的线程实现
from ui.batch_video.video_process_thread import (
    VideoProcessThread as _VideoProcessThread,
)

VideoProcessThread = _VideoProcessThread


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from utils.icon_utils import build_app_logo_icon

    # 确保项目根目录在Python路径中
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 创建应用程序
    app = QApplication(sys.argv)
    app.setWindowIcon(build_app_logo_icon())

    # PyQt6中高DPI默认启用，不需要手动设置
    # Qt6已经默认支持高DPI，以下代码仅用于兼容性

    # 设置默认字体（确保中文显示正常）
    from PyQt6.QtGui import QFont

    default_font = QFont("Microsoft YaHei", 9)
    default_font.setStyleHint(QFont.StyleHint.SansSerif)
    default_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    app.setFont(default_font)

    print("[✓] UI配置完成，字体: 微软雅黑")

    # 创建并显示主窗口
    window = BatchVideoProcessorWindow()
    window.show()

    sys.exit(app.exec())
