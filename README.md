# Tool Pouch

A modular, extensible GUI for Python utility scripts. Drop in a new tool folder and it appears automatically in the sidebar.

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

Output lands in `dist\ToolPouch\`. The entire folder is portable -- copy it anywhere and run `ToolPouch.exe`.

---

## Adding a New Tool

### Option A: Use the in-app wizard

Click **"+ Add new tool"** at the bottom of the sidebar. The wizard will:
1. Ask for metadata (name, description, icon)
2. Let you pick your `.py` script
3. Let you define input parameters (text fields, folder pickers, dropdowns, etc.)
4. Generate `tool.toml` and copy your script into a new `tools/<folder>/` directory

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

## Included Tools

| Tool | Description |
|---|---|
| JSON Translator | Translates Chinese JSON fields to English |
| TXT to PDF | Merges TXT files into a single PDF |
| Cleanup TXT | Strips whitespace and blank lines from TXT files |
| Pattern Remover | Removes/replaces regex patterns in TXT/MD files |
| XHTML Converter | Converts HTML/XHTML to plain TXT or Markdown |
