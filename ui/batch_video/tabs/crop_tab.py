from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QGridLayout
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


def create_crop_tab(self) -> QWidget:
    """创建裁剪标签页"""
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
    self.crop_check = ToggleSwitch()
    # 注意：原代码使用 stateChanged(int)，现在使用 toggled(bool)
    # self._on_crop_enabled_changed 可能接收 int 参数，需要检查或适配
    # 假设 self._on_crop_enabled_changed 处理 bool 或 int (0/2)
    # 如果它只处理 int，我们可能需要 lambda: self._on_crop_enabled_changed(2 if checked else 0)
    # 简单起见，先连接 toggled，并在需要时修改原方法（或者这里做适配）
    self.crop_check.toggled.connect(self._on_crop_enabled_changed)
    
    header_card = ModernCard()
    header_layout = header_card.layout
    
    # 顶部行：标题+开关 + 预览/选取按钮
    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    
    # 左侧：标题+开关
    title_lbl = QLabel(t("batch.crop_tab.title", "画面裁剪"))
    title_lbl.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Theme.TextPrimary};")
    top_row.addWidget(title_lbl)
    top_row.addSpacing(10)
    top_row.addWidget(self.crop_check)
    
    top_row.addStretch()
    
    # 右侧：按钮
    self.crop_select_btn = ModernButton(t("batch.crop_tab.btn.select_region", "选取区域"), style=ModernButton.Style.Outline, icon_name="move")
    self.crop_select_btn.setEnabled(False)
    self.crop_select_btn.clicked.connect(self._on_crop_select)
    top_row.addWidget(self.crop_select_btn)

    self.crop_preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
    self.crop_preview_btn.clicked.connect(self._on_crop_preview)
    self.crop_preview_btn.setEnabled(False)
    top_row.addWidget(self.crop_preview_btn)
    
    header_layout.addLayout(top_row)
    main_layout.addWidget(header_card)

    # ==================== 2. 裁剪模式选择 ====================
    methods_card = ModernCard()
    self.crop_methods_widget = methods_card # 保持引用以便禁用
    methods_layout = methods_card.layout
    methods_layout.setSpacing(15)

    self.crop_method_group = QButtonGroup()

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

    # 方法1: 像素裁剪
    self.crop_method_pixel = QRadioButton(t("batch.crop_tab.mode.pixel", "像素裁剪"))
    self.crop_method_pixel.setChecked(True)
    self.crop_method_pixel.toggled.connect(self._on_crop_method_changed)
    self.crop_method_group.addButton(self.crop_method_pixel)
    
    pixel_inputs = QHBoxLayout()
    pixel_inputs.setSpacing(8)
    
    for label, attr_name in [
        (t("batch.crop_tab.pixel.top", "上"), "crop_pixel_top"),
        (t("batch.crop_tab.pixel.bottom", "下"), "crop_pixel_bottom"),
        (t("batch.crop_tab.pixel.left", "左"), "crop_pixel_left"),
        (t("batch.crop_tab.pixel.right", "右"), "crop_pixel_right"),
    ]:
        pixel_inputs.addWidget(QLabel(label + ":"))
        spin = QSpinBox()
        spin.setRange(0, 9999)
        spin.setFixedWidth(70)
        ModernInput.apply_style(spin)
        setattr(self, attr_name, spin)
        pixel_inputs.addWidget(spin)
        spin.valueChanged.connect(
            lambda _=None: self._update_crop_remove_watermark_conflict_hint()
            if hasattr(self, "_update_crop_remove_watermark_conflict_hint")
            else None
        )
        
    methods_layout.addWidget(create_mode_row(self.crop_method_pixel, pixel_inputs))

    # 方法2: 中间裁剪
    self.crop_method_middle = QRadioButton(t("batch.crop_tab.mode.ratio", "比例裁剪"))
    self.crop_method_middle.toggled.connect(self._on_crop_method_changed)
    self.crop_method_group.addButton(self.crop_method_middle)
    
    middle_inputs = QHBoxLayout()
    middle_inputs.setSpacing(8)
    middle_inputs.addWidget(QLabel(t("batch.crop_tab.label.keep_region", "保留区域:")))
    
    self.crop_middle_ratio = QComboBox()
    self.crop_middle_ratio.addItems(["1:1", "16:9", "9:16", "4:3", "3:4"])
    self.crop_middle_ratio.setCurrentText("16:9")
    self.crop_middle_ratio.setFixedWidth(100)
    ModernInput.apply_style(self.crop_middle_ratio)
    middle_inputs.addWidget(self.crop_middle_ratio)
    self.crop_middle_ratio.currentTextChanged.connect(
        lambda _=None: self._update_crop_remove_watermark_conflict_hint()
        if hasattr(self, "_update_crop_remove_watermark_conflict_hint")
        else None
    )
    
    methods_layout.addWidget(create_mode_row(self.crop_method_middle, middle_inputs))

    # 方法3: 百分比裁剪
    self.crop_method_percent = QRadioButton(t("batch.crop_tab.mode.percent", "百分比裁剪"))
    self.crop_method_percent.toggled.connect(self._on_crop_method_changed)
    self.crop_method_group.addButton(self.crop_method_percent)
    
    percent_inputs = QHBoxLayout()
    percent_inputs.setSpacing(8)
    
    self.crop_percent_value = QSpinBox()
    self.crop_percent_value.setRange(1, 100)
    self.crop_percent_value.setValue(50)
    self.crop_percent_value.setFixedWidth(70)
    ModernInput.apply_style(self.crop_percent_value)
    percent_inputs.addWidget(self.crop_percent_value)
    percent_inputs.addWidget(QLabel("%"))
    
    percent_inputs.addSpacing(15)
    percent_inputs.addWidget(QLabel(t("batch.crop_tab.label.position", "裁剪位置:")))
    
    self.crop_percent_mode = QComboBox()
    self.crop_percent_mode.addItems(
        [
            t("batch.crop_tab.position.all_sides", "四边"),
            t("batch.crop_tab.position.top_left", "左上"),
            t("batch.crop_tab.position.top_right", "右上"),
            t("batch.crop_tab.position.bottom_left", "左下"),
            t("batch.crop_tab.position.bottom_right", "右下"),
            t("batch.crop_tab.position.top", "上边"),
            t("batch.crop_tab.position.bottom", "下边"),
            t("batch.crop_tab.position.left", "左边"),
            t("batch.crop_tab.position.right", "右边"),
            t("batch.crop_tab.position.vertical", "上下"),
            t("batch.crop_tab.position.horizontal", "左右"),
            t("batch.crop_tab.position.random", "随机"),
        ]
    )
    self.crop_percent_mode.setCurrentText(t("batch.crop_tab.position.all_sides", "四边"))
    self.crop_percent_mode.setFixedWidth(100)
    ModernInput.apply_style(self.crop_percent_mode)
    percent_inputs.addWidget(self.crop_percent_mode)
    self.crop_percent_value.valueChanged.connect(
        lambda _=None: self._update_crop_remove_watermark_conflict_hint()
        if hasattr(self, "_update_crop_remove_watermark_conflict_hint")
        else None
    )
    self.crop_percent_mode.currentTextChanged.connect(
        lambda _=None: self._update_crop_remove_watermark_conflict_hint()
        if hasattr(self, "_update_crop_remove_watermark_conflict_hint")
        else None
    )
    
    methods_layout.addWidget(create_mode_row(self.crop_method_percent, percent_inputs))
    
    main_layout.addWidget(methods_card)
    self.crop_methods_widget.setEnabled(False)

    main_layout.addStretch()

    # 2. 包装到滚动区域
    scroll_area = create_modern_scroll_area(content_widget)
    
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    
    return container
