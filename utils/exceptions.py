# -*- coding: utf-8 -*-
"""
统一异常处理系统 - 定义所有应该使用的异常类
"""


class VideoProcessException(Exception):
    """视频处理异常基类"""
    
    def __init__(self, message, error_code=None, details=None):
        self.message = message
        self.error_code = error_code or 'UNKNOWN_ERROR'
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self):
        """转换为字典"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }


class ValidationException(VideoProcessException):
    """验证异常"""
    
    def __init__(self, message, field=None, value=None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = value
        
        super().__init__(message, 'VALIDATION_ERROR', details)


class ProcessorException(VideoProcessException):
    """处理器异常"""
    
    def __init__(self, message, processor_name=None, processor_step=None):
        details = {}
        if processor_name:
            details['processor'] = processor_name
        if processor_step:
            details['step'] = processor_step
        
        super().__init__(message, 'PROCESSOR_ERROR', details)


class IOException(VideoProcessException):
    """IO异常"""
    
    def __init__(self, message, file_path=None, operation=None):
        details = {}
        if file_path:
            details['file_path'] = file_path
        if operation:
            details['operation'] = operation
        
        super().__init__(message, 'IO_ERROR', details)


class ConfigException(VideoProcessException):
    """配置异常"""
    
    def __init__(self, message, config_key=None):
        details = {}
        if config_key:
            details['config_key'] = config_key
        
        super().__init__(message, 'CONFIG_ERROR', details)


class ResourceException(VideoProcessException):
    """资源异常"""

    def __init__(self, message, resource_type=None, resource_name=None):
        details = {}
        if resource_type:
            details['resource_type'] = resource_type
        if resource_name:
            details['resource_name'] = resource_name

        super().__init__(message, 'RESOURCE_ERROR', details)


class NetworkException(VideoProcessException):
    """网络请求异常"""

    # 错误类型枚举
    ERROR_TIMEOUT = 'TIMEOUT'
    ERROR_CONNECTION = 'CONNECTION'
    ERROR_HTTP = 'HTTP'
    ERROR_UNKNOWN = 'UNKNOWN'

    def __init__(
        self,
        message: str,
        error_type: str = ERROR_UNKNOWN,
        url: str = None,
        status_code: int = None,
        retry_count: int = 0,
        max_retries: int = 0
    ):
        details = {
            'error_type': error_type,
            'url': url,
            'status_code': status_code,
            'retry_count': retry_count,
            'max_retries': max_retries,
        }
        error_code = f'NETWORK_{error_type}'
        super().__init__(message, error_code, details)

    @property
    def is_retryable(self) -> bool:
        """判断是否可重试"""
        return self.details.get('error_type') in (self.ERROR_TIMEOUT, self.ERROR_CONNECTION)


class VideoCodecException(VideoProcessException):
    """视频编码不支持异常"""

    def __init__(
        self,
        message: str,
        codec_name: str = None,
        codec_type: str = None,  # video/audio
        suggestions: list = None
    ):
        details = {
            'codec_name': codec_name,
            'codec_type': codec_type,
            'suggestions': suggestions or [],
        }
        super().__init__(message, 'VIDEO_CODEC_UNSUPPORTED', details)
