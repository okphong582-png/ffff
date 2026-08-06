import time
import logging
import requests
import numpy as np
import cv2
import win32gui
import win32ui
import win32con
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

logger = logging.getLogger("StreamReceiver")

class StreamReceiverThread(QThread):
    """
    Receives and decodes live screen frames from 3uTools Mirror Engine or WDA Stream.
    Converts raw frames into PySide6 QImage and emits them for display at 60 FPS.
    """
    frame_ready = Signal(QImage, int, int) # QImage frame, width, height
    fps_updated = Signal(float)            # Stream FPS count
    connection_lost = Signal(str)          # Error message

    def __init__(self, stream_url: str = "http://localhost:9200", fallback_url: str = "http://localhost:8200/mjpegfeed", parent=None):
        super().__init__(parent)
        self.stream_url = stream_url
        self.fallback_url = fallback_url
        self._running = True
        self.current_fps = 0.0

    def stop(self):
        self._running = False

    def run(self):
        logger.info("StreamReceiver started.")

        # Attempt 1: 3uTools Real-time Screen Mirror Engine (Best for iOS 18)
        if self._run_3utools_capture():
            return

        # Attempt 2: WDA Stream HTTP Fallback
        self._run_wda_stream()

    def _run_3utools_capture(self) -> bool:
        """Captures 3uTools Real-time Screen window in real time."""
        hwnd = self._find_3utools_window()
        if not hwnd:
            return False

        logger.info(f"Found 3uTools Real-time Screen window handle: HWND {hwnd}")
        frame_count = 0
        last_fps_time = time.time()

        while self._running:
            try:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]

                if w <= 10 or h <= 10:
                    time.sleep(0.1)
                    continue

                hwndDC = win32gui.GetWindowDC(hwnd)
                mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
                saveDC = mfcDC.CreateCompatibleDC()

                saveBitMap = win32ui.CreateBitmap()
                saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
                saveDC.SelectObject(saveBitMap)

                saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)

                bmpstr = saveBitMap.GetBitmapBits(True)
                img = np.frombuffer(bmpstr, dtype=np.uint8)
                img.shape = (h, w, 4)

                win32gui.DeleteObject(saveBitMap.GetHandle())
                saveDC.DeleteDC()
                mfcDC.DeleteDC()
                win32gui.ReleaseDC(hwnd, hwndDC)

                # Convert BGRA to RGB
                frame_rgb = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
                bytes_per_line = 3 * w
                q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

                self.frame_ready.emit(q_img, w, h)

                frame_count += 1
                now = time.time()
                elapsed = now - last_fps_time
                if elapsed >= 1.0:
                    self.current_fps = frame_count / elapsed
                    self.fps_updated.emit(self.current_fps)
                    frame_count = 0
                    last_fps_time = now

                time.sleep(0.02) # ~50 FPS

            except Exception as e:
                logger.error(f"3uTools capture exception: {e}")
                time.sleep(0.1)
                break

        return True

    def _find_3utools_window(self):
        hwnd = None
        def enum_cb(h, _):
            nonlocal hwnd
            txt = win32gui.GetWindowText(h)
            if "real-time screen" in txt.lower() or "3uairplayer" in txt.lower():
                hwnd = h
        win32gui.EnumWindows(enum_cb, None)
        return hwnd

    def _run_wda_stream(self):
        target_url = self.stream_url
        session = requests.Session()
        resp = self._connect_stream(session, target_url)

        if not resp:
            target_url = self.fallback_url
            resp = self._connect_stream(session, target_url)

        if not resp or resp.status_code != 200:
            self.connection_lost.emit("Không tìm thấy luồng màn hình 3uTools hoặc WDA")
            return

        bytes_buffer = b""
        frame_count = 0
        last_fps_time = time.time()

        try:
            for chunk in resp.iter_content(chunk_size=4096):
                if not self._running or not chunk:
                    continue

                bytes_buffer += chunk
                a = bytes_buffer.find(b'\xff\xd8')
                b = bytes_buffer.find(b'\xff\xd9')

                if a != -1 and b != -1 and a < b:
                    jpg_data = bytes_buffer[a:b+2]
                    bytes_buffer = bytes_buffer[b+2:]

                    nparr = np.frombuffer(jpg_data, dtype=np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if frame is not None:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = frame_rgb.shape
                        q_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
                        self.frame_ready.emit(q_img, w, h)

                        frame_count += 1
                        now = time.time()
                        if now - last_fps_time >= 1.0:
                            self.current_fps = frame_count / (now - last_fps_time)
                            self.fps_updated.emit(self.current_fps)
                            frame_count = 0
                            last_fps_time = now

        except Exception as e:
            self.connection_lost.emit(f"Lỗi luồng: {e}")
        finally:
            if resp:
                resp.close()
            session.close()

    def _connect_stream(self, session, url):
        try:
            return session.get(url, stream=True, timeout=3.0)
        except Exception:
            return None
