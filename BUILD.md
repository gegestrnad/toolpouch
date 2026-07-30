# BUILD.md

How to produce a Tool Pouch v3 Windows installer from source.

> **⚠️ For the full installer guide with troubleshooting, see
> [`INSTALLER_GUIDE.md`](INSTALLER_GUIDE.md).** This file is a quick
> reference; the installer guide has detailed error fixes.
>
> **Dev environment note:** this codebase was developed and unit-tested
> on Linux for portability of the Python logic, but the **target is
> Windows-only**. The PyInstaller and Inno Setup steps below MUST be
> run on a Windows machine — they cannot run on Linux or macOS.

---

## ⚠️ Two critical things to know before building

### 1. Use Python 3.12 or 3.13 — NOT 3.14

PyInstaller 6.x does NOT fully support Python 3.14 yet. Building with
3.14 produces a broken exe that fails with:

```
Failed to load Python DLL
...\ToolPouch\_internal\python314.dll
LoadLibrary: The specified module could not be found.
```

**Fix:** Install Python 3.12 or 3.13 from https://python.org/downloads/
and use that for the build. If you have multiple Pythons, use
`py -3.12` to target the older version specifically.

### 2. Run from `dist\`, NOT `build\`

PyInstaller uses two folders:
- `build\` — temporary working directory (INCOMPLETE, do NOT run from here)
- `dist\` — the actual output (RUN FROM HERE)

If you run `build\ToolPouch\ToolPouch.exe`, you'll get a "Failed to
load Python DLL" error because `build\` doesn't have the complete
runtime. **Always run `dist\ToolPouch\ToolPouch.exe`.**

---

## Prerequisites (Windows build machine)

1. **Windows 10/11** (x64)
2. **Python 3.10+** on PATH — https://python.org/
   - During install, check "Add Python to PATH"
   - Verify: `python --version`
3. **PyInstaller** — install via `pip install pyinstaller` (or it'll
   be installed automatically by `build.bat` from `requirements.txt`)
4. **Inno Setup 6** — https://jrsoftware.org/isdl.php
   - During install, check "Add ISCC to PATH" (optional — `build.bat`
     also checks the default install location)
5. **(Optional) Embeddable Python** for the tool-execution fallback:
   - Download "Windows embeddable package (64-bit)" from python.org
     matching your build Python version (e.g. `python-3.12.x-embed-amd64.zip`)
   - Extract into `installer/python-embed/` so that
     `installer/python-embed/python.exe` exists
   - See `installer/python-embed/README.md` for details

---

## Build steps

### Quick build (one click)

```bat
:: From the project root, in a Command Prompt:
build.bat
```

This will:
1. `pip install -r requirements.txt`
2. Clean previous `build/` and `dist/` folders
3. Run PyInstaller (`--onedir`, no Qt, no console)
4. Run Inno Setup to produce the installer

**Output:**
- `dist\ToolPouch\` — the portable folder (you can run `ToolPouch.exe` directly)
- `dist\installer\ToolPouch-Setup-3.0.0.exe` — the installer

### PowerShell build

```powershell
.\build.ps1
# or:
.\build.ps1 -SkipInstaller   # just PyInstaller, no Inno Setup
```

### Manual step-by-step

```bat
:: 1. Install deps
pip install -r requirements.txt

:: 2. PyInstaller (recommended: use the spec file for consistency)
pyinstaller --noconfirm --clean --distpath "dist" --workpath "build" installer\ToolPouch.spec

:: OR inline (must match the spec — including PIL collection):
:: pyinstaller --name "ToolPouch" --onedir --windowed --noupx --noconfirm ^
::   --add-data "tools;tools" --add-data "assets;assets" --add-data "ui\themes;ui\themes" ^
::   --hidden-import "darkdetect" --hidden-import "tkinterdnd2" ^
::   --hidden-import "PIL" --hidden-import "PIL.Image" ^
::   --collect-all "customtkinter" --collect-all "PIL" ^
::   --exclude-module "PySide6" --exclude-module "PyQt6" --exclude-module "PyQt5" ^
::   --exclude-module "numpy" --exclude-module "pandas" ^
::   main.py

