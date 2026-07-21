# -*- coding: utf-8 -*-
"""
Pytest 配置文件
"""
import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_path():
    """返回项目根目录路径"""
    return project_root


@pytest.fixture(scope="function")
def temp_dir():
    """创建临时目录，测试结束后自动清理"""
    tmp = tempfile.mkdtemp(prefix="batch_video_test_")
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="function")
def mock_config_dir(monkeypatch, temp_dir):
    """模拟配置目录"""
    def mock_get_user_config_dir():
        return temp_dir
    
    monkeypatch.setattr(
        "config.config_manager.get_user_config_dir",
        mock_get_user_config_dir
    )
    return temp_dir


@pytest.fixture(scope="function")
def mock_data_dir(monkeypatch, temp_dir):
    """模拟数据目录"""
    def mock_get_user_data_dir(app_folder="batch-video"):
        data_dir = temp_dir / app_folder / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    monkeypatch.setattr(
        "utils.app_data_paths.get_user_data_dir",
        mock_get_user_data_dir
    )
    return temp_dir


@pytest.fixture(scope="function")
def sample_video_path(temp_dir):
    """创建模拟视频文件路径（不实际创建文件）"""
    video_path = temp_dir / "test_video.mp4"
    return str(video_path)


@pytest.fixture(scope="function")
def sample_image_path(temp_dir):
    """创建模拟图片文件路径"""
    image_path = temp_dir / "test_image.png"
    # 创建一个空的PNG文件
    image_path.write_bytes(b'\x89PNG\r\n\x1a\n')
    return str(image_path)


@pytest.fixture(scope="function")
def clean_config_manager():
    """清理配置管理器单例"""
    import config.config_manager as cm
    # 重置单例
    cm._config_manager = None
    yield
    # 测试后清理
    cm._config_manager = None
