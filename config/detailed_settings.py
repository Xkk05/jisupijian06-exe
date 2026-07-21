"""
详细配置设置系统
为所有功能提供细粒度的配置选项，满足用户的各种需求
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from typing import Optional

from config.config_manager import get_user_config_dir
from enum import Enum
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoCodec(Enum):
    """视频编码器"""

    H264 = "h264"  # 通用兼容
    H265 = "h265"  # 高压缩
    VP9 = "vp9"  # WebM标准
    AV1 = "av1"  # 最新标准


class AudioCodec(Enum):
    """音频编码器"""

    AAC = "aac"  # 通用
    MP3 = "mp3"  # 常用
    OPUS = "opus"  # 高质量
    FLAC = "flac"  # 无损


class PresetQuality(Enum):
    """预设质量"""

    ULTRAFAST = "ultrafast"  # 1080p60fps 快速编码
    SUPERFAST = "superfast"  # 1080p30fps 较快编码
    VERYFAST = "veryfast"  # 720p60fps 快速编码
    FASTER = "faster"  # 720p30fps 平衡编码
    FAST = "fast"  # 480p30fps 平衡
    MEDIUM = "medium"  # 标准编码
    SLOW = "slow"  # 高质量编码
    SLOWER = "slower"  # 更高质量编码
    VERYSLOW = "veryslow"  # 最高质量编码


@dataclass
class VideoSettings:
    """视频详细设置"""

    # 基础设置
    codec: VideoCodec = VideoCodec.H264
    preset: PresetQuality = PresetQuality.MEDIUM
    crf: int = 23  # 0-51, 越小越好, 18为无损质量

    # 分辨率设置
    width: Optional[int] = None  # None表示保持原始
    height: Optional[int] = None
    aspect_ratio: str = "16:9"  # 16:9, 9:16, 4:3, 1:1等
    scale_mode: str = "fit"  # fit, crop, stretch, pad

    # 帧率设置
    fps: Optional[int] = None  # None表示保持原始
    fps_min: int = 1
    fps_max: int = 120

    # 比特率设置
    bitrate: Optional[str] = None  # None表示自动 (e.g., "5000k")
    bitrate_mode: str = "vbr"  # vbr, cbr, abr
    max_bitrate: str = "10000k"
    buffer_size: str = "20000k"

    # 高级设置
    profile: str = "main"  # baseline, main, high
    level: str = "4.2"  # H.264/H.265版本
    pixel_format: str = "yuv420p"  # yuv420p, yuvj420p, yuv422p等
    color_space: str = "bt709"  # bt709, bt601等

    # 关键帧设置
    keyint_min: int = 25  # 最小关键帧间隔
    keyint_max: int = 250  # 最大关键帧间隔

    # 其他
    enable_gpu: bool = False  # GPU加速
    threads: int = 0  # 0表示自动


@dataclass
class AudioSettings:
    """音频详细设置"""

    # 基础设置
    codec: AudioCodec = AudioCodec.AAC

    # 采样率和位深
    sample_rate: int = 48000  # 44100, 48000, 96000等
    bit_depth: int = 16  # 16, 24, 32位
    channels: int = 2  # 1, 2, 6等
    channel_layout: str = "stereo"  # mono, stereo, 5.1, 7.1等

    # 比特率设置
    bitrate: str = "128k"  # 32k-320k for MP3
    bitrate_mode: str = "vbr"  # vbr, cbr, abr

    # 音频处理
    normalize: bool = False  # 音频归一化
    peak_level: float = -1.0  # 峰值电平 (dB)

    # EQ设置
    bass_boost: int = 0  # -10到10
    treble_boost: int = 0  # -10到10

    # 压缩和限制
    compressor_enabled: bool = False
    compressor_ratio: float = 4.0  # 压缩比
    compressor_threshold: float = -20.0  # 阈值 (dB)

    # 其他
    max_channels: int = 8  # 最大处理声道数
    use_float: bool = True  # 使用浮点数处理


@dataclass
class WatermarkSettings:
    """水印详细设置"""

    # 位置和大小
    position: str = "bottom_right"  # 预设位置
    custom_x: int = 0  # 自定义X坐标
    custom_y: int = 0  # 自定义Y坐标
    width_percent: float = 10.0  # 宽度百分比
    height_percent: float = 10.0  # 高度百分比

    # 透明度和样式
    opacity: float = 0.8  # 0-1
    blur_radius: int = 0  # 模糊半径
    shadow_enabled: bool = False  # 阴影
    shadow_offset_x: int = 2
    shadow_offset_y: int = 2
    shadow_blur: int = 3
    shadow_opacity: float = 0.5

    # 时间设置
    start_time: float = 0.0  # 开始时间(秒)
    end_time: Optional[float] = None  # 结束时间
    fade_in: float = 0.0  # 淡入时长(秒)
    fade_out: float = 0.0  # 淡出时长(秒)

    # 动画
    animation_enabled: bool = False
    animation_type: str = "none"  # none, fade, move, rotate
    animation_duration: float = 1.0

    # 高级
    tile_mode: bool = False  # 平铺模式
    tile_gap: int = 10  # 瓷砖间隔
    border_enabled: bool = False  # 边框
    border_color: str = "#000000"
    border_width: int = 2

    # GPU优化
    use_gpu: bool = True  # 默认启用GPU加速


@dataclass
class SubtitleSettings:
    """字幕详细设置"""

    # 字体和样式
    font_family: str = "Arial"
    font_size: int = 24
    font_weight: int = 400  # 400, 700等

    # 颜色和背景
    text_color: str = "#FFFFFF"
    background_color: str = "#000000"
    background_opacity: float = 0.7
    outline_color: str = "#000000"
    outline_width: int = 2

    # 位置和对齐
    vertical_position: str = "bottom"  # top, middle, bottom
    vertical_margin: int = 20  # 像素
    horizontal_align: str = "center"  # left, center, right
    horizontal_margin: int = 20

    # 动画效果
    animation_type: str = "none"  # none, fade, slide, pop等
    animation_duration: float = 0.5
    animation_preset: str = "default"  # 预设动画

    # 高级功能
    auto_scaling: bool = True  # 自动缩放以适应视频
    bold_text: bool = False
    italic_text: bool = False
    underline_text: bool = False

    # 字幕处理
    delay: float = 0.0  # 延迟时间(秒)
    speed_factor: float = 1.0  # 速度因子
    character_spacing: int = 0
    line_spacing: float = 1.0


@dataclass
class TTSSettings:
    """TTS文本转语音详细设置"""

    # 基础设置
    language: str = "zh"
    voice_id: str = "default"

    # 声音参数
    speaking_rate: float = 1.0  # 0.5-2.0
    pitch: float = 1.0  # 0.5-2.0
    volume: float = 1.0  # 0-2

    # 情感控制
    emotion: str = "normal"  # normal, happy, sad, angry等
    emotion_intensity: float = 1.0  # 0-1

    # 音频处理
    sample_rate: int = 48000
    bit_depth: int = 16
    codec: AudioCodec = AudioCodec.AAC

    # 高级功能
    phoneme_mode: bool = False  # 音素模式
    ssml_enabled: bool = False  # SSML支持


@dataclass
class TranslationSettings:
    """翻译详细设置"""

    # 基础设置
    source_language: str = "auto"
    target_language: str = "zh"

    # 引擎选择
    engine: str = "local"  # local, google, baidu, minio等

    # 质量设置
    enable_quality_check: bool = True
    quality_threshold: float = 0.7  # 最小质量分数

    # 缓存策略
    enable_cache: bool = True
    cache_timeout: int = 86400  # 1天

    # 并发处理
    max_concurrent_requests: int = 5
    timeout: int = 30  # 秒

    # 后处理
    fix_punctuation: bool = True
    fix_spacing: bool = True

    # 高级
    context_aware: bool = True  # 上下文感知
    preserve_formatting: bool = True  # 保留格式
    domain: str = "general"  # general, tech, medical等


@dataclass
class BatchProcessSettings:
    """批量处理详细设置"""

    # 并发设置
    max_concurrent_tasks: int = 4
    max_workers: int = 4

    # 优先级和调度
    task_scheduling: str = "priority"  # fifo, priority, load_balance
    enable_load_balance: bool = True

    # 重试策略
    max_retries: int = 3
    retry_delay: int = 5  # 秒
    exponential_backoff: bool = True

    # 超时设置
    task_timeout: int = 3600  # 1小时
    connection_timeout: int = 30  # 秒

    # 资源限制
    max_memory_usage: int = 4096  # MB
    max_cpu_usage: float = 90.0  # %
    enable_resource_monitoring: bool = True

    # 断点续传
    enable_checkpoints: bool = True
    checkpoint_interval: int = 300  # 秒

    # 日志
    enable_detailed_logging: bool = True
    log_level: str = "INFO"

    # GPU加速
    enable_gpu_acceleration: bool = False
    gpu_device_id: int = 0


@dataclass
class ImageSettings:
    """图像处理详细设置"""

    # 基础设置
    quality: int = 95  # 0-100

    # 分辨率
    target_width: Optional[int] = None
    target_height: Optional[int] = None
    upscale_algorithm: str = "bicubic"  # nearest, linear, cubic, lanczos

    # 去水印
    watermark_removal_strength: int = 5  # 1-10
    watermark_detection_threshold: float = 0.5  # 0-1
    inpainting_method: str = "telea"  # telea, ns

    # 清晰度增强
    sharpening_strength: float = 1.0  # 0-2
    noise_reduction_strength: float = 0.5  # 0-1

    # 颜色调整
    brightness: int = 0  # -100到100
    contrast: int = 0  # -100到100
    saturation: int = 0  # -100到100
    hue_shift: int = 0  # -180到180

    # 滤镜
    enable_filters: bool = True
    filter_type: str = "none"  # none, sepia, grayscale, blur等

    # 颜色空间
    color_space: str = "srgb"  # srgb, adobe_rgb, prophoto

    # 高级
    auto_enhance: bool = True
    face_detection_enabled: bool = False


@dataclass
class CameraSettings:
    """摄像头详细设置"""

    # 设备设置
    camera_id: int = 0
    resolution_width: int = 1920
    resolution_height: int = 1080
    fps: int = 30

    # 显示设置
    flip_horizontal: bool = False
    flip_vertical: bool = False
    rotate_angle: int = 0  # 0, 90, 180, 270

    # 效果设置
    enable_background_removal: bool = False
    background_image: Optional[str] = None
    background_blur_strength: int = 5  # 1-10

    # 滤镜
    beauty_filter_enabled: bool = False
    beauty_level: int = 5  # 0-10

    # 高级功能
    enable_face_tracking: bool = False
    enable_gesture_recognition: bool = False
    recording_format: str = "mp4"
    recording_bitrate: str = "5000k"


@dataclass
class SystemSettings:
    """系统全局设置"""

    # UI设置
    theme: str = "dark"  # light, dark, auto
    language: str = "zh_CN"  # zh_CN, en 等
    default_font: str = "Arial"
    window_size: str = "1600x900"

    # 性能设置
    max_preview_resolution: str = "1920x1080"
    preview_fps: int = 30
    hardware_acceleration: bool = True

    # 路径设置
    default_output_dir: str = "./output"
    default_project_dir: str = "./projects"
    default_cache_dir: str = "./cache"

    # 日志设置
    enable_logging: bool = True
    log_level: str = "INFO"
    log_max_size: int = 10  # MB
    log_retention_days: int = 30

    # 更新设置
    check_updates: bool = True
    auto_update: bool = False

    # 其他
    enable_analytics: bool = False
    enable_crash_reporting: bool = True
    auto_save_project: bool = True
    auto_save_interval: int = 300  # 秒


class DetailedSettings:
    """详细设置管理器"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = get_user_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.video = VideoSettings()
        self.audio = AudioSettings()
        self.watermark = WatermarkSettings()
        self.subtitle = SubtitleSettings()
        self.tts = TTSSettings()
        self.translation = TranslationSettings()
        self.batch = BatchProcessSettings()
        self.image = ImageSettings()
        self.camera = CameraSettings()
        self.system = SystemSettings()

        self._load_all_settings()

    def _load_all_settings(self):
        """加载所有设置"""
        self._load_setting("video", self.video)
        self._load_setting("audio", self.audio)
        self._load_setting("watermark", self.watermark)
        self._load_setting("subtitle", self.subtitle)
        self._load_setting("tts", self.tts)
        self._load_setting("translation", self.translation)
        self._load_setting("batch", self.batch)
        self._load_setting("image", self.image)
        self._load_setting("camera", self.camera)
        self._load_setting("system", self.system)

        logger.info("所有设置已加载")

    def _load_setting(self, name: str, setting_obj):
        """加载单个设置"""
        config_file = self.config_dir / f"{name}_settings.json"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 更新设置对象
                    for key, value in data.items():
                        if hasattr(setting_obj, key):
                            setattr(setting_obj, key, value)
                logger.info(f"已加载设置: {name}")
            except Exception as e:
                logger.warning(f"加载设置失败 ({name}): {e}")

    def save_all_settings(self):
        """保存所有设置"""
        self._save_setting("video", self.video)
        self._save_setting("audio", self.audio)
        self._save_setting("watermark", self.watermark)
        self._save_setting("subtitle", self.subtitle)
        self._save_setting("tts", self.tts)
        self._save_setting("translation", self.translation)
        self._save_setting("batch", self.batch)
        self._save_setting("image", self.image)
        self._save_setting("camera", self.camera)
        self._save_setting("system", self.system)

        logger.info("所有设置已保存")

    def _save_setting(self, name: str, setting_obj):
        """保存单个设置"""
        config_file = self.config_dir / f"{name}_settings.json"
        try:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(asdict(setting_obj), f, indent=2, ensure_ascii=False)
            logger.info(f"已保存设置: {name}")
        except Exception as e:
            logger.error(f"保存设置失败 ({name}): {e}")

    def get_preset(self, preset_name: str) -> Dict[str, Any]:
        """获取预设配置"""
        presets = {
            "fast": {
                "video": {"preset": "ultrafast", "crf": 28},
                "audio": {"bitrate": "96k"},
                "batch": {"max_concurrent_tasks": 8},
            },
            "balanced": {
                "video": {"preset": "medium", "crf": 23},
                "audio": {"bitrate": "128k"},
                "batch": {"max_concurrent_tasks": 4},
            },
            "quality": {
                "video": {"preset": "slow", "crf": 18},
                "audio": {"bitrate": "320k"},
                "batch": {"max_concurrent_tasks": 2},
            },
            "ultra_quality": {
                "video": {"preset": "veryslow", "crf": 0},
                "audio": {"codec": "flac"},
                "batch": {"max_concurrent_tasks": 1},
            },
        }

        return presets.get(preset_name, {})

    def apply_preset(self, preset_name: str):
        """应用预设配置"""
        preset = self.get_preset(preset_name)

        if "video" in preset:
            for key, value in preset["video"].items():
                if hasattr(self.video, key):
                    setattr(self.video, key, value)

        if "audio" in preset:
            for key, value in preset["audio"].items():
                if hasattr(self.audio, key):
                    setattr(self.audio, key, value)

        if "batch" in preset:
            for key, value in preset["batch"].items():
                if hasattr(self.batch, key):
                    setattr(self.batch, key, value)

        logger.info(f"已应用预设: {preset_name}")

    def get_all_settings(self) -> Dict[str, Dict[str, Any]]:
        """获取所有设置"""
        return {
            "video": asdict(self.video),
            "audio": asdict(self.audio),
            "watermark": asdict(self.watermark),
            "subtitle": asdict(self.subtitle),
            "tts": asdict(self.tts),
            "translation": asdict(self.translation),
            "batch": asdict(self.batch),
            "image": asdict(self.image),
            "camera": asdict(self.camera),
            "system": asdict(self.system),
        }

    def reset_to_defaults(self):
        """重置为默认设置"""
        self.video = VideoSettings()
        self.audio = AudioSettings()
        self.watermark = WatermarkSettings()
        self.subtitle = SubtitleSettings()
        self.tts = TTSSettings()
        self.translation = TranslationSettings()
        self.batch = BatchProcessSettings()
        self.image = ImageSettings()
        self.camera = CameraSettings()
        self.system = SystemSettings()

        logger.info("已重置为默认设置")


# 延迟初始化的全局设置实例
_global_settings = None


def get_global_settings() -> DetailedSettings:
    global _global_settings
    if _global_settings is None:
        _global_settings = DetailedSettings()
    return _global_settings
