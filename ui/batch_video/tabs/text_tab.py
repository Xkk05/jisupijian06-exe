from PyQt6.QtWidgets import (
    QHBoxLayout, 
    QVBoxLayout, 
    QWidget, 
    QLabel, 
    QLineEdit
)
from ui.components import (
    ModernCard,
    ToggleSwitch,
    ModernInput,
    ModernButton,
    create_param_row,
    create_modern_scroll_area
)
from ui.i18n import t


def create_text_tab(self) -> QWidget:
    """创建文本标签页"""
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

    # 辅助函数：创建单个文本轨道
    def create_tab_section_header(text, switch_widget=None):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(text)
        label.setStyleSheet("font-size: 13px; font-weight: bold;")
        layout.addWidget(label)

        layout.addStretch()

        if switch_widget:
            layout.addWidget(switch_widget)

        return container

    def create_track_card(track_num):
        card = ModernCard()
        card_layout = card.layout
        
        # 1. 标题 + 开关
        check = ToggleSwitch()
        # 兼容旧逻辑：setattr 并连接信号
        setattr(self, f'text{track_num}_check', check)
        check.toggled.connect(lambda checked, num=track_num: self._on_text_check_changed(num, checked))
        
        card_layout.addWidget(
            create_tab_section_header(
                t("batch.text_tab.track.title", "文本轨道 {num}").format(num=track_num),
                check,
            )
        )
        
        # 2. 内容区域
        content_layout = QHBoxLayout()
        content_layout.setSpacing(10)
        
        # 文本预览/输入
        preview = QLineEdit()
        preview.setPlaceholderText(t("batch.text_tab.placeholder.input", "请输入文本内容..."))
        preview.setEnabled(False)
        ModernInput.apply_style(preview)
        preview.textChanged.connect(lambda text, num=track_num: self._on_text_inline_changed(num, text))
        setattr(self, f'text{track_num}_preview', preview)
        content_layout.addWidget(preview, 1)
        
        card_layout.addLayout(content_layout)
        
        # 3. 操作按钮行
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        # 设置按钮
        settings_btn = ModernButton(t("batch.text_tab.btn.settings", "参数设置"), style=ModernButton.Style.Outline, icon_name="settings")
        settings_btn.setEnabled(False)
        settings_btn.clicked.connect(lambda checked, num=track_num: self._on_text_settings(num))
        setattr(self, f'text{track_num}_settings_btn', settings_btn)
        btn_layout.addWidget(settings_btn)
        
        btn_layout.addStretch()
        
        # 预览按钮
        preview_btn = ModernButton(t("common.btn.preview", "预览效果"), style=ModernButton.Style.Outline, icon_name="eye")
        preview_btn.setEnabled(False)
        preview_btn.clicked.connect(lambda checked, num=track_num: self._on_text_preview(num))
        setattr(self, f'text{track_num}_preview_btn', preview_btn)
        btn_layout.addWidget(preview_btn)
        
        card_layout.addLayout(btn_layout)
        
        return card

    # 创建三个文本轨道
    for i in range(1, 4):
        main_layout.addWidget(create_track_card(i))

    main_layout.addStretch()

    # 2. 包装到滚动区域
    scroll_area = create_modern_scroll_area(content_widget)
    
    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(0, 0, 0, 0)
    container_layout.addWidget(scroll_area)
    
    return container
