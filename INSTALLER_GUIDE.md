# Windows Installer Guide

This guide walks you through building the Tool Pouch v3 Windows installer
from source. You CANNOT do this on Linux or macOS — PyInstaller and
Inno Setup are Windows-only tools.

---

## Prerequisites

### 1. Python (CRITICAL — read this first)

**Use Python 3.12 or 3.13.** Do NOT use Python 3.14.

PyInstaller 6.x does NOT fully support Python 3.14 yet (released
October 2025). Building with 3.14 produces a broken exe that fails with:

```
Failed to load Python DLL
...\ToolPouch\_internal\python314.dll
LoadLibrary: The specified module could not be found.
```

The DLL is physically present but PyInstaller's bootloader can't load
it because the Python 3.14 ABI changed in ways PyInstaller 6.x doesn't
handle yet.

**To fix:**

1. Uninstall Python 3.14 (or just don't use it for this build).
2. Install **Python 3.12.x** or **Python 3.13.x** from
   https://python.org/downloads/
3. During install, check **"Add Python to PATH"**
4. Verify:
   ```bat
   python --version
   :: Should print: Python 3.12.x or Python 3.13.x
   ```

If you need Python 3.14 for other projects, use `py -3.12` to target
the older version specifically:

```bat
py -3.12 -m pip install -r requirements.txt
py -3.12 -m PyInstaller ...
```

### 2. PyInstaller

```bat
pip install pyinstaller
```

Verify: `pyinstaller --version` should print `6.x.x`.

### 3. Inno Setup 6

Download from https://jrsoftware.org/isdl.php

During install, you can let it add `ISCC.exe` to PATH (optional —
`build.bat` also checks the default install location).

Verify: `ISCC.exe /?` should print the Inno Setup banner.

### 4. (Optional) Embeddable Python fallback

If you want `.py` tools to work on machines with NO system Python
installed, download the embeddable Python and extract it into
`installer/python-embed/`. See
`installer/python-embed/README.md` for details.

This is OPTIONAL — without it, `.py` tools simply require the user to
have Python installed, and they get a clear error message if they don't.

---

## Build steps

### Quick build (one click)

```bat
cd D:\path\to\toolpouch-v3
build.bat
```

This will:
1. `pip install -r requirements.txt`
2. Clean `build/` and `dist/` folders
3. Run PyInstaller (`--onedir`, no Qt, no console)
4. Run Inno Setup to produce the installer

**Output:**
- `dist\ToolPouch\` — the portable folder
- `dist\installer\ToolPouch-Setup-3.0.0.exe` — the installer

### ⚠️ CRITICAL: Run from `dist\`, NOT `build\`

PyInstaller uses two folders:
- `build\` — temporary working directory (incomplete, do NOT run from here)
- `dist\` — the actual output (this is what you run)

If you try to run `build\ToolPouch\ToolPouch.exe`, you'll get:

```
Failed to load Python DLL
...\build\ToolPouch\_internal\python3.dll
```

**Always run from `dist\ToolPouch\ToolPouch.exe`.**

### ⚠️ CRITICAL: Install location matters

The installer defaults to `%LOCALAPPDATA%\Programs\Tool Pouch` (user-writable, no admin needed). **Do NOT override this to install to `C:\Program Files\`** — that directory is read-only for non-admin users, and the app will crash on first launch with:

```
PermissionError: [WinError 5] Access is denied: 'C:\Program Files\Tool Pouch\assets'
```

The app seeds user-editable tools to `~/.toolpouch/tools/` (always user-writable), but the install dir itself must also be user-writable for the first-launch seeding of assets. If you must install to `C:\Program Files\`, the user needs to run the app as administrator (not recommended).

If you already installed to `C:\Program Files\` and hit this error:
1. Uninstall Tool Pouch (via Add/Remove Programs)
2. Re-run the installer and accept the default install location
3. OR install to any user-writable folder like `D:\Tools\ToolPouch`

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

:: 2. PyInstaller (recommended: use the spec file)
pyinstaller --noconfirm --clean --distpath "dist" --workpath "build" installer\ToolPouch.spec

:: 3. Inno Setup
ISCC.exe installer\toolpouch.iss
```

---

## Common errors and fixes

### "Failed to load Python DLL"

**Cause:** Either (a) you're running from `build/` instead of `dist/`,
or (b) you built with Python 3.14 which PyInstaller 6.x doesn't
support.

**Fix:**
1. Run `dist\ToolPouch\ToolPouch.exe`, NOT `build\ToolPouch\ToolPouch.exe`.
2. If that doesn't fix it, rebuild with Python 3.12 or 3.13 (see
   Prerequisites §1 above).

### "ModuleNotFoundError: No module named 'customtkinter'"

PyInstaller can't bundle what isn't installed.

**Fix:** `pip install customtkinter` on the build machine first.

### "Cannot find ISCC.exe"

