# Tool Pouch

A modular, extensible GUI for Python utility scripts. Drop in a new tool folder and it appears automatically in the sidebar.

---

## What's new (v2.0.0)

- Improved and more foolproof Add Tool wizard (better validation, parameter editor, script selection)
- Theme system with 5 built-in themes: Modern Dark, Moonlit Slate, Paper Daylight, Mist Garden, Clear Contrast
- Per-user configuration stored at ~/.toolpouch (theme, window geometry, recent tools)
- Execution logging (logs in ~/.toolpouch/logs)
- Tool export/import support using `.toolpouch` ZIP packages
- Input validation and safer TOML generation (quotes escaped)
- Better packaged runtime behavior when running as a PyInstaller bundle

---

## Requirements

- Python 3.11+
- Windows 10/11 (HiDPI / 4K friendly)

---

## Setup (Development)

```bash
pip install -r requirements.txt
python main.py
```

---

## Build Portable EXE

```bash
build.bat
```

Output lands in `dist\ToolPouch\`. The entire folder is portable -- copy that whole folder anywhere and run `ToolPouch.exe`.

The build includes a portable Python runtime under `dist\ToolPouch\runtime\` plus the dependencies needed by the included tools. The packaged app does not run `pip install` on first launch.

---

## Configuration & Logs

User configuration and logs are saved to `~/.toolpouch/`:

- `config.json` — user preferences (theme, window geometry, recent tools)
- `logs/` — execution logs by date

---

## Adding a New Tool

### Option A: Use the in-app wizard (recommended)

Click **"+ Add new tool"** at the bottom of the sidebar. The wizard will:
1. Ask for metadata (name, description, icon)
2. Let you pick your `.py` script (required)
3. Let you define input parameters with validation (text fields, folder pickers, dropdowns, etc.)
4. Generate `tool.toml` safely (user input is escaped) and copy your script into a new `tools/<folder>/` directory

The wizard now validates:
- Tool name and description are required
- Script file must be selected
- Parameter IDs must be alphanumeric + underscores
- Dropdowns require options

### Option B: Drop it in manually

Create a folder under `tools/`:

```
tools/
└── my_tool/
    ├── tool.toml
    └── my_script.py
```

**`tool.toml` structure:**

```toml
[tool]
name = "My Tool"
description = "What it does in one sentence"
icon = "ti-tool"          # any Tabler icon name
script = "my_script.py"
long_running = false      # true = active progress bar expected

[[params]]
id = "input_dir"
label = "Input folder"
type = "folder"           # text | folder | file | save | dropdown
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
icon = "ti-settings"
```

**Script requirements:**
- Accept all parameters via `argparse` with `--param_id` flags matching your `tool.toml` param IDs
- Print `PROGRESS:N` (0-100) to stdout to update the progress bar
- Prefix log lines with `[OK]`, `[WARN]`, or `[ERROR]` for color-coded output
- For packaged builds, custom tools that need extra third-party packages must have those packages added to the portable runtime during build, or be run from source with the dependencies installed in your development Python environment

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

Restart Tool Pouch (or add via wizard) to pick up new tools.

---

## Themes

Choose a theme from the sidebar: two dark themes, two light themes, and one high-contrast theme are included.

---

## Export / Import Tools

Right-click a tool in the sidebar to export it as a `.toolpouch` ZIP package. Use **Import tool...** at the bottom of the sidebar to import a `.toolpouch` file.

Imports are validated before copying. A package must contain exactly one tool folder with a `tool.toml` file and the script referenced by that TOML. If a folder with the same name already exists, Tool Pouch imports the new copy with a numbered suffix such as `_2` instead of overwriting your existing tool.

---

## Included Tools

| Tool | Description |
|---|---|
| JSON Translator | Translates Chinese JSON fields to English |
| TXT to PDF | Merges TXT files into a single PDF |
| Text/Markdown Cleanup | Cleans whitespace and simple Markdown formatting in TXT/MD files |
| Filename Cleaner | Batch-cleans filenames with a safe preview mode |
| TXT Splitter | Splits large TXT files by lines, characters, or chapter markers |
| Regex Extractor | Extracts emails, URLs, headings, or custom regex matches to CSV |
| Folder Inventory | Exports CSV/Markdown reports of file names, sizes, dates, and paths |
| Pattern Remover | Removes/replaces regex patterns in TXT/MD files |
| XHTML Converter | Converts HTML/XHTML to plain TXT or Markdown |

---

## Contributing

PRs welcome. Please run the app locally and ensure the wizard validations and themes behave as expected.
