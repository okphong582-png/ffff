import subprocess
import socket
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("PortForwarder")

class PortForwarder:
    """
    Manages local USB port forwarding from PC to connected iOS devices over usbmuxd.
    Supports iproxy CLI or pymobiledevice3 tunnel forwarding.
    """
    def __init__(self, udid: str, wda_port: int = 8100, mjpeg_port: int = 9100):
        self.udid = udid
        self.wda_port = wda_port
        self.mjpeg_port = mjpeg_port
        self.procs = []
        self._is_active = False

    def is_port_in_use(self, port: int) -> bool:
        """Checks if a local TCP port is currently open/listening."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def start_forwarding(self) -> bool:
        """
        Starts forwarding local ports for WDA (8100) and MJPEG Stream (9100),
        and automatically launches WDA test runner on iOS device.
        """
        logger.info(f"Starting port forward & WDA launcher for device {self.udid}: local ports {self.wda_port}, {self.mjpeg_port}")

        # Attempt 1: Try using tidevice wdaproxy (Launches WDA app on iPhone + forwards ports automatically)
        success = self._start_tidevice_wdaproxy()
        if not success:
            # Attempt 2: Try iproxy (part of libimobiledevice)
            success = self._start_iproxy()
        if not success:
            # Attempt 3: Try pymobiledevice3 forwarding
            success = self._start_pymd3_forward()

        self._is_active = success
        return success

    def _start_tidevice_wdaproxy(self) -> bool:
        try:
            # tidevice wdaproxy automatically launches WDA app on iOS and forwards port
            cmd = ["python", "-m", "tidevice", "-u", self.udid, "wdaproxy", "-B", "com.facebook.WebDriverAgentRunner.xctrunner", "--port", str(self.wda_port)]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p)
            time.sleep(2.0)
            logger.info("tidevice wdaproxy process started successfully.")
            return True
        except Exception as e:
            logger.warning(f"tidevice wdaproxy launch notice: {e}")
            return False

    def _start_iproxy(self) -> bool:
        try:
            # Launch iproxy for WDA port
            cmd1 = ["iproxy", str(self.wda_port), str(self.wda_port), "-u", self.udid]
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p1)

            # Launch iproxy for MJPEG port
            cmd2 = ["iproxy", str(self.mjpeg_port), str(self.mjpeg_port), "-u", self.udid]
            p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p2)

            time.sleep(1.0)
            logger.info("iproxy processes started.")
            return True
        except FileNotFoundError:
            logger.warning("iproxy executable not found in PATH. Trying fallback...")
            return False
        except Exception as e:
            logger.error(f"Failed starting iproxy: {e}")
            return False

    def _start_pymd3_forward(self) -> bool:
        try:
            cmd1 = ["python", "-m", "pymobiledevice3", "usbmux", "forward", str(self.wda_port), str(self.wda_port), "--udid", self.udid]
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p1)

            cmd2 = ["python", "-m", "pymobiledevice3", "usbmux", "forward", str(self.mjpeg_port), str(self.mjpeg_port), "--udid", self.udid]
            p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p2)

            time.sleep(1.0)
            logger.info("pymobiledevice3 forward processes started.")
            return True
        except Exception as e:
            logger.error(f"Failed pymobiledevice3 forward: {e}")
            return False

    def stop_forwarding(self):
        """Stops all active port forwarding processes."""
        for p in self.procs:
            try:
                p.terminate()
                p.wait(timeout=1.0)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        self.procs.clear()
        self._is_active = False
        logger.info(f"Port forwarding stopped for device {self.udid}")
