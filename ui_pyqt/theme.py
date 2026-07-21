"""Visual tokens and stylesheet for the PyQt6 interface."""

LIGHT_STYLESHEET = """
QWidget {
    color: #243447;
    font-family: "Rubik", "Inter", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QWidget#appRoot { background: #f4f7fb; }
QFrame#sidebar { background: #ffffff; border-right: 1px solid #dce4ee; }
QFrame#header, QFrame#consoleCard, QFrame[card="true"] {
    background: #ffffff;
    border: 1px solid #dde6f0;
    border-radius: 14px;
}
QLabel#brandMark {
    color: #16a34a;
    font-size: 23px;
    font-weight: 800;
    letter-spacing: 2px;
}
QLabel#brandCaption, QLabel[muted="true"] { color: #6f8093; }
QLabel#pageTitle, QLabel#page_title { color: #172536; font-size: 24px; font-weight: 750; }
QLabel#sectionTitle, QLabel#consoleTitle, QLabel#workspaceTitle,
QLabel#treeTitle, QLabel#contextTitle, QLabel#importTitle, QLabel#entryTitle,
QLabel#listTitle, QLabel#actionTitle, QLabel#resultsTitle, QLabel#generalTitle,
QLabel#modelTitle { color: #1c2d40; font-size: 16px; font-weight: 650; }
QLabel#metricValue { color: #16a34a; font-size: 18px; font-weight: 750; }
QPushButton {
    color: #294057;
    background: #f8fafc;
    border: 1px solid #ccd8e5;
    border-radius: 9px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover { background: #eef4f8; border-color: #9cb2c7; }
QPushButton:pressed { background: #e3ebf3; }
QPushButton:disabled { color: #9aa9b8; background: #f1f4f7; }
QPushButton[primary="true"] {
    color: #ffffff;
    background: #16a34a;
    border-color: #16a34a;
}
QPushButton[primary="true"]:hover { background: #15803d; border-color: #15803d; }
QPushButton#info_button {
    color: #6f8093;
    background: transparent;
    border: 1px solid #dce4ee;
    border-radius: 7px;
    padding: 0px;
    font-size: 15px;
    font-weight: 700;
}
QPushButton#info_button:hover { color: #243447; background: #f0f4f8; border-color: #b8c6d4; }
QPushButton[nav="true"] {
    color: #64778b;
    background: transparent;
    border: 0;
    border-radius: 9px;
    padding: 11px 13px;
    text-align: left;
}
QPushButton[nav="true"]:hover { color: #1e384e; background: #edf4f6; }
QPushButton[nav="true"]:checked {
    color: #14532d;
    background: #dcfce7;
    border-left: 3px solid #16a34a;
}
QLineEdit, QComboBox, QTextEdit, QTextBrowser, QPlainTextEdit, QListWidget, QTreeWidget, QTableWidget {
    color: #243447;
    background: #ffffff;
    border: 1px solid #cfdbe7;
    border-radius: 9px;
    padding: 7px;
    selection-color: #ffffff;
    selection-background-color: #16a34a;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus,
QListWidget:focus, QTreeWidget:focus, QTableWidget:focus { border-color: #16a34a; }
QComboBox::drop-down { border: 0; width: 26px; }
QComboBox QAbstractItemView { background: #ffffff; border: 1px solid #c7d5e3; }
QHeaderView::section {
    color: #52677c;
    background: #edf3f8;
    border: 0;
    border-bottom: 1px solid #d5e0ea;
    padding: 8px;
    font-weight: 650;
}
QTreeWidget, QTableWidget { alternate-background-color: #f7f9fc; }
QTreeWidget::item, QListWidget::item { padding: 5px; }
QTreeWidget::item:hover, QListWidget::item:hover { background: #eaf3f4; }
QTreeWidget::item:selected, QListWidget::item:selected { color: #ffffff; background: #16a34a; }
QTabWidget::pane { border: 0; }
QGroupBox {
    border: 1px solid #d5e0ea;
    border-radius: 11px;
    margin-top: 13px;
    padding-top: 13px;
    font-weight: 650;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #52677c; }
QCheckBox, QRadioButton { spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 17px; height: 17px; }
QProgressBar {
    background: #e6edf3;
    border: 1px solid #cbd8e4;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk { background: #16a34a; border-radius: 4px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #b8c6d4; border-radius: 5px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #d9e3ec; width: 2px; }
QToolTip { color: #243447; background: #ffffff; border: 1px solid #b8c8d8; }
QStatusBar { background: #f4f7fb; color: #6f8093; border-top: 1px solid #dce4ee; }
QDialog, QMessageBox, QFileDialog { background: #ffffff; }
QPushButton[landing="true"] {
    color: #294057;
    background: #ffffff;
    border: 2px solid #dde6f0;
    border-radius: 14px;
    padding: 22px 20px;
    font-size: 15px;
    font-weight: 650;
    text-align: left;
}
QPushButton[landing="true"]:hover { background: #dcfce7; border-color: #16a34a; }
QPushButton[landing="true"]:pressed { background: #bbf7d0; }
QPushButton[landing="true"]:pressed { background: #bbf7d0; }
QPushButton[landing="true"][primary="true"] {
    color: #ffffff;
    background: #16a34a;
    border-color: #16a34a;
}
QPushButton[landing="true"][primary="true"]:hover { background: #15803d; border-color: #15803d; }
"""

