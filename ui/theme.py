from __future__ import annotations
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication


def apply_dark_palette(app: QApplication) -> None:
    """Force a dark palette onto the entire application."""
    app.setStyle("Fusion")

    p = QPalette()

    # Base surfaces
    p.setColor(QPalette.Window,          QColor("#1e1e1e"))
    p.setColor(QPalette.WindowText,      QColor("#e8e8e8"))
    p.setColor(QPalette.Base,            QColor("#252525"))
    p.setColor(QPalette.AlternateBase,   QColor("#1a1a1a"))
    p.setColor(QPalette.ToolTipBase,     QColor("#2a2a2a"))
    p.setColor(QPalette.ToolTipText,     QColor("#e8e8e8"))

    # Text
    p.setColor(QPalette.Text,            QColor("#e8e8e8"))
    p.setColor(QPalette.BrightText,      QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, QColor("#666666"))

    # Buttons
    p.setColor(QPalette.Button,          QColor("#2a2a2a"))
    p.setColor(QPalette.ButtonText,      QColor("#e8e8e8"))

    # Borders / separators
    p.setColor(QPalette.Mid,             QColor("#333333"))
    p.setColor(QPalette.Dark,            QColor("#141414"))
    p.setColor(QPalette.Shadow,          QColor("#0a0a0a"))
    p.setColor(QPalette.Light,           QColor("#3a3a3a"))
    p.setColor(QPalette.Midlight,        QColor("#2e2e2e"))

    # Selection
    p.setColor(QPalette.Highlight,       QColor("#534AB7"))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))

    # Links
    p.setColor(QPalette.Link,            QColor("#7B74D4"))
    p.setColor(QPalette.LinkVisited,     QColor("#9B94E4"))

    # Disabled state -- mute everything
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor("#555555"))

    app.setPalette(p)
