from PyQt6.QtWidgets import QVBoxLayout, QWidget
from ui.batch_video.bottom_panel import create_bottom_panel
from ui.components import SegmentedControl
from ui.i18n import t

def create_right_panel(self) -> QWidget:
    """创建右侧功能设置面板"""
    panel = QWidget()
    panel.setMinimumWidth(560)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 20, 0)
    layout.setSpacing(15)

    # 功能标签栏 - 替换为 SegmentedControl
    tab_widget = self.create_function_tabs()
    layout.addWidget(tab_widget) # 移除 stretch，由内容决定高度

    # 右侧底部：输出相关控件
    bottom_panel = create_bottom_panel(self)
    layout.addWidget(bottom_panel)

    return panel


def create_function_tabs(self) -> QWidget:
    """创建功能标签栏"""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    tabs = [
        t("batch.tabs.image_adjust", "画面调整"),
        t("batch.tabs.remove_watermark", "去水印"),
        t("batch.tabs.add_watermark", "加水印"),
        t("batch.tabs.crop", "裁剪"),
        t("batch.tabs.pip", "画中画"),
        t("batch.tabs.trim", "去头尾"),
        t("batch.tabs.add_intro_outro", "加头尾"),
        t("batch.tabs.speed", "变速"),
        t("batch.tabs.text", "文本"),
        t("batch.tabs.audio", "背景音"),
    ]

    # 使用自定义的分段控制器
    self.tab_control = SegmentedControl(tabs)
    self.tab_control.valueChanged.connect(self.switch_tab)
    layout.addWidget(self.tab_control)

    # 标签内容容器（透明背景，用于放置 ModernCard）
    self.tab_content = QWidget()
    self.tab_content.setStyleSheet("background: transparent;")
    content_layout = QVBoxLayout(self.tab_content)
    content_layout.setContentsMargins(0, 0, 0, 0)

    # 创建所有标签页内容
    self.tab_pages = []
    # 新增：画面调整 Tab
    self.tab_pages.append(self.create_image_adjust_tab())
    
    # 原有 Tabs
    self.tab_pages.append(self.create_remove_watermark_tab())
    self.tab_pages.append(self.create_add_watermark_tab())
    self.tab_pages.append(self.create_crop_tab())
    self.tab_pages.append(self.create_pip_tab())
    self.tab_pages.append(self.create_trim_tab())
    self.tab_pages.append(self.create_add_intro_outro_tab())
    self.tab_pages.append(self.create_speed_tab())
    self.tab_pages.append(self.create_text_tab())
    self.tab_pages.append(self.create_audio_tab())

    for page in self.tab_pages:
        page.setVisible(False)
        content_layout.addWidget(page)

    # 默认选中第一个标签 (画面调整)
    self.tab_pages[0].setVisible(True)
    
    layout.addWidget(self.tab_content)
    
    return container
