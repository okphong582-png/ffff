import time
import logging
from PySide6.QtCore import QThread, Signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("USBMuxMonitor")

class USBMuxMonitorThread(QThread):
    """
    Background worker thread monitoring iOS device connections over USB Lightning.
    Emits signals when a new device is connected or an existing device is disconnected.
    """
    device_connected = Signal(dict)       # Emits device info dict: {'udid': ..., 'name': ..., 'model': ...}
    device_disconnected = Signal(str)     # Emits device UDID
    status_changed = Signal(str)          # Emits status message for UI logging

    def __init__(self, poll_interval=2.0, parent=None):
        super().__init__(parent)
        self.poll_interval = poll_interval
        self._running = True
        self.known_devices = {}  # udid -> device_info

    def stop(self):
        self._running = False

    def run(self):
        self.status_changed.emit("Đang khởi chạy bộ theo dõi kết nối USB Lightning...")
        logger.info("USBMuxMonitor started.")

        while self._running:
            try:
                current_devices = self._fetch_connected_devices()
                current_udids = set(current_devices.keys())
                known_udids = set(self.known_devices.keys())

                # New devices connected
                new_udids = current_udids - known_udids
                for udid in new_udids:
                    dev_info = current_devices[udid]
                    self.known_devices[udid] = dev_info
                    logger.info(f"New iPhone connected over USB: {udid} ({dev_info.get('name', 'iPhone')})")
                    self.device_connected.emit(dev_info)

                # Devices disconnected
                removed_udids = known_udids - current_udids
                for udid in removed_udids:
                    logger.info(f"iPhone disconnected: {udid}")
                    del self.known_devices[udid]
                    self.device_disconnected.emit(udid)

            except Exception as e:
                logger.error(f"Error monitoring USB devices: {e}")
                self.status_changed.emit(f"Lỗi đọc USBMux: {e}")

            time.sleep(self.poll_interval)

    def _fetch_connected_devices(self) -> dict:
        """
        Retrieves current connected devices using pymobiledevice3 if available,
        falling back to USBMux / iTunes service enumeration.
        """
        devices = {}
        
        # Strategy 1: Attempt using pymobiledevice3
        try:
            from pymobiledevice3.usbmux import list_devices as pymd3_list
            import asyncio
            
            # Run async call synchronously in thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            pymd3_devs = loop.run_until_complete(pymd3_list())
            loop.close()

            for dev in pymd3_devs:
                udid = getattr(dev, 'serial', None) or getattr(dev, 'udid', str(dev))
                devices[udid] = {
                    'udid': udid,
                    'connection_type': getattr(dev, 'connection_type', 'USB'),
                    'name': f"iPhone ({udid[:8]}...)",
                    'raw': dev
                }
            return devices
        except Exception as e:
            logger.debug(f"pymobiledevice3 fetch notice: {e}")

        # Strategy 2: Fallback to usbmuxd query or mock/subprocess checks
        try:
            import subprocess
            output = subprocess.check_output(['python', '-m', 'pymobiledevice3', 'usbmux', 'list'], stderr=subprocess.DEVNULL)
            lines = output.decode('utf-8', errors='ignore').splitlines()
            for line in lines:
                if 'Serial' in line or 'UDID' in line or 'usbmux' in line:
                    parts = line.split()
                    for p in parts:
                        if len(p) >= 24: # Typical UDID length
                            devices[p] = {
                                'udid': p,
                                'connection_type': 'USB',
                                'name': f"iPhone ({p[:8]}...)"
                            }
        except Exception as e:
            logger.debug(f"Subprocess fallback notice: {e}")

        return devices
