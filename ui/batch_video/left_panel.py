import os
from datetime import datetime
from PyQt6.QtCore import Qt, QVariantAnimation, QRect
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QSizePolicy,
    QStyle,
    QStyleOptionButton
)
from ui.components import ModernCard, ModernButton, load_svg_icon
from ui.theme import Theme
from ui.i18n import t


class CheckableHeaderView(QHeaderView):
    """支持复选框的表头视图"""
    
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._check_state = Qt.CheckState.Unchecked
        self._checkbox_column = 0
        self._callback = None
        self.setSectionsClickable(True)
    
    def set_state_changed_callback(self, callback):
        """设置状态改变回调"""
        self._callback = callback
    
    def set_check_state(self, state):
        """设置复选框状态"""
        if self._check_state != state:
            self._check_state = state
            self.viewport().update()
    
    def get_check_state(self):
        """获取复选框状态"""
        return self._check_state
    
    def paintSection(self, painter, rect, logicalIndex):
        """绘制表头区域"""
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()
        
        if logicalIndex == self._checkbox_column:
            option = QStyleOptionButton()
            checkbox_width = 16
            checkbox_height = 16
            option.rect = QRect(
                rect.x() + (rect.width() - checkbox_width) // 2,  # 在列宽内居中
                rect.y() + (rect.height() - checkbox_height) // 2,
                checkbox_width,
                checkbox_height
            )
            
            if self._check_state == Qt.CheckState.Checked:
                option.state |= QStyle.StateFlag.State_On
            elif self._check_state == Qt.CheckState.PartiallyChecked:
                option.state |= QStyle.StateFlag.State_NoChange
            else:
                option.state |= QStyle.StateFlag.State_Off
            
            option.state |= QStyle.StateFlag.State_Enabled
            self.style().drawControl(QStyle.ControlElement.CE_CheckBox, option, painter)
    
    def mousePressEvent(self, event):
        """处理鼠标点击"""
        logical_index = self.logicalIndexAt(event.pos())
        if logical_index == self._checkbox_column:
            new_state = Qt.CheckState.Unchecked if self._check_state == Qt.CheckState.Checked else Qt.CheckState.Checked
            self.set_check_state(new_state)
            if self._callback:
                self._callback(new_state)
        else:
            super().mousePressEvent(event)