:: 3. Inno Setup
ISCC.exe installer\toolpouch.iss
```

---

## Verify the system-first invariant (spec §7 — CRITICAL)

This is the single most important test per spec §9:

> "a .py tool script run through the installed app uses system Python,
> not the PyInstaller-bundled interpreter meant for the host UI —
> confirm by checking which sys.executable/process path actually
> launched the tool script during a test run."

**How to verify on Windows:**

1. Install Tool Pouch via the installer.
2. Launch the app.
3. In the sidebar, pick **Hello Python** (one of the test tools).
4. In the **path** field, enter: `C:\Test Folder (2026)\file.txt`
   (a path with spaces — verifies the arg-passing invariant too).
5. Click **Run**.
6. Check the log output. You should see:
   ```
   [OK] Hello from Python 3.12.x
   [OK] python_exe: C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe
   [OK] path_arg:   C:\Test Folder (2026)\file.txt
   [OK] Path contains spaces — preserved correctly.
   ```

   **`python_exe` MUST point at a system Python install** (typically
   under `C:\Users\<you>\AppData\Local\Programs\Python\` or
   `C:\Python312\`). If it points at something inside the Tool Pouch
   install dir (e.g. `...\Tool Pouch\_internal\python.exe`), the
   invariant is **violated** — file a bug.

7. Repeat for **Hello PowerShell**, **Hello Batch**, **Hello Node** —
   each should print its own runtime's executable path, NOT a
   Tool-Pouch-internal path.

---

## Verify on a clean VM (spec §8 checkpoint)

The Phase 8 spec checkpoint calls for testing on a clean Windows VM
with no dev environment.

**Test 1: No Python installed, no `python-embed/` shipped**
- Expected: app launches, .bat tools run, .ps1 tools run (Windows
  PowerShell is built in), .js tools fail with a clear actionable
  error pointing to nodejs.org, .py tools fail with a clear
  actionable error pointing to python.org.

**Test 2: No Python installed, `python-embed/` shipped**
- Expected: .py tools run using the embedded Python. Tools needing
  third-party packages (e.g. `fitz` / PyMuPDF) report missing deps
  clearly; if pip was added to the embed per
  `installer/python-embed/README.md`, the Dependency Manager can
  install them.

**Test 3: System Python installed**
- Expected: .py tools use the system Python (verify via `python_exe:`
  log line as above). The embedded Python is not touched.

---

## Build artifacts reference

| Path | Purpose |
|---|---|
| `build/` | PyInstaller working dir (delete freely) |
| `dist/ToolPouch/` | Portable app folder — copy anywhere, run `ToolPouch.exe` |
| `dist/ToolPouch/ToolPouch.exe` | The host app launcher |
| `dist/ToolPouch/_internal/` | Python + CTk + bundled deps (UI only) |
| `dist/ToolPouch/python-embed/` | Optional fallback Python for .py tools |
| `dist/ToolPouch/tools/` | Seeded on first launch from bundled tools |
| `dist/ToolPouch/assets/` | Seeded on first launch (icon) |
| `dist/installer/ToolPouch-Setup-3.0.0.exe` | The installer |
| `%USERPROFILE%\.toolpouch\` | User config + logs (created on first run, not by installer) |

---

## Troubleshooting

**PyInstaller error: `ModuleNotFoundError: No module named 'customtkinter'`**
- Run `pip install customtkinter` on the build machine first; PyInstaller can't bundle what isn't installed.

**Inno Setup error: `Cannot find ISCC.exe`**
- Either add Inno Setup to PATH, or set `ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe` before running `build.bat`.

**Installed app crashes immediately on launch**
- Run `ToolPouch.exe` from a Command Prompt to see the error output (the installer builds a windowed app with no console by default).
- Most common cause: missing `tools/` or `assets/` data in the bundle. Verify `dist/ToolPouch/_internal/tools/` and `dist/ToolPouch/_internal/assets/` exist after PyInstaller.

**`.py` tools fail with "No Python interpreter found"**
- Either install Python 3.10+ from python.org, or populate `installer/python-embed/` before building.

**`.js` tools fail with "No Node.js found on PATH"**
- Install Node.js LTS from https://nodejs.org/. Tool Pouch deliberately does NOT bundle Node (spec §1.7 footprint goal).
