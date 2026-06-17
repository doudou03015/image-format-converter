"""Simple light and dark themes."""

from __future__ import annotations


LIGHT_THEME = """
QWidget {
    background: #f5f7fb;
    color: #1f2937;
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog {
    background: #eef2f8;
}
QGroupBox {
    border: 1px solid #d7deea;
    border-radius: 10px;
    margin-top: 14px;
    padding: 12px;
    background: #ffffff;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QListWidget, QPlainTextEdit, QLabel#PreviewFrame, QLineEdit, QComboBox, QSpinBox {
    background: #ffffff;
    border: 1px solid #d7deea;
    border-radius: 8px;
    padding: 6px;
}
QListWidget::item:selected {
    background: #dbeafe;
    color: #0f172a;
}
QPushButton {
    background: #1d4ed8;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #1e40af;
}
QPushButton:disabled {
    background: #93a4c4;
}
QPushButton[secondary="true"] {
    background: #ffffff;
    color: #1d4ed8;
    border: 1px solid #bfd0ff;
}
QPushButton[secondary="true"]:hover {
    background: #eff6ff;
}
QProgressBar {
    border: 1px solid #d7deea;
    border-radius: 7px;
    background: #ffffff;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 6px;
    background: #16a34a;
}
QTabWidget::pane {
    border: 1px solid #d7deea;
    border-radius: 10px;
    background: #ffffff;
}
QTabBar::tab {
    background: #e7edf7;
    border: 1px solid #d7deea;
    padding: 8px 14px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #ffffff;
}
"""


DARK_THEME = """
QWidget {
    background: #0f172a;
    color: #e5e7eb;
    font-family: "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog {
    background: #0b1220;
}
QGroupBox {
    border: 1px solid #334155;
    border-radius: 10px;
    margin-top: 14px;
    padding: 12px;
    background: #111827;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}
QListWidget, QPlainTextEdit, QLabel#PreviewFrame, QLineEdit, QComboBox, QSpinBox {
    background: #111827;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px;
}
QListWidget::item:selected {
    background: #1e3a8a;
}
QPushButton {
    background: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background: #1d4ed8;
}
QPushButton:disabled {
    background: #475569;
}
QPushButton[secondary="true"] {
    background: #111827;
    color: #bfdbfe;
    border: 1px solid #3b82f6;
}
QPushButton[secondary="true"]:hover {
    background: #172554;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 7px;
    background: #111827;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 6px;
    background: #22c55e;
}
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 10px;
    background: #111827;
}
QTabBar::tab {
    background: #1e293b;
    border: 1px solid #334155;
    padding: 8px 14px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #111827;
}
"""


def get_stylesheet(theme: str) -> str:
    """Return the stylesheet for the requested theme."""

    return DARK_THEME if theme == "dark" else LIGHT_THEME
