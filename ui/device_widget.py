import time
import logging
import win32gui
import win32api
import win32con
import pyautogui

# Disable PyAutoGUI fail-safe to prevent corner cursor exceptions
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFrame, QSizePolicy
)
from PySide6.QtGui import QImage, QPixmap, QMouseEvent, QKeyEvent

from core.port_forwarder import PortForwarder
from core.stream_receiver import StreamReceiverThread
from core.wda_controller import WDAController

logger = logging.getLogger("DeviceWidget")

class ScreenCanvas(QLabel):
    """
    Interactive QLabel screen canvas.
    Displays live iOS screen frame (from 3uTools HD Mirror Engine or WDA stream)
    and translates mouse clicks/drags directly to screen!
    """
    def __init__(self, controller: WDAController, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #000000; border-radius: 6px;")

        self.current_qimage: QImage = None
        self.ios_screen_w = 375
        self.ios_screen_h = 812
        
        self.press_start_pos: QPoint = None
        self.press_start_time: float = 0.0

    def update_frame(self, q_img: QImage, w: int, h: int):
        """Updates current frame and scales to fit canvas container."""
        self.current_qimage = q_img
        if w > 0 and h > 0:
            self.ios_screen_w = w
            self.ios_screen_h = h
        
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
            
            dx = abs(end_pos.x() - self.press_start_pos.x())
            dy = abs(end_pos.y() - self.press_start_pos.y())

            # Attempt 1: Try WDA tap/swipe if WDA is connected
            if self.controller and self.controller.is_connected:
                start_ios = self._map_to_ios_coords(self.press_start_pos)
                end_ios = self._map_to_ios_coords(end_pos)
                if start_ios and end_ios:
                    if dx < 10 and dy < 10:
                        self.controller.tap(start_ios[0], start_ios[1])
                    else:
                        self.controller.swipe(start_ios[0], start_ios[1], end_ios[0], end_ios[1], duration=max(0.2, min(1.5, duration)))
            else:
                # Attempt 2: Dispatch mouse click/drag to 3uTools Real-time Screen Window
                self._dispatch_to_3utools_window(self.press_start_pos, end_pos, is_click=(dx < 10 and dy < 10))

            self.press_start_pos = None
        super().mouseReleaseEvent(event)

    def _dispatch_to_3utools_window(self, start_pt: QPoint, end_pt: QPoint, is_click: bool):
        """Dispatches mouse click or drag to 3uTools Real-time Screen window."""
        hwnd = self._find_3utools_window()
        if not hwnd:
            return

        rect = win32gui.GetWindowRect(hwnd)
        win_w = rect[2] - rect[0]
        win_h = rect[3] - rect[1]

        if not self.pixmap() or self.pixmap().isNull():
            return

        pm_w = self.pixmap().width()
        pm_h = self.pixmap().height()
        lbl_w = self.width()
        lbl_h = self.height()

        offset_x = (lbl_w - pm_w) // 2
        offset_y = (lbl_h - pm_h) // 2

        rel_x = start_pt.x() - offset_x
        rel_y = start_pt.y() - offset_y

        if 0 <= rel_x <= pm_w and 0 <= rel_y <= pm_h:
            target_x = rect[0] + int((rel_x / pm_w) * win_w)
            target_y = rect[1] + int((rel_y / pm_h) * win_h)

            if is_click:
                pyautogui.click(target_x, target_y)
            else:
                end_rel_x = end_pt.x() - offset_x
                end_rel_y = end_pt.y() - offset_y
                end_target_x = rect[0] + int((end_rel_x / pm_w) * win_w)
                end_target_y = rect[1] + int((end_rel_y / pm_h) * win_h)
                pyautogui.moveTo(target_x, target_y)
                pyautogui.dragTo(end_target_x, end_target_y, duration=0.3, button='left')

    def _find_3utools_window(self):
        hwnd = None
        keywords = ["real-time screen", "3uairplayer", "3utools", "iphone", "idevice", "screen"]
        def enum_cb(h, _):
            nonlocal hwnd
            txt = win32gui.GetWindowText(h)
            if txt:
                txt_lower = txt.lower()
                for k in keywords:
                    if k in txt_lower and "phim" not in txt_lower and "antigravity" not in txt_lower and "command prompt" not in txt_lower:
                        hwnd = h
                        return
        win32gui.EnumWindows(enum_cb, None)
        return hwnd

    def keyPressEvent(self, event: QKeyEvent):
        text = event.text()
        if text and text.isprintable():
            if self.controller and self.controller.is_connected:
                self.controller.type_text(text)
            else:
                pyautogui.write(text)
        super().keyPressEvent(event)

    def _map_to_ios_coords(self, pt: QPoint):
        if not self.pixmap() or self.pixmap().isNull():
            return None

        pm_w = self.pixmap().width()
        pm_h = self.pixmap().height()
        lbl_w = self.width()
        lbl_h = self.height()

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
    Displays Live Stream (3uTools HD Mirror / WDA) & Control Bar.
    """
    def __init__(self, udid: str, device_name: str = "iPhone", wda_port: int = 8200, mjpeg_port: int = 9200, parent=None):
        super().__init__(parent)
        self.udid = udid
        self.device_name = device_name
        self.wda_port = wda_port
        self.mjpeg_port = mjpeg_port

        self.setObjectName("device_card")

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

        header = QHBoxLayout()
        self.lbl_title = QLabel(f"📱 {self.device_name}")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.lbl_status = QLabel("Đang quét màn hình...")
        self.lbl_status.setObjectName("status_label")

        self.lbl_fps = QLabel("FPS: 0")
        self.lbl_fps.setStyleSheet("color: #00B37E; font-weight: bold;")

        header.addWidget(self.lbl_title)
        header.addStretch()
        header.addWidget(self.lbl_fps)
        header.addWidget(self.lbl_status)
        layout.addLayout(header)

        self.canvas = ScreenCanvas(self.controller)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.canvas)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        btn_home = QPushButton("🏠 Home")
        btn_home.clicked.connect(self.on_click_home)

        btn_appswitcher = QPushButton("📑 Apps")
        btn_appswitcher.clicked.connect(self.on_click_appswitcher)

        btn_lock = QPushButton("🔒 Power")
        btn_lock.clicked.connect(self.on_click_lock)

        toolbar.addWidget(btn_home)
        toolbar.addWidget(btn_appswitcher)
        toolbar.addWidget(btn_lock)
        layout.addLayout(toolbar)

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
        """Starts stream thread and control bridge."""
        self.lbl_status.setText("Luồng HD Sẵn sàng")

        # 1. Forward USB ports in background
        self.forwarder.start_forwarding()

        # 2. Try WDA connection
        self.controller.connect(retries=2, delay=0.5)

        # 3. Connect Stream Thread (3uTools HD Mirror / WDA)
        self.stream_thread.frame_ready.connect(self.canvas.update_frame)
        self.stream_thread.fps_updated.connect(lambda fps: self.lbl_fps.setText(f"FPS: {fps:.1f}"))
        self.stream_thread.connection_lost.connect(lambda err: self.lbl_status.setText(f"Lỗi luồng: {err}"))
        self.stream_thread.start()

    def stop_device(self):
        self.stream_thread.stop()
        self.stream_thread.wait(1000)
        self.forwarder.stop_forwarding()

    def on_click_home(self):
        if self.controller and self.controller.is_connected:
            self.controller.press_home()
        else:
            pyautogui.press('win')

    def on_click_appswitcher(self):
        if self.controller and self.controller.is_connected:
            self.controller.press_app_switcher()

    def on_click_lock(self):
        if self.controller and self.controller.is_connected:
            self.controller.lock_screen()

    def on_send_text(self):
        text = self.txt_input.text()
        if text:
            if self.controller and self.controller.is_connected:
                self.controller.type_text(text)
            else:
                pyautogui.write(text)
            self.txt_input.clear()
