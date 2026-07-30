# Tool Pouch v3

A modular, extensible GUI for local utility scripts. Drop a new tool
folder into `Tools/` and it appears in the sidebar automatically.

Multi-language: **Python (.py)**, **PowerShell (.ps1)**, **Batch
(.bat/.cmd)**, and **JavaScript (.js)** tools are all supported.

Built with **CustomTkinter** — no Qt, lightweight, Windows-native.

---

## What's new in v3 (vs v2)

- **Multi-language scripts** — `.py`, `.ps1`, `.bat`/`.cmd`, `.js`. The
  `RuntimeResolver` picks the right interpreter per extension (or per
  `runtime` override in `tool.toml`).
- **Script-type icons** — each tool in the sidebar shows a colored
  language icon (Python blue, PowerShell navy, Batch gray, Node green).
  The tool panel header shows a badge chip + the full language name.
- **System-first dependency resolution** — for `.py` tools, prefers
  system-installed Python on PATH. Only falls back to a bundled
  minimal embeddable Python when no system Python is found.
- **Real installer** — Inno Setup `.exe` installer replaces v2's
  portable-folder approach. Installs to `%LOCALAPPDATA%\Programs\Tool
  Pouch`, creates Start Menu shortcut, no admin elevation needed.
- **Lightweight** — CustomTkinter + deps ≈ 5 MB; total installed
  footprint ~50-70 MB (vs v2's >200 MB).
- **CustomTkinter UI** — replaces PySide6/Qt6. Same three-zone layout
  (sidebar / panel header / panel body) you already know.
- **Multi-ecosystem Dependency Manager** — one table with an
  Ecosystem column for Python (pip), Node (npm), and PowerShell
  (Install-Module) deps. Supports installing all missing OR selected
  individual dependencies.
- **Edit tool** — right-click any tool → "Edit tool..." opens the
  wizard pre-filled with that tool's data. Edit metadata, script, or
  parameters and save in place.
- **Universal wizard** — auto-detects the script language from the
  file extension, shows a per-language code snippet demonstrating the
  stdout protocol, and lets you override the runtime if needed.
- **Backward-compatible manifest parsing** — all existing v2
  `tool.toml` files parse without error (the loader tolerates
  capitalized types, `default_value`, comma-string options, and the
  broken `[[dependencies]] id=` form).
- **UTF-8 output** — tool scripts can print any Unicode character
  (CJK, emoji, smart quotes) without crashing on Windows cp1252.
- **Deletion persistence** — deleted tools stay deleted across
  restarts (tracked in `~/.toolpouch/deleted_tools.json`).

---

## Requirements

- **Runtime**: Windows 10/11 x64 (HiDPI / 4K friendly). Not cross-platform
  — this is a deliberate decision (see `DECISIONS.md`). The installer
  requires 64-bit Windows (`ArchitecturesAllowed=x64compatible`).
- **Development**: Python 3.12 or 3.13 (NOT 3.14 — PyInstaller 6.x
  doesn't support it yet). On 3.11+ uses stdlib `tomllib`; on 3.10 the
  `tomli` backport is auto-loaded.
- **For .py tools**: any Python 3.10+ installed on the system
  (python.org recommended).
- **For .ps1 tools**: built into Windows 10/11 (Windows PowerShell
  5.1) or PowerShell 7+ (`pwsh`).
- **For .bat/.cmd tools**: always available on Windows.
- **For .js tools**: Node.js LTS from https://nodejs.org/ (NOT
  bundled — see `DECISIONS.md` §1.7 footprint goal).

---

## Development setup

```bash
# 1. Clone / extract the source
cd toolpouch-v3

# 2. Install runtime deps
pip install -r requirements.txt

# 3. Run from source (no build step needed for dev)
python main.py
```

The first launch reads tools from `./tools/` and writes config to
`~/.toolpouch/config.json`.

---

## Build a Windows installer

See **`INSTALLER_GUIDE.md`** for the full step-by-step. Short version:

```bat
:: On a Windows machine with Python 3.12+, PyInstaller, and Inno Setup 6:
build.bat
:: Output: dist\installer\ToolPouch-Setup-3.0.0.exe
```

**Important:** Use Python 3.12 or 3.13, NOT 3.14. Run from `dist\`, not
`build\`. See `BUILD.md` for details.

---

## Configuration & logs

User configuration and logs are saved to `~/.toolpouch/` (on Windows,
that's `%USERPROFILE%\.toolpouch\`):

- `config.json` — user preferences (theme, window geometry, recent
  tools, favorites)
- `deleted_tools.json` — tools the user has deleted (prevents re-seeding)
- `logs/` — per-day execution logs
- `tools/` — writable copy of bundled tools (seeded on first launch)

---

## Adding a new tool

### Option A: Use the in-app wizard (recommended)

Click **"+ Add new tool"** at the bottom of the sidebar. The wizard will:

1. Ask for metadata (name, description, icon, long-running, runtime
   override)
2. Let you pick your script file (`.py`, `.ps1`, `.bat`/`.cmd`, or
   `.js`). The wizard auto-detects the language and shows a code
   snippet demonstrating the stdout protocol for that language.
3. Let you define input parameters with validation (text fields,
   folder/file pickers, dropdowns, etc.)
4. Generate `tool.toml` safely (user input is escaped) and copy your
   script into a new `tools/<folder>/` directory

### Option B: Edit an existing tool

Right-click any tool in the sidebar → **"Edit tool..."**. The wizard
opens pre-filled with that tool's existing metadata, script path, and
parameters. Edit what you need and click **Save tool** — it reuses the
same folder name and overwrites the `tool.toml` + script in place.

### Option C: Drop it in manually

Create a folder under `tools/`:

```
tools/
└── my_tool/
    ├── tool.toml
    └── my_script.py    (or .ps1, .bat, .js)
```

**`tool.toml` structure:**

```toml
[tool]
name = "My Tool"
description = "What it does in one sentence"
icon = "ti-tool"          # any Tabler icon name, or an emoji
script = "my_script.py"   # relative to this folder
long_running = false      # true = active progress bar expected
runtime = ""              # optional: "python" | "pwsh" | "powershell" | "cmd" | "node"
                          # empty = infer from script extension

[[params]]
id = "input_dir"
label = "Input folder"
type = "folder"           # text | folder | folders | file | files | save | dropdown
placeholder = "Select a folder"
required = true
icon = "ti-folder"

[[params]]
id = "mode"
label = "Mode"
type = "dropdown"
options = ["fast", "thorough"]
default = "fast"
required = true

[[dependencies]]
import = "fitz"            # import name
package = "PyMuPDF"        # pip package name (only for python ecosystem)
version = ">=1.24"
ecosystem = "python"       # python | node | powershell | none (default: python)
notes = "PDF parsing"
```

Restart Tool Pouch (or use the wizard) to pick up new tools.

---

## Script requirements

Tool scripts communicate with Tool Pouch via stdout:

- Accept all parameters via CLI args as `--param_id value` flags
  matching your `tool.toml` param IDs.
- For multi-value params (`files`, `folders` types), pass each value
  as a separate `--id value` pair.
- Print `PROGRESS:N` (0-100) to stdout to update the progress bar.
- Prefix log lines with `[OK]`, `[WARN]`, or `[ERROR]` for
  color-coded output.
- Exit code 0 = success, non-zero = failure.

### Minimal Python example

```python
import argparse, sys

def progress(pct):
    print(f"PROGRESS:{pct}", flush=True)

parser = argparse.ArgumentParser()
parser.add_argument("--input_dir", required=True)
args = parser.parse_args()

progress(0)
# ... do work ...
print("[OK] Done.", flush=True)
progress(100)
```

### Minimal PowerShell example

```powershell
param([Parameter(Mandatory=$true)][string]$InputDir)
Write-Output "PROGRESS:0"
Write-Output "[OK] Hello from PowerShell"
Write-Output "PROGRESS:100"
```

### Minimal Batch example

```bat
@echo off
:parse
if "%~1"=="" goto run
if /i "%~1"=="--input_dir" set "INPUT_DIR=%~2"
shift & shift & goto parse
:run
echo PROGRESS:0
echo [OK] Hello from Batch
echo PROGRESS:100
exit /b 0
```

### Minimal Node.js example

```javascript
function parseArgs(argv) {
    const params = {};
    for (let i = 2; i < argv.length; i += 2) {
        params[argv[i].replace(/^--/, '')] = argv[i + 1] || '';
    }
    return params;
}
const args = parseArgs(process.argv);
console.log('PROGRESS:0');
console.log(`[OK] Hello from Node ${process.version}`);
console.log('PROGRESS:100');
```

---

## Tool management

### Right-click context menu

Right-click any tool in the sidebar for:

- **★ Add/Remove from favorites** — favorites appear at the top when
  the favorites filter is active
- **Edit tool...** — opens the wizard pre-filled with this tool's data
- **Export as .toolpouch...** — bundles the tool into a `.toolpouch`
  ZIP package
- **Delete tool...** — removes the tool folder; deleted tools stay
  deleted across restarts

### Import / Export

- **Export**: right-click a tool → "Export as .toolpouch..." to create
  a `.toolpouch` ZIP package.
- **Import**: click "Import .toolpouch..." at the bottom of the
  sidebar. Imports are validated for path-traversal attacks. If a
  folder with the same name exists, the new copy gets a numbered
  suffix (`_2`, `_3`, ...).

---

## Themes

Five built-in themes:

- **Modern Dark** — violet-on-slate, dark
- **Moonlit Slate** — sky-blue-on-deep-slate, dark
- **Paper Daylight** — neutral grays, light
- **Mist Garden** — emerald-on-cream, light
- **Clear Contrast** — pure black/white, high-contrast (accessibility)

Pick from the sidebar theme picker. Choice persists across restarts.
Theme switching rebuilds the sidebar and panel instantly (no restart
needed).

---

## Multi-ecosystem Dependency Manager

Click **Dependency Manager** in the sidebar to see all dependencies
across all tools. Each row shows: checkbox / Tool / Import / Package /
Ecosystem / Status / Version / Notes.

- **Re-scan** rebuilds the table.
- **Select all missing** checks every row that's currently missing.
- **Install selected** installs only the checkbox-selected deps.
  Useful for updating or force-reinstalling specific packages without
  touching everything else. Works for both missing AND installed deps.
- **Install all missing** installs every missing dependency.

The auto-detection scans `.py` scripts for `import` statements and
checks `pip show`. For `.js` tools, it reads `package.json` if present.
For `.ps1` tools, it reads declared `[[dependencies]] ecosystem =
"powershell"` entries from `tool.toml` and checks `Get-Module
-ListAvailable`.

Install operations run in a background thread (no UI freeze). Log
output streams to the log box at the bottom. No cmd-window flashing
(uses `CREATE_NO_WINDOW` on Windows).

---

## Included tools (36 total)

### Python tools (27)
Base64 Converter, Biosafety PDF to Excel, Book Context Finder, Count
Characters, CSV Previewer, Duplicate Finder, Extract Numbers, File
Hasher, File Stats, Filename Cleaner, Find Long Lines, Folder
Inventory, HTML to Text, Image Splitter, JSON Formatter, JSON
Translator, JSON Validator, Merge Text, Movie Organizer, Music Artist
Organizer, Pattern Remover, Regex Extractor, Remove Empty Lines, RR
Downloader, TXT Splitter, TXT to PDF, XHTML Converter

### Batch tools (4)
File Hasher, Hello Batch, **IP Config Viewer**, **Environment
Inspector**

### PowerShell tools (2)
Hello PowerShell, **Process List**

### JavaScript tools (3)
Hello Node, JSON Validator, **JSON Sorter**

---

## Testing

```bash
# Unit tests (must pass on any platform):
python -m unittest discover tests

# Smoke tests (imports, themes parse, tool loader, wizard round-trip):
python scripts/smoke_test.py

# End-to-end runner test (launches a real .py tool):
python scripts/runner_test.py
```

45 unit tests cover the three critical modules per spec §9:
`runtime_resolver`, `tool_loader`, `tool_importer`.

---

## Documentation

- `DECISIONS.md` — framework/library choices and rationale
- `PROGRESS.md` — phase-by-phase verification log
- `BUILD.md` — Windows build quick reference
- `INSTALLER_GUIDE.md` — full installer guide with troubleshooting
- `AI_AGENT_GUIDE.md` — **guide for AI agents on how to create
  `.toolpouch` packages** (share this with Claude/GPT when asking them
  to write a Tool Pouch tool)
- `installer/python-embed/README.md` — how to populate the fallback
  Python interpreter

---

## .toolpouch file association

After installing Tool Pouch via the installer, `.toolpouch` files are
registered with Windows. **Double-clicking a `.toolpouch` file** opens
Tool Pouch, imports the tool, and selects it automatically — no manual
import dialog needed.

This is the fastest way to install a tool someone shared with you:
just double-click the `.toolpouch` file. The file association is
registered by the Inno Setup installer (see `installer/toolpouch.iss`
→ `[Registry]` section).

If you're running from source (not the installer), file association
isn't registered — use the "Import .toolpouch..." button in the
sidebar instead.

---

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+F` | Focus the search box |
| `Enter` | Run the currently-selected tool (when not in a text field) |
| `Escape` | Stop running tool / clear search / defocus |
| `Ctrl+A` (in log) | Select all log text |
| Right-click tool | Context menu: favorite, edit, export, delete |

---

## Future ideas

These aren't implemented yet but would make good future updates:

- **Tool categories/tags** — group tools by category (File, Text, Network,
  etc.) with collapsible sections in the sidebar
- **Tool scheduling** — run a tool on a schedule (cron-style) with
  saved parameter presets; output logged automatically
- **Multi-tool pipelines** — chain tools so one's output feeds the next
  (e.g. "Download → Clean → Convert → Upload")
- **Parameter presets** — save common parameter combinations per tool
  for quick reuse
- **Tool marketplace** — online directory of community `.toolpouch`
  packages, browseable from within the app
- **Cross-platform** — macOS/Linux support (currently Windows-only by
  design; would need to audit the runtime resolver + path handling)
- **Tool versioning** — semantic version field in `tool.toml`, with
  update-check against a remote registry
- **Output filtering** — filter log console lines by level (info/ok/
  warn/error) with toggle buttons
- **Dark/light mode auto-switch** — detect OS theme change and switch
  Tool Pouch's appearance mode to match
- **Tool search by parameter** — "find tools that accept a folder
  input" or "find tools that output a PDF"
- **Batch run** — run the same tool multiple times with different
  parameter sets (queue them, run sequentially, collect all outputs)
- **Tool dependencies between tools** — declare that tool B requires
  tool A's output as input; the wizard offers to chain them
- **Internationalization** — UI translations (currently English-only)

