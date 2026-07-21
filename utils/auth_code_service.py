# -*- coding: utf-8 -*-
"""
鲲穹工具箱授权码服务。

负责机器码生成、授权码接口调用、授权码缓存和获取页面跳转。
UI 层只需要关心检查结果和验证结果，不直接处理接口细节。
"""

import hashlib
import json
import os
import platform
import subprocess
import uuid
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from config.app_info import SOFT_NUMBER
from utils.app_data_paths import get_user_data_dir
from utils.exceptions import NetworkException
from utils.network_utils import post as network_post
from utils.unified_logger import logger


API_BASE_URL = "https://api-web.kunqiongai.com"
DEFAULT_AUTH_CODE_URL = "https://auth-code.kunqiongai.com/web/auth/index"
AUTH_CODE_CACHE_FILE = "auth_code.json"


@dataclass
class AuthCodeCheckResult:
    success: bool
    need_auth_code: bool
    device_id: str
    auth_code_url: str = DEFAULT_AUTH_CODE_URL
    message: str = ""


@dataclass
class AuthCodeVerifyResult:
    success: bool
    is_valid: bool
    message: str = ""
    auth_code_status: int = 0


def _run_system_command(command: list[str]) -> str:
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    output = subprocess.check_output(
        command,
        text=True,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags,
    )
    return output.strip()


def get_cpu_info() -> Optional[str]:
    """获取 CPU 标识，失败时返回 None。"""
    system = platform.system()
    try:
        if system == "Windows":
            result = _run_system_command(["wmic", "cpu", "get", "ProcessorId"])
            lines = [line.strip() for line in result.splitlines() if line.strip()]
            if len(lines) >= 2:
                return lines[1]
        if system == "Linux":
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.startswith("serial"):
                        return line.split(":", 1)[1].strip()
        if system == "Darwin":
            return _run_system_command(["sysctl", "-n", "machdep.cpu.core_count"])
    except Exception as exc:
        logger.debug(f"[AuthCodeService] 获取 CPU 信息失败: {exc}")
    return None


def get_mac_address() -> str:
    """获取 MAC 地址。"""
    mac_num = f"{uuid.getnode():012X}"
    return "-".join(mac_num[i : i + 2] for i in range(0, 12, 2))


def get_motherboard_serial() -> Optional[str]:
    """获取主板序列号，目前仅 Windows 支持。"""
    if platform.system() != "Windows":
        return None
    try:
        result = _run_system_command(["wmic", "baseboard", "get", "SerialNumber"])
        lines = [line.strip() for line in result.splitlines() if line.strip()]
        if len(lines) >= 2 and lines[1]:
            return lines[1]
    except Exception as exc:
        logger.debug(f"[AuthCodeService] 获取主板序列号失败: {exc}")
    return None


def get_machine_code() -> str:
    """生成唯一机器码：CPU + MAC + 主板信息组合后 SHA256。"""
    hardware_infos: list[str] = []

    cpu_info = get_cpu_info()
    if cpu_info:
        hardware_infos.append(cpu_info)

    mac_info = get_mac_address()
    if mac_info:
        hardware_infos.append(mac_info)

    board_serial = get_motherboard_serial()
    if board_serial:
        hardware_infos.append(board_serial)

    combined = "|".join(hardware_infos)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def build_auth_code_url(base_url: str, device_id: str, soft_number: str = SOFT_NUMBER) -> str:
    """构建授权码获取页地址，保留原 URL 查询参数并覆盖设备与软件编号。"""
    parsed = urlparse(base_url or DEFAULT_AUTH_CODE_URL)
    query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_items["device_id"] = device_id
    query_items["software_code"] = soft_number
    return urlunparse(parsed._replace(query=urlencode(query_items)))


