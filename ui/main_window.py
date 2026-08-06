import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QScrollArea, QToolBar, QStatusBar,
    QSpinBox, QMessageBox, QDialog, QTextEdit
)

from core.usbmux_monitor import USBMuxMonitorThread
from ui.device_widget import DeviceWidget
from ui.styles import DARK_THEME_QSS

logger = logging.getLogger("MainWindow")

class MainWindow(QMainWindow):
    """
    Main Box Phone Control Center Window.
    Manages USB device auto-detection, device grid layout, and global controls.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iOS Box Phone PC Mirror & Touch Control")
        self.resize(1100, 800)
        self.setStyleSheet(DARK_THEME_QSS)

        self.device_widgets = {}  # udid -> DeviceWidget instance
        self.next_wda_port = 8100
        self.next_mjpeg_port = 9100

        self.init_ui()
        self.init_monitor()

    def init_ui(self):
        # Top Toolbar
        toolbar = QToolBar("Main Controls")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        lbl_app_title = QLabel("⚡ iOS Box Phone Manager ")
        lbl_app_title.setStyleSheet("font-weight: bold; font-size: 15px; color: #00B37E;")
        toolbar.addWidget(lbl_app_title)

        toolbar.addSeparator()

        btn_manual_add = QPushButton("➕ Thêm iPhone (Thủ công)")
        btn_manual_add.clicked.connect(self.on_manual_add)
        toolbar.addWidget(btn_manual_add)

        toolbar.addSeparator()

        lbl_cols = QLabel("Cột hiển thị:")
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 6)
        self.spin_cols.setValue(2)
        self.spin_cols.valueChanged.connect(self.rearrange_grid)

        toolbar.addWidget(lbl_cols)
        toolbar.addWidget(self.spin_cols)

        toolbar.addSeparator()

        btn_help = QPushButton("❓ Hướng dẫn Cài đặt")
        btn_help.clicked.connect(self.show_help_dialog)
        toolbar.addWidget(btn_help)

        # Central Area (Scrollable Grid)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none; background-color: #121214;")

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(15, 15, 15, 15)
        self.grid_layout.setSpacing(15)

        scroll_area.setWidget(self.grid_container)
        self.setCentralWidget(scroll_area)

        # Empty status placeholder
        self.lbl_empty = QLabel("🔌 Hãy cắm cáp Lightning iPhone vào PC để tự động kết nối và điều khiển màn hình...")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setStyleSheet("color: #8D8D99; font-size: 16px; margin: 40px;")
        self.grid_layout.addWidget(self.lbl_empty, 0, 0)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ứng dụng sẵn sàng. Đang chờ kết nối USB Lightning...")

    def init_monitor(self):
        """Starts background USB Lightning detection thread."""
        self.monitor_thread = USBMuxMonitorThread()
        self.monitor_thread.device_connected.connect(self.on_device_connected)
        self.monitor_thread.device_disconnected.connect(self.on_device_disconnected)
        self.monitor_thread.status_changed.connect(lambda msg: self.status_bar.showMessage(msg))
        self.monitor_thread.start()

    def on_device_connected(self, dev_info: dict):
        udid = dev_info.get('udid')
        name = dev_info.get('name', 'iPhone')

        if udid in self.device_widgets:
            return

        logger.info(f"Adding device UI card for UDID: {udid}")
        self.status_bar.showMessage(f"Đã phát hiện iPhone mới cắm USB: {udid}")

        # Hide empty placeholder label
        self.lbl_empty.hide()

        # Assign unique ports for multi-device box phone setup
        wda_p = self.next_wda_port
        mjpeg_p = self.next_mjpeg_port
        self.next_wda_port += 2
        self.next_mjpeg_port += 2

        dev_widget = DeviceWidget(udid=udid, device_name=name, wda_port=wda_p, mjpeg_port=mjpeg_p)
        self.device_widgets[udid] = dev_widget

        self.rearrange_grid()

    def on_device_disconnected(self, udid: str):
        if udid in self.device_widgets:
            logger.info(f"Removing device UI card for UDID: {udid}")
            self.status_bar.showMessage(f"iPhone đã rút cáp USB: {udid}")

            widget = self.device_widgets.pop(udid)
            widget.stop_device()
            self.grid_layout.removeWidget(widget)
            widget.deleteLater()

            self.rearrange_grid()

            if not self.device_widgets:
                self.lbl_empty.show()

    def rearrange_grid(self):
        """Rearranges connected device cards into a clean multi-column grid."""
        cols = self.spin_cols.value()
        widgets = list(self.device_widgets.values())

        for idx, w in enumerate(widgets):
            row = idx // cols
            col = idx % cols
            self.grid_layout.addWidget(w, row, col)

    def on_manual_add(self):
        """Allows manually adding a device for testing or specific ports."""
        dummy_udid = f"manual_dev_{len(self.device_widgets)+1}"
        dev_info = {
            'udid': dummy_udid,
            'name': f"iPhone test #{len(self.device_widgets)+1}"
        }
        self.on_device_connected(dev_info)

    def show_help_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Hướng dẫn Cài đặt & Chuẩn bị iOS Box Phone")
        dlg.resize(650, 450)
        
        layout = QVBoxLayout(dlg)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setHtml("""
        <h3>📱 Hướng dẫn Kết nối & Điều khiển iPhone trên PC:</h3>
        <ol>
            <li><b>Bước 1: Cài đặt Driver iTunes trên Windows</b><br/>
            Cài đặt <i>iTunes</i> (bản 64-bit chính thức từ Apple hoặc Microsoft Store) để PC có đủ Driver Apple Mobile Device Service (USBMux).</li>
            <br/>
            <li><b>Bước 2: Bật Chế độ Nhà phát triển (Developer Mode) trên iPhone</b><br/>
            Trên iPhone: Vào <i>Cài đặt -> Quyền riêng tư & Bảo mật -> Chế độ Nhà phát triển (Developer Mode)</i> -> Bật và Khởi động lại iPhone.</li>
            <br/>
            <li><b>Bước 3: Cài đặt WebDriverAgent (WDA) lên iPhone</b><br/>
            Cài đặt file <b>WebDriverAgentRunner.ipa</b> lên iPhone (sử dụng AltStore, Sideloadly, 3uTools hoặc Xcode).<br/>
            Khởi chạy WebDriverAgent trên iPhone để kích hoạt cổng 8100 & 9100.</li>
            <br/>
            <li><b>Bước 4: Cắm cáp Lightning USB</b><br/>
            Cắm cáp Lightning kết nối iPhone với máy tính. Ứng dụng Python trên PC sẽ tự động nhận diện thiết bị, mở luồng màn hình và cho phép nhấn chuột / gõ phím để điều khiển!</li>
        </ol>
        """)
        layout.addWidget(txt)
        dlg.exec()

    def closeEvent(self, event):
        """Cleanup on close."""
        self.monitor_thread.stop()
        self.monitor_thread.wait(1000)

        for dev in self.device_widgets.values():
            dev.stop_device()
        super().closeEvent(event)
