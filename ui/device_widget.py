import time
import logging
from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFrame, QSizePolicy, QMessageBox
)
from PySide6.QtGui import QImage, QPixmap, QPainter, QMouseEvent, QKeyEvent

from core.port_forwarder import PortForwarder
from core.stream_receiver import StreamReceiverThread
from core.wda_controller import WDAController

logger = logging.getLogger("DeviceWidget")

class ScreenCanvas(QLabel):
    """
    Interactive QLabel screen canvas.
    Displays live iOS screen frame and handles mouse click, drag-to-swipe, and key events.
    """
    def __init__(self, controller: WDAController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #000000; border-radius: 6px;")

        self.current_qimage: QImage = None
        self.ios_screen_w = 375  # Default baseline width
        self.ios_screen_h = 812  # Default baseline height
        
        self.press_start_pos: QPoint = None
        self.press_start_time: float = 0.0

    def update_frame(self, q_img: QImage, w: int, h: int):
        """Updates current frame and scales to fit canvas container."""
        self.current_qimage = q_img
        if w > 0 and h > 0:
            self.ios_screen_w = w
            self.ios_screen_h = h
        
        # Scale pixmap preserving aspect ratio
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled_pixmap)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.press_start_pos = event.position().toPoint()
            self.press_start_time = time.time()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.press_start_pos is not None:
            end_pos = event.position().toPoint()
            duration = time.time() - self.press_start_time
            
            # Map canvas coordinates to iOS native screen coordinates
            start_ios = self._map_to_ios_coords(self.press_start_pos)
            end_ios = self._map_to_ios_coords(end_pos)

            if start_ios and end_ios:
                dx = abs(end_pos.x() - self.press_start_pos.x())
                dy = abs(end_pos.y() - self.press_start_pos.y())

                # If movement is small, treat as Click/Tap
                if dx < 10 and dy < 10:
                    logger.info(f"Click -> Tap at iOS ({start_ios[0]}, {start_ios[1]})")
                    self.controller.tap(start_ios[0], start_ios[1])
                else:
                    # Treat as Drag/Swipe
                    logger.info(f"Drag -> Swipe from {start_ios} to {end_ios} (duration={duration:.2f}s)")
                    self.controller.swipe(start_ios[0], start_ios[1], end_ios[0], end_ios[1], duration=max(0.2, min(1.5, duration)))

            self.press_start_pos = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        text = event.text()
        if text and text.isprintable():
            logger.info(f"PC Keyboard -> Type text '{text}' into iOS")
            self.controller.type_text(text)
        elif event.key() == Qt.Key_Backspace:
            self.controller.type_text("\b")
        elif event.key() == Qt.Key_Return:
            self.controller.type_text("\n")
        super().keyPressEvent(event)

    def _map_to_ios_coords(self, pt: QPoint):
        """Converts canvas widget relative (x, y) to iOS native pixel coordinates."""
        if not self.pixmap() or self.pixmap().isNull():
            return None

        pm_w = self.pixmap().width()
        pm_h = self.pixmap().height()
        lbl_w = self.width()
        lbl_h = self.height()

        # Pixmap centered offset
        offset_x = (lbl_w - pm_w) // 2
        offset_y = (lbl_h - pm_h) // 2

        rel_x = pt.x() - offset_x
        rel_y = pt.y() - offset_y

        if 0 <= rel_x <= pm_w and 0 <= rel_y <= pm_h:
            ios_x = int((rel_x / pm_w) * self.ios_screen_w)
            ios_y = int((rel_y / pm_h) * self.ios_screen_h)
            return (ios_x, ios_y)
        return None

    def resizeEvent(self, event):
        if self.current_qimage:
            pixmap = QPixmap.fromImage(self.current_qimage)
            scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled)
        super().resizeEvent(event)


