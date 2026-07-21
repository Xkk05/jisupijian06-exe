from typing import Dict, List

from PyQt6.QtCore import QThread, pyqtSignal

from processor.batch_video_runner import process_batch


class VideoProcessThread(QThread):
    """视频批量处理线程"""

    progress_updated = pyqtSignal(int, str)  # (进度, 消息)
    video_status_updated = pyqtSignal(int, str)  # (行号, 状态)
    finished = pyqtSignal()

    def __init__(self, video_list: List[Dict], config: Dict):
        super().__init__()
        self.video_list = video_list
        self.config = config
        self.is_running = True
        self.was_stopped = False
        self.batch_output_dir = None

    def run(self):
        """执行批量处理"""
        process_batch(
            self.video_list,
            self.config,
            progress_callback=lambda p, m: self.progress_updated.emit(p, m),
            status_callback=lambda idx, status: self.video_status_updated.emit(idx, status),
            is_running_callback=lambda: self.is_running,
        )
        self.was_stopped = not self.is_running
        self.finished.emit()

    def stop(self):
        """停止处理"""
        self.was_stopped = True
        self.is_running = False
