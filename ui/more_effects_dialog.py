"""
更多效果对话框
集成现代化UI组件
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QCheckBox, QPushButton, QDoubleSpinBox, QSpinBox,
    QComboBox, QMessageBox, QScrollArea, QWidget, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ui.components import ModernButton, ModernCard, ToggleSwitch, ModernInput, create_section_header, create_param_row, open_color_dialog
from ui.theme import Theme
from ui.i18n import apply_language_to_widget, get_language_manager, t
from utils.enum_codes import (
    BORDER_STYLE_LABELS,
    CURTAIN_DIRECTION_LABELS,
    enum_label,
    normalize_border_style,
    normalize_curtain_direction,
)


class MoreEffectsDialog(QDialog):
    """更多效果对话框"""
    
    def __init__(self, parent=None, video_path=None):
        super().__init__(parent)
        self.video_path = video_path
        self.border_color = QColor("#000000")
        self.grid_color = QColor("#000000")
        self.curtain_color = QColor("#000000")
        self._language_manager = get_language_manager()
        
        self.setWindowTitle(t("more_effects.title", "更多效果设置"))
        self.setMinimumSize(600, 600)
        self.resize(600, 600)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.init_ui()
        self._language_manager.language_changed.connect(self._on_language_changed)
        self._on_language_changed(self._language_manager.language)

    def _refresh_enum_combo_labels(self) -> None:
        lang = self._language_manager.language

        if hasattr(self, "border_style"):
            current = self.border_style.currentData()
            self.border_style.blockSignals(True)
            self.border_style.clear()
            for code in ("all", "vertical", "horizontal", "top", "bottom", "left", "right"):
                self.border_style.addItem(enum_label(BORDER_STYLE_LABELS, code, lang), code)
            index = self.border_style.findData(current or "all")
            self.border_style.setCurrentIndex(index if index >= 0 else 0)
            self.border_style.blockSignals(False)

        if hasattr(self, "curtain_direction"):
            current = self.curtain_direction.currentData()
            self.curtain_direction.blockSignals(True)
            self.curtain_direction.clear()
            for code in (
                "auto",
                "vertical",
                "horizontal",
                "up",
                "down",
                "left",
                "right",
                "auto_close",
                "horizontal_close",
                "vertical_close",
            ):
                self.curtain_direction.addItem(
                    enum_label(CURTAIN_DIRECTION_LABELS, code, lang), code
                )
            index = self.curtain_direction.findData(current or "auto")
            self.curtain_direction.setCurrentIndex(index if index >= 0 else 0)
            self.curtain_direction.blockSignals(False)

    def _on_language_changed(self, _lang: str) -> None:
        self._refresh_enum_combo_labels()
        apply_language_to_widget(self)
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 滚动区域
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
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(0, 0, 10, 0)
        
        # ==== 渐入渐出 ====
        fade_card = ModernCard(t("more_effects.fade.title", "渐入渐出"))
        fade_layout = QHBoxLayout()
        fade_layout.setSpacing(20)
        
        # 渐入
        self.fade_in_check = QCheckBox(t("more_effects.fade.in", "启用渐入"))
        self.fade_in_check.toggled.connect(lambda c: self.fade_in_duration.setEnabled(c))
        
        self.fade_in_duration = QDoubleSpinBox()
        self.fade_in_duration.setRange(0.0, 999.0)
        self.fade_in_duration.setSingleStep(0.1)
        self.fade_in_duration.setValue(1.5)
        self.fade_in_duration.setDecimals(1)
        self.fade_in_duration.setEnabled(False)
        self.fade_in_duration.setSuffix(t("common.suffix.second", " 秒"))
        ModernInput.apply_style(self.fade_in_duration)
        
        fade_in_layout = QVBoxLayout()
        fade_in_layout.addWidget(self.fade_in_check)
        fade_in_layout.addWidget(self.fade_in_duration)
        fade_layout.addLayout(fade_in_layout)
        
        # 渐出
        self.fade_out_check = QCheckBox(t("more_effects.fade.out", "启用渐出"))
        self.fade_out_check.toggled.connect(lambda c: self.fade_out_duration.setEnabled(c))
        
        self.fade_out_duration = QDoubleSpinBox()
        self.fade_out_duration.setRange(0.0, 999.0)
        self.fade_out_duration.setSingleStep(0.1)
        self.fade_out_duration.setValue(1.5)
        self.fade_out_duration.setDecimals(1)
        self.fade_out_duration.setEnabled(False)
        self.fade_out_duration.setSuffix(t("common.suffix.second", " 秒"))
        ModernInput.apply_style(self.fade_out_duration)
        
        fade_out_layout = QVBoxLayout()
        fade_out_layout.addWidget(self.fade_out_check)
        fade_out_layout.addWidget(self.fade_out_duration)
        fade_layout.addLayout(fade_out_layout)
        
        fade_layout.addStretch()
        fade_card.addLayout(fade_layout)
        scroll_layout.addWidget(fade_card)
        
        # ==== 边框 ====
        self.border_switch = ToggleSwitch()
        self.border_switch.toggled.connect(self.on_border_check_changed)
        border_card = ModernCard()
        border_card.addWidget(
            create_section_header(t("more_effects.border.title", "边框设置"), self.border_switch)
        )
        
        border_grid = QGridLayout()
        border_grid.setHorizontalSpacing(15)
        border_grid.setVerticalSpacing(10)
        
        # 颜色
        self.border_color_btn = QPushButton()
        self.border_color_btn.setFixedSize(50, 28)
        self.border_color_btn.setStyleSheet(f"background-color: {self.border_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.border_color_btn.setEnabled(False)
        self.border_color_btn.clicked.connect(self.choose_border_color)
        border_grid.addWidget(
            create_param_row(t("common.label.color", "颜色:"), self.border_color_btn), 0, 0
        )
        
        # 透明度
        self.border_opacity = QDoubleSpinBox()
        self.border_opacity.setRange(0.0, 1.0)
        self.border_opacity.setSingleStep(0.01)
        self.border_opacity.setValue(1.0)
        self.border_opacity.setEnabled(False)
        ModernInput.apply_style(self.border_opacity)
        border_grid.addWidget(
            create_param_row(t("common.label.opacity", "透明度:"), self.border_opacity), 0, 1
        )
        
        # 宽度
        self.border_width = QSpinBox()
        self.border_width.setRange(1, 999)
        self.border_width.setValue(3)
        self.border_width.setEnabled(False)
        self.border_width.setSuffix(" px")
        ModernInput.apply_style(self.border_width)
        border_grid.addWidget(
            create_param_row(t("common.label.width", "宽度:"), self.border_width), 1, 0
        )
        
        # 样式
        self.border_style = QComboBox()
        lang = self._language_manager.language
        for code in ("all", "vertical", "horizontal", "top", "bottom", "left", "right"):
            self.border_style.addItem(enum_label(BORDER_STYLE_LABELS, code, lang), code)
        self.border_style.setEnabled(False)
        ModernInput.apply_style(self.border_style)
        border_grid.addWidget(
            create_param_row(t("common.label.style", "样式:"), self.border_style), 1, 1
        )
        
        border_card.addLayout(border_grid)
        scroll_layout.addWidget(border_card)
        
        # ==== 网格 ====
        self.grid_switch = ToggleSwitch()
        self.grid_switch.toggled.connect(self.on_grid_check_changed)
        grid_card = ModernCard()
        grid_card.addWidget(
            create_section_header(t("more_effects.grid.title", "网格设置"), self.grid_switch)
        )
        
        grid_grid = QGridLayout()
        grid_grid.setHorizontalSpacing(15)
        grid_grid.setVerticalSpacing(10)
        
        # 颜色
        self.grid_color_btn = QPushButton()
        self.grid_color_btn.setFixedSize(50, 28)
        self.grid_color_btn.setStyleSheet(f"background-color: {self.grid_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.grid_color_btn.setEnabled(False)
        self.grid_color_btn.clicked.connect(self.choose_grid_color)
        grid_grid.addWidget(
            create_param_row(t("common.label.color", "颜色:"), self.grid_color_btn), 0, 0
        )
        
        # 透明度
        self.grid_opacity = QDoubleSpinBox()
        self.grid_opacity.setRange(0.0, 1.0)
        self.grid_opacity.setValue(1.0)
        self.grid_opacity.setEnabled(False)
        ModernInput.apply_style(self.grid_opacity)
        grid_grid.addWidget(
            create_param_row(t("common.label.opacity", "透明度:"), self.grid_opacity), 0, 1
        )
        
        # 宽度
        self.grid_width = QSpinBox()
        self.grid_width.setRange(1, 9999)
        self.grid_width.setValue(100)
        self.grid_width.setEnabled(False)
        self.grid_width.setSuffix(" px")
        ModernInput.apply_style(self.grid_width)
        grid_grid.addWidget(
            create_param_row(t("more_effects.grid.cell_width", "单元格宽:"), self.grid_width), 1, 0
        )
        
        # 高度
        self.grid_height = QSpinBox()
        self.grid_height.setRange(1, 9999)
        self.grid_height.setValue(100)
        self.grid_height.setEnabled(False)
        self.grid_height.setSuffix(" px")
        ModernInput.apply_style(self.grid_height)
        grid_grid.addWidget(
            create_param_row(t("more_effects.grid.cell_height", "单元格高:"), self.grid_height), 1, 1
        )
        
        # 线宽
        self.grid_line = QDoubleSpinBox()
        self.grid_line.setRange(0.1, 99.0)
        self.grid_line.setValue(1.0)
        self.grid_line.setEnabled(False)
        self.grid_line.setSuffix(" px")
        ModernInput.apply_style(self.grid_line)
        grid_grid.addWidget(
            create_param_row(t("more_effects.grid.line_width", "线宽:"), self.grid_line), 2, 0
        )
        
        grid_card.addLayout(grid_grid)
        scroll_layout.addWidget(grid_card)
        
        # ==== 延时 ====
        self.delay_switch = ToggleSwitch()
        self.delay_switch.toggled.connect(self.on_delay_check_changed)
        delay_card = ModernCard()
        delay_card.addWidget(
            create_section_header(t("more_effects.delay.title", "延时设置"), self.delay_switch)
        )
        
        delay_layout = QHBoxLayout()
        delay_layout.setSpacing(15)
        
        self.delay_time = QDoubleSpinBox()
        self.delay_time.setRange(0.0, 999.0)
        self.delay_time.setValue(0.0)
        self.delay_time.setEnabled(False)
        self.delay_time.setSuffix(t("common.suffix.second", " 秒"))
        ModernInput.apply_style(self.delay_time)
        
        self.delay_interval = QDoubleSpinBox()
        self.delay_interval.setRange(0.0, 999.0)
        self.delay_interval.setValue(1.0)
        self.delay_interval.setEnabled(False)
        self.delay_interval.setSuffix(t("common.suffix.second", " 秒"))
        ModernInput.apply_style(self.delay_interval)
        
        self.delay_duration = QDoubleSpinBox()
        self.delay_duration.setRange(0.0, 999.0)
        self.delay_duration.setValue(3.0)
        self.delay_duration.setEnabled(False)
        self.delay_duration.setSuffix(t("common.suffix.second", " 秒"))
        ModernInput.apply_style(self.delay_duration)
        
        delay_layout.addWidget(
            create_param_row(t("more_effects.delay.start", "延时开始:"), self.delay_time)
        )
        delay_layout.addWidget(
            create_param_row(t("more_effects.delay.interval", "间隔时间:"), self.delay_interval)
        )
        delay_layout.addWidget(
            create_param_row(t("more_effects.delay.duration", "持续时间:"), self.delay_duration)
        )
        
        delay_card.addLayout(delay_layout)
        scroll_layout.addWidget(delay_card)
        
        # ==== 开幕动画 ====
        self.curtain_switch = ToggleSwitch()
        self.curtain_switch.toggled.connect(self.on_curtain_check_changed)
        curtain_card = ModernCard()
        curtain_card.addWidget(
            create_section_header(t("more_effects.curtain.title", "开幕动画"), self.curtain_switch)
        )
        
        curtain_grid = QGridLayout()
        curtain_grid.setHorizontalSpacing(15)
        curtain_grid.setVerticalSpacing(10)
        
        self.curtain_color_btn = QPushButton()
        self.curtain_color_btn.setFixedSize(50, 28)
        self.curtain_color_btn.setStyleSheet(f"background-color: {self.curtain_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.curtain_color_btn.setEnabled(False)
        self.curtain_color_btn.clicked.connect(self.choose_curtain_color)
        curtain_grid.addWidget(
            create_param_row(t("common.label.color", "颜色:"), self.curtain_color_btn), 0, 0
        )
        
        self.curtain_direction = QComboBox()
        for code in (
            "auto",
            "vertical",
            "horizontal",
            "up",
            "down",
            "left",
            "right",
            "auto_close",
            "horizontal_close",
            "vertical_close",
        ):
            self.curtain_direction.addItem(
                enum_label(CURTAIN_DIRECTION_LABELS, code, lang), code
            )
        self.curtain_direction.setEnabled(False)
        ModernInput.apply_style(self.curtain_direction)
        curtain_grid.addWidget(
            create_param_row(t("common.label.direction", "方向:"), self.curtain_direction), 0, 1
        )
        
        self.curtain_duration = QDoubleSpinBox()
        self.curtain_duration.setRange(0.0, 999.0)
        self.curtain_duration.setValue(2.0)
        self.curtain_duration.setEnabled(False)
        self.curtain_duration.setSuffix(t("common.suffix.second", " 秒"))
        ModernInput.apply_style(self.curtain_duration)
        curtain_grid.addWidget(
            create_param_row(t("common.label.duration", "时长:"), self.curtain_duration), 1, 0
        )
        
        self.curtain_video_check = QCheckBox(
            t("more_effects.curtain.video_only", "仅对视频生效")
        )
        self.curtain_video_check.setEnabled(False)
        curtain_grid.addWidget(self.curtain_video_check, 1, 1)
        
        curtain_card.addLayout(curtain_grid)
        
        tip_label = QLabel(
            t(
                "more_effects.curtain.tip",
                "提示: 视频开始时以设定颜色与方向做开幕动画。方向为[自动]时，横屏左右开，竖屏上下开。时长为0则持续至视频结束。",
            )
        )
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 11px; margin-top: 5px;")
        curtain_card.addWidget(tip_label)
        
        scroll_layout.addWidget(curtain_card)
        
        # ==== 其他效果 ====
        other_card = ModernCard(t("more_effects.image.title", "图像处理"))
        other_grid = QGridLayout()
        other_grid.setHorizontalSpacing(15)
        other_grid.setVerticalSpacing(10)
        
        # 蒙版倒置
        self.mask_invert_check = QCheckBox(t("more_effects.image.mask_invert", "蒙版倒置"))
        self.mask_invert_check.toggled.connect(lambda c: self.mask_invert_value.setEnabled(c))
        other_grid.addWidget(self.mask_invert_check, 0, 0)
        
        self.mask_invert_value = QDoubleSpinBox()
        self.mask_invert_value.setRange(0.0, 1.0)
        self.mask_invert_value.setSingleStep(0.01)
        self.mask_invert_value.setValue(0.05)
        self.mask_invert_value.setEnabled(False)
        ModernInput.apply_style(self.mask_invert_value)
        other_grid.addWidget(
            create_param_row(t("common.label.threshold", "阈值:"), self.mask_invert_value), 0, 1
        )
        
        # 虚化
        self.blur_check = QCheckBox(t("more_effects.image.blur", "虚化/模糊"))
        self.blur_check.toggled.connect(lambda c: self.blur_value.setEnabled(c))
        other_grid.addWidget(self.blur_check, 1, 0)
        
        self.blur_value = QDoubleSpinBox()
        self.blur_value.setRange(0.0, 10.0)
        self.blur_value.setValue(0.5)
        self.blur_value.setEnabled(False)
        ModernInput.apply_style(self.blur_value)
        other_grid.addWidget(
            create_param_row(t("common.label.level", "程度:"), self.blur_value), 1, 1
        )
        
        # 马赛克
        self.mosaic_check = QCheckBox(t("more_effects.image.mosaic", "马赛克"))
        self.mosaic_check.toggled.connect(lambda c: self.mosaic_size.setEnabled(c))
        other_grid.addWidget(self.mosaic_check, 2, 0)
        
        self.mosaic_size = QSpinBox()
        self.mosaic_size.setRange(1, 999)
        self.mosaic_size.setValue(24)
        self.mosaic_size.setEnabled(False)
        self.mosaic_size.setSuffix(" px")
        ModernInput.apply_style(self.mosaic_size)
        other_grid.addWidget(
            create_param_row(t("common.label.size", "大小:"), self.mosaic_size), 2, 1
        )
        
        other_card.addLayout(other_grid)
        scroll_layout.addWidget(other_card)
        
        # ==== 特效滤镜 ====
        effects_card = ModernCard(t("more_effects.effects.title", "特效滤镜"))
        effects_layout = QGridLayout()
        effects_layout.setSpacing(10)
        
        self.glow_check = QCheckBox(t("more_effects.effects.glow", "光晕 (Glow)"))
        self.bw_check = QCheckBox(t("more_effects.effects.bw", "黑白 (Black & White)"))
        self.negative_check = QCheckBox(
            t("more_effects.effects.negative", "底片 (Negative)")
        )
        self.cartoon_check = QCheckBox(t("more_effects.effects.cartoon", "卡通 (Cartoon)"))
        self.emboss_check = QCheckBox(t("more_effects.effects.emboss", "浮雕 (Emboss)"))
        self.smart_blur_check = QCheckBox(
            t("more_effects.effects.smart_blur", "智能模糊 (Smart Blur)")
        )
        
        effects_layout.addWidget(self.glow_check, 0, 0)
        effects_layout.addWidget(self.bw_check, 0, 1)
        effects_layout.addWidget(self.negative_check, 0, 2)
        effects_layout.addWidget(self.cartoon_check, 1, 0)
        effects_layout.addWidget(self.emboss_check, 1, 1)
        effects_layout.addWidget(self.smart_blur_check, 1, 2)
        
        effects_card.addLayout(effects_layout)
        scroll_layout.addWidget(effects_card)
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        reset_btn = ModernButton(t("common.btn.reset", "重置"), ModernButton.Style.Secondary)
        reset_btn.clicked.connect(self.reset)
        button_layout.addWidget(reset_btn)
        
        self.preview_btn = ModernButton(
            t("common.btn.preview", "预览效果"),
            style=ModernButton.Style.Outline,
            icon_name="eye",
        )
        self.preview_btn.clicked.connect(self.preview)
        button_layout.addWidget(self.preview_btn)
        
        button_layout.addStretch()
        
        ok_btn = ModernButton(t("common.btn.ok", "确定"), ModernButton.Style.Primary)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = ModernButton(t("common.btn.cancel", "取消"), ModernButton.Style.Secondary)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def on_border_check_changed(self, checked: bool):
        """边框复选框状态改变"""
        self.border_color_btn.setEnabled(checked)
        self.border_opacity.setEnabled(checked)
        self.border_width.setEnabled(checked)
        self.border_style.setEnabled(checked)
    
    def on_grid_check_changed(self, checked: bool):
        """网格复选框状态改变"""
        self.grid_color_btn.setEnabled(checked)
        self.grid_opacity.setEnabled(checked)
        self.grid_width.setEnabled(checked)
        self.grid_height.setEnabled(checked)
        self.grid_line.setEnabled(checked)
    
    def on_delay_check_changed(self, checked: bool):
        """延时复选框状态改变"""
        self.delay_time.setEnabled(checked)
        self.delay_interval.setEnabled(checked)
        self.delay_duration.setEnabled(checked)
    
    def on_curtain_check_changed(self, checked: bool):
        """开幕动画复选框状态改变"""
        self.curtain_color_btn.setEnabled(checked)
        self.curtain_direction.setEnabled(checked)
        self.curtain_duration.setEnabled(checked)
        self.curtain_video_check.setEnabled(checked)
    
    def choose_border_color(self):
        """选择边框颜色"""
        color = open_color_dialog(
            self.border_color, self, t("more_effects.color.border", "选择边框颜色")
        )
        if color:
            self.border_color = color
            self.border_color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
    
    def choose_grid_color(self):
        """选择网格颜色"""
        color = open_color_dialog(
            self.grid_color, self, t("more_effects.color.grid", "选择网格颜色")
        )
        if color:
            self.grid_color = color
            self.grid_color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
    
    def choose_curtain_color(self):
        """选择开幕动画颜色"""
        color = open_color_dialog(
            self.curtain_color, self, t("more_effects.color.curtain", "选择开幕动画颜色")
        )
        if color:
            self.curtain_color = color
            self.curtain_color_btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
    
    def reset(self):
        """重置所有参数"""
        self.fade_in_check.setChecked(False)
        self.fade_in_duration.setValue(1.5)
        self.fade_out_check.setChecked(False)
        self.fade_out_duration.setValue(1.5)
        
        self.border_switch.setChecked(False)
        self.border_color = QColor("#000000")
        self.border_color_btn.setStyleSheet(f"background-color: {self.border_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.border_opacity.setValue(1.0)
        self.border_width.setValue(3)
        idx = self.border_style.findData("all")
        if idx >= 0:
            self.border_style.setCurrentIndex(idx)
        
        self.grid_switch.setChecked(False)
        self.grid_color = QColor("#000000")
        self.grid_color_btn.setStyleSheet(f"background-color: {self.grid_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.grid_opacity.setValue(1.0)
        self.grid_width.setValue(100)
        self.grid_height.setValue(100)
        self.grid_line.setValue(1.0)
        
        self.delay_switch.setChecked(False)
        self.delay_time.setValue(0.0)
        self.delay_interval.setValue(1.0)
        self.delay_duration.setValue(3.0)
        
        self.curtain_switch.setChecked(False)
        self.curtain_color = QColor("#000000")
        self.curtain_color_btn.setStyleSheet(f"background-color: {self.curtain_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        idx = self.curtain_direction.findData("auto")
        if idx >= 0:
            self.curtain_direction.setCurrentIndex(idx)
        self.curtain_duration.setValue(2.0)
        self.curtain_video_check.setChecked(False)
        
        self.mask_invert_check.setChecked(False)
        self.mask_invert_value.setValue(0.05)
        self.blur_check.setChecked(False)
        self.blur_value.setValue(0.5)
        self.mosaic_check.setChecked(False)
        self.mosaic_size.setValue(24)
        
        self.glow_check.setChecked(False)
        self.bw_check.setChecked(False)
        self.negative_check.setChecked(False)
        self.cartoon_check.setChecked(False)
        self.emboss_check.setChecked(False)
        self.smart_blur_check.setChecked(False)
    
    def preview(self):
        """预览效果"""
        if not self.video_path:
            QMessageBox.warning(
                self,
                t("common.notice", "提示"),
                t("more_effects.preview.no_video", "没有可预览的视频"),
            )
            return
        
        # 使用主窗口的预览方法
        if hasattr(self.parent(), '_show_preview_with_config'):
            config = self.get_config()
            self.parent()._show_preview_with_config(
                self.video_path,
                t("more_effects.preview.title", "更多效果预览"),
                {'more_effects': config},
            )
        else:
            QMessageBox.information(
                self,
                t("common.notice", "提示"),
                t("more_effects.preview.info", "预览功能已实现，请在主窗口中点击确定后预览"),
            )
    
    def get_config(self):
        """获取配置"""
        return {
            # 渐入渐出
            'fade_in_enabled': self.fade_in_check.isChecked(),
            'fade_in_duration': self.fade_in_duration.value(),
            'fade_out_enabled': self.fade_out_check.isChecked(),
            'fade_out_duration': self.fade_out_duration.value(),
            
            # 边框
            'border_enabled': self.border_switch.isChecked(),
            'border_color': self.border_color.name(),
            'border_opacity': self.border_opacity.value(),
            'border_width': self.border_width.value(),
            'border_style': self.border_style.currentData() or "all",
            
            # 网格
            'grid_enabled': self.grid_switch.isChecked(),
            'grid_color': self.grid_color.name(),
            'grid_opacity': self.grid_opacity.value(),
            'grid_width': self.grid_width.value(),
            'grid_height': self.grid_height.value(),
            'grid_line': self.grid_line.value(),
            
            # 延时
            'delay_enabled': self.delay_switch.isChecked(),
            'delay_time': self.delay_time.value(),
            'delay_interval': self.delay_interval.value(),
            'delay_duration': self.delay_duration.value(),
            
            # 幕布
            'curtain_enabled': self.curtain_switch.isChecked(),
            'curtain_color': self.curtain_color.name(),
            'curtain_direction': self.curtain_direction.currentData() or "auto",
            'curtain_duration': self.curtain_duration.value(),
            'curtain_video': self.curtain_video_check.isChecked(),
            
            # 蒙版反转
            'mask_invert_enabled': self.mask_invert_check.isChecked(),
            'mask_invert_value': self.mask_invert_value.value(),
            
            # 虚化
            'blur_enabled': self.blur_check.isChecked(),
            'blur_value': self.blur_value.value(),
            
            # 马赛克
            'mosaic_enabled': self.mosaic_check.isChecked(),
            'mosaic_size': self.mosaic_size.value(),
            
            # 其他效果
            'glow_enabled': self.glow_check.isChecked(),
            'bw_enabled': self.bw_check.isChecked(),
            'negative_enabled': self.negative_check.isChecked(),
            'cartoon_enabled': self.cartoon_check.isChecked(),
            'emboss_enabled': self.emboss_check.isChecked(),
            'smart_blur_enabled': self.smart_blur_check.isChecked(),
        }
    
    def set_config(self, config: dict):
        """设置配置（恢复之前的设置）"""
        if not config:
            return
        
        # 渐入渐出
        self.fade_in_check.setChecked(config.get('fade_in_enabled', config.get('fade_in', False)))
        self.fade_in_duration.setValue(config.get('fade_in_duration', 1.5))
        self.fade_out_check.setChecked(config.get('fade_out_enabled', config.get('fade_out', False)))
        self.fade_out_duration.setValue(config.get('fade_out_duration', 1.5))
        
        # 边框
        self.border_switch.setChecked(config.get('border_enabled', config.get('border', False)))
        self.border_color = QColor(config.get('border_color', '#FFFFFF'))
        self.border_color_btn.setStyleSheet(f"background-color: {self.border_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.border_opacity.setValue(config.get('border_opacity', 1.0))
        self.border_width.setValue(config.get('border_width', 3))
        border_style = normalize_border_style(config.get('border_style', 'all'))
        index = self.border_style.findData(border_style)
        if index >= 0:
            self.border_style.setCurrentIndex(index)
        
        # 网格
        self.grid_switch.setChecked(config.get('grid_enabled', config.get('grid', False)))
        self.grid_color = QColor(config.get('grid_color', '#FFFFFF'))
        self.grid_color_btn.setStyleSheet(f"background-color: {self.grid_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.grid_opacity.setValue(config.get('grid_opacity', 0.5))
        self.grid_width.setValue(config.get('grid_width', 100))
        self.grid_height.setValue(config.get('grid_height', 100))
        self.grid_line.setValue(config.get('grid_line', 1.0))
        
        # 延时
        self.delay_switch.setChecked(config.get('delay_enabled', config.get('delay', False)))
        self.delay_time.setValue(config.get('delay_time', 3.0))
        self.delay_interval.setValue(config.get('delay_interval', 0.1))
        self.delay_duration.setValue(config.get('delay_duration', 1.0))
        
        # 幕布
        self.curtain_switch.setChecked(config.get('curtain_enabled', config.get('curtain', False)))
        self.curtain_color = QColor(config.get('curtain_color', '#000000'))
        self.curtain_color_btn.setStyleSheet(f"background-color: {self.curtain_color.name()}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        curtain_direction = normalize_curtain_direction(config.get('curtain_direction', 'auto'))
        index = self.curtain_direction.findData(curtain_direction)
        if index >= 0:
            self.curtain_direction.setCurrentIndex(index)
        self.curtain_duration.setValue(config.get('curtain_duration', 2.0))
        self.curtain_video_check.setChecked(config.get('curtain_video', False))
        
        # 其他效果
        self.mask_invert_check.setChecked(config.get('mask_invert_enabled', config.get('mask_invert', False)))
        self.mask_invert_value.setValue(config.get('mask_invert_value', 0.5))
        self.blur_check.setChecked(config.get('blur_enabled', config.get('blur', False)))
        self.blur_value.setValue(config.get('blur_value', 0.5))
        self.mosaic_check.setChecked(config.get('mosaic_enabled', config.get('mosaic', False)))
        self.mosaic_size.setValue(config.get('mosaic_size', 24))
        self.glow_check.setChecked(config.get('glow_enabled', config.get('glow', False)))
        self.bw_check.setChecked(config.get('bw_enabled', config.get('bw', False)))
        self.negative_check.setChecked(config.get('negative_enabled', config.get('negative', False)))
        self.cartoon_check.setChecked(config.get('cartoon_enabled', config.get('cartoon', False)))
        self.emboss_check.setChecked(config.get('emboss_enabled', config.get('emboss', False)))
        self.smart_blur_check.setChecked(config.get('smart_blur_enabled', config.get('smart_blur', False)))
