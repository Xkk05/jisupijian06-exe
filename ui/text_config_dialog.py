"""
文本配置对话框
集成现代化UI组件
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QRadioButton, QSpinBox, QDoubleSpinBox, QPushButton, QLabel,
    QComboBox, QLineEdit, QButtonGroup, QTextEdit,
    QWidget, QScrollArea, QFileDialog, QMessageBox, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from typing import Dict, Any, Optional
import os
from ui.components import ModernButton, ModernCard, ToggleSwitch, ModernInput, create_section_header, create_param_row, open_color_dialog
from ui.theme import Theme
from ui.i18n import apply_language_to_widget, get_language_manager
from utils.enum_codes import (
    BG_STYLE_LABELS,
    SCROLL_DIRECTION_LABELS,
    TEXT_FILTER_ACTION_LABELS,
    TEXT_FILTER_POSITION_LABELS,
    TEXT_POSITION_LABELS,
    TEXT_SOURCE_MODE_LABELS,
    enum_label,
    normalize_bg_style,
    normalize_scroll_direction,
    normalize_text_filter_action,
    normalize_text_filter_position,
    normalize_text_position,
    normalize_text_source_mode,
)


def _ts(text: str) -> str:
    return get_language_manager().translate_source_text(text)


class TextConfigDialog(QDialog):
    """文本配置对话框"""
    
    def __init__(self, parent=None, track_num: int = 1, initial_config: Optional[Dict] = None):
        super().__init__(parent)
        self.track_num = track_num
        self.config = initial_config or {}
        self._language_manager = get_language_manager()
        
        self.setWindowTitle(_ts(f"文字设置 - 文本{track_num}"))
        self.setModal(True)
        self.setMinimumWidth(800)
        self.setMinimumHeight(650)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.init_ui()
        self.load_config()
        self._language_manager.language_changed.connect(self._on_language_changed)
        self._on_language_changed(self._language_manager.language)

    def _refresh_enum_combo_labels(self) -> None:
        lang = self._language_manager.language

        combo_specs = [
            ("filter_action", ("keep", "remove"), TEXT_FILTER_ACTION_LABELS, "keep"),
            ("filter_position", ("before", "after", "between"), TEXT_FILTER_POSITION_LABELS, "before"),
            (
                "position",
                (
                    "top",
                    "bottom",
                    "left",
                    "right",
                    "top_left",
                    "top_right",
                    "bottom_left",
                    "bottom_right",
                    "center",
                    "random",
                ),
                TEXT_POSITION_LABELS,
                "center",
            ),
            ("bg_style", ("default", "fill"), BG_STYLE_LABELS, "default"),
            ("scroll_direction", ("right", "left", "up", "down", "random"), SCROLL_DIRECTION_LABELS, "right"),
        ]

        for combo_name, codes, labels, fallback in combo_specs:
            combo = getattr(self, combo_name, None)
            if combo is None:
                continue
            current = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            for code in codes:
                combo.addItem(enum_label(labels, code, lang), code)
            index = combo.findData(current or fallback)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def _on_language_changed(self, _lang: str) -> None:
        self._refresh_enum_combo_labels()
        apply_language_to_widget(self)
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("""
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
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #F8FAFC;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(0, 0, 10, 0)
        
        # 1. 文本来源模式
        content_layout.addWidget(self.create_source_mode_group())
        
        # 2. 位置与边距设置
        content_layout.addWidget(self.create_position_group())
        
        # 3. 字体样式设置
        content_layout.addWidget(self.create_font_group())
        
        # 4. 阴影与描边设置
        content_layout.addWidget(self.create_shadow_stroke_group())
        
        # 5. 背景样式设置
        content_layout.addWidget(self.create_background_group())
        
        # 6. 滚动动态设置
        content_layout.addWidget(self.create_scroll_group())
        
        # 7. 显示时序设置
        content_layout.addWidget(self.create_timing_group())
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        button_layout.addStretch()
        
        preview_btn = ModernButton(_ts("预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
        preview_btn.clicked.connect(self.on_preview)
        button_layout.addWidget(preview_btn)
        
        ok_btn = ModernButton(_ts("确定"), ModernButton.Style.Primary)
        ok_btn.clicked.connect(self.on_ok)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = ModernButton(_ts("取消"), ModernButton.Style.Secondary)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
    
    def create_source_mode_group(self) -> ModernCard:
        """创建文本来源模式分组"""
        card = ModernCard(_ts("文本来源模式"))
        
        # 单选按钮组
        self.mode_group = QButtonGroup()
        
        # 1. 文件名模式
        filename_layout = QHBoxLayout()
        self.filename_radio = QRadioButton(_ts("文件名模式"))
        self.filename_radio.toggled.connect(self.on_mode_changed)
        self.mode_group.addButton(self.filename_radio, 0)
        filename_layout.addWidget(self.filename_radio)
        filename_layout.addStretch()
        card.addLayout(filename_layout)
        
        # 文件名模式参数
        self.filename_params = QWidget()
        filename_params_layout = QVBoxLayout(self.filename_params)
        filename_params_layout.setContentsMargins(30, 8, 0, 8)
        filename_params_layout.setSpacing(12)
        
        # 断行配置
        break_layout = QHBoxLayout()
        break_layout.setSpacing(10)
        self.break_by_punct_check = QCheckBox(_ts("以标点符号做断行"))
        self.break_by_punct_check.toggled.connect(self.on_break_punct_changed)
        break_layout.addWidget(self.break_by_punct_check)
        
        break_layout.addWidget(QLabel(_ts("符号:")))
        self.punct_symbols = QLineEdit("。；：？！")
        self.punct_symbols.setPlaceholderText(_ts("请输入用于断行的标点"))
        self.punct_symbols.setMinimumWidth(120)
        self.punct_symbols.setMaximumWidth(150)
        self.punct_symbols.setEnabled(False)
        self.punct_symbols.textChanged.connect(lambda _text: self._update_source_live_feedback())
        ModernInput.apply_style(self.punct_symbols)
        break_layout.addWidget(self.punct_symbols)
        
        self.include_punct_check = QCheckBox(_ts("包括标点"))
        self.include_punct_check.setEnabled(False)
        break_layout.addWidget(self.include_punct_check)
        break_layout.addStretch()
        filename_params_layout.addLayout(break_layout)
        
        # 内容筛选
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        self.filter_action = QComboBox()
        lang = self._language_manager.language
        for code in ("keep", "remove"):
            self.filter_action.addItem(
                enum_label(TEXT_FILTER_ACTION_LABELS, code, lang), code
            )
        self.filter_action.setMinimumWidth(80)
        ModernInput.apply_style(self.filter_action)
        filter_layout.addWidget(self.filter_action)
        
        self.filter_keyword = QLineEdit()
        self.filter_keyword.setPlaceholderText(_ts("关键词"))
        self.filter_keyword.setMinimumWidth(120)
        self.filter_keyword.setMaximumWidth(150)
        ModernInput.apply_style(self.filter_keyword)
        filter_layout.addWidget(self.filter_keyword)
        
        filter_layout.addWidget(QLabel(_ts("及之")))

        self.filter_position = QComboBox()
        for code in ("before", "after", "between"):
            self.filter_position.addItem(
                enum_label(TEXT_FILTER_POSITION_LABELS, code, lang), code
            )
        self.filter_position.setMinimumWidth(60)
        ModernInput.apply_style(self.filter_position)
        filter_layout.addWidget(self.filter_position)
        
        filter_layout.addWidget(QLabel(_ts("内容")))
        filter_layout.addStretch()
        filename_params_layout.addLayout(filter_layout)
        
        card.addWidget(self.filename_params)
        self.filename_params.setEnabled(False)
        
        # 2. 文件夹模式
        folder_layout = QHBoxLayout()
        self.folder_radio = QRadioButton(_ts("文件夹模式"))
        self.folder_radio.toggled.connect(self.on_mode_changed)
        self.mode_group.addButton(self.folder_radio, 1)
        folder_layout.addWidget(self.folder_radio)
        folder_layout.addStretch()
        card.addLayout(folder_layout)
        
        # 文件夹模式参数
        self.folder_params = QWidget()
        folder_params_layout = QGridLayout(self.folder_params)
        folder_params_layout.setContentsMargins(30, 8, 0, 8)
        folder_params_layout.setHorizontalSpacing(10)
        folder_params_layout.setVerticalSpacing(10)
        
        # 第一行：文件夹路径 + 浏览按钮
        folder_params_layout.addWidget(QLabel(_ts("文件夹:")), 0, 0)
        self.folder_path = QLineEdit()
        self.folder_path.setReadOnly(True)
        self.folder_path.setPlaceholderText(_ts("未选择"))
        self.folder_path.setMinimumWidth(200)
        self.folder_path.textChanged.connect(lambda _text: self._update_source_live_feedback())
        ModernInput.apply_style(self.folder_path)
        folder_params_layout.addWidget(self.folder_path, 0, 1)
        
        self.folder_browse_btn = ModernButton(_ts("浏览"), ModernButton.Style.Secondary)
        self.folder_browse_btn.clicked.connect(self.on_browse_folder)
        self.folder_browse_btn.setFixedHeight(32)
        folder_params_layout.addWidget(self.folder_browse_btn, 0, 2)
        
        # 第二行：复选框
        options_layout = QHBoxLayout()
        options_layout.setSpacing(15)
        self.folder_random_check = QCheckBox(_ts("随机应用"))
        options_layout.addWidget(self.folder_random_check)
        
        self.single_line_check = QCheckBox(_ts("单行抽取"))
        self.single_line_check.toggled.connect(self.on_single_line_changed)
        options_layout.addWidget(self.single_line_check)
        
        self.space_break_check = QCheckBox(_ts("空格换行"))
        self.space_break_check.setEnabled(False)
        options_layout.addWidget(self.space_break_check)
        options_layout.addStretch()
        
        folder_params_layout.addLayout(options_layout, 1, 0, 1, 3)
        
        card.addWidget(self.folder_params)
        self.folder_params.setEnabled(False)
        
        # 3. 文本模式
        text_layout = QHBoxLayout()
        self.text_radio = QRadioButton(_ts("文本模式"))
        self.text_radio.toggled.connect(self.on_mode_changed)
        self.mode_group.addButton(self.text_radio, 2)
        text_layout.addWidget(self.text_radio)
        text_layout.addStretch()
        card.addLayout(text_layout)
        
        # 文本模式参数
        self.text_params = QWidget()
        text_params_layout = QHBoxLayout(self.text_params)
        text_params_layout.setContentsMargins(30, 8, 0, 8)
        text_params_layout.setSpacing(10)
        
        self.text_content = QTextEdit()
        self.text_content.setPlaceholderText(_ts("输入文本内容..."))
        self.text_content.setMaximumHeight(80)
        self.text_content.textChanged.connect(self._update_source_live_feedback)
        ModernInput.apply_style(self.text_content)
        text_params_layout.addWidget(self.text_content)
        
        
        card.addWidget(self.text_params)
        self.text_params.setEnabled(False)
        
        self.source_feedback_label = QLabel("")
        self.source_feedback_label.setStyleSheet(f"color: {Theme.Warning}; font-size: 12px;")
        self.source_feedback_label.setVisible(False)
        card.addWidget(self.source_feedback_label)

        # 默认选中文本模式（放在反馈标签创建后，避免初始化时信号触发访问未定义属性）
        self.text_radio.setChecked(True)
        
        return card
    
    def create_position_group(self) -> ModernCard:
        """创建位置与边距设置分组"""
        card = ModernCard(_ts("位置与边距设置"))
        layout = QHBoxLayout()
        layout.setSpacing(12)
        lang = self._language_manager.language
        
        self.position = QComboBox()
        for code in (
            "top",
            "bottom",
            "left",
            "right",
            "top_left",
            "top_right",
            "bottom_left",
            "bottom_right",
            "center",
            "random",
        ):
            self.position.addItem(enum_label(TEXT_POSITION_LABELS, code, lang), code)
        self.position.setCurrentIndex(self.position.findData("center"))
        self.position.setMinimumWidth(80)
        ModernInput.apply_style(self.position)
        layout.addWidget(create_param_row("位置:", self.position))
        
        self.margin_x = QSpinBox()
        self.margin_x.setRange(0, 9999)
        self.margin_x.setValue(0)
        self.margin_x.setMinimumWidth(70)
        ModernInput.apply_style(self.margin_x)
        layout.addWidget(create_param_row("X边距:", self.margin_x))
        
        # 单位切换
        self.unit_btn = ModernButton("p", ModernButton.Style.Outline)
        self.unit_btn.setFixedWidth(32)
        self.unit_btn.setFixedHeight(32)
        self.unit_btn.setToolTip(_ts("点击切换单位（p=像素，%=百分比）"))
        self.unit_btn.clicked.connect(self.toggle_unit)
        layout.addWidget(self.unit_btn)
        
        self.margin_y = QSpinBox()
        self.margin_y.setRange(0, 9999)
        self.margin_y.setValue(0)
        self.margin_y.setMinimumWidth(70)
        ModernInput.apply_style(self.margin_y)
        layout.addWidget(create_param_row("Y边距:", self.margin_y))
        
        self.line_spacing = QSpinBox()
        self.line_spacing.setRange(1, 999)
        self.line_spacing.setValue(10)
        self.line_spacing.setMinimumWidth(70)
        ModernInput.apply_style(self.line_spacing)
        layout.addWidget(create_param_row("行距:", self.line_spacing))
        
        layout.addStretch()
        card.addLayout(layout)
        return card
    
    def create_font_group(self) -> ModernCard:
        """创建字体样式设置分组"""
        self.font_switch = ToggleSwitch()
        self.font_switch.setChecked(True)
        self.font_switch.toggled.connect(self.on_font_check_changed)
        
        card = ModernCard()
        card.addWidget(create_section_header("字体样式设置", self.font_switch))
        
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        self.font_family = QComboBox()
        self.font_family.addItems(
            [_ts("微软雅黑"), _ts("宋体"), _ts("黑体"), _ts("楷体"), _ts("仿宋"), _ts("等线"), "Arial"]
        )
        self.font_family.setMinimumWidth(100)
        ModernInput.apply_style(self.font_family)
        layout.addWidget(self.font_family)
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 100)
        self.font_size.setValue(24)
        self.font_size.setMinimumWidth(70)
        ModernInput.apply_style(self.font_size)
        layout.addWidget(create_param_row("字号:", self.font_size))
        
        self.font_color_btn = QPushButton()
        self.font_color_btn.setFixedSize(50, 32)
        self.font_color = "#000000"
        self.font_color_btn.setStyleSheet(f"background-color: {self.font_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.font_color_btn.clicked.connect(self.on_choose_font_color)
        layout.addWidget(create_param_row("颜色:", self.font_color_btn))
        
        self.font_opacity = QDoubleSpinBox()
        self.font_opacity.setRange(0.1, 1.0)
        self.font_opacity.setSingleStep(0.1)
        self.font_opacity.setValue(0.80)
        self.font_opacity.setMinimumWidth(70)
        ModernInput.apply_style(self.font_opacity)
        layout.addWidget(create_param_row("透明度:", self.font_opacity))
        
        layout.addStretch()
        card.addLayout(layout)
        return card
    
    def create_shadow_stroke_group(self) -> ModernCard:
        """创建阴影与描边设置分组"""
        card = ModernCard(_ts("装饰设置"))
        
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # 阴影
        shadow_layout = QHBoxLayout()
        shadow_layout.setSpacing(10)
        self.shadow_check = QCheckBox(_ts("启用阴影"))
        self.shadow_check.toggled.connect(self.on_shadow_check_changed)
        shadow_layout.addWidget(self.shadow_check)
        
        self.shadow_color_btn = QPushButton()
        self.shadow_color_btn.setFixedSize(40, 28)
        self.shadow_color = "#000000"
        self.shadow_color_btn.setStyleSheet(f"background-color: {self.shadow_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.shadow_color_btn.clicked.connect(self.on_choose_shadow_color)
        self.shadow_color_btn.setEnabled(False)
        shadow_layout.addWidget(self.shadow_color_btn)
        
        self.shadow_depth = QSpinBox()
        self.shadow_depth.setRange(1, 50)
        self.shadow_depth.setValue(2)
        self.shadow_depth.setMinimumWidth(60)
        self.shadow_depth.setEnabled(False)
        ModernInput.apply_style(self.shadow_depth)
        shadow_layout.addWidget(create_param_row("深度:", self.shadow_depth))
        
        layout.addLayout(shadow_layout)
        
        # 描边
        stroke_layout = QHBoxLayout()
        stroke_layout.setSpacing(10)
        self.stroke_check = QCheckBox(_ts("启用描边"))
        self.stroke_check.toggled.connect(self.on_stroke_check_changed)
        stroke_layout.addWidget(self.stroke_check)
        
        self.stroke_color_btn = QPushButton()
        self.stroke_color_btn.setFixedSize(40, 28)
        self.stroke_color = "#FFFFFF"
        self.stroke_color_btn.setStyleSheet(f"background-color: {self.stroke_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.stroke_color_btn.clicked.connect(self.on_choose_stroke_color)
        self.stroke_color_btn.setEnabled(False)
        stroke_layout.addWidget(self.stroke_color_btn)
        
        self.stroke_width = QSpinBox()
        self.stroke_width.setRange(1, 20)
        self.stroke_width.setValue(1)
        self.stroke_width.setMinimumWidth(60)
        self.stroke_width.setEnabled(False)
        ModernInput.apply_style(self.stroke_width)
        stroke_layout.addWidget(create_param_row("宽度:", self.stroke_width))
        
        layout.addLayout(stroke_layout)
        layout.addStretch()
        
        card.addLayout(layout)
        return card
    
    def create_background_group(self) -> ModernCard:
        """创建背景样式设置分组"""
        self.bg_switch = ToggleSwitch()
        self.bg_switch.toggled.connect(self.on_bg_check_changed)
        
        card = ModernCard()
        card.addWidget(create_section_header("背景样式设置", self.bg_switch))
        
        layout = QHBoxLayout()
        layout.setSpacing(12)
        lang = self._language_manager.language
        
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(50, 32)
        self.bg_color = "#808080"
        self.bg_color_btn.setStyleSheet(f"background-color: {self.bg_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.bg_color_btn.clicked.connect(self.on_choose_bg_color)
        self.bg_color_btn.setEnabled(False)
        layout.addWidget(create_param_row("颜色:", self.bg_color_btn))
        
        self.bg_opacity = QDoubleSpinBox()
        self.bg_opacity.setRange(0.1, 1.0)
        self.bg_opacity.setSingleStep(0.1)
        self.bg_opacity.setValue(0.8)
        self.bg_opacity.setMinimumWidth(70)
        self.bg_opacity.setEnabled(False)
        ModernInput.apply_style(self.bg_opacity)
        layout.addWidget(create_param_row("透明度:", self.bg_opacity))
        
        self.bg_style = QComboBox()
        for code in ("default", "fill"):
            self.bg_style.addItem(enum_label(BG_STYLE_LABELS, code, lang), code)
        self.bg_style.currentTextChanged.connect(self.on_bg_style_changed)
        self.bg_style.setMinimumWidth(80)
        self.bg_style.setEnabled(False)
        ModernInput.apply_style(self.bg_style)
        layout.addWidget(create_param_row("样式:", self.bg_style))
        
        self.bg_fit_check = QCheckBox(_ts("贴合"))
        self.bg_fit_check.setEnabled(False)
        layout.addWidget(self.bg_fit_check)
        
        self.bg_padding = QSpinBox()
        self.bg_padding.setRange(-20, 50)
        self.bg_padding.setValue(5)
        self.bg_padding.setMinimumWidth(70)
        self.bg_padding.setEnabled(False)
        ModernInput.apply_style(self.bg_padding)
        layout.addWidget(create_param_row("边距:", self.bg_padding))
        
        layout.addStretch()
        card.addLayout(layout)
        return card
    
    def create_scroll_group(self) -> ModernCard:
        """创建滚动动态设置分组"""
        self.scroll_switch = ToggleSwitch()
        self.scroll_switch.toggled.connect(self.on_scroll_check_changed)
        
        card = ModernCard()
        card.addWidget(create_section_header("滚动动态设置", self.scroll_switch))
        
        layout = QHBoxLayout()
        layout.setSpacing(12)
        lang = self._language_manager.language
        
        self.scroll_direction = QComboBox()
        for code in ("right", "left", "up", "down", "random"):
            self.scroll_direction.addItem(
                enum_label(SCROLL_DIRECTION_LABELS, code, lang), code
            )
        self.scroll_direction.setMinimumWidth(80)
        self.scroll_direction.setEnabled(False)
        ModernInput.apply_style(self.scroll_direction)
        layout.addWidget(create_param_row("方向:", self.scroll_direction))
        
        self.scroll_speed = QDoubleSpinBox()
        self.scroll_speed.setRange(0.01, 20.0)
        self.scroll_speed.setSingleStep(0.1)
        self.scroll_speed.setValue(1.0)
        self.scroll_speed.setMinimumWidth(70)
        self.scroll_speed.setEnabled(False)
        ModernInput.apply_style(self.scroll_speed)
        layout.addWidget(create_param_row("速度:", self.scroll_speed))
        
        self.random_speed_check = QCheckBox(_ts("随机速度"))
        self.random_speed_check.setEnabled(False)
        layout.addWidget(self.random_speed_check)
        
        self.diagonal_check = QCheckBox(_ts("对角移动"))
        self.diagonal_check.setEnabled(False)
        layout.addWidget(self.diagonal_check)
        
        layout.addStretch()
        card.addLayout(layout)
        return card
    
    def create_timing_group(self) -> ModernCard:
        """创建显示时序设置分组"""
        card = ModernCard(_ts("显示时序设置"))
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        self.delay = QSpinBox()
        self.delay.setRange(0, 300)
        self.delay.setValue(0)
        self.delay.setSuffix(_ts(" 秒"))
        self.delay.setMinimumWidth(70)
        ModernInput.apply_style(self.delay)
        layout.addWidget(create_param_row("延时:", self.delay))
        
        self.interval = QSpinBox()
        self.interval.setRange(0, 60)
        self.interval.setValue(1)
        self.interval.setSuffix(_ts(" 秒"))
        self.interval.setMinimumWidth(70)
        ModernInput.apply_style(self.interval)
        layout.addWidget(create_param_row("间隔:", self.interval))
        
        self.duration = QSpinBox()
        self.duration.setRange(1, 300)
        self.duration.setValue(5)
        self.duration.setSuffix(_ts(" 秒"))
        self.duration.setMinimumWidth(70)
        ModernInput.apply_style(self.duration)
        layout.addWidget(create_param_row("持续:", self.duration))
        
        self.line_display_check = QCheckBox(_ts("行显"))
        layout.addWidget(self.line_display_check)
        
        self.loop_check = QCheckBox(_ts("循环"))
        
        layout.addWidget(self.loop_check)
        
        layout.addStretch()
        card.addLayout(layout)
        return card
    
    # 事件处理函数
    def on_mode_changed(self):
        """文本来源模式切换"""
        if self.filename_radio.isChecked():
            self.filename_params.setEnabled(True)
            self.folder_params.setEnabled(False)
            self.text_params.setEnabled(False)
        elif self.folder_radio.isChecked():
            self.filename_params.setEnabled(False)
            self.folder_params.setEnabled(True)
            self.text_params.setEnabled(False)
        elif self.text_radio.isChecked():
            self.filename_params.setEnabled(False)
            self.folder_params.setEnabled(False)
            self.text_params.setEnabled(True)
        self._update_source_live_feedback()
    
    def on_break_punct_changed(self, checked: bool):
        """断行配置变化"""
        self.punct_symbols.setEnabled(checked)
        self.include_punct_check.setEnabled(checked)
        self._update_source_live_feedback()
    
    def on_single_line_changed(self, checked: bool):
        """单行抽取变化"""
        self.space_break_check.setEnabled(checked)
    
    def on_browse_folder(self):
        """选择文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文本文件夹")
        if folder:
            self.folder_path.setText(folder)
        self._update_source_live_feedback()

    def _set_source_input_highlight(self, control, valid: bool) -> None:
        if valid:
            ModernInput.apply_style(control)
            return
        control.setStyleSheet("border: 1px solid #EF4444; border-radius: 6px;")

    def _update_source_live_feedback(self) -> bool:
        """输入时即时反馈文本来源配置。"""
        if not hasattr(self, "source_feedback_label"):
            return True

        message = ""
        invalid_control = None

        if self.filename_radio.isChecked():
            if self.break_by_punct_check.isChecked() and not self.punct_symbols.text().strip():
                message = "已启用标点断行，请输入至少一个断行标点。"
                invalid_control = self.punct_symbols
            self._set_source_input_highlight(self.punct_symbols, invalid_control is not self.punct_symbols)
        elif self.folder_radio.isChecked():
            folder_path = self.folder_path.text().strip()
            if not folder_path:
                message = "文件夹模式下请选择文本文件夹。"
                invalid_control = self.folder_path
            elif not os.path.isdir(folder_path):
                message = "所选路径不是有效文件夹。"
                invalid_control = self.folder_path
            else:
                has_text_file = any(
                    os.path.isfile(os.path.join(folder_path, name))
                    and name.lower().endswith((".txt", ".srt", ".ass"))
                    for name in os.listdir(folder_path)
                )
                if not has_text_file:
                    message = "文件夹中未发现可用文本文件（.txt/.srt/.ass）。"
                    invalid_control = self.folder_path
            self._set_source_input_highlight(self.folder_path, invalid_control is not self.folder_path)
        elif self.text_radio.isChecked():
            if not self.text_content.toPlainText().strip():
                message = "文本模式下请输入文本内容。"
                invalid_control = self.text_content
            self._set_source_input_highlight(self.text_content, invalid_control is not self.text_content)

        valid = not message
        self.source_feedback_label.setVisible(not valid)
        self.source_feedback_label.setText(message)
        return valid
    
    def toggle_unit(self):
        """切换单位"""
        if self.unit_btn.text() == "p":
            self.unit_btn.setText("%")
        else:
            self.unit_btn.setText("p")
    
    def on_font_check_changed(self, checked: bool):
        """字体复选框变化"""
        self.font_family.setEnabled(checked)
        self.font_size.setEnabled(checked)
        self.font_color_btn.setEnabled(checked)
        self.font_opacity.setEnabled(checked)
    
    def on_shadow_check_changed(self, checked: bool):
        """阴影复选框变化"""
        self.shadow_color_btn.setEnabled(checked)
        self.shadow_depth.setEnabled(checked)
    
    def on_stroke_check_changed(self, checked: bool):
        """描边复选框变化"""
        self.stroke_color_btn.setEnabled(checked)
        self.stroke_width.setEnabled(checked)
    
    def on_bg_check_changed(self, checked: bool):
        """背景复选框变化"""
        self.bg_color_btn.setEnabled(checked)
        self.bg_opacity.setEnabled(checked)
        self.bg_style.setEnabled(checked)
        self.bg_padding.setEnabled(checked)
        self.on_bg_style_changed(self.bg_style.currentData() or self.bg_style.currentText())
    
    def on_bg_style_changed(self, style: str):
        """背景样式变化"""
        if self.bg_switch.isChecked() and normalize_bg_style(style) == "fill":
            self.bg_fit_check.setEnabled(True)
        else:
            self.bg_fit_check.setEnabled(False)
    
    def on_scroll_check_changed(self, checked: bool):
        """滚动复选框变化"""
        self.scroll_direction.setEnabled(checked)
        self.scroll_speed.setEnabled(checked)
        self.random_speed_check.setEnabled(checked)
        self.diagonal_check.setEnabled(checked)
    
    def on_choose_font_color(self):
        """选择字体颜色"""
        color = open_color_dialog(QColor(self.font_color), self, "选择字体颜色")
        if color:
            self.font_color = color.name()
            self.font_color_btn.setStyleSheet(f"background-color: {self.font_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
    
    def on_choose_shadow_color(self):
        """选择阴影颜色"""
        color = open_color_dialog(QColor(self.shadow_color), self, "选择阴影颜色")
        if color:
            self.shadow_color = color.name()
            self.shadow_color_btn.setStyleSheet(f"background-color: {self.shadow_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
    
    def on_choose_stroke_color(self):
        """选择描边颜色"""
        color = open_color_dialog(QColor(self.stroke_color), self, "选择描边颜色")
        if color:
            self.stroke_color = color.name()
            self.stroke_color_btn.setStyleSheet(f"background-color: {self.stroke_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
    
    def on_choose_bg_color(self):
        """选择背景颜色"""
        color = open_color_dialog(QColor(self.bg_color), self, "选择背景颜色")
        if color:
            self.bg_color = color.name()
            self.bg_color_btn.setStyleSheet(f"background-color: {self.bg_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")

    def _validate_source_input(self) -> bool:
        """校验文本来源输入"""
        if self.filename_radio.isChecked():
            if self.break_by_punct_check.isChecked() and not self.punct_symbols.text().strip():
                QMessageBox.warning(self, _ts("警告"), _ts("已启用标点断行，请输入至少一个断行标点"))
                self.punct_symbols.setFocus()
                return False
            return True
        if self.folder_radio.isChecked():
            folder_path = self.folder_path.text().strip()
            if not folder_path:
                QMessageBox.warning(self, _ts("警告"), _ts("请选择文本文件夹"))
                self.folder_browse_btn.setFocus()
                return False
            if not os.path.exists(folder_path):
                QMessageBox.warning(self, _ts("警告"), _ts("文本文件夹不存在"))
                self.folder_browse_btn.setFocus()
                return False
            if not os.path.isdir(folder_path):
                QMessageBox.warning(self, _ts("警告"), _ts("所选路径不是文件夹，请重新选择"))
                self.folder_browse_btn.setFocus()
                return False
            has_text_file = any(
                os.path.isfile(os.path.join(folder_path, name))
                and name.lower().endswith((".txt", ".srt", ".ass"))
                for name in os.listdir(folder_path)
            )
            if not has_text_file:
                QMessageBox.warning(self, _ts("警告"), _ts("文本文件夹内未发现可用文本文件（.txt/.srt/.ass）"))
                self.folder_browse_btn.setFocus()
                return False
        elif self.text_radio.isChecked():
            if not self.text_content.toPlainText().strip():
                QMessageBox.warning(self, _ts("警告"), _ts("请输入文本内容"))
                self.text_content.setFocus()
                return False
        return True
    
    def on_preview(self):
        """预览按钮"""
        # 检查父窗口
        if not self.parent():
            QMessageBox.warning(self, _ts("提示"), _ts("请在主窗口中打开对话框使用预览功能"))
            return

        if not self._validate_source_input():
            return
        
        # 获取视频路径
        video_path = None
        if hasattr(self.parent(), 'get_selected_rows') and hasattr(self.parent(), 'video_list'):
            selected_rows = self.parent().get_selected_rows()
            if selected_rows:
                video_path = self.parent().video_list[selected_rows[0]]['path']
            elif self.parent().video_list:
                video_path = self.parent().video_list[0]['path']
        
        if not video_path:
            QMessageBox.warning(self, _ts("提示"), _ts("请先导入视频"))
            return
        
        # 检查父窗口是否有预览方法
        if not hasattr(self.parent(), '_show_preview_with_config') or not hasattr(self.parent(), 'collect_config'):
            QMessageBox.warning(self, _ts("提示"), _ts("预览功能不可用，请确保在主窗口中打开"))
            return
        
        # 获取当前配置
        current_config = self.get_config()
        
        # 构建临时配置
        temp_config = self.parent().collect_config()
        temp_config['text'] = {
            'text1_enabled': self.track_num == 1,
            'text1_config': current_config if self.track_num == 1 else None,
            'text2_enabled': self.track_num == 2,
            'text2_config': current_config if self.track_num == 2 else None,
            'text3_enabled': self.track_num == 3,
            'text3_config': current_config if self.track_num == 3 else None,
        }
        
        # 调用预览
        self.parent()._show_preview_with_config(video_path, f"文本{self.track_num}预览", temp_config)
    
    def on_ok(self):
        """确定按钮"""
        if not self._validate_source_input():
            return
        
        self.accept()
    
    def load_config(self):
        """加载配置"""
        if not self.config:
            return
        
        # 加载文本来源模式
        mode = normalize_text_source_mode(self.config.get('source_mode', 'plain'))
        if mode == 'filename':
            self.filename_radio.setChecked(True)
            self.break_by_punct_check.setChecked(self.config.get('break_by_punct', False))
            self.punct_symbols.setText(self.config.get('punct_symbols', '。；：？！'))
            self.include_punct_check.setChecked(self.config.get('include_punct', False))
            action_code = normalize_text_filter_action(self.config.get('filter_action', 'keep'))
            idx = self.filter_action.findData(action_code)
            if idx >= 0:
                self.filter_action.setCurrentIndex(idx)
            self.filter_keyword.setText(self.config.get('filter_keyword', ''))
            pos_code = normalize_text_filter_position(self.config.get('filter_position', 'before'))
            idx = self.filter_position.findData(pos_code)
            if idx >= 0:
                self.filter_position.setCurrentIndex(idx)
        elif mode == 'folder':
            self.folder_radio.setChecked(True)
            self.folder_path.setText(self.config.get('folder_path', ''))
            self.folder_random_check.setChecked(self.config.get('folder_random', False))
            self.single_line_check.setChecked(self.config.get('single_line', False))
            self.space_break_check.setChecked(self.config.get('space_break', False))
        elif mode == 'plain':
            self.text_radio.setChecked(True)
            self.text_content.setPlainText(self.config.get('text_content', ''))
        
        # 加载位置与边距
        position_code = normalize_text_position(self.config.get('position', 'center'))
        idx = self.position.findData(position_code)
        if idx >= 0:
            self.position.setCurrentIndex(idx)
        self.margin_x.setValue(self.config.get('margin_x', 0))
        self.margin_y.setValue(self.config.get('margin_y', 0))
        self.line_spacing.setValue(self.config.get('line_spacing', 10))
        unit = self.config.get('unit', 'p')
        self.unit_btn.setText(unit)
        
        # 加载字体样式
        self.font_switch.setChecked(self.config.get('font_enabled', True))
        self.font_family.setCurrentText(self.config.get('font_family', '微软雅黑'))
        self.font_size.setValue(self.config.get('font_size', 24))
        self.font_color = self.config.get('font_color', '#000000')
        self.font_color_btn.setStyleSheet(f"background-color: {self.font_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.font_opacity.setValue(self.config.get('font_opacity', 0.80))
        
        # 加载阴影与描边
        self.shadow_check.setChecked(self.config.get('shadow_enabled', False))
        self.shadow_color = self.config.get('shadow_color', '#000000')
        self.shadow_color_btn.setStyleSheet(f"background-color: {self.shadow_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.shadow_depth.setValue(self.config.get('shadow_depth', 2))
        
        self.stroke_check.setChecked(self.config.get('stroke_enabled', False))
        self.stroke_color = self.config.get('stroke_color', '#FFFFFF')
        self.stroke_color_btn.setStyleSheet(f"background-color: {self.stroke_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.stroke_width.setValue(self.config.get('stroke_width', 1))
        
        # 加载背景样式
        self.bg_switch.setChecked(self.config.get('bg_enabled', False))
        self.bg_color = self.config.get('bg_color', '#808080')
        self.bg_color_btn.setStyleSheet(f"background-color: {self.bg_color}; border: 1px solid {Theme.Border}; border-radius: 4px;")
        self.bg_opacity.setValue(self.config.get('bg_opacity', 0.8))
        bg_style_code = normalize_bg_style(self.config.get('bg_style', 'default'))
        idx = self.bg_style.findData(bg_style_code)
        if idx >= 0:
            self.bg_style.setCurrentIndex(idx)
        self.bg_fit_check.setChecked(self.config.get('bg_fit', False))
        self.bg_padding.setValue(self.config.get('bg_padding', 5))
        
        # 加载滚动动态
        self.scroll_switch.setChecked(self.config.get('scroll_enabled', False))
        scroll_code = normalize_scroll_direction(self.config.get('scroll_direction', 'right'))
        idx = self.scroll_direction.findData(scroll_code)
        if idx >= 0:
            self.scroll_direction.setCurrentIndex(idx)
        self.scroll_speed.setValue(self.config.get('scroll_speed', 1.0))
        self.random_speed_check.setChecked(self.config.get('random_speed', False))
        self.diagonal_check.setChecked(self.config.get('diagonal', False))
        
        # 加载显示时序
        self.delay.setValue(self.config.get('delay', 0))
        self.interval.setValue(self.config.get('interval', 1))
        self.duration.setValue(self.config.get('duration', 5))
        self.line_display_check.setChecked(self.config.get('line_display', False))
        self.loop_check.setChecked(self.config.get('loop', False))
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        config = {}
        
        # 文本来源模式
        if self.filename_radio.isChecked():
            config['source_mode'] = 'filename'
            config['break_by_punct'] = self.break_by_punct_check.isChecked()
            config['punct_symbols'] = self.punct_symbols.text()
            config['include_punct'] = self.include_punct_check.isChecked()
            config['filter_action'] = self.filter_action.currentData() or 'keep'
            config['filter_keyword'] = self.filter_keyword.text()
            config['filter_position'] = self.filter_position.currentData() or 'before'
        elif self.folder_radio.isChecked():
            config['source_mode'] = 'folder'
            config['folder_path'] = self.folder_path.text()
            config['folder_random'] = self.folder_random_check.isChecked()
            config['single_line'] = self.single_line_check.isChecked()
            config['space_break'] = self.space_break_check.isChecked()
        elif self.text_radio.isChecked():
            config['source_mode'] = 'plain'
            config['text_content'] = self.text_content.toPlainText()
        
        # 位置与边距
        config['position'] = self.position.currentData() or 'center'
        config['margin_x'] = self.margin_x.value()
        config['margin_y'] = self.margin_y.value()
        config['line_spacing'] = self.line_spacing.value()
        config['unit'] = self.unit_btn.text()
        
        # 字体样式
        config['font_enabled'] = self.font_switch.isChecked()
        config['font_family'] = self.font_family.currentText()
        config['font_size'] = self.font_size.value()
        config['font_color'] = self.font_color
        config['font_opacity'] = self.font_opacity.value()
        
        # 阴影与描边
        config['shadow_enabled'] = self.shadow_check.isChecked()
        config['shadow_color'] = self.shadow_color
        config['shadow_depth'] = self.shadow_depth.value()
        
        config['stroke_enabled'] = self.stroke_check.isChecked()
        config['stroke_color'] = self.stroke_color
        config['stroke_width'] = self.stroke_width.value()
        
        # 背景样式
        config['bg_enabled'] = self.bg_switch.isChecked()
        config['bg_color'] = self.bg_color
        config['bg_opacity'] = self.bg_opacity.value()
        config['bg_style'] = self.bg_style.currentData() or 'default'
        config['bg_fit'] = self.bg_fit_check.isChecked()
        config['bg_padding'] = self.bg_padding.value()
        
        # 滚动动态
        config['scroll_enabled'] = self.scroll_switch.isChecked()
        config['scroll_direction'] = self.scroll_direction.currentData() or 'right'
        config['scroll_speed'] = self.scroll_speed.value()
        config['random_speed'] = self.random_speed_check.isChecked()
        config['diagonal'] = self.diagonal_check.isChecked()
        
        # 显示时序
        config['delay'] = self.delay.value()
        config['interval'] = self.interval.value()
        config['duration'] = self.duration.value()
        config['line_display'] = self.line_display_check.isChecked()
        config['loop'] = self.loop_check.isChecked()
        
        return config
