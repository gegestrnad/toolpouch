import sys
import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.main_window import MainWindow


TOOL_DEPENDENCIES = [
    "requests",
    "beautifulsoup4",
    "reportlab",
    "deep-translator",
]


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def _find_python(exe_dir: Path) -> str:
    """
    Locate the real python.exe bundled by PyInstaller.
    PyInstaller 6+ places it inside _internal/ next to the exe.
    """
    candidates = [
        exe_dir / "python.exe",                  # PyInstaller <6 / explicit --add-binary
        exe_dir / "_internal" / "python.exe",    # PyInstaller 6+
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return "python"  # last resort: whatever is on PATH


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


def ensure_packages(exe_dir: Path):
    """
    Install tool script dependencies into packages/ next to the exe.
    Only runs when frozen and not yet installed.
    """
    if not getattr(sys, "frozen", False):
        return

    packages_dir = exe_dir / "packages"
    marker = packages_dir / ".installed"
    if marker.exists():
        return

    packages_dir.mkdir(exist_ok=True)
    python = _find_python(exe_dir)
    print(f"First run: installing tool dependencies using {python}...")
    print(f"Target: {packages_dir}")

    try:
        result = subprocess.run(
            [python, "-m", "pip", "install",
             "--target", str(packages_dir),
             "--no-cache-dir"] + TOOL_DEPENDENCIES,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            marker.touch()
            print("[OK] Dependencies installed successfully.")
        else:
            print(f"[ERROR] pip failed (exit {result.returncode}):")
            # FIX: Preserve full output instead of truncating
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
    except Exception as e:
        print(f"[ERROR] Could not run pip: {e}")


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
    ensure_packages(exe_dir)

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
