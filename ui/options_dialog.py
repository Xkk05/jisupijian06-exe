"""
选项设置对话框
包含转换和设置两个标签页，所有配置参数保存到全局配置中
"""

import os
import sys
import traceback
import subprocess
import re
import webbrowser
import requests
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QRadioButton,
    QCheckBox,
    QSpinBox,
    QLineEdit,
    QPushButton,
    QButtonGroup,
    QGroupBox,
    QGridLayout,
    QMessageBox,
    QFileDialog,
    QFrame,
    QStackedLayout,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from ui.components import (
    ModernButton,
    ModernCard,
    ModernInput,
    create_modern_scroll_area,
    create_param_row,
    SegmentedControl,
)
from ui.theme import Theme
from ui.i18n import (
    apply_language_to_widget,
    get_language_manager,
    get_native_language_name,
    get_supported_languages,
    t,
)
from processor.options_manager import OptionsConfigManager
from config.app_info import APP_NAME, APP_VERSION, SOFT_NUMBER
from utils.unified_logger import logger, get_log_dir
from utils.icon_utils import build_app_logo_icon


def _ts(text: str) -> str:
    return get_language_manager().translate_source_text(text)


class OptionsDialog(QDialog):
    """选项设置对话框"""

    # 配置更新信号
    config_updated = pyqtSignal(dict)
    language_changed = pyqtSignal(str)

    def __init__(self, parent=None, config=None, update_service=None):
        super().__init__(parent)
        try:
            logger.info(f"[Options] __init__ start config_passed={config is not None}")
            self._update_service = update_service
            self._language_manager = get_language_manager()
            self.options_manager = OptionsConfigManager()
            merged_config = self.get_default_config()
            merged_config.update(self.options_manager.get_batch_options())
            merged_config["ui_language"] = self.options_manager.get_language()

            if config:
                merged_config.update(config)
            self.config = merged_config
            self.init_ui()
            self.load_config()
            self._language_manager.language_changed.connect(self._on_language_changed)
            apply_language_to_widget(self)

            # 设置窗口图标
            icon = build_app_logo_icon()
            if not icon.isNull():
                self.setWindowIcon(icon)
            logger.info("[Options] __init__ end")
        except Exception:
            error_detail = traceback.format_exc()
            logger.error(f"[Options] __init__ failed:\n{error_detail}")
            raise

    def _on_language_changed(self, _lang: str):
        self._refresh_language_combo_labels()
        apply_language_to_widget(self)

    def _refresh_language_combo_labels(self):
        if not hasattr(self, "language_combo"):
            return
        current = self.language_combo.currentData()
        self.language_combo.blockSignals(True)
        self.language_combo.clear()
        for lang_code in get_supported_languages():
            label = get_native_language_name(lang_code)
            self.language_combo.addItem(label, lang_code)
        idx = self.language_combo.findData(current)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        elif self.language_combo.count() > 0:
            self.language_combo.setCurrentIndex(0)
        self.language_combo.blockSignals(False)

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(t("options.title", "选项"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")

        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 创建分段控制器
        self.tab_control = SegmentedControl(
            [t("options.tab.convert", "转换"), t("options.tab.settings", "设置")]
        )
        self.tab_control.setFixedWidth(440)
        self.tab_control.valueChanged.connect(self._switch_tab)
        # 设置每个按钮的宽度
        for btn in self.tab_control.buttons:
            btn.setMinimumWidth(190)
        layout.addWidget(self.tab_control, alignment=Qt.AlignmentFlag.AlignCenter)

        # 标签内容容器
        tabs_container = QWidget()
        tabs_container.setStyleSheet("background: #F8FAFC;")
        tabs_layout = QStackedLayout(tabs_container)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(0)
        self._tabs_layout = tabs_layout

        tabs_layout.addWidget(self.create_convert_tab())
        tabs_layout.addWidget(self.create_settings_tab())
        tabs_layout.setCurrentIndex(0)
        layout.addWidget(tabs_container)

        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        reset_btn = ModernButton(t("options.btn.reset", "重置"), ModernButton.Style.Secondary)
        reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        ok_btn = ModernButton(t("options.btn.ok", "确定"), ModernButton.Style.Primary)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept_config)
        button_layout.addWidget(ok_btn)

        cancel_btn = ModernButton(t("options.btn.cancel", "取消"), ModernButton.Style.Secondary)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _switch_tab(self, index: int):
        """切换分段控制器标签页"""
        if 0 <= index < self._tabs_layout.count():
            self._tabs_layout.setCurrentIndex(index)

    def create_convert_tab(self) -> QWidget:
        """创建转换标签页"""
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #F8FAFC;")
        layout = QVBoxLayout(content_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # 1. 目标文件格式
        format_card = ModernCard(t("options.section.target_format", "目标文件格式"))
        format_layout = QHBoxLayout()

        self.format_mp4_radio = QRadioButton("Mp4")
        self.format_mp4_radio.setChecked(True)
        self.format_source_radio = QRadioButton(t("options.option.source_format", "源格式"))

        self.format_group_btn = QButtonGroup()
        self.format_group_btn.addButton(self.format_mp4_radio, 0)
        self.format_group_btn.addButton(self.format_source_radio, 1)

        format_layout.addWidget(self.format_mp4_radio)
        format_layout.addWidget(self.format_source_radio)
        format_layout.addStretch()
        format_card.addLayout(format_layout)
        layout.addWidget(format_card)

        # 2. 若目标文件存在，则
        exist_card = ModernCard(
            t("options.section.file_exists_action", "若目标文件已存在，则")
        )
        exist_layout = QVBoxLayout()

        exist_radio_layout = QHBoxLayout()
        self.exist_rename_radio = QRadioButton(t("options.option.rename", "重命名"))
        self.exist_rename_radio.setChecked(True)
        self.exist_overwrite_radio = QRadioButton(t("options.option.overwrite", "覆盖"))

        self.exist_group_btn = QButtonGroup()
        self.exist_group_btn.addButton(self.exist_rename_radio, 0)
        self.exist_group_btn.addButton(self.exist_overwrite_radio, 1)

        exist_radio_layout.addWidget(self.exist_rename_radio)
        exist_radio_layout.addWidget(self.exist_overwrite_radio)
        exist_radio_layout.addStretch()
        exist_layout.addLayout(exist_radio_layout)

        # 文件名去除
        remove_layout = QHBoxLayout()
        self.filename_remove_check = QCheckBox(t("options.label.filename_remove", "文件名去除:"))
        self.filename_remove_input = QLineEdit(t("options.default.filename_remove_text", "抖音|快手"))
        self.filename_remove_input.setEnabled(False)
        self.filename_remove_input.setPlaceholderText(
            t("options.placeholder.filename_remove_keywords", "多个关键词用 | 分隔，如：抖音|快手")
        )
        self.filename_remove_input.setToolTip(
            t(
                "options.tooltip.filename_remove_mode",
                "开启“正则”后按正则表达式匹配；未开启时按普通关键词替换",
            )
        )
        ModernInput.apply_style(self.filename_remove_input)
        self.filename_regex_check = QCheckBox(t("options.option.regex", "正则"))

        self.filename_remove_check.stateChanged.connect(
            lambda state: self.filename_remove_input.setEnabled(
                state == Qt.CheckState.Checked.value
            )
        )
        self.filename_remove_check.stateChanged.connect(
            lambda _state: self._update_filename_remove_live_feedback()
        )
        self.filename_regex_check.toggled.connect(
            lambda _checked: self._update_filename_remove_live_feedback()
        )
        self.filename_remove_input.textChanged.connect(
            lambda _text: self._update_filename_remove_live_feedback()
        )

        remove_layout.addWidget(self.filename_remove_check)
        remove_layout.addWidget(self.filename_remove_input)
        remove_layout.addWidget(self.filename_regex_check)
        remove_layout.addStretch()
        exist_layout.addLayout(remove_layout)

        self.filename_remove_feedback = QLabel("")
        self.filename_remove_feedback.setStyleSheet(
            f"color: {Theme.Warning}; font-size: 12px;"
        )
        self.filename_remove_feedback.setVisible(False)
        exist_layout.addWidget(self.filename_remove_feedback)

        exist_card.addLayout(exist_layout)
        layout.addWidget(exist_card)

        # 3. 并行任务数量
        parallel_card = ModernCard(t("options.section.parallel_tasks", "并行任务数量"))
        parallel_layout = QHBoxLayout()
        self.parallel_spinbox = QSpinBox()
        self.parallel_spinbox.setMinimum(1)
        self.parallel_spinbox.setMaximum(os.cpu_count() or 8)
        self.parallel_spinbox.setValue(2)
        ModernInput.apply_style(self.parallel_spinbox)
        parallel_layout.addWidget(
            create_param_row("并行任务数量:", self.parallel_spinbox)
        )
        parallel_card.addLayout(parallel_layout)
        layout.addWidget(parallel_card)

        # 4. 使用H265编码、HDR转SDR（放在一行）
        encode_card = ModernCard(t("options.section.encoding_processing", "编码与画面处理"))
        h265_hdr_layout = QHBoxLayout()
        self.h265_check = QCheckBox(t("options.option.use_h265", "使用H265编码"))
        self.hdr_to_sdr_check = QCheckBox(t("options.option.hdr_to_sdr", "HDR转SDR"))
        h265_hdr_layout.addWidget(self.h265_check)
        h265_hdr_layout.addWidget(self.hdr_to_sdr_check)
        h265_hdr_layout.addStretch()
        encode_card.addLayout(h265_hdr_layout)

        # 5. 重新处理忽略已完成任务
        self.ignore_completed_check = QCheckBox(
            t("options.option.ignore_completed_on_reprocess", "重新处理忽略已完成任务")
        )
        self.ignore_completed_check.setChecked(True)
        ignore_layout = QHBoxLayout()
        ignore_layout.addWidget(self.ignore_completed_check)
        ignore_layout.addStretch()
        encode_card.addLayout(ignore_layout)
        layout.addWidget(encode_card)

        layout.addStretch()
        scroll_area = create_modern_scroll_area(content_widget)
        outer_layout.addWidget(scroll_area)
        return widget

    def create_settings_tab(self) -> QWidget:
        """创建设置标签页"""
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #F8FAFC;")
        layout = QVBoxLayout(content_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # 0. 语言设置
        language_card = ModernCard(t("options.section.language", "语言"))
        language_layout = QHBoxLayout()
        language_layout.setSpacing(10)
        language_layout.addWidget(QLabel(t("options.label.ui_language", "界面语言:")))
        self.language_combo = QComboBox()
        ModernInput.apply_style(self.language_combo)
        self.language_combo.setMinimumWidth(180)
        language_layout.addWidget(self.language_combo)
        hint = QLabel(t("options.language.apply_tip", "语言修改将立即生效。"))
        hint.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 12px;")
        language_layout.addWidget(hint)
        language_layout.addStretch()
        language_card.addLayout(language_layout)
        layout.addWidget(language_card)
        self._refresh_language_combo_labels()

        # 1. 所有任务完成后
        complete_card = ModernCard(t("options.section.on_all_tasks_complete", "所有任务完成后"))
        complete_layout = QVBoxLayout()

        complete_radio_layout = QHBoxLayout()
        self.complete_none_radio = QRadioButton(t("options.option.no_action", "无操作"))
        self.complete_none_radio.setChecked(True)
        self.complete_exit_radio = QRadioButton(t("options.option.exit_program", "退出程序"))

        self.complete_group_btn = QButtonGroup()
        self.complete_group_btn.addButton(self.complete_none_radio, 0)
        self.complete_group_btn.addButton(self.complete_exit_radio, 1)

        complete_radio_layout.addWidget(self.complete_none_radio)
        complete_radio_layout.addWidget(self.complete_exit_radio)
        complete_radio_layout.addStretch()
        complete_layout.addLayout(complete_radio_layout)

        # 2. 打开输出文件夹、声音提示
        complete_options_layout = QHBoxLayout()
        self.open_folder_check = QCheckBox(t("options.option.open_output_folder", "打开输出文件夹"))
        self.open_folder_check.setChecked(True)
        self.sound_alert_check = QCheckBox(t("options.option.sound_alert", "声音提示"))
        self.sound_alert_check.setChecked(True)

        complete_options_layout.addWidget(self.open_folder_check)
        complete_options_layout.addWidget(self.sound_alert_check)
        complete_options_layout.addStretch()
        complete_layout.addLayout(complete_options_layout)

        complete_card.addLayout(complete_layout)
        layout.addWidget(complete_card)

        # 3. 启用GPU硬件加速
        hardware_card = ModernCard(t("options.section.hardware_acceleration", "硬件加速"))
        gpu_layout = QHBoxLayout()
        self.gpu_accel_check = QCheckBox(
            t("options.option.enable_gpu_accel", "启用GPU硬件加速")
        )
        self.gpu_accel_check.setChecked(True)
        gpu_layout.addWidget(self.gpu_accel_check)
        gpu_layout.addStretch()
        hardware_card.addLayout(gpu_layout)

        # 4-5. N卡优化、I卡优化（放在一行）
        card_layout = QHBoxLayout()
        self.nvidia_optimize_check = QCheckBox(t("options.option.nvidia_optimize", "N卡优化"))
        self.intel_optimize_check = QCheckBox(t("options.option.intel_optimize", "I卡优化"))
        card_layout.addWidget(self.nvidia_optimize_check)
        card_layout.addWidget(self.intel_optimize_check)
        card_layout.addStretch()
        hardware_card.addLayout(card_layout)
        layout.addWidget(hardware_card)

        # 6-7. 文件名加数字编号、目录模式支持子级（放在一行）
        naming_card = ModernCard(t("options.section.naming_directory", "命名与目录"))
        filename_layout = QHBoxLayout()
        self.filename_number_check = QCheckBox(
            t("options.option.filename_number", "文件名加数字编号")
        )
        self.subdir_support_check = QCheckBox(
            t("options.option.subdir_support", "目录模式支持子级")
        )
        filename_layout.addWidget(self.filename_number_check)
        filename_layout.addWidget(self.subdir_support_check)
        filename_layout.addStretch()
        naming_card.addLayout(filename_layout)

        # 8. 输出目录选项（放在一行）
        output_layout = QHBoxLayout()
        self.output_to_folder_check = QCheckBox(
            t("options.option.output_to_separate_folder", "输出至独立文件夹中")
        )
        self.output_to_video_folder_check = QCheckBox(
            t("options.option.output_to_video_named_folder", "输出至视频同名文件夹中")
        )
        self.output_to_folder_check.stateChanged.connect(
            lambda state: self._sync_output_folder_checks(
                self.output_to_folder_check, self.output_to_video_folder_check, state
            )
        )
        self.output_to_video_folder_check.stateChanged.connect(
            lambda state: self._sync_output_folder_checks(
                self.output_to_video_folder_check, self.output_to_folder_check, state
            )
        )
        output_layout.addWidget(self.output_to_folder_check)
        output_layout.addWidget(self.output_to_video_folder_check)
        output_layout.addStretch()
        naming_card.addLayout(output_layout)
        layout.addWidget(naming_card)

        # 9. 处理后删除原视频（只与到回收站关联）
        cleanup_card = ModernCard(t("options.section.cleanup_task", "清理与任务"))
        delete_layout = QHBoxLayout()
        self.delete_original_check = QCheckBox(
            t("options.option.delete_original", "处理后删除原视频")
        )
        self.delete_original_check.stateChanged.connect(self.on_delete_original_changed)

        self.to_recycle_check = QCheckBox(t("options.option.to_recycle_bin", "到回收站"))
        self.to_recycle_check.setChecked(True)
        self.to_recycle_check.setEnabled(False)

        delete_layout.addWidget(self.delete_original_check)
        delete_layout.addWidget(self.to_recycle_check)
        delete_layout.addStretch()
        cleanup_card.addLayout(delete_layout)

        # 10-11. 移入原处、移除任务（独立选项，放在一行）
        move_layout = QHBoxLayout()
        self.move_to_original_check = QCheckBox(t("options.option.move_to_original", "移入原处"))
        self.remove_task_check = QCheckBox(t("options.option.remove_task", "移除任务"))

        move_layout.addWidget(self.move_to_original_check)
        move_layout.addWidget(self.remove_task_check)
        move_layout.addStretch()
        cleanup_card.addLayout(move_layout)

        # 12-13. 移除任务弹出确认提示、保留未完成任务列表（放在一行）
        confirm_layout = QHBoxLayout()
        self.remove_confirm_check = QCheckBox(
            t("options.option.remove_confirm", "移除任务弹出确认提示")
        )
        self.remove_confirm_check.setChecked(True)
        self.keep_unfinished_check = QCheckBox(
            t("options.option.keep_unfinished", "保留未完成任务列表")
        )

        confirm_layout.addWidget(self.remove_confirm_check)
        confirm_layout.addWidget(self.keep_unfinished_check)
        confirm_layout.addStretch()
        cleanup_card.addLayout(confirm_layout)
        layout.addWidget(cleanup_card)

        # 日志管理
        log_card = ModernCard(t("options.section.log_management", "日志管理"))
        log_layout = QHBoxLayout()
        open_log_btn = ModernButton(
            t("options.btn.open_log_dir", "打开日志目录"), ModernButton.Style.Outline, icon_name="folder-open"
        )
        open_log_btn.clicked.connect(self.open_log_directory)
        log_layout.addWidget(open_log_btn)
        log_layout.addStretch()
        log_card.addLayout(log_layout)
        layout.addWidget(log_card)

        # 问题反馈
        feedback_card = ModernCard(t("options.section.feedback", "问题反馈"))
        feedback_layout = QHBoxLayout()
        feedback_btn = ModernButton(t("options.btn.feedback", "问题反馈"), ModernButton.Style.Outline)
        feedback_btn.clicked.connect(self._open_feedback)
        feedback_layout.addWidget(feedback_btn)
        feedback_layout.addStretch()
        feedback_card.addLayout(feedback_layout)
        layout.addWidget(feedback_card)

        # 关于
        about_card = ModernCard(t("options.section.about", "关于"))
        about_layout = QVBoxLayout()
        about_layout.setSpacing(8)
        about_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo_label = QLabel()
        logo_label.setFixedSize(220, 80)
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "logo.png",
        )
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                logo_label.setPixmap(
                    pixmap.scaled(
                        220,
                        80,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        about_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        name_label = QLabel(APP_NAME)
        name_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        about_layout.addWidget(name_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        version_label = QLabel(_ts(f"版本 {APP_VERSION}"))
        version_label.setStyleSheet(f"color: {Theme.TextSecondary};")
        about_layout.addWidget(version_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 检查更新区域
        update_row = QHBoxLayout()
        update_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        update_row.setSpacing(10)

        self._update_status_label = QLabel("")
        self._update_status_label.setStyleSheet(
            f"color: {Theme.TextSecondary}; font-size: 12px;"
        )
        update_row.addWidget(self._update_status_label)

        self._check_update_btn = ModernButton(
            t("options.btn.check_update", "检查更新"), ModernButton.Style.Outline
        )
        self._check_update_btn.setFixedHeight(28)
        self._check_update_btn.clicked.connect(self._on_check_update)
        update_row.addWidget(self._check_update_btn)

        self._do_update_btn = ModernButton(
            t("options.btn.update_now", "立即更新"), ModernButton.Style.Primary
        )
        self._do_update_btn.setFixedHeight(28)
        self._do_update_btn.setVisible(False)
        self._do_update_btn.clicked.connect(self._on_do_update)
        update_row.addWidget(self._do_update_btn)

        about_layout.addLayout(update_row)

        # 更新日志（默认隐藏）
        self._update_log_label = QLabel("")
        self._update_log_label.setWordWrap(True)
        self._update_log_label.setStyleSheet(f"""
            color: {Theme.TextSecondary};
            font-size: 12px;
            background-color: {Theme.PrimaryLight};
            border-radius: 6px;
            padding: 8px;
        """)
        self._update_log_label.setVisible(False)
        about_layout.addWidget(self._update_log_label)

        # 如果已检测到更新，立即显示
        if self._update_service and self._update_service.has_update:
            info = self._update_service.update_info
            self._show_update_available(info)

        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(6)
        brand_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        brand_icon = QLabel()
        brand_icon.setFixedSize(16, 16)
        brand_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "kunqiong.png",
        )
        if os.path.exists(brand_icon_path):
            brand_pixmap = QPixmap(brand_icon_path)
            if not brand_pixmap.isNull():
                brand_icon.setPixmap(
                    brand_pixmap.scaled(
                        16,
                        16,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        brand_layout.addWidget(brand_icon)

        brand_label = QLabel(t("options.brand.name", "极速批剪"))
        brand_label.setStyleSheet(f"color: {Theme.TextSecondary};")
        brand_layout.addWidget(brand_label)

        about_layout.addLayout(brand_layout)

        about_card.addLayout(about_layout)
        layout.addWidget(about_card)

        layout.addStretch()
        scroll_area = create_modern_scroll_area(content_widget)
        outer_layout.addWidget(scroll_area)
        return widget

    def on_delete_original_changed(self, state):
        """删除原视频状态改变（只关联到回收站）"""
        enabled = state == Qt.CheckState.Checked.value
        self.to_recycle_check.setEnabled(enabled)
        # 移入原处和移除任务是独立选项，不受影响

    def _sync_output_folder_checks(
        self, active_check: QCheckBox, other_check: QCheckBox, state: int
    ):
        if state == Qt.CheckState.Checked.value and other_check.isChecked():
            other_check.blockSignals(True)
            other_check.setChecked(False)
            other_check.blockSignals(False)

    def _open_feedback(self):
        """打开问题反馈页面"""
        try:
            resp = requests.post(
                "https://api-web.kunqiongai.com/soft_desktop/get_feedback_url",
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 1:
                url = result["data"]["url"]
                # 拼接软件编号
                if url.endswith("soft_number="):
                    url += SOFT_NUMBER
                elif "soft_number=" in url:
                    # 已经有值，替换
                    pass
                else:
                    url += SOFT_NUMBER
                webbrowser.open(url)
            else:
                QMessageBox.warning(
                    self, "提示", f"获取反馈链接失败: {result.get('msg', '未知错误')}"
                )
        except Exception as e:
            logger.error(f"[Options] 获取反馈链接失败: {e}")
            QMessageBox.warning(self, "提示", f"获取反馈链接失败:\n{str(e)}")

    def _on_check_update(self):
        """手动检查更新"""
        if not self._update_service:
            return
        self._update_status_label.setText(t("options.status.checking_update", "正在检查更新..."))
        self._check_update_btn.setEnabled(False)
        self._do_update_btn.setVisible(False)
        self._update_log_label.setVisible(False)

        # 连接信号
        self._update_service.update_available.connect(self._show_update_available)
        self._update_service.no_update.connect(self._show_no_update)
        self._update_service.check_failed.connect(self._show_check_failed)
        self._update_service.check_update()

    def _show_update_available(self, info):
        """显示有更新"""
        try:
            self._update_service.update_available.disconnect(
                self._show_update_available
            )
            self._update_service.no_update.disconnect(self._show_no_update)
            self._update_service.check_failed.disconnect(self._show_check_failed)
        except (TypeError, RuntimeError):
            pass
        self._update_status_label.setText(_ts(f"发现新版本: {info.version}"))
        self._update_status_label.setStyleSheet(
            f"color: {Theme.Primary}; font-size: 12px; font-weight: 500;"
        )
        self._check_update_btn.setEnabled(True)
        self._do_update_btn.setVisible(True)
        if info.update_log:
            self._update_log_label.setText(info.update_log)
            self._update_log_label.setVisible(True)

    def _show_no_update(self):
        """显示已是最新"""
        try:
            self._update_service.update_available.disconnect(
                self._show_update_available
            )
            self._update_service.no_update.disconnect(self._show_no_update)
            self._update_service.check_failed.disconnect(self._show_check_failed)
        except (TypeError, RuntimeError):
            pass
        self._update_status_label.setText(t("options.status.latest", "已是最新版本"))
        self._update_status_label.setStyleSheet(
            f"color: {Theme.Success}; font-size: 12px;"
        )
        self._check_update_btn.setEnabled(True)

    def _show_check_failed(self, error: str):
        """显示检查失败"""
        try:
            self._update_service.update_available.disconnect(
                self._show_update_available
            )
            self._update_service.no_update.disconnect(self._show_no_update)
            self._update_service.check_failed.disconnect(self._show_check_failed)
        except (TypeError, RuntimeError):
            pass
        self._update_status_label.setText(t("options.status.check_failed", "检查更新失败"))
        self._update_status_label.setStyleSheet(
            f"color: {Theme.Error}; font-size: 12px;"
        )
        self._check_update_btn.setEnabled(True)

    def _on_do_update(self):
        """执行更新"""
        if not self._update_service:
            return
        reply = QMessageBox.question(
            self,
            t("options.dialog.confirm_update.title", "确认更新"),
            t(
                "options.dialog.confirm_update.message",
                "更新将关闭当前程序并启动更新器。\n确定要立即更新吗？",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._update_service.start_update()

    def open_log_directory(self):
        """打开日志目录"""
        try:
            log_dir = get_log_dir(Path("."))

            # 确保目录存在
            if not log_dir.exists():
                log_dir.mkdir(parents=True, exist_ok=True)

            # 在Windows系统中打开文件夹
            if sys.platform == "win32":
                os.startfile(str(log_dir))
            else:
                # 其他系统使用xdg-open或open
                subprocess.Popen(["xdg-open", str(log_dir)])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开日志目录:\n{str(e)}")

    def get_default_config(self) -> dict:
        """获取默认配置"""
        return {
            # 转换页面
            "target_format": "mp4",  # mp4 或 source
            "file_exists_action": "rename",  # rename 或 overwrite
            "filename_remove_enabled": False,
            "filename_remove_text": "抖音|快手",
            "filename_remove_regex": False,
            "parallel_tasks": 2,
            "use_h265": False,
            "hdr_to_sdr": False,
            "ignore_completed": True,
            # 设置页面
            "complete_action": "none",  # none, exit
            "open_folder_after_complete": True,
            "sound_alert": True,
            "gpu_accel": True,
            "nvidia_optimize": False,
            "intel_optimize": False,
            "filename_add_number": False,
            "subdir_support": False,
            "output_to_folder": False,
            "output_to_video_folder": False,
            "delete_original": False,
            "to_recycle": True,
            "move_to_original": False,
            "remove_task_after_complete": False,
            "remove_confirm": True,
            "keep_unfinished": False,
            "ui_language": self.options_manager.get_language(),
        }

    def load_config(self):
        """加载配置到界面"""
        # 转换页面
        if self.config.get("target_format") == "mp4":
            self.format_mp4_radio.setChecked(True)
        else:
            self.format_source_radio.setChecked(True)

        if self.config.get("file_exists_action") == "rename":
            self.exist_rename_radio.setChecked(True)
        else:
            self.exist_overwrite_radio.setChecked(True)

        self.filename_remove_check.setChecked(
            self.config.get("filename_remove_enabled", False)
        )
        self.filename_remove_input.setText(
            self.config.get("filename_remove_text", "抖音|快手")
        )
        self.filename_regex_check.setChecked(
            self.config.get("filename_remove_regex", False)
        )

        self.parallel_spinbox.setValue(self.config.get("parallel_tasks", 2))

        self.h265_check.setChecked(self.config.get("use_h265", False))
        self.hdr_to_sdr_check.setChecked(self.config.get("hdr_to_sdr", False))
        self.ignore_completed_check.setChecked(
            self.config.get("ignore_completed", True)
        )

        # 设置页面
        complete_action = self.config.get("complete_action", "none")
        if complete_action == "none":
            self.complete_none_radio.setChecked(True)
        else:
            self.complete_exit_radio.setChecked(True)

        self.open_folder_check.setChecked(
            self.config.get("open_folder_after_complete", True)
        )
        self.sound_alert_check.setChecked(self.config.get("sound_alert", True))

        self.gpu_accel_check.setChecked(self.config.get("gpu_accel", True))
        self.nvidia_optimize_check.setChecked(self.config.get("nvidia_optimize", False))
        self.intel_optimize_check.setChecked(self.config.get("intel_optimize", False))
        self.filename_number_check.setChecked(
            self.config.get("filename_add_number", False)
        )
        self.subdir_support_check.setChecked(self.config.get("subdir_support", False))

        self.output_to_folder_check.setChecked(
            self.config.get("output_to_folder", False)
        )
        self.output_to_video_folder_check.setChecked(
            self.config.get("output_to_video_folder", False)
        )

        self.delete_original_check.setChecked(self.config.get("delete_original", False))
        self.to_recycle_check.setChecked(self.config.get("to_recycle", True))
        self.move_to_original_check.setChecked(
            self.config.get("move_to_original", False)
        )
        self.remove_task_check.setChecked(
            self.config.get("remove_task_after_complete", False)
        )

        self.remove_confirm_check.setChecked(self.config.get("remove_confirm", True))
        self.keep_unfinished_check.setChecked(self.config.get("keep_unfinished", False))
        if hasattr(self, "language_combo"):
            lang_code = self.config.get("ui_language", self.options_manager.get_language())
            idx = self.language_combo.findData(lang_code)
            if idx >= 0:
                self.language_combo.setCurrentIndex(idx)
        self._update_filename_remove_live_feedback()

    def save_config(self) -> dict:
        """保存界面配置"""
        config = {}

        # 转换页面
        config["target_format"] = (
            "mp4" if self.format_mp4_radio.isChecked() else "source"
        )
        config["file_exists_action"] = (
            "rename" if self.exist_rename_radio.isChecked() else "overwrite"
        )
        config["filename_remove_enabled"] = self.filename_remove_check.isChecked()
        config["filename_remove_text"] = self.filename_remove_input.text().strip()
        config["filename_remove_regex"] = self.filename_regex_check.isChecked()
        config["parallel_tasks"] = self.parallel_spinbox.value()
        config["use_h265"] = self.h265_check.isChecked()
        config["hdr_to_sdr"] = self.hdr_to_sdr_check.isChecked()
        config["ignore_completed"] = self.ignore_completed_check.isChecked()

        # 设置页面
        if self.complete_none_radio.isChecked():
            config["complete_action"] = "none"
        else:
            config["complete_action"] = "exit"

        config["open_folder_after_complete"] = self.open_folder_check.isChecked()
        config["sound_alert"] = self.sound_alert_check.isChecked()
        config["gpu_accel"] = self.gpu_accel_check.isChecked()
        config["nvidia_optimize"] = self.nvidia_optimize_check.isChecked()
        config["intel_optimize"] = self.intel_optimize_check.isChecked()
        config["filename_add_number"] = self.filename_number_check.isChecked()
        config["subdir_support"] = self.subdir_support_check.isChecked()
        config["output_to_folder"] = self.output_to_folder_check.isChecked()
        config["output_to_video_folder"] = self.output_to_video_folder_check.isChecked()
        config["delete_original"] = self.delete_original_check.isChecked()
        config["to_recycle"] = self.to_recycle_check.isChecked()
        config["move_to_original"] = self.move_to_original_check.isChecked()
        config["remove_task_after_complete"] = self.remove_task_check.isChecked()
        config["remove_confirm"] = self.remove_confirm_check.isChecked()
        config["keep_unfinished"] = self.keep_unfinished_check.isChecked()
        config["ui_language"] = (
            self.language_combo.currentData()
            if hasattr(self, "language_combo")
            else self.options_manager.get_language()
        )

        return config

    def _validate_convert_inputs(self) -> bool:
        """校验“转换”标签页中的手动输入项。"""
        if not self.filename_remove_check.isChecked():
            return True

        raw_text = self.filename_remove_input.text().strip()
        use_regex = self.filename_regex_check.isChecked()
        if not raw_text:
            QMessageBox.warning(
                self, "输入不完整", "已开启“文件名去除”，请填写关键词或关闭该选项。"
            )
            self.filename_remove_input.setFocus()
            return False

        if use_regex:
            try:
                re.compile(raw_text)
            except re.error as exc:
                QMessageBox.warning(
                    self,
                    "正则表达式无效",
                    f"文件名去除正则无法编译：\n{exc}\n\n请修正表达式后再保存。",
                )
                self.filename_remove_input.setFocus()
                return False
        else:
            tokens = [token.strip() for token in raw_text.split("|") if token.strip()]
            if not tokens:
                QMessageBox.warning(
                    self, "输入不完整", "请至少填写一个有效关键词（可用 | 分隔多个）。"
                )
                self.filename_remove_input.setFocus()
                return False

        return True

    def _set_filename_remove_input_state(self, valid: bool, message: str = "") -> None:
        if valid:
            ModernInput.apply_style(self.filename_remove_input)
            self.filename_remove_feedback.setVisible(False)
            self.filename_remove_feedback.setText("")
        else:
            self.filename_remove_input.setStyleSheet(
                "QLineEdit { border: 1px solid #EF4444; border-radius: 6px; padding: 0 10px; }"
            )
            self.filename_remove_feedback.setText(message)
            self.filename_remove_feedback.setVisible(True)

    def _update_filename_remove_live_feedback(self) -> bool:
        """输入时即时反馈文件名去除配置有效性。"""
        if not self.filename_remove_check.isChecked():
            self._set_filename_remove_input_state(True)
            return True

        raw_text = self.filename_remove_input.text().strip()
        if not raw_text:
            self._set_filename_remove_input_state(
                False, "已启用“文件名去除”，请填写关键词或关闭该选项。"
            )
            return False

        if self.filename_regex_check.isChecked():
            try:
                re.compile(raw_text)
            except re.error as exc:
                self._set_filename_remove_input_state(False, f"正则无效：{exc}")
                return False
            self._set_filename_remove_input_state(True)
            return True

        tokens = [token.strip() for token in raw_text.split("|") if token.strip()]
        if not tokens:
            self._set_filename_remove_input_state(
                False, "请至少输入一个关键词，多个关键词可用 | 分隔。"
            )
            return False

        self._set_filename_remove_input_state(True)
        return True

    def reset_to_default(self):
        """重置为默认配置"""
        reply = QMessageBox.question(
            self,
            t("options.dialog.reset.title", "确认重置"),
            t("options.dialog.reset.message", "确定要恢复默认设置吗？"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config = self.get_default_config()
            self.load_config()

    def accept_config(self):
        """确定按钮"""
        if not self._update_filename_remove_live_feedback():
            return
        if not self._validate_convert_inputs():
            return

        # 检查H265编码选项
        if self.h265_check.isChecked():
            reply = QMessageBox.warning(
                self,
                "警告",
                "使用H265编码可能导致某些播放器或网站不支持，建议使用默认H264编码。\n\n确定要使用H265编码吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # 检查删除原视频选项
        if self.delete_original_check.isChecked():
            reply = QMessageBox.warning(
                self,
                "警告",
                "处理后删除原视频可能导致数据丢失，请确保已做好备份。\n\n确定要启用此选项吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                self.delete_original_check.setChecked(False)
                return

        self.config = self.save_config()
        self.options_manager.set_batch_options(self.config)
        old_language = self._language_manager.language
        new_language = self.config.get("ui_language", old_language)
        if new_language != old_language:
            self.options_manager.set_language(new_language)
            self.options_manager.save_config()
            self._language_manager.set_language(new_language)
            self.language_changed.emit(new_language)
        self.config_updated.emit(self.config)
        self.accept()


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setWindowIcon(build_app_logo_icon())
    dialog = OptionsDialog()

    def on_config_updated(config):
        print("配置已更新:")
        for key, value in config.items():
            print(f"  {key}: {value}")

    dialog.config_updated.connect(on_config_updated)
    dialog.exec()
