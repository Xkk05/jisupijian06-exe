"""
用户登录认证服务
支持网页端同步登录、Token 管理、用户信息获取、退出登录
"""

import os
import json
import uuid
import time
import hmac
import hashlib
import base64
import webbrowser
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, QObject

from utils.app_data_paths import get_user_data_dir
from utils.unified_logger import logger
from utils.exceptions import NetworkException
from utils.network_utils import (
    post as network_post,
    get as network_get,
    DEFAULT_RETRY_CONFIG,
)

# API 基础地址
API_BASE_URL = "https://api-web.kunqiongai.com"

# 客户端与服务端约定的密钥
SECRET_KEY = b"7530bfb1ad6c41627b0f0620078fa5ed"


def _get_token_file_path() -> str:
    """获取 Token 持久化文件路径"""
    return str(get_user_data_dir() / "auth_token.json")


@dataclass
class UserInfo:
    """用户信息"""
    avatar: str = ""
    nickname: str = ""


class TokenPollWorker(QThread):
    """轮询获取 Token 的工作线程"""
    token_received = pyqtSignal(str)  # token
    poll_failed = pyqtSignal(str)     # error message
    poll_timeout = pyqtSignal()

    def __init__(self, encoded_nonce: str, timeout: int = 300, parent=None):
        super().__init__(parent)
        self.encoded_nonce = encoded_nonce
        self.timeout = timeout
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        start_time = time.time()
        poll_url = f"{API_BASE_URL}/user/desktop_get_token"

        while time.time() - start_time < self.timeout and not self._stop:
            try:
                response = network_post(
                    poll_url,
                    params={
                        "client_type": "desktop",
                        "client_nonce": self.encoded_nonce,
                    },
                    timeout=5,
                )
                result = response.json()

                if result.get("code") == 1:
                    token = result["data"]["token"]
                    logger.info("[AuthService] 轮询获取 Token 成功")
                    self.token_received.emit(token)
                    return
                else:
                    # 尚未登录，继续轮询
                    time.sleep(2)
            except NetworkException as e:
                logger.debug(f"[AuthService] 轮询网络异常: {e.message}")
                time.sleep(2)
            except Exception as e:
                logger.debug(f"[AuthService] 轮询中: {e}")
                time.sleep(2)

        if not self._stop:
            logger.warning("[AuthService] 轮询超时")
            self.poll_timeout.emit()


class UserInfoWorker(QThread):
    """后台检查登录并获取用户信息。"""

    success = pyqtSignal(object)   # UserInfo
    invalid = pyqtSignal(str)      # invalid reason
    failed = pyqtSignal(str)

    def __init__(self, token: str, check_first: bool = True, parent=None):
        super().__init__(parent)
        self._token = token
        self._check_first = check_first

    def run(self):
        try:
            if self._check_first:
                check_resp = network_post(
                    f"{API_BASE_URL}/user/check_login",
                    data={"token": self._token},
                    timeout=8,
                )
                check_data = check_resp.json()
                if check_data.get("code") != 1:
                    self.invalid.emit(check_data.get("msg", "token 无效"))
                    return

            user_resp = network_post(
                f"{API_BASE_URL}/soft_desktop/get_user_info",
                headers={"token": self._token},
                timeout=10,
            )
            user_data = user_resp.json()
            if user_data.get("code") != 1:
                self.invalid.emit(user_data.get("msg", "获取用户信息失败"))
                return

            ui = user_data["data"]["user_info"]
            self.success.emit(
                UserInfo(
                    avatar=ui.get("avatar", ""),
                    nickname=ui.get("nickname", ""),
                )
            )
        except NetworkException as exc:
            logger.error(f"[AuthService] 获取用户信息网络异常: {exc.message}")
            self.failed.emit(f"网络请求失败: {exc.message}")
        except Exception as exc:
            self.failed.emit(str(exc))


