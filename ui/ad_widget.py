"""
广告展示组件
在标题栏中展示 4:1 广告横幅，支持圆角、悬浮动效和本地缓存。
"""

import json
import os
import webbrowser

import requests
from PyQt6.QtCore import QThread, QUrl, QPoint, pyqtSignal, Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsDropShadowEffect

from config.app_info import SOFT_NUMBER
from utils.app_data_paths import get_user_data_dir
from utils.unified_logger import logger


class AdInfoWorker(QThread):
    """后台拉取广告元数据，避免阻塞 UI。"""

    loaded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, adv_position: str):
        super().__init__()
        self._adv_position = adv_position

    def run(self):
        try:
            resp = requests.post(
                "https://api-web.kunqiongai.com/soft_desktop/get_adv",
                data={
                    "soft_number": SOFT_NUMBER,
                    "adv_position": self._adv_position,
                },
                timeout=10,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 1 and result.get("data"):
                ad_data = result["data"][0] if isinstance(result["data"], list) else result["data"]
                self.loaded.emit(
                    {
                        "adv_url": ad_data.get("adv_url", ""),
                        "target_url": ad_data.get("target_url", ""),
                    }
                )
            else:
                self.failed.emit("无广告数据")
        except Exception as exc:
            self.failed.emit(str(exc))


class AdBanner(QWidget):
    """标题栏广告横幅 (4:1 宽高比)。"""

    clicked = pyqtSignal()

    def __init__(self, parent=None, height: int = 38):
        super().__init__(parent)
        self._target_url = ""
        self._ad_height = height
        self._ad_width = height * 4
        self._display_height = max(28, height - 4)
        self._radius = 10
        self._worker = None

        self.setFixedSize(self._ad_width, self._ad_height)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setVisible(False)

        self._image_label = QLabel(self)
        self._image_label.setFixedSize(self._ad_width, self._display_height)
        self._image_label.move(0, 2)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("border: none; background: transparent;")

        # 阴影 + 悬浮动画
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(10)
        self._shadow.setOffset(0, 1)
        self._shadow.setColor(QColor(15, 23, 42, 28))
        self._image_label.setGraphicsEffect(self._shadow)

        self._hover_anim = QPropertyAnimation(self._image_label, b"pos", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._nam = QNetworkAccessManager(self)
        self._nam.finished.connect(self._on_image_loaded)
        self.setStyleSheet("background: transparent; border: none;")

    def _get_cache_dir(self) -> str:
        return str(get_user_data_dir())

    def _cache_meta_path(self) -> str:
        return os.path.join(self._get_cache_dir(), "ad_cache.json")

    def _cache_image_path(self) -> str:
        return os.path.join(self._get_cache_dir(), "ad_cache.png")

    def _load_cache(self) -> None:
        """先展示本地缓存，提升启动首屏速度。"""
        try:
            meta_path = self._cache_meta_path()
            img_path = self._cache_image_path()
            if not os.path.exists(meta_path) or not os.path.exists(img_path):
                return

            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            self._target_url = meta.get("target_url", "")

            pixmap = QPixmap(img_path)
            if pixmap.isNull():
                return
            rounded = self._rounded_pixmap(pixmap)
            self._image_label.setPixmap(rounded)
            self.setVisible(True)
        except Exception as exc:
            logger.warning(f"[AdBanner] 读取广告缓存失败: {exc}")

    def _save_cache_meta(self, adv_url: str, target_url: str) -> None:
        try:
            with open(self._cache_meta_path(), "w", encoding="utf-8") as f:
                json.dump({"adv_url": adv_url, "target_url": target_url}, f, ensure_ascii=False)
        except Exception as exc:
            logger.warning(f"[AdBanner] 写入广告缓存元数据失败: {exc}")

    def _rounded_pixmap(self, source: QPixmap) -> QPixmap:
        dpr = max(1.0, float(self.devicePixelRatioF()))
        target_w = max(1, int(round(self._ad_width * dpr)))
        target_h = max(1, int(round(self._display_height * dpr)))

        scaled = source.scaled(
            target_w,
            target_h,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        output = QPixmap(target_w, target_h)
        output.fill(Qt.GlobalColor.transparent)
        output.setDevicePixelRatio(dpr)

        painter = QPainter(output)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            # Qt6 / PyQt6 某些版本没有 HighQualityAntialiasing，使用兼容写法
            if hasattr(QPainter.RenderHint, "HighQualityAntialiasing"):
                painter.setRenderHint(QPainter.RenderHint.HighQualityAntialiasing)
            path = QPainterPath()
            path.addRoundedRect(
                0.0,
                0.0,
                float(target_w),
                float(target_h),
                float(self._radius * dpr),
                float(self._radius * dpr),
            )
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled)
        finally:
            painter.end()
        return output

    def load_ad(self, adv_position: str = "adv_position_01"):
        """加载广告：先缓存，后异步刷新。"""
        self._load_cache()

        self._worker = AdInfoWorker(adv_position)
        self._worker.loaded.connect(self._on_ad_meta_loaded)
        self._worker.failed.connect(self._on_ad_meta_failed)
        self._worker.start()

    def _on_ad_meta_loaded(self, data: dict):
        adv_url = data.get("adv_url", "")
        self._target_url = data.get("target_url", "")
        if not adv_url:
            logger.info("[AdBanner] 无广告图片地址")
            return
        self._save_cache_meta(adv_url, self._target_url)
        self._load_image(adv_url)
        logger.info(f"[AdBanner] 广告元数据加载成功: {adv_url}")

    def _on_ad_meta_failed(self, error: str):
        logger.warning(f"[AdBanner] 拉取广告数据失败: {error}")

    def _load_image(self, url: str):
        request = QNetworkRequest(QUrl(url))
        self._nam.get(request)

    def _on_image_loaded(self, reply: QNetworkReply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = bytes(reply.readAll())
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                rounded = self._rounded_pixmap(pixmap)
                self._image_label.setPixmap(rounded)
                self.setVisible(True)
                try:
                    with open(self._cache_image_path(), "wb") as f:
                        f.write(data)
                except Exception as exc:
                    logger.warning(f"[AdBanner] 写入广告缓存图片失败: {exc}")
        else:
            logger.warning(f"[AdBanner] 图片加载失败: {reply.errorString()}")
        reply.deleteLater()

    def enterEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._image_label.pos())
        self._hover_anim.setEndValue(QPoint(0, 0))
        self._hover_anim.start()
        self._shadow.setBlurRadius(12)
        self._shadow.setOffset(0, 2)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._image_label.pos())
        self._hover_anim.setEndValue(QPoint(0, 2))
        self._hover_anim.start()
        self._shadow.setBlurRadius(10)
        self._shadow.setOffset(0, 1)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._target_url:
            webbrowser.open(self._target_url)
            self.clicked.emit()
        super().mousePressEvent(event)
