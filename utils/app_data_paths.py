"""
应用运行时数据路径工具。
统一将可写数据放到用户目录，避免安装在 Program Files 时写入失败。
"""

import os
import tempfile
from pathlib import Path


def get_user_data_dir(app_folder: str = "batch-video") -> Path:
    """返回用户可写的数据目录（不存在时自动创建）。"""
    base_dir = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or tempfile.gettempdir()
    data_dir = Path(base_dir) / app_folder / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

