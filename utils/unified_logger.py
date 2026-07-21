# -*- coding: utf-8 -*-
"""
统一日志系统 - UnifiedLogger
所有模块都应该使用这个日志系统
"""

import logging
import os
import sys
import tempfile
import threading
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional


class UnifiedLogger:
    """统一的日志记录系统"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.logger = logging.getLogger('VideoMate')
        self._initialized = True

    def _parse_level(self, level_name: str, fallback: int) -> int:
        if not level_name:
            return fallback
        return getattr(logging, level_name.upper(), fallback)

    def _clear_handlers(self):
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
            handler.close()

    def init(
        self,
        base_dir: Path,
        enable_logging: bool = True,
        log_level: str = "INFO",
        log_retention_days: int = 30,
        console_level: Optional[str] = None,
        log_dir: Optional[Path] = None,
    ):
        """初始化日志输出（按天滚动）"""
        self.logger.setLevel(logging.DEBUG)
        self._clear_handlers()

        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        if enable_logging:
            target_log_dir = log_dir or (base_dir / 'logs')
            log_dirs = [target_log_dir, get_log_dir(base_dir), Path(tempfile.gettempdir()) / "batch-video" / "logs"]
            file_handlers_added = False

            for candidate_dir in log_dirs:
                try:
                    candidate_dir.mkdir(parents=True, exist_ok=True)

                    file_handler = TimedRotatingFileHandler(
                        candidate_dir / 'processing.log',
                        when='midnight',
                        backupCount=log_retention_days,
                        encoding='utf-8'
                    )
                    file_handler.setLevel(self._parse_level(log_level, logging.INFO))
                    file_handler.setFormatter(formatter)
                    self.logger.addHandler(file_handler)

                    error_handler = TimedRotatingFileHandler(
                        candidate_dir / 'error.log',
                        when='midnight',
                        backupCount=log_retention_days,
                        encoding='utf-8'
                    )
                    error_handler.setLevel(logging.ERROR)
                    error_handler.setFormatter(formatter)
                    self.logger.addHandler(error_handler)

                    file_handlers_added = True
                    break
                except Exception:
                    for handler in list(self.logger.handlers):
                        self.logger.removeHandler(handler)
                        handler.close()

            if not file_handlers_added:
                enable_logging = False

        console_handler = logging.StreamHandler()
        console_handler.setLevel(self._parse_level(console_level or log_level, logging.INFO))
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        self.logger.propagate = False
        self._initialized = True
    
    def debug(self, message, *args, **kwargs):
        """调试日志"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        """信息日志"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """警告日志"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        """错误日志"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        """严重错误日志"""
        self.logger.critical(message, *args, **kwargs)


# stdout/stderr 重定向辅助
class _NullStream:
    def write(self, _data):
        return 0

    def flush(self):
        return None

    def isatty(self):
        return False


class TeeStream:
    """同时写入原始流与日志（按行记录）"""

    def __init__(self, original_stream, log_func):
        self._original_stream = original_stream or _NullStream()
        self._log_func = log_func
        self._buffer = ""
        self._lock = threading.Lock()
        self._local = threading.local()

    @property
    def encoding(self):
        return getattr(self._original_stream, "encoding", "utf-8")

    def write(self, data):
        if data is None:
            return 0
        if isinstance(data, bytes):
            try:
                text = data.decode(self.encoding or "utf-8", errors="replace")
            except Exception:
                text = data.decode("utf-8", errors="replace")
        else:
            text = str(data)

        with self._lock:
            self._original_stream.write(text)
            self._original_stream.flush()

            if getattr(self._local, "in_log", False):
                return len(text)

            self._local.in_log = True
            try:
                self._buffer += text
                while True:
                    if "\n" not in self._buffer:
                        break
                    line, self._buffer = self._buffer.split("\n", 1)
                    line = line.rstrip("\r")
                    if line.strip():
                        try:
                            self._log_func(line)
                        except Exception:
                            _write_raw_logging_error(line)
            finally:
                self._local.in_log = False
        return len(text)

    def flush(self):
        with self._lock:
            self._original_stream.flush()
            if self._buffer.strip():
                try:
                    self._log_func(self._buffer.rstrip("\r"))
                except Exception:
                    _write_raw_logging_error(self._buffer.rstrip("\r"))
            self._buffer = ""

    def isatty(self):
        return getattr(self._original_stream, "isatty", lambda: False)()


_std_streams = {"stdout": None, "stderr": None}


def redirect_std_streams(enable: bool = True, enable_stdout: bool = True, enable_stderr: bool = True):
    """启用/禁用 stdout/stderr 重定向到日志"""
    global _std_streams
    if enable:
        if enable_stdout:
            if _std_streams["stdout"] is None:
                _std_streams["stdout"] = sys.stdout or getattr(sys, "__stdout__", None)
            sys.stdout = TeeStream(_std_streams["stdout"], logger.info)
        if enable_stderr:
            if _std_streams["stderr"] is None:
                _std_streams["stderr"] = sys.stderr or getattr(sys, "__stderr__", None)
            sys.stderr = TeeStream(_std_streams["stderr"], logger.error)
    else:
        if _std_streams["stdout"] is not None:
            sys.stdout = _std_streams["stdout"]
        if _std_streams["stderr"] is not None:
            sys.stderr = _std_streams["stderr"]


def _write_raw_logging_error(message: str):
    try:
        log_dir = get_log_dir(Path.cwd())
        log_dir.mkdir(parents=True, exist_ok=True)
        error_file = log_dir / "logging_error.txt"
        with open(error_file, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass


# 创建全局日志实例
logger = UnifiedLogger()


def get_log_dir(base_dir: Path) -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "batch-video" / "logs"
    return Path(tempfile.gettempdir()) / "batch-video" / "logs"


def init_logger(base_dir: Path, settings: Optional[object] = None) -> UnifiedLogger:
    """按配置初始化统一日志"""
    enable_logging = True
    log_level = "INFO"
    log_retention_days = 30

    if settings is not None:
        enable_logging = getattr(settings, "enable_logging", enable_logging)
        log_level = getattr(settings, "log_level", log_level)
        log_retention_days = getattr(settings, "log_retention_days", log_retention_days)

    logger.init(
        base_dir=base_dir,
        enable_logging=enable_logging,
        log_level=log_level,
        log_retention_days=log_retention_days,
        log_dir=get_log_dir(base_dir),
    )
    return logger
