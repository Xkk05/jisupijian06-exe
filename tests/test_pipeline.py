# -*- coding: utf-8 -*-
"""
处理器管道系统单元测试
"""
import pytest
from dataclasses import dataclass
from typing import Dict, Any


class TestProcessingData:
    """ProcessingData 数据类测试"""
    
    def test_default_values(self):
        """测试默认值"""
        from utils.pipeline import ProcessingData
        
        data = ProcessingData(video_path="/path/to/video.mp4")
        
        assert data.video_path == "/path/to/video.mp4"
        assert data.audio_path == ""
        assert data.output_path == ""
        assert data.duration == 0.0
        assert data.metadata is None
        assert data.extra_params == {}

    def test_full_values(self):
        """测试完整值"""
        from utils.pipeline import ProcessingData
        
        data = ProcessingData(
            video_path="/input/video.mp4",
            audio_path="/input/audio.mp3",
            output_path="/output/result.mp4",
            duration=120.5,
            metadata={"fps": 30, "resolution": "1920x1080"},
            extra_params={"codec": "h264", "quality": "high"}
        )
        
        assert data.video_path == "/input/video.mp4"
        assert data.audio_path == "/input/audio.mp3"
        assert data.output_path == "/output/result.mp4"
        assert data.duration == 120.5
        assert data.metadata == {"fps": 30, "resolution": "1920x1080"}
        assert data.extra_params == {"codec": "h264", "quality": "high"}

    def test_copy_method(self):
        """测试复制方法"""
        from utils.pipeline import ProcessingData
        
        original = ProcessingData(
            video_path="/input/video.mp4",
            metadata={"key": "value"},
            extra_params={"param": "value"}
        )
        
        copy = original.copy()
        
        # 验证值相等
        assert copy.video_path == original.video_path
        assert copy.metadata == original.metadata
        assert copy.extra_params == original.extra_params
        
        # 验证是不同对象
        assert copy is not original
        assert copy.metadata is not original.metadata
        assert copy.extra_params is not original.extra_params

    def test_copy_independence(self):
        """测试复制后的独立性"""
        from utils.pipeline import ProcessingData
        
        original = ProcessingData(
            video_path="/input/video.mp4",
            metadata={"key": "original"},
            extra_params={"param": "original"}
        )
        
        copy = original.copy()
        
        # 修改复制对象
        copy.metadata["key"] = "modified"
        copy.extra_params["param"] = "modified"
        
        # 验证原对象不受影响
        assert original.metadata["key"] == "original"
        assert original.extra_params["param"] == "original"


class MockProcessor:
    """模拟处理器"""
    
    def __init__(self, name: str, should_succeed: bool = True):
        self.name = name
        self.should_succeed = should_succeed
        self.was_called = False
        self.received_data = None
    
    def process(self, data):
        self.was_called = True
        self.received_data = data
        
        if self.should_succeed:
            output = data.copy()
            output.extra_params[self.name] = "processed"
            return True, output, [f"{self.name} processed successfully"]
        else:
            return False, data, [f"{self.name} failed"]


