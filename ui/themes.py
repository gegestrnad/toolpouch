from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class ThemeManager:
    DEFAULT_THEME = "Modern Dark"
    LEGACY_THEME_NAMES = {
        "Deep Dark": "Moonlit Slate",
        "Light Classic": "Paper Daylight",
        "Soft Light": "Mist Garden",
        "High Contrast": "Clear Contrast",
    }

    THEMES = {
        "Modern Dark": {
            "window": "#1E1E1E",
            "windowText": "#E0E0E0",
            "base": "#2D2D2D",
            "alternateBase": "#252525",
            "text": "#E0E0E0",
            "placeholderText": "#888888",
            "mid": "#3D3D3D",
            "midlight": "#4D4D4D",
            "dark": "#1A1A1A",
            "light": "#404040",
            "button": "#2D2D2D",
            "buttonText": "#E0E0E0",
            "highlight": "#534AB7",
            "highlightedText": "#FFFFFF",
            "link": "#7B74D4",
            "linkVisited": "#9B94E4",
            "toolTipBase": "#2D2D2D",
            "toolTipText": "#E0E0E0",
            "brightText": "#FFFFFF",
            "shadow": "#101010",
            "disabledText": "#666666",
        },
        "Moonlit Slate": {
            "window": "#20242A",
            "windowText": "#E8EDF2",
            "base": "#2A3038",
            "alternateBase": "#252A31",
            "text": "#E8EDF2",
            "placeholderText": "#9AA6B2",
            "mid": "#3A424C",
            "midlight": "#4A5460",
            "dark": "#171B20",
            "light": "#56616D",
            "button": "#2A3038",
            "buttonText": "#E8EDF2",
            "highlight": "#4F7CAC",
            "highlightedText": "#FFFFFF",
            "link": "#72A7D8",
            "linkVisited": "#9CBFE0",
            "toolTipBase": "#2A3038",
            "toolTipText": "#E8EDF2",
            "brightText": "#FFFFFF",
            "shadow": "#101419",
            "disabledText": "#77828D",
        },
        "Paper Daylight": {
            "window": "#FBFAF7",
            "windowText": "#242424",
            "base": "#FFFFFF",
            "alternateBase": "#F2F0EA",
            "text": "#242424",
            "placeholderText": "#76736D",
            "mid": "#D8D3C8",
            "midlight": "#E8E3D8",
            "dark": "#6A665E",
            "light": "#FFFFFF",
            "button": "#F5F2EA",
            "buttonText": "#242424",
            "highlight": "#2F6F73",
            "highlightedText": "#FFFFFF",
            "link": "#2F6F73",
            "linkVisited": "#5D8A8C",
            "toolTipBase": "#FFFFFF",
            "toolTipText": "#242424",
            "brightText": "#000000",
            "shadow": "#B7B0A3",
            "disabledText": "#8A867D",
        },
        "Mist Garden": {
            "window": "#F4F8F5",
            "windowText": "#233026",
            "base": "#FFFFFF",
            "alternateBase": "#EAF1EC",
            "text": "#233026",
            "placeholderText": "#708076",
            "mid": "#C9D8CE",
            "midlight": "#DDE8E1",
            "dark": "#5E7165",
            "light": "#FFFFFF",
            "button": "#EEF5F0",
            "buttonText": "#233026",
            "highlight": "#5B7F68",
            "highlightedText": "#FFFFFF",
            "link": "#3E7559",
            "linkVisited": "#6A9278",
            "toolTipBase": "#FFFFFF",
            "toolTipText": "#233026",
            "brightText": "#000000",
            "shadow": "#B4C5BA",
            "disabledText": "#7D8D82",
        },
        "Clear Contrast": {
            "window": "#000000",
            "windowText": "#FFFFFF",
            "base": "#1A1A1A",
            "alternateBase": "#0D0D0D",
            "text": "#FFFFFF",
            "placeholderText": "#CCCCCC",
            "mid": "#333333",
            "midlight": "#555555",
            "dark": "#000000",
            "light": "#262626",
            "button": "#1A1A1A",
            "buttonText": "#FFFFFF",
            "highlight": "#00D7FF",
            "highlightedText": "#000000",
            "link": "#66E8FF",
            "linkVisited": "#FF80FF",
            "toolTipBase": "#000000",
            "toolTipText": "#FFFFFF",
            "brightText": "#FFFFFF",
            "shadow": "#000000",
            "disabledText": "#CCCCCC",
        },
    }

    def get_theme_names(self):
        return list(self.THEMES.keys())

    def resolve_theme_name(self, theme_name: str | None) -> str:
        if theme_name in self.LEGACY_THEME_NAMES:
            return self.LEGACY_THEME_NAMES[theme_name]
        if theme_name in self.THEMES:
            return theme_name
        return self.DEFAULT_THEME

    def get_palette(self, theme_name: str) -> QPalette:
        theme_name = self.resolve_theme_name(theme_name)
        theme = self.THEMES[theme_name]
        palette = QPalette()

        palette.setColor(QPalette.Window, QColor(theme["window"]))
        palette.setColor(QPalette.WindowText, QColor(theme["windowText"]))
        palette.setColor(QPalette.Base, QColor(theme["base"]))
        palette.setColor(QPalette.AlternateBase, QColor(theme["alternateBase"]))
        palette.setColor(QPalette.ToolTipBase, QColor(theme["toolTipBase"]))
        palette.setColor(QPalette.ToolTipText, QColor(theme["toolTipText"]))
        palette.setColor(QPalette.Text, QColor(theme["text"]))
        palette.setColor(QPalette.BrightText, QColor(theme["brightText"]))
        palette.setColor(QPalette.PlaceholderText, QColor(theme["placeholderText"]))
        palette.setColor(QPalette.Mid, QColor(theme["mid"]))
        palette.setColor(QPalette.Midlight, QColor(theme["midlight"]))
        palette.setColor(QPalette.Dark, QColor(theme["dark"]))
        palette.setColor(QPalette.Light, QColor(theme["light"]))
        palette.setColor(QPalette.Shadow, QColor(theme["shadow"]))
        palette.setColor(QPalette.Button, QColor(theme["button"]))
        palette.setColor(QPalette.ButtonText, QColor(theme["buttonText"]))
        palette.setColor(QPalette.Highlight, QColor(theme["highlight"]))
        palette.setColor(QPalette.HighlightedText, QColor(theme["highlightedText"]))
        palette.setColor(QPalette.Link, QColor(theme["link"]))
        palette.setColor(QPalette.LinkVisited, QColor(theme["linkVisited"]))

        for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
            palette.setColor(QPalette.Disabled, role, QColor(theme["disabledText"]))

        return palette

    def apply(self, app: QApplication | None, theme_name: str) -> None:
        if app is None:
            return

        app.setStyle("Fusion")
        app.setPalette(self.get_palette(theme_name))
