"""
色调设置对话框
集成现代化UI组件
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QDoubleSpinBox, QSpinBox, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt
from ui.components import ModernButton, ModernCard, create_param_row, ModernInput
from ui.theme import Theme
from ui.i18n import t


class ColorToneDialog(QDialog):
    """色调设置对话框"""
    
    def __init__(self, parent=None, video_path=None):
        super().__init__(parent)
        self.video_path = video_path
        self.setWindowTitle(t("color_tone_dialog.title", "色调设置"))
        self.setMinimumWidth(480)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 参数卡片
        card = ModernCard(t("color_tone_dialog.section.basic", "基本参数"))
        
        # 伽玛值
        self.gamma = QDoubleSpinBox()
        self.gamma.setRange(0.01, 10.0)
        self.gamma.setSingleStep(0.01)
        self.gamma.setValue(1.00)
        self.gamma.setDecimals(2)
        ModernInput.apply_style(self.gamma)
        card.addWidget(create_param_row(t("color_tone_dialog.label.gamma", "伽玛值 (Gamma):"), self.gamma))
        
        # RGB通道
        rgb_layout = QGridLayout()
        rgb_layout.setSpacing(10)
        
        self.red = QDoubleSpinBox()
        self.red.setRange(0.0, 10.0)
        self.red.setSingleStep(0.01)
        self.red.setValue(1.00)
        self.red.setDecimals(2)
        ModernInput.apply_style(self.red)
        
        self.green = QDoubleSpinBox()
        self.green.setRange(0.0, 10.0)
        self.green.setSingleStep(0.01)
        self.green.setValue(1.00)
        self.green.setDecimals(2)
        ModernInput.apply_style(self.green)
        
        self.blue = QDoubleSpinBox()
        self.blue.setRange(0.0, 10.0)
        self.blue.setSingleStep(0.01)
        self.blue.setValue(1.00)
        self.blue.setDecimals(2)
        ModernInput.apply_style(self.blue)
        
        rgb_layout.addWidget(QLabel(t("color_tone_dialog.label.red", "红色通道 (R):")), 0, 0)
        rgb_layout.addWidget(self.red, 0, 1)
        rgb_layout.addWidget(QLabel(t("color_tone_dialog.label.green", "绿色通道 (G):")), 1, 0)
        rgb_layout.addWidget(self.green, 1, 1)
        rgb_layout.addWidget(QLabel(t("color_tone_dialog.label.blue", "蓝色通道 (B):")), 2, 0)
        rgb_layout.addWidget(self.blue, 2, 1)
        
        rgb_widget = QWidget()
        rgb_widget.setLayout(rgb_layout)
        card.addWidget(rgb_widget)
        
        layout.addWidget(card)
        
        # 色温卡片
        temp_card = ModernCard(t("color_tone_dialog.section.color_temp", "色温范围"))
        
        temp_layout = QHBoxLayout()
        temp_layout.setSpacing(10)
        
        self.color_temp_min = QSpinBox()
        self.color_temp_min.setRange(1000, 20000)
        self.color_temp_min.setSingleStep(100)
        self.color_temp_min.setValue(6500)
        self.color_temp_min.setSuffix(" K")
        self.color_temp_min.valueChanged.connect(self._update_live_feedback)
        ModernInput.apply_style(self.color_temp_min)
        
        self.color_temp_max = QSpinBox()
        self.color_temp_max.setRange(1000, 20000)
        self.color_temp_max.setSingleStep(100)
        self.color_temp_max.setValue(6500)
        self.color_temp_max.setSuffix(" K")
        self.color_temp_max.valueChanged.connect(self._update_live_feedback)
        ModernInput.apply_style(self.color_temp_max)
        
        temp_layout.addWidget(self.color_temp_min)
        temp_layout.addWidget(QLabel(t("common.label.to", "至")))
        temp_layout.addWidget(self.color_temp_max)
        
        temp_card.addLayout(temp_layout)
        
        tip_label = QLabel(
            t(
                "color_tone_dialog.tip",
                "提示: 1000~20000。值越大色调越冷，越小越暖 (默认6500K)",
            )
        )
        tip_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 11px; margin-top: 5px;")
        temp_card.addWidget(tip_label)
        
        self.live_feedback_label = QLabel("")
        self.live_feedback_label.setStyleSheet(f"color: {Theme.Warning}; font-size: 12px;")
        self.live_feedback_label.setVisible(False)
        temp_card.addWidget(self.live_feedback_label)
        
        layout.addWidget(temp_card)
        layout.addStretch()
        
        # 按钮行
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
        self.preview_btn.clicked.connect(self.preview)
        button_layout.addWidget(self.preview_btn)
        
        button_layout.addStretch()
        
        self.ok_btn = ModernButton(t("common.btn.ok", "确定"), style=ModernButton.Style.Primary)
        self.ok_btn.clicked.connect(self.on_ok)
        button_layout.addWidget(self.ok_btn)
        
        cancel_btn = ModernButton(t("common.btn.cancel", "取消"), style=ModernButton.Style.Secondary)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self._update_live_feedback()
    
    def preview(self):
        """预览效果"""
        if not self.video_path:
            QMessageBox.warning(
                self,
                t("common.notice", "提示"),
                t("color_tone_dialog.preview.no_video", "没有可预览的视频"),
            )
            return
        if not self._validate_inputs():
            return
        
        # 使用主窗口的预览方法
        if hasattr(self.parent(), '_show_preview_with_config'):
            config = self.get_config()
            self.parent()._show_preview_with_config(
                self.video_path,
                t("color_tone_dialog.preview.title", "色调调整预览"),
                {'color_tone': config},
            )
        else:
            QMessageBox.information(
                self,
                t("common.notice", "提示"),
                t("color_tone_dialog.preview.not_supported", "预览功能已实现，请在主窗口中点击确定后预览"),
            )
    
    def get_config(self):
        """获取配置"""
        return {
            'gamma': self.gamma.value(),
            'red': self.red.value(),
            'green': self.green.value(),
            'blue': self.blue.value(),
            'color_temp_min': self.color_temp_min.value(),
            'color_temp_max': self.color_temp_max.value(),
        }
    
    def set_config(self, config: dict):
        """设置配置（恢复之前的设置）"""
        if not config:
            return
        
        self.gamma.setValue(config.get('gamma', 1.00))
        self.red.setValue(config.get('red', 1.00))
        self.green.setValue(config.get('green', 1.00))
        self.blue.setValue(config.get('blue', 1.00))
        self.color_temp_min.setValue(config.get('color_temp_min', 6500))
        self.color_temp_max.setValue(config.get('color_temp_max', 6500))
        self._update_live_feedback()

    def _validate_inputs(self) -> bool:
        """校验色温区间。"""
        if self.color_temp_min.value() > self.color_temp_max.value():
            QMessageBox.warning(
                self,
                t("dynamic_zoom_dialog.validation.failed.title", "参数校验未通过"),
                t("color_tone_dialog.validation.color_temp", "色温范围无效：最小值不能大于最大值。"),
            )
            self.color_temp_min.setFocus()
            return False
        return True

    def _update_live_feedback(self) -> None:
        """输入时即时反馈色温区间。"""
        has_issue = self.color_temp_min.value() > self.color_temp_max.value()
        self.live_feedback_label.setVisible(has_issue)
        self.live_feedback_label.setText(
            t("color_tone_dialog.validation.color_temp", "色温范围无效：最小值不能大于最大值。")
        )
        self.ok_btn.setEnabled(not has_issue)
        self.preview_btn.setEnabled(not has_issue)

    def on_ok(self):
        """确定按钮"""
        if not self._validate_inputs():
            return
        self.accept()
