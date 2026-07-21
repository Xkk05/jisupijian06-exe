from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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
    load_svg_icon,
    create_param_row,
    create_modern_scroll_area
)
from ui.theme import Theme
from ui.i18n import apply_language_to_widget, get_language_manager, t
from utils.enum_codes import TEXT_POSITION_LABELS, enum_label


def create_add_watermark_tab(self) -> QWidget:
    """创建加水印标签页"""
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

    # 初始化水印配置列表
    self.watermark_widgets = []

    # ==================== 1. 功能总开关 ====================
    self.add_watermark_check = ToggleSwitch()
    self.add_watermark_check.toggled.connect(self.on_add_watermark_check_changed)
    
    # 使用 ModernCard 包裹头部开关，保持统一感
    header_card = ModernCard()
    header_layout = header_card.layout

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

    header_layout.addWidget(
        create_tab_section_header(t("batch.add_watermark_tab.enable", "启用加水印功能"), self.add_watermark_check)
    )
    main_layout.addWidget(header_card)

    # ==================== 2. 水印配置容器 ====================
    self.watermark_container_layout = QVBoxLayout()
    self.watermark_container_layout.setSpacing(15)
    main_layout.addLayout(self.watermark_container_layout)
    self.watermark_tab_content_widget = content_widget

    # 默认添加第一个水印配置
    self.create_watermark_config_widget(0)

    # ==================== 3. 添加按钮 ====================
    add_btn_layout = QHBoxLayout()
    add_btn_layout.setContentsMargins(10, 0, 10, 0)
    
    add_new_watermark_btn = ModernButton(
        t("batch.add_watermark_tab.btn.add_one", "+ 增加一个水印"),
        style=ModernButton.Style.Outline
    )
    # 自定义样式使其更显眼
    add_new_watermark_btn.setStyleSheet(f"""
        QPushButton {{
            border: 2px dashed {Theme.Primary};
            border-radius: 8px;
            background: transparent;
            color: {Theme.Primary};
            font-weight: bold;
            font-size: 13px;
            height: 40px;
        }}
        QPushButton:hover {{
            background: {Theme.Background};
        }}
    """)
    add_new_watermark_btn.setToolTip(
        t("batch.add_watermark_tab.tooltip.max_count", "最多支持{count}个水印").format(
            count=self.MAX_WATERMARKS
        )
    )
    add_new_watermark_btn.clicked.connect(self.add_new_watermark_widget)
    self.add_new_watermark_btn = add_new_watermark_btn
    self._update_watermark_add_button_state()
    add_btn_layout.addWidget(add_new_watermark_btn)
    
    main_layout.addLayout(add_btn_layout)
    main_layout.addStretch()

    # 2. 创建现代滚动区域
    scroll_area = create_modern_scroll_area(content_widget)

    # 3. 外层容器
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    self.watermark_tab_container = container

    # 初始化状态：未启用总开关时，所有配置区域和新增按钮应置灰
    initial_checked = self.add_watermark_check.isChecked()
    for widget_dict in self.watermark_widgets:
        group = widget_dict.get("group")
        if group:
            group.setEnabled(initial_checked)
    self._update_watermark_add_button_state()

    return container


