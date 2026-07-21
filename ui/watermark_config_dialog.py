"""
水印样式配置对话框
支持图片水印和文字水印的详细配置
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QRadioButton, QSpinBox, QDoubleSpinBox, QPushButton, QLabel,
    QComboBox, QLineEdit, QButtonGroup, QTabWidget,
    QWidget, QScrollArea, QFontDialog, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from ui.components import ModernButton, open_color_dialog
from ui.i18n import get_language_manager
from typing import Dict, Any


def _ts(text: str) -> str:
    return get_language_manager().translate_source_text(text)


class WatermarkStylePanel(QWidget):
    """水印样式设置面板（可嵌入到其他对话框中）"""
    
    # 参数变更信号
    style_changed = pyqtSignal()
    
    def __init__(self, watermark_type: str = "image", parent=None, show_size_group: bool = True):
        super().__init__(parent)
        self.watermark_type = watermark_type  # "image" or "text"
        self.show_size_group = show_size_group
        self.config = {}
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self.watermark_type == "image":
            # 图片水印：所有设置组合到一个面板
            if self.show_size_group:
                layout.addWidget(self.create_image_size_group())
            layout.addWidget(self.create_timing_group())
            layout.addWidget(self.create_effects_group())
            layout.addWidget(self.create_advanced_group())
        else:
            # 文字水印：所有设置组合到一个面板
            layout.addWidget(self.create_text_content_group())
            layout.addWidget(self.create_text_style_group())
            layout.addWidget(self.create_text_effects_group())
        
        layout.addStretch()
        
        # 延迟连接信号以确保所有控件已创建
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._connect_change_signals)

    def _get_allowed_fonts(self) -> list:
        """允许显示的字体列表（已适配）"""
        return [
            "Microsoft YaHei", "微软雅黑",
            "SimSun", "宋体",
            "SimHei", "黑体",
            "SimKai", "楷体",
            "FangSong", "仿宋",
            "DengXian", "等线",
            "Arial"
        ]
    
    def create_image_size_group(self) -> QGroupBox:
        """创建图片尺寸设置分组"""
        group = QGroupBox(_ts("尺寸设置"))
        layout = QVBoxLayout(group)
        
        # 水印大小
        size_group = QGroupBox(_ts("水印大小"))
        size_group.setCheckable(True)
        size_group.setChecked(False)
        size_layout = QVBoxLayout()
        
        # 自定义尺寸
        custom_layout = QHBoxLayout()
        self.size_custom_radio = QRadioButton(_ts("自定义"))
        self.size_custom_radio.setChecked(True)
        custom_layout.addWidget(self.size_custom_radio)
        
        custom_layout.addWidget(QLabel(_ts("宽度:")))
        self.watermark_width = QSpinBox()
        self.watermark_width.setRange(1, 9999)
        self.watermark_width.setValue(160)
        custom_layout.addWidget(self.watermark_width)
        
        custom_layout.addWidget(QLabel(_ts("高度:")))
        self.watermark_height = QSpinBox()
        self.watermark_height.setRange(1, 9999)
        self.watermark_height.setValue(90)
        custom_layout.addWidget(self.watermark_height)
        
        self.lock_aspect_ratio = QCheckBox(_ts("锁定比例"))
        custom_layout.addWidget(self.lock_aspect_ratio)
        custom_layout.addStretch()
        size_layout.addLayout(custom_layout)
        
        # 原比例缩放
        ratio_layout = QHBoxLayout()
        self.size_ratio_radio = QRadioButton(_ts("原比例"))
        ratio_layout.addWidget(self.size_ratio_radio)
        
        self.watermark_scale = QSpinBox()
        self.watermark_scale.setRange(1, 500)
        self.watermark_scale.setValue(100)
        self.watermark_scale.setSuffix("%")
        ratio_layout.addWidget(self.watermark_scale)
        ratio_layout.addStretch()
        size_layout.addLayout(ratio_layout)
        
        # 相对视频尺寸
        video_layout = QHBoxLayout()
        self.size_video_radio = QRadioButton(_ts("视频"))
        video_layout.addWidget(self.size_video_radio)
        
        self.video_size_ref = QComboBox()
        self.video_size_ref.addItems([_ts("高"), _ts("宽"), _ts("对角")])
        video_layout.addWidget(self.video_size_ref)
        
        video_layout.addWidget(QLabel(_ts("比例:")))
        self.video_size_ratio = QSpinBox()
        self.video_size_ratio.setRange(1, 100)
        self.video_size_ratio.setValue(15)
        self.video_size_ratio.setSuffix("%")
        video_layout.addWidget(self.video_size_ratio)
        video_layout.addStretch()
        size_layout.addLayout(video_layout)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        return group
    
    def create_timing_group(self) -> QGroupBox:
        """创建时间控制设置分组"""
        group = QGroupBox(_ts("⏱️ 时间控制"))
        layout = QVBoxLayout(group)
        
        # 延时设置
        timing_group = QGroupBox(_ts("延时"))
        timing_group.setCheckable(True)
        timing_group.setChecked(False)
        timing_layout = QVBoxLayout()
        
        # 延时、间隔、持续
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel(_ts("延时:")))
        self.delay_time = QDoubleSpinBox()
        self.delay_time.setRange(0, 9999)
        self.delay_time.setValue(1.0)
        self.delay_time.setSuffix(" 秒")
        time_layout.addWidget(self.delay_time)
        
        time_layout.addWidget(QLabel(_ts("间隔:")))
        self.interval_time = QDoubleSpinBox()
        self.interval_time.setRange(0, 9999)
        self.interval_time.setValue(1.0)
        self.interval_time.setSuffix(" 秒")
        time_layout.addWidget(self.interval_time)
        
        time_layout.addWidget(QLabel(_ts("持续:")))
        self.duration_time = QDoubleSpinBox()
        self.duration_time.setRange(0, 9999)
        self.duration_time.setValue(3.0)
        self.duration_time.setSuffix(" 秒")
        time_layout.addWidget(self.duration_time)
        time_layout.addStretch()
        timing_layout.addLayout(time_layout)
        
        # 循环显示等选项
        options_layout = QHBoxLayout()
        self.loop_display = QCheckBox(_ts("循环显示"))
        options_layout.addWidget(self.loop_display)
        
        self.reverse_order = QCheckBox(_ts("倒序"))
        options_layout.addWidget(self.reverse_order)
        
        self.video_duration = QCheckBox(_ts("视频水印其时长"))
        options_layout.addWidget(self.video_duration)
        
        self.display_at_end = QCheckBox(_ts("尾部显示"))
        options_layout.addWidget(self.display_at_end)
        options_layout.addStretch()
        timing_layout.addLayout(options_layout)
        
        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)
        
        # 隔帧显示
        frame_group = QGroupBox(_ts("隔帧显示"))
        frame_group.setCheckable(True)
        frame_group.setChecked(False)
        frame_layout = QHBoxLayout()
        
        frame_layout.addWidget(QLabel(_ts("隔帧显示:")))
        self.frame_interval = QSpinBox()
        self.frame_interval.setRange(1, 999)
        self.frame_interval.setValue(1)
        self.frame_interval.setSuffix(" 帧")
        frame_layout.addWidget(self.frame_interval)
        frame_layout.addStretch()
        
        frame_group.setLayout(frame_layout)
        layout.addWidget(frame_group)
        
        # 淡入淡出（视频水印）
        fade_group = QGroupBox(_ts("若水印为视频文件,淡入淡出"))
        fade_group.setCheckable(True)
        fade_group.setChecked(False)
        fade_layout = QHBoxLayout()
        
        fade_layout.addWidget(QLabel(_ts("淡入:")))
        self.fade_in = QDoubleSpinBox()
        self.fade_in.setRange(0, 99)
        self.fade_in.setValue(1.5)
        self.fade_in.setSuffix(" 秒")
        fade_layout.addWidget(self.fade_in)
        
        fade_layout.addWidget(QLabel(_ts("淡出:")))
        self.fade_out = QDoubleSpinBox()
        self.fade_out.setRange(0, 99)
        self.fade_out.setValue(0.0)
        self.fade_out.setSuffix(" 秒")
        fade_layout.addWidget(self.fade_out)
        fade_layout.addStretch()
        
        fade_group.setLayout(fade_layout)
        layout.addWidget(fade_group)
        
        return group
    
    def create_effects_group(self) -> QGroupBox:
        """创建效果设置分组"""
        group = QGroupBox(_ts("✨ 效果设置"))
        layout = QVBoxLayout(group)
        
        # 旋转
        rotate_group = QGroupBox(_ts("旋转"))
        rotate_group.setCheckable(True)
        rotate_group.setChecked(False)
        rotate_layout = QHBoxLayout()
        
        self.rotation_angle = QDoubleSpinBox()
        self.rotation_angle.setRange(-360, 360)
        self.rotation_angle.setValue(1.0)
        self.rotation_angle.setSuffix(" 度")
        rotate_layout.addWidget(self.rotation_angle)
        
        self.remove_black_edges = QCheckBox(_ts("黑边去除"))
        rotate_layout.addWidget(self.remove_black_edges)
        rotate_layout.addStretch()
        
        rotate_group.setLayout(rotate_layout)
        layout.addWidget(rotate_group)
        
        # 羽化
        feather_group = QGroupBox(_ts("羽化"))
        feather_group.setCheckable(True)
        feather_group.setChecked(False)
        feather_layout = QHBoxLayout()
        
        self.feather_value = QDoubleSpinBox()
        self.feather_value.setRange(0, 1)
        self.feather_value.setSingleStep(0.01)
        self.feather_value.setValue(0.10)
        feather_layout.addWidget(self.feather_value)
        
        self.circular_display = QCheckBox(_ts("圆形显示"))
        feather_layout.addWidget(self.circular_display)
        feather_layout.addStretch()
        
        feather_group.setLayout(feather_layout)
        layout.addWidget(feather_group)
        
        return group
    
    def create_advanced_group(self) -> QGroupBox:
        """创建高级选项分组"""
        group = QGroupBox(_ts("⚙️ 高级选项"))
        layout = QVBoxLayout(group)
        
        # 背景色消除
        bg_group = QGroupBox(_ts("背景色消除(诸如视频之蓝幕、绿幕等)"))
        bg_group.setCheckable(True)
        bg_group.setChecked(False)
        bg_layout = QVBoxLayout()
        
        # 水印背景色取样
        sample_layout = QHBoxLayout()
        self.bg_sample_radio = QRadioButton(_ts("水印背景色"))
        self.bg_sample_radio.setChecked(True)
        sample_layout.addWidget(self.bg_sample_radio)
        
        sample_layout.addWidget(QLabel(_ts("X:")))
        self.bg_sample_x = QSpinBox()
        self.bg_sample_x.setRange(0, 9999)
        self.bg_sample_x.setValue(10)
        sample_layout.addWidget(self.bg_sample_x)
        
        sample_layout.addWidget(QLabel(_ts("Y:")))
        self.bg_sample_y = QSpinBox()
        self.bg_sample_y.setRange(0, 9999)
        self.bg_sample_y.setValue(10)
        sample_layout.addWidget(self.bg_sample_y)
        
        sample_layout.addWidget(QLabel(_ts("位置:")))
        self.bg_sample_time = QDoubleSpinBox()
        self.bg_sample_time.setRange(0, 9999)
        self.bg_sample_time.setValue(0.0)
        self.bg_sample_time.setSuffix(" 秒")
        sample_layout.addWidget(self.bg_sample_time)
        sample_layout.addStretch()
        bg_layout.addLayout(sample_layout)
        
        # 指定背景色
        specify_layout = QHBoxLayout()
        self.bg_specify_radio = QRadioButton(_ts("指定背景色"))
        specify_layout.addWidget(self.bg_specify_radio)
        
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(40, 25)
        self.bg_color = QColor(0, 255, 0)  # 默认绿色
        self.bg_color_btn.setStyleSheet(f"background-color: {self.bg_color.name()}")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        specify_layout.addWidget(self.bg_color_btn)
        specify_layout.addStretch()
        bg_layout.addLayout(specify_layout)
        
        # 相似度和透明度
        similarity_layout = QHBoxLayout()
        similarity_layout.addWidget(QLabel(_ts("背景色相似度:")))
        self.bg_similarity = QDoubleSpinBox()
        self.bg_similarity.setRange(0, 1)
        self.bg_similarity.setSingleStep(0.01)
        self.bg_similarity.setValue(0.10)
        similarity_layout.addWidget(self.bg_similarity)
        
        similarity_layout.addWidget(QLabel(_ts("迭加透明度:")))
        self.bg_opacity = QDoubleSpinBox()
        self.bg_opacity.setRange(0, 1)
        self.bg_opacity.setSingleStep(0.01)
        self.bg_opacity.setValue(0.30)
        similarity_layout.addWidget(self.bg_opacity)
        similarity_layout.addStretch()
        bg_layout.addLayout(similarity_layout)
        
        bg_group.setLayout(bg_layout)
        layout.addWidget(bg_group)
        
        # 滚动速度
        scroll_layout = QHBoxLayout()
        scroll_layout.addWidget(QLabel(_ts("若水印支持滚动,其速度为:")))
        self.scroll_speed = QDoubleSpinBox()
        self.scroll_speed.setRange(0.1, 99.9)
        self.scroll_speed.setValue(2.0)
        scroll_layout.addWidget(self.scroll_speed)
        
        self.random_speed = QCheckBox(_ts("随机速度"))
        scroll_layout.addWidget(self.random_speed)
        scroll_layout.addStretch()
        layout.addLayout(scroll_layout)
        
        return group
    
    def create_text_content_group(self) -> QGroupBox:
        """创建文字内容设置分组"""
        group = QGroupBox(_ts("文字内容"))
        layout = QVBoxLayout(group)
        
        layout.addWidget(QLabel(_ts("文字内容:")))
        self.text_content = QTextEdit()
        self.text_content.setPlaceholderText(_ts("请输入水印文字内容..."))
        self.text_content.setMaximumHeight(150)
        layout.addWidget(self.text_content)
        
        # 文字预设
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel(_ts("预设文字:")))
        preset_combo = QComboBox()
        preset_combo.addItems([
            _ts("自定义"),
            _ts("版权所有 ©"),
            _ts("严禁转载"),
            _ts("内部资料"),
            _ts("机密文件"),
            _ts("样片")
        ])
        preset_combo.currentTextChanged.connect(self.apply_text_preset)
        preset_layout.addWidget(preset_combo)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)
        
        # 动态文字
        dynamic_group = QGroupBox(_ts("动态文字"))
        dynamic_layout = QVBoxLayout()
        
        self.add_timestamp = QCheckBox(_ts("添加时间戳"))
        dynamic_layout.addWidget(self.add_timestamp)
        
        self.add_filename = QCheckBox(_ts("添加文件名"))
        dynamic_layout.addWidget(self.add_filename)
        
        self.add_frame_number = QCheckBox(_ts("添加帧编号"))
        dynamic_layout.addWidget(self.add_frame_number)
        
        dynamic_group.setLayout(dynamic_layout)
        layout.addWidget(dynamic_group)
        
        return group
    
    def create_text_style_group(self) -> QGroupBox:
        """创建文字样式设置分组"""
        group = QGroupBox(_ts("文字样式"))
        layout = QVBoxLayout(group)
        
        # 字体设置
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(_ts("字体:")))

        self.text_font = QFont("Microsoft YaHei", 24)
        self.font_combo = QComboBox()
        self.font_combo.addItems(self._get_allowed_fonts())
        self.font_combo.setCurrentText(self.text_font.family())
        self.font_combo.currentTextChanged.connect(self.on_font_family_changed)
        font_layout.addWidget(self.font_combo)

        font_layout.addWidget(QLabel(_ts("大小:")))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 200)
        self.font_size_spin.setValue(self.text_font.pointSize())
        self.font_size_spin.valueChanged.connect(self.on_font_size_changed)
        font_layout.addWidget(self.font_size_spin)
        font_layout.addStretch()
        layout.addLayout(font_layout)
        
        # 颜色设置
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel(_ts("文字颜色:")))
        
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(60, 30)
        self.text_color = QColor(255, 255, 255)  # 默认白色
        self.text_color_btn.setStyleSheet(f"background-color: {self.text_color.name()}")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        color_layout.addWidget(self.text_color_btn)
        
        color_layout.addWidget(QLabel(_ts("透明度:")))
        self.text_opacity = QDoubleSpinBox()
        self.text_opacity.setRange(0, 1)
        self.text_opacity.setSingleStep(0.1)
        self.text_opacity.setValue(1.0)
        color_layout.addWidget(self.text_opacity)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # 描边设置
        stroke_group = QGroupBox(_ts("描边"))
        stroke_group.setCheckable(True)
        stroke_group.setChecked(False)
        self.stroke_group = stroke_group
        stroke_layout = QHBoxLayout()
        
        stroke_layout.addWidget(QLabel(_ts("描边颜色:")))
        self.stroke_color_btn = QPushButton()
        self.stroke_color_btn.setFixedSize(60, 30)
        self.stroke_color = QColor(0, 0, 0)  # 默认黑色
        self.stroke_color_btn.setStyleSheet(f"background-color: {self.stroke_color.name()}")
        self.stroke_color_btn.clicked.connect(self.choose_stroke_color)
        stroke_layout.addWidget(self.stroke_color_btn)
        
        stroke_layout.addWidget(QLabel(_ts("宽度:")))
        self.stroke_width = QSpinBox()
        self.stroke_width.setRange(1, 20)
        self.stroke_width.setValue(2)
        stroke_layout.addWidget(self.stroke_width)
        stroke_layout.addStretch()
        
        stroke_group.setLayout(stroke_layout)
        layout.addWidget(stroke_group)
        
        # 阴影设置
        shadow_group = QGroupBox(_ts("阴影"))
        shadow_group.setCheckable(True)
        shadow_group.setChecked(False)
        self.shadow_group = shadow_group
        shadow_layout = QVBoxLayout()
        
        shadow_offset_layout = QHBoxLayout()
        shadow_offset_layout.addWidget(QLabel(_ts("偏移 X:")))
        self.shadow_x = QSpinBox()
        self.shadow_x.setRange(-100, 100)
        self.shadow_x.setValue(2)
        shadow_offset_layout.addWidget(self.shadow_x)
        
        shadow_offset_layout.addWidget(QLabel(_ts("Y:")))
        self.shadow_y = QSpinBox()
        self.shadow_y.setRange(-100, 100)
        self.shadow_y.setValue(2)
        shadow_offset_layout.addWidget(self.shadow_y)
        shadow_offset_layout.addStretch()
        shadow_layout.addLayout(shadow_offset_layout)
        
        shadow_color_layout = QHBoxLayout()
        shadow_color_layout.addWidget(QLabel(_ts("阴影颜色:")))
        self.shadow_color_btn = QPushButton()
        self.shadow_color_btn.setFixedSize(60, 30)
        self.shadow_color = QColor(0, 0, 0, 180)  # 半透明黑色
        self.shadow_color_btn.setStyleSheet(f"background-color: rgba({self.shadow_color.red()}, {self.shadow_color.green()}, {self.shadow_color.blue()}, {self.shadow_color.alpha()})")
        self.shadow_color_btn.clicked.connect(self.choose_shadow_color)
        shadow_color_layout.addWidget(self.shadow_color_btn)
        
        shadow_color_layout.addWidget(QLabel(_ts("模糊度:")))
        self.shadow_blur = QSpinBox()
        self.shadow_blur.setRange(0, 50)
        self.shadow_blur.setValue(5)
        shadow_color_layout.addWidget(self.shadow_blur)
        shadow_color_layout.addStretch()
        shadow_layout.addLayout(shadow_color_layout)
        
        shadow_group.setLayout(shadow_layout)
        layout.addWidget(shadow_group)
        
        return group
    
    def create_text_effects_group(self) -> QGroupBox:
        """创建文字效果设置分组"""
        group = QGroupBox(_ts("✨ 文字效果"))
        layout = QVBoxLayout(group)
        
        # 文字排列
        arrange_layout = QHBoxLayout()
        arrange_layout.addWidget(QLabel(_ts("文字排列:")))
        self.text_arrange = QComboBox()
        self.text_arrange.addItems([_ts("水平"), _ts("垂直"), _ts("倾斜")])
        arrange_layout.addWidget(self.text_arrange)
        
        arrange_layout.addWidget(QLabel(_ts("角度:")))
        self.text_angle = QSpinBox()
        self.text_angle.setRange(-180, 180)
        self.text_angle.setValue(0)
        self.text_angle.setSuffix("°")
        arrange_layout.addWidget(self.text_angle)
        arrange_layout.addStretch()
        layout.addLayout(arrange_layout)
        
        # 文字动画
        animation_group = QGroupBox(_ts("文字动画"))
        animation_group.setCheckable(True)
        animation_group.setChecked(False)
        animation_layout = QVBoxLayout()
        
        anim_type_layout = QHBoxLayout()
        anim_type_layout.addWidget(QLabel(_ts("动画类型:")))
        self.animation_type = QComboBox()
        self.animation_type.addItems([
            _ts("无"),
            _ts("滚动"),
            _ts("淡入淡出"),
            _ts("缩放"),
            _ts("旋转"),
            _ts("弹跳")
        ])
        anim_type_layout.addWidget(self.animation_type)
        anim_type_layout.addStretch()
        animation_layout.addLayout(anim_type_layout)
        
        anim_speed_layout = QHBoxLayout()
        anim_speed_layout.addWidget(QLabel(_ts("动画速度:")))
        self.animation_speed = QDoubleSpinBox()
        self.animation_speed.setRange(0.1, 10.0)
        self.animation_speed.setValue(1.0)
        anim_speed_layout.addWidget(self.animation_speed)
        anim_speed_layout.addStretch()
        animation_layout.addLayout(anim_speed_layout)
        
        animation_group.setLayout(animation_layout)
        layout.addWidget(animation_group)
        
        # 背景框
        background_group = QGroupBox(_ts("背景框"))
        background_group.setCheckable(True)
        background_group.setChecked(False)
        self.background_group = background_group
        background_layout = QVBoxLayout()
        
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel(_ts("背景颜色:")))
        self.text_bg_color_btn = QPushButton()
        self.text_bg_color_btn.setFixedSize(60, 30)
        self.text_bg_color = QColor(0, 0, 0, 128)  # 半透明黑色
        self.text_bg_color_btn.setStyleSheet(f"background-color: rgba({self.text_bg_color.red()}, {self.text_bg_color.green()}, {self.text_bg_color.blue()}, {self.text_bg_color.alpha()})")
        self.text_bg_color_btn.clicked.connect(self.choose_text_bg_color)
        bg_color_layout.addWidget(self.text_bg_color_btn)
        
        bg_color_layout.addWidget(QLabel(_ts("内边距:")))
        self.text_padding = QSpinBox()
        self.text_padding.setRange(0, 50)
        self.text_padding.setValue(10)
        bg_color_layout.addWidget(self.text_padding)
        bg_color_layout.addStretch()
        background_layout.addLayout(bg_color_layout)
        
        bg_round_layout = QHBoxLayout()
        bg_round_layout.addWidget(QLabel(_ts("圆角:")))
        self.text_bg_radius = QSpinBox()
        self.text_bg_radius.setRange(0, 50)
        self.text_bg_radius.setValue(5)
        bg_round_layout.addWidget(self.text_bg_radius)
        bg_round_layout.addStretch()
        background_layout.addLayout(bg_round_layout)
        
        background_group.setLayout(background_layout)
        layout.addWidget(background_group)
        
        return group
    
    def _connect_change_signals(self):
        """连接控件变更信号到style_changed"""
        # 为所有输入控件连接信号
        for widget in self.findChildren((QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox, QTextEdit, QGroupBox)):
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(self.style_changed.emit)
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(self.style_changed.emit)
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(self.style_changed.emit)
            elif isinstance(widget, QTextEdit):
                widget.textChanged.connect(self.style_changed.emit)
            elif isinstance(widget, QGroupBox) and widget.isCheckable():
                widget.toggled.connect(self.style_changed.emit)
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        if self.watermark_type == "image":
            return self.get_image_config()
        else:
            return self.get_text_config()
    
    def get_image_config(self) -> Dict[str, Any]:
        """获取图片水印配置"""
        config = {
            'type': 'image',
            'size': {
                'enabled': False,
                'mode': 'custom' if hasattr(self, 'size_custom_radio') and self.size_custom_radio.isChecked() else 'ratio',
                'width': self.watermark_width.value() if hasattr(self, 'watermark_width') else 160,
                'height': self.watermark_height.value() if hasattr(self, 'watermark_height') else 90,
                'scale': self.watermark_scale.value() if hasattr(self, 'watermark_scale') else 100,
                'video_ref': self.video_size_ref.currentText() if hasattr(self, 'video_size_ref') else "高",
                'video_ratio': self.video_size_ratio.value() if hasattr(self, 'video_size_ratio') else 15,
                'lock_aspect': self.lock_aspect_ratio.isChecked() if hasattr(self, 'lock_aspect_ratio') else False
            },
            'timing': {
                'delay': self.delay_time.value() if hasattr(self, 'delay_time') else 1.0,
                'interval': self.interval_time.value() if hasattr(self, 'interval_time') else 1.0,
                'duration': self.duration_time.value() if hasattr(self, 'duration_time') else 3.0,
                'loop': self.loop_display.isChecked() if hasattr(self, 'loop_display') else False,
                'reverse': self.reverse_order.isChecked() if hasattr(self, 'reverse_order') else False,
                'video_duration': self.video_duration.isChecked() if hasattr(self, 'video_duration') else False,
                'display_at_end': self.display_at_end.isChecked() if hasattr(self, 'display_at_end') else False
            },
            'frame_interval': self.frame_interval.value() if hasattr(self, 'frame_interval') else 1,
            'fade': {
                'fade_in': self.fade_in.value() if hasattr(self, 'fade_in') else 1.5,
                'fade_out': self.fade_out.value() if hasattr(self, 'fade_out') else 0.0
            },
            'effects': {
                'rotation': self.rotation_angle.value() if hasattr(self, 'rotation_angle') else 1.0,
                'remove_black_edges': self.remove_black_edges.isChecked() if hasattr(self, 'remove_black_edges') else False,
                'feather': self.feather_value.value() if hasattr(self, 'feather_value') else 0.10,
                'circular': self.circular_display.isChecked() if hasattr(self, 'circular_display') else False
            },
            'background_removal': {
                'mode': 'sample' if hasattr(self, 'bg_sample_radio') and self.bg_sample_radio.isChecked() else 'specify',
                'sample_x': self.bg_sample_x.value() if hasattr(self, 'bg_sample_x') else 10,
                'sample_y': self.bg_sample_y.value() if hasattr(self, 'bg_sample_y') else 10,
                'sample_time': self.bg_sample_time.value() if hasattr(self, 'bg_sample_time') else 0.0,
                'color': self.bg_color.name() if hasattr(self, 'bg_color') else '#00ff00',
                'similarity': self.bg_similarity.value() if hasattr(self, 'bg_similarity') else 0.10,
                'opacity': self.bg_opacity.value() if hasattr(self, 'bg_opacity') else 0.30
            },
            'scroll_speed': self.scroll_speed.value() if hasattr(self, 'scroll_speed') else 2.0,
            'random_speed': self.random_speed.isChecked() if hasattr(self, 'random_speed') else False
        }
        return config
    
    def get_text_config(self) -> Dict[str, Any]:
        """获取文字水印配置"""
        config = {
            'type': 'text',
            'content': self.text_content.toPlainText() if hasattr(self, 'text_content') else '',
            'font': {
                'family': self.text_font.family() if hasattr(self, 'text_font') else 'Arial',
                'size': self.text_font.pointSize() if hasattr(self, 'text_font') else 24,
                'bold': self.text_font.bold() if hasattr(self, 'text_font') else False,
                'italic': self.text_font.italic() if hasattr(self, 'text_font') else False
            },
            'color': self.text_color.name() if hasattr(self, 'text_color') else '#ffffff',
            'opacity': self.text_opacity.value() if hasattr(self, 'text_opacity') else 1.0,
            'stroke': {
                'color': self.stroke_color.name() if hasattr(self, 'stroke_color') else '#000000',
                'width': self.stroke_width.value() if hasattr(self, 'stroke_width') else 2
            },
            'shadow': {
                'x': self.shadow_x.value() if hasattr(self, 'shadow_x') else 2,
                'y': self.shadow_y.value() if hasattr(self, 'shadow_y') else 2,
                'color': self.shadow_color.name() if hasattr(self, 'shadow_color') else '#000000',
                'blur': self.shadow_blur.value() if hasattr(self, 'shadow_blur') else 5
            },
            'arrange': self.text_arrange.currentText() if hasattr(self, 'text_arrange') else '水平',
            'angle': self.text_angle.value() if hasattr(self, 'text_angle') else 0,
            'animation': {
                'type': self.animation_type.currentText() if hasattr(self, 'animation_type') else '无',
                'speed': self.animation_speed.value() if hasattr(self, 'animation_speed') else 1.0
            },
            'background': {
                'color': self.text_bg_color.name() if hasattr(self, 'text_bg_color') else '#000000',
                'padding': self.text_padding.value() if hasattr(self, 'text_padding') else 10,
                'radius': self.text_bg_radius.value() if hasattr(self, 'text_bg_radius') else 5
            },
            'dynamic': {
                'timestamp': self.add_timestamp.isChecked() if hasattr(self, 'add_timestamp') else False,
                'filename': self.add_filename.isChecked() if hasattr(self, 'add_filename') else False,
                'frame_number': self.add_frame_number.isChecked() if hasattr(self, 'add_frame_number') else False
            }
        }
        return config
    
    def choose_bg_color(self):
        """选择背景色"""
        color = open_color_dialog(self.bg_color, self)
        if color:
            self.bg_color = color
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.style_changed.emit()
    
    def choose_text_color(self):
        """选择文字颜色"""
        color = open_color_dialog(self.text_color, self)
        if color:
            self.text_color = color
            self.text_color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.style_changed.emit()
    
    def choose_stroke_color(self):
        """选择描边颜色"""
        color = open_color_dialog(self.stroke_color, self)
        if color:
            self.stroke_color = color
            self.stroke_color_btn.setStyleSheet(f"background-color: {color.name()}")
            self.style_changed.emit()
    
    def choose_shadow_color(self):
        """选择阴影颜色"""
        color = open_color_dialog(self.shadow_color, self)
        if color:
            self.shadow_color = color
            self.shadow_color_btn.setStyleSheet(f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})")
            self.style_changed.emit()
    
    def choose_text_bg_color(self):
        """选择文字背景颜色"""
        color = open_color_dialog(self.text_bg_color, self)
        if color:
            self.text_bg_color = color
            self.text_bg_color_btn.setStyleSheet(f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})")
            self.style_changed.emit()
    
    def choose_font(self):
        """选择字体"""
        font, ok = QFontDialog.getFont(self.text_font, self)
        if ok:
            self.text_font = font
            self.font_btn.setText(f"{font.family()} {font.pointSize()}pt")
            self.style_changed.emit()

    def on_font_family_changed(self, family: str):
        """字体家族改变"""
        self.text_font.setFamily(family)
        self.style_changed.emit()

    def on_font_size_changed(self, size: int):
        """字体大小改变"""
        self.text_font.setPointSize(size)
        self.style_changed.emit()
    
    def apply_text_preset(self, text: str):
        """应用文字预设"""
        if text != "自定义":
            self.text_content.setPlainText(text)
            self.style_changed.emit()
    
    def load_config(self, config: Dict[str, Any]):
        """从配置字典加载设置到控件"""
        if not config:
            return
        
        # 暂时断开信号以避免多次触发
        self.blockSignals(True)
        
        try:
            if self.watermark_type == "image":
                self._load_image_config(config)
            else:
                self._load_text_config(config)
        finally:
            self.blockSignals(False)
    
    def _load_text_config(self, config: Dict[str, Any]):
        """加载文字水印配置"""
        # 文字内容
        if hasattr(self, 'text_content'):
            text_content = config.get('text_content', '')
            if not text_content:
                # 尝试从style_config获取
                style_config = config.get('style_config', {})
                text_content = style_config.get('content', '')
            if text_content:
                self.text_content.setPlainText(text_content)
        
        # 样式配置
        style_config = config.get('style_config', {})
        
        # 字体
        font_info = style_config.get('font', {})
        if font_info and hasattr(self, 'text_font'):
            self.text_font = QFont(
                font_info.get('family', 'Microsoft YaHei'),
                font_info.get('size', 24)
            )
            self.text_font.setBold(font_info.get('bold', False))
            self.text_font.setItalic(font_info.get('italic', False))
            if hasattr(self, 'font_combo'):
                self.font_combo.setCurrentText(self.text_font.family())
            if hasattr(self, 'font_size_spin'):
                self.font_size_spin.setValue(self.text_font.pointSize())
        
        # 文字颜色
        if 'color' in style_config and hasattr(self, 'text_color'):
            self.text_color = QColor(style_config['color'])
            if hasattr(self, 'text_color_btn'):
                self.text_color_btn.setStyleSheet(f"background-color: {self.text_color.name()}")
        
        # 透明度
        if 'opacity' in style_config and hasattr(self, 'text_opacity'):
            self.text_opacity.setValue(style_config['opacity'])
        
        # 描边
        stroke_info = style_config.get('stroke', {})
        if stroke_info:
            if hasattr(self, 'stroke_group'):
                self.stroke_group.setChecked(bool(stroke_info.get('enabled', False)))
            if 'width' in stroke_info and hasattr(self, 'stroke_width'):
                self.stroke_width.setValue(stroke_info['width'])
            if 'color' in stroke_info and hasattr(self, 'stroke_color'):
                self.stroke_color = QColor(stroke_info['color'])
                if hasattr(self, 'stroke_color_btn'):
                    self.stroke_color_btn.setStyleSheet(f"background-color: {self.stroke_color.name()}")
        
        # 阴影
        shadow_info = style_config.get('shadow', {})
        if shadow_info:
            if hasattr(self, 'shadow_group'):
                self.shadow_group.setChecked(bool(shadow_info.get('enabled', False)))
            if 'x' in shadow_info and hasattr(self, 'shadow_x'):
                self.shadow_x.setValue(shadow_info['x'])
            if 'y' in shadow_info and hasattr(self, 'shadow_y'):
                self.shadow_y.setValue(shadow_info['y'])
            if 'blur' in shadow_info and hasattr(self, 'shadow_blur'):
                self.shadow_blur.setValue(shadow_info['blur'])
            if 'color' in shadow_info and hasattr(self, 'shadow_color'):
                self.shadow_color = QColor(shadow_info['color'])
                if hasattr(self, 'shadow_color_btn'):
                    self.shadow_color_btn.setStyleSheet(
                        f"background-color: rgba({self.shadow_color.red()}, "
                        f"{self.shadow_color.green()}, {self.shadow_color.blue()}, "
                        f"{self.shadow_color.alpha()})"
                    )
        
        # 文字排列和角度
        if 'arrange' in style_config and hasattr(self, 'text_arrange'):
            arrange_text = style_config['arrange']
            index = self.text_arrange.findText(arrange_text)
            if index >= 0:
                self.text_arrange.setCurrentIndex(index)
        
        if 'angle' in style_config and hasattr(self, 'text_angle'):
            self.text_angle.setValue(style_config['angle'])
        
        # 动画
        animation_info = style_config.get('animation', {})
        if animation_info:
            if 'type' in animation_info and hasattr(self, 'animation_type'):
                anim_type = animation_info['type']
                index = self.animation_type.findText(anim_type)
                if index >= 0:
                    self.animation_type.setCurrentIndex(index)
            if 'speed' in animation_info and hasattr(self, 'animation_speed'):
                self.animation_speed.setValue(animation_info['speed'])
        
        # 背景框
        background_info = style_config.get('background', {})
        if background_info:
            if hasattr(self, 'background_group'):
                self.background_group.setChecked(bool(background_info.get('enabled', False)))
            if 'padding' in background_info and hasattr(self, 'text_padding'):
                self.text_padding.setValue(background_info['padding'])
            if 'radius' in background_info and hasattr(self, 'text_bg_radius'):
                self.text_bg_radius.setValue(background_info['radius'])
            if 'color' in background_info and hasattr(self, 'text_bg_color'):
                self.text_bg_color = QColor(background_info['color'])
                if hasattr(self, 'text_bg_color_btn'):
                    self.text_bg_color_btn.setStyleSheet(
                        f"background-color: rgba({self.text_bg_color.red()}, "
                        f"{self.text_bg_color.green()}, {self.text_bg_color.blue()}, "
                        f"{self.text_bg_color.alpha()})"
                    )
        
        # 动态文字
        dynamic_info = style_config.get('dynamic', {})
        if dynamic_info:
            if 'timestamp' in dynamic_info and hasattr(self, 'add_timestamp'):
                self.add_timestamp.setChecked(dynamic_info['timestamp'])
            if 'filename' in dynamic_info and hasattr(self, 'add_filename'):
                self.add_filename.setChecked(dynamic_info['filename'])
            if 'frame_number' in dynamic_info and hasattr(self, 'add_frame_number'):
                self.add_frame_number.setChecked(dynamic_info['frame_number'])
    
    def _load_image_config(self, config: Dict[str, Any]):
        """加载图片水印配置"""
        style_config = config.get('style_config', {})
        
        # 尺寸设置
        size_info = style_config.get('size', {})
        if size_info:
            if 'width' in size_info and hasattr(self, 'watermark_width'):
                self.watermark_width.setValue(size_info['width'])
            if 'height' in size_info and hasattr(self, 'watermark_height'):
                self.watermark_height.setValue(size_info['height'])
            if 'scale' in size_info and hasattr(self, 'watermark_scale'):
                self.watermark_scale.setValue(size_info['scale'])
            if 'lock_aspect' in size_info and hasattr(self, 'lock_aspect_ratio'):
                self.lock_aspect_ratio.setChecked(size_info['lock_aspect'])
        
        # 时间控制
        timing_info = style_config.get('timing', {})
        if timing_info:
            if 'delay' in timing_info and hasattr(self, 'delay_time'):
                self.delay_time.setValue(timing_info['delay'])
            if 'interval' in timing_info and hasattr(self, 'interval_time'):
                self.interval_time.setValue(timing_info['interval'])
            if 'duration' in timing_info and hasattr(self, 'duration_time'):
                self.duration_time.setValue(timing_info['duration'])
            if 'loop' in timing_info and hasattr(self, 'loop_display'):
                self.loop_display.setChecked(timing_info['loop'])
            if 'reverse' in timing_info and hasattr(self, 'reverse_order'):
                self.reverse_order.setChecked(timing_info['reverse'])
        
        # 效果
        effects_info = style_config.get('effects', {})
        if effects_info:
            if 'rotation' in effects_info and hasattr(self, 'rotation_angle'):
                self.rotation_angle.setValue(effects_info['rotation'])
            if 'feather' in effects_info and hasattr(self, 'feather_value'):
                self.feather_value.setValue(effects_info['feather'])
            if 'circular' in effects_info and hasattr(self, 'circular_display'):
                self.circular_display.setChecked(effects_info['circular'])
        
        # 高级选项
        if 'scroll_speed' in style_config and hasattr(self, 'scroll_speed'):
            self.scroll_speed.setValue(style_config['scroll_speed'])
        if 'random_speed' in style_config and hasattr(self, 'random_speed'):
            self.random_speed.setChecked(style_config['random_speed'])


class WatermarkStyleDialog(QDialog):
    """水印样式配置对话框（使用WatermarkStylePanel）"""
    
    def __init__(self, watermark_type: str = "image", video_path: str = None, parent=None):
        super().__init__(parent)
        self.watermark_type = watermark_type  # "image" or "text"
        self.video_path = video_path  # 视频路径（用于预览）
        self.config = {}
        self.style_panel = None
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(_ts("水印样式设置"))
        self.setMinimumWidth(650)
        self.setMinimumHeight(750)
        
        # 移除标题栏的"?"帮助按钮
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # 使用样式面板
        self.style_panel = WatermarkStylePanel(watermark_type=self.watermark_type, parent=self)
        scroll.setWidget(self.style_panel)
        layout.addWidget(scroll)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        reset_btn = ModernButton("重置", style=ModernButton.Style.Secondary)
        reset_btn.clicked.connect(self.reset_config)
        button_layout.addWidget(reset_btn)
        
        preview_btn = ModernButton("预览效果", style=ModernButton.Style.Outline, icon_name="eye")
        preview_btn.clicked.connect(self.preview_watermark)
        button_layout.addWidget(preview_btn)
        
        ok_btn = ModernButton("确定", style=ModernButton.Style.Primary)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = ModernButton("取消", style=ModernButton.Style.Secondary)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def reset_config(self):
        """重置配置到默认值"""
        if self.style_panel:
            # 委托给样式面板处理
            pass  # Panel doesn't have reset yet, we can add later if needed
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        if self.style_panel:
            return self.style_panel.get_config()
        return {}
    
    def preview_watermark(self):
        """预览水印效果"""
        # 这里可以调用预览功能，暂时先留空，后续可以添加
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, _ts("预览"), _ts("预览功能将在集成后实现"))
    
    def create_image_size_group(self) -> QGroupBox:
        """创建图片尺寸设置分组"""
        group = QGroupBox(_ts("尺寸设置"))
        layout = QVBoxLayout(group)
        
        # 水印大小
        size_group = QGroupBox(_ts("水印大小"))
        size_group.setCheckable(True)
        size_group.setChecked(False)
        size_layout = QVBoxLayout()
        
        # 自定义尺寸
        custom_layout = QHBoxLayout()
        self.size_custom_radio = QRadioButton(_ts("自定义"))
        self.size_custom_radio.setChecked(True)
        custom_layout.addWidget(self.size_custom_radio)
        
        custom_layout.addWidget(QLabel(_ts("宽度:")))
        self.watermark_width = QSpinBox()
        self.watermark_width.setRange(1, 9999)
        self.watermark_width.setValue(160)
        custom_layout.addWidget(self.watermark_width)
        
        custom_layout.addWidget(QLabel(_ts("高度:")))
        self.watermark_height = QSpinBox()
        self.watermark_height.setRange(1, 9999)
        self.watermark_height.setValue(90)
        custom_layout.addWidget(self.watermark_height)
        
        self.lock_aspect_ratio = QCheckBox(_ts("锁定比例"))
        custom_layout.addWidget(self.lock_aspect_ratio)
        custom_layout.addStretch()
        size_layout.addLayout(custom_layout)
        
        # 原比例缩放
        ratio_layout = QHBoxLayout()
        self.size_ratio_radio = QRadioButton(_ts("原比例"))
        ratio_layout.addWidget(self.size_ratio_radio)
        
        self.watermark_scale = QSpinBox()
        self.watermark_scale.setRange(1, 500)
        self.watermark_scale.setValue(100)
        self.watermark_scale.setSuffix("%")
        ratio_layout.addWidget(self.watermark_scale)
        ratio_layout.addStretch()
        size_layout.addLayout(ratio_layout)
        
        # 相对视频尺寸
        video_layout = QHBoxLayout()
        self.size_video_radio = QRadioButton(_ts("视频"))
        video_layout.addWidget(self.size_video_radio)
        
        self.video_size_ref = QComboBox()
        self.video_size_ref.addItems([_ts("高"), _ts("宽"), _ts("对角")])
        video_layout.addWidget(self.video_size_ref)
        
        video_layout.addWidget(QLabel(_ts("比例:")))
        self.video_size_ratio = QSpinBox()
        self.video_size_ratio.setRange(1, 100)
        self.video_size_ratio.setValue(15)
        self.video_size_ratio.setSuffix("%")
        video_layout.addWidget(self.video_size_ratio)
        video_layout.addStretch()
        size_layout.addLayout(video_layout)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        return group
    
    def create_timing_group(self) -> QGroupBox:
        """创建时间控制设置分组"""
        group = QGroupBox(_ts("⏱️ 时间控制"))
        layout = QVBoxLayout(group)
        
        # 延时设置
        timing_group = QGroupBox(_ts("延时"))
        timing_group.setCheckable(True)
        timing_group.setChecked(False)
        timing_layout = QVBoxLayout()
        
        # 延时、间隔、持续
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel(_ts("延时:")))
        self.delay_time = QDoubleSpinBox()
        self.delay_time.setRange(0, 9999)
        self.delay_time.setValue(1.0)
        self.delay_time.setSuffix(" 秒")
        time_layout.addWidget(self.delay_time)
        
        time_layout.addWidget(QLabel(_ts("间隔:")))
        self.interval_time = QDoubleSpinBox()
        self.interval_time.setRange(0, 9999)
        self.interval_time.setValue(1.0)
        self.interval_time.setSuffix(" 秒")
        time_layout.addWidget(self.interval_time)
        
        time_layout.addWidget(QLabel(_ts("持续:")))
        self.duration_time = QDoubleSpinBox()
        self.duration_time.setRange(0, 9999)
        self.duration_time.setValue(3.0)
        self.duration_time.setSuffix(" 秒")
        time_layout.addWidget(self.duration_time)
        time_layout.addStretch()
        timing_layout.addLayout(time_layout)
        
        # 循环显示等选项
        options_layout = QHBoxLayout()
        self.loop_display = QCheckBox(_ts("循环显示"))
        options_layout.addWidget(self.loop_display)
        
        self.reverse_order = QCheckBox(_ts("倒序"))
        options_layout.addWidget(self.reverse_order)
        
        self.video_duration = QCheckBox(_ts("视频水印其时长"))
        options_layout.addWidget(self.video_duration)
        
        self.display_at_end = QCheckBox(_ts("尾部显示"))
        options_layout.addWidget(self.display_at_end)
        options_layout.addStretch()
        timing_layout.addLayout(options_layout)
        
        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)
        
        # 隔帧显示
        frame_group = QGroupBox(_ts("隔帧显示"))
        frame_group.setCheckable(True)
        frame_group.setChecked(False)
        frame_layout = QHBoxLayout()
        
        frame_layout.addWidget(QLabel(_ts("隔帧显示:")))
        self.frame_interval = QSpinBox()
        self.frame_interval.setRange(1, 999)
        self.frame_interval.setValue(1)
        self.frame_interval.setSuffix(" 帧")
        frame_layout.addWidget(self.frame_interval)
        frame_layout.addStretch()
        
        frame_group.setLayout(frame_layout)
        layout.addWidget(frame_group)
        
        # 淡入淡出（视频水印）
        fade_group = QGroupBox(_ts("若水印为视频文件,淡入淡出"))
        fade_group.setCheckable(True)
        fade_group.setChecked(False)
        fade_layout = QHBoxLayout()
        
        fade_layout.addWidget(QLabel(_ts("淡入:")))
        self.fade_in = QDoubleSpinBox()
        self.fade_in.setRange(0, 99)
        self.fade_in.setValue(1.5)
        self.fade_in.setSuffix(" 秒")
        fade_layout.addWidget(self.fade_in)
        
        fade_layout.addWidget(QLabel(_ts("淡出:")))
        self.fade_out = QDoubleSpinBox()
        self.fade_out.setRange(0, 99)
        self.fade_out.setValue(0.0)
        self.fade_out.setSuffix(" 秒")
        fade_layout.addWidget(self.fade_out)
        fade_layout.addStretch()
        
        fade_group.setLayout(fade_layout)
        layout.addWidget(fade_group)
        
        return group
    
    def create_effects_group(self) -> QGroupBox:
        """创建效果设置分组"""
        group = QGroupBox(_ts("✨ 效果设置"))
        layout = QVBoxLayout(group)
        
        # 旋转
        rotate_group = QGroupBox(_ts("旋转"))
        rotate_group.setCheckable(True)
        rotate_group.setChecked(False)
        rotate_layout = QHBoxLayout()
        
        self.rotation_angle = QDoubleSpinBox()
        self.rotation_angle.setRange(-360, 360)
        self.rotation_angle.setValue(1.0)
        self.rotation_angle.setSuffix(" 度")
        rotate_layout.addWidget(self.rotation_angle)
        
        self.remove_black_edges = QCheckBox(_ts("黑边去除"))
        rotate_layout.addWidget(self.remove_black_edges)
        rotate_layout.addStretch()
        
        rotate_group.setLayout(rotate_layout)
        layout.addWidget(rotate_group)
        
        # 羽化
        feather_group = QGroupBox(_ts("羽化"))
        feather_group.setCheckable(True)
        feather_group.setChecked(False)
        feather_layout = QHBoxLayout()
        
        self.feather_value = QDoubleSpinBox()
        self.feather_value.setRange(0, 1)
        self.feather_value.setSingleStep(0.01)
        self.feather_value.setValue(0.10)
        feather_layout.addWidget(self.feather_value)
        
        self.circular_display = QCheckBox(_ts("圆形显示"))
        feather_layout.addWidget(self.circular_display)
        feather_layout.addStretch()
        
        feather_group.setLayout(feather_layout)
        layout.addWidget(feather_group)
        
        return group
    
    def create_advanced_group(self) -> QGroupBox:
        """创建高级选项分组"""
        group = QGroupBox(_ts("⚙️ 高级选项"))
        layout = QVBoxLayout(group)
        
        # 背景色消除
        bg_group = QGroupBox(_ts("背景色消除(诸如视频之蓝幕、绿幕等)"))
        bg_group.setCheckable(True)
        bg_group.setChecked(False)
        bg_layout = QVBoxLayout()
        
        # 水印背景色取样
        sample_layout = QHBoxLayout()
        self.bg_sample_radio = QRadioButton(_ts("水印背景色"))
        self.bg_sample_radio.setChecked(True)
        sample_layout.addWidget(self.bg_sample_radio)
        
        sample_layout.addWidget(QLabel(_ts("X:")))
        self.bg_sample_x = QSpinBox()
        self.bg_sample_x.setRange(0, 9999)
        self.bg_sample_x.setValue(10)
        sample_layout.addWidget(self.bg_sample_x)
        
        sample_layout.addWidget(QLabel(_ts("Y:")))
        self.bg_sample_y = QSpinBox()
        self.bg_sample_y.setRange(0, 9999)
        self.bg_sample_y.setValue(10)
        sample_layout.addWidget(self.bg_sample_y)
        
        sample_layout.addWidget(QLabel(_ts("位置:")))
        self.bg_sample_time = QDoubleSpinBox()
        self.bg_sample_time.setRange(0, 9999)
        self.bg_sample_time.setValue(0.0)
        self.bg_sample_time.setSuffix(" 秒")
        sample_layout.addWidget(self.bg_sample_time)
        sample_layout.addStretch()
        bg_layout.addLayout(sample_layout)
        
        # 指定背景色
        specify_layout = QHBoxLayout()
        self.bg_specify_radio = QRadioButton(_ts("指定背景色"))
        specify_layout.addWidget(self.bg_specify_radio)
        
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.setFixedSize(40, 25)
        self.bg_color = QColor(0, 255, 0)  # 默认绿色
        self.bg_color_btn.setStyleSheet(f"background-color: {self.bg_color.name()}")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        specify_layout.addWidget(self.bg_color_btn)
        specify_layout.addStretch()
        bg_layout.addLayout(specify_layout)
        
        # 相似度和透明度
        similarity_layout = QHBoxLayout()
        similarity_layout.addWidget(QLabel(_ts("背景色相似度:")))
        self.bg_similarity = QDoubleSpinBox()
        self.bg_similarity.setRange(0, 1)
        self.bg_similarity.setSingleStep(0.01)
        self.bg_similarity.setValue(0.10)
        similarity_layout.addWidget(self.bg_similarity)
        
        similarity_layout.addWidget(QLabel(_ts("迭加透明度:")))
        self.bg_opacity = QDoubleSpinBox()
        self.bg_opacity.setRange(0, 1)
        self.bg_opacity.setSingleStep(0.01)
        self.bg_opacity.setValue(0.30)
        similarity_layout.addWidget(self.bg_opacity)
        similarity_layout.addStretch()
        bg_layout.addLayout(similarity_layout)
        
        bg_group.setLayout(bg_layout)
        layout.addWidget(bg_group)
        
        # 滚动速度
        scroll_layout = QHBoxLayout()
        scroll_layout.addWidget(QLabel(_ts("若水印支持滚动,其速度为:")))
        self.scroll_speed = QDoubleSpinBox()
        self.scroll_speed.setRange(0.1, 99.9)
        self.scroll_speed.setValue(2.0)
        scroll_layout.addWidget(self.scroll_speed)
        
        self.random_speed = QCheckBox(_ts("随机速度"))
        scroll_layout.addWidget(self.random_speed)
        scroll_layout.addStretch()
        layout.addLayout(scroll_layout)
        
        return group
    
    def create_text_content_group(self) -> QGroupBox:
        """创建文字内容设置分组"""
        group = QGroupBox(_ts("文字内容"))
        layout = QVBoxLayout(group)
        
        layout.addWidget(QLabel(_ts("文字内容:")))
        self.text_content = QTextEdit()
        self.text_content.setPlaceholderText(_ts("请输入水印文字内容..."))
        self.text_content.setMaximumHeight(150)
        layout.addWidget(self.text_content)
        
        # 文字预设
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel(_ts("预设文字:")))
        preset_combo = QComboBox()
        preset_combo.addItems([
            _ts("自定义"),
            _ts("版权所有 ©"),
            _ts("严禁转载"),
            _ts("内部资料"),
            _ts("机密文件"),
            _ts("样片")
        ])
        preset_combo.currentTextChanged.connect(self.apply_text_preset)
        preset_layout.addWidget(preset_combo)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)
        
        # 动态文字
        dynamic_group = QGroupBox(_ts("动态文字"))
        dynamic_layout = QVBoxLayout()
        
        self.add_timestamp = QCheckBox(_ts("添加时间戳"))
        dynamic_layout.addWidget(self.add_timestamp)
        
        self.add_filename = QCheckBox(_ts("添加文件名"))
        dynamic_layout.addWidget(self.add_filename)
        
        self.add_frame_number = QCheckBox(_ts("添加帧编号"))
        dynamic_layout.addWidget(self.add_frame_number)
        
        dynamic_group.setLayout(dynamic_layout)
        layout.addWidget(dynamic_group)
        
        return group
    
    def create_text_style_group(self) -> QGroupBox:
        """创建文字样式设置分组"""
        group = QGroupBox(_ts("文字样式"))
        layout = QVBoxLayout(group)
        
        # 字体设置
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel(_ts("字体:")))
        
        self.text_font = QFont("Arial", 24)
        self.font_btn = QPushButton(f"{self.text_font.family()} {self.text_font.pointSize()}pt")
        self.font_btn.clicked.connect(self.choose_font)
        font_layout.addWidget(self.font_btn)
        font_layout.addStretch()
        layout.addLayout(font_layout)
        
        # 颜色设置
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel(_ts("文字颜色:")))
        
        self.text_color_btn = QPushButton()
        self.text_color_btn.setFixedSize(60, 30)
        self.text_color = QColor(255, 255, 255)  # 默认白色
        self.text_color_btn.setStyleSheet(f"background-color: {self.text_color.name()}")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        color_layout.addWidget(self.text_color_btn)
        
        color_layout.addWidget(QLabel(_ts("透明度:")))
        self.text_opacity = QDoubleSpinBox()
        self.text_opacity.setRange(0, 1)
        self.text_opacity.setSingleStep(0.1)
        self.text_opacity.setValue(1.0)
        color_layout.addWidget(self.text_opacity)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # 描边设置
        stroke_group = QGroupBox(_ts("描边"))
        stroke_group.setCheckable(True)
        stroke_group.setChecked(False)
        stroke_layout = QHBoxLayout()
        
        stroke_layout.addWidget(QLabel(_ts("描边颜色:")))
        self.stroke_color_btn = QPushButton()
        self.stroke_color_btn.setFixedSize(60, 30)
        self.stroke_color = QColor(0, 0, 0)  # 默认黑色
        self.stroke_color_btn.setStyleSheet(f"background-color: {self.stroke_color.name()}")
        self.stroke_color_btn.clicked.connect(self.choose_stroke_color)
        stroke_layout.addWidget(self.stroke_color_btn)
        
        stroke_layout.addWidget(QLabel(_ts("宽度:")))
        self.stroke_width = QSpinBox()
        self.stroke_width.setRange(1, 20)
        self.stroke_width.setValue(2)
        stroke_layout.addWidget(self.stroke_width)
        stroke_layout.addStretch()
        
        stroke_group.setLayout(stroke_layout)
        layout.addWidget(stroke_group)
        
        # 阴影设置
        shadow_group = QGroupBox(_ts("阴影"))
        shadow_group.setCheckable(True)
        shadow_group.setChecked(False)
        shadow_layout = QVBoxLayout()
        
        shadow_offset_layout = QHBoxLayout()
        shadow_offset_layout.addWidget(QLabel(_ts("偏移 X:")))
        self.shadow_x = QSpinBox()
        self.shadow_x.setRange(-100, 100)
        self.shadow_x.setValue(2)
        shadow_offset_layout.addWidget(self.shadow_x)
        
        shadow_offset_layout.addWidget(QLabel(_ts("Y:")))
        self.shadow_y = QSpinBox()
        self.shadow_y.setRange(-100, 100)
        self.shadow_y.setValue(2)
        shadow_offset_layout.addWidget(self.shadow_y)
        shadow_offset_layout.addStretch()
        shadow_layout.addLayout(shadow_offset_layout)
        
        shadow_color_layout = QHBoxLayout()
        shadow_color_layout.addWidget(QLabel(_ts("阴影颜色:")))
        self.shadow_color_btn = QPushButton()
        self.shadow_color_btn.setFixedSize(60, 30)
        self.shadow_color = QColor(0, 0, 0, 180)  # 半透明黑色
        self.shadow_color_btn.setStyleSheet(f"background-color: rgba({self.shadow_color.red()}, {self.shadow_color.green()}, {self.shadow_color.blue()}, {self.shadow_color.alpha()})")
        self.shadow_color_btn.clicked.connect(self.choose_shadow_color)
        shadow_color_layout.addWidget(self.shadow_color_btn)
        
        shadow_color_layout.addWidget(QLabel(_ts("模糊度:")))
        self.shadow_blur = QSpinBox()
        self.shadow_blur.setRange(0, 50)
        self.shadow_blur.setValue(5)
        shadow_color_layout.addWidget(self.shadow_blur)
        shadow_color_layout.addStretch()
        shadow_layout.addLayout(shadow_color_layout)
        
        shadow_group.setLayout(shadow_layout)
        layout.addWidget(shadow_group)
        
        return group
    
    def create_text_effects_group(self) -> QGroupBox:
        """创建文字效果设置分组"""
        group = QGroupBox(_ts("✨ 文字效果"))
        layout = QVBoxLayout(group)
        
        # 文字排列
        arrange_layout = QHBoxLayout()
        arrange_layout.addWidget(QLabel(_ts("文字排列:")))
        self.text_arrange = QComboBox()
        self.text_arrange.addItems([_ts("水平"), _ts("垂直"), _ts("倾斜")])
        arrange_layout.addWidget(self.text_arrange)
        
        arrange_layout.addWidget(QLabel(_ts("角度:")))
        self.text_angle = QSpinBox()
        self.text_angle.setRange(-180, 180)
        self.text_angle.setValue(0)
        self.text_angle.setSuffix("°")
        arrange_layout.addWidget(self.text_angle)
        arrange_layout.addStretch()
        layout.addLayout(arrange_layout)
        
        # 文字动画
        animation_group = QGroupBox(_ts("文字动画"))
        animation_group.setCheckable(True)
        animation_group.setChecked(False)
        animation_layout = QVBoxLayout()
        
        anim_type_layout = QHBoxLayout()
        anim_type_layout.addWidget(QLabel(_ts("动画类型:")))
        self.animation_type = QComboBox()
        self.animation_type.addItems([
            _ts("无"),
            _ts("滚动"),
            _ts("淡入淡出"),
            _ts("缩放"),
            _ts("旋转"),
            _ts("弹跳")
        ])
        anim_type_layout.addWidget(self.animation_type)
        anim_type_layout.addStretch()
        animation_layout.addLayout(anim_type_layout)
        
        anim_speed_layout = QHBoxLayout()
        anim_speed_layout.addWidget(QLabel(_ts("动画速度:")))
        self.animation_speed = QDoubleSpinBox()
        self.animation_speed.setRange(0.1, 10.0)
        self.animation_speed.setValue(1.0)
        anim_speed_layout.addWidget(self.animation_speed)
        anim_speed_layout.addStretch()
        animation_layout.addLayout(anim_speed_layout)
        
        animation_group.setLayout(animation_layout)
        layout.addWidget(animation_group)
        
        # 背景框
        background_group = QGroupBox(_ts("背景框"))
        background_group.setCheckable(True)
        background_group.setChecked(False)
        background_layout = QVBoxLayout()
        
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel(_ts("背景颜色:")))
        self.text_bg_color_btn = QPushButton()
        self.text_bg_color_btn.setFixedSize(60, 30)
        self.text_bg_color = QColor(0, 0, 0, 128)  # 半透明黑色
        self.text_bg_color_btn.setStyleSheet(f"background-color: rgba({self.text_bg_color.red()}, {self.text_bg_color.green()}, {self.text_bg_color.blue()}, {self.text_bg_color.alpha()})")
        self.text_bg_color_btn.clicked.connect(self.choose_text_bg_color)
        bg_color_layout.addWidget(self.text_bg_color_btn)
        
        bg_color_layout.addWidget(QLabel(_ts("内边距:")))
        self.text_padding = QSpinBox()
        self.text_padding.setRange(0, 50)
        self.text_padding.setValue(10)
        bg_color_layout.addWidget(self.text_padding)
        bg_color_layout.addStretch()
        background_layout.addLayout(bg_color_layout)
        
        bg_round_layout = QHBoxLayout()
        bg_round_layout.addWidget(QLabel(_ts("圆角:")))
        self.text_bg_radius = QSpinBox()
        self.text_bg_radius.setRange(0, 50)
        self.text_bg_radius.setValue(5)
        bg_round_layout.addWidget(self.text_bg_radius)
        bg_round_layout.addStretch()
        background_layout.addLayout(bg_round_layout)
        
        background_group.setLayout(background_layout)
        layout.addWidget(background_group)
        
        return group
    
    def choose_bg_color(self):
        """选择背景色"""
        color = open_color_dialog(self.bg_color, self)
        if color:
            self.bg_color = color
            self.bg_color_btn.setStyleSheet(f"background-color: {color.name()}")
    
    def choose_text_color(self):
        """选择文字颜色"""
        color = open_color_dialog(self.text_color, self)
        if color:
            self.text_color = color
            self.text_color_btn.setStyleSheet(f"background-color: {color.name()}")
    
    def choose_stroke_color(self):
        """选择描边颜色"""
        color = open_color_dialog(self.stroke_color, self)
        if color:
            self.stroke_color = color
            self.stroke_color_btn.setStyleSheet(f"background-color: {color.name()}")
    
    def choose_shadow_color(self):
        """选择阴影颜色"""
        color = open_color_dialog(self.shadow_color, self)
        if color:
            self.shadow_color = color
            self.shadow_color_btn.setStyleSheet(f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})")
    
    def choose_text_bg_color(self):
        """选择文字背景颜色"""
        color = open_color_dialog(self.text_bg_color, self)
        if color:
            self.text_bg_color = color
            self.text_bg_color_btn.setStyleSheet(f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})")
    
    def choose_font(self):
        """选择字体"""
        font, ok = QFontDialog.getFont(self.text_font, self)
        if ok:
            self.text_font = font
            self.font_btn.setText(f"{font.family()} {font.pointSize()}pt")
    
    def apply_text_preset(self, text: str):
        """应用文字预设"""
        if text != "自定义":
            self.text_content.setPlainText(text)
    
    def reset_config(self):
        """重置配置到默认值"""
        if self.watermark_type == "image":
            # 图片水印重置
            self.reset_image_watermark()
        else:
            # 文字水印重置
            self.reset_text_watermark()
        
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, _ts("提示"), _ts("所有设置已重置为默认值"))
    
    def reset_image_watermark(self):
        """重置图片水印配置"""
        # 重置所有可选分组框为未选中
        for widget in self.findChildren(QGroupBox):
            if widget.isCheckable():
                widget.setChecked(False)
        
        # 尺寸设置
        if hasattr(self, 'watermark_width'):
            self.watermark_width.setValue(160)
        if hasattr(self, 'watermark_height'):
            self.watermark_height.setValue(90)
        if hasattr(self, 'lock_aspect_ratio'):
            self.lock_aspect_ratio.setChecked(False)
        if hasattr(self, 'watermark_scale'):
            self.watermark_scale.setValue(100)
        if hasattr(self, 'video_size_ratio'):
            self.video_size_ratio.setValue(15)
        if hasattr(self, 'video_size_ref'):
            self.video_size_ref.setCurrentIndex(0)
        if hasattr(self, 'size_custom_radio'):
            self.size_custom_radio.setChecked(True)
        
        # 时间控制
        if hasattr(self, 'delay_time'):
            self.delay_time.setValue(1.0)
        if hasattr(self, 'interval_time'):
            self.interval_time.setValue(1.0)
        if hasattr(self, 'duration_time'):
            self.duration_time.setValue(5.0)
        if hasattr(self, 'fade_in'):
            self.fade_in.setValue(0.0)
        if hasattr(self, 'fade_out'):
            self.fade_out.setValue(0.0)
        
        # 效果设置
        if hasattr(self, 'rotate_angle'):
            self.rotate_angle.setValue(0)
        if hasattr(self, 'flip_horizontal'):
            self.flip_horizontal.setChecked(False)
        if hasattr(self, 'flip_vertical'):
            self.flip_vertical.setChecked(False)
        if hasattr(self, 'feather_radius'):
            self.feather_radius.setValue(0)
        if hasattr(self, 'circular_display'):
            self.circular_display.setChecked(False)
        
        # 高级选项
        if hasattr(self, 'bg_similarity'):
            self.bg_similarity.setValue(0.3)
        if hasattr(self, 'scroll_speed'):
            self.scroll_speed.setValue(1)
        if hasattr(self, 'random_speed'):
            self.random_speed.setChecked(False)
    
    def reset_text_watermark(self):
        """重置文字水印配置"""
        # 重置所有可选分组框为未选中
        for widget in self.findChildren(QGroupBox):
            if widget.isCheckable():
                widget.setChecked(False)
        
        # 文字内容
        if hasattr(self, 'text_content'):
            self.text_content.clear()
        if hasattr(self, 'text_preset'):
            self.text_preset.setCurrentIndex(0)
        if hasattr(self, 'add_timestamp'):
            self.add_timestamp.setChecked(False)
        if hasattr(self, 'add_frame_number'):
            self.add_frame_number.setChecked(False)
        
        # 文字样式
        if hasattr(self, 'text_font'):
            self.text_font = QFont("Microsoft YaHei", 36)
        if hasattr(self, 'font_combo'):
            self.font_combo.setCurrentText("Microsoft YaHei")
        if hasattr(self, 'font_size_spin'):
            self.font_size_spin.setValue(36)
        if hasattr(self, 'text_size'):
            self.text_size.setValue(36)
        if hasattr(self, 'text_color'):
            self.text_color = QColor(255, 255, 255)
        if hasattr(self, 'text_color_btn'):
            self.text_color_btn.setStyleSheet("background-color: #FFFFFF")
        if hasattr(self, 'text_align'):
            self.text_align.setCurrentIndex(0)
        if hasattr(self, 'text_bold'):
            self.text_bold.setChecked(False)
        if hasattr(self, 'text_italic'):
            self.text_italic.setChecked(False)
        if hasattr(self, 'text_underline'):
            self.text_underline.setChecked(False)
        
        # 描边
        if hasattr(self, 'stroke_width'):
            self.stroke_width.setValue(0)
        if hasattr(self, 'stroke_color'):
            self.stroke_color = QColor(0, 0, 0)
        if hasattr(self, 'stroke_color_btn'):
            self.stroke_color_btn.setStyleSheet("background-color: #000000")
        
        # 阴影
        if hasattr(self, 'shadow_offset_x'):
            self.shadow_offset_x.setValue(2)
        if hasattr(self, 'shadow_offset_y'):
            self.shadow_offset_y.setValue(2)
        if hasattr(self, 'shadow_blur'):
            self.shadow_blur.setValue(4)
        if hasattr(self, 'shadow_color'):
            self.shadow_color = QColor(0, 0, 0, 128)
        
        # 文字效果
        if hasattr(self, 'text_arrange'):
            self.text_arrange.setCurrentIndex(0)
        if hasattr(self, 'text_scale_x'):
            self.text_scale_x.setValue(100)
        if hasattr(self, 'text_scale_y'):
            self.text_scale_y.setValue(100)
        if hasattr(self, 'text_rotate'):
            self.text_rotate.setValue(0)
        if hasattr(self, 'text_animation'):
            self.text_animation.setCurrentIndex(0)
        
        # 背景框
        if hasattr(self, 'text_bg_enabled'):
            self.text_bg_enabled.setChecked(False)
        if hasattr(self, 'text_bg_padding'):
            self.text_bg_padding.setValue(10)
        if hasattr(self, 'text_bg_opacity'):
            self.text_bg_opacity.setValue(0.8)
        if hasattr(self, 'text_bg_radius'):
            self.text_bg_radius.setValue(5)
    
    def preview_watermark(self):
        """预览水印效果"""
        from PyQt6.QtWidgets import QMessageBox, QLabel, QVBoxLayout
        from PyQt6.QtGui import QPixmap, QImage
        from PyQt6.QtCore import Qt
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        import os
        
        # 如果有视频路径且文件存在，使用视频预览
        if self.video_path and os.path.exists(self.video_path):
            try:
                from ui.video_preview_player import VideoPreviewPlayer
                
                # 获取并转换配置为 VideoPreviewPlayer 期望的格式
                config = self.convert_config_for_preview()
                
                # 创建视频播放器预览
                description = "• 水印预览"
                if config.get('type') == 'image':
                    description = f"• 图片水印预览<br>尺寸: {config.get('size', '自适应')}"
                else:
                    text = config.get('text', '')
                    description = f"• 文字水印预览<br>内容: {text[:15]}..." if len(text) > 15 else f"• 文字水印预览<br>内容: {text}"

                player = VideoPreviewPlayer(
                    video_path=self.video_path,
                    watermark_configs=[config],
                    duration=10,
                    parent=self,
                    description=description
                )
                player.exec()
                return
            except Exception as e:
                print(f"视频预览失败，使用静态预览: {e}")
                import traceback
                traceback.print_exc()
        
        # 静态预览（没有视频或视频预览失败时）
        try:
            # 创建预览对话框
            preview_dialog = QDialog(self)
            preview_dialog.setWindowTitle(_ts("水印预览"))
            preview_dialog.setMinimumSize(600, 400)
            
            layout = QVBoxLayout(preview_dialog)
            
            # 创建预览图像
            preview_size = (800, 450)  # 预览尺寸
            
            if self.watermark_type == "image":
                # 图片水印预览 - 生成示例图
                # 创建预览图像（灰色背景带网格）
                img = Image.new('RGB', preview_size, color=(200, 200, 200))
                draw = ImageDraw.Draw(img)
                
                # 绘制背景网格
                for i in range(0, preview_size[0], 50):
                    draw.line([(i, 0), (i, preview_size[1])], fill=(220, 220, 220), width=1)
                for i in range(0, preview_size[1], 50):
                    draw.line([(0, i), (preview_size[0], i)], fill=(220, 220, 220), width=1)
                
                # 绘制示例水印框（表示水印位置和大小）
                wm_w = self.watermark_width.value() if hasattr(self, 'watermark_width') else 160
                wm_h = self.watermark_height.value() if hasattr(self, 'watermark_height') else 90
                
                # 居中放置
                x = (preview_size[0] - wm_w) // 2
                y = (preview_size[1] - wm_h) // 2
                
                # 绘制水印边框
                draw.rectangle([x, y, x + wm_w, y + wm_h], outline=(0, 120, 215), width=3)
                
                # 绘制对角线
                draw.line([(x, y), (x + wm_w, y + wm_h)], fill=(0, 120, 215), width=2)
                draw.line([(x + wm_w, y), (x, y + wm_h)], fill=(0, 120, 215), width=2)
                
                # 绘制中心文字说明
                try:
                    font = ImageFont.truetype("msyh.ttc", 24)
                except:
                    try:
                        font = ImageFont.truetype("arial.ttf", 24)
                    except:
                        font = ImageFont.load_default()
                
                text = "图片水印区域"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                text_x = x + (wm_w - text_w) // 2
                text_y = y + (wm_h - text_h) // 2
                
                # 绘制文字背景
                draw.rectangle([text_x - 10, text_y - 5, text_x + text_w + 10, text_y + text_h + 5], 
                             fill=(255, 255, 255), outline=(0, 120, 215), width=2)
                draw.text((text_x, text_y), text, font=font, fill=(0, 120, 215))
                
                # 转换为QPixmap
                img_array = np.array(img)
                height, width, channel = img_array.shape
                bytes_per_line = 3 * width
                q_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                
                # 显示图像
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(image_label)
                
                # 显示配置信息
                info_text = f"水印尺寸: {wm_w} × {wm_h} px\n"
                if hasattr(self, 'watermark_scale'):
                    info_text += f"缩放比例: {self.watermark_scale.value()}%\n"
                if hasattr(self, 'delay_time'):
                    info_text += f"延时: {self.delay_time.value()}秒\n"
                if hasattr(self, 'rotate_angle'):
                    info_text += f"旋转: {self.rotate_angle.value()}°\n"
                if hasattr(self, 'flip_horizontal') and self.flip_horizontal.isChecked():
                    info_text += "水平翻转: 开启\n"
                if hasattr(self, 'flip_vertical') and self.flip_vertical.isChecked():
                    info_text += "垂直翻转: 开启\n"
                if hasattr(self, 'feather_radius'):
                    info_text += f"羽化半径: {self.feather_radius.value()}px\n"
                
                info_label = QLabel(info_text)
                info_label.setStyleSheet("padding: 10px; background: #E3F2FD; border-radius: 4px; font-size: 11px;")
                layout.addWidget(info_label)
                
            else:
                # 文字水印预览
                text_content = self.text_content.toPlainText() if hasattr(self, 'text_content') else "预览文字"
                if not text_content.strip():
                    text_content = "预览文字"
                
                # 创建预览图像
                img = Image.new('RGB', preview_size, color=(200, 200, 200))
                draw = ImageDraw.Draw(img)
                
                # 绘制背景网格
                for i in range(0, preview_size[0], 50):
                    draw.line([(i, 0), (i, preview_size[1])], fill=(220, 220, 220), width=1)
                for i in range(0, preview_size[1], 50):
                    draw.line([(0, i), (preview_size[0], i)], fill=(220, 220, 220), width=1)
                
                # 获取字体
                font_size = self.text_size.value() if hasattr(self, 'text_size') else 36
                try:
                    font = ImageFont.truetype("msyh.ttc", font_size)
                except:
                    try:
                        font = ImageFont.truetype("arial.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                
                # 获取文字颜色
                color = self.text_color if hasattr(self, 'text_color') else QColor(255, 255, 255)
                text_color = (color.red(), color.green(), color.blue())
                
                # 绘制文字（居中）
                bbox = draw.textbbox((0, 0), text_content, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                x = (preview_size[0] - text_w) // 2
                y = (preview_size[1] - text_h) // 2
                
                # 绘制阴影
                if hasattr(self, 'shadow_offset_x') and self.shadow_offset_x.value() != 0:
                    shadow_x = x + self.shadow_offset_x.value()
                    shadow_y = y + self.shadow_offset_y.value()
                    draw.text((shadow_x, shadow_y), text_content, font=font, fill=(0, 0, 0, 128))
                
                # 绘制描边
                if hasattr(self, 'stroke_width') and self.stroke_width.value() > 0:
                    stroke_w = self.stroke_width.value()
                    stroke_color = self.stroke_color if hasattr(self, 'stroke_color') else QColor(0, 0, 0)
                    stroke_rgb = (stroke_color.red(), stroke_color.green(), stroke_color.blue())
                    
                    # 简单描边实现
                    for dx in range(-stroke_w, stroke_w + 1):
                        for dy in range(-stroke_w, stroke_w + 1):
                            if dx*dx + dy*dy <= stroke_w*stroke_w:
                                draw.text((x + dx, y + dy), text_content, font=font, fill=stroke_rgb)
                
                # 绘制主文字
                draw.text((x, y), text_content, font=font, fill=text_color)
                
                # 转换为QPixmap
                img_array = np.array(img)
                height, width, channel = img_array.shape
                bytes_per_line = 3 * width
                q_image = QImage(img_array.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(q_image)
                
                # 显示图像
                image_label = QLabel()
                image_label.setPixmap(pixmap)
                image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(image_label)
                
                # 显示配置信息
                info_text = f"文字内容: {text_content}\n"
                info_text += f"字体大小: {font_size}px\n"
                info_text += f"文字颜色: RGB({color.red()}, {color.green()}, {color.blue()})\n"
                if hasattr(self, 'stroke_width') and self.stroke_width.value() > 0:
                    info_text += f"描边宽度: {self.stroke_width.value()}px\n"
                if hasattr(self, 'shadow_offset_x') and self.shadow_offset_x.value() != 0:
                    info_text += f"阴影偏移: ({self.shadow_offset_x.value()}, {self.shadow_offset_y.value()})\n"
                
                info_label = QLabel(info_text)
                info_label.setStyleSheet("padding: 10px; background: #FFF3CD; border-radius: 4px; font-size: 11px;")
                layout.addWidget(info_label)
            
            # 关闭按钮
            close_btn = QPushButton(_ts("关闭"))
            close_btn.clicked.connect(preview_dialog.accept)
            close_btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 30px;
                    font-size: 13px;
                    background: #4CAF50;
                    border: none;
                    border-radius: 4px;
                    color: white;
                }
                QPushButton:hover {
                    background: #45A049;
                }
            """)
            layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
            
            preview_dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "预览错误", f"生成预览失败：{str(e)}\n\n请确保已正确配置所有参数")
            import traceback
            traceback.print_exc()
    
    def convert_config_for_preview(self) -> Dict[str, Any]:
        """转换配置为预览播放器期望的格式"""
        if self.watermark_type == "image":
            return self.convert_image_config_for_preview()
        else:
            return self.convert_text_config_for_preview()
    
    def convert_image_config_for_preview(self) -> Dict[str, Any]:
        """转换图片水印配置为预览格式"""
        config = {
            'type': 'image',
            'position': 'top_right',  # 默认位置
        }
        
        # 尺寸设置
        if hasattr(self, 'watermark_width') and hasattr(self, 'watermark_height'):
            config['size'] = (self.watermark_width.value(), self.watermark_height.value())
        
        return config
    
    def convert_text_config_for_preview(self) -> Dict[str, Any]:
        """转换文字水印配置为预览格式"""
        config = {
            'type': 'text',
            'text': '',
            'position': 'top_right',  # 默认位置
            'font_size': 36,
            'color': (255, 255, 255),
        }
        
        # 文字内容
        if hasattr(self, 'text_content'):
            config['text'] = self.text_content.toPlainText().strip()
            if not config['text']:
                config['text'] = '预览文字'
        
        # 字体大小
        if hasattr(self, 'text_size'):
            config['font_size'] = self.text_size.value()
        elif hasattr(self, 'text_font'):
            config['font_size'] = self.text_font.pointSize()
        
        # 文字颜色
        if hasattr(self, 'text_color'):
            color = self.text_color
            config['color'] = (color.red(), color.green(), color.blue())
        
        # 字体设置
        if hasattr(self, 'text_font'):
            config['font_family'] = self.text_font.family()
            config['font_bold'] = self.text_font.bold()
            config['font_italic'] = self.text_font.italic()
        
        # 描边
        if hasattr(self, 'stroke_width') and hasattr(self, 'stroke_color'):
            config['stroke_width'] = self.stroke_width.value()
            stroke_color = self.stroke_color
            config['stroke_color'] = (stroke_color.red(), stroke_color.green(), stroke_color.blue())
        
        # 阴影
        if hasattr(self, 'shadow_offset_x') and hasattr(self, 'shadow_offset_y'):
            config['shadow_offset_x'] = self.shadow_offset_x.value()
            config['shadow_offset_y'] = self.shadow_offset_y.value()
        if hasattr(self, 'shadow_color'):
            shadow_color = self.shadow_color
            config['shadow_color'] = (shadow_color.red(), shadow_color.green(), shadow_color.blue(), shadow_color.alpha())
        if hasattr(self, 'shadow_blur'):
            config['shadow_blur'] = self.shadow_blur.value()
        
        # 透明度
        if hasattr(self, 'text_opacity'):
            opacity = self.text_opacity.value()
            # 如果颜色是3个值，添加alpha通道
            if len(config['color']) == 3:
                config['color'] = (*config['color'], int(opacity * 255))
        
        return config
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置"""
        if self.watermark_type == "image":
            return self.get_image_config()
        else:
            return self.get_text_config()
    
    def get_image_config(self) -> Dict[str, Any]:
        """获取图片水印配置"""
        config = {
            'type': 'image',
            'size': {
                'enabled': False,  # 由groupbox的checkable状态决定
                'mode': 'custom' if self.size_custom_radio.isChecked() else ('ratio' if self.size_ratio_radio.isChecked() else 'video'),
                'width': self.watermark_width.value(),
                'height': self.watermark_height.value(),
                'scale': self.watermark_scale.value(),
                'video_ref': self.video_size_ref.currentText(),
                'video_ratio': self.video_size_ratio.value(),
                'lock_aspect': self.lock_aspect_ratio.isChecked()
            },
            'timing': {
                'delay': self.delay_time.value(),
                'interval': self.interval_time.value(),
                'duration': self.duration_time.value(),
                'loop': self.loop_display.isChecked(),
                'reverse': self.reverse_order.isChecked(),
                'video_duration': self.video_duration.isChecked(),
                'display_at_end': self.display_at_end.isChecked()
            },
            'frame_interval': self.frame_interval.value(),
            'fade': {
                'fade_in': self.fade_in.value(),
                'fade_out': self.fade_out.value()
            },
            'effects': {
                'rotation': self.rotation_angle.value(),
                'remove_black_edges': self.remove_black_edges.isChecked(),
                'feather': self.feather_value.value(),
                'circular': self.circular_display.isChecked()
            },
            'background_removal': {
                'mode': 'sample' if self.bg_sample_radio.isChecked() else 'specify',
                'sample_x': self.bg_sample_x.value(),
                'sample_y': self.bg_sample_y.value(),
                'sample_time': self.bg_sample_time.value(),
                'color': self.bg_color.name(),
                'similarity': self.bg_similarity.value(),
                'opacity': self.bg_opacity.value()
            },
            'scroll_speed': self.scroll_speed.value(),
            'random_speed': self.random_speed.isChecked()
        }
        return config
    
    def get_text_config(self) -> Dict[str, Any]:
        """获取文字水印配置"""
        stroke_enabled = self.stroke_group.isChecked() if hasattr(self, 'stroke_group') else False
        shadow_enabled = self.shadow_group.isChecked() if hasattr(self, 'shadow_group') else False
        background_enabled = self.background_group.isChecked() if hasattr(self, 'background_group') else False

        config = {
            'type': 'text',
            'content': self.text_content.toPlainText(),
            'font': {
                'family': self.text_font.family(),
                'size': self.text_font.pointSize(),
                'bold': self.text_font.bold(),
                'italic': self.text_font.italic()
            },
            'color': self.text_color.name(),
            'opacity': self.text_opacity.value(),
            'stroke': {
                'enabled': stroke_enabled,
                'color': self.stroke_color.name(),
                'width': self.stroke_width.value() if stroke_enabled else 0
            },
            'shadow': {
                'enabled': shadow_enabled,
                'x': self.shadow_x.value() if shadow_enabled else 0,
                'y': self.shadow_y.value() if shadow_enabled else 0,
                'color': self.shadow_color.name(),
                'blur': self.shadow_blur.value() if shadow_enabled else 0
            },
            'arrange': self.text_arrange.currentText(),
            'angle': self.text_angle.value(),
            'animation': {
                'type': self.animation_type.currentText(),
                'speed': self.animation_speed.value()
            },
            'background': {
                'enabled': background_enabled,
                'color': self.text_bg_color.name() if background_enabled else '#00000000',
                'padding': self.text_padding.value(),
                'radius': self.text_bg_radius.value()
            },
            'dynamic': {
                'timestamp': self.add_timestamp.isChecked(),
                'filename': self.add_filename.isChecked(),
                'frame_number': self.add_frame_number.isChecked()
            }
        }
        return config