DARK_STYLESHEET = """
QWidget {
    color: #dbe7f4;
    font-family: "Rubik", "Inter", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QWidget#appRoot { background: #08111f; }
QFrame#sidebar { background: #0b1728; border-right: 1px solid #1d2d43; }
QFrame#header, QFrame#consoleCard, QFrame[card="true"] {
    background: #0f1c2e;
    border: 1px solid #20324a;
    border-radius: 14px;
}
QLabel#brandMark {
    color: #63e6be;
    font-size: 23px;
    font-weight: 800;
    letter-spacing: 2px;
}
QLabel#brandCaption, QLabel[muted="true"], QLabel#workspacePathLabel { color: #7f93aa; }
QLabel#pageTitle, QLabel#page_title { color: #f5f9ff; font-size: 24px; font-weight: 750; }
QLabel#sectionTitle, QLabel#consoleTitle, QLabel#workspaceTitle,
QLabel#treeTitle, QLabel#contextTitle, QLabel#importTitle, QLabel#entryTitle,
QLabel#listTitle, QLabel#actionTitle, QLabel#resultsTitle, QLabel#generalTitle,
QLabel#modelTitle { color: #eef6ff; font-size: 16px; font-weight: 650; }
QLabel#metricValue { color: #63e6be; font-size: 18px; font-weight: 750; }
QPushButton {
    background: #17283e;
    border: 1px solid #2a405c;
    border-radius: 9px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover { background: #203754; border-color: #436280; }
QPushButton:pressed { background: #132337; }
QPushButton:disabled { color: #586b80; background: #111d2d; }
QPushButton[primary="true"] {
    color: #06131b;
    background: #63e6be;
    border-color: #63e6be;
}
QPushButton[primary="true"]:hover { background: #7cebc9; }
QPushButton#info_button {
    color: #7f93aa;
    background: transparent;
    border: 1px solid #20324a;
    border-radius: 7px;
    padding: 0px;
    font-size: 15px;
    font-weight: 700;
}
QPushButton#info_button:hover { color: #dbe7f4; background: #162030; border-color: #304a60; }
QPushButton[nav="true"] {
    color: #91a5bb;
    background: transparent;
    border: 0;
    border-radius: 9px;
    padding: 11px 13px;
    text-align: left;
}
QPushButton[nav="true"]:hover { color: #dce9f7; background: #13243a; }
QPushButton[nav="true"]:checked {
    color: #ecfffa;
    background: #153a3c;
    border-left: 3px solid #63e6be;
}
QLineEdit, QComboBox, QTextEdit, QTextBrowser, QPlainTextEdit, QListWidget, QTreeWidget, QTableWidget {
    color: #dce8f5;
    background: #0a1525;
    border: 1px solid #263a53;
    border-radius: 9px;
    padding: 7px;
    selection-background-color: #21615b;
}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QListWidget:focus,
QTreeWidget:focus, QTableWidget:focus { border-color: #57cdb0; }
QComboBox::drop-down { border: 0; width: 26px; }
QComboBox QAbstractItemView { background: #101e31; border: 1px solid #2a405c; }
QHeaderView::section {
    color: #91a6bc;
    background: #102035;
    border: 0;
    border-bottom: 1px solid #29405b;
    padding: 8px;
    font-weight: 650;
}
QTreeWidget, QTableWidget { alternate-background-color: #0d1a2b; }
QTreeWidget::item, QListWidget::item { padding: 5px; }
QTreeWidget::item:hover, QListWidget::item:hover { background: #142a42; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #1d4b4a; }
QTabWidget::pane { border: 0; }
QTabBar { background: transparent; }
QTabBar::tab {
    color: #7f93aa;
    background: transparent;
    border: 1px solid #20324a;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 2px;
}
QTabBar::tab:selected { color: #dbe7f4; background: #0f1c2e; border-color: #20324a; }
QTabBar::tab:hover:!selected { color: #dbe7f4; background: #162030; }
QGroupBox {
    border: 1px solid #243850;
    border-radius: 11px;
    margin-top: 13px;
    padding-top: 13px;
    font-weight: 650;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #a9bdd2; }
QCheckBox, QRadioButton { spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 17px; height: 17px; }
QProgressBar {
    background: #111f31;
    border: 1px solid #263a53;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk { background: #63e6be; border-radius: 4px; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #304660; border-radius: 5px; min-height: 25px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #182a40; width: 2px; }
QToolTip { color: #e9f3fe; background: #17283e; border: 1px solid #3b5673; }
QStatusBar { background: #08111f; color: #7f93aa; border-top: 1px solid #1d2d43; }
QDialog, QMessageBox, QFileDialog { background: #0f1c2e; }
QPushButton[landing="true"] {
    color: #dbe7f4;
    background: #0f1c2e;
    border: 2px solid #20324a;
    border-radius: 14px;
    padding: 22px 20px;
    font-size: 15px;
    font-weight: 650;
    text-align: left;
}
QPushButton[landing="true"]:hover { background: #153a3c; border-color: #63e6be; }
QPushButton[landing="true"]:pressed { background: #0d2e2f; }
QPushButton[landing="true"][primary="true"] {
    color: #06131b;
    background: #63e6be;
    border-color: #63e6be;
}
QPushButton[landing="true"][primary="true"]:hover { background: #7cebc9; border-color: #7cebc9; }
"""

# Kept as the public default for callers that imported this constant previously.
APP_STYLESHEET = LIGHT_STYLESHEET