class DragDropWidget(QWidget):
    def __init__(self, on_files_dropped, on_click=None, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)  # 确保样式表生效
        self.setObjectName("DragDropZone")
        self._on_files_dropped = on_files_dropped
        self._on_click_callback = on_click
        self.setAcceptDrops(True)
        self._outer_border_enabled = True
        
        # 动画相关属性
        self.icon_label = None
        self.high_res_pixmap = None
        self.animation = None
        
        # 设置鼠标样式为手型
        if on_click:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._set_idle_style()

    def set_icon_label(self, label, icon_name):
        self.icon_label = label
        
        # 预加载高清大图 (96x96) 用于高质量缩放
        # 颜色与原代码一致使用 Theme.Border
        icon = load_svg_icon(icon_name, 96, Theme.Border)
        self.high_res_pixmap = icon.pixmap(96, 96)
        
        # 初始化动画
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(200) # 200ms
        self.animation.valueChanged.connect(self.update_icon_size)
        
        # 设置初始大小
        self.update_icon_size(64)

    def update_icon_size(self, size):
        if self.icon_label and self.high_res_pixmap:
            s = int(size)
            scaled_pixmap = self.high_res_pixmap.scaled(
                s, s, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.icon_label.setPixmap(scaled_pixmap)

    def start_hover_animation(self):
        if self.animation:
            self.animation.stop()
            # 从当前值或64开始
            start = self.animation.currentValue() if isinstance(self.animation.currentValue(), (int, float)) else 64
            self.animation.setStartValue(start)
            self.animation.setEndValue(76) # 放大到 76
            self.animation.start()

    def start_idle_animation(self):
        if self.animation:
            self.animation.stop()
            # 从当前值或76开始
            start = self.animation.currentValue() if isinstance(self.animation.currentValue(), (int, float)) else 76
            self.animation.setStartValue(start)
            self.animation.setEndValue(64) # 恢复到 64
            self.animation.start()

    def set_outer_border_enabled(self, enabled: bool):
        self._outer_border_enabled = enabled
        self._set_idle_style()

    def _set_idle_style(self):
        border_style = "none"
        if self._outer_border_enabled:
            # 鼠标未悬停时显示非常浅的蓝色虚线
            border_style = f"2px dashed rgba(59, 130, 246, 0.3)"  # Alpha 0.3
        
        # 使用 rgba 确保背景色兼容性，避免 #RRGGBBAA 可能导致的问题
        # 添加 margin 来缩减视觉上的高度 (上下30px, 左右0)
        self.setStyleSheet(f"""
            QWidget#DragDropZone {{
                background-color: transparent; 
                border: {border_style};
                border-radius: 8px;
                margin: 30px 0;
            }}
        """)

    def _set_hover_style(self):
        border_style = "none"
        if self._outer_border_enabled:
            # 鼠标悬停时显示正常的蓝色虚线
            border_style = f"2px dashed {Theme.Primary}"
        self.setStyleSheet(f"""
            QWidget#DragDropZone {{
                background-color: rgba(59, 130, 246, 0.03);
                border: {border_style};
                border-radius: 8px;
                margin: 30px 0;
            }}
        """)

    def enterEvent(self, event):
        self._set_hover_style()
        self.start_hover_animation()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_idle_style()
        self.start_idle_animation()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._on_click_callback:
            self._on_click_callback()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_hover_style()
            self.start_hover_animation()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_idle_style()
        self.start_idle_animation()
        event.accept()

    def dropEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        self._set_idle_style()
        self.start_idle_animation()
        if paths:
            self._on_files_dropped(paths)
        event.acceptProposedAction()

def create_left_panel(self) -> QWidget:
    """创建左侧视频列表面板"""
    
    # 使用 ModernCard 包裹
    panel = ModernCard()
    layout = panel.layout # 已经是 QVBoxLayout，且有 padding
    
    # 视频列表表格
    self.video_table = QTableWidget()
    self.video_table.setColumnCount(5)
    # 将 "勾选" 改为空，"No." 改为 "#"，以节省空间
    self.video_table.setHorizontalHeaderLabels(
        [
            "",
            "#",
            t("batch.left_panel.table.header.video_file", "视频文件"),
            t("batch.left_panel.table.header.info", "信息"),
            t("batch.left_panel.table.header.status", "状态"),
        ]
    )
    
    # 隐藏垂直表头
    self.video_table.verticalHeader().setVisible(False)
    # 允许窗口缩小时左侧先适度收缩，避免右侧参数区被挤压错位
    self.video_table.setMinimumWidth(420)
    
    # 设置列宽模式
    self.header_view = CheckableHeaderView(Qt.Orientation.Horizontal, self.video_table)
    self.video_table.setHorizontalHeader(self.header_view)
    
    self.header_view.setMinimumSectionSize(20)  # 允许列宽更窄
    self.header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
    self.header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
    self.header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
    self.header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    self.header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
    self.video_table.setColumnWidth(4, 100)  # 状态列需要放置圆点+文字
    
    # 设置复选框回调
    self.header_view.set_state_changed_callback(self.on_header_checkbox_changed)

    # 设置表头对齐方式
    for i, align in enumerate([
        Qt.AlignmentFlag.AlignCenter,  # 勾选
        Qt.AlignmentFlag.AlignCenter,  # No.
        Qt.AlignmentFlag.AlignLeft,    # 视频文件
        Qt.AlignmentFlag.AlignLeft,    # 信息
        Qt.AlignmentFlag.AlignCenter   # 状态
    ]):
        item = self.video_table.horizontalHeaderItem(i)
        if item:
            item.setTextAlignment(align)
    
    # 交互设置
    self.video_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    self.video_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    self.video_table.itemSelectionChanged.connect(self.on_selection_changed)
    self.video_table.cellDoubleClicked.connect(self.on_video_double_clicked)
    self.video_table.itemChanged.connect(self.on_table_item_changed)
    
    # 右键菜单
    self.video_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    self.video_table.customContextMenuRequested.connect(self.show_table_context_menu)
    
    # 样式表：扁平化、灰色水印背景、Slate配色
    watermark_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'kunqiong_gray.png')).replace('\\', '/')
    self.video_table.setStyleSheet(f"""
        QTableWidget {{
            border: 1px solid {Theme.Border};
            background-color: {Theme.Surface};
            background-image: url({watermark_path});
            background-repeat: no-repeat;
            background-position: center center;
            background-attachment: fixed;
            gridline-color: {Theme.Divider};
            border-radius: 8px;
            selection-background-color: {Theme.PrimaryLight};
            selection-color: {Theme.Primary};
        }}
        QTableWidget::item {{
            padding: 8px; /* 增加行高 */
            border-bottom: 1px solid {Theme.Divider};
            background-color: transparent;
        }}
        QHeaderView::section {{
            background-color: {Theme.Background};
            color: {Theme.TextSecondary};
            padding: 4px 2px;
            border: none;
            border-bottom: 1px solid {Theme.Border};
            font-weight: 600;
            font-size: 13px;
        }}
    """)
    
    self.video_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    self.video_table.setMinimumHeight(400)
    
    # 顶部工具栏
    toolbar_layout = QHBoxLayout()
    toolbar_layout.setSpacing(8)

    self.load_video_btn = ModernButton(t("common.btn.import", "导入"), ModernButton.Style.Outline, icon_name="import")
    self.load_video_btn.clicked.connect(self.show_load_menu)
    toolbar_layout.addWidget(self.load_video_btn)

    self.remove_btn = ModernButton(t("common.btn.remove", "移除"), ModernButton.Style.Secondary, icon_name="remove")
    self.remove_btn.setEnabled(False)
    self.remove_btn.clicked.connect(self.remove_checked_videos)
    toolbar_layout.addWidget(self.remove_btn)

    self.clear_btn = ModernButton(t("common.btn.clear", "清空"), ModernButton.Style.Secondary, icon_name="trash")
    self.clear_btn.clicked.connect(self.clear_queue)
    self.clear_btn.setEnabled(False)
    toolbar_layout.addWidget(self.clear_btn)

    toolbar_layout.addStretch()

    self.queue_label = QLabel(t("batch.left_panel.queue.summary", "总数: {total} | 已选: {selected}").format(total=0, selected=0))
    self.queue_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    toolbar_layout.addWidget(self.queue_label)

    self.apply_params_to_all_check = QCheckBox(t("batch.left_panel.apply_params_to_all", "应用参数到全部"))
    self.apply_params_to_all_check.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    self.apply_params_to_all_check.setChecked(bool(getattr(self, "apply_params_to_all", False)))
    self.apply_params_to_all_check.toggled.connect(self.on_apply_params_to_all_changed)
    toolbar_layout.addWidget(self.apply_params_to_all_check)

    layout.addLayout(toolbar_layout)

    # 创建空状态提示
    self.create_empty_state_widget(layout)

    # 处理记录区域（折叠）
    record_header_layout = QHBoxLayout()

    self.log_toggle_btn = QPushButton(t("batch.left_panel.log.title", "处理记录"))
    self.log_toggle_btn.setCheckable(True)
    self.log_toggle_btn.setChecked(False)
    self.log_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    self.log_toggle_btn.setStyleSheet(f"""
        QPushButton {{
            color: {Theme.TextPrimary};
            border: none;
            background: transparent;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton:hover {{
            color: {Theme.Primary};
        }}
    """)
    record_header_layout.addWidget(self.log_toggle_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    self.log_summary_label = QLabel(t("batch.left_panel.log.empty", "暂无记录"))
    self.log_summary_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 13px; font-weight: normal;")
    record_header_layout.addWidget(self.log_summary_label, 0, Qt.AlignmentFlag.AlignVCenter)

    record_header_layout.addStretch()

    clear_log_btn = QPushButton(t("batch.left_panel.log.clear_all", "清理所有记录"))
    clear_log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    clear_log_btn.setStyleSheet(f"""
        QPushButton {{
            color: {Theme.TextSecondary};
            border: none;
            background: transparent;
            font-size: 13px;
            font-weight: normal;
        }}
        QPushButton:hover {{
            color: {Theme.Primary};
            text-decoration: underline;
        }}
    """)
    clear_log_btn.clicked.connect(self.clear_process_log)
    record_header_layout.addWidget(clear_log_btn, 0, Qt.AlignmentFlag.AlignVCenter)
    layout.addLayout(record_header_layout)

    self.process_log = QTextEdit()
    self.process_log.setMaximumHeight(80)
    self.process_log.setReadOnly(True)
    startup_time = datetime.now().strftime("%H:%M:%S")
    self.process_log.append(f"{startup_time} -> {t('batch.left_panel.log.startup', '软件启动')}")
    self.process_log.setStyleSheet(f"""
        QTextEdit {{
            background-color: {Theme.Background};
            border: 1px solid {Theme.Border};
            border-radius: 6px;
            color: {Theme.TextSecondary};
            font-size: 12px;
            padding: 5px;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #CBD5E1;
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #94A3B8;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: #CBD5E1;
            min-width: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: #94A3B8;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    """)
    self.process_log.setVisible(False)
    layout.addWidget(self.process_log)

    def update_log_summary():
        if self.process_log.isVisible():
            self.log_summary_label.setVisible(False)
            return
        text = self.process_log.toPlainText().strip().splitlines()
        summary = text[-1] if text else t("batch.left_panel.log.empty", "暂无记录")
        self.log_summary_label.setText(summary)
        self.log_summary_label.setVisible(True)

    def toggle_log(checked: bool):
        self.process_log.setVisible(checked)
        update_log_summary()

    self.log_toggle_btn.toggled.connect(toggle_log)
    self.process_log.textChanged.connect(update_log_summary)
    update_log_summary()
    
    return panel


def create_empty_state_widget(self, parent_layout):
    """创建空状态提示界面"""
    def handle_dropped_paths(paths):
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg']
        video_files = []
        total_added = 0
        for path in paths:
            if os.path.isdir(path):
                folder_files = []
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in video_extensions):
                            folder_files.append(os.path.join(root, file))
                if folder_files:
                    self.add_videos(folder_files, root_dir=path)
                    total_added += len(folder_files)
            else:
                if any(path.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(path)
        if video_files:
            self.add_videos(video_files)
            total_added += len(video_files)
            if hasattr(self, "process_log"):
                self.process_log.append(
                    t("batch.left_panel.log.drop_imported", "拖拽导入了 {count} 个视频").format(count=total_added)
                )

    self.empty_state_widget = DragDropWidget(handle_dropped_paths, on_click=self.import_video_files)
    self.empty_state_widget.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )

    outer_layout = QVBoxLayout(self.empty_state_widget)
    outer_layout.setContentsMargins(10, 10, 10, 10)
    outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    inner_widget = QWidget()
    inner_widget.setObjectName("emptyStateInner")
    inner_widget.setSizePolicy(
        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
    )
    inner_widget.setStyleSheet("""
        QWidget#emptyStateInner {
            background-color: transparent;
            border: none;
        }
    """)
    outer_layout.addWidget(inner_widget)

    empty_layout = QVBoxLayout(inner_widget)
    empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    empty_layout.setSpacing(15)

    icon_label = QLabel()
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    # 初始图标由 set_icon_label 设置
    empty_layout.addWidget(icon_label)
    
    # 启用图标动效
    self.empty_state_widget.set_icon_label(icon_label, "import")

    tip_label = QLabel(t("batch.left_panel.empty.tip", "还没有视频，请导入视频文件或拖拽到这里"))
    tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    tip_label.setStyleSheet(f"color: {Theme.TextSecondary}; font-size: 14px; font-weight: 500;")
    empty_layout.addWidget(tip_label)

    button_layout = QHBoxLayout()
    button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    button_layout.setSpacing(10)

    import_file_btn = ModernButton(t("batch.left_panel.empty.import_file", "导入文件"), ModernButton.Style.Primary, icon_name="import")
    import_file_btn.clicked.connect(self.import_video_files)
    button_layout.addWidget(import_file_btn)

    import_folder_btn = ModernButton(
        t("batch.left_panel.empty.import_folder", "导入文件夹"),
        ModernButton.Style.Outline,
        icon_name="folder",
    )
    import_folder_btn.clicked.connect(self.import_video_folder)
    button_layout.addWidget(import_folder_btn)

    empty_layout.addLayout(button_layout)

    # 替换原有的添加逻辑：这里我们不直接 addWidget，而是依赖调用方
    parent_layout.addWidget(self.empty_state_widget)
    parent_layout.addWidget(self.video_table)

    self.update_empty_state()
