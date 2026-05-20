import sys
import shutil
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def seed_assets(exe_dir: Path):
    if not getattr(sys, "frozen", False):
        return
    assets_dir = exe_dir / "assets"
    bundled = Path(sys._MEIPASS) / "assets"  # type: ignore[attr-defined]
    if bundled.exists():
        assets_dir.mkdir(exist_ok=True)
        for f in bundled.iterdir():
            dest = assets_dir / f.name
            if not dest.exists():
                shutil.copy2(f, dest)


def seed_tools(exe_dir: Path):
    if not getattr(sys, "frozen", False):
        return
    tools_dir = exe_dir / "tools"
    tools_dir.mkdir(exist_ok=True)
    bundled = Path(sys._MEIPASS) / "tools"  # type: ignore[attr-defined]
    if bundled.exists():
        for tool_folder in bundled.iterdir():
            if tool_folder.is_dir():
                dest = tools_dir / tool_folder.name
                if not dest.exists():
                    shutil.copytree(tool_folder, dest)


def get_tools_dir(exe_dir: Path) -> Path:
    tools_dir = exe_dir / "tools"
    tools_dir.mkdir(exist_ok=True)
    return tools_dir


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Tool Pouch")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("ToolPouch")

    exe_dir = _exe_dir()
    seed_assets(exe_dir)
    seed_tools(exe_dir)

    from PySide6.QtGui import QIcon
    icon_path = exe_dir / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    tools_dir = get_tools_dir(exe_dir)
    window = MainWindow(tools_dir)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