class DeviceWidget(QFrame):
    """
    Card Container for a single connected iPhone.
    Combines Device Header Info, Interactive Screen Canvas, and Control Toolbar.
    """
    def __init__(self, udid: str, device_name: str = "iPhone", wda_port: int = 8100, mjpeg_port: int = 9100, parent=None):
        super().__init__(parent)
        self.udid = udid
        self.device_name = device_name
        self.wda_port = wda_port
        self.mjpeg_port = mjpeg_port

        self.setObjectName("device_card")

        # Core components
        self.forwarder = PortForwarder(udid, wda_port, mjpeg_port)
        self.controller = WDAController(f"http://localhost:{wda_port}")
        self.stream_thread = StreamReceiverThread(
            stream_url=f"http://localhost:{mjpeg_port}",
            fallback_url=f"http://localhost:{wda_port}/mjpegfeed"
        )

        self.init_ui()
        self.start_device()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header Info Bar
        header = QHBoxLayout()
        self.lbl_title = QLabel(f"📱 {self.device_name}")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.lbl_status = QLabel("Offline")
        self.lbl_status.setObjectName("status_label")

        self.lbl_fps = QLabel("FPS: 0")
        self.lbl_fps.setStyleSheet("color: #00B37E; font-weight: bold;")

        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_fps)
        header.addWidget(self.lbl_status)
        layout.addLayout(header)

        # Interactive Canvas Screen
        self.canvas = ScreenCanvas(self.controller)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas)

        # Quick Control Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        btn_home = QPushButton("🏠 Home")
        btn_home.clicked.connect(self.on_click_home)

        btn_appswitcher = QPushButton("📑 Apps")
        btn_appswitcher.clicked.connect(self.on_click_appswitcher)

        btn_lock = QPushButton("🔒 Power")
        btn_lock.clicked.connect(self.on_click_lock)

        btn_vol_up = QPushButton("🔊 +")
        btn_vol_up.clicked.connect(lambda: self.controller.volume_up())

        btn_vol_down = QPushButton("🔉 -")
        btn_vol_down.clicked.connect(lambda: self.controller.volume_down())

        toolbar.addWidget(btn_home)
        toolbar.addWidget(btn_appswitcher)
        toolbar.addWidget(btn_lock)
        toolbar.addWidget(btn_vol_up)
        toolbar.addWidget(btn_vol_down)
        layout.addLayout(toolbar)

        # Text input row
        input_row = QHBoxLayout()
        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Gõ chữ để gửi sang iPhone...")
        self.txt_input.returnPressed.connect(self.on_send_text)

        btn_send = QPushButton("Gửi")
        btn_send.setObjectName("btn_accent")
        btn_send.clicked.connect(self.on_send_text)

        input_row.addWidget(self.txt_input)
        input_row.addWidget(btn_send)
        layout.addLayout(input_row)

    def start_device(self):
        """Starts port forwarding, connects WDA API, and starts video stream thread."""
        self.lbl_status.setText("Đang kết nối USB...")
        
        # 1. Forward USB ports
        self.forwarder.start_forwarding()

        # 2. Connect WDA Controller
        if self.controller.connect():
            self.lbl_status.setText("WDA Sẵn sàng")
        else:
            self.lbl_status.setText("Chờ WDA...")

        # 3. Connect Stream Thread
        self.stream_thread.frame_ready.connect(self.canvas.update_frame)
        self.stream_thread.fps_updated.connect(lambda fps: self.lbl_fps.setText(f"FPS: {fps:.1f}"))
        self.stream_thread.connection_lost.connect(lambda err: self.lbl_status.setText(f"Lỗi luồng: {err}"))
        self.stream_thread.start()

    def stop_device(self):
        """Clean up threads and port forwarders on device disconnect."""
        self.stream_thread.stop()
        self.stream_thread.wait(1000)
        self.forwarder.stop_forwarding()

    def on_click_home(self):
        self.controller.press_home()

    def on_click_appswitcher(self):
        self.controller.press_app_switcher()

    def on_click_lock(self):
        self.controller.lock_screen()

    def on_send_text(self):
        text = self.txt_input.text()
        if text:
            self.controller.type_text(text)
            self.txt_input.clear()