def create_watermark_config_widget(self, index: int):
    """创建单个水印配置区域 (ModernCard)"""
    
    card = ModernCard()
    card_layout = card.layout
    card_layout.setSpacing(12)
    current_lang = get_language_manager().language

    # 标题栏
    title_layout = QHBoxLayout()
    title = QLabel(t("batch.add_watermark_tab.title.index", "水印 #{index}").format(index=index + 1))
    title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Theme.TextPrimary};")
    title_layout.addWidget(title)
    title_layout.addStretch()
    card_layout.addLayout(title_layout)

    # 控件字典
    widgets_dict = {"group": card, "index": index, "title_label": title} # 保持 key="group" 以兼容旧逻辑

    # 水印类型
    type_combo = QComboBox()
    type_combo.addItem(t("batch.add_watermark_tab.type.image", "图片水印"), "image")
    type_combo.addItem(t("batch.add_watermark_tab.type.text", "文字水印"), "text")
    ModernInput.apply_style(type_combo)
    type_combo.setFixedWidth(120)
    type_combo.currentIndexChanged.connect(
        lambda idx, w=widgets_dict: self.on_single_watermark_type_changed(w["index"], idx)
    )
    widgets_dict["type_combo"] = type_combo
    card_layout.addWidget(create_param_row(t("batch.add_watermark_tab.label.type", "水印类型:"), type_combo))

    # ==== 图片水印配置 ====
    image_widget = QWidget()
    image_layout = QVBoxLayout(image_widget)
    image_layout.setContentsMargins(0, 0, 0, 0)
    image_layout.setSpacing(10)

    # 文件选择
    file_row = QHBoxLayout()
    file_row.setSpacing(8)
    
    file_path = QLineEdit()
    file_path.setPlaceholderText(t("batch.add_watermark_tab.placeholder.file", "选择水印文件..."))
    ModernInput.apply_style(file_path)
    widgets_dict["file_path"] = file_path
    file_row.addWidget(file_path, 1)

    browse_btn = ModernButton("...", style=ModernButton.Style.Secondary)
    browse_btn.setFixedSize(40, 30)
    browse_btn.clicked.connect(
        lambda checked=False, w=widgets_dict: self.browse_single_watermark_source(w["index"])
    )
    file_row.addWidget(browse_btn)

    file_mode_btn = ModernButton(t("common.option.file", "文件"), style=ModernButton.Style.Secondary, icon_name="file")
    file_mode_btn.setFixedHeight(30)
    file_mode_btn.setMinimumWidth(88)
    file_mode_btn.setToolTip(t("batch.add_watermark_tab.tooltip.file_mode", "当前：文件模式（点击切换到文件夹模式）"))
    file_mode_btn.clicked.connect(
        lambda checked=False, w=widgets_dict: self.toggle_single_file_mode(w["index"])
    )
    widgets_dict["file_mode_btn"] = file_mode_btn
    widgets_dict["file_mode"] = "file"
    file_row.addWidget(file_mode_btn)
    
    image_layout.addWidget(create_param_row(t("batch.add_watermark_tab.label.file", "水印文件:"), file_row))

    # 位置 & 选项
    pos_grid = QGridLayout()
    pos_grid.setSpacing(10)
    
    position_combo = QComboBox()
    for code in (
        "top_right",
        "top_left",
        "bottom_right",
        "bottom_left",
        "center",
        "custom",
    ):
        position_combo.addItem(enum_label(TEXT_POSITION_LABELS, code, current_lang), code)
    ModernInput.apply_style(position_combo)
    widgets_dict["position_combo"] = position_combo
    
    # 组合 Checkbox
    checks_layout = QHBoxLayout()
    random_check = QCheckBox(t("common.option.random_select", "随机选取"))
    random_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    random_check.setEnabled(False)
    random_check.setChecked(False)
    widgets_dict["random_check"] = random_check
    checks_layout.addWidget(random_check)
    
    image_layout.addWidget(create_param_row(t("common.label.position", "位置:"), position_combo))
    image_layout.addWidget(create_param_row(t("common.label.options", "选项:"), checks_layout))

    # 偏移 & 透明度
    offset_layout = QHBoxLayout()
    offset_layout.setSpacing(8)
    
    offset_x = QSpinBox()
    offset_x.setRange(-9999, 9999)
    offset_x.setValue(6)
    offset_x.setFixedWidth(70)
    ModernInput.apply_style(offset_x)
    widgets_dict["offset_x"] = offset_x
    
    offset_y = QSpinBox()
    offset_y.setRange(-9999, 9999)
    offset_y.setValue(6)
    offset_y.setFixedWidth(70)
    ModernInput.apply_style(offset_y)
    widgets_dict["offset_y"] = offset_y
    
    offset_layout.addWidget(QLabel(t("common.axis.x", "X:")))
    offset_layout.addWidget(offset_x)
    offset_layout.addWidget(QLabel(t("common.axis.y", "Y:")))
    offset_layout.addWidget(offset_y)
    offset_layout.addStretch()
    
    image_layout.addWidget(create_param_row(t("batch.add_watermark_tab.label.boundary_offset", "边界偏移:"), offset_layout))
    
    opacity = QDoubleSpinBox()
    opacity.setRange(0, 1)
    opacity.setSingleStep(0.01)
    opacity.setValue(1.0)
    opacity.setFixedWidth(70)
    ModernInput.apply_style(opacity)
    widgets_dict["opacity"] = opacity
    image_layout.addWidget(create_param_row(t("common.label.opacity", "不透明度:"), opacity))

    widgets_dict["image_widget"] = image_widget
    card_layout.addWidget(image_widget)

    # ==== 文字水印配置 ====
    text_widget = QWidget()
    text_layout = QVBoxLayout(text_widget)
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(10)

    text_content = QLineEdit()
    text_content.setPlaceholderText(t("batch.add_watermark_tab.placeholder.text", "输入水印文字..."))
    ModernInput.apply_style(text_content)
    widgets_dict["text_content"] = text_content
    text_layout.addWidget(create_param_row(t("batch.add_watermark_tab.label.text_content", "文字内容:"), text_content))

    text_position = QComboBox()
    for code in (
        "top_right",
        "top_left",
        "bottom_right",
        "bottom_left",
        "center",
        "custom",
    ):
        text_position.addItem(enum_label(TEXT_POSITION_LABELS, code, current_lang), code)
    ModernInput.apply_style(text_position)
    widgets_dict["text_position"] = text_position
    text_layout.addWidget(create_param_row(t("common.label.position", "位置:"), text_position))
    
    text_opacity = QDoubleSpinBox()
    text_opacity.setRange(0, 1)
    text_opacity.setSingleStep(0.1)
    text_opacity.setValue(1.0)
    text_opacity.setFixedWidth(70)
    ModernInput.apply_style(text_opacity)
    widgets_dict["text_opacity"] = text_opacity
    text_layout.addWidget(create_param_row(t("common.label.opacity", "不透明度:"), text_opacity))

    widgets_dict["text_widget"] = text_widget
    text_widget.setVisible(False)
    card_layout.addWidget(text_widget)

    # ==== 操作按钮区域 ====
    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(10)

    style_btn = ModernButton(t("batch.add_watermark_tab.btn.style", "样式设置"), style=ModernButton.Style.Outline, icon_name="settings")
    style_btn.clicked.connect(
        lambda checked=False, w=widgets_dict: self.open_single_watermark_style(w["index"])
    )
    btn_layout.addWidget(style_btn)

    position_btn = ModernButton(t("batch.add_watermark_tab.btn.manual_position", "手动定位"), style=ModernButton.Style.Outline, icon_name="move")
    position_btn.clicked.connect(
        lambda checked=False, w=widgets_dict: self.open_single_position_selector(w["index"])
    )
    btn_layout.addWidget(position_btn)

    # 预览按钮
    preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
    preview_btn.clicked.connect(
        lambda checked=False, w=widgets_dict: self.preview_cumulative_watermark(w["index"])
    )
    widgets_dict["preview_btn"] = preview_btn
    btn_layout.addWidget(preview_btn)

    # 删除按钮
    if index > 0:
        delete_btn = ModernButton(t("common.btn.delete", "删除"), style=ModernButton.Style.Danger, icon_name="trash")
        delete_btn.setFixedWidth(80)
        delete_btn.clicked.connect(
            lambda checked=False, w=widgets_dict: self.delete_single_watermark(w["index"])
        )
        widgets_dict["delete_btn"] = delete_btn
        btn_layout.addWidget(delete_btn)

    btn_layout.addStretch()
    card_layout.addLayout(btn_layout)

    # 添加到容器
    self.watermark_container_layout.addWidget(card)

    # 保存引用并初始化
    self.watermark_widgets.append(widgets_dict)
    self._ensure_watermark_config(index)
    self._connect_watermark_widget_signals(widgets_dict)
    self._sync_watermark_config_from_widget(widgets_dict)
    apply_language_to_widget(card)
