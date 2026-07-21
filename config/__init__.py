"""配置模块"""
from types import SimpleNamespace

# 兼容：api_config 在部分版本中已移除，避免导入 config.* 时直接失败
try:
    from .api_config import (
        ConfigManager as APIConfigManager,
        APIConfig,
        AliyunConfig,
        TencentConfig,
        BaiduConfig,
        OpenAIConfig,
        GoogleConfig,
        BarkConfig,
        get_config_manager as get_api_config_manager,
    )
except ImportError:
    APIConfigManager = SimpleNamespace
    APIConfig = SimpleNamespace
    AliyunConfig = SimpleNamespace
    TencentConfig = SimpleNamespace
    BaiduConfig = SimpleNamespace
    OpenAIConfig = SimpleNamespace
    GoogleConfig = SimpleNamespace
    BarkConfig = SimpleNamespace

    def get_api_config_manager():
        raise RuntimeError("api_config 模块不存在，相关 API 配置能力不可用")

from .config_manager import (
    ConfigManager,
    UIConfig,
    VideoProcessConfig,
    AudioConfig,
    ExportConfig,
    AdvancedConfig,
    get_config_manager,
    init_config_manager,
)

from .detailed_settings import DetailedSettings

# 为了兼容旧代码，创建配置类别名
WatermarkConfig = SimpleNamespace
CropConfig = SimpleNamespace
TrimConfig = SimpleNamespace
SpeedConfig = SimpleNamespace
TextConfig = SimpleNamespace
AudioPanelConfig = SimpleNamespace
ImageAdjustConfig = SimpleNamespace
OutputConfig = SimpleNamespace
AIConfig = SimpleNamespace

__all__ = [
    # API配置
    'APIConfigManager',
    'APIConfig',
    'AliyunConfig',
    'TencentConfig',
    'BaiduConfig',
    'OpenAIConfig',
    'GoogleConfig',
    'BarkConfig',
    'get_api_config_manager',
    # 通用配置
    'ConfigManager',
    'UIConfig',
    'VideoProcessConfig',
    'AudioConfig',
    'AIConfig',
    'ExportConfig',
    'AdvancedConfig',
    'get_config_manager',
    'init_config_manager',
    # 详细设置
    'DetailedSettings',
    # 兼容别名
    'WatermarkConfig',
    'CropConfig',
    'TrimConfig',
    'SpeedConfig',
    'TextConfig',
    'AudioPanelConfig',
    'ImageAdjustConfig',
    'OutputConfig',
]