**Fix:** Either add Inno Setup to PATH, or set the `ISCC` environment
variable:
```bat
set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
build.bat
```

### Installed app crashes immediately on launch

Run `ToolPouch.exe` from a Command Prompt to see the error:
```bat
cd "%LOCALAPPDATA%\Programs\Tool Pouch"
ToolPouch.exe
```
Most common cause: missing `tools/` or `assets/` data in the bundle.
Verify `dist\ToolPouch\_internal\tools\` and
`dist\ToolPouch\_internal\assets\` exist after PyInstaller.

### Explorer shows the wrong exe icon (but taskbar/title bar are correct)

**This is almost always a PyInstaller icon embedding issue, NOT a Windows cache issue.** PyInstaller 6.x's `--icon` flag can silently fail to embed the icon into the exe's PE resource section — this is especially common with Python 3.14 (which PyInstaller 6.x doesn't fully support yet). The build log will say "Copying icon to EXE" and your verification script will say "[OK] Icon embedded", but the icon isn't actually there.

Here's the definitive fix:

#### Step 1: Force-embed the icon with rcedit (THE FIX)

`rcedit.exe` is a tool that directly modifies the exe's PE resource section. It bypasses PyInstaller's icon-copying logic entirely and ALWAYS works.

```bat
:: 1. Download rcedit (one-time setup):
powershell -ExecutionPolicy Bypass -File download_rcedit.ps1

:: 2. Force-embed the icon into the already-built exe:
force_icon.bat
```

OR, rebuild from scratch — `build.bat` now detects when PyInstaller's icon embedding fails and automatically calls rcedit to force-embed it:

```bat
build.bat skip-installer
:: Watch for: "[OK] Icon force-embedded with rcedit."
```

#### Step 2: Clear the Windows icon cache

After force-embedding, Explorer may still show the cached old icon. Clear it:

```bat
:: Right-click clear_icon_cache.bat → Run as administrator
clear_icon_cache.bat
```

#### Step 3: Verify

```powershell
powershell -ExecutionPolicy Bypass -File verify_icon.ps1
```

OR manually: right-click `dist\ToolPouch\ToolPouch.exe` → Properties. The icon in the top-left should now be your custom icon.

#### Why this happens

PyInstaller's `--icon` flag uses an internal copy of rcedit to embed the icon. With Python 3.14, PyInstaller's bootloader has known issues that can cause this step to silently fail — the log says "Copying icon to EXE" but the icon isn't actually written. The fix is to call rcedit directly, which bypasses PyInstaller's broken logic.

**The real root-cause fix is to use Python 3.12 or 3.13** (not 3.14) for building. But if you can't change your Python version, the rcedit force-embed above is a reliable workaround.

---

## Verify the system-first invariant

After building and installing, verify that `.py` tools use the SYSTEM
Python, not the bundled one:

1. Launch Tool Pouch.
2. Pick **Hello Python** in the sidebar.
3. In the **path** field, enter: `C:\Test Folder (2026)\file.txt`
4. Click **Run**.
5. Check the log output. You should see:
   ```
   [OK] python_exe: C:\Users\<you>\AppData\Local\Programs\Python\Python312\python.exe
   ```
   The path MUST point at your system Python install, NOT at
   `...\Tool Pouch\_internal\python.exe`. If it points inside Tool
   Pouch, the system-first invariant is violated — file a bug.

---

## Build artifacts reference

| Path | Purpose |
|---|---|
| `build/` | PyInstaller working dir (DELETE freely, do NOT run from here) |
| `dist/ToolPouch/` | Portable app folder — run `ToolPouch.exe` from here |
| `dist/ToolPouch/ToolPouch.exe` | The host app launcher |
| `dist/ToolPouch/_internal/` | Python + CTk + bundled deps (UI only) |
| `dist/ToolPouch/python-embed/` | Optional fallback Python for .py tools |
| `dist/ToolPouch/tools/` | Seeded on first launch from bundled tools |
| `dist/ToolPouch/assets/` | Seeded on first launch (icon) |
| `dist/installer/ToolPouch-Setup-3.0.0.exe` | The installer |
| `%USERPROFILE%\.toolpouch\` | User config + logs (created on first run) |

---

## Clean-VM test (spec §8 checkpoint)

Test on a fresh Windows VM with no dev environment:

**Test 1: No Python installed, no `python-embed/` shipped**
- Expected: app launches, `.bat` tools run, `.ps1` tools run (Windows
  PowerShell is built in), `.js` tools fail with a clear actionable
  error pointing to nodejs.org, `.py` tools fail with a clear
  actionable error pointing to python.org.

**Test 2: No Python installed, `python-embed/` shipped**
- Expected: `.py` tools run using the embedded Python. Tools needing
  third-party packages report missing deps clearly.

**Test 3: System Python installed**
- Expected: `.py` tools use the system Python (verify via `python_exe:`
  log line). The embedded Python is not touched.
