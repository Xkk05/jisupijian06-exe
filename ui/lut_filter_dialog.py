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
from PyQt6.QtGui import QPixmap
import os
import subprocess
import tempfile

from ui.components import ModernButton, ModernCard, ToggleSwitch, ModernInput, create_section_header
from ui.theme import Theme
from ui.i18n import t
from utils.lut_filters import list_filters, display_to_id, resolve_lut_path


class _LUTPreviewWorker(QObject):
    finished = pyqtSignal(int, str, bool)

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
        try:
            subprocess.run(self._cmd, capture_output=True, check=True, creationflags=creation_flags)
            success = True
        except Exception:
            success = False
        self.finished.emit(self._generation, self._output_file, success)


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
            checkbox = QCheckBox(item["name"])
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
        sample_image_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            t("lut_filter_dialog.preview.sample_image", "样例.jpg"),
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
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        bundled_ffmpeg = os.path.join(app_dir, "ffmpeg", "ffmpeg.exe")
        if os.path.exists(bundled_ffmpeg):
            return bundled_ffmpeg
        processor_ffmpeg = os.path.join(app_dir, "processor", "ffmpeg.exe")
        if os.path.exists(processor_ffmpeg):
            return processor_ffmpeg
        return "ffmpeg"

    def _escape_filter_path(self, path: str) -> str:
        return path.replace("\\", "/").replace(":", "\\:")

    def update_preview_from_selection(self):
        self._preview_generation += 1
        generation = self._preview_generation
        if not self._sample_pixmap:
            return
        if not self.apply_switch.isChecked():
            self._sample_pixmap = self._original_pixmap
            self.update_sample_preview()
            return

        selected_ids = []
        for checkbox in self.filter_checkboxes:
            if checkbox.isChecked():
                filter_id = checkbox.property("filter_id")
                if filter_id:
                    selected_ids.append(filter_id)

        if not selected_ids:
            self._sample_pixmap = self._original_pixmap
            self.update_sample_preview()
            return

        if self.random_apply_check.isChecked():
            selected_ids = [selected_ids[0]]

        lut_paths = []
        for filter_id in selected_ids:
            lut_path = resolve_lut_path(filter_id)
            if lut_path and os.path.exists(lut_path):
                lut_paths.append(lut_path)

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

    def _on_preview_worker_finished(self, generation, output_file, success):
        self._preview_inflight = False
        self._preview_thread = None
        self._preview_worker = None
        if generation == self._preview_generation:
            if success:
                pixmap = QPixmap(output_file)
                if not pixmap.isNull():
                    self._sample_pixmap = pixmap
                    self.update_sample_preview()
                else:
                    self.sample_label.setText(t("lut_filter_dialog.error.preview_failed", "预览生成失败"))
            else:
                self.sample_label.setText(t("lut_filter_dialog.error.preview_failed", "预览生成失败"))

        if self._preview_pending:
            self._preview_pending = False
            self.update_preview_from_selection()
