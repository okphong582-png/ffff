import asyncio
import socket
import logging
import threading
import time
from pymobiledevice3.tcp_forwarder import UsbmuxTcpForwarder

logger = logging.getLogger("PortForwarder")

def find_free_port(start_port: int) -> int:
    """Finds an available local TCP port starting from start_port."""
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    return start_port

class PortForwarder:
    """
    Native Python USB TCP Port Forwarder using pymobiledevice3.
    Bridges local PC ports dynamically to connected iOS device WDA ports (8100, 9100).
    """
    def __init__(self, udid: str, preferred_wda_port: int = 8200, preferred_mjpeg_port: int = 9200):
        self.udid = udid
        self.wda_port = find_free_port(preferred_wda_port)
        self.mjpeg_port = find_free_port(preferred_mjpeg_port)
        self.remote_wda_port = 8100
        self.remote_mjpeg_port = 9100

        self.wda_forwarder = None
        self.mjpeg_forwarder = None
        self.loop = None
        self.thread = None
        self._is_active = False

    def start_forwarding(self) -> bool:
        """Starts background thread with native UsbmuxTcpForwarder instances."""
        logger.info(f"Starting native UsbmuxTcpForwarder for device {self.udid}: local ({self.wda_port}->{self.remote_wda_port}, {self.mjpeg_port}->{self.remote_mjpeg_port})")

        # Try launching tunneld for iOS 17/18 CoreDevice support
        try:
            cmd = ["python", "-m", "pymobiledevice3", "remote", "tunneld"]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.tunnel_proc = p
            time.sleep(1.0)
            logger.info("iOS 17/18 Tunneld process initiated.")
        except Exception as e:
            logger.debug(f"Tunneld launch notice: {e}")

        try:
            self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self.thread.start()
            time.sleep(0.8)
            self._is_active = True
            return True
        except Exception as e:
            logger.error(f"Error starting UsbmuxTcpForwarder: {e}")
            self._is_active = False
            return False

    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            # Correct signature: (serial, dst_port, src_port)
            self.wda_forwarder = UsbmuxTcpForwarder(self.udid, dst_port=self.remote_wda_port, src_port=self.wda_port)
            self.mjpeg_forwarder = UsbmuxTcpForwarder(self.udid, dst_port=self.remote_mjpeg_port, src_port=self.mjpeg_port)

            self.loop.create_task(self.wda_forwarder.start())
            self.loop.create_task(self.mjpeg_forwarder.start())

            logger.info(f"Native TCP forwarders active: PC:{self.wda_port}->iOS:{self.remote_wda_port} and PC:{self.mjpeg_port}->iOS:{self.remote_mjpeg_port}")
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Forwarder loop error: {e}")

    def stop_forwarding(self):
        """Cleanly stops the async loop and forwarders."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self._is_active = False
        logger.info(f"Native Port forwarding stopped for device {self.udid}")
