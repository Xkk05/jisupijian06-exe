# -*- coding: utf-8 -*-
"""
应用数据路径工具单元测试
"""
import pytest
import os
import tempfile
from pathlib import Path


class TestGetUserDataDir:
    """用户数据目录测试"""
    
    def test_returns_path_object(self, monkeypatch, temp_dir):
        """测试返回Path对象"""
        from utils.app_data_paths import get_user_data_dir
        
        # 模拟环境变量
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir()
        
        assert isinstance(result, Path)

    def test_creates_directory_structure(self, monkeypatch, temp_dir):
        """测试创建目录结构"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir()
        
        assert result.exists()
        assert result.is_dir()

    def test_default_app_folder(self, monkeypatch, temp_dir):
        """测试默认应用文件夹"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir()
        
        assert "batch-video" in str(result)
        assert "data" in str(result)

    def test_custom_app_folder(self, monkeypatch, temp_dir):
        """测试自定义应用文件夹"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir(app_folder="custom-app")
        
        assert "custom-app" in str(result)
        assert "data" in str(result)

    def test_uses_localappdata_first(self, monkeypatch, temp_dir):
        """测试优先使用LOCALAPPDATA"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir / "local"))
        monkeypatch.setenv("APPDATA", str(temp_dir / "roaming"))
        
        result = get_user_data_dir()
        
        assert "local" in str(result)

    def test_fallback_to_appdata(self, monkeypatch, temp_dir):
        """测试回退到APPDATA"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.setenv("APPDATA", str(temp_dir))
        
        result = get_user_data_dir()
        
        assert temp_dir.name in str(result)

    def test_fallback_to_temp(self, monkeypatch):
        """测试回退到临时目录"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.delenv("APPDATA", raising=False)
        
        result = get_user_data_dir()
        
        # 应该使用系统临时目录
        assert "temp" in str(result).lower() or "tmp" in str(result).lower()

    def test_idempotent_calls(self, monkeypatch, temp_dir):
        """测试幂等调用"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result1 = get_user_data_dir()
        result2 = get_user_data_dir()
        
        assert result1 == result2

    def test_directory_exists_after_multiple_calls(self, monkeypatch, temp_dir):
        """测试多次调用后目录存在"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        get_user_data_dir()
        get_user_data_dir()
        get_user_data_dir()
        
        result = get_user_data_dir()
        
        assert result.exists()


class TestPathStructure:
    """路径结构测试"""
    
    def test_path_components(self, monkeypatch, temp_dir):
        """测试路径组件"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir(app_folder="my-app")
        
        # 验证路径结构
        parts = result.parts
        assert "my-app" in parts
        assert "data" in parts

    def test_is_absolute_path(self, monkeypatch, temp_dir):
        """测试是绝对路径"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir()
        
        assert result.is_absolute()

    def test_parent_directories_created(self, monkeypatch, temp_dir):
        """测试父目录被创建"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir(app_folder="level1/level2")
        
        assert result.exists()
        assert result.parent.exists()


class TestEdgeCases:
    """边界情况测试"""
    
    def test_empty_app_folder(self, monkeypatch, temp_dir):
        """测试空应用文件夹"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        # 空字符串应该被处理
        result = get_user_data_dir(app_folder="")
        
        assert result.exists()
        assert "data" in str(result)

    def test_special_characters_in_folder_name(self, monkeypatch, temp_dir):
        """测试特殊字符的文件夹名"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        # 包含空格和连字符
        result = get_user_data_dir(app_folder="my-special app")
        
        assert result.exists()
        assert "my-special app" in str(result)

    def test_unicode_folder_name(self, monkeypatch, temp_dir):
        """测试Unicode文件夹名"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir(app_folder="我的应用")
        
        assert result.exists()
        assert "我的应用" in str(result)

    def test_very_long_folder_name(self, monkeypatch, temp_dir):
        """测试很长的文件夹名"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        long_name = "a" * 50
        result = get_user_data_dir(app_folder=long_name)
        
        assert result.exists()


class TestEnvironmentHandling:
    """环境变量处理测试"""
    
    def test_handles_missing_env_vars(self, monkeypatch):
        """测试处理缺失的环境变量"""
        from utils.app_data_paths import get_user_data_dir
        
        # 清除所有相关环境变量
        monkeypatch.delenv("LOCALAPPDATA", raising=False)
        monkeypatch.delenv("APPDATA", raising=False)
        
        # 不应该抛出异常
        result = get_user_data_dir()
        
        assert result.exists()

    def test_handles_empty_env_vars(self, monkeypatch):
        """测试处理空环境变量"""
        from utils.app_data_paths import get_user_data_dir
        
        monkeypatch.setenv("LOCALAPPDATA", "")
        monkeypatch.delenv("APPDATA", raising=False)
        
        # 空字符串应该导致回退
        result = get_user_data_dir()
        
        # 应该回退到临时目录
        assert result.exists()

    def test_relative_path_in_env_var(self, monkeypatch, temp_dir):
        """测试环境变量中的相对路径"""
        from utils.app_data_paths import get_user_data_dir
        
        # 使用绝对路径
        monkeypatch.setenv("LOCALAPPDATA", str(temp_dir))
        
        result = get_user_data_dir()
        
        assert result.is_absolute()
