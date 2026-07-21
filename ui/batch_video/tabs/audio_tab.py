from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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


def create_audio_tab(self) -> QWidget:
    """创建背景音标签页"""
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

    def create_tab_section_header(text, switch_widget=None):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(text)
        label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Theme.TextPrimary};")
        layout.addWidget(label)

        layout.addStretch()

        if switch_widget:
            layout.addWidget(switch_widget)

        return container

    # ==================== 1. 背景音乐设置 ====================
    self.bgm_check = ToggleSwitch()
    self.bgm_check.toggled.connect(self.on_bgm_check_changed)
    
    bgm_card = ModernCard()
    bgm_layout = bgm_card.layout
    bgm_layout.addWidget(create_tab_section_header(t("batch.audio_tab.title", "背景音乐设置"), self.bgm_check))

    # 文件选择
    file_layout = QHBoxLayout()
    file_layout.setSpacing(8)
    
    self.bgm_path = QLineEdit()
    self.bgm_path.setReadOnly(True)
    self.bgm_path.setPlaceholderText(t("batch.audio_tab.placeholder.no_audio", "未选择音频文件"))
    self.bgm_path.setEnabled(False)
    ModernInput.apply_style(self.bgm_path)
    file_layout.addWidget(self.bgm_path, 1)
    
    self.bgm_import_btn = ModernButton(t("common.btn.import", "导入"), style=ModernButton.Style.Secondary)
    self.bgm_import_btn.setFixedSize(60, 32)
    self.bgm_import_btn.setEnabled(False)
    self.bgm_import_btn.clicked.connect(self.on_bgm_import_clicked)
    file_layout.addWidget(self.bgm_import_btn)
    
    self.bgm_mode_btn = ModernButton(t("common.option.file", "文件"), style=ModernButton.Style.Secondary, icon_name="file")
    self.bgm_mode_btn.setFixedHeight(32)
    self.bgm_mode_btn.setMinimumWidth(88)
    self.bgm_mode_btn.setToolTip(t("common.tooltip.file_mode", "当前：文件模式（点击切换到文件夹模式）"))
    self.bgm_mode_btn.setEnabled(False)
    self.bgm_mode_btn.clicked.connect(self.on_bgm_mode_toggle)
    self.bgm_mode = "file"
    file_layout.addWidget(self.bgm_mode_btn)
    
    bgm_layout.addWidget(create_param_row(t("batch.audio_tab.label.audio_source", "音频源:"), file_layout))

    # 音量设置
    self.bgm_volume = QDoubleSpinBox()
    self.bgm_volume.setRange(0, 10)
    self.bgm_volume.setSingleStep(0.1)
    self.bgm_volume.setValue(0.50)
    self.bgm_volume.setFixedWidth(70)
    self.bgm_volume.setEnabled(False)
    ModernInput.apply_style(self.bgm_volume)
    bgm_layout.addWidget(create_param_row(t("batch.audio_tab.label.bgm_volume", "背景音量:"), self.bgm_volume))

    # 淡入淡出 & 延迟
    fade_layout = QHBoxLayout()
    fade_layout.setSpacing(10)
    
    self.bgm_fadein_check = QCheckBox(t("batch.audio_tab.option.fade_in_out", "淡入淡出"))
    self.bgm_fadein_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.bgm_fadein_check.setEnabled(False)
    self.bgm_fadein_check.toggled.connect(self.on_bgm_fadein_check_changed)
    fade_layout.addWidget(self.bgm_fadein_check)
    
    self.bgm_fadein_duration = QDoubleSpinBox()
    self.bgm_fadein_duration.setRange(0, 999)
    self.bgm_fadein_duration.setSingleStep(1.0)
    self.bgm_fadein_duration.setValue(3.0)
    self.bgm_fadein_duration.setFixedWidth(60)
    self.bgm_fadein_duration.setEnabled(False)
    ModernInput.apply_style(self.bgm_fadein_duration)
    fade_layout.addWidget(self.bgm_fadein_duration)
    fade_layout.addWidget(QLabel(t("common.second", "秒")))
    
    fade_layout.addSpacing(15)
    
    self.bgm_delay_check = QCheckBox(t("batch.audio_tab.option.delay", "延迟"))
    self.bgm_delay_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.bgm_delay_check.setEnabled(False)
    self.bgm_delay_check.toggled.connect(self.on_bgm_delay_check_changed)
    fade_layout.addWidget(self.bgm_delay_check)
    
    self.bgm_delay = QDoubleSpinBox()
    self.bgm_delay.setRange(0, 999)
    self.bgm_delay.setSingleStep(1.0)
    self.bgm_delay.setValue(0.0)
    self.bgm_delay.setFixedWidth(60)
    self.bgm_delay.setEnabled(False)
    ModernInput.apply_style(self.bgm_delay)
    fade_layout.addWidget(self.bgm_delay)
    fade_layout.addWidget(QLabel(t("common.second", "秒")))
    
    fade_layout.addStretch()
    bgm_layout.addWidget(create_param_row(t("common.label.effect", "效果:"), fade_layout))

    # 其他选项
    options_layout = QHBoxLayout()
    options_layout.setSpacing(15)
    
    self.bgm_loop_check = QCheckBox(t("batch.audio_tab.option.loop", "循环播放"))
    self.bgm_loop_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.bgm_loop_check.setEnabled(False)
    options_layout.addWidget(self.bgm_loop_check)
    
    self.bgm_random_check = QCheckBox(t("batch.audio_tab.option.random_apply", "随机应用"))
    self.bgm_random_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.bgm_random_check.setEnabled(False)
    options_layout.addWidget(self.bgm_random_check)
    
    options_layout.addStretch()
    bgm_layout.addWidget(create_param_row(t("common.label.options", "选项:"), options_layout))
    
    main_layout.addWidget(bgm_card)

    # ==================== 2. 原音设置 ====================
    original_card = ModernCard()
    original_layout = original_card.layout
    
    self.original_volume_check = ToggleSwitch()
    self.original_volume_check.setEnabled(False) # 默认可能不可用，需看业务逻辑，原代码为 checkable
    # 原代码 self.original_volume_check 是 QCheckBox("原音音量")，这里我们把它作为 section header 的开关
    # 注意：原代码逻辑中 self.original_volume_check.toggled 控制 self.original_volume 的 enable 状态
    self.original_volume_check.toggled.connect(self.on_original_volume_check_changed)

    original_layout.addWidget(create_tab_section_header(t("batch.audio_tab.original.title", "原音处理"), self.original_volume_check))
    
    vol_layout = QHBoxLayout()
    vol_layout.setSpacing(10)
    
    self.original_volume = QDoubleSpinBox()
    self.original_volume.setRange(0, 10)
    self.original_volume.setSingleStep(0.1)
    self.original_volume.setValue(1.00)
    self.original_volume.setFixedWidth(70)
    self.original_volume.setEnabled(False)
    ModernInput.apply_style(self.original_volume)
    vol_layout.addWidget(self.original_volume)
    
    self.original_fade_sync_check = QCheckBox(t("batch.audio_tab.original.fade_sync", "原音亦淡入淡出"))
    self.original_fade_sync_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.original_fade_sync_check.setEnabled(False)
    vol_layout.addWidget(self.original_fade_sync_check)
    
    vol_layout.addStretch()
    original_layout.addWidget(create_param_row(t("batch.audio_tab.original.volume", "原音音量:"), vol_layout))

    main_layout.addWidget(original_card)

    main_layout.addStretch()

    # 2. 包装到滚动区域
    scroll_area = create_modern_scroll_area(content_widget)
    
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    
    return container
