from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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


def create_add_intro_outro_tab(self) -> QWidget:
    """创建加头尾标签页"""
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

    # 辅助函数：创建文件选择行
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

    def create_file_row(file_widget, browse_slot, mode_slot, random_check=None):
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        
        row_layout.addWidget(file_widget, 1)
        
        browse_btn = ModernButton(t("common.btn.choose_file", "选择文件"), style=ModernButton.Style.Secondary)
        browse_btn.setFixedSize(96, 32)
        browse_btn.clicked.connect(browse_slot)
        row_layout.addWidget(browse_btn)
        
        mode_btn = ModernButton(t("common.option.file", "文件"), style=ModernButton.Style.Secondary, icon_name="file")
        mode_btn.setFixedHeight(32)
        mode_btn.setMinimumWidth(88)
        mode_btn.setToolTip(t("common.tooltip.file_mode", "当前：文件模式（点击切换到文件夹模式）"))
        mode_btn.clicked.connect(mode_slot)
        mode_btn.setProperty("mode", "file")
        row_layout.addWidget(mode_btn)
        
        if random_check:
            row_layout.addSpacing(10)
            random_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
            row_layout.addWidget(random_check)
            
        return container, browse_btn, mode_btn

    # ==================== 1. 片头设置 ====================
    self.head_check = ToggleSwitch()
    self.head_check.toggled.connect(self.on_head_check_changed)
    
    head_card = ModernCard()
    head_layout = head_card.layout
    head_layout.addWidget(create_tab_section_header(t("batch.add_intro_outro_tab.head.title", "片头设置"), self.head_check))
    
    self.head_file = QLineEdit()
    self.head_file.setReadOnly(True)
    self.head_file.setPlaceholderText(t("batch.add_intro_outro_tab.head.placeholder", "未选择片头文件"))
    self.head_file.setEnabled(False)
    ModernInput.apply_style(self.head_file)
    
    self.head_random_check = QCheckBox(t("batch.audio_tab.option.random_apply", "随机应用"))
    self.head_random_check.setEnabled(False)
    
    head_row, self.head_browse_btn, self.head_mode_btn = create_file_row(
        self.head_file, 
        self.on_head_browse_clicked,
        self.on_head_mode_clicked,
        self.head_random_check
    )
    # 初始化禁用
    self.head_browse_btn.setEnabled(False)
    self.head_mode_btn.setEnabled(False)
    
    head_layout.addWidget(head_row)
    main_layout.addWidget(head_card)

    # ==================== 2. 片尾设置 ====================
    self.tail_check = ToggleSwitch()
    self.tail_check.toggled.connect(self.on_tail_check_changed)
    
    tail_card = ModernCard()
    tail_layout = tail_card.layout
    tail_layout.addWidget(create_tab_section_header(t("batch.add_intro_outro_tab.tail.title", "片尾设置"), self.tail_check))
    
    self.tail_file = QLineEdit()
    self.tail_file.setReadOnly(True)
    self.tail_file.setPlaceholderText(t("batch.add_intro_outro_tab.tail.placeholder", "未选择片尾文件"))
    self.tail_file.setEnabled(False)
    ModernInput.apply_style(self.tail_file)
    
    self.tail_random_check = QCheckBox(t("batch.audio_tab.option.random_apply", "随机应用"))
    self.tail_random_check.setEnabled(False)
    
    tail_row, self.tail_browse_btn, self.tail_mode_btn = create_file_row(
        self.tail_file, 
        self.on_tail_browse_clicked,
        self.on_tail_mode_clicked,
        self.tail_random_check
    )
    self.tail_browse_btn.setEnabled(False)
    self.tail_mode_btn.setEnabled(False)
    
    tail_layout.addWidget(tail_row)
    main_layout.addWidget(tail_card)

    # ==================== 3. 边框设置 ====================
    self.border_check = ToggleSwitch()
    self.border_check.toggled.connect(self.on_border_check_changed)
    
    border_card = ModernCard()
    border_layout = border_card.layout
    border_layout.addWidget(create_tab_section_header(t("batch.add_intro_outro_tab.border.title", "边框叠加"), self.border_check))
    
    self.border_file = QLineEdit()
    self.border_file.setReadOnly(True)
    self.border_file.setPlaceholderText(
        t("batch.add_intro_outro_tab.border.placeholder", "未选择边框文件（png, jpg, gif）")
    )
    self.border_file.setEnabled(False)
    ModernInput.apply_style(self.border_file)
    
    border_row, self.border_browse_btn, self.border_mode_btn = create_file_row(
        self.border_file, 
        self.on_border_browse_clicked,
        self.on_border_mode_clicked
    )
    self.border_browse_btn.setEnabled(False)
    self.border_mode_btn.setEnabled(False)
    border_layout.addWidget(border_row)
    
    # 操作行
    action_row = QHBoxLayout()
    action_row.setSpacing(15)
    
    # 样式配置链接
    self.border_style_label = QLabel(t("batch.add_intro_outro_tab.border.style_config", "⚙️ 透明&边距配置"))
    self.border_style_label.setStyleSheet(f"color: {Theme.TextDisabled}; font-size: 13px; font-weight: normal;")
    self.border_style_label.setCursor(Qt.CursorShape.PointingHandCursor)
    # 保持兼容性：双重绑定防止有些环境只触发 mousePress
    self.border_style_label.mousePressEvent = (
        lambda event: self.on_border_style_clicked() if self.border_style_label.isEnabled() else None
    )
    self.border_style_label.setEnabled(False)
    action_row.addWidget(self.border_style_label)
    
    action_row.addStretch()
    
    # 预览按钮
    self.border_preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
    self.border_preview_btn.clicked.connect(self.on_border_preview_clicked)
    self.border_preview_btn.setEnabled(False)
    action_row.addWidget(self.border_preview_btn)
    
    border_layout.addLayout(action_row)
    main_layout.addWidget(border_card)

    main_layout.addStretch()

    # 初始化配置（保持原有逻辑）
    self.border_style_config = {
        "opacity_min": 1.0,
        "opacity_max": 1.0,
        "margin_x": 0,
        "margin_y": 0,
        "border_random": False,
        "remove_bg": False,
        "bg_method": "video_color",
        "bg_x": 10,
        "bg_y": 10,
        "bg_time": 0.0,
        "bg_color": "#00FF00",
        "bg_similarity": 0.10,
        "bg_blend": 0.30,
    }

    # 2. 包装到滚动区域
    scroll_area = create_modern_scroll_area(content_widget)
    
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    
    return container
