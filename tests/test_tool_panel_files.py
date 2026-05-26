import os
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData, QUrl
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

    def test_file_field_accepts_dropped_file(self):
        widget = FieldWidget(ToolParam(id="input_file", label="Input file", type="file"))

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file_path = tmp.name

        try:
            self.assertTrue(widget._apply_dropped_paths([file_path]))
            self.assertEqual(widget.value(), file_path)
        finally:
            os.unlink(file_path)

    def test_folder_field_accepts_dropped_folder(self):
        widget = FieldWidget(ToolParam(id="input_dir", label="Input folder", type="folder"))

        with tempfile.TemporaryDirectory() as folder_path:
            self.assertTrue(widget._apply_dropped_paths([folder_path]))
            self.assertEqual(widget.value(), folder_path)

    def test_files_field_accepts_multiple_dropped_files(self):
        widget = FieldWidget(ToolParam(id="selected_files", label="Selected files", type="files"))

        with tempfile.NamedTemporaryFile(delete=False) as first, tempfile.NamedTemporaryFile(
            delete=False
        ) as second:
            paths = [first.name, second.name]

        try:
            self.assertTrue(widget._apply_dropped_paths(paths))
            self.assertEqual(widget.value(), "\n".join(paths))
            self.assertEqual(widget._input.text(), "2 files selected")
        finally:
            for path in paths:
                os.unlink(path)

    def test_file_field_rejects_dropped_folder_without_changing_value(self):
        widget = FieldWidget(ToolParam(id="input_file", label="Input file", type="file"))
        widget._input.setText(r"D:\Existing\file.txt")

        with tempfile.TemporaryDirectory() as folder_path:
            self.assertFalse(widget._apply_dropped_paths([folder_path]))

        self.assertEqual(widget.value(), r"D:\Existing\file.txt")

    def test_only_local_file_urls_are_extracted_from_drops(self):
        widget = FieldWidget(ToolParam(id="input_file", label="Input file", type="file"))
        mime_data = QMimeData()
        mime_data.setUrls([QUrl("https://example.com/file.txt")])

        self.assertEqual(widget._local_paths_from_mime_data(mime_data), [])


if __name__ == "__main__":
    unittest.main()
