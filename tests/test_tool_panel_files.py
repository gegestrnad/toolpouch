import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from core.tool_loader import ToolParam
from ui.tool_panel import FieldWidget


class FilesFieldWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_files_field_returns_newline_separated_selected_paths(self):
        widget = FieldWidget(ToolParam(id="selected_files", label="Selected files", type="files"))

        with patch(
            "ui.tool_panel.QFileDialog.getOpenFileNames",
            return_value=([r"D:\Movies\Movie.mkv", r"D:\Movies\Movie.srt"], ""),
        ):
            widget._browse()

        self.assertEqual(widget.value(), "D:\\Movies\\Movie.mkv\nD:\\Movies\\Movie.srt")
        self.assertEqual(widget._input.text(), "2 files selected")

    def test_required_files_field_is_invalid_until_files_are_selected(self):
        widget = FieldWidget(
            ToolParam(id="selected_files", label="Selected files", type="files", required=True)
        )

        self.assertFalse(widget.is_valid())

        with patch(
            "ui.tool_panel.QFileDialog.getOpenFileNames",
            return_value=([r"D:\Movies\Movie.mkv"], ""),
        ):
            widget._browse()

        self.assertTrue(widget.is_valid())


if __name__ == "__main__":
    unittest.main()
