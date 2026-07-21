"""
配置管理系统 - 统一管理所有配置，支持文件加载、验证、缓存
"""

import json
import os
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_user_config_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "batch-video" / "config"
    return Path(tempfile.gettempdir()) / "batch-video" / "config"


@dataclass
class UIConfig:
    """UI配置"""

    theme: str = "dark"  # dark, light
    language: str = "zh_CN"  # zh_CN, en
    font_family: str = "Microsoft YaHei"
    font_size: int = 10
    window_width: int = 1400
    window_height: int = 900
    show_tips: bool = True
    auto_save: bool = True
    auto_save_interval: int = 300  # 秒
    enable_shortcuts: bool = True


@dataclass
class VideoProcessConfig:
    """视频处理配置"""

    default_codec: str = "libx264"
    default_preset: str = "medium"
    default_crf: int = 23
    gpu_acceleration: bool = False
    max_threads: int = 4
    temp_dir: str = ""
    cache_enabled: bool = True
    cache_size_mb: int = 500

    # 为了兼容旧代码，添加各个面板需要的配置属性
    def __post_init__(self):
        from types import SimpleNamespace

        # 创建各个面板的配置对象，带有默认属性
        self.watermark = SimpleNamespace(
            remove_enabled=False,
            add_enabled=False,
            watermark_path="",
            watermark_file="",
            opacity=100,
            position="right-bottom",
            offset_x=10,
            offset_y=10,
            scale=100,
            # 去水印相关
            watermark_scheme="不去水印",
            time_segment_enabled=False,
            time_segment_start=0.0,
            time_segment_duration=0.1,
            custom_region1=(0, 0, 100, 100),
            custom_region2=(0, 0, 100, 100),
            custom_region3=(0, 0, 100, 100),
            # 画中画相关
            pip_enabled=False,
            pip_video="",
            pip_position="右上",
            pip_size=(320, 240),
            # 预览相关
            preview_enabled=False,
        )
        self.crop = SimpleNamespace(
            enabled=False,
            mode="像素",  # "像素", "中间", "百分比"
            pixel_top=0,
            pixel_bottom=0,
            pixel_left=0,
            pixel_right=0,
            aspect_ratio="16:9",  # "1:1", "16:9", "9:16", "4:3", "3:4"
            percent_value=50.0,  # 1-100
            percent_crop_mode="四边",  # "左上", "右上", "左下", "右下", "上边", "下边", "左边", "右边", "上下", "左右", "随机"
            random_crop=False,
        )
        self.trim = SimpleNamespace(
            enabled=False, start_time=0.0, end_time=0.0, duration=0.0
        )
        self.speed = SimpleNamespace(
            enabled=False, speed_factor=1.0, maintain_pitch=True
        )
        self.text = SimpleNamespace(
            enabled=False,
            text="",
            font_size=48,
            font_color="#FFFFFF",
            position="center",
            duration=5.0,
        )
        self.audio = SimpleNamespace(
            enabled=False, volume=100, fade_in=0.0, fade_out=0.0
        )
        self.image_adjust = SimpleNamespace(
            enabled=False, brightness=0, contrast=0, saturation=0, hue=0
        )
        self.output = SimpleNamespace(output_dir="", format="mp4", quality="high")


@dataclass
class AudioConfig:
    """音频处理配置"""

    sample_rate: int = 44100
    channels: int = 2
    bit_depth: int = 16
    default_mixer_mode: str = "longest"
    normalize_audio: bool = True
    loudnorm_integrated_loudness: float = -16.0
    loudnorm_true_peak: float = -1.5


@dataclass
class ExportConfig:
    """导出配置"""

    default_format: str = "mp4"
    default_quality: str = "high"
    default_bitrate: str = "auto"
    parallel_export: bool = True
    max_export_tasks: int = 2
    enable_breakpoint_resume: bool = True
    quality_assessment: bool = True


