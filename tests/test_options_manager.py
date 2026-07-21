# -*- coding: utf-8 -*-
"""
Options配置管理器单元测试
"""
import pytest
import configparser
from pathlib import Path


class TestOptionsConfigManagerInitialization:
    """OptionsConfigManager初始化测试"""
    
    def test_initialization_with_temp_dir(self, temp_dir, monkeypatch):
        """测试使用临时目录初始化"""
        from processor.options_manager import OptionsConfigManager
        
        # 模拟用户配置目录
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.config_file.parent == temp_dir
        assert isinstance(manager.config, configparser.ConfigParser)

    def test_config_file_created_if_not_exists(self, temp_dir, monkeypatch):
        """测试配置文件不存在时创建"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        # 如果模板存在，配置应该被复制
        assert manager.config_file.parent.exists()

    def test_load_existing_config(self, temp_dir, monkeypatch):
        """测试加载现有配置"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        # 创建预配置文件
        config_path = temp_dir / "options.ini"
        config_content = """[Fission]
FissionFolder = true
FissionCount = 5

[GPU]
EnableGPU = true
GPUType = cuda
"""
        config_path.write_text(config_content, encoding='utf-8')
        
        manager = OptionsConfigManager()
        
        assert manager.is_fission_enabled() is True
        assert manager.get_fission_count() == 5
        assert manager.is_gpu_enabled() is True
        assert manager.get_gpu_type() == "cuda"


class TestFissionConfig:
    """裂变配置测试"""
    
    def test_default_fission_enabled(self, temp_dir, monkeypatch):
        """测试裂变默认禁用"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.is_fission_enabled() is False

    def test_default_fission_count(self, temp_dir, monkeypatch):
        """测试默认裂变数量"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.get_fission_count() == 2

    def test_set_fission_enabled(self, temp_dir, monkeypatch):
        """测试设置裂变启用"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_fission_enabled(True)
        
        assert manager.is_fission_enabled() is True

    def test_set_fission_count(self, temp_dir, monkeypatch):
        """测试设置裂变数量"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_fission_count(10)
        
        assert manager.get_fission_count() == 10


class TestSpeedLengthConfig:
    """变速自适应配置测试"""
    
    def test_default_speed_length_enabled(self, temp_dir, monkeypatch):
        """测试默认启用变速自适应"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.is_speed_length_enabled() is True

    def test_set_speed_length_enabled(self, temp_dir, monkeypatch):
        """测试设置变速自适应"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_speed_length_enabled(False)
        
        assert manager.is_speed_length_enabled() is False


