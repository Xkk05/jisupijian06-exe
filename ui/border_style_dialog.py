"""
边框样式设置对话框
集成现代化UI组件
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, 
    QDoubleSpinBox, QLabel, QSpinBox, QRadioButton, 
    QButtonGroup, QComboBox, QMessageBox, QWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from ui.theme import Theme
from ui.components import ModernButton, ModernCard, create_param_row, ModernInput
from ui.i18n import t

class BorderStyleDialog(QDialog):
    """边框样式设置对话框"""
    
    def __init__(self, parent=None, initial_config=None, allow_random: bool = False):
        super().__init__(parent)
        self.setWindowTitle(t("border_style_dialog.title", "边框样式"))
        self.setModal(True)
        self.setMinimumWidth(550)
        self.setMinimumHeight(600)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        self.allow_random = allow_random
        
        # 初始化配置（兼容旧字段）
        base_config = initial_config or {}
        legacy_opacity = base_config.get('opacity', 1.0)
        self.config = {
            'opacity_min': base_config.get('opacity_min', legacy_opacity),
            'opacity_max': base_config.get('opacity_max', legacy_opacity),
            'margin_x': base_config.get('margin_x', 0),
            'margin_y': base_config.get('margin_y', 0),
            'border_random': base_config.get('border_random', False),
            'remove_bg': base_config.get('remove_bg', False),
            'bg_method': base_config.get('bg_method', 'video_color'),
            'bg_x': base_config.get('bg_x', 10),
            'bg_y': base_config.get('bg_y', 10),
            'bg_time': base_config.get('bg_time', 0.0),
            'bg_color': base_config.get('bg_color', '#00FF00'),
            'bg_similarity': base_config.get('bg_similarity', 0.10),
            'bg_blend': base_config.get('bg_blend', 0.30)
        }
        
        self.init_ui()
    
    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: #F8FAFC;
                border: none;
            }
            QScrollArea QWidget {
                background: #F8FAFC;
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
        
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #F8FAFC;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(0, 0, 10, 0)  # 右侧留出滚动条空间
        
        # ==== 透明设置卡片 ====
        opacity_card = ModernCard(t("border_style_dialog.opacity.title", "透明设置"))
        
        opacity_row = QHBoxLayout()
        self.opacity_check = QCheckBox(
            t("border_style_dialog.opacity.enable", "启用透明度")
        )
        self.opacity_check.setChecked(self.config.get('opacity_min', 1.0) < 1.0 or self.config.get('opacity_max', 1.0) < 1.0)
        self.opacity_check.toggled.connect(self.on_opacity_check_changed)
        opacity_row.addWidget(self.opacity_check)
        opacity_row.addStretch()
        opacity_card.addLayout(opacity_row)
        
        range_layout = QHBoxLayout()
        range_layout.setSpacing(10)
        
        self.opacity_min_spin = QDoubleSpinBox()
        self.opacity_min_spin.setRange(0.01, 1.0)
        self.opacity_min_spin.setSingleStep(0.01)
        self.opacity_min_spin.setDecimals(2)
        self.opacity_min_spin.setValue(self.config.get('opacity_min', 1.0))
        ModernInput.apply_style(self.opacity_min_spin)
        
        self.opacity_max_spin = QDoubleSpinBox()
        self.opacity_max_spin.setRange(0.01, 1.0)
        self.opacity_max_spin.setSingleStep(0.01)
        self.opacity_max_spin.setDecimals(2)
        self.opacity_max_spin.setValue(self.config.get('opacity_max', 1.0))
        ModernInput.apply_style(self.opacity_max_spin)
        
        range_layout.addWidget(
            QLabel(t("border_style_dialog.opacity.min", "最小透明度:"))
        )
        range_layout.addWidget(self.opacity_min_spin)
        range_layout.addWidget(QLabel("-"))
        range_layout.addWidget(
            QLabel(t("border_style_dialog.opacity.max", "最大透明度:"))
        )
        range_layout.addWidget(self.opacity_max_spin)
        range_layout.addStretch()
        
        opacity_card.addLayout(range_layout)
        opacity_card.addWidget(
            QLabel(t("border_style_dialog.opacity.tip", "(范围: 0.01~1.0，值越小越透明)"))
        )
        
        content_layout.addWidget(opacity_card)
        
        # ==== 边距设置卡片 ====
        margin_card = ModernCard(t("border_style_dialog.margin.title", "边距设置"))
        
        margin_check_row = QHBoxLayout()
        self.margin_check = QCheckBox(t("border_style_dialog.margin.enable", "启用边距"))
        self.margin_check.setChecked(
            self.config.get('margin_x', 0) != 0 or self.config.get('margin_y', 0) != 0
        )
        self.margin_check.toggled.connect(self.on_margin_check_changed)
        margin_check_row.addWidget(self.margin_check)
        
        self.border_random_check = QCheckBox(
            t("border_style_dialog.margin.random", "随机应用")
        )
        self.border_random_check.setChecked(self.config.get('border_random', False) if self.allow_random else False)
        self.border_random_check.setEnabled(self.allow_random)
        margin_check_row.addWidget(self.border_random_check)
        margin_check_row.addStretch()
        margin_card.addLayout(margin_check_row)
        
        margin_params_layout = QHBoxLayout()
        margin_params_layout.setSpacing(15)
        
        # X 边距
        self.margin_x_spin = QSpinBox()
        self.margin_x_spin.setRange(0, 9999)
        self.margin_x_spin.setValue(self.config.get('margin_x', 0))
        self.margin_x_spin.setSuffix(" px")
        ModernInput.apply_style(self.margin_x_spin)
        
        # Y 边距
        self.margin_y_spin = QSpinBox()
        self.margin_y_spin.setRange(0, 9999)
        self.margin_y_spin.setValue(self.config.get('margin_y', 0))
        self.margin_y_spin.setSuffix(" px")
        ModernInput.apply_style(self.margin_y_spin)
        
        margin_params_layout.addWidget(
            QLabel(t("border_style_dialog.margin.horizontal_x", "水平边距 (X):"))
        )
        margin_params_layout.addWidget(self.margin_x_spin)
        margin_params_layout.addWidget(
            QLabel(t("border_style_dialog.margin.vertical_y", "垂直边距 (Y):"))
        )
        margin_params_layout.addWidget(self.margin_y_spin)
        margin_params_layout.addStretch()
        
        margin_card.addLayout(margin_params_layout)
        content_layout.addWidget(margin_card)
        
        # ==== 背景色消除卡片 ====
        bg_card = ModernCard(t("border_style_dialog.bg_remove.title", "背景色消除"))
        
        bg_check_row = QHBoxLayout()
        self.bg_remove_check = QCheckBox(
            t(
                "border_style_dialog.bg_remove.enable",
                "启用背景色消除 (模拟绿幕/蓝幕抠像)",
            )
        )
        self.bg_remove_check.setChecked(self.config.get('remove_bg', False))
        self.bg_remove_check.toggled.connect(self.on_bg_remove_check_changed)
        bg_check_row.addWidget(self.bg_remove_check)
        bg_check_row.addStretch()
        bg_card.addLayout(bg_check_row)
        
        # 方法选择
        method_group_box = QWidget()
        method_layout = QVBoxLayout(method_group_box)
        method_layout.setContentsMargins(0, 10, 0, 0)
        
        self.bg_method_group = QButtonGroup()
        
        # 方法1：拾取
        method1_layout = QHBoxLayout()
        self.bg_method1_radio = QRadioButton(
            t("border_style_dialog.bg_remove.auto_pick", "自动拾取背景色")
        )
        self.bg_method1_radio.setChecked(self.config.get('bg_method') == 'video_color')
        self.bg_method_group.addButton(self.bg_method1_radio, 1)
        self.bg_method1_radio.toggled.connect(self._sync_controls_enabled)
        method1_layout.addWidget(self.bg_method1_radio)
        method_layout.addLayout(method1_layout)
        
        # 拾取参数
        pick_params_layout = QHBoxLayout()
        pick_params_layout.setContentsMargins(25, 0, 0, 0)
        pick_params_layout.setSpacing(10)
        
        self.bg_x_spin = QSpinBox()
        self.bg_x_spin.setRange(0, 9999)
        self.bg_x_spin.setValue(self.config.get('bg_x', 10))
        self.bg_x_spin.setPrefix("X: ")
        ModernInput.apply_style(self.bg_x_spin)
        
        self.bg_y_spin = QSpinBox()
        self.bg_y_spin.setRange(0, 9999)
        self.bg_y_spin.setValue(self.config.get('bg_y', 10))
        self.bg_y_spin.setPrefix("Y: ")
        ModernInput.apply_style(self.bg_y_spin)
        
        self.bg_time_spin = QDoubleSpinBox()
        self.bg_time_spin.setRange(0.0, 99999.0)
        self.bg_time_spin.setSingleStep(0.1)
        self.bg_time_spin.setDecimals(1)
        self.bg_time_spin.setValue(self.config.get('bg_time', 0.0))
        self.bg_time_spin.setPrefix(t("border_style_dialog.bg_remove.time_prefix", "时间点: "))
        self.bg_time_spin.setSuffix(t("common.suffix.second", " 秒"))
        ModernInput.apply_style(self.bg_time_spin)
        
        pick_params_layout.addWidget(self.bg_x_spin)
        pick_params_layout.addWidget(self.bg_y_spin)
        pick_params_layout.addWidget(self.bg_time_spin)
        pick_params_layout.addStretch()
        method_layout.addLayout(pick_params_layout)
        
        # 方法2：指定
        method2_layout = QHBoxLayout()
        self.bg_method2_radio = QRadioButton(
            t("border_style_dialog.bg_remove.fixed_color", "指定固定背景色")
        )
        self.bg_method2_radio.setChecked(self.config.get('bg_method') == 'specified')
        self.bg_method_group.addButton(self.bg_method2_radio, 2)
        self.bg_method2_radio.toggled.connect(self._sync_controls_enabled)
        method2_layout.addWidget(self.bg_method2_radio)
        
        self.bg_color_combo = QComboBox()
        self.bg_color_combo.addItems([
            t("border_style_dialog.bg_remove.color.green", "绿色 (#00FF00)"),
            t("border_style_dialog.bg_remove.color.blue", "蓝色 (#0000FF)"),
            t("border_style_dialog.bg_remove.color.red", "红色 (#FF0000)"),
            t("border_style_dialog.bg_remove.color.white", "白色 (#FFFFFF)"),
            t("border_style_dialog.bg_remove.color.black", "黑色 (#000000)")
        ])
        current_color = self.config.get('bg_color', '#00FF00').upper()
        for idx in range(self.bg_color_combo.count()):
            item_text = self.bg_color_combo.itemText(idx)
            if current_color in item_text:
                self.bg_color_combo.setCurrentIndex(idx)
                break
        ModernInput.apply_style(self.bg_color_combo)
        method2_layout.addWidget(self.bg_color_combo)
        method2_layout.addStretch()
        method_layout.addLayout(method2_layout)
        
        # 相似度与混合
        chroma_layout = QHBoxLayout()
        chroma_layout.setContentsMargins(0, 10, 0, 0)
        
        self.bg_similarity_spin = QDoubleSpinBox()
        self.bg_similarity_spin.setRange(0.0, 1.0)
        self.bg_similarity_spin.setSingleStep(0.01)
        self.bg_similarity_spin.setDecimals(2)
        self.bg_similarity_spin.setValue(self.config.get('bg_similarity', 0.10))
        ModernInput.apply_style(self.bg_similarity_spin)
        
        self.bg_blend_spin = QDoubleSpinBox()
        self.bg_blend_spin.setRange(0.0, 1.0)
        self.bg_blend_spin.setSingleStep(0.01)
        self.bg_blend_spin.setDecimals(2)
        self.bg_blend_spin.setValue(self.config.get('bg_blend', 0.30))
        ModernInput.apply_style(self.bg_blend_spin)
        
        chroma_layout.addWidget(
            create_param_row(
                t("border_style_dialog.bg_remove.similarity", "颜色相似度:"),
                self.bg_similarity_spin,
            )
        )
        chroma_layout.addWidget(
            create_param_row(
                t("border_style_dialog.bg_remove.blend", "混合平滑度:"),
                self.bg_blend_spin,
            )
        )
        
        method_layout.addLayout(chroma_layout)
        bg_card.addWidget(method_group_box)
        content_layout.addWidget(bg_card)
        
        content_layout.addStretch()
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # ==== 底部按钮 ====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        reset_btn = ModernButton(
            t("border_style_dialog.btn.reset_default", "重置默认"),
            ModernButton.Style.Secondary,
        )
        reset_btn.clicked.connect(self.on_reset_clicked)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        ok_btn = ModernButton(t("common.btn.ok", "确定"), ModernButton.Style.Primary)
        ok_btn.clicked.connect(self.on_ok_clicked)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = ModernButton(
            t("common.btn.cancel", "取消"), ModernButton.Style.Secondary
        )
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        self._sync_controls_enabled()
    
    def on_opacity_check_changed(self, checked):
        self.opacity_min_spin.setEnabled(checked)
        self.opacity_max_spin.setEnabled(checked)
    
    def on_margin_check_changed(self, checked):
        self.margin_x_spin.setEnabled(checked)
        self.margin_y_spin.setEnabled(checked)
    
    def on_bg_remove_check_changed(self, checked):
        self._sync_controls_enabled()
    
    def _sync_controls_enabled(self):
        """同步控件可用状态"""
        opacity_enabled = self.opacity_check.isChecked()
        self.opacity_min_spin.setEnabled(opacity_enabled)
        self.opacity_max_spin.setEnabled(opacity_enabled)
        
        margin_enabled = self.margin_check.isChecked()
        self.margin_x_spin.setEnabled(margin_enabled)
        self.margin_y_spin.setEnabled(margin_enabled)
        
        bg_enabled = self.bg_remove_check.isChecked()
        self.bg_method1_radio.setEnabled(bg_enabled)
        self.bg_method2_radio.setEnabled(bg_enabled)
        
        use_method1 = self.bg_method1_radio.isChecked()
        self.bg_x_spin.setEnabled(bg_enabled and use_method1)
        self.bg_y_spin.setEnabled(bg_enabled and use_method1)
        self.bg_time_spin.setEnabled(bg_enabled and use_method1)
        
        use_method2 = self.bg_method2_radio.isChecked()
        self.bg_color_combo.setEnabled(bg_enabled and use_method2)
        
        self.bg_similarity_spin.setEnabled(bg_enabled)
        self.bg_blend_spin.setEnabled(bg_enabled)
    
    def on_reset_clicked(self):
        """重置所有设置"""
        self.opacity_check.setChecked(False)
        self.opacity_min_spin.setValue(1.0)
        self.opacity_max_spin.setValue(1.0)
        self.margin_check.setChecked(False)
        self.margin_x_spin.setValue(0)
        self.margin_y_spin.setValue(0)
        self.border_random_check.setChecked(False)
        self.bg_remove_check.setChecked(False)
        self.bg_method1_radio.setChecked(True)
        self.bg_x_spin.setValue(10)
        self.bg_y_spin.setValue(10)
        self.bg_time_spin.setValue(0.0)
        self.bg_color_combo.setCurrentIndex(0)
        self.bg_similarity_spin.setValue(0.10)
        self.bg_blend_spin.setValue(0.30)
        self._sync_controls_enabled()
    
    def on_ok_clicked(self):
        """确定并保存配置"""
        # 验证透明度
        if self.opacity_check.isChecked():
            opacity_min = self.opacity_min_spin.value()
            opacity_max = self.opacity_max_spin.value()
            if opacity_min < 0.01 or opacity_max > 1.0 or opacity_min > opacity_max:
                QMessageBox.warning(
                    self,
                    t("common.warning", "警告"),
                    t(
                        "border_style_dialog.opacity.invalid_range",
                        "请输入有效的透明度范围（0.01-1.0）且最小<=最大",
                    ),
                )
                return
        
        # 保存配置
        self.config = {
            'opacity_min': self.opacity_min_spin.value() if self.opacity_check.isChecked() else 1.0,
            'opacity_max': self.opacity_max_spin.value() if self.opacity_check.isChecked() else 1.0,
            'margin_x': self.margin_x_spin.value() if self.margin_check.isChecked() else 0,
            'margin_y': self.margin_y_spin.value() if self.margin_check.isChecked() else 0,
            'border_random': self.border_random_check.isChecked(),
            'remove_bg': self.bg_remove_check.isChecked(),
            'bg_method': 'video_color' if self.bg_method1_radio.isChecked() else 'specified',
            'bg_x': self.bg_x_spin.value(),
            'bg_y': self.bg_y_spin.value(),
            'bg_time': self.bg_time_spin.value(),
            'bg_color': self.bg_color_combo.currentText().split('(')[1].rstrip(')'),
            'bg_similarity': self.bg_similarity_spin.value(),
            'bg_blend': self.bg_blend_spin.value()
        }
        
        self.accept()
    
    def get_config(self):
        """获取配置"""
        return self.config
