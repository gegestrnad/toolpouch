import unittest

from PySide6.QtGui import QPalette

from ui.main_window import STYLESHEET
from ui.themes import ThemeManager


class ThemeManagerTests(unittest.TestCase):
    def test_resolves_current_unknown_and_legacy_theme_names(self):
        manager = ThemeManager()

        self.assertEqual(manager.resolve_theme_name("Modern Dark"), "Modern Dark")
        self.assertEqual(manager.resolve_theme_name("Not A Theme"), "Modern Dark")
        self.assertEqual(manager.resolve_theme_name("Deep Dark"), "Moonlit Slate")
        self.assertEqual(manager.resolve_theme_name("Light Classic"), "Paper Daylight")
        self.assertEqual(manager.resolve_theme_name("Soft Light"), "Mist Garden")
        self.assertEqual(manager.resolve_theme_name("High Contrast"), "Clear Contrast")

    def test_palette_includes_roles_used_by_stylesheets(self):
        manager = ThemeManager()

        palette = manager.get_palette("Moonlit Slate")

        self.assertTrue(palette.color(QPalette.Highlight).isValid())
        self.assertTrue(palette.color(QPalette.HighlightedText).isValid())
        self.assertTrue(palette.color(QPalette.Link).isValid())
        self.assertTrue(palette.color(QPalette.LinkVisited).isValid())

    def test_main_stylesheet_uses_qt_css_braces(self):
        self.assertNotIn("{{", STYLESHEET)
        self.assertNotIn("}}", STYLESHEET)

    def test_clear_contrast_uses_non_yellow_accent(self):
        manager = ThemeManager()

        palette = manager.get_palette("Clear Contrast")

        self.assertNotEqual(palette.color(QPalette.Highlight).name().upper(), "#FFFF00")
        self.assertEqual(palette.color(QPalette.HighlightedText).name().upper(), "#000000")

    def test_combo_box_styles_define_readable_popup_colors(self):
        self.assertIn("QComboBox QAbstractItemView", STYLESHEET)
        self.assertIn("selection-background-color: palette(highlight);", STYLESHEET)
        self.assertIn("selection-color: palette(highlightedText);", STYLESHEET)


if __name__ == "__main__":
    unittest.main()
