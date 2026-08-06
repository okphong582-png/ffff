import sys
import logging
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("iOS Box Phone Control PC")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
