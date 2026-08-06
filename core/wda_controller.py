import logging
import time
import requests
import wda
from typing import Optional, Tuple

logger = logging.getLogger("WDAController")

class WDAController:
    """
    Controller bridge handling user touch input, swipes, text typing,
    and physical button events via iOS WebDriverAgent REST API.
    """
    def __init__(self, wda_url: str = "http://localhost:8100"):
        self.wda_url = wda_url
        self.client: Optional[wda.Client] = None
        self.session: Optional[wda.Session] = None
        self.device_width = 0
        self.device_height = 0
        self.is_connected = False

    def connect(self, retries: int = 5, delay: float = 1.0) -> bool:
        """Connects to WebDriverAgent running on iOS device with retries."""
        for attempt in range(retries):
            try:
                logger.info(f"Connecting WDA client at {self.wda_url} (attempt {attempt+1}/{retries})...")
                self.client = wda.Client(self.wda_url)
                
                # Check status
                status = self.client.status()
                logger.info(f"WDA Status: {status}")
                
                # Fetch device screen size
                window_size = self.client.window_size()
                self.device_width = window_size.width
                self.device_height = window_size.height
                logger.info(f"Device Screen Resolution: {self.device_width}x{self.device_height}")

                self.is_connected = True
                return True
            except Exception as e:
                logger.warning(f"WDA connect attempt {attempt+1} failed at {self.wda_url}: {e}")
                time.sleep(delay)

        self.is_connected = False
        return False

    def tap(self, x: int, y: int) -> bool:
        """Performs single tap at iOS screen coordinates (x, y)."""
        if not self.is_connected and not self.connect():
            return False
        try:
            self.client.tap(x, y)
            return True
        except Exception as e:
            logger.error(f"Tap error at ({x}, {y}): {e}")
            return False

    def double_tap(self, x: int, y: int) -> bool:
        """Performs double tap at (x, y)."""
        if not self.is_connected and not self.connect():
            return False
        try:
            self.client.double_tap(x, y)
            return True
        except Exception as e:
            logger.error(f"Double tap error at ({x}, {y}): {e}")
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> bool:
        """Performs swipe gesture from (x1, y1) to (x2, y2)."""
        if not self.is_connected and not self.connect():
            return False
        try:
            self.client.swipe(x1, y1, x2, y2, duration=duration)
            return True
        except Exception as e:
            logger.error(f"Swipe error ({x1},{y1}) -> ({x2},{y2}): {e}")
            return False

    def press_home(self) -> bool:
        """Presses physical Home button / Home indicator gesture."""
        if not self.is_connected and not self.connect():
            return False
        try:
            self.client.home()
            return True
        except Exception as e:
            logger.error(f"Home button error: {e}")
            # Fallback swipe up from bottom
            if self.device_width > 0 and self.device_height > 0:
                mid_x = self.device_width // 2
                return self.swipe(mid_x, self.device_height - 10, mid_x, self.device_height // 2, duration=0.2)
            return False

    def press_app_switcher(self) -> bool:
        """Swipes up and holds to trigger App Switcher."""
        if self.device_width > 0 and self.device_height > 0:
            mid_x = self.device_width // 2
            return self.swipe(mid_x, self.device_height - 10, mid_x, self.device_height // 3, duration=0.8)
        return False

    def type_text(self, text: str) -> bool:
        """Types text into currently active input field on iOS."""
        if not self.is_connected and not self.connect():
            return False
        try:
            self.client.send_keys(text)
            return True
        except Exception as e:
            logger.error(f"Send keys error: {e}")
            return False

    def volume_up(self) -> bool:
        try:
            self.client.press("volumeUp")
            return True
        except Exception:
            return False

    def volume_down(self) -> bool:
        try:
            self.client.press("volumeDown")
            return True
        except Exception:
            return False

    def lock_screen(self) -> bool:
        """Locks or unlocks screen."""
        try:
            self.client.press("power")
            return True
        except Exception:
            return False
