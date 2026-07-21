import os

from ui.batch_video.main_window import BatchVideoProcessorWindow, BorderStyleDialog

__all__ = ["BatchVideoProcessorWindow", "BorderStyleDialog"]


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from PyQt6.QtCore import Qt
    from ui.theme import Theme
    from utils.icon_utils import build_app_logo_icon

    # Qt 字体渲染设置（必须在任何 Qt 相关环境变量之前设置）
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_FONT_DPI"] = "96"

    # 确保项目根目录在Python路径中
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 创建应用程序
    app = QApplication(sys.argv)

    # 设置默认字体（确保中文显示正常）
    default_font = QFont(["Segoe UI", "Microsoft YaHei UI"], 10)
    default_font.setStyleStrategy(QFont.StyleStrategy.PreferQuality)
    default_font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
    app.setFont(default_font)
    app.setStyleSheet(Theme.global_stylesheet())
    app.setWindowIcon(build_app_logo_icon())

    print("[✓] UI配置完成，字体: 微软雅黑")

    # 创建并显示主窗口
    window = BatchVideoProcessorWindow()
    window.show()

    sys.exit(app.exec())
