#!/usr/bin/env python
"""
极速批剪 - 启动程序
"""

import sys
import os
from pathlib import Path


def main():
    # 确保项目根目录在Python路径中
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)

    # 初始化日志（优先使用可执行文件所在目录）
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = current_dir

    try:
        from config.config_manager import get_user_config_dir

        get_user_config_dir().mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    settings = None
    try:
        from config.detailed_settings import DetailedSettings

        settings = DetailedSettings().system
    except Exception:
        settings = None

    logging_ready = False
    try:
        from utils.unified_logger import init_logger, redirect_std_streams, logger

        init_logger(Path(base_dir), settings)
        logging_ready = True
        logger.info("日志系统已初始化")
    except Exception:
        pass

    if logging_ready:
        try:
            from utils.unified_logger import redirect_std_streams

            frozen = getattr(sys, "frozen", False)
            has_console = sys.stderr is not None and sys.stderr is not getattr(
                sys, "__stderr__", None
            )
            if frozen and not has_console:
                redirect_std_streams(True, enable_stdout=True, enable_stderr=False)
            else:
                redirect_std_streams(True, enable_stdout=True, enable_stderr=True)
        except Exception:
            pass

    # Qt 字体渲染设置（必须在任何 Qt 相关环境变量之前设置）
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_FONT_DPI"] = "96"

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import Qt, QLocale
        from ui.theme import Theme
        from ui.i18n import get_language_manager
        from ui.batch_video_processor_window import BatchVideoProcessorWindow
        from processor.options_manager import OptionsConfigManager
        from utils.icon_utils import build_app_logo_icon

        QLocale.setDefault(QLocale.c())

        # 创建应用
        app = QApplication(sys.argv)

        # 初始化界面语言
        options_manager = OptionsConfigManager()
        get_language_manager().set_language(options_manager.get_language())

        # 全局字体与样式
        default_font = QFont(["Segoe UI", "Microsoft YaHei UI"], 10)
        default_font.setStyleStrategy(QFont.StyleStrategy.PreferQuality)
        default_font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
        app.setFont(default_font)
        app.setStyleSheet(Theme.global_stylesheet())
        app.setWindowIcon(build_app_logo_icon())

        # 启动主窗口
        window = BatchVideoProcessorWindow()
        window.show()

        sys.exit(app.exec())

    except ImportError as e:
        try:
            from utils.unified_logger import logger

            logger.error(f"启动失败: {e}")
        except Exception:
            pass
        print(f"启动失败: {e}")
        input("按回车键退出...")
    except Exception as e:
        import traceback

        try:
            from utils.unified_logger import logger

            logger.error("未捕获异常:\n%s", traceback.format_exc())
        except Exception:
            pass
        traceback.print_exc()
        input("按回车键退出...")


if __name__ == "__main__":
    main()