class AuthCodeService:
    """授权码业务服务。"""

    def __init__(
        self,
        soft_number: str = SOFT_NUMBER,
        api_base_url: str = API_BASE_URL,
        data_dir_provider: Callable[[], Path] = get_user_data_dir,
        machine_code_provider: Callable[[], str] = get_machine_code,
        post_func: Callable = network_post,
        opener: Callable[[str], object] = webbrowser.open,
    ):
        self.soft_number = str(soft_number)
        self.api_base_url = api_base_url.rstrip("/")
        self._data_dir_provider = data_dir_provider
        self._machine_code_provider = machine_code_provider
        self._post = post_func
        self._opener = opener

    @property
    def cache_path(self) -> Path:
        data_dir = Path(self._data_dir_provider())
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / AUTH_CODE_CACHE_FILE

    def get_device_id(self) -> str:
        return self._machine_code_provider()

    def get_stored_auth_code(self) -> Optional[str]:
        try:
            if not self.cache_path.exists():
                return None
            with self.cache_path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            auth_code = str(payload.get("auth_code", "")).strip()
            return auth_code or None
        except Exception as exc:
            logger.warning(f"[AuthCodeService] 读取授权码缓存失败: {exc}")
            return None

    def store_auth_code(self, auth_code: Optional[str]) -> None:
        if not auth_code:
            self.clear_auth_code()
            return
        try:
            with self.cache_path.open("w", encoding="utf-8") as f:
                json.dump({"auth_code": auth_code.strip()}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"[AuthCodeService] 保存授权码缓存失败: {exc}")

    def clear_auth_code(self) -> None:
        try:
            if self.cache_path.exists():
                self.cache_path.unlink()
        except Exception as exc:
            logger.warning(f"[AuthCodeService] 清理授权码缓存失败: {exc}")

    def check_need_auth_code(self) -> AuthCodeCheckResult:
        device_id = self.get_device_id()
        try:
            response = self._post(
                f"{self.api_base_url}/soft_desktop/check_get_auth_code",
                data={"device_id": device_id, "soft_number": self.soft_number},
                timeout=10,
            )
            result = response.json()
            if result.get("code") != 1:
                return AuthCodeCheckResult(
                    success=False,
                    need_auth_code=True,
                    device_id=device_id,
                    message=result.get("msg", "检查授权码失败"),
                )

            data = result.get("data") or {}
            return AuthCodeCheckResult(
                success=True,
                need_auth_code=int(data.get("is_need_auth_code") or 0) == 1,
                auth_code_url=data.get("auth_code_url") or DEFAULT_AUTH_CODE_URL,
                device_id=device_id,
                message=result.get("msg", ""),
            )
        except NetworkException as exc:
            logger.warning(f"[AuthCodeService] 检查授权码网络异常: {exc.message}")
            return AuthCodeCheckResult(
                success=False,
                need_auth_code=True,
                device_id=device_id,
                message=f"检查授权码失败: {exc.message}",
            )
        except Exception as exc:
            logger.warning(f"[AuthCodeService] 检查授权码失败: {exc}")
            return AuthCodeCheckResult(
                success=False,
                need_auth_code=True,
                device_id=device_id,
                message=f"检查授权码失败: {exc}",
            )

    def verify_auth_code(self, auth_code: str) -> AuthCodeVerifyResult:
        clean_code = auth_code.strip()
        if not clean_code:
            return AuthCodeVerifyResult(False, False, "请输入授权码")

        try:
            response = self._post(
                f"{self.api_base_url}/soft_desktop/check_auth_code_valid",
                data={
                    "device_id": self.get_device_id(),
                    "soft_number": self.soft_number,
                    "auth_code": clean_code,
                },
                timeout=10,
            )
            result = response.json()
            if result.get("code") != 1:
                return AuthCodeVerifyResult(
                    success=False,
                    is_valid=False,
                    message=result.get("msg", "授权码验证失败"),
                )

            data = result.get("data") or {}
            status = int(data.get("auth_code_status") or 0)
            is_valid = status == 1
            if is_valid:
                self.store_auth_code(clean_code)
            else:
                self.clear_auth_code()

            return AuthCodeVerifyResult(
                success=True,
                is_valid=is_valid,
                auth_code_status=status,
                message=result.get("msg", "授权码有效" if is_valid else "授权码无效或已过期"),
            )
        except NetworkException as exc:
            logger.warning(f"[AuthCodeService] 验证授权码网络异常: {exc.message}")
            return AuthCodeVerifyResult(False, False, f"授权码验证失败: {exc.message}")
        except Exception as exc:
            logger.warning(f"[AuthCodeService] 验证授权码失败: {exc}")
            return AuthCodeVerifyResult(False, False, f"授权码验证失败: {exc}")

    def validate_stored_auth_code(self) -> AuthCodeVerifyResult:
        auth_code = self.get_stored_auth_code()
        if not auth_code:
            return AuthCodeVerifyResult(success=True, is_valid=False, message="暂无授权码")

        result = self.verify_auth_code(auth_code)
        if result.success and not result.is_valid:
            self.clear_auth_code()
        return result

    def open_get_auth_code_page(self, auth_code_url: str = DEFAULT_AUTH_CODE_URL) -> str:
        url = build_auth_code_url(
            auth_code_url or DEFAULT_AUTH_CODE_URL,
            device_id=self.get_device_id(),
            soft_number=self.soft_number,
        )
        self._opener(url)
        logger.info("[AuthCodeService] 已打开授权码获取页面")
        return url
