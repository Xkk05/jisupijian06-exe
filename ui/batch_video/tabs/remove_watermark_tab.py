from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from ui.components import ModernCard, ToggleSwitch, ModernButton, ModernInput
from ui.i18n import t
from ui.theme import Theme


def create_remove_watermark_tab(self) -> QWidget:
    """创建去水印标签页 - 现代卡片风格"""
    # 主滚动区域
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll_area.setStyleSheet("""
        QScrollArea {
            background: transparent;
            border: none;
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
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    # 内容容器
    content_widget = QWidget()
    content_widget.setStyleSheet("""
        background: transparent;
        QLabel {
            font-size: 13px;
            font-weight: normal;
        }
    """)
    layout = QVBoxLayout(content_widget)
    layout.setSpacing(15)
    layout.setContentsMargins(5, 5, 5, 5)

    # ==================== 功能开关卡片 ====================
    # 以前是单纯的 QCheckBox，现在我们把它做成一个 Header Card
    header_card = ModernCard(parent=content_widget)
    header_layout = header_card.layout  # QVBoxLayout
    header_layout.setContentsMargins(20, 15, 20, 15)

    switch_layout = QHBoxLayout()

    enable_label = QLabel(t("batch.remove_watermark_tab.enable", "启用去水印功能"))
    enable_label.setStyleSheet(
        f"font-size: 13px; font-weight: bold; color: {Theme.TextPrimary};"
    )
    switch_layout.addWidget(enable_label)

    switch_layout.addStretch()

    self.remove_watermark_check = ToggleSwitch()
    self.remove_watermark_check.toggled.connect(self.on_remove_watermark_check_changed)
    switch_layout.addWidget(self.remove_watermark_check)

    header_layout.addLayout(switch_layout)
    layout.addWidget(header_card)

    # ==================== 方法说明（无卡片UI） ====================
    method_row_widget = QWidget()
    method_row_layout = QHBoxLayout(method_row_widget)
    method_row_layout.setContentsMargins(10, 0, 10, 0)
    method_row_layout.setSpacing(10)

    method_label = QLabel(t("batch.remove_watermark_tab.method", "去水印方法:"))
    method_label.setStyleSheet(
        f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;"
    )
    method_row_layout.addWidget(method_label)

    self.watermark_method_combo = QComboBox(method_row_widget)
    self.watermark_method_combo.addItems(
        [
            t("batch.remove_watermark_tab.method.choose", "请选中您需要的使用场景"),
            t("batch.remove_watermark_tab.method.ffmpeg_delogo", "静态水印-FFMPEG-DELOGO"),
        ]
    )
    self.watermark_method_combo.setCurrentIndex(1)
    self.watermark_method_combo.setEnabled(False)
    self.watermark_method_combo.setVisible(False)
    ModernInput.apply_style(self.watermark_method_combo)

    # 静态展示（避免无意义下拉框）
    self.watermark_method_display = QLabel(
        t("batch.remove_watermark_tab.method.ffmpeg_delogo", "静态水印-FFMPEG-DELOGO")
    )
    self.watermark_method_display.setStyleSheet(
        f"background: {Theme.Surface}; border: 1px solid {Theme.Border}; border-radius: 6px; "
        f"padding: 6px 10px; color: {Theme.TextDisabled}; font-size: 13px;"
    )
    self.watermark_method_display.setMinimumHeight(28)
    method_row_layout.addWidget(self.watermark_method_display, 1)

    method_note = QLabel(
        t(
            "batch.remove_watermark_tab.method.note",
            "这是 FFmpeg 的 delogo 滤镜检测方法",
        )
    )
    method_note.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 12px;")
    method_row_layout.addWidget(method_note)

    # 连接信号
    self.watermark_method_combo.currentIndexChanged.connect(
        self.on_watermark_method_changed
    )

    layout.addWidget(method_row_widget)

    # ==================== 区域设置卡片 ====================
    self.region_group = ModernCard(
        t("batch.remove_watermark_tab.region.title", "水印区域设置"),
        parent=content_widget,
    )
    self.region_group.setVisible(True)
    region_layout = self.region_group.layout

    # 区域数量与预设
    region_top_layout = QHBoxLayout()

    count_label = QLabel(t("batch.remove_watermark_tab.region.count", "区域数量:"))
    count_label.setStyleSheet(
        f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;"
    )
    region_top_layout.addWidget(count_label)

    self.region_count_combo = QComboBox()
    self.region_count_combo.addItems(
        [
            t("batch.remove_watermark_tab.region.count.1", "1个区域"),
            t("batch.remove_watermark_tab.region.count.2", "2个区域"),
            t("batch.remove_watermark_tab.region.count.3", "3个区域"),
        ]
    )
    self.region_count_combo.setEnabled(False)
    ModernInput.apply_style(self.region_count_combo)
    self.region_count_combo.currentIndexChanged.connect(self.on_region_count_changed)
    region_top_layout.addWidget(self.region_count_combo)

    region_top_layout.addSpacing(20)

    preset_label = QLabel(t("batch.remove_watermark_tab.region.preset", "平台预设:"))
    preset_label.setStyleSheet(
        f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;"
    )
    region_top_layout.addWidget(preset_label)

    self.watermark_preset = QComboBox()
    # ... 添加 items (省略长列表，保持原逻辑) ...
    presets = [
        t("batch.remove_watermark_tab.region.preset.custom", "自定义"),
        t("batch.remove_watermark_tab.region.preset.bilibili_top_right", "B站 - 右上角"),
        t("batch.remove_watermark_tab.region.preset.douyin_bottom_right", "抖音 - 右下角"),
        t(
            "batch.remove_watermark_tab.region.preset.xiaohongshu_bottom_right",
            "小红书 - 右下角",
        ),
        t("batch.remove_watermark_tab.region.preset.iqiyi_top_right", "爱奇艺 - 右上角"),
        t(
            "batch.remove_watermark_tab.region.preset.youtube_bottom_left",
            "YouTube - 左下角",
        ),
        t("batch.remove_watermark_tab.region.preset.tiktok_bottom_right", "TikTok - 右下角"),
        t("batch.remove_watermark_tab.region.preset.weibo_bottom_right", "微博 - 右下角"),
        t(
            "batch.remove_watermark_tab.region.preset.tencent_video_top_right",
            "腾讯视频 - 右上角",
        ),
        t("batch.remove_watermark_tab.region.preset.kuaishou_bottom_right", "快手 - 右下角"),
        t("batch.remove_watermark_tab.region.preset.xigua_top_right", "西瓜视频 - 右上角"),
        t("batch.remove_watermark_tab.region.preset.toutiao_bottom_right", "今日头条 - 右下角"),
        t(
            "batch.remove_watermark_tab.region.preset.netease_music_bottom_left",
            "网易云音乐 - 左下角",
        ),
        t("batch.remove_watermark_tab.region.preset.youku_top_right", "优酷 - 右上角"),
        t("batch.remove_watermark_tab.region.preset.sohu_bottom_right", "搜狐视频 - 右下角"),
        t("batch.remove_watermark_tab.region.preset.letv_top_right", "乐视视频 - 右上角"),
        t("batch.remove_watermark_tab.region.preset.migu_bottom_right", "咪咕视频 - 右下角"),
        t("batch.remove_watermark_tab.region.preset.acfun_top_right", "AcFun - 右上角"),
        t(
            "batch.remove_watermark_tab.region.preset.bilibili_bottom_left",
            "哔哩哔哩 - 左下角",
        ),
        t("batch.remove_watermark_tab.region.preset.zhihu_bottom_right", "知乎 - 右下角"),
        t("batch.remove_watermark_tab.region.preset.douban_top_right", "豆瓣 - 右上角"),
    ]
    self.watermark_preset.addItems(presets)
    self.watermark_preset.setEnabled(False)
    ModernInput.apply_style(self.watermark_preset)
    self.watermark_preset.currentIndexChanged.connect(self.apply_watermark_preset)
    region_top_layout.addWidget(self.watermark_preset, 1)

    region_layout.addLayout(region_top_layout)

    # 预设提示
    self.preset_hint_label = QLabel(
        t("batch.remove_watermark_tab.region.preset_hint", "如效果不理想，请手动微调。")
    )
    self.preset_hint_label.setStyleSheet(
        f"color: {Theme.Warning}; font-size: 13px; font-weight: normal;"
    )
    self.preset_hint_label.setVisible(False)
    region_layout.addWidget(self.preset_hint_label)

    region_layout.addSpacing(10)

    # 区域具体参数 (使用 grid layout)
    # 封装一个辅助函数来创建区域行
    def create_region_row(index, layout_grid):
        """创建单个区域的配置行"""
        base_row = (index - 1) * 2  # 每一组占用2行或者1行紧凑

        # 标题
        lbl = QLabel(
            t("batch.remove_watermark_tab.region.index", "区域 {index}").format(index=index)
        )
        lbl.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {Theme.TextPrimary};"
        )
        layout_grid.addWidget(lbl, index - 1, 0)

        # 参数容器
        params_widget = QWidget()
        params_layout = QHBoxLayout(params_widget)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.setSpacing(10)

        # X
        params_layout.addWidget(QLabel("X"))
        spin_x = QSpinBox()
        spin_x.setRange(0, 9999)
        ModernInput.apply_style(spin_x)
        params_layout.addWidget(spin_x)

        # Y
        params_layout.addWidget(QLabel("Y"))
        spin_y = QSpinBox()
        spin_y.setRange(0, 9999)
        ModernInput.apply_style(spin_y)
        params_layout.addWidget(spin_y)

        # W
        params_layout.addWidget(QLabel("W"))
        spin_w = QSpinBox()
        spin_w.setRange(0, 9999)
        ModernInput.apply_style(spin_w)
        params_layout.addWidget(spin_w)

        # H
        params_layout.addWidget(QLabel("H"))
        spin_h = QSpinBox()
        spin_h.setRange(0, 9999)
        ModernInput.apply_style(spin_h)
        params_layout.addWidget(spin_h)

        # Select Button
        btn = ModernButton(
            t("batch.remove_watermark_tab.region.select", "选区"),
            ModernButton.Style.Outline,
        )
        btn.setFixedWidth(60)
        btn.clicked.connect(lambda: self.open_region_selector(index))
        params_layout.addWidget(btn)

        layout_grid.addWidget(params_widget, index - 1, 1)

        return spin_x, spin_y, spin_w, spin_h, btn, params_widget, lbl

    # 创建 Grid
    regions_grid = QGridLayout()
    regions_grid.setVerticalSpacing(10)

    # 区域 1
    (
        self.region1_x,
        self.region1_y,
        self.region1_w,
        self.region1_h,
        self.region1_select_btn,
        self.region1_widget,
        self.region1_label,
    ) = create_region_row(1, regions_grid)

    # 区域 2
    (
        self.region2_x,
        self.region2_y,
        self.region2_w,
        self.region2_h,
        self.region2_select_btn,
        self.region2_widget,
        self.region2_label,
    ) = create_region_row(2, regions_grid)
    self.region2_widget.setVisible(False)
    self.region2_label.setVisible(False)

    # 区域 3
    (
        self.region3_x,
        self.region3_y,
        self.region3_w,
        self.region3_h,
        self.region3_select_btn,
        self.region3_widget,
        self.region3_label,
    ) = create_region_row(3, regions_grid)
    self.region3_widget.setVisible(False)
    self.region3_label.setVisible(False)

    # 设置默认值
    self.region1_x.setValue(10)
    self.region1_y.setValue(10)
    self.region1_w.setValue(200)
    self.region1_h.setValue(100)
    self.region2_x.setValue(860)
    self.region2_y.setValue(490)
    self.region2_w.setValue(200)
    self.region2_h.setValue(100)
    self.region3_x.setValue(1720)
    self.region3_y.setValue(10)
    self.region3_w.setValue(200)
    self.region3_h.setValue(100)

    # 禁用所有
    for w in [
        self.region1_x,
        self.region1_y,
        self.region1_w,
        self.region1_h,
        self.region1_select_btn,
        self.region2_x,
        self.region2_y,
        self.region2_w,
        self.region2_h,
        self.region2_select_btn,
        self.region3_x,
        self.region3_y,
        self.region3_w,
        self.region3_h,
        self.region3_select_btn,
    ]:
        w.setEnabled(False)

    region_layout.addLayout(regions_grid)

    # 裁剪冲突提示：当裁剪会覆盖去水印区域时给出实时提醒
    self.crop_rm_conflict_label = QLabel("")
    self.crop_rm_conflict_label.setStyleSheet(
        f"color: {Theme.Warning}; font-size: 12px; font-weight: normal;"
    )
    self.crop_rm_conflict_label.setWordWrap(True)
    self.crop_rm_conflict_label.setVisible(False)
    region_layout.addWidget(self.crop_rm_conflict_label)

    for spin in [
        self.region1_x,
        self.region1_y,
        self.region1_w,
        self.region1_h,
        self.region2_x,
        self.region2_y,
        self.region2_w,
        self.region2_h,
        self.region3_x,
        self.region3_y,
        self.region3_w,
        self.region3_h,
    ]:
        spin.valueChanged.connect(
            lambda _=None: self._update_crop_remove_watermark_conflict_hint()
            if hasattr(self, "_update_crop_remove_watermark_conflict_hint")
            else None
        )

    layout.addWidget(self.region_group)

    # ==================== 时间段设置卡片 ====================
    self.time_period_group = ModernCard(
        t("batch.remove_watermark_tab.time.title", "去水印时间段"),
        parent=content_widget,
    )
    self.time_period_group.setVisible(True)
    time_layout = self.time_period_group.layout

    time_row = QHBoxLayout()

    self.time_period_enable_check = QCheckBox(
        t("batch.remove_watermark_tab.time.enable", "启用时间段限制")
    )
    self.time_period_enable_check.setStyleSheet(
        f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;"
    )
    self.time_period_enable_check.toggled.connect(self.on_time_period_enable_changed)
    self.time_period_enable_check.setEnabled(False)
    time_row.addWidget(self.time_period_enable_check)

    self.time_period_select_btn = ModernButton(
        t("batch.remove_watermark_tab.time.select", "选择时间"),
        ModernButton.Style.Outline,
        icon_name="clock",
    )
    self.time_period_select_btn.clicked.connect(self.open_time_period_selector)
    self.time_period_select_btn.setEnabled(False)
    time_row.addWidget(self.time_period_select_btn)

    self.time_period_display = QLabel(t("batch.remove_watermark_tab.time.unset", "未设置"))
    self.time_period_display.setStyleSheet(
        f"background: {Theme.Background}; padding: 4px 8px; border-radius: 4px; "
        f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;"
    )
    self.time_period_display.setEnabled(False)
    time_row.addWidget(self.time_period_display)

    time_row.addStretch()
    time_layout.addLayout(time_row)
    layout.addWidget(self.time_period_group)

    # ==================== 高级设置卡片 (FFmpeg / OpenCV) ====================
    # 这里我们只创建容器，具体的子控件逻辑较多，我们只展示 FFmpeg 的改造示例
    # 其他组 (OpenCV) 逻辑类似，需要全部迁移

    # 1. FFmpeg
    self.ffmpeg_group = ModernCard(
        t("batch.remove_watermark_tab.ffmpeg.title", "FFmpeg 高级设置"),
        parent=content_widget,
    )
    self.ffmpeg_group.setVisible(True)
    ffmpeg_inner = self.ffmpeg_group.layout

    # CRF
    crf_row = QHBoxLayout()
    crf_row.addWidget(QLabel(t("batch.remove_watermark_tab.ffmpeg.crf", "输出质量 (CRF):")))
    self.ffmpeg_crf = QSpinBox()
    self.ffmpeg_crf.setRange(0, 51)
    self.ffmpeg_crf.setValue(18)
    self.ffmpeg_crf.setEnabled(False)
    ModernInput.apply_style(self.ffmpeg_crf)
    crf_row.addWidget(self.ffmpeg_crf)
    crf_row.addWidget(
        QLabel(t("batch.remove_watermark_tab.ffmpeg.crf_hint", "(0-51, 越小越好)"))
    )
    crf_row.addStretch()
    ffmpeg_inner.addLayout(crf_row)

    # Preset
    preset_row = QHBoxLayout()
    preset_row.addWidget(QLabel(t("batch.remove_watermark_tab.ffmpeg.preset", "编码速度:")))
    self.ffmpeg_preset = QComboBox()
    self.ffmpeg_preset.addItems(
        [
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ]
    )
    self.ffmpeg_preset.setCurrentText("medium")
    self.ffmpeg_preset.setEnabled(False)
    ModernInput.apply_style(self.ffmpeg_preset)
    preset_row.addWidget(self.ffmpeg_preset)
    preset_row.addStretch()
    ffmpeg_inner.addLayout(preset_row)

    layout.addWidget(self.ffmpeg_group)

    # 2. OpenCV Group
    self.opencv_group = ModernCard(
        t("batch.remove_watermark_tab.opencv.title", "OpenCV 设置"),
        parent=content_widget,
    )
    self.opencv_group.setVisible(False)
    cv_inner = self.opencv_group.layout

    cv_method_row = QHBoxLayout()
    cv_method_row.addWidget(QLabel(t("batch.remove_watermark_tab.opencv.method", "处理方式:")))
    self.opencv_method = QComboBox()
    self.opencv_method.addItems(
        [
            t("batch.remove_watermark_tab.opencv.method.copy", "自动背景复制"),
            t("batch.remove_watermark_tab.opencv.method.gaussian", "高斯模糊"),
        ]
    )
    self.opencv_method.setEnabled(False)
    ModernInput.apply_style(self.opencv_method)
    self.opencv_method.currentIndexChanged.connect(self._on_opencv_method_changed)
    cv_method_row.addWidget(self.opencv_method, 1)
    cv_inner.addLayout(cv_method_row)

    # Blur strength
    self.opencv_blur_strength_label = QLabel(
        t("batch.remove_watermark_tab.opencv.blur_strength", "模糊强度:")
    )
    self.opencv_blur_strength = QSpinBox()
    self.opencv_blur_strength.setRange(1, 10)
    self.opencv_blur_strength.setValue(3)
    ModernInput.apply_style(self.opencv_blur_strength)
    # 默认隐藏，在回调中控制
    self.opencv_blur_strength_label.setVisible(False)
    self.opencv_blur_strength.setVisible(False)

    cv_blur_row = QHBoxLayout()
    cv_blur_row.addWidget(self.opencv_blur_strength_label)
    cv_blur_row.addWidget(self.opencv_blur_strength)
    cv_blur_row.addStretch()
    cv_inner.addLayout(cv_blur_row)

    layout.addWidget(self.opencv_group)

    # 3. API Group
    self.api_group = ModernCard(
        t("batch.remove_watermark_tab.api.title", "API 设置"),
        parent=content_widget,
    )
    self.api_group.setVisible(False)
    api_inner = self.api_group.layout

    api_prov_row = QHBoxLayout()
    api_prov_row.addWidget(QLabel(t("batch.remove_watermark_tab.api.provider", "提供商:")))
    self.api_provider = QComboBox()
    self.api_provider.addItems(
        [
            t("batch.remove_watermark_tab.api.provider.aliyun", "阿里云"),
            t("batch.remove_watermark_tab.api.provider.tencent", "腾讯云"),
            t("batch.remove_watermark_tab.api.provider.baidu", "百度云"),
            t("batch.remove_watermark_tab.api.provider.volcengine", "火山引擎"),
            "Segmind",
            "Unwatermark",
        ]
    )
    self.api_provider.setEnabled(False)
    ModernInput.apply_style(self.api_provider)
    api_prov_row.addWidget(self.api_provider, 1)
    api_inner.addLayout(api_prov_row)

    api_key_row = QHBoxLayout()
    api_key_row.addWidget(QLabel("API Key:"))
    self.api_key = QLineEdit()
    self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
    self.api_key.setEnabled(False)
    ModernInput.apply_style(self.api_key)
    api_key_row.addWidget(self.api_key, 1)
    api_inner.addLayout(api_key_row)
    layout.addWidget(self.api_group)

    # 6. Text Remover Group
    self.textremover_group = ModernCard(
        t("batch.remove_watermark_tab.text_remover.title", "文字去除设置"),
        parent=content_widget,
    )
    self.textremover_group.setVisible(False)
    tr_inner = self.textremover_group.layout

    tr_method_row = QHBoxLayout()
    tr_method_row.addWidget(QLabel(t("batch.remove_watermark_tab.text_remover.method", "方式:")))
    self.textremover_method = QComboBox()
    self.textremover_method.addItems(
        [
            t("batch.remove_watermark_tab.text_remover.method.copy", "背景复制"),
            t("batch.remove_watermark_tab.text_remover.method.gaussian", "高斯模糊"),
        ]
    )
    self.textremover_method.setEnabled(False)
    ModernInput.apply_style(self.textremover_method)
    self.textremover_method.currentIndexChanged.connect(
        self._on_textremover_method_changed
    )
    tr_method_row.addWidget(self.textremover_method, 1)
    tr_inner.addLayout(tr_method_row)

    self.textremover_blur_strength_label = QLabel(
        t("batch.remove_watermark_tab.text_remover.strength", "强度:")
    )
    self.textremover_blur_strength = QSpinBox()
    self.textremover_blur_strength.setRange(1, 10)
    self.textremover_blur_strength.setValue(3)
    self.textremover_blur_strength.setEnabled(False)
    ModernInput.apply_style(self.textremover_blur_strength)
    self.textremover_blur_strength_label.setVisible(False)
    self.textremover_blur_strength.setVisible(False)

    tr_blur_row = QHBoxLayout()
    tr_blur_row.addWidget(self.textremover_blur_strength_label)
    tr_blur_row.addWidget(self.textremover_blur_strength)
    tr_blur_row.addStretch()
    tr_inner.addLayout(tr_blur_row)

    layout.addWidget(self.textremover_group)

    # ==================== 预览按钮 ====================
    preview_layout = QHBoxLayout()
    self.watermark_preview_btn = ModernButton(
        t("batch.remove_watermark_tab.preview", "预览效果"),
        ModernButton.Style.Outline,
        parent=content_widget,
        icon_name="eye",
    )
    self.watermark_preview_btn.setEnabled(False)
    self.watermark_preview_btn.setVisible(True)
    self.watermark_preview_btn.clicked.connect(self.preview_watermark_removal)
    preview_layout.addWidget(self.watermark_preview_btn)
    preview_layout.addStretch()
    layout.addLayout(preview_layout)

    layout.addStretch()

    scroll_area.setWidget(content_widget)
    self.watermark_scroll_area = scroll_area

    # 包装在 Widget 中返回
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)

    return container
