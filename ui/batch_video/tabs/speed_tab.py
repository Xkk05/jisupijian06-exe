from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
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


def create_speed_tab(self) -> QWidget:
    """创建变速标签页"""
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

    # ==================== 1. 变速设置 ====================
    self.speed_check = ToggleSwitch()
    self.speed_check.toggled.connect(self.on_speed_check_changed)
    
    speed_card = ModernCard()
    speed_layout = speed_card.layout
    
    # 顶部行
    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    
    title_lbl = QLabel(t("batch.speed_tab.title", "音视频变速"))
    title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Theme.TextPrimary};")
    top_row.addWidget(title_lbl)
    top_row.addSpacing(10)
    top_row.addWidget(self.speed_check)
    
    top_row.addStretch()
    
    self.speed_preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
    self.speed_preview_btn.clicked.connect(self.preview_speed_effect)
    self.speed_preview_btn.setEnabled(False)
    top_row.addWidget(self.speed_preview_btn)
    
    speed_layout.addLayout(top_row)

    # 参数设置
    params_layout = QVBoxLayout()
    params_layout.setSpacing(15)

    # 变速倍数
    range_layout = QHBoxLayout()
    range_layout.setSpacing(8)
    
    self.speed_min = QDoubleSpinBox()
    self.speed_min.setRange(0.5, 4.0)
    self.speed_min.setSingleStep(0.1)
    self.speed_min.setValue(1.0)
    self.speed_min.setFixedWidth(70)
    self.speed_min.setEnabled(False)
    ModernInput.apply_style(self.speed_min)
    range_layout.addWidget(self.speed_min)
    
    range_layout.addWidget(QLabel("~"))
    
    self.speed_max = QDoubleSpinBox()
    self.speed_max.setRange(0.5, 4.0)
    self.speed_max.setSingleStep(0.1)
    self.speed_max.setValue(1.05)
    self.speed_max.setFixedWidth(70)
    self.speed_max.setEnabled(False)
    ModernInput.apply_style(self.speed_max)
    range_layout.addWidget(self.speed_max)
    
    range_layout.addWidget(QLabel("(0.5~4.0)"))
    range_layout.addStretch()
    
    params_layout.addWidget(create_param_row(t("batch.speed_tab.label.speed_ratio", "变速倍数:"), range_layout))

    # 最短时长
    min_duration_layout = QHBoxLayout()
    min_duration_layout.setSpacing(10)
    
    self.speed_min_duration_check = QCheckBox(t("common.option.enable", "启用"))
    self.speed_min_duration_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.speed_min_duration_check.setEnabled(False)
    min_duration_layout.addWidget(self.speed_min_duration_check)
    
    self.speed_min_duration = QSpinBox()
    self.speed_min_duration.setRange(1, 9999)
    self.speed_min_duration.setValue(10)
    self.speed_min_duration.setFixedWidth(80)
    self.speed_min_duration.setEnabled(False)
    ModernInput.apply_style(self.speed_min_duration)
    min_duration_layout.addWidget(self.speed_min_duration)
    min_duration_layout.addWidget(QLabel(t("common.second", "秒")))
    min_duration_layout.addStretch()
    
    params_layout.addWidget(create_param_row(t("batch.speed_tab.label.min_duration_limit", "最短时长限制:"), min_duration_layout))

    # 分段变速
    segment_layout = QHBoxLayout()
    segment_layout.setSpacing(10)
    
    self.speed_segment_check = QCheckBox(t("common.option.enable", "启用"))
    self.speed_segment_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.speed_segment_check.setEnabled(False)
    segment_layout.addWidget(self.speed_segment_check)
    
    self.speed_segment_duration = QSpinBox()
    self.speed_segment_duration.setRange(1, 9999)
    self.speed_segment_duration.setValue(10)
    self.speed_segment_duration.setFixedWidth(80)
    self.speed_segment_duration.setEnabled(False)
    ModernInput.apply_style(self.speed_segment_duration)
    segment_layout.addWidget(self.speed_segment_duration)
    segment_layout.addWidget(QLabel(t("batch.speed_tab.label.seconds_per_segment", "秒为一段")))
    segment_layout.addStretch()
    
    params_layout.addWidget(create_param_row(t("batch.speed_tab.label.segment_speed", "分段变速:"), segment_layout))

    # 变调
    self.speed_pitch_check = QCheckBox(t("batch.speed_tab.option.enable_pitch_shift", "启用变调"))
    self.speed_pitch_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.speed_pitch_check.setEnabled(False)
    params_layout.addWidget(create_param_row(t("batch.speed_tab.label.audio_process", "音频处理:"), self.speed_pitch_check))

    speed_layout.addLayout(params_layout)
    main_layout.addWidget(speed_card)
    
    main_layout.addStretch()

    # 2. 包装到滚动区域
    scroll_area = create_modern_scroll_area(content_widget)
    
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    
    return container