class AuthService(QObject):
    """认证服务 - 管理登录、用户信息、退出登录"""

    # 信号
    login_success = pyqtSignal(object)   # UserInfo
    login_failed = pyqtSignal(str)       # error message
    login_timeout = pyqtSignal()
    logout_done = pyqtSignal()
    user_info_updated = pyqtSignal(object)  # UserInfo

    def __init__(self, parent=None):
        super().__init__(parent)
        self._token: Optional[str] = None
        self._user_info: Optional[UserInfo] = None
        self._poll_worker: Optional[TokenPollWorker] = None
        self._user_worker: Optional[UserInfoWorker] = None
        self._load_token()

    @property
    def is_logged_in(self) -> bool:
        return self._token is not None

    @property
    def token(self) -> Optional[str]:
        return self._token

    @property
    def user_info(self) -> Optional[UserInfo]:
        return self._user_info

    # =================== Token 持久化 ===================

    def _load_token(self):
        """从本地文件加载 Token"""
        try:
            path = _get_token_file_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._token = data.get("token")
                user_data = data.get("user_info") or {}
                if user_data.get("nickname") or user_data.get("avatar"):
                    self._user_info = UserInfo(
                        avatar=user_data.get("avatar", ""),
                        nickname=user_data.get("nickname", ""),
                    )
                logger.info("[AuthService] 本地 Token 已加载")
        except Exception as e:
            logger.warning(f"[AuthService] 加载本地 Token 失败: {e}")

    def _save_token(self):
        """保存 Token 到本地文件"""
        try:
            path = _get_token_file_path()
            with open(path, "w", encoding="utf-8") as f:
                payload = {"token": self._token}
                if self._user_info:
                    payload["user_info"] = {
                        "avatar": self._user_info.avatar,
                        "nickname": self._user_info.nickname,
                    }
                json.dump(payload, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[AuthService] 保存 Token 失败: {e}")

    def _clear_token(self):
        """清除本地 Token"""
        self._token = None
        self._user_info = None
        try:
            path = _get_token_file_path()
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    # =================== 签名 Nonce ===================

    @staticmethod
    def _generate_signed_nonce() -> dict:
        """生成带签名的临时会话 ID"""
        nonce = str(uuid.uuid4()).replace("-", "")
        timestamp = int(time.time())
        message = f"{nonce}|{timestamp}".encode("utf-8")
        hmac_obj = hmac.new(SECRET_KEY, message, hashlib.sha256)
        signature = base64.b64encode(hmac_obj.digest()).decode("utf-8")
        return {"nonce": nonce, "timestamp": timestamp, "signature": signature}

    @staticmethod
    def _encode_signed_nonce(signed_nonce: dict) -> str:
        """将签名 nonce 编码为 URL 安全字符串"""
        json_str = json.dumps(signed_nonce, separators=(",", ":"))
        url_safe = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")
        url_safe = url_safe.replace("+", "-").replace("/", "_").rstrip("=")
        return url_safe

    # =================== 登录流程 ===================

    def start_login(self):
        """启动完整登录流程：获取登录 URL -> 打开浏览器 -> 轮询 Token"""
        try:
            # 1. 获取网页端登录地址
            resp = network_post(
                f"{API_BASE_URL}/soft_desktop/get_web_login_url",
                timeout=10,
            )
            result = resp.json()
            if result.get("code") != 1:
                self.login_failed.emit(f"获取登录地址失败: {result.get('msg', '未知错误')}")
                return
            web_login_url = result["data"]["login_url"]

            # 2. 生成签名 nonce
            signed_nonce = self._generate_signed_nonce()
            encoded_nonce = self._encode_signed_nonce(signed_nonce)

            # 3. 启动轮询线程
            if self._poll_worker and self._poll_worker.isRunning():
                self._poll_worker.stop()
                self._poll_worker.wait()

            self._poll_worker = TokenPollWorker(encoded_nonce, timeout=300, parent=self)
            self._poll_worker.token_received.connect(self._on_token_received)
            self._poll_worker.poll_failed.connect(self._on_poll_failed)
            self._poll_worker.poll_timeout.connect(self._on_poll_timeout)
            self._poll_worker.start()

            # 4. 打开浏览器
            login_url = f"{web_login_url}?client_type=desktop&client_nonce={encoded_nonce}"
            webbrowser.open(login_url)
            logger.info(f"[AuthService] 已打开登录页面")

        except Exception as e:
            logger.error(f"[AuthService] 启动登录失败: {e}")
            self.login_failed.emit(str(e))

    def _on_token_received(self, token: str):
        """Token 获取成功"""
        self._token = token
        self._save_token()
        self.fetch_user_info_async(check_login=False)

    def _on_poll_failed(self, error: str):
        self.login_failed.emit(error)

    def _on_poll_timeout(self):
        self.login_timeout.emit()

    # =================== 用户信息 ===================

    def _start_user_worker(self, check_login: bool):
        if not self._token:
            return
        if self._user_worker and self._user_worker.isRunning():
            return
        self._user_worker = UserInfoWorker(self._token, check_first=check_login, parent=self)
        self._user_worker.success.connect(self._on_user_info_success)
        self._user_worker.invalid.connect(self._on_user_info_invalid)
        self._user_worker.failed.connect(self._on_user_info_failed)
        self._user_worker.start()

    def fetch_user_info_async(self, check_login: bool = False):
        """异步获取用户信息。"""
        self._start_user_worker(check_login=check_login)

    def fetch_user_info(self):
        """兼容旧调用：同步接口改为异步。"""
        self.fetch_user_info_async(check_login=False)

    def _on_user_info_success(self, user_info: UserInfo):
        self._user_info = user_info
        self._save_token()
        logger.info(f"[AuthService] 用户信息: {self._user_info.nickname}")
        self.login_success.emit(self._user_info)
        self.user_info_updated.emit(self._user_info)

    def _on_user_info_invalid(self, message: str):
        logger.info(f"[AuthService] 登录态失效: {message}")
        self._clear_token()
        self.login_failed.emit(message)

    def _on_user_info_failed(self, error: str):
        logger.warning(f"[AuthService] 获取用户信息失败: {error}")
        self.login_failed.emit(error)

    # =================== 检查登录状态 ===================

    def check_login(self):
        """检查当前 Token 是否有效，有效则获取用户信息"""
        if not self._token:
            return False
        try:
            resp = network_post(
                f"{API_BASE_URL}/user/check_login",
                data={"token": self._token},
                timeout=10,
            )
            result = resp.json()
            if result.get("code") == 1:
                logger.info("[AuthService] Token 有效，已登录")
                self.fetch_user_info_async(check_login=False)
                return True
            else:
                logger.info("[AuthService] Token 已失效")
                self._clear_token()
                return False
        except NetworkException as e:
            logger.warning(f"[AuthService] 检查登录失败（网络异常）: {e.message}")
            return False
        except Exception as e:
            logger.warning(f"[AuthService] 检查登录失败: {e}")
            return False

    def check_login_async(self):
        """异步检查 Token 有效性并刷新用户信息。"""
        if not self._token:
            return
        self._start_user_worker(check_login=True)

    # =================== 退出登录 ===================

    def logout(self):
        """退出登录"""
        if self._token:
            try:
                network_post(
                    f"{API_BASE_URL}/logout",
                    headers={"token": self._token},
                    timeout=5,
                )
            except NetworkException as e:
                logger.warning(f"[AuthService] 退出登录请求失败: {e.message}")
            except Exception as e:
                logger.warning(f"[AuthService] 退出登录请求失败: {e}")
        self._clear_token()
        self.logout_done.emit()
        logger.info("[AuthService] 已退出登录")

    def cancel_login(self):
        """取消正在进行的登录轮询"""
        if self._poll_worker and self._poll_worker.isRunning():
            self._poll_worker.stop()
            self._poll_worker.wait()
        # 用户信息刷新线程是短任务，这里不强制终止，避免资源状态不一致
