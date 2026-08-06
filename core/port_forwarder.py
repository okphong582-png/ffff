import subprocess
import socket
import logging
import time
from typing import Optional

logger = logging.getLogger("PortForwarder")

class PortForwarder:
    """
    Manages local USB port forwarding from PC to connected iOS devices over usbmuxd.
    Local ports (e.g. 8200, 9200) forward to iOS device WDA ports (8100, 9100).
    """
    def __init__(self, udid: str, wda_port: int = 8200, mjpeg_port: int = 9200):
        self.udid = udid
        self.wda_port = wda_port        # Local PC port for WDA (e.g. 8200)
        self.mjpeg_port = mjpeg_port    # Local PC port for MJPEG Stream (e.g. 9200)
        self.remote_wda_port = 8100     # iOS Device WDA Port
        self.remote_mjpeg_port = 9100   # iOS Device MJPEG Port
        self.procs = []
        self._is_active = False

    def is_port_in_use(self, port: int) -> bool:
        """Checks if a local TCP port is currently open/listening."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0

    def start_forwarding(self) -> bool:
        """
        Starts forwarding local ports to iOS device WDA ports.
        """
        logger.info(f"Starting port forward for device {self.udid}: local ports ({self.wda_port}->{self.remote_wda_port}, {self.mjpeg_port}->{self.remote_mjpeg_port})")

        # 1. Try iproxy
        success = self._start_iproxy()
        if not success:
            # 2. Try pymobiledevice3 forward
            success = self._start_pymd3_forward()
        if not success:
            # 3. Try tidevice wdaproxy
            success = self._start_tidevice_wdaproxy()

        self._is_active = success
        return success

    def _start_iproxy(self) -> bool:
        try:
            # iproxy <local_port> <remote_port> -u <udid>
            cmd1 = ["iproxy", str(self.wda_port), str(self.remote_wda_port), "-u", self.udid]
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p1)

            cmd2 = ["iproxy", str(self.mjpeg_port), str(self.remote_mjpeg_port), "-u", self.udid]
            p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p2)

            time.sleep(1.0)
            logger.info("iproxy processes started successfully.")
            return True
        except Exception as e:
            logger.warning(f"iproxy notice: {e}")
            return False

    def _start_pymd3_forward(self) -> bool:
        try:
            # pymobiledevice3 usbmux forward <local_port> <remote_port> --udid <udid>
            cmd1 = ["python", "-m", "pymobiledevice3", "usbmux", "forward", str(self.wda_port), str(self.remote_wda_port), "--udid", self.udid]
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p1)

            cmd2 = ["python", "-m", "pymobiledevice3", "usbmux", "forward", str(self.mjpeg_port), str(self.remote_mjpeg_port), "--udid", self.udid]
            p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p2)

            time.sleep(1.0)
            logger.info("pymobiledevice3 forward processes started successfully.")
            return True
        except Exception as e:
            logger.warning(f"pymobiledevice3 forward notice: {e}")
            return False

    def _start_tidevice_wdaproxy(self) -> bool:
        try:
            cmd = ["python", "-m", "tidevice", "-u", self.udid, "relay", str(self.wda_port), str(self.remote_wda_port)]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.procs.append(p)
            time.sleep(1.0)
            logger.info("tidevice relay process started successfully.")
            return True
        except Exception as e:
            logger.warning(f"tidevice relay notice: {e}")
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
