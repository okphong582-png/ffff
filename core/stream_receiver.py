import time
import logging
import requests
import numpy as np
import cv2
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

logger = logging.getLogger("StreamReceiver")

class StreamReceiverThread(QThread):
    """
    Receives and decodes live screen frames from iOS WebDriverAgent (MJPEG stream or fallback).
    Converts raw frames into PySide6 QImage and emits them for display.
    """
    frame_ready = Signal(QImage, int, int) # QImage frame, width, height
    fps_updated = Signal(float)            # Stream FPS count
    connection_lost = Signal(str)          # Error message

    def __init__(self, stream_url: str = "http://localhost:9100", fallback_url: str = "http://localhost:8100/mjpegfeed", parent=None):
        super().__init__(parent)
        self.stream_url = stream_url
        self.fallback_url = fallback_url
        self._running = True
        self.current_fps = 0.0

    def stop(self):
        self._running = False

    def run(self):
        logger.info(f"StreamReceiver connecting to: {self.stream_url}")
        
        target_url = self.stream_url
        session = requests.Session()
        
        # Try primary MJPEG stream
        resp = self._connect_stream(session, target_url)
        if not resp:
            logger.warning(f"Primary stream failed. Trying fallback URL: {self.fallback_url}")
            target_url = self.fallback_url
            resp = self._connect_stream(session, target_url)

        if not resp or resp.status_code != 200:
            logger.error(f"Cannot connect to iOS MJPEG screen stream at {target_url}")
            self.connection_lost.emit(f"Không thể kết nối luồng màn hình tại {target_url}")
            return

        bytes_buffer = b""
        frame_count = 0
        last_fps_time = time.time()

        try:
            for chunk in resp.iter_content(chunk_size=4096):
                if not self._running:
                    break

                if not chunk:
                    continue

                bytes_buffer += chunk

                # Search for JPEG start (0xFF 0xD8) and end (0xFF 0xD9) flags
                a = bytes_buffer.find(b'\xff\xd8')
                b = bytes_buffer.find(b'\xff\xd9')

                if a != -1 and b != -1 and a < b:
                    jpg_data = bytes_buffer[a:b+2]
                    bytes_buffer = bytes_buffer[b+2:]

                    # Decode JPEG image buffer with OpenCV
                    nparr = np.frombuffer(jpg_data, dtype=np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if frame is not None:
                        # Convert BGR (OpenCV format) to RGB (Qt format)
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = frame_rgb.shape
                        bytes_per_line = ch * w

                        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
                        
                        # Emit frame to UI canvas
                        self.frame_ready.emit(q_img, w, h)

                        # Calculate FPS
                        frame_count += 1
                        now = time.time()
                        elapsed = now - last_fps_time
                        if elapsed >= 1.0:
                            self.current_fps = frame_count / elapsed
                            self.fps_updated.emit(self.current_fps)
                            frame_count = 0
                            last_fps_time = now

        except Exception as e:
            logger.error(f"Stream receiver exception: {e}")
            self.connection_lost.emit(f"Lỗi luồng màn hình: {e}")
        finally:
            resp.close()
            session.close()

    def _connect_stream(self, session: requests.Session, url: str):
        try:
            resp = session.get(url, stream=True, timeout=5.0)
            return resp
        except Exception as e:
            logger.debug(f"Connection error to {url}: {e}")
            return None
