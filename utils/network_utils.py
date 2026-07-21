# -*- coding: utf-8 -*-
"""
网络请求工具 - 带重试机制的 HTTP 请求封装
"""

import time
import requests
from typing import Optional, Dict, Any, Callable
from urllib.parse import urljoin

from utils.exceptions import NetworkException
from utils.unified_logger import logger


# 默认重试配置
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # 初始重试间隔（秒）
DEFAULT_BACKOFF_FACTOR = 2.0  # 指数退避因子
DEFAULT_TIMEOUT = 10  # 默认超时时间（秒）


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_delay: float = DEFAULT_RETRY_DELAY,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        timeout: int = DEFAULT_TIMEOUT,
        retry_on_timeout: bool = True,
        retry_on_connection_error: bool = True,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.retry_on_timeout = retry_on_timeout
        self.retry_on_connection_error = retry_on_connection_error


def _classify_error(exception: Exception) -> str:
    """分类错误类型"""
    error_str = str(exception).lower()

    if isinstance(exception, requests.Timeout):
        return NetworkException.ERROR_TIMEOUT
    elif isinstance(exception, requests.ConnectionError):
        return NetworkException.ERROR_CONNECTION
    elif isinstance(exception, requests.HTTPError):
        return NetworkException.ERROR_HTTP
    elif 'timeout' in error_str:
        return NetworkException.ERROR_TIMEOUT
    elif 'connection' in error_str:
        return NetworkException.ERROR_CONNECTION
    else:
        return NetworkException.ERROR_UNKNOWN


def _is_retryable(exception: Exception, config: RetryConfig) -> bool:
    """判断异常是否可重试"""
    if isinstance(exception, requests.Timeout):
        return config.retry_on_timeout
    elif isinstance(exception, requests.ConnectionError):
        return config.retry_on_connection_error
    elif isinstance(exception, requests.HTTPError):
        # 4xx 错误通常不可重试，5xx 可以
        if exception.response is not None:
            return 500 <= exception.response.status_code < 600
        return False
    return False


def _get_status_code(exception: Exception) -> Optional[int]:
    """获取 HTTP 状态码"""
    if isinstance(exception, requests.HTTPError):
        if exception.response is not None:
            return exception.response.status_code
    return None


def request_with_retry(
    method: str,
    url: str,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> requests.Response:
    """
    带重试机制的 HTTP 请求

    Args:
        method: HTTP 方法 (GET, POST, etc.)
        url: 请求 URL
        config: 重试配置，如果为 None 则使用默认配置
        **kwargs: 传递给 requests 的其他参数

    Returns:
        requests.Response: 响应对象

    Raises:
        NetworkException: 网络请求失败（所有重试都失败后）
    """
    if config is None:
        config = RetryConfig()

    # 设置默认超时
    if 'timeout' not in kwargs:
        kwargs['timeout'] = config.timeout

    last_exception: Optional[Exception] = None
    error_type = NetworkException.ERROR_UNKNOWN

    for attempt in range(config.max_retries + 1):
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        except Exception as e:
            last_exception = e
            error_type = _classify_error(e)

            # 记录错误
            status_code = _get_status_code(e)
            if attempt < config.max_retries and _is_retryable(e, config):
                # 计算延迟（指数退避）
                delay = config.retry_delay * (config.backoff_factor ** attempt)
                logger.warning(
                    f"[Network] 请求失败 (尝试 {attempt + 1}/{config.max_retries + 1}), "
                    f"错误类型: {error_type}, 状态码: {status_code}, "
                    f"{config.retry_delay:.1f}秒后重试... URL: {url}"
                )
                time.sleep(delay)
            else:
                # 不可重试或已达最大重试次数
                if isinstance(e, requests.HTTPError):
                    logger.error(
                        f"[Network] HTTP请求失败: {error_type}, 状态码: {status_code}, URL: {url}"
                    )
                else:
                    logger.error(
                        f"[Network] 网络请求失败: {error_type}, 错误: {e}, URL: {url}"
                    )
                break

    # 所有重试都失败，抛出自定义异常
    raise NetworkException(
        message=f"请求失败 (已重试{config.max_retries}次): {last_exception}",
        error_type=error_type,
        url=url,
        status_code=_get_status_code(last_exception) if last_exception else None,
        retry_count=config.max_retries,
        max_retries=config.max_retries
    )


def get(url: str, config: Optional[RetryConfig] = None, **kwargs) -> requests.Response:
    """GET 请求（带重试）"""
    return request_with_retry('GET', url, config, **kwargs)


def post(url: str, config: Optional[RetryConfig] = None, **kwargs) -> requests.Response:
    """POST 请求（带重试）"""
    return request_with_retry('POST', url, config, **kwargs)


def put(url: str, config: Optional[RetryConfig] = None, **kwargs) -> requests.Response:
    """PUT 请求（带重试）"""
    return request_with_retry('PUT', url, config, **kwargs)


def delete(url: str, config: Optional[RetryConfig] = None, **kwargs) -> requests.Response:
    """DELETE 请求（带重试）"""
    return request_with_retry('DELETE', url, config, **kwargs)


# 便捷配置
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    retry_delay=1.0,
    backoff_factor=2.0,
    timeout=10,
)

SLOW_RETRY_CONFIG = RetryConfig(
    max_retries=5,
    retry_delay=2.0,
    backoff_factor=2.0,
    timeout=30,
)
