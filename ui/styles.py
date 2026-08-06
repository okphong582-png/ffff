DARK_THEME_QSS = """
QMainWindow {
    background-color: #121214;
    color: #E1E1E6;
}

QWidget {
    font-family: "Segoe UI", Roboto, Arial, sans-serif;
    font-size: 13px;
    color: #E1E1E6;
}

QToolBar {
    background-color: #1A1A1E;
    border-bottom: 1px solid #29292E;
    spacing: 8px;
    padding: 6px;
}

QPushButton {
    background-color: #202024;
    border: 1px solid #323238;
    border-radius: 6px;
    padding: 6px 12px;
    color: #E1E1E6;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #29292E;
    border-color: #48484E;
}

QPushButton:pressed {
    background-color: #00875F;
    border-color: #00B37E;
    color: #FFFFFF;
}

QPushButton#btn_accent {
    background-color: #00875F;
    border: 1px solid #00B37E;
    color: #FFFFFF;
}

QPushButton#btn_accent:hover {
    background-color: #00B37E;
}

QFrame#device_card {
    background-color: #1A1A1E;
    border: 1px solid #29292E;
    border-radius: 10px;
}

QLabel#status_label {
    color: #8D8D99;
    font-size: 12px;
}

QLineEdit {
    background-color: #121214;
    border: 1px solid #323238;
    border-radius: 4px;
    padding: 6px;
    color: #E1E1E6;
}

QStatusBar {
    background-color: #1A1A1E;
    color: #8D8D99;
    border-top: 1px solid #29292E;
}
"""
