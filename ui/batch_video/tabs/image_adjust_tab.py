from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QWidget, QHBoxLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QPushButton, QComboBox,
    QRadioButton, QButtonGroup, QGridLayout, QFrame
)
from ui.components import (
    ModernCard, ToggleSwitch, ModernInput, ModernButton, create_modern_scroll_area
)
from ui.theme import Theme
from ui.i18n import t

def create_image_adjust_tab(self) -> QWidget:
    """创建画面调整标签页 - 现代极简风格"""
    
    # --- 辅助函数：创建分节标题行 (标签 + 开关) ---
    def create_section_header(text, switch_widget=None):
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

    # --- 内容容器 ---
    content_widget = QWidget()
    content_widget.setStyleSheet("background: transparent;")
    main_layout = QVBoxLayout(content_widget)
    main_layout.setSpacing(20) # 增加卡片间距
    # 增加底部 Margin 防止圆角被裁剪；左右 Margin 设为 0 以对齐底部面板
    main_layout.setContentsMargins(0, 10, 0, 20)
    
    # --- 主滚动区域 ---
    scroll_area = create_modern_scroll_area(content_widget)

    # ==================== 1. 画面微调部分 ====================
    frame_card = ModernCard()
    frame_layout = frame_card.layout # 获取 ModernCard 的布局
    frame_layout.setSpacing(15)
    
    # 标题 + 开关
    self.frame_adjust_check = ToggleSwitch()
    header = create_section_header(
        t("batch.image_adjust_tab.section.frame_adjust", "画面微调 (随机微调)"),
        self.frame_adjust_check,
    )
    frame_layout.addWidget(header)
    
    # 参数区域 (Grid)
    params_grid = QGridLayout()
    params_grid.setHorizontalSpacing(10)
    params_grid.setVerticalSpacing(12)
    # 增加最后一列的拉伸因子，使左侧内容紧凑，避免间隔过大
    params_grid.setColumnStretch(4, 1)
    
    # 辅助：创建范围输入控件对
    def create_range_input(row_idx, label, min_widget, max_widget):
        l = QLabel(label)
        l.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
        params_grid.addWidget(l, row_idx, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0,0,0,0)
        h.setSpacing(5)
        
        ModernInput.apply_style(min_widget)
        min_widget.setFixedWidth(80)
        min_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(min_widget)
        
        sep = QLabel("~")
        sep.setStyleSheet(f"color: {Theme.TextDisabled}; font-size: 13px; font-weight: normal;")
        h.addWidget(sep)
        
        ModernInput.apply_style(max_widget)
        max_widget.setFixedWidth(80)
        max_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(max_widget)
        
        params_grid.addWidget(container, row_idx, 1, alignment=Qt.AlignmentFlag.AlignLeft)

    # 亮度
    self.brightness_min = QDoubleSpinBox()
    self.brightness_min.setRange(-1.0, 1.0)
    self.brightness_min.setSingleStep(0.01)
    self.brightness_min.setValue(-0.05)
    self.brightness_min.setDecimals(2)
    
    self.brightness_max = QDoubleSpinBox()
    self.brightness_max.setRange(-1.0, 1.0)
    self.brightness_max.setSingleStep(0.01)
    self.brightness_max.setValue(0.05)
    self.brightness_max.setDecimals(2)
    create_range_input(
        0, t("batch.image_adjust_tab.param.brightness", "亮度"), self.brightness_min, self.brightness_max
    )
    
    # 对比度
    self.contrast_min = QDoubleSpinBox()
    self.contrast_min.setRange(-2.0, 2.0)
    self.contrast_min.setSingleStep(0.01)
    self.contrast_min.setValue(0.95)
    self.contrast_min.setDecimals(2)
    
    self.contrast_max = QDoubleSpinBox()
    self.contrast_max.setRange(-2.0, 2.0)
    self.contrast_max.setSingleStep(0.01)
    self.contrast_max.setValue(1.05)
    self.contrast_max.setDecimals(2)
    create_range_input(
        1, t("batch.image_adjust_tab.param.contrast", "对比度"), self.contrast_min, self.contrast_max
    )
    
    # 饱和度
    self.saturation_min = QDoubleSpinBox()
    self.saturation_min.setRange(0.0, 3.0)
    self.saturation_min.setSingleStep(0.01)
    self.saturation_min.setValue(0.95)
    self.saturation_min.setDecimals(2)
    
    self.saturation_max = QDoubleSpinBox()
    self.saturation_max.setRange(0.0, 3.0)
    self.saturation_max.setSingleStep(0.01)
    self.saturation_max.setValue(1.05)
    self.saturation_max.setDecimals(2)
    create_range_input(
        2, t("batch.image_adjust_tab.param.saturation", "饱和度"), self.saturation_min, self.saturation_max
    )

    # 锐化 (右侧列)
    self.sharpness_min = QDoubleSpinBox()
    self.sharpness_min.setRange(-2.0, 5.0)
    self.sharpness_min.setSingleStep(0.1)
    self.sharpness_min.setValue(1.0)
    self.sharpness_min.setDecimals(1)
    
    self.sharpness_max = QDoubleSpinBox()
    self.sharpness_max.setRange(-2.0, 5.0)
    self.sharpness_max.setSingleStep(0.1)
    self.sharpness_max.setValue(1.2)
    self.sharpness_max.setDecimals(1)
    
    # 将锐化放在第0行第2列
    l_sharp = QLabel(t("batch.image_adjust_tab.param.sharpness", "锐化"))
    l_sharp.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal; margin-left: 20px;")
    params_grid.addWidget(l_sharp, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
    
    container_sharp = QWidget()
    h_sharp = QHBoxLayout(container_sharp)
    h_sharp.setContentsMargins(0,0,0,0)
    h_sharp.setSpacing(5)
    ModernInput.apply_style(self.sharpness_min)
    self.sharpness_min.setFixedWidth(80)
    self.sharpness_min.setAlignment(Qt.AlignmentFlag.AlignCenter)
    h_sharp.addWidget(self.sharpness_min)
    sep_sharp = QLabel("~")
    sep_sharp.setStyleSheet(f"color: {Theme.TextDisabled}; font-size: 13px; font-weight: normal;")
    h_sharp.addWidget(sep_sharp)
    ModernInput.apply_style(self.sharpness_max)
    self.sharpness_max.setFixedWidth(80)
    self.sharpness_max.setAlignment(Qt.AlignmentFlag.AlignCenter)
    h_sharp.addWidget(self.sharpness_max)
    params_grid.addWidget(container_sharp, 0, 3, alignment=Qt.AlignmentFlag.AlignLeft)
    
    # 降噪
    self.denoise_min = QSpinBox()
    self.denoise_min.setRange(0, 10)
    self.denoise_min.setValue(3)
    
    self.denoise_max = QSpinBox()
    self.denoise_max.setRange(0, 10)
    self.denoise_max.setValue(5)
    
    l_denoise = QLabel(t("batch.image_adjust_tab.param.denoise", "降噪"))
    l_denoise.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal; margin-left: 20px;")
    params_grid.addWidget(l_denoise, 1, 2, alignment=Qt.AlignmentFlag.AlignRight)
    
    container_denoise = QWidget()
    h_denoise = QHBoxLayout(container_denoise)
    h_denoise.setContentsMargins(0,0,0,0)
    h_denoise.setSpacing(5)
    ModernInput.apply_style(self.denoise_min)
    self.denoise_min.setFixedWidth(80)
    self.denoise_min.setAlignment(Qt.AlignmentFlag.AlignCenter)
    h_denoise.addWidget(self.denoise_min)
    sep_denoise = QLabel("~")
    sep_denoise.setStyleSheet(f"color: {Theme.TextDisabled}; font-size: 13px; font-weight: normal;")
    h_denoise.addWidget(sep_denoise)
    ModernInput.apply_style(self.denoise_max)
    self.denoise_max.setFixedWidth(80)
    self.denoise_max.setAlignment(Qt.AlignmentFlag.AlignCenter)
    h_denoise.addWidget(self.denoise_max)
    params_grid.addWidget(container_denoise, 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)

    frame_layout.addLayout(params_grid)
    
    # 效果按钮行
    effects_layout = QHBoxLayout()
    effects_layout.setSpacing(10)
    
    def create_effect_btn(text, slot, icon_name=None):
        btn = ModernButton(text, ModernButton.Style.Outline, icon_name=icon_name)
        btn.clicked.connect(slot)
        return btn
        
    self.color_tone_btn = create_effect_btn(
        t("batch.image_adjust_tab.btn.color_tone", "色调调节"),
        self.show_color_tone_dialog,
        icon_name="settings",
    )
    effects_layout.addWidget(self.color_tone_btn)
    
    self.lut_filter_btn = create_effect_btn(
        t("batch.image_adjust_tab.btn.lut_filter", "LUT滤镜"),
        self.show_lut_filter_dialog,
        icon_name="magic",
    )
    effects_layout.addWidget(self.lut_filter_btn)
    
    self.more_effects_btn = create_effect_btn(
        t("batch.image_adjust_tab.btn.more_effects", "更多效果"),
        self.show_more_effects_dialog,
        icon_name="magic",
    )
    effects_layout.addWidget(self.more_effects_btn)
    
    effects_layout.addStretch()
    
    # 预览按钮
    self.frame_adjust_preview_btn = ModernButton(
        t("common.btn.preview", "预览效果"),
        style=ModernButton.Style.Outline,
        icon_name="eye",
    )
    self.frame_adjust_preview_btn.clicked.connect(self.preview_frame_adjust_effect)
    effects_layout.addWidget(self.frame_adjust_preview_btn)
    
    frame_layout.addLayout(effects_layout)
    main_layout.addWidget(frame_card)
    
    # ==================== 2. 宫格分屏 ====================
    grid_card = ModernCard()
    grid_layout_inner = grid_card.layout
    
    self.grid_split_check = ToggleSwitch()
    grid_layout_inner.addWidget(
        create_section_header(
            t("batch.image_adjust_tab.section.grid_split", "宫格分屏"),
            self.grid_split_check,
        )
    )
    
    # 改用 Grid 布局以保证对齐
    grid_params = QGridLayout()
    grid_params.setHorizontalSpacing(15)
    grid_params.setVerticalSpacing(15)
    
    # 数量
    l_count = QLabel(t("common.label.count", "数量:"))
    l_count.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    grid_params.addWidget(l_count, 0, 0)
    
    self.grid_count = QSpinBox()
    self.grid_count.setRange(1, 9)
    self.grid_count.setValue(3)
    ModernInput.apply_style(self.grid_count)
    self.grid_count.setFixedWidth(80)
    grid_params.addWidget(self.grid_count, 0, 1)
    
    # 方向
    l_dir = QLabel(t("common.label.direction", "方向:"))
    l_dir.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    grid_params.addWidget(l_dir, 0, 2)
    
    self.grid_direction = QComboBox()
    self.grid_direction.addItems(
        [
            t("common.option.auto", "自动"),
            t("common.option.vertical", "上下"),
            t("common.option.horizontal", "左右"),
        ]
    )
    ModernInput.apply_style(self.grid_direction)
    self.grid_direction.setFixedWidth(100)
    grid_params.addWidget(self.grid_direction, 0, 3)
    
    # 两端虚化
    l_blur = QLabel(t("batch.image_adjust_tab.option.dual_side_blur", "两端虚化"))
    l_blur.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    grid_params.addWidget(l_blur, 0, 4)
    
    self.grid_blur_check = ToggleSwitch()
    grid_params.addWidget(self.grid_blur_check, 0, 5)
    
    # 预览按钮 (放在第6列)
    self.grid_preview_btn = ModernButton(
        t("common.btn.preview", "预览效果"),
        style=ModernButton.Style.Outline,
        icon_name="eye",
    )
    self.grid_preview_btn.clicked.connect(self.preview_grid_effect)
    grid_params.addWidget(self.grid_preview_btn, 0, 6)
    
    # 关键：设置最后一列拉伸，将所有控件挤向左侧
    grid_params.setColumnStretch(7, 1)
    
    grid_layout_inner.addLayout(grid_params)
    main_layout.addWidget(grid_card)

    # ==================== 3. 分辨率 & 模式 ====================
    res_card = ModernCard()
    res_layout = res_card.layout
    
    self.resolution_check = ToggleSwitch()
    res_layout.addWidget(
        create_section_header(
            t("batch.image_adjust_tab.section.resolution", "分辨率调整"),
            self.resolution_check,
        )
    )
    
    # 分辨率设置行 (改用 Grid 以固定位置)
    res_grid = QGridLayout()
    res_grid.setHorizontalSpacing(10)
    
    self.resolution_preset = QComboBox()
    self.resolution_preset.addItems(
        [
            t("common.option.custom", "自定义"),
            t("common.option.swap_width_height", "宽高互换"),
            "360P",
            "480P",
            "720P",
            "1080P",
        ]
    )
    ModernInput.apply_style(self.resolution_preset)
    self.resolution_preset.setFixedWidth(100)
    res_grid.addWidget(self.resolution_preset, 0, 0)
    
    self.resolution_width = QSpinBox()
    self.resolution_width.setRange(0, 9999)
    self.resolution_width.setValue(1920)
    ModernInput.apply_style(self.resolution_width)
    self.resolution_width.setFixedWidth(80)
    res_grid.addWidget(self.resolution_width, 0, 1)
    
    res_x_label = QLabel("x")
    res_x_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    res_grid.addWidget(res_x_label, 0, 2)
    
    self.resolution_height = QSpinBox()
    self.resolution_height.setRange(0, 9999)
    self.resolution_height.setValue(1080)
    ModernInput.apply_style(self.resolution_height)
    self.resolution_height.setFixedWidth(80)
    res_grid.addWidget(self.resolution_height, 0, 3)
    
    self.resolution_swap_btn = QPushButton("↔")
    self.resolution_swap_btn.setToolTip(
        t("batch.image_adjust_tab.tooltip.swap_resolution", "交换宽高")
    )
    self.resolution_swap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    self.resolution_swap_btn.setStyleSheet(f"""
        QPushButton {{
            border: 1px solid {Theme.Border};
            background: {Theme.Background};
            border-radius: 4px;
            padding: 4px 8px;
            color: {Theme.TextSecondary};
        }}
        QPushButton:hover {{
            background: {Theme.Border};
            color: {Theme.Primary};
        }}
    """)
    self.resolution_swap_btn.clicked.connect(self.swap_resolution)
    res_grid.addWidget(self.resolution_swap_btn, 0, 4)
    
    res_grid.setColumnStretch(5, 1) # 挤压左侧
    res_layout.addLayout(res_grid)
    
    # 模式选择
    mode_container = QFrame()
    mode_container.setStyleSheet(f"background: {Theme.Background}; border-radius: 8px; padding: 10px;")
    mode_layout = QVBoxLayout(mode_container)
    mode_layout.setSpacing(10)
    
    mode_title = QLabel(t("batch.image_adjust_tab.mode.title", "填充模式"))
    mode_title.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: bold;")
    mode_layout.addWidget(mode_title)
    
    radio_layout = QHBoxLayout()
    self.mode_stretch = QRadioButton(t("batch.image_adjust_tab.mode.stretch", "拉伸"))
    self.mode_crop = QRadioButton(t("batch.image_adjust_tab.mode.crop", "裁切"))
    self.mode_original = QRadioButton(t("batch.image_adjust_tab.mode.original", "原比例"))
    self.mode_original.setChecked(True)
    
    mode_group = QButtonGroup(self)
    mode_group.addButton(self.mode_stretch)
    mode_group.addButton(self.mode_crop)
    mode_group.addButton(self.mode_original)
    mode_group.buttonToggled.connect(self.on_resolution_mode_changed)
    
    for rb in [self.mode_stretch, self.mode_crop, self.mode_original]:
        rb.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
        radio_layout.addWidget(rb)
        
    radio_layout.addStretch()
    mode_layout.addLayout(radio_layout)
    
    # 背景与倒影选项
    extra_mode_layout = QHBoxLayout()
    
    # 背景模糊
    bg_container = QWidget()
    bg_h = QHBoxLayout(bg_container)
    bg_h.setContentsMargins(0,0,0,0)
    self.background_blur_check = ToggleSwitch() 
    bg_lbl = QLabel(t("batch.image_adjust_tab.option.background_blur", "背景模糊"))
    bg_lbl.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    bg_h.addWidget(self.background_blur_check) # 左对齐习惯
    bg_h.addWidget(bg_lbl)
    extra_mode_layout.addWidget(bg_container)
    
    extra_mode_layout.addSpacing(20)
    
    # 倒影
    ref_container = QWidget()
    ref_h = QHBoxLayout(ref_container)
    ref_h.setContentsMargins(0,0,0,0)
    self.reflection_check = ToggleSwitch()
    ref_lbl = QLabel(t("batch.image_adjust_tab.option.reflection", "倒影"))
    ref_lbl.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    ref_h.addWidget(self.reflection_check)
    ref_h.addWidget(ref_lbl)
    extra_mode_layout.addWidget(ref_container)
    
    self.reflection_opacity = QDoubleSpinBox()
    self.reflection_opacity.setRange(0.0, 1.0)
    self.reflection_opacity.setSingleStep(0.1)
    self.reflection_opacity.setValue(0.5)
    ModernInput.apply_style(self.reflection_opacity)
    self.reflection_opacity.setFixedWidth(60)
    self.reflection_opacity.setToolTip(
        t("batch.image_adjust_tab.tooltip.reflection_opacity", "倒影不透明度")
    )
    extra_mode_layout.addWidget(self.reflection_opacity)

    extra_mode_layout.addStretch()
    
    self.resolution_preview_btn = ModernButton(
        t("common.btn.preview", "预览效果"),
        style=ModernButton.Style.Outline,
        icon_name="eye",
    )
    self.resolution_preview_btn.clicked.connect(self.preview_resolution_effect)
    extra_mode_layout.addWidget(self.resolution_preview_btn)

    mode_layout.addLayout(extra_mode_layout)
    res_layout.addWidget(mode_container)
    
    main_layout.addWidget(res_card)

    # ==================== 4. 旋转与翻转 ====================
    rotate_card = ModernCard()
    rotate_layout = rotate_card.layout
    
    self.rotate_check = ToggleSwitch()
    rotate_layout.addWidget(
        create_section_header(
            t("batch.image_adjust_tab.section.rotate_flip", "旋转 & 翻转"),
            self.rotate_check,
        )
    )
    
    rot_grid = QGridLayout()
    
    self.flip_left90 = QRadioButton(t("batch.image_adjust_tab.rotate.left90", "左转90°"))
    self.flip_right90 = QRadioButton(t("batch.image_adjust_tab.rotate.right90", "右转90°"))
    self.flip_horizontal = QRadioButton(
        t("batch.image_adjust_tab.rotate.horizontal_flip", "水平翻转")
    )
    self.flip_vertical = QRadioButton(
        t("batch.image_adjust_tab.rotate.vertical_flip", "垂直翻转")
    )
    self.flip_random_direction = QRadioButton(
        t("batch.image_adjust_tab.rotate.random_direction", "随机方向")
    )
    self.flip_random = QRadioButton(
        t("batch.image_adjust_tab.rotate.random_angle", "随机角度")
    )
    
    rotate_group = QButtonGroup(self)
    for btn in [self.flip_left90, self.flip_right90, self.flip_horizontal, self.flip_vertical,
                self.flip_random_direction, self.flip_random]:
        rotate_group.addButton(btn)
        btn.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    
    rot_grid.addWidget(self.flip_left90, 0, 0)
    rot_grid.addWidget(self.flip_right90, 0, 1)
    rot_grid.addWidget(self.flip_horizontal, 0, 2)
    rot_grid.addWidget(self.flip_vertical, 1, 0)
    rot_grid.addWidget(self.flip_random_direction, 1, 1)
    rot_grid.addWidget(self.flip_random, 1, 2)
    
    # 关键：设置列拉伸，防止按钮随窗口变宽而移动
    rot_grid.setColumnStretch(3, 1)
    
    rotate_layout.addLayout(rot_grid)
    
    # 随机角度范围
    angle_row = QHBoxLayout()
    angle_row.setSpacing(8)
    
    angle_label = QLabel(
        t("batch.image_adjust_tab.rotate.random_angle_range", "随机角度:")
    )
    angle_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    angle_row.addWidget(angle_label)
    
    self.flip_random_angle = QDoubleSpinBox()
    self.flip_random_angle.setRange(-180.0, 180.0)
    self.flip_random_angle.setSingleStep(0.1)
    self.flip_random_angle.setValue(-1.0)
    self.flip_random_angle.setDecimals(1)
    ModernInput.apply_style(self.flip_random_angle)
    self.flip_random_angle.setFixedWidth(80)
    angle_row.addWidget(self.flip_random_angle)
    
    angle_sep = QLabel("~")
    angle_sep.setStyleSheet(f"color: {Theme.TextDisabled}; font-size: 13px; font-weight: normal;")
    angle_row.addWidget(angle_sep)
    
    self.flip_random_angle_max = QDoubleSpinBox()
    self.flip_random_angle_max.setRange(-180.0, 180.0)
    self.flip_random_angle_max.setSingleStep(0.1)
    self.flip_random_angle_max.setValue(1.0)
    self.flip_random_angle_max.setDecimals(1)
    ModernInput.apply_style(self.flip_random_angle_max)
    self.flip_random_angle_max.setFixedWidth(80)
    angle_row.addWidget(self.flip_random_angle_max)
    
    angle_row.addStretch()
    rotate_layout.addLayout(angle_row)
    
    # 额外选项 + 预览
    rotate_opts = QHBoxLayout()
    rotate_opts.setSpacing(12)
    
    self.flip_complete_check = ToggleSwitch()
    complete_label = QLabel(t("batch.image_adjust_tab.rotate.full_display", "完全显示"))
    complete_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    rotate_opts.addWidget(self.flip_complete_check)
    rotate_opts.addWidget(complete_label)
    
    self.flip_black_edge_check = ToggleSwitch()
    black_label = QLabel(
        t("batch.image_adjust_tab.rotate.remove_black_edge", "黑边去除")
    )
    black_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    rotate_opts.addWidget(self.flip_black_edge_check)
    rotate_opts.addWidget(black_label)
    
    rotate_opts.addStretch()
    
    self.rotate_preview_btn = ModernButton(
        t("common.btn.preview", "预览效果"),
        style=ModernButton.Style.Outline,
        icon_name="eye",
    )
    self.rotate_preview_btn.clicked.connect(self.preview_rotate_effect)
    rotate_opts.addWidget(self.rotate_preview_btn)
    
    rotate_layout.addLayout(rotate_opts)
    main_layout.addWidget(rotate_card)

    main_layout.addStretch()

    # 外层容器
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    
    # === 信号绑定与初始化状态 (保持业务逻辑一致性) ===
    
    # 画面微调
    self.frame_adjust_check.toggled.connect(self.on_frame_adjust_check_changed)
    # 默认禁用
    for w in [self.brightness_min, self.brightness_max, self.sharpness_min, self.sharpness_max,
              self.contrast_min, self.contrast_max, self.denoise_min, self.denoise_max,
              self.saturation_min, self.saturation_max, self.color_tone_btn, self.lut_filter_btn,
              self.more_effects_btn, self.frame_adjust_preview_btn]:
        w.setEnabled(False)
        
    # 宫格
    self.grid_split_check.toggled.connect(self.on_grid_split_check_changed)
    for w in [self.grid_count, self.grid_direction, self.grid_blur_check, self.grid_preview_btn]:
        w.setEnabled(False)
        
    # 分辨率
    self.resolution_check.toggled.connect(self.on_resolution_check_changed)
    self.resolution_preset.currentTextChanged.connect(self.on_resolution_preset_changed)
    for w in [self.resolution_preset, self.resolution_width, self.resolution_height, 
              self.resolution_swap_btn, self.mode_stretch, self.mode_crop, self.mode_original,
              self.background_blur_check, self.reflection_check, self.reflection_opacity, 
              self.resolution_preview_btn]:
        w.setEnabled(False)
        
    # 旋转
    self.rotate_check.toggled.connect(self.on_rotate_check_changed)
    self.flip_random.toggled.connect(self._update_rotate_random_controls)
    for w in [self.flip_left90, self.flip_right90, self.flip_horizontal, self.flip_vertical,
              self.flip_random_direction, self.flip_random,
              self.flip_random_angle, self.flip_random_angle_max, self.flip_complete_check,
              self.flip_black_edge_check, self.rotate_preview_btn]:
        w.setEnabled(False)

    return container
