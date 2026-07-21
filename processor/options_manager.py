"""
Options.ini 配置管理器
处理扩展功能的配置
"""
import configparser
import logging
import os
import shutil
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import config.config_manager as config_manager

logger = logging.getLogger(__name__)


class OptionsConfigManager:
    @staticmethod
    def _normalize_language_code(language: str) -> str:
        raw = (language or "zh_CN").strip()
        if raw.lower() in {"en_us", "en-us", "english_us"}:
            return "en"
        return raw

    """Options.ini 配置管理器"""
    
    def __init__(
        self,
        config_file: str = "config/options.ini",
        user_config_dir: Optional[Path] = None,
    ):
        user_config_dir = (
            Path(user_config_dir) if user_config_dir else config_manager.get_user_config_dir()
        )
        user_config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = user_config_dir / "options.ini"
        self.template_config_file = self._resolve_template_config(Path(config_file))

        if not self.config_file.exists():
            root_config = Path("options.ini")
            if root_config.exists():
                self.template_config_file = root_config
            if self.template_config_file and self.template_config_file.exists():
                try:
                    shutil.copyfile(self.template_config_file, self.config_file)
                    logger.info(f"已复制模板配置到用户目录: {self.config_file}")
                except Exception as e:
                    logger.warning(f"复制模板配置失败: {e}")
        
        self.config = configparser.ConfigParser()
        self._load_config()

    def _resolve_template_config(self, config_file: Path) -> Optional[Path]:
        if hasattr(sys, "_MEIPASS"):
            base_dir = Path(sys._MEIPASS)
        else:
            base_dir = Path(__file__).resolve().parents[1]
        candidate = base_dir / config_file
        return candidate if candidate.exists() else None
    
    def _load_config(self):
        """加载配置文件"""
        if self.config_file.exists():
            try:
                self.config.read(self.config_file, encoding='utf-8')
                logger.info(f"已加载配置文件: {self.config_file}")
            except Exception as e:
                logger.error(f"加载配置文件失败: {e}")
        elif self.template_config_file and self.template_config_file.exists():
            try:
                self.config.read(self.template_config_file, encoding='utf-8')
                logger.info(f"已加载模板配置文件: {self.template_config_file}")
            except Exception as e:
                logger.error(f"加载模板配置文件失败: {e}")
        else:
            logger.warning(f"配置文件不存在: {self.config_file}")
    
    def save_config(self):
        """保存配置文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            logger.info(f"已保存配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    # ==================== Fission 裂变配置 ====================
    
    def is_fission_enabled(self) -> bool:
        """检查裂变功能是否启用"""
        return self.config.getboolean('Fission', 'FissionFolder', fallback=False)
    
    def get_fission_count(self) -> int:
        """获取裂变生成版本数"""
        return self.config.getint('Fission', 'FissionCount', fallback=2)
    
    def set_fission_enabled(self, enabled: bool):
        """设置裂变功能"""
        if not self.config.has_section('Fission'):
            self.config.add_section('Fission')
        self.config.set('Fission', 'FissionFolder', str(enabled))
    
    def set_fission_count(self, count: int):
        """设置裂变版本数"""
        if not self.config.has_section('Fission'):
            self.config.add_section('Fission')
        self.config.set('Fission', 'FissionCount', str(count))
    
    # ==================== Speed Length 变速自适应配置 ====================
    
    def is_speed_length_enabled(self) -> bool:
        """检查变速自适应是否启用"""
        return self.config.getboolean('SpeedProcessing', 'SpeedLength', fallback=True)
    
    def set_speed_length_enabled(self, enabled: bool):
        """设置变速自适应"""
        if not self.config.has_section('SpeedProcessing'):
            self.config.add_section('SpeedProcessing')
        self.config.set('SpeedProcessing', 'SpeedLength', str(enabled))
    
    # ==================== Reduce Size 视频减肥配置 ====================
    
    def is_reduce_size_enabled(self) -> bool:
        """检查视频减肥是否启用"""
        return self.config.getboolean('VideoOptimization', 'ReduceSize', fallback=True)
    
    def set_reduce_size_enabled(self, enabled: bool):
        """设置视频减肥"""
        if not self.config.has_section('VideoOptimization'):
            self.config.add_section('VideoOptimization')
        self.config.set('VideoOptimization', 'ReduceSize', str(enabled))
    
    # ==================== GPU 加速配置 ====================
    
    def is_gpu_enabled(self) -> bool:
        """检查GPU加速是否启用"""
        return self.config.getboolean('GPU', 'EnableGPU', fallback=True)
    
    def get_gpu_type(self) -> str:
        """获取GPU类型"""
        return self.config.get('GPU', 'GPUType', fallback='cuda')
    
    def is_intel_priority(self) -> bool:
        """检查是否I卡优先"""
        return self.config.getboolean('GPU', 'IntelPriority', fallback=False)
    
    def is_nvidia_warning_disabled(self) -> bool:
        """检查是否禁用N卡驱动警告"""
        return self.config.getboolean('GPU', 'DisableNvidiaWarning', fallback=False)
    
    def set_gpu_enabled(self, enabled: bool):
        """设置GPU加速"""
        if not self.config.has_section('GPU'):
            self.config.add_section('GPU')
        self.config.set('GPU', 'EnableGPU', str(enabled))
    
    def set_gpu_type(self, gpu_type: str):
        """设置GPU类型"""
        if not self.config.has_section('GPU'):
            self.config.add_section('GPU')
        self.config.set('GPU', 'GPUType', gpu_type)
    
    # ==================== Output 输出配置 ====================
    
    def get_output_directory(self) -> str:
        """获取默认输出目录"""
        return self.config.get('Output', 'OutputDirectory', fallback='./output')
    
    def is_separate_folder_enabled(self) -> bool:
        """检查是否输出至独立文件夹"""
        return self.config.getboolean('Output', 'SeparateFolder', fallback=True)
    
    def is_numbering_enabled(self) -> bool:
        """检查是否添加数字编号"""
        return self.config.getboolean('Output', 'AddNumbering', fallback=False)
    
    def is_subdirs_supported(self) -> bool:
        """检查是否支持子目录"""
        return self.config.getboolean('Output', 'SupportSubdirs', fallback=False)
    
    def set_output_directory(self, directory: str):
        """设置输出目录"""
        if not self.config.has_section('Output'):
            self.config.add_section('Output')
        self.config.set('Output', 'OutputDirectory', directory)
    
    # ==================== PostProcess 后处理配置 ====================
    
    def get_completion_action(self) -> str:
        """获取完成操作"""
        return self.config.get('PostProcess', 'OnCompletion', fallback='none')
    
    def is_output_folder_opened(self) -> bool:
        """检查是否打开输出文件夹"""
        return self.config.getboolean('PostProcess', 'OpenOutputFolder', fallback=False)
    
    def is_sound_notification_enabled(self) -> bool:
        """检查是否启用声音提示"""
        return self.config.getboolean('PostProcess', 'SoundNotification', fallback=True)
    
    def is_source_deleted(self) -> bool:
        """检查是否删除原视频"""
        return self.config.getboolean('PostProcess', 'DeleteSource', fallback=False)
    
    def set_completion_action(self, action: str):
        """设置完成操作"""
        if not self.config.has_section('PostProcess'):
            self.config.add_section('PostProcess')
        self.config.set('PostProcess', 'OnCompletion', action)
    
    # ==================== TaskManagement 任务管理配置 ====================
    
    def is_incomplete_tasks_preserved(self) -> bool:
        """检查是否保留未完成任务"""
        return self.config.getboolean('TaskManagement', 'PreserveIncompleteTasks', fallback=True)
    
    def is_removal_confirmation_enabled(self) -> bool:
        """检查是否移除任务时确认"""
        return self.config.getboolean('TaskManagement', 'ConfirmTaskRemoval', fallback=True)
    
    def get_max_parallel_tasks(self) -> int:
        """获取最大并行任务数"""
        return self.config.getint('TaskManagement', 'MaxParallelTasks', fallback=4)
    
    def set_max_parallel_tasks(self, count: int):
        """设置最大并行任务数"""
        if not self.config.has_section('TaskManagement'):
            self.config.add_section('TaskManagement')
        self.config.set('TaskManagement', 'MaxParallelTasks', str(count))
    
    # ==================== UI 界面配置 ====================
    
    def get_theme(self) -> str:
        """获取主题"""
        return self.config.get('UI', 'Theme', fallback='dark')
    
    def get_language(self) -> str:
        """获取语言"""
        value = self.config.get('UI', 'Language', fallback='zh_CN')
        return self._normalize_language_code(value)
    
    def is_minimize_to_tray(self) -> bool:
        """检查是否最小化到系统托盘"""
        return self.config.getboolean('UI', 'MinimizeToTray', fallback=False)
    
    def is_preview_muted(self) -> bool:
        """检查是否静音预览"""
        return self.config.getboolean('UI', 'MutePreview', fallback=False)
    
    def set_theme(self, theme: str):
        """设置主题"""
        if not self.config.has_section('UI'):
            self.config.add_section('UI')
        self.config.set('UI', 'Theme', theme)

    def set_language(self, language: str):
        """设置语言"""
        if not self.config.has_section('UI'):
            self.config.add_section('UI')
        self.config.set('UI', 'Language', self._normalize_language_code(language))
    
    # ==================== Performance 性能配置 ====================
    
    def is_hardware_acceleration_enabled(self) -> bool:
        """检查是否启用硬件加速"""
        return self.config.getboolean('Performance', 'HardwareAcceleration', fallback=True)
    
    def get_max_preview_resolution(self) -> str:
        """获取最大预览分辨率"""
        return self.config.get('Performance', 'MaxPreviewResolution', fallback='1920x1080')
    
    def get_preview_fps(self) -> int:
        """获取预览帧率"""
        return self.config.getint('Performance', 'PreviewFPS', fallback=30)
    
    # ==================== Update 更新配置 ====================
    
    def is_auto_update_enabled(self) -> bool:
        """检查是否启用自动更新"""
        return self.config.getboolean('Update', 'AutoUpdate', fallback=False)
    
    def get_update_check_interval(self) -> int:
        """获取检查更新间隔(天)"""
        return self.config.getint('Update', 'CheckUpdateInterval', fallback=7)
    
    # ==================== Advanced 高级配置 ====================
    
    def is_detailed_logging_enabled(self) -> bool:
        """检查是否启用详细日志"""
        return self.config.getboolean('Advanced', 'DetailedLogging', fallback=False)
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        return self.config.get('Advanced', 'LogLevel', fallback='INFO')
    
    def get_temp_file_retention(self) -> int:
        """获取临时文件保留时间(小时)"""
        return self.config.getint('Advanced', 'TempFileRetention', fallback=24)
    
    # ==================== Batch Options 批处理选项 ====================
    
    def get_batch_options(self) -> Dict[str, Any]:
        """获取批处理选项配置"""
        defaults = {
            # 转换页面
            'target_format': 'mp4',
            'file_exists_action': 'rename',
            'filename_remove_enabled': False,
            'filename_remove_text': '抖音|快手',
            'filename_remove_regex': False,
            'parallel_tasks': 2,
            'use_h265': False,
            'hdr_to_sdr': False,
            'ignore_completed': True,
            # 设置页面
            'complete_action': 'none',
            'open_folder_after_complete': True,
            'sound_alert': True,
            'gpu_accel': True,
            'nvidia_optimize': False,
            'intel_optimize': False,
            'filename_add_number': False,
            'subdir_support': False,
            'output_to_folder': False,
            'output_to_video_folder': False,
            'delete_original': False,
            'to_recycle': True,
            'move_to_original': False,
            'remove_task_after_complete': False,
            'remove_confirm': True,
            'keep_unfinished': False,
            # UI
            'ui_language': self.get_language(),
        }
        mapping = {
            'target_format': ('BatchConvert', 'TargetFormat'),
            'file_exists_action': ('BatchConvert', 'FileExistsAction'),
            'filename_remove_enabled': ('BatchConvert', 'FilenameRemoveEnabled'),
            'filename_remove_text': ('BatchConvert', 'FilenameRemoveText'),
            'filename_remove_regex': ('BatchConvert', 'FilenameRemoveRegex'),
            'parallel_tasks': ('BatchConvert', 'ParallelTasks'),
            'use_h265': ('BatchConvert', 'UseH265'),
            'hdr_to_sdr': ('BatchConvert', 'HdrToSdr'),
            'ignore_completed': ('BatchConvert', 'IgnoreCompleted'),
            'complete_action': ('BatchSettings', 'CompleteAction'),
            'open_folder_after_complete': ('BatchSettings', 'OpenFolderAfterComplete'),
            'sound_alert': ('BatchSettings', 'SoundAlert'),
            'gpu_accel': ('BatchSettings', 'GpuAccel'),
            'nvidia_optimize': ('BatchSettings', 'NvidiaOptimize'),
            'intel_optimize': ('BatchSettings', 'IntelOptimize'),
            'filename_add_number': ('BatchSettings', 'FilenameAddNumber'),
            'subdir_support': ('BatchSettings', 'SubdirSupport'),
            'output_to_folder': ('BatchSettings', 'OutputToFolder'),
            'output_to_video_folder': ('BatchSettings', 'OutputToVideoFolder'),
            'delete_original': ('BatchSettings', 'DeleteOriginal'),
            'to_recycle': ('BatchSettings', 'ToRecycle'),
            'move_to_original': ('BatchSettings', 'MoveToOriginal'),
            'remove_task_after_complete': ('BatchSettings', 'RemoveTaskAfterComplete'),
            'remove_confirm': ('BatchSettings', 'RemoveConfirm'),
            'keep_unfinished': ('BatchSettings', 'KeepUnfinished'),
            'ui_language': ('UI', 'Language'),
        }
        
        options = {}
        for key, default in defaults.items():
            section, ini_key = mapping[key]
            if isinstance(default, bool):
                value = self.config.getboolean(section, ini_key, fallback=default)
            elif isinstance(default, int):
                value = self.config.getint(section, ini_key, fallback=default)
            else:
                value = self.config.get(section, ini_key, fallback=default)
            options[key] = value
        return options
    
    def set_batch_options(self, options: Dict[str, Any]):
        """保存批处理选项配置"""
        mapping = {
            'target_format': ('BatchConvert', 'TargetFormat'),
            'file_exists_action': ('BatchConvert', 'FileExistsAction'),
            'filename_remove_enabled': ('BatchConvert', 'FilenameRemoveEnabled'),
            'filename_remove_text': ('BatchConvert', 'FilenameRemoveText'),
            'filename_remove_regex': ('BatchConvert', 'FilenameRemoveRegex'),
            'parallel_tasks': ('BatchConvert', 'ParallelTasks'),
            'use_h265': ('BatchConvert', 'UseH265'),
            'hdr_to_sdr': ('BatchConvert', 'HdrToSdr'),
            'ignore_completed': ('BatchConvert', 'IgnoreCompleted'),
            'complete_action': ('BatchSettings', 'CompleteAction'),
            'open_folder_after_complete': ('BatchSettings', 'OpenFolderAfterComplete'),
            'sound_alert': ('BatchSettings', 'SoundAlert'),
            'gpu_accel': ('BatchSettings', 'GpuAccel'),
            'nvidia_optimize': ('BatchSettings', 'NvidiaOptimize'),
            'intel_optimize': ('BatchSettings', 'IntelOptimize'),
            'filename_add_number': ('BatchSettings', 'FilenameAddNumber'),
            'subdir_support': ('BatchSettings', 'SubdirSupport'),
            'output_to_folder': ('BatchSettings', 'OutputToFolder'),
            'output_to_video_folder': ('BatchSettings', 'OutputToVideoFolder'),
            'delete_original': ('BatchSettings', 'DeleteOriginal'),
            'to_recycle': ('BatchSettings', 'ToRecycle'),
            'move_to_original': ('BatchSettings', 'MoveToOriginal'),
            'remove_task_after_complete': ('BatchSettings', 'RemoveTaskAfterComplete'),
            'remove_confirm': ('BatchSettings', 'RemoveConfirm'),
            'keep_unfinished': ('BatchSettings', 'KeepUnfinished'),
            'ui_language': ('UI', 'Language'),
        }
        
        for key, value in options.items():
            if key in mapping:
                section, ini_key = mapping[key]
                self.set_value(section, ini_key, value)
        self.save_config()
    
    # ==================== 获取所有配置 ====================
    
    def get_all_config(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置"""
        config_dict = {}
        
        for section in self.config.sections():
            config_dict[section] = {}
            for key, value in self.config.items(section):
                config_dict[section][key] = value
        
        return config_dict
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取指定部分的配置"""
        if self.config.has_section(section):
            return dict(self.config.items(section))
        return {}
    
    def set_value(self, section: str, key: str, value: Any):
        """设置配置值"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, str(value))
    
    def get_value(self, section: str, key: str, fallback: Any = None) -> Any:
        """获取配置值"""
        if self.config.has_option(section, key):
            return self.config.get(section, key)
        return fallback


# 全局配置实例
global_options = OptionsConfigManager()