class TestGPUConfig:
    """GPU配置测试"""
    
    def test_default_gpu_enabled(self, temp_dir, monkeypatch):
        """测试默认启用GPU"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.is_gpu_enabled() is True

    def test_default_gpu_type(self, temp_dir, monkeypatch):
        """测试默认GPU类型"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.get_gpu_type() == "cuda"

    def test_default_intel_priority(self, temp_dir, monkeypatch):
        """测试默认Intel优先"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.is_intel_priority() is False

    def test_set_gpu_enabled(self, temp_dir, monkeypatch):
        """测试设置GPU启用"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_gpu_enabled(False)
        
        assert manager.is_gpu_enabled() is False

    def test_set_gpu_type(self, temp_dir, monkeypatch):
        """测试设置GPU类型"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_gpu_type("opencl")
        
        assert manager.get_gpu_type() == "opencl"


class TestOutputConfig:
    """输出配置测试"""
    
    def test_default_output_directory(self, temp_dir, monkeypatch):
        """测试默认输出目录"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.get_output_directory() == "./output"

    def test_default_separate_folder(self, temp_dir, monkeypatch):
        """测试默认独立文件夹"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.is_separate_folder_enabled() is True

    def test_default_numbering(self, temp_dir, monkeypatch):
        """测试默认编号"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.is_numbering_enabled() is False

    def test_set_output_directory(self, temp_dir, monkeypatch):
        """测试设置输出目录"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_output_directory("/custom/output/path")
        
        assert manager.get_output_directory() == "/custom/output/path"


class TaskManagementConfig:
    """任务管理配置测试"""
    
    def test_default_max_parallel_tasks(self, temp_dir, monkeypatch):
        """测试默认最大并行任务"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.get_max_parallel_tasks() == 4

    def test_set_max_parallel_tasks(self, temp_dir, monkeypatch):
        """测试设置最大并行任务"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_max_parallel_tasks(8)
        
        assert manager.get_max_parallel_tasks() == 8


class TestBatchOptions:
    """批处理选项测试"""
    
    def test_default_batch_options(self, temp_dir, monkeypatch):
        """测试默认批处理选项"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        options = manager.get_batch_options()
        
        assert options["target_format"] == "mp4"
        assert options["file_exists_action"] == "rename"
        assert options["parallel_tasks"] == 2
        assert options["use_h265"] is False
        assert options["ignore_completed"] is True

    def test_batch_options_structure(self, temp_dir, monkeypatch):
        """测试批处理选项结构"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        options = manager.get_batch_options()
        
        required_keys = [
            'target_format', 'file_exists_action', 'filename_remove_enabled',
            'filename_remove_text', 'filename_remove_regex', 'parallel_tasks',
            'use_h265', 'hdr_to_sdr', 'ignore_completed', 'complete_action',
            'open_folder_after_complete', 'sound_alert', 'gpu_accel',
            'nvidia_optimize', 'intel_optimize', 'filename_add_number',
            'subdir_support', 'output_to_folder', 'output_to_video_folder',
            'delete_original', 'to_recycle', 'move_to_original',
            'remove_task_after_complete', 'remove_confirm', 'keep_unfinished',
            'ui_language'
        ]
        
        for key in required_keys:
            assert key in options, f"缺少必需的键: {key}"


class TestGenericConfigMethods:
    """通用配置方法测试"""
    
    def test_get_all_config(self, temp_dir, monkeypatch):
        """测试获取所有配置"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        all_config = manager.get_all_config()
        
        assert isinstance(all_config, dict)

    def test_get_section(self, temp_dir, monkeypatch):
        """测试获取指定部分"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        # 获取不存在的部分
        section = manager.get_section("NonExistentSection")
        assert section == {}

    def test_set_and_get_value(self, temp_dir, monkeypatch):
        """测试设置和获取值"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_value("TestSection", "TestKey", "TestValue")
        
        assert manager.get_value("TestSection", "TestKey") == "TestValue"

    def test_get_value_with_fallback(self, temp_dir, monkeypatch):
        """测试带默认值的获取"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        # 获取不存在的值
        value = manager.get_value("NonExistent", "Key", fallback="default")
        assert value == "default"


class TestSaveConfig:
    """保存配置测试"""
    
    def test_save_config_creates_file(self, temp_dir, monkeypatch):
        """测试保存配置创建文件"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_fission_enabled(True)
        manager.set_fission_count(5)
        manager.save_config()
        
        assert manager.config_file.exists()

    def test_save_and_reload_config(self, temp_dir, monkeypatch):
        """测试保存并重新加载配置"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        # 第一个实例
        manager1 = OptionsConfigManager()
        manager1.set_fission_enabled(True)
        manager1.set_fission_count(10)
        manager1.save_config()
        
        # 第二个实例（应该加载保存的配置）
        manager2 = OptionsConfigManager()
        
        assert manager2.is_fission_enabled() is True
        assert manager2.get_fission_count() == 10


class TestUIConfig:
    """UI配置测试"""
    
    def test_default_theme(self, temp_dir, monkeypatch):
        """测试默认主题"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.get_theme() == "dark"

    def test_default_language(self, temp_dir, monkeypatch):
        """测试默认语言"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.get_language() == "zh_CN"

    def test_set_theme(self, temp_dir, monkeypatch):
        """测试设置主题"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        manager.set_theme("light")
        
        assert manager.get_theme() == "light"

    def test_set_language(self, temp_dir, monkeypatch):
        """测试设置语言"""
        from processor.options_manager import OptionsConfigManager

        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )

        manager = OptionsConfigManager()
        manager.set_language("en")

        assert manager.get_language() == "en"


class TestPerformanceConfig:
    """性能配置测试"""
    
    def test_default_hardware_acceleration(self, temp_dir, monkeypatch):
        """测试默认硬件加速"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.is_hardware_acceleration_enabled() is True

    def test_default_preview_resolution(self, temp_dir, monkeypatch):
        """测试默认预览分辨率"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.get_max_preview_resolution() == "1920x1080"

    def test_default_preview_fps(self, temp_dir, monkeypatch):
        """测试默认预览FPS"""
        from processor.options_manager import OptionsConfigManager
        
        monkeypatch.setattr(
            "config.config_manager.get_user_config_dir",
            lambda: temp_dir
        )
        
        manager = OptionsConfigManager()
        
        assert manager.get_preview_fps() == 30
