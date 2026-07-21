# -*- coding: utf-8 -*-
"""
处理器管道系统 - 支持链式调用处理器
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional


@dataclass
class ProcessingData:
    """处理器间的统一数据格式"""
    video_path: str
    audio_path: str = ""
    output_path: str = ""
    duration: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)
    
    def copy(self):
        """创建副本"""
        return ProcessingData(
            video_path=self.video_path,
            audio_path=self.audio_path,
            output_path=self.output_path,
            duration=self.duration,
            metadata=self.metadata.copy() if self.metadata else None,
            extra_params=self.extra_params.copy()
        )


class ProcessorPipeline:
    """处理器链式调用管道"""
    
    def __init__(self):
        self.processors = []
        self.results = []
    
    def add_processor(self, processor):
        """添加处理器到管道"""
        self.processors.append(processor)
        return self
    
    def execute(self, data: ProcessingData) -> Tuple[bool, ProcessingData, List[str]]:
        """执行处理器链"""
        try:
            from .unified_logger import logger
        except ImportError:
            logger = None
        
        self.results = []
        current_data = data.copy()
        errors = []
        
        try:
            for i, processor in enumerate(self.processors):
                processor_name = processor.__class__.__name__
                processor_label = getattr(processor, "name", processor_name)
                
                try:
                    if logger:
                        logger.info(f"执行处理器 [{i+1}/{len(self.processors)}]: {processor_name}")
                    
                    # 执行处理器
                    if hasattr(processor, 'process'):
                        success, output_data, logs = processor.process(current_data)
                    else:
                        # 如果处理器没有process方法，则跳过
                        success = True
                        output_data = current_data
                        logs = []
                    
                    # 记录日志
                    if logger:
                        for log in logs:
                            logger.info(f"  {log}")
                    
                    if not success:
                        error_msg = f"处理器 {processor_label} 失败"
                        errors.append(error_msg)
                        if logger:
                            logger.error(error_msg)
                        return False, current_data, errors
                    
                    # 将输出作为下一个处理器的输入
                    current_data = output_data
                    self.results.append((processor_name, success, output_data))
                    
                    if logger:
                        logger.info(f"✓ {processor_name} 完成")
                    
                except Exception as e:
                    error_msg = f"处理器 {processor_name} 异常: {str(e)}"
                    errors.append(error_msg)
                    if logger:
                        logger.error(error_msg)
                    return False, current_data, errors
            
            return True, current_data, errors if errors else ["所有处理器执行完成"]
            
        except Exception as e:
            error_msg = f"管道执行异常: {str(e)}"
            if logger:
                logger.error(error_msg)
            return False, current_data, [error_msg]
    
    def get_results(self):
        """获取执行结果"""
        return self.results
