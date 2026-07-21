# -*- coding: utf-8 -*-
"""
异常处理系统单元测试
"""
import pytest


class TestVideoProcessException:
    """视频处理异常基类测试"""
    
    def test_default_error_code(self):
        """测试默认错误码"""
        from utils.exceptions import VideoProcessException
        
        exc = VideoProcessException("Something went wrong")
        
        assert exc.message == "Something went wrong"
        assert exc.error_code == "UNKNOWN_ERROR"
        assert exc.details == {}
        assert str(exc) == "Something went wrong"

    def test_custom_error_code(self):
        """测试自定义错误码"""
        from utils.exceptions import VideoProcessException
        
        exc = VideoProcessException(
            "Custom error",
            error_code="CUSTOM_ERROR",
            details={"key": "value"}
        )
        
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == {"key": "value"}

    def test_to_dict(self):
        """测试转换为字典"""
        from utils.exceptions import VideoProcessException
        
        exc = VideoProcessException(
            "Test error",
            error_code="TEST_ERROR",
            details={"field": "test"}
        )
        
        result = exc.to_dict()
        
        assert result == {
            "error_code": "TEST_ERROR",
            "message": "Test error",
            "details": {"field": "test"}
        }

    def test_inheritance(self):
        """测试继承自Exception"""
        from utils.exceptions import VideoProcessException
        
        exc = VideoProcessException("Test")
        
        assert isinstance(exc, Exception)


class TestValidationException:
    """验证异常测试"""
    
    def test_default_validation_error(self):
        """测试默认验证错误"""
        from utils.exceptions import ValidationException
        
        exc = ValidationException("Invalid value")
        
        assert exc.message == "Invalid value"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details == {}

    def test_with_field_and_value(self):
        """测试带字段和值"""
        from utils.exceptions import ValidationException
        
        exc = ValidationException(
            "Value out of range",
            field="age",
            value=-5
        )
        
        assert exc.details == {
            "field": "age",
            "value": -5
        }

    def test_with_field_only(self):
        """测试仅带字段"""
        from utils.exceptions import ValidationException
        
        exc = ValidationException("Missing field", field="username")
        
        assert exc.details == {"field": "username"}

    def test_inheritance(self):
        """测试继承关系"""
        from utils.exceptions import ValidationException, VideoProcessException
        
        exc = ValidationException("Test")
        
        assert isinstance(exc, VideoProcessException)


class TestProcessorException:
    """处理器异常测试"""
    
    def test_default_processor_error(self):
        """测试默认处理器错误"""
        from utils.exceptions import ProcessorException
        
        exc = ProcessorException("Processing failed")
        
        assert exc.message == "Processing failed"
        assert exc.error_code == "PROCESSOR_ERROR"
        assert exc.details == {}

    def test_with_processor_info(self):
        """测试带处理器信息"""
        from utils.exceptions import ProcessorException
        
        exc = ProcessorException(
            "Encoder error",
            processor_name="VideoEncoder",
            processor_step="encoding"
        )
        
        assert exc.details == {
            "processor": "VideoEncoder",
            "step": "encoding"
        }

    def test_inheritance(self):
        """测试继承关系"""
        from utils.exceptions import ProcessorException, VideoProcessException
        
        exc = ProcessorException("Test")
        
        assert isinstance(exc, VideoProcessException)


class TestIOException:
    """IO异常测试"""
    
    def test_default_io_error(self):
        """测试默认IO错误"""
        from utils.exceptions import IOException
        
        exc = IOException("File error")
        
        assert exc.message == "File error"
        assert exc.error_code == "IO_ERROR"
        assert exc.details == {}

    def test_with_file_info(self):
        """测试带文件信息"""
        from utils.exceptions import IOException
        
        exc = IOException(
            "Cannot read file",
            file_path="/path/to/file.mp4",
            operation="read"
        )
        
        assert exc.details == {
            "file_path": "/path/to/file.mp4",
            "operation": "read"
        }

    def test_inheritance(self):
        """测试继承关系"""
        from utils.exceptions import IOException, VideoProcessException
        
        exc = IOException("Test")
        
        assert isinstance(exc, VideoProcessException)


class TestConfigException:
    """配置异常测试"""
    
    def test_default_config_error(self):
        """测试默认配置错误"""
        from utils.exceptions import ConfigException
        
        exc = ConfigException("Config error")
        
        assert exc.message == "Config error"
        assert exc.error_code == "CONFIG_ERROR"
        assert exc.details == {}

    def test_with_config_key(self):
        """测试带配置键"""
        from utils.exceptions import ConfigException
        
        exc = ConfigException("Invalid value", config_key="video.codec")
        
        assert exc.details == {"config_key": "video.codec"}

    def test_inheritance(self):
        """测试继承关系"""
        from utils.exceptions import ConfigException, VideoProcessException
        
        exc = ConfigException("Test")
        
        assert isinstance(exc, VideoProcessException)


class TestResourceException:
    """资源异常测试"""
    
    def test_default_resource_error(self):
        """测试默认资源错误"""
        from utils.exceptions import ResourceException
        
        exc = ResourceException("Resource not found")
        
        assert exc.message == "Resource not found"
        assert exc.error_code == "RESOURCE_ERROR"
        assert exc.details == {}

    def test_with_resource_info(self):
        """测试带资源信息"""
        from utils.exceptions import ResourceException
        
        exc = ResourceException(
            "Model not found",
            resource_type="ai_model",
            resource_name="whisper-large"
        )
        
        assert exc.details == {
            "resource_type": "ai_model",
            "resource_name": "whisper-large"
        }

    def test_inheritance(self):
        """测试继承关系"""
        from utils.exceptions import ResourceException, VideoProcessException
        
        exc = ResourceException("Test")
        
        assert isinstance(exc, VideoProcessException)


class TestExceptionUsage:
    """异常使用场景测试"""
    
    def test_catch_base_exception(self):
        """测试捕获基类异常"""
        from utils.exceptions import VideoProcessException

        caught = []
        try:
            raise VideoProcessException("Base error")
        except VideoProcessException as e:
            caught.append(type(e).__name__)

        assert len(caught) == 1
        assert caught[0] == "VideoProcessException"

        with pytest.raises(Exception, match="Other error"):
            try:
                raise Exception("Other error")
            except VideoProcessException:
                pytest.fail("普通异常不应被 VideoProcessException 捕获")

    def test_exception_chaining(self):
        """测试异常链"""
        from utils.exceptions import ProcessorException, ValidationException
        
        try:
            try:
                raise ValidationException("Invalid input", field="duration")
            except ValidationException as e:
                raise ProcessorException("Processing failed") from e
        except ProcessorException as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ValidationException)

    def test_exception_in_function(self):
        """测试函数中的异常"""
        from utils.exceptions import ValidationException
        
        def validate_positive(value):
            if value <= 0:
                raise ValidationException(
                    "Value must be positive",
                    field="value",
                    value=value
                )
            return True
        
        assert validate_positive(5) is True
        
        with pytest.raises(ValidationException) as exc_info:
            validate_positive(-1)
        
        assert exc_info.value.details["value"] == -1
        assert exc_info.value.details["field"] == "value"
