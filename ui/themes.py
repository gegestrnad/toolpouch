from PySide6.QtGui import QPalette, QColor


class ThemeManager:
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
        },
        "Deep Dark": {
            "window": "#0D0D0D",
            "windowText": "#F0F0F0",
            "base": "#1A1A1A",
            "alternateBase": "#151515",
            "text": "#F0F0F0",
            "placeholderText": "#777777",
            "mid": "#2A2A2A",
            "midlight": "#3A3A3A",
            "dark": "#090909",
            "light": "#2D2D2D",
            "button": "#1A1A1A",
            "buttonText": "#F0F0F0",
            "highlight": "#6B5FD0",
        },
        "Light Classic": {
            "window": "#FFFFFF",
            "windowText": "#1A1A1A",
            "base": "#F5F5F5",
            "alternateBase": "#F0F0F0",
            "text": "#1A1A1A",
            "placeholderText": "#888888",
            "mid": "#D0D0D0",
            "midlight": "#E0E0E0",
            "dark": "#505050",
            "light": "#FAFAFA",
            "button": "#F5F5F5",
            "buttonText": "#1A1A1A",
            "highlight": "#534AB7",
        },
        "Soft Light": {
            "window": "#FAFAFA",
            "windowText": "#2C2C2C",
            "base": "#F8F8F8",
            "alternateBase": "#F3F3F3",
            "text": "#2C2C2C",
            "placeholderText": "#999999",
            "mid": "#E8E8E8",
            "midlight": "#EEEEEE",
            "dark": "#606060",
            "light": "#FFFFFF",
            "button": "#F8F8F8",
            "buttonText": "#2C2C2C",
            "highlight": "#4A3FA0",
        },
        "High Contrast": {
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
            "highlight": "#FFFF00",
        },
    }

    def get_theme_names(self):
        return list(self.THEMES.keys())

    def get_palette(self, theme_name: str) -> QPalette:
        if theme_name not in self.THEMES:
            theme_name = "Modern Dark"
        
        theme = self.THEMES[theme_name]
        palette = QPalette()
        
        palette.setColor(QPalette.Window, QColor(theme["window"]))
        palette.setColor(QPalette.WindowText, QColor(theme["windowText"]))
        palette.setColor(QPalette.Base, QColor(theme["base"]))
        palette.setColor(QPalette.AlternateBase, QColor(theme["alternateBase"]))
        palette.setColor(QPalette.Text, QColor(theme["text"]))
        palette.setColor(QPalette.PlaceholderText, QColor(theme["placeholderText"]))
        palette.setColor(QPalette.Mid, QColor(theme["mid"]))
        palette.setColor(QPalette.Midlight, QColor(theme["midlight"]))
        palette.setColor(QPalette.Dark, QColor(theme["dark"]))
        palette.setColor(QPalette.Light, QColor(theme["light"]))
        palette.setColor(QPalette.Button, QColor(theme["button"]))
        palette.setColor(QPalette.ButtonText, QColor(theme["buttonText"]))
        palette.setColor(QPalette.Highlight, QColor(theme["highlight"]))
        
        return palette
