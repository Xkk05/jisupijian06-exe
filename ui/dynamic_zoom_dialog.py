"""
动态缩放设置对话框
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QCheckBox, QPushButton, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QMessageBox
)
from PyQt6.QtCore import Qt
from ui.components import ModernButton
from ui.i18n import t


class DynamicZoomDialog(QDialog):
    """动态缩放设置对话框"""
    
    def __init__(self, parent=None, video_path=None):
        super().__init__(parent)
        self.video_path = video_path
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(t("dynamic_zoom_dialog.title", "动态缩放设置"))
        self.setMinimumSize(450, 350)  # 缩小窗口尺寸
        
        layout = QVBoxLayout(self)
        layout.setSpacing(3)  # 紧凑间距
        layout.setContentsMargins(8, 8, 8, 8)  # 紧凑边距
        
        # 入场效果
        effect_group = QGroupBox(t("dynamic_zoom_dialog.section.entry_effect", "入场效果"))
        effect_layout = QVBoxLayout(effect_group)
        effect_layout.setSpacing(2)  # 紧凑间距
        effect_layout.setContentsMargins(5, 3, 5, 3)  # 紧凑边距
        
        # 单选：放大/缩小
        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(5)  # 紧凑间距
        
        self.zoom_in_radio = QRadioButton(t("dynamic_zoom_dialog.zoom.in", "放大"))
        self.zoom_out_radio = QRadioButton(t("dynamic_zoom_dialog.zoom.out", "缩小"))
        self.zoom_in_radio.setChecked(True)
        
        zoom_group = QButtonGroup(self)
        zoom_group.addButton(self.zoom_in_radio)
        zoom_group.addButton(self.zoom_out_radio)
        
        zoom_layout.addWidget(self.zoom_in_radio)
        zoom_layout.addWidget(self.zoom_out_radio)
        zoom_layout.addStretch()
        
        effect_layout.addLayout(zoom_layout)
        
        # 缩放中心点随机选取
        self.random_center_check = QCheckBox(
            t("dynamic_zoom_dialog.random_center", "缩放中心点随机选取")
        )
        effect_layout.addWidget(self.random_center_check)
        
        # 提示
        tip_label = QLabel(
            t(
                "dynamic_zoom_dialog.random_center.tip",
                "视频缩放默认从画面中心点开始，若勾选此项，则随机择一位置进行缩放。",
            )
        )
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        effect_layout.addWidget(tip_label)
        
        layout.addWidget(effect_group)
        
        # 时间设置
        time_group = QGroupBox(t("dynamic_zoom_dialog.section.time", "时间设置"))
        time_layout = QGridLayout(time_group)
        time_layout.setHorizontalSpacing(3)  # 水平间距3px
        time_layout.setVerticalSpacing(5)  # 垂直间距5px
        time_layout.setContentsMargins(5, 3, 5, 3)  # 紧凑边距
        
        # 始于 0.0-0.0秒（默认都是0.0，每步0.1）
        time_layout.addWidget(QLabel(t("dynamic_zoom_dialog.time.start_at", "始于:")), 0, 0)
        
        self.start_min = QDoubleSpinBox()
        self.start_min.setRange(0.0, 999.0)
        self.start_min.setSingleStep(0.1)
        self.start_min.setValue(0.0)
        self.start_min.setDecimals(1)
        self.start_min.valueChanged.connect(self._update_live_feedback)
        time_layout.addWidget(self.start_min, 0, 1)
        
        time_layout.addWidget(QLabel("~"), 0, 2)
        
        self.start_max = QDoubleSpinBox()
        self.start_max.setRange(0.0, 999.0)
        self.start_max.setSingleStep(0.1)
        self.start_max.setValue(0.0)
        self.start_max.setDecimals(1)
        self.start_max.valueChanged.connect(self._update_live_feedback)
        time_layout.addWidget(self.start_max, 0, 3)
        
        time_layout.addWidget(QLabel(t("common.second", "秒")), 0, 4)
        
        # 历时 5.0-10.0秒（默认5.0,10.0，每步0.1）
        time_layout.addWidget(QLabel(t("dynamic_zoom_dialog.time.duration", "历时:")), 1, 0)
        
        self.duration_min = QDoubleSpinBox()
        self.duration_min.setRange(0.0, 999.0)
        self.duration_min.setSingleStep(0.1)
        self.duration_min.setValue(5.0)
        self.duration_min.setDecimals(1)
        self.duration_min.valueChanged.connect(self._update_live_feedback)
        time_layout.addWidget(self.duration_min, 1, 1)
        
        time_layout.addWidget(QLabel("~"), 1, 2)
        
        self.duration_max = QDoubleSpinBox()
        self.duration_max.setRange(0.0, 999.0)
        self.duration_max.setSingleStep(0.1)
        self.duration_max.setValue(10.0)
        self.duration_max.setDecimals(1)
        self.duration_max.valueChanged.connect(self._update_live_feedback)
        time_layout.addWidget(self.duration_max, 1, 3)
        
        time_layout.addWidget(QLabel(t("common.second", "秒")), 1, 4)
        
        # 提示
        duration_tip = QLabel(
            t(
                "dynamic_zoom_dialog.time.duration.tip",
                "放大或缩小单程所需时间，取两值范围中一随机值。",
            )
        )
        duration_tip.setWordWrap(True)
        duration_tip.setStyleSheet("color: #666; font-size: 10px; padding: 5px;")
        time_layout.addWidget(duration_tip, 2, 0, 1, 5)
        
        layout.addWidget(time_group)
        
        # 循环设置
        loop_group = QGroupBox()
        loop_layout = QVBoxLayout(loop_group)
        loop_layout.setSpacing(2)  # 紧凑间距
        loop_layout.setContentsMargins(5, 3, 5, 3)  # 紧凑边距
        
        self.loop_check = QCheckBox(t("dynamic_zoom_dialog.loop.enable", "循环缩放"))
        self.loop_check.toggled.connect(self.on_loop_check_changed)
        self.loop_check.toggled.connect(lambda _checked: self._update_live_feedback())
        loop_layout.addWidget(self.loop_check)
        
        # 每次缩放间视频画面停留 3.0-3.0秒（默认3.0，每步0.1）
        pause_layout = QHBoxLayout()
        pause_layout.setSpacing(3)  # 紧凑间距
        pause_layout.addWidget(
            QLabel(t("dynamic_zoom_dialog.loop.pause", "每次缩放间视频画面停留:"))
        )
        
        self.pause_min = QDoubleSpinBox()
        self.pause_min.setRange(0.0, 999.0)
        self.pause_min.setSingleStep(0.1)
        self.pause_min.setValue(3.0)
        self.pause_min.setDecimals(1)
        self.pause_min.setEnabled(False)
        self.pause_min.valueChanged.connect(self._update_live_feedback)
        pause_layout.addWidget(self.pause_min)
        
        pause_layout.addWidget(QLabel("~"))
        
        self.pause_max = QDoubleSpinBox()
        self.pause_max.setRange(0.0, 999.0)
        self.pause_max.setSingleStep(0.1)
        self.pause_max.setValue(3.0)
        self.pause_max.setDecimals(1)
        self.pause_max.setEnabled(False)
        self.pause_max.valueChanged.connect(self._update_live_feedback)
        pause_layout.addWidget(self.pause_max)
        
        pause_layout.addWidget(QLabel(t("common.second", "秒")))
        pause_layout.addStretch()
        
        loop_layout.addLayout(pause_layout)
        self.live_feedback_label = QLabel("")
        self.live_feedback_label.setStyleSheet("color: #F59E0B; font-size: 12px;")
        self.live_feedback_label.setVisible(False)
        loop_layout.addWidget(self.live_feedback_label)
        layout.addWidget(loop_group)
        
        layout.addStretch()
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # 紧凑间距
        
        # 重置按钮
        reset_btn = QPushButton(t("common.reset", "重置"))
        reset_btn.clicked.connect(self.reset)
        button_layout.addWidget(reset_btn)
        
        # 预览按钮
        self.preview_btn = ModernButton(
            t("common.preview", "预览效果"),
            style=ModernButton.Style.Outline,
            icon_name="eye",
        )
        self.preview_btn.clicked.connect(self.preview)
        button_layout.addWidget(self.preview_btn)
        
        button_layout.addStretch()
        
        self.ok_btn = QPushButton(t("common.ok", "确定"))
        self.ok_btn.clicked.connect(self.on_ok)
        button_layout.addWidget(self.ok_btn)
        
        cancel_btn = QPushButton(t("common.cancel", "取消"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self._update_live_feedback()
    
    def on_loop_check_changed(self, checked: bool):
        """循环缩放复选框状态改变"""
        self.pause_min.setEnabled(checked)
        self.pause_max.setEnabled(checked)
    
    def reset(self):
        """重置所有参数"""
        self.zoom_in_radio.setChecked(True)
        self.random_center_check.setChecked(False)
        self.start_min.setValue(0.0)
        self.start_max.setValue(0.0)
        self.duration_min.setValue(5.0)
        self.duration_max.setValue(10.0)
        self.loop_check.setChecked(False)
        self.pause_min.setValue(3.0)
        self.pause_max.setValue(3.0)
    
    def preview(self):
        """预览效果"""
        if not self.video_path:
            QMessageBox.warning(
                self,
                t("common.notice", "提示"),
                t("dynamic_zoom_dialog.preview.no_video", "没有可预览的视频"),
            )
            return
        if not self._validate_inputs():
            return
        
        # 使用主窗口的预览方法
        if hasattr(self.parent(), '_show_preview_with_config'):
            config = self.get_config()
            self.parent()._show_preview_with_config(
                self.video_path,
                t("dynamic_zoom_dialog.preview.title", "动态缩放高级预览"),
                {'dynamic_zoom': {'advanced': config}},
            )
        else:
            QMessageBox.information(
                self,
                t("common.notice", "提示"),
                t(
                    "dynamic_zoom_dialog.preview.not_supported",
                    "预览功能已实现，请在主窗口中点击确定后预览",
                ),
            )
    
    def get_config(self):
        """获取配置"""
        return {
            'zoom_in': self.zoom_in_radio.isChecked(),
            'zoom_out': self.zoom_out_radio.isChecked(),
            'random_center': self.random_center_check.isChecked(),
            'start_min': self.start_min.value(),
            'start_max': self.start_max.value(),
            'duration_min': self.duration_min.value(),
            'duration_max': self.duration_max.value(),
            'loop': self.loop_check.isChecked(),
            'pause_min': self.pause_min.value(),
            'pause_max': self.pause_max.value(),
        }

    def _validate_inputs(self) -> bool:
        """校验手动输入区间，避免最小值大于最大值。"""
        issues = []
        if self.start_min.value() > self.start_max.value():
            issues.append(
                t("dynamic_zoom_dialog.validation.start", "「始于」最小值不能大于最大值")
            )
        if self.duration_min.value() > self.duration_max.value():
            issues.append(
                t("dynamic_zoom_dialog.validation.duration", "「历时」最小值不能大于最大值")
            )
        if self.loop_check.isChecked() and self.pause_min.value() > self.pause_max.value():
            issues.append(
                t("dynamic_zoom_dialog.validation.pause", "「停留」最小值不能大于最大值")
            )

        if not issues:
            return True

        QMessageBox.warning(
            self,
            t("dynamic_zoom_dialog.validation.failed.title", "参数校验未通过"),
            t("dynamic_zoom_dialog.validation.failed.message", "请先修正以下问题：\n• ")
            + "\n• ".join(issues),
        )
        return False

    def _update_live_feedback(self) -> None:
        """输入时即时反馈区间合法性。"""
        issues = []
        if self.start_min.value() > self.start_max.value():
            issues.append(t("dynamic_zoom_dialog.validation.start.short", "始于区间无效"))
        if self.duration_min.value() > self.duration_max.value():
            issues.append(t("dynamic_zoom_dialog.validation.duration.short", "历时区间无效"))
        if self.loop_check.isChecked() and self.pause_min.value() > self.pause_max.value():
            issues.append(t("dynamic_zoom_dialog.validation.pause.short", "停留区间无效"))

        has_issues = bool(issues)
        self.live_feedback_label.setVisible(has_issues)
        self.live_feedback_label.setText("，".join(issues))
        self.ok_btn.setEnabled(not has_issues)
        self.preview_btn.setEnabled(not has_issues)

    def on_ok(self):
        """确定按钮"""
        if not self._validate_inputs():
            return
        self.accept()
    
    def set_config(self, config: dict):
        """设置配置（恢复之前的设置）"""
        if not config:
            return
        
        # 缩放方向
        if config.get('zoom_in', True):
            self.zoom_in_radio.setChecked(True)
        else:
            self.zoom_out_radio.setChecked(True)
        
        # 其他参数
        self.random_center_check.setChecked(config.get('random_center', False))
        self.start_min.setValue(config.get('start_min', 0.0))
        self.start_max.setValue(config.get('start_max', 0.0))
        self.duration_min.setValue(config.get('duration_min', 1.0))
        self.duration_max.setValue(config.get('duration_max', 1.0))
        self.loop_check.setChecked(config.get('loop', False))
        self.pause_min.setValue(config.get('pause_min', 0.0))
        self.pause_max.setValue(config.get('pause_max', 0.0))
        self._update_live_feedback()
