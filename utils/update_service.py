"""
软件自动更新服务
负责检查更新、启动 updater.exe 执行更新
"""

import os
import sys
import subprocess
from dataclasses import dataclass, field
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from config.app_info import APP_VERSION, SOFT_NUMBER
from utils.unified_logger import logger
from utils.exceptions import NetworkException
from utils.network_utils import get as network_get, DEFAULT_RETRY_CONFIG

# 更新服务器地址
UPDATE_SERVER_URL = "http://software.kunqiongai.com:8000"


@dataclass
class UpdateInfo:
    """更新信息数据类"""
    has_update: bool = False
    version: Optional[str] = None
    update_log: Optional[str] = None
    download_url: Optional[str] = None
    package_size: Optional[int] = None
    package_hash: Optional[str] = None
    is_mandatory: bool = False
    release_date: Optional[str] = None


class UpdateCheckWorker(QThread):
    """异步检查更新的工作线程"""
    update_found = pyqtSignal(object)   # UpdateInfo
    no_update = pyqtSignal()
    check_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            url = f"{UPDATE_SERVER_URL}/api/v1/updates/check/"
            params = {
                "software": SOFT_NUMBER,
                "version": APP_VERSION,
            }
            logger.info(f"[UpdateService] 正在检查更新... server={UPDATE_SERVER_URL} software={SOFT_NUMBER} version={APP_VERSION}")
            response = network_get(url, params=params, timeout=10)
            data = response.json()

            if data.get("has_update"):
                info = UpdateInfo(
                    has_update=True,
                    version=data.get("version"),
                    update_log=data.get("update_log"),
                    download_url=data.get("download_url"),
                    package_size=data.get("package_size"),
                    package_hash=data.get("package_hash"),
                    is_mandatory=data.get("is_mandatory", False),
                    release_date=data.get("release_date"),
                )
                logger.info(f"[UpdateService] 发现新版本: {info.version}")
                self.update_found.emit(info)
            else:
                logger.info("[UpdateService] 当前已是最新版本")
                self.no_update.emit()

        except NetworkException as e:
            logger.error(f"[UpdateService] 检查更新失败（网络异常）: {e.message}")
            self.check_failed.emit(f"网络请求失败: {e.message}")
        except Exception as e:
            logger.error(f"[UpdateService] 检查更新失败: {e}")
            self.check_failed.emit(str(e))


class UpdateService(QObject):
    """更新服务 - 管理检查更新和执行更新的完整流程"""

    # 信号
    update_available = pyqtSignal(object)   # UpdateInfo
    no_update = pyqtSignal()
    check_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[UpdateCheckWorker] = None
        self._update_info: Optional[UpdateInfo] = None

    @property
    def has_update(self) -> bool:
        return self._update_info is not None and self._update_info.has_update

    @property
    def update_info(self) -> Optional[UpdateInfo]:
        return self._update_info

    def check_update(self):
        """异步检查更新"""
        if self._worker is not None and self._worker.isRunning():
            logger.warning("[UpdateService] 已有更新检查正在进行")
            return

        self._worker = UpdateCheckWorker(self)
        self._worker.update_found.connect(self._on_update_found)
        self._worker.no_update.connect(self._on_no_update)
        self._worker.check_failed.connect(self._on_check_failed)
        self._worker.start()

    def _on_update_found(self, info: UpdateInfo):
        self._update_info = info
        self.update_available.emit(info)

    def _on_no_update(self):
        self._update_info = None
        self.no_update.emit()

    def _on_check_failed(self, error: str):
        self.check_failed.emit(error)

    def _resolve_updater_path(self, app_dir: str) -> Optional[str]:
        """
        解析 updater.exe 路径。
        兼容 PyInstaller onedir 默认把附带文件放到 _internal 的场景。
        """
        candidates = [
            os.path.join(app_dir, "updater.exe"),
            os.path.join(app_dir, "_internal", "updater.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        logger.error(f"[UpdateService] updater.exe 不存在，已检查: {candidates}")
        return None

    def start_update(self):
        """启动 updater.exe 执行更新，然后退出主程序"""
        if not self._update_info or not self._update_info.has_update:
            logger.error("[UpdateService] 没有可用的更新信息")
            return False

        info = self._update_info

        # 确定 updater.exe 路径
        if getattr(sys, "frozen", False):
            # 打包后，updater.exe 和主程序同级
            app_dir = os.path.dirname(sys.executable)
            main_exe = os.path.basename(sys.executable)
        else:
            # 开发环境
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            main_exe = "launch_application.py"

        updater_path = self._resolve_updater_path(app_dir)
        if not updater_path:
            return False

        # 构建下载地址
        download_url = info.download_url or ""
        if download_url and not download_url.startswith("http"):
            download_url = f"{UPDATE_SERVER_URL}{download_url}"

        # 构建命令
        cmd = [
            updater_path,
            "--url", download_url,
            "--dir", app_dir,
            "--exe", main_exe,
            "--pid", str(os.getpid()),
        ]
        if info.package_hash:
            cmd.extend(["--hash", info.package_hash])

        logger.info(f"[UpdateService] 启动 updater: {' '.join(cmd)}")

        try:
            subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            )
            # 退出主程序
            sys.exit(0)
        except Exception as e:
            logger.error(f"[UpdateService] 启动 updater 失败: {e}")
            return False
