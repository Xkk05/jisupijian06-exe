import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)
from ui.theme import Theme
from ui.components import ModernCard, ModernButton, ModernInput, ModernProgressBar, ProgressStatus
from ui.i18n import t

def create_bottom_panel(self) -> QWidget:
    """创建底部控制面板"""
    # 底部面板也使用 ModernCard 包裹，与其他部分统一
    panel = ModernCard()
    layout = panel.layout # 自动包含 padding

    # 进度条（细条风格）
    self.progress_bar = ModernProgressBar()
    self.progress_bar.setFormat(t("batch.bottom_panel.progress.not_started", "%p% - 未开始处理"))
    self.progress_bar.setValue(0)
    layout.addWidget(self.progress_bar)

    # 主内容区域
    main_layout = QHBoxLayout()
    main_layout.setSpacing(20)

    left_col_layout = QVBoxLayout()
    left_col_layout.setSpacing(10)

    # 输出位置
    output_layout = QHBoxLayout()
    output_layout.setSpacing(10)

    output_label = QLabel(t("batch.bottom_panel.output.label", "输出位置:"))
    output_label.setStyleSheet(f"font-weight: normal; font-size: 13px; color: {Theme.TextPrimary};")
    output_layout.addWidget(output_label)

    # 默认输出位置（为空，强制用户选择）
    self.output_path = QLineEdit("")
    self.output_path.setPlaceholderText(t("batch.bottom_panel.output.placeholder", "留空则输出到原目录"))
    ModernInput.apply_style(self.output_path)
    output_layout.addWidget(self.output_path, 1)

    self.browse_btn = ModernButton(t("common.btn.browse", "浏览..."), ModernButton.Style.Secondary, icon_name="folder")
    self.browse_btn.clicked.connect(self.browse_output_dir)
    output_layout.addWidget(self.browse_btn)

    self.folder_btn = ModernButton("", ModernButton.Style.Secondary, icon_name="folder")
    self.folder_btn.setToolTip(t("batch.bottom_panel.output.open_folder", "打开输出文件夹"))
    self.folder_btn.setMaximumWidth(40)
    self.folder_btn.clicked.connect(self.open_output_folder)
    output_layout.addWidget(self.folder_btn)

    left_col_layout.addLayout(output_layout)

    # 输出选项
    output_options_layout = QHBoxLayout()
    output_options_layout.setSpacing(20)

    self.unified_output_check = QCheckBox(t("batch.bottom_panel.option.unified_output", "统一输出位置"))
    self.unified_output_check.setChecked(True)
    self.unified_output_check.setToolTip(
        t(
            "batch.bottom_panel.option.unified_output.tip",
            "勾选后所有视频使用同一个输出位置，取消勾选可为每个视频单独设置",
        )
    )
    self.unified_output_check.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    output_options_layout.addWidget(self.unified_output_check)

    self.keep_structure = QCheckBox(t("batch.bottom_panel.option.keep_structure", "在新路径中按原子目录路径输出"))
    self.keep_structure.setChecked(True)
    self.keep_structure.setStyleSheet(f"color: {Theme.TextPrimary}; font-size: 13px; font-weight: normal;")
    self.keep_structure.toggled.connect(self.on_keep_structure_changed)
    output_options_layout.addWidget(self.keep_structure)

    output_options_layout.addStretch()

    self.setting_btn = ModernButton(t("options.title", "选项"), ModernButton.Style.Outline, icon_name="settings")
    self.setting_btn.clicked.connect(self.show_options_dialog)
    output_options_layout.addWidget(self.setting_btn)

    left_col_layout.addLayout(output_options_layout)
    main_layout.addLayout(left_col_layout, 1)

    # 右侧操作区域（按钮+状态提示）
    right_layout = QVBoxLayout()
    right_layout.setSpacing(12)  # 增加间距
    right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    # 开始处理按钮
    self.start_btn = ModernButton(t("batch.main_window.auto.029", "开始处理"), ModernButton.Style.Primary, icon_name="rocket")
    self.start_btn.setMinimumHeight(48)
    self.start_btn.setFixedWidth(180)
    # 添加操作动效：按下时文字下沉
    self.start_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {Theme.Primary};
            color: white;
            font-size: 15px;
            font-weight: bold;
            border-radius: 8px;
            border: none;
            padding: 0 22px;
        }}
        QPushButton:hover {{
            background-color: {Theme.PrimaryHover};
        }}
        QPushButton:pressed {{
            background-color: {Theme.PrimaryPressed};
            padding-top: 3px;
        }}
    """)
    self.start_btn.clicked.connect(self.start_processing)
    right_layout.addWidget(self.start_btn)

    # 状态标签（用于实时校验与处理状态提示）
    self.status_label = QLabel(t("batch.bottom_panel.status.ready", "参数校验通过，可开始处理"), panel)
    self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.status_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 12px;")
    self.status_label.setVisible(False)
    right_layout.addWidget(self.status_label)

    # 底部增加一点留白，使整体视觉重心上移
    right_layout.addSpacing(8)

    main_layout.addLayout(right_layout, 0)

    layout.addLayout(main_layout)

    return panel
