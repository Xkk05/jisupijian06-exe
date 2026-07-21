from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
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


def create_pip_tab(self) -> QWidget:
    """创建画中画标签页"""
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
    self.pip_check = ToggleSwitch()
    self.pip_check.toggled.connect(self.on_pip_check_changed)
    
    header_card = ModernCard()
    header_layout = header_card.layout
    
    # 顶部行
    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    
    title_lbl = QLabel(t("batch.pip_tab.title", "画中画"))
    title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Theme.TextPrimary};")
    top_row.addWidget(title_lbl)
    top_row.addSpacing(10)
    top_row.addWidget(self.pip_check)
    
    top_row.addStretch()
    
    self.pip_preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
    self.pip_preview_btn.clicked.connect(self.preview_pip_effect)
    self.pip_preview_btn.setEnabled(False)
    top_row.addWidget(self.pip_preview_btn)
    
    header_layout.addLayout(top_row)
    main_layout.addWidget(header_card)

    # ==================== 2. 参数设置区域 ====================
    settings_card = ModernCard()
    settings_layout = settings_card.layout
    settings_layout.setSpacing(15)

    # 模式选择
    mode_layout = QHBoxLayout()
    mode_layout.setSpacing(15)
    
    self.pip_mode_group = QButtonGroup(self)
    
    self.pip_mode_video = QRadioButton(t("batch.pip_tab.mode.video", "视频模式"))
    self.pip_mode_video.setChecked(True)
    self.pip_mode_video.setEnabled(False)
    self.pip_mode_video.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.pip_mode_video.toggled.connect(self.on_pip_mode_changed)
    self.pip_mode_group.addButton(self.pip_mode_video, 0)
    mode_layout.addWidget(self.pip_mode_video)

    self.pip_mode_background = QRadioButton(t("batch.pip_tab.mode.background", "背景模式"))
    self.pip_mode_background.setEnabled(False)
    self.pip_mode_background.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.pip_mode_group.addButton(self.pip_mode_background, 1)
    mode_layout.addWidget(self.pip_mode_background)
    
    mode_layout.addStretch()
    settings_layout.addWidget(create_param_row(t("batch.pip_tab.label.mode", "模式:"), mode_layout))

    # ==== 视频模式参数区 ====
    self.pip_video_widget = QWidget()
    video_layout = QVBoxLayout(self.pip_video_widget)
    video_layout.setContentsMargins(0, 0, 0, 0)
    video_layout.setSpacing(10)

    # 边距
    margin_layout = QHBoxLayout()
    margin_layout.setSpacing(8)
    
    self.pip_margin_top = QSpinBox()
    self.pip_margin_top.setRange(0, 9999)
    self.pip_margin_top.setValue(50)
    self.pip_margin_top.setFixedWidth(70)
    ModernInput.apply_style(self.pip_margin_top)
    margin_layout.addWidget(QLabel(t("batch.pip_tab.label.vertical", "上下:")))
    margin_layout.addWidget(self.pip_margin_top)
    
    self.pip_margin_left = QSpinBox()
    self.pip_margin_left.setRange(0, 9999)
    self.pip_margin_left.setValue(50)
    self.pip_margin_left.setFixedWidth(70)
    ModernInput.apply_style(self.pip_margin_left)
    margin_layout.addWidget(QLabel(t("batch.pip_tab.label.horizontal", "左右:")))
    margin_layout.addWidget(self.pip_margin_left)
    
    margin_layout.addStretch()
    video_layout.addWidget(create_param_row(t("batch.pip_tab.label.margin", "边距:"), margin_layout))

    # 虚化 & 透明度
    effect_layout = QHBoxLayout()
    effect_layout.setSpacing(8)
    
    self.pip_video_blur_check = QCheckBox(t("batch.pip_tab.option.background_blur", "背景虚化"))
    self.pip_video_blur_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    effect_layout.addWidget(self.pip_video_blur_check)
    
    self.pip_video_blur = QDoubleSpinBox()
    self.pip_video_blur.setRange(0, 30)
    self.pip_video_blur.setSingleStep(1)
    self.pip_video_blur.setValue(10)
    self.pip_video_blur.setFixedWidth(80)
    ModernInput.apply_style(self.pip_video_blur)
    effect_layout.addWidget(self.pip_video_blur)
    
    effect_layout.addSpacing(15)
    
    self.pip_video_opacity = QDoubleSpinBox()
    self.pip_video_opacity.setRange(0.01, 1.0)
    self.pip_video_opacity.setSingleStep(0.01)
    self.pip_video_opacity.setValue(1.0)
    self.pip_video_opacity.setFixedWidth(80)
    ModernInput.apply_style(self.pip_video_opacity)
    effect_layout.addWidget(QLabel(t("common.label.opacity", "透明度:")))
    effect_layout.addWidget(self.pip_video_opacity)
    
    effect_layout.addStretch()
    video_layout.addWidget(create_param_row(t("common.label.effect", "效果:"), effect_layout))

    # 视频大小
    self.pip_video_size = QSpinBox()
    self.pip_video_size.setRange(10, 100)
    self.pip_video_size.setValue(80)
    self.pip_video_size.setFixedWidth(70)
    ModernInput.apply_style(self.pip_video_size)
    video_layout.addWidget(create_param_row(t("batch.pip_tab.label.video_size_percent", "视频大小(%):"), self.pip_video_size))

    self.pip_video_widget.setEnabled(False)
    settings_layout.addWidget(self.pip_video_widget)

    # ==== 背景模式参数区 ====
    self.pip_bg_widget = QWidget()
    bg_layout = QVBoxLayout(self.pip_bg_widget)
    bg_layout.setContentsMargins(0, 0, 0, 0)
    bg_layout.setSpacing(10)

    # 文件选择
    file_layout = QHBoxLayout()
    file_layout.setSpacing(8)
    
    self.pip_bg_path = QLineEdit()
    self.pip_bg_path.setReadOnly(True)
    self.pip_bg_path.setPlaceholderText(t("batch.pip_tab.placeholder.background_file", "选择背景文件（图片/视频）"))
    ModernInput.apply_style(self.pip_bg_path)
    file_layout.addWidget(self.pip_bg_path, 1)

    self.pip_bg_browse_btn = ModernButton(t("common.btn.choose", "选择"), style=ModernButton.Style.Secondary)
    self.pip_bg_browse_btn.setFixedSize(60, 32)
    self.pip_bg_browse_btn.clicked.connect(self.on_pip_bg_browse_clicked)
    file_layout.addWidget(self.pip_bg_browse_btn)
    
    bg_layout.addWidget(create_param_row(t("batch.pip_tab.label.background_file", "背景文件:"), file_layout))

    # 偏移
    offset_layout = QHBoxLayout()
    offset_layout.setSpacing(8)
    
    self.pip_bg_offset_x = QSpinBox()
    self.pip_bg_offset_x.setRange(-9999, 9999)
    self.pip_bg_offset_x.setValue(0)
    self.pip_bg_offset_x.setFixedWidth(70)
    ModernInput.apply_style(self.pip_bg_offset_x)
    offset_layout.addWidget(QLabel(t("common.axis.x", "X:")))
    offset_layout.addWidget(self.pip_bg_offset_x)
    
    self.pip_bg_offset_y = QSpinBox()
    self.pip_bg_offset_y.setRange(-9999, 9999)
    self.pip_bg_offset_y.setValue(0)
    self.pip_bg_offset_y.setFixedWidth(70)
    ModernInput.apply_style(self.pip_bg_offset_y)
    offset_layout.addWidget(QLabel(t("common.axis.y", "Y:")))
    offset_layout.addWidget(self.pip_bg_offset_y)
    
    offset_layout.addStretch()
    bg_layout.addWidget(create_param_row(t("batch.pip_tab.label.offset", "偏移:"), offset_layout))

    # 其他参数
    other_layout = QHBoxLayout()
    other_layout.setSpacing(8)
    
    self.pip_bg_opacity = QDoubleSpinBox()
    self.pip_bg_opacity.setRange(0.01, 1.0)
    self.pip_bg_opacity.setSingleStep(0.01)
    self.pip_bg_opacity.setValue(1.0)
    self.pip_bg_opacity.setFixedWidth(70)
    ModernInput.apply_style(self.pip_bg_opacity)
    other_layout.addWidget(QLabel(t("common.label.opacity", "透明度:")))
    other_layout.addWidget(self.pip_bg_opacity)
    
    other_layout.addSpacing(15)
    
    self.pip_bg_size = QSpinBox()
    self.pip_bg_size.setRange(10, 100)
    self.pip_bg_size.setValue(60)
    self.pip_bg_size.setFixedWidth(70)
    ModernInput.apply_style(self.pip_bg_size)
    other_layout.addWidget(QLabel(t("batch.pip_tab.label.video_size_percent", "视频大小(%):")))
    other_layout.addWidget(self.pip_bg_size)
    
    other_layout.addStretch()
    bg_layout.addWidget(create_param_row(t("batch.pip_tab.label.params", "参数:"), other_layout))

    self.pip_bg_widget.setEnabled(False)
    self.pip_bg_widget.setVisible(False)
    settings_layout.addWidget(self.pip_bg_widget)

    main_layout.addWidget(settings_card)
    main_layout.addStretch()

    # 2. 包装到滚动区域
    scroll_area = create_modern_scroll_area(content_widget)
    
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    
    return container
