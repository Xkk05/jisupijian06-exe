from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)
from ui.components import (
    ModernCard,
    ToggleSwitch,
    ModernInput,
    ModernButton,
    create_param_row,
    create_modern_scroll_area
)
from ui.theme import Theme
from ui.i18n import t


def create_trim_tab(self) -> QWidget:
    """创建去头尾标签页"""
    # 1. 创建内容容器
    content_widget = QWidget()
    content_widget.setStyleSheet("""
        background: transparent;
        QLabel {
            font-size: 13px;
            font-weight: normal;
        }
    """)
    main_layout = QVBoxLayout(content_widget)
    main_layout.setSpacing(20)
    main_layout.setContentsMargins(0, 10, 0, 20)

    # ==================== 1. 功能总开关 ====================
    self.trim_check = ToggleSwitch()
    self.trim_check.toggled.connect(self.on_trim_check_changed)
    
    header_card = ModernCard()
    header_layout = header_card.layout
    
    # 顶部行
    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    
    title_lbl = QLabel(t("batch.trim_tab.title", "视频长度裁剪"))
    title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Theme.TextPrimary};")
    top_row.addWidget(title_lbl)
    top_row.addSpacing(10)
    top_row.addWidget(self.trim_check)
    
    top_row.addStretch()
    
    self.trim_preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
    self.trim_preview_btn.clicked.connect(self.preview_trim_effect)
    self.trim_preview_btn.setEnabled(False)
    top_row.addWidget(self.trim_preview_btn)
    
    header_layout.addLayout(top_row)
    main_layout.addWidget(header_card)

    # ==================== 2. 裁剪模式选择 ====================
    settings_card = ModernCard()
    settings_layout = settings_card.layout
    settings_layout.setSpacing(15)

    self.trim_mode_group = QButtonGroup(self)

    # 辅助函数：创建模式行
    def create_mode_row(radio_btn, content_layout):
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)
        
        radio_btn.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
        row_layout.addWidget(radio_btn)
        
        if content_layout:
            row_layout.addLayout(content_layout)
        
        row_layout.addStretch()
        return container

    # 模式一：去头尾
    self.trim_mode1_radio = QRadioButton(t("batch.trim_tab.mode.trim_edges", "去头尾"))
    self.trim_mode1_radio.setChecked(True)
    self.trim_mode1_radio.setEnabled(False)
    self.trim_mode1_radio.toggled.connect(self.on_trim_mode_changed)
    self.trim_mode_group.addButton(self.trim_mode1_radio, 0)

    mode1_inputs = QHBoxLayout()
    mode1_inputs.setSpacing(8)
    
    self.trim_head = QDoubleSpinBox()
    self.trim_head.setRange(0, 99999)
    self.trim_head.setValue(3.0)
    self.trim_head.setFixedWidth(80)
    self.trim_head.setEnabled(False)
    ModernInput.apply_style(self.trim_head)
    mode1_inputs.addWidget(QLabel(t("batch.trim_tab.label.trim_head", "去片头:")))
    mode1_inputs.addWidget(self.trim_head)
    mode1_inputs.addWidget(QLabel(t("common.second", "秒")))
    
    mode1_inputs.addSpacing(15)
    
    self.trim_tail = QDoubleSpinBox()
    self.trim_tail.setRange(0, 99999)
    self.trim_tail.setValue(3.0)
    self.trim_tail.setFixedWidth(80)
    self.trim_tail.setEnabled(False)
    ModernInput.apply_style(self.trim_tail)
    mode1_inputs.addWidget(QLabel(t("batch.trim_tab.label.trim_tail", "去片尾:")))
    mode1_inputs.addWidget(self.trim_tail)
    mode1_inputs.addWidget(QLabel(t("common.second", "秒")))
    
    settings_layout.addWidget(create_mode_row(self.trim_mode1_radio, mode1_inputs))

    # 模式二：截取
    self.trim_mode2_radio = QRadioButton(t("batch.trim_tab.mode.keep_middle", "保留中间"))
    self.trim_mode2_radio.setEnabled(False)
    self.trim_mode2_radio.toggled.connect(self.on_trim_mode_changed)
    self.trim_mode_group.addButton(self.trim_mode2_radio, 1)

    mode2_inputs = QHBoxLayout()
    mode2_inputs.setSpacing(8)
    
    self.trim_start = QDoubleSpinBox()
    self.trim_start.setRange(0, 99999)
    self.trim_start.setValue(0.0)
    self.trim_start.setFixedWidth(80)
    self.trim_start.setEnabled(False)
    ModernInput.apply_style(self.trim_start)
    mode2_inputs.addWidget(QLabel(t("batch.trim_tab.label.start_time", "开始时间:")))
    mode2_inputs.addWidget(self.trim_start)
    mode2_inputs.addWidget(QLabel(t("common.second", "秒")))
    
    mode2_inputs.addSpacing(15)
    
    self.trim_duration = QDoubleSpinBox()
    self.trim_duration.setRange(0, 99999)
    self.trim_duration.setValue(10.0)
    self.trim_duration.setFixedWidth(80)
    self.trim_duration.setEnabled(False)
    ModernInput.apply_style(self.trim_duration)
    mode2_inputs.addWidget(QLabel(t("batch.trim_tab.label.keep_duration", "保留时长:")))
    mode2_inputs.addWidget(self.trim_duration)
    mode2_inputs.addWidget(QLabel(t("common.second", "秒")))
    
    settings_layout.addWidget(create_mode_row(self.trim_mode2_radio, mode2_inputs))
    
    main_layout.addWidget(settings_card)
    main_layout.addStretch()

    # 2. 包装到滚动区域
    scroll_area = create_modern_scroll_area(content_widget)
    
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    
    return container
