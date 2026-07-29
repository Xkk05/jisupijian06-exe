"""
LUT滤镜对话框
集成现代化UI组件
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QCheckBox, QScrollArea, QWidget,
    QGroupBox, QMessageBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QObject, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QImage, QPixmap
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ui.components import ModernButton, ModernCard, ToggleSwitch, ModernInput, create_section_header
from ui.theme import Theme
from ui.i18n import t
from utils.lut_filters import (
    display_to_id,
    get_lut_dir,
    list_filters,
    resolve_ffmpeg_lut_path,
    resolve_lut_path,
)
from utils.unified_logger import logger


class _LUTPreviewWorker(QObject):
    finished = pyqtSignal(int, str, bool, str)

    def __init__(self, cmd, output_file, generation, parent=None):
        super().__init__(parent)
        self._cmd = cmd
        self._output_file = output_file
        self._generation = generation

    def run(self):
        creation_flags = 0
        if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            creation_flags = subprocess.CREATE_NO_WINDOW
        success = False
        error_message = ""
        try:
            result = subprocess.run(
                self._cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
            )
            success = (
                result.returncode == 0
                and os.path.exists(self._output_file)
                and os.path.getsize(self._output_file) > 0
            )
            if not success:
                error_message = (result.stderr or "").strip() or (
                    f"FFmpeg返回码 {result.returncode}，未生成有效图片"
                )
        except Exception as exc:
            error_message = str(exc)

        if not success:
            logger.error(
                "[LUTPreview] failed command=%s error=%s",
                subprocess.list2cmdline(self._cmd),
                error_message[-4000:],
            )
        self.finished.emit(
            self._generation, self._output_file, success, error_message
        )


class LUTFilterDialog(QDialog):
    """LUT滤镜对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_checkboxes = []
        self._sample_pixmap = None
        self._original_pixmap = None
        self._sample_image_path = None
        self._preview_inflight = False
        self._preview_pending = False
        self._preview_generation = 0
        self._preview_thread = None
        self._preview_worker = None
        self._cube_cache = {}
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self.update_preview_from_selection)
        self.setWindowTitle(t("lut_filter_dialog.title", "LUT滤镜设置"))
        self.setMinimumSize(700, 500)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 头部开关
        header_layout = QHBoxLayout()
        header_label = QLabel(t("lut_filter_dialog.apply", "应用LUT滤镜"))
        header_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {Theme.TextPrimary};")
        
        self.apply_switch = ToggleSwitch()
        self.apply_switch.toggled.connect(self.on_apply_check_changed)
        
        header_layout.addWidget(header_label)
        header_layout.addWidget(self.apply_switch)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        tip_label = QLabel(
            t(
                "lut_filter_dialog.tip",
                "说明: 程序在处理视频时，将于勾选的滤镜中顺序或随机选取应用。",
            )
        )
        tip_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(tip_label)
        
        # 内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)
        
        # 左侧：滤镜列表
        list_card = ModernCard(t("lut_filter_dialog.filter_list", "滤镜列表"))
        list_layout = QVBoxLayout() # Card internal layout is VBox by default, but we want custom control
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: #F8FAFC;
                border: none;
            }
            QScrollArea QWidget {
                background: #F8FAFC;
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
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background-color: #F8FAFC;")
        scroll_grid = QGridLayout(scroll_widget)
        scroll_grid.setHorizontalSpacing(10)
        scroll_grid.setVerticalSpacing(8)
        scroll_grid.setContentsMargins(5, 5, 5, 5)
        
        # LUT滤镜列表（中文显示）
        filters = list_filters()

        row = 0
        col = 0
        for item in filters:
            checkbox = QCheckBox(
                t(f"lut_filter_dialog.filter.{item['id']}", item["name"])
            )
            checkbox.setProperty("filter_id", item["id"])
            checkbox.setChecked(True)
            checkbox.setEnabled(False)
            checkbox.stateChanged.connect(self.schedule_preview_update)
            self.filter_checkboxes.append(checkbox)
            scroll_grid.addWidget(checkbox, row, col)
            
            col += 1
            if col >= 3:  # 每行3个
                col = 0
                row += 1
        
        scroll_area.setWidget(scroll_widget)
        list_card.addWidget(scroll_area)
        
        # 列表操作按钮
        op_btn_layout = QHBoxLayout()
        op_btn_layout.setSpacing(8)
        
        self.select_all_btn = ModernButton(t("lut_filter_dialog.btn.select_all", "全选"), ModernButton.Style.Secondary)
        self.select_all_btn.setFixedHeight(30)
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        
        self.invert_btn = ModernButton(t("lut_filter_dialog.btn.invert", "反选"), ModernButton.Style.Secondary)
        self.invert_btn.setFixedHeight(30)
        self.invert_btn.clicked.connect(self.invert_selection)
        self.invert_btn.setEnabled(False)
        
        self.random_apply_check = QCheckBox(t("lut_filter_dialog.option.random_apply", "随机选取"))
        self.random_apply_check.setEnabled(False)
        self.random_apply_check.stateChanged.connect(self.schedule_preview_update)
        
        op_btn_layout.addWidget(self.select_all_btn)
        op_btn_layout.addWidget(self.invert_btn)
        op_btn_layout.addStretch()
        op_btn_layout.addWidget(self.random_apply_check)
        
        list_card.addLayout(op_btn_layout)
        content_layout.addWidget(list_card, stretch=2)
        
        # 右侧：样例预览
        preview_card = ModernCard(t("lut_filter_dialog.preview.title", "效果预览"))
        
        self.sample_label = QLabel()
        self.sample_label.setMinimumSize(240, 180)
        self.sample_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.sample_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sample_label.setStyleSheet(f"""
            QLabel {{
                background-color: {Theme.Background};
                border: 1px dashed {Theme.Border};
                border-radius: 8px;
            }}
        """)
        
        # 尝试加载样例
        self.load_sample_image()
        
        preview_card.addWidget(self.sample_label)
        preview_card.layout.addStretch()
        
        content_layout.addWidget(preview_card, stretch=1)
        layout.addLayout(content_layout)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.reset_btn = ModernButton(t("common.btn.reset", "重置"), ModernButton.Style.Secondary)
        self.reset_btn.clicked.connect(self.reset)
        self.reset_btn.setEnabled(False)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        ok_btn = ModernButton(t("common.btn.ok", "确定"), ModernButton.Style.Primary)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = ModernButton(t("common.btn.cancel", "取消"), ModernButton.Style.Secondary)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def load_sample_image(self):
        """加载样例图片"""
        assets_dir = os.path.dirname(get_lut_dir())
        translated_name = t("lut_filter_dialog.preview.sample_image", "样例.jpg")
        sample_candidates = [
            os.path.join(assets_dir, translated_name),
            os.path.join(assets_dir, "样例.jpg"),
        ]
        sample_image_path = next(
            (path for path in sample_candidates if os.path.exists(path)),
            sample_candidates[0],
        )
        if os.path.exists(sample_image_path):
            pixmap = QPixmap(sample_image_path)
            self._sample_pixmap = pixmap
            self._original_pixmap = pixmap
            self._sample_image_path = sample_image_path
            self.update_sample_preview()
        else:
            self._sample_pixmap = None
            self._original_pixmap = None
            self._sample_image_path = None
            self.sample_label.setText(t("lut_filter_dialog.preview.none", "暂无预览图片"))

    def update_sample_preview(self):
        """根据卡片尺寸更新预览图"""
        if not self._sample_pixmap:
            return
        target_size = self.sample_label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        scaled_pixmap = self._sample_pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.sample_label.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_sample_preview()
    
    def on_apply_check_changed(self, checked: bool):
        """应用LUT滤镜开关状态改变"""
        self.random_apply_check.setEnabled(checked)
        # 同时启用/禁用所有滤镜复选框
        for checkbox in self.filter_checkboxes:
            checkbox.setEnabled(checked)
        # 启用/禁用操作按钮
        self.select_all_btn.setEnabled(checked)
        self.invert_btn.setEnabled(checked)
        self.reset_btn.setEnabled(checked)
        self.schedule_preview_update()
    
    def select_all(self):
        """全选"""
        for checkbox in self.filter_checkboxes:
            checkbox.setChecked(True)
        self.schedule_preview_update()
    
    def invert_selection(self):
        """反选"""
        for checkbox in self.filter_checkboxes:
            checkbox.setChecked(not checkbox.isChecked())
        self.schedule_preview_update()
    
    def reset(self):
        """重置为默认（不选中）"""
        self.apply_switch.setChecked(False)
        self.random_apply_check.setChecked(False)
        for checkbox in self.filter_checkboxes:
            checkbox.setChecked(True)
        self._sample_pixmap = self._original_pixmap
        self.update_sample_preview()
    
    def get_config(self):
        """获取配置"""
        selected_filters = []
        for checkbox in self.filter_checkboxes:
            if checkbox.isChecked():
                filter_id = checkbox.property("filter_id")
                if filter_id:
                    selected_filters.append(filter_id)
        
        return {
            'apply': self.apply_switch.isChecked(),
            'random_apply': self.random_apply_check.isChecked(),
            'filters': selected_filters
        }
    
    def set_config(self, config: dict):
        """设置配置（恢复之前的设置）"""
        if not config:
            return
        
        # 恢复应用状态
        self.apply_switch.setChecked(config.get('apply', False))
        self.random_apply_check.setChecked(config.get('random_apply', False))
        
        # 恢复滤镜选择
        selected_filters = config.get('filters', [])
        normalized_ids = []
        for item in selected_filters:
            if item in (cb.property("filter_id") for cb in self.filter_checkboxes):
                normalized_ids.append(item)
                continue
            mapped_id = display_to_id(item)
            if mapped_id:
                normalized_ids.append(mapped_id)
        if selected_filters:
            # 先全部取消选中
            for checkbox in self.filter_checkboxes:
                checkbox.setChecked(False)
            # 然后选中保存的滤镜
            for checkbox in self.filter_checkboxes:
                if checkbox.property("filter_id") in normalized_ids:
                    checkbox.setChecked(True)
        self.schedule_preview_update()

    def schedule_preview_update(self):
        if self._preview_timer.isActive():
            self._preview_timer.stop()
        self._preview_timer.start(150)

    def _find_ffmpeg(self) -> str:
        executable_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        roots = []
        if hasattr(sys, "_MEIPASS"):
            roots.append(Path(sys._MEIPASS))
        roots.append(Path(__file__).resolve().parents[1])
        if getattr(sys, "frozen", False):
            executable_root = Path(sys.executable).resolve().parent
            roots.extend((executable_root / "_internal", executable_root))

        relative_candidates = (
            ("ffmpeg", executable_name),
            ("processor", executable_name),
            (executable_name,),
        )
        seen = set()
        for root in roots:
            for parts in relative_candidates:
                candidate = root.joinpath(*parts)
                key = os.path.normcase(os.path.abspath(str(candidate)))
                if key in seen:
                    continue
                seen.add(key)
                if candidate.is_file():
                    return str(candidate)
        return "ffmpeg"

    def _escape_filter_path(self, path: str) -> str:
        return path.replace("\\", "/").replace(":", "\\:")

    def _selected_filter_ids(self):
        selected_ids = []
        for checkbox in self.filter_checkboxes:
            if checkbox.isChecked():
                filter_id = checkbox.property("filter_id")
                if filter_id:
                    selected_ids.append(filter_id)
        if self.random_apply_check.isChecked() and selected_ids:
            return [selected_ids[0]]
        return selected_ids

    def _load_cube_table(self, lut_path: str):
        cached = self._cube_cache.get(lut_path)
        if cached:
            return cached

        size = None
        values = []
        with open(lut_path, "r", encoding="utf-8", errors="ignore") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                upper = line.upper()
                if upper.startswith("LUT_3D_SIZE"):
                    parts = line.split()
                    if len(parts) >= 2:
                        size = int(parts[1])
                    continue
                if upper.startswith(
                    ("TITLE", "DOMAIN_MIN", "DOMAIN_MAX", "LUT_1D_SIZE")
                ):
                    continue
                parts = line.split()
                if len(parts) < 3:
                    continue
                try:
                    values.append(
                        tuple(
                            max(0, min(255, int(float(part) * 255)))
                            for part in parts[:3]
                        )
                    )
                except ValueError:
                    continue

        if not size or len(values) < size * size * size:
            return None

        table = (size, values[: size * size * size])
        self._cube_cache[lut_path] = table
        return table

    def _apply_cube_table_to_image(self, image: QImage, cube_table):
        size, values = cube_table
        max_index = size - 1
        for y in range(image.height()):
            for x in range(image.width()):
                color = image.pixelColor(x, y)
                r_idx = round(color.red() * max_index / 255)
                g_idx = round(color.green() * max_index / 255)
                b_idx = round(color.blue() * max_index / 255)
                lut_index = r_idx + g_idx * size + b_idx * size * size
                red, green, blue = values[lut_index]
                image.setPixelColor(x, y, QColor(red, green, blue, color.alpha()))

    def _apply_qimage_lut_preview(self, selected_ids) -> bool:
        if not self._original_pixmap or not selected_ids:
            return False
        target_size = self.sample_label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            target_size = self.sample_label.minimumSize()

        preview_pixmap = self._original_pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image = preview_pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)

        applied = False
        for filter_id in selected_ids:
            lut_path = resolve_lut_path(filter_id)
            if not lut_path or not os.path.exists(lut_path):
                continue
            try:
                cube_table = self._load_cube_table(lut_path)
                if not cube_table:
                    continue
                self._apply_cube_table_to_image(image, cube_table)
                applied = True
            except Exception as exc:
                logger.warning(
                    "[LUTPreview] qimage fallback failed file=%s error=%s",
                    lut_path,
                    exc,
                )

        if not applied:
            return False

        self._sample_pixmap = QPixmap.fromImage(image)
        self.update_sample_preview()
        return True

    def update_preview_from_selection(self):
        self._preview_generation += 1
        generation = self._preview_generation
        if not self._sample_pixmap:
            return
        if not self.apply_switch.isChecked():
            self._sample_pixmap = self._original_pixmap
            self.update_sample_preview()
            return

        selected_ids = self._selected_filter_ids()

        if not selected_ids:
            self._sample_pixmap = self._original_pixmap
            self.update_sample_preview()
            return

        lut_paths = []
        try:
            for filter_id in selected_ids:
                lut_path = resolve_ffmpeg_lut_path(filter_id)
                if lut_path and os.path.exists(lut_path):
                    lut_paths.append(lut_path)
        except (OSError, RuntimeError) as exc:
            logger.error("[LUTPreview] prepare FFmpeg path failed: %s", exc)
            if not self._apply_qimage_lut_preview(selected_ids):
                self.sample_label.setText(
                    t("lut_filter_dialog.error.preview_failed", "预览生成失败")
                )
            return

        if not lut_paths:
            self.sample_label.setText(t("lut_filter_dialog.error.no_lut", "未找到可用的LUT文件"))
            return

        ffmpeg_path = self._find_ffmpeg()
        output_file = os.path.join(
            tempfile.gettempdir(),
            f"kq_lut_preview_{generation}.png"
        )

        filter_chain = ",".join(
            [f"lut3d='{self._escape_filter_path(p)}'" for p in lut_paths]
        )

        cmd = [
            ffmpeg_path,
            "-y",
            "-i",
            self._sample_image_path,
            "-vf",
            filter_chain,
            "-frames:v",
            "1",
            output_file,
        ]

        if self._preview_inflight:
            self._preview_pending = True
            return

        self._preview_inflight = True
        self._preview_thread = QThread(self)
        self._preview_worker = _LUTPreviewWorker(cmd, output_file, generation)
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_thread.started.connect(self._preview_worker.run)
        self._preview_worker.finished.connect(self._on_preview_worker_finished)
        self._preview_worker.finished.connect(self._preview_thread.quit)
        self._preview_worker.finished.connect(self._preview_worker.deleteLater)
        self._preview_thread.finished.connect(self._preview_thread.deleteLater)
        self._preview_thread.start()

    def _on_preview_worker_finished(
        self, generation, output_file, success, error_message
    ):
        self._preview_inflight = False
        self._preview_thread = None
        self._preview_worker = None
        try:
            if generation == self._preview_generation:
                if success:
                    pixmap = QPixmap(output_file)
                    if not pixmap.isNull():
                        self._sample_pixmap = pixmap
                        self.update_sample_preview()
                    else:
                        if not self._apply_qimage_lut_preview(self._selected_filter_ids()):
                            self.sample_label.setText(
                                t(
                                    "lut_filter_dialog.error.preview_failed",
                                    "预览生成失败",
                                )
                            )
                elif not self._apply_qimage_lut_preview(self._selected_filter_ids()):
                    self.sample_label.setText(
                        t("lut_filter_dialog.error.preview_failed", "预览生成失败")
                    )
                    logger.error(
                        "[LUTPreview] generation=%s error=%s",
                        generation,
                        error_message[-4000:],
                    )
        finally:
            try:
                os.remove(output_file)
            except FileNotFoundError:
                pass
            except OSError as cleanup_error:
                logger.warning(
                    "[LUTPreview] cleanup failed file=%s error=%s",
                    output_file,
                    cleanup_error,
                )

        if self._preview_pending:
            self._preview_pending = False
            self.update_preview_from_selection()
