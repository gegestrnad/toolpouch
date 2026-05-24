import json
import tempfile
import unittest
from pathlib import Path

from core.config import ConfigManager
from core.tool_loader import ToolDefinition
from ui.main_window import sort_tools_for_sidebar


def make_tool(folder_name, name):
    return ToolDefinition(
        name=name,
        description=f"{name} description",
        icon="ti-tool",
        script_path=Path(folder_name) / "tool.py",
        long_running=False,
        params=[],
        folder=Path(folder_name),
    )


class SidebarToolSortingTests(unittest.TestCase):
    def setUp(self):
        self.tools = [
            make_tool("txt_to_pdf", "TXT to PDF"),
            make_tool("cleanup_txt", "Text Cleanup"),
            make_tool("json_translator", "JSON Translator"),
            make_tool("folder_inventory", "Folder Inventory"),
        ]

    def test_favorites_are_first_and_default_order_preserves_loader_order(self):
        sorted_tools = sort_tools_for_sidebar(
            self.tools,
            favorite_tool_ids=["json_translator", "missing_tool"],
            recent_tool_ids=[],
            sort_order="Default",
        )

        self.assertEqual(
            [tool.folder.name for tool in sorted_tools],
            ["json_translator", "txt_to_pdf", "cleanup_txt", "folder_inventory"],
        )

    def test_name_sort_applies_inside_favorites_and_regular_tools(self):
        sorted_tools = sort_tools_for_sidebar(
            self.tools,
            favorite_tool_ids=["txt_to_pdf", "json_translator"],
            recent_tool_ids=[],
            sort_order="Name A-Z",
        )

        self.assertEqual(
            [tool.name for tool in sorted_tools],
            ["JSON Translator", "TXT to PDF", "Folder Inventory", "Text Cleanup"],
        )

    def test_name_desc_sort_applies_inside_favorites_and_regular_tools(self):
        sorted_tools = sort_tools_for_sidebar(
            self.tools,
            favorite_tool_ids=["folder_inventory", "cleanup_txt"],
            recent_tool_ids=[],
            sort_order="Name Z-A",
        )

        self.assertEqual(
            [tool.name for tool in sorted_tools],
            ["Text Cleanup", "Folder Inventory", "TXT to PDF", "JSON Translator"],
        )

    def test_recent_sort_uses_recent_order_then_name_fallback(self):
        sorted_tools = sort_tools_for_sidebar(
            self.tools,
            favorite_tool_ids=["folder_inventory"],
            recent_tool_ids=["cleanup_txt", "txt_to_pdf"],
            sort_order="Recently Used",
        )

        self.assertEqual(
            [tool.folder.name for tool in sorted_tools],
            ["folder_inventory", "cleanup_txt", "txt_to_pdf", "json_translator"],
        )


class ConfigDefaultsTests(unittest.TestCase):
    def test_default_config_includes_sidebar_preferences(self):
        config = ConfigManager.__new__(ConfigManager)

        self.assertEqual(config._default_config()["favorite_tools"], [])
        self.assertEqual(config._default_config()["tool_sort_order"], "Default")

    def test_legacy_config_load_merges_sidebar_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = ConfigManager.__new__(ConfigManager)
            config.config_file = Path(tmp_dir) / "config.json"
            config.config_file.write_text(json.dumps({"theme": "Paper Daylight"}))

            loaded = config._load_config()

        self.assertEqual(loaded["theme"], "Paper Daylight")
        self.assertEqual(loaded["favorite_tools"], [])
        self.assertEqual(loaded["tool_sort_order"], "Default")


if __name__ == "__main__":
    unittest.main()
