# -*- coding: utf-8 -*-
"""
配置管理器单元测试
"""

import pytest
import yaml
from pathlib import Path


class TestUIConfig:
    """UI配置测试"""

    def test_default_values(self):
        """测试UI配置默认值"""
        from config.config_manager import UIConfig

        config = UIConfig()
        assert config.theme == "dark"
        assert config.language == "zh_CN"
        assert config.font_family == "Microsoft YaHei"
        assert config.font_size == 10
        assert config.window_width == 1400
        assert config.window_height == 900
        assert config.show_tips is True
        assert config.auto_save is True
        assert config.auto_save_interval == 300
        assert config.enable_shortcuts is True

    def test_custom_values(self):
        """测试自定义UI配置"""
        from config.config_manager import UIConfig

        config = UIConfig(theme="light", language="en", window_width=1920, window_height=1080)
        assert config.theme == "light"
        assert config.language == "en"
        assert config.window_width == 1920
        assert config.window_height == 1080


class TestVideoProcessConfig:
    """视频处理配置测试"""

    def test_default_values(self):
        """测试视频处理配置默认值"""
        from config.config_manager import VideoProcessConfig

        config = VideoProcessConfig()
        assert config.default_codec == "libx264"
        assert config.default_preset == "medium"
        assert config.default_crf == 23
        assert config.gpu_acceleration is False
        assert config.max_threads == 4
        assert config.cache_enabled is True
        assert config.cache_size_mb == 500

    def test_post_init_subconfigs(self):
        """测试__post_init__创建的子配置"""
        from config.config_manager import VideoProcessConfig

        config = VideoProcessConfig()
        # 测试水印配置
        assert hasattr(config, "watermark")
        assert hasattr(config.watermark, "remove_enabled")
        assert hasattr(config.watermark, "add_enabled")

        # 测试裁剪配置
        assert hasattr(config, "crop")
        assert config.crop.mode == "像素"

        # 测试变速配置
        assert hasattr(config, "speed")
        assert config.speed.speed_factor == 1.0


class TestAudioConfig:
    """音频配置测试"""

    def test_default_values(self):
        """测试音频配置默认值"""
        from config.config_manager import AudioConfig

        config = AudioConfig()
        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.bit_depth == 16
        assert config.default_mixer_mode == "longest"
        assert config.normalize_audio is True
        assert config.loudnorm_integrated_loudness == -16.0
        assert config.loudnorm_true_peak == -1.5


class TestConfigManager:
    """配置管理器测试"""

    def test_initialization(self, temp_dir, monkeypatch, clean_config_manager):
        """测试配置管理器初始化"""
        from config.config_manager import ConfigManager

        # 模拟配置目录
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir", lambda: temp_dir
        )

        manager = ConfigManager(str(temp_dir))

        assert manager.config_dir == temp_dir
        assert manager.ui is not None
        assert manager.video is not None
        assert manager.audio is not None
        assert manager.export is not None
        assert manager.advanced is not None

    def test_save_and_load_config(self, temp_dir, monkeypatch, clean_config_manager):
        """测试配置保存和加载"""
        from config.config_manager import ConfigManager

        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir", lambda: temp_dir
        )

        # 创建管理器并修改配置
        manager = ConfigManager(str(temp_dir))
        manager.ui.theme = "light"
        manager.ui.font_size = 14
        manager.video.max_threads = 8

        # 保存配置
        manager.save_all_configs()

        # 验证文件存在
        assert (temp_dir / "ui.yaml").exists()
        assert (temp_dir / "video.yaml").exists()

        # 创建新管理器实例并加载配置
        monkeypatch.setattr("config.config_manager._config_manager", None)
        manager2 = ConfigManager(str(temp_dir))

        assert manager2.ui.theme == "light"
        assert manager2.ui.font_size == 14
        assert manager2.video.max_threads == 8

    def test_reset_to_defaults(self, temp_dir, monkeypatch, clean_config_manager):
        """测试重置为默认值"""
        from config.config_manager import ConfigManager, UIConfig

        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir", lambda: temp_dir
        )

        manager = ConfigManager(str(temp_dir))
        manager.ui.theme = "custom_theme"
        manager.save_all_configs()

        # 重置
        manager.reset_to_defaults()

        assert manager.ui.theme == "dark"  # 默认值

    def test_validate_configs(self, temp_dir, monkeypatch, clean_config_manager):
        """测试配置验证"""
        from config.config_manager import ConfigManager

        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir", lambda: temp_dir
        )

        manager = ConfigManager(str(temp_dir))

        # 设置无效值
        manager.ui.window_width = 100  # 小于800
        manager.video.max_threads = 0  # 小于1
        manager.audio.sample_rate = 1000  # 小于8000

        # 验证应该修复这些问题
        result = manager.validate_configs()
        assert result is True
        assert manager.ui.window_width >= 800
        assert manager.video.max_threads >= 1
        assert manager.audio.sample_rate >= 8000

    def test_get_all_configs(self, temp_dir, monkeypatch, clean_config_manager):
        """测试获取所有配置"""
        from config.config_manager import ConfigManager

        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir", lambda: temp_dir
        )

        manager = ConfigManager(str(temp_dir))
        all_configs = manager.get_all_configs()

        assert "ui" in all_configs
        assert "video" in all_configs
        assert "audio" in all_configs
        assert "export" in all_configs
        assert "advanced" in all_configs


class TestGlobalConfigManager:
    """全局配置管理器测试"""

    def test_singleton_pattern(self, temp_dir, monkeypatch, clean_config_manager):
        """测试单例模式"""
        from config.config_manager import get_config_manager, init_config_manager

        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir", lambda: temp_dir
        )

        manager1 = get_config_manager()
        manager2 = get_config_manager()

        assert manager1 is manager2

    def test_init_config_manager(self, temp_dir, monkeypatch, clean_config_manager):
        """测试初始化配置管理器"""
        from config.config_manager import init_config_manager

        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir", lambda: temp_dir
        )

        manager = init_config_manager(str(temp_dir))
        assert manager.config_dir == temp_dir