@dataclass
class AdvancedConfig:
    """高级配置"""

    log_level: str = "INFO"
    debug_mode: bool = False
    profile_performance: bool = False
    memory_limit_mb: int = 4096
    enable_telemetry: bool = False
    check_updates: bool = True
    auto_update: bool = False


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = get_user_config_dir()
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 初始化所有配置
        self.ui = UIConfig()
        self.video = VideoProcessConfig()
        self.audio = AudioConfig()
        self.export = ExportConfig()
        self.advanced = AdvancedConfig()

        # 加载配置
        self._load_configs()

    def _load_configs(self):
        """加载所有配置文件"""
        config_files = {
            "ui.yaml": ("ui", UIConfig),
            "video.yaml": ("video", VideoProcessConfig),
            "audio.yaml": ("audio", AudioConfig),
            "export.yaml": ("export", ExportConfig),
            "advanced.yaml": ("advanced", AdvancedConfig),
        }

        for filename, (attr_name, config_class) in config_files.items():
            config_path = self.config_dir / filename
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        config_data = yaml.safe_load(f) or {}

                    # 合并配置（后续内容覆盖默认值）
                    current_config = getattr(self, attr_name)
                    for key, value in config_data.items():
                        if hasattr(current_config, key):
                            setattr(current_config, key, value)

                    logger.info(f"✅ 配置已加载: {filename}")
                except Exception as e:
                    logger.warning(f"⚠️ 配置加载失败 {filename}: {e}")
            else:
                # 创建默认配置文件
                self._save_config(attr_name, filename)

    def _save_config(self, attr_name: str, filename: str):
        """保存单个配置文件"""
        try:
            config_obj = getattr(self, attr_name)
            config_data = asdict(config_obj)

            config_path = self.config_dir / filename
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, allow_unicode=True, default_flow_style=False)

            logger.debug(f"✅ 配置已保存: {filename}")
        except Exception as e:
            logger.error(f"❌ 配置保存失败 {filename}: {e}")

    def save_all_configs(self):
        """保存所有配置"""
        self._save_config("ui", "ui.yaml")
        self._save_config("video", "video.yaml")
        self._save_config("audio", "audio.yaml")
        self._save_config("export", "export.yaml")
        self._save_config("advanced", "advanced.yaml")

        logger.info("✅ 所有配置已保存")

    def reset_to_defaults(self):
        """重置为默认配置"""
        self.ui = UIConfig()
        self.video = VideoProcessConfig()
        self.audio = AudioConfig()
        self.export = ExportConfig()
        self.advanced = AdvancedConfig()

        self.save_all_configs()
        logger.info("✅ 配置已重置为默认值")

    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置的字典"""
        return {
            "ui": asdict(self.ui),
            "video": asdict(self.video),
            "audio": asdict(self.audio),
            "export": asdict(self.export),
            "advanced": asdict(self.advanced),
        }

    def validate_configs(self) -> bool:
        """验证配置的有效性"""
        try:
            # 验证UI配置
            if self.ui.window_width < 800 or self.ui.window_height < 600:
                logger.warning("⚠️ 窗口大小过小，将调整")
                self.ui.window_width = max(800, self.ui.window_width)
                self.ui.window_height = max(600, self.ui.window_height)

            # 验证视频配置
            if self.video.max_threads < 1:
                self.video.max_threads = 4

            # 验证音频配置
            if self.audio.sample_rate < 8000:
                self.audio.sample_rate = 44100

            logger.info("✅ 配置验证通过")
            return True
        except Exception as e:
            logger.error(f"❌ 配置验证失败: {e}")
            return False


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.validate_configs()
    return _config_manager


def init_config_manager(config_dir: Optional[str] = None) -> ConfigManager:
    """初始化配置管理器"""
    global _config_manager
    _config_manager = ConfigManager(config_dir)
    _config_manager.validate_configs()
    return _config_manager