class TestProcessorPipeline:
    """ProcessorPipeline 测试"""
    
    def test_empty_pipeline(self):
        """测试空管道"""
        from utils.pipeline import ProcessorPipeline, ProcessingData
        
        pipeline = ProcessorPipeline()
        data = ProcessingData(video_path="/test/video.mp4")
        
        success, result, logs = pipeline.execute(data)
        
        assert success is True
        assert result.video_path == "/test/video.mp4"
        assert "所有处理器执行完成" in logs

    def test_single_processor_success(self):
        """测试单个处理器成功"""
        from utils.pipeline import ProcessorPipeline, ProcessingData
        
        pipeline = ProcessorPipeline()
        processor = MockProcessor("TestProcessor")
        pipeline.add_processor(processor)
        
        data = ProcessingData(video_path="/test/video.mp4")
        success, result, logs = pipeline.execute(data)
        
        assert success is True
        assert processor.was_called is True
        assert result.extra_params.get("TestProcessor") == "processed"

    def test_multiple_processors_success(self):
        """测试多个处理器成功执行"""
        from utils.pipeline import ProcessorPipeline, ProcessingData
        
        pipeline = ProcessorPipeline()
        processor1 = MockProcessor("Processor1")
        processor2 = MockProcessor("Processor2")
        processor3 = MockProcessor("Processor3")
        
        pipeline.add_processor(processor1)
        pipeline.add_processor(processor2)
        pipeline.add_processor(processor3)
        
        data = ProcessingData(video_path="/test/video.mp4")
        success, result, logs = pipeline.execute(data)
        
        assert success is True
        assert processor1.was_called is True
        assert processor2.was_called is True
        assert processor3.was_called is True
        assert result.extra_params.get("Processor1") == "processed"
        assert result.extra_params.get("Processor2") == "processed"
        assert result.extra_params.get("Processor3") == "processed"

    def test_processor_failure(self):
        """测试处理器失败"""
        from utils.pipeline import ProcessorPipeline, ProcessingData
        
        pipeline = ProcessorPipeline()
        processor1 = MockProcessor("Processor1", should_succeed=True)
        processor2 = MockProcessor("Processor2", should_succeed=False)
        processor3 = MockProcessor("Processor3", should_succeed=True)
        
        pipeline.add_processor(processor1)
        pipeline.add_processor(processor2)
        pipeline.add_processor(processor3)
        
        data = ProcessingData(video_path="/test/video.mp4")
        success, result, errors = pipeline.execute(data)
        
        assert success is False
        assert processor1.was_called is True
        assert processor2.was_called is True
        assert processor3.was_called is False  # 失败后就停止
        assert any("Processor2" in err for err in errors)

    def test_processor_chain_data_flow(self):
        """测试处理器链数据流"""
        from utils.pipeline import ProcessorPipeline, ProcessingData
        
        class DataModifier:
            def __init__(self, key, value):
                self.key = key
                self.value = value
            
            def process(self, data):
                output = data.copy()
                output.extra_params[self.key] = self.value
                return True, output, []
        
        pipeline = ProcessorPipeline()
        pipeline.add_processor(DataModifier("step1", "value1"))
        pipeline.add_processor(DataModifier("step2", "value2"))
        
        data = ProcessingData(video_path="/test/video.mp4")
        success, result, _ = pipeline.execute(data)
        
        assert success is True
        assert result.extra_params.get("step1") == "value1"
        assert result.extra_params.get("step2") == "value2"

    def test_processor_without_process_method(self):
        """测试没有process方法的处理器"""
        from utils.pipeline import ProcessorPipeline, ProcessingData
        
        class NoProcessMethod:
            pass
        
        pipeline = ProcessorPipeline()
        pipeline.add_processor(NoProcessMethod())
        
        data = ProcessingData(video_path="/test/video.mp4")
        success, result, _ = pipeline.execute(data)
        
        assert success is True

    def test_processor_exception_handling(self):
        """测试处理器异常处理"""
        from utils.pipeline import ProcessorPipeline, ProcessingData
        
        class ExceptionProcessor:
            def process(self, data):
                raise ValueError("Test exception")
        
        pipeline = ProcessorPipeline()
        pipeline.add_processor(ExceptionProcessor())
        
        data = ProcessingData(video_path="/test/video.mp4")
        success, result, errors = pipeline.execute(data)
        
        assert success is False
        assert any("异常" in err for err in errors)

    def test_get_results(self):
        """测试获取执行结果"""
        from utils.pipeline import ProcessorPipeline, ProcessingData
        
        pipeline = ProcessorPipeline()
        processor1 = MockProcessor("Processor1")
        processor2 = MockProcessor("Processor2")
        
        pipeline.add_processor(processor1)
        pipeline.add_processor(processor2)
        
        data = ProcessingData(video_path="/test/video.mp4")
        pipeline.execute(data)
        
        results = pipeline.get_results()
        
        assert len(results) == 2
        assert results[0][0] == "MockProcessor"
        assert results[0][1] is True
        assert results[1][0] == "MockProcessor"
        assert results[1][1] is True

    def test_chaining_interface(self):
        """测试链式调用接口"""
        from utils.pipeline import ProcessorPipeline
        
        pipeline = ProcessorPipeline()
        processor1 = MockProcessor("P1")
        processor2 = MockProcessor("P2")
        
        # 测试add_processor返回self支持链式调用
        result = pipeline.add_processor(processor1)
        assert result is pipeline
        
        pipeline.add_processor(processor2)
        assert len(pipeline.processors) == 2
