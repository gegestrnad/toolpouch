# AI Agent Guide: Creating .toolpouch Packages

This guide is for AI agents (Claude, GPT, etc.) who are asked by a
user to "write a tool for Tool Pouch" or "create a Tool Pouch tool
that does X". It explains exactly how to create a `.toolpouch` package
the user can double-click to install.

---

## What is a .toolpouch file?

A `.toolpouch` file is a **ZIP archive** with the `.toolpouch`
extension. It contains exactly one tool folder, which has:

1. A `tool.toml` manifest describing the tool's metadata and parameters
2. A script file (`.py`, `.ps1`, `.bat`/`.cmd`, or `.js`) that does the
   actual work

When the user double-clicks a `.toolpouch` file, Tool Pouch opens,
imports the tool, and selects it automatically. The user doesn't need
to manually copy files or edit anything.

---

## When to create a .toolpouch package

Create one when the user asks you to:
- "Write a Tool Pouch tool that does X"
- "Make a tool for [task]"
- "Add a script to Tool Pouch that [does something]"
- Any request that involves creating a reusable utility script that
  fits the Tool Pouch model (CLI args in, colored stdout out)

**Do NOT** create one when:
- The user just wants a standalone script (give them the script
  directly)
- The task requires a GUI (Tool Pouch tools are CLI-only)
- The task needs interactivity (prompting for input mid-run) — Tool
  Pouch tools receive all input as CLI args and run unattended

---

## Structure of a .toolpouch file

```
my_tool_name.toolpouch          ← ZIP file with .toolpouch extension
└── my_tool_name/               ← exactly ONE root folder
    ├── tool.toml               ← manifest (required)
    └── my_script.py            ← the script (required)
```

**Rules:**
- The ZIP must contain exactly ONE top-level folder
- That folder must contain a `tool.toml`
- The `tool.toml`'s `script` field must point to a file INSIDE that
  folder (no `../` escapes — path-traversal is rejected)
- The script file must exist in the archive
- No `__pycache__` or `.pyc` files (they're build artifacts)

---

## The tool.toml manifest

```toml
[tool]
name = "My Tool"                    # display name (required)
description = "What it does"        # one-line description (required)
icon = "ti-tool"                    # Tabler icon name or emoji
script = "my_script.py"             # filename relative to this folder (required)
long_running = false                # true = show active progress bar
runtime = ""                        # optional: "python"|"pwsh"|"powershell"|"cmd"|"node"
                                    # empty = infer from script extension

[[params]]
id = "input_file"                   # alphanumeric + underscore, starts with letter/_
label = "Input file"                # display label
type = "file"                       # text|folder|folders|file|files|save|dropdown
filter = "*.txt *.md"              # file type filter (for file/files/save types)
placeholder = "Select a file"       # greyed-out hint text
required = true                     # must the user provide a value?
icon = "ti-file-text"               # Tabler icon for this param
default = ""                        # default value if user leaves it empty

[[params]]
id = "mode"
label = "Mode"
type = "dropdown"
options = ["fast", "thorough"]      # required for dropdown type
default = "fast"
required = true

[[dependencies]]
import = "fitz"                     # Python import name
package = "PyMuPDF"                 # pip package name
version = ">=1.24"                  # version specifier (optional)
ecosystem = "python"                # python|node|powershell|none (default: python)
notes = "PDF parsing"               # shown in the Dependency Manager
```

### Param types

| Type | UI widget | Use for |
|---|---|---|
| `text` | text entry | free-form strings, numbers |
| `folder` | browse button → folder picker | single folder path |
| `folders` | browse button → multi-folder picker | multiple folder paths (newline-joined) |
| `file` | browse button → file picker | single file path |
| `files` | browse button → multi-file picker | multiple file paths (newline-joined) |
| `save` | browse button → save-as dialog | output file path |
| `dropdown` | option menu | fixed set of choices |

### Runtime inference

If `runtime` is empty, the extension determines the interpreter:
- `.py` → system Python (or bundled fallback)
- `.ps1` → PowerShell (`pwsh` or `powershell.exe`)
- `.bat`/`.cmd` → `cmd.exe /c`
- `.js` → system Node.js

Set `runtime` explicitly only if the extension doesn't match the
intended interpreter (rare).

---

## The stdout protocol

Tool Pouch parses the script's stdout to update the UI. Your script
MUST follow this protocol:

| Output | Effect |
|---|---|
| `PROGRESS:N` (0-100) | Updates the progress bar |
| `[OK] message` | Green line in the log console |
| `[WARN] message` | Yellow line in the log console |
| `[ERROR] message` | Red line in the log console |
| anything else | Plain info line (default color) |
| exit code 0 | Success |
| exit code non-zero | Failure |

### Argument convention

All params are passed as `--param_id value` pairs. For `files`/`folders`
types, each value is a separate `--id value` pair.

---

## Code templates by language

### Python (.py)

```python
"""My Tool — does something useful."""
import argparse
import sys
from pathlib import Path


def progress(pct: int):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="My Tool")
    parser.add_argument("--input_file", required=True, help="Input file")
    parser.add_argument("--mode", default="fast", choices=["fast", "thorough"])
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}", flush=True)
        sys.exit(1)

    print(f"[OK] Processing {input_path.name}...", flush=True)
    progress(0)

    # ... do the actual work ...

    progress(50)
    print(f"[OK] Mode: {args.mode}", flush=True)

    progress(100)
    print(f"[OK] Done. Output written to ...", flush=True)


if __name__ == "__main__":
    main()
```

### PowerShell (.ps1)

```powershell
# My Tool — does something useful.
param(
    [Parameter(Mandatory=$true)]
    [string]$InputFile,
    [string]$Mode = "fast"
)

Write-Output "PROGRESS:0"
Write-Output "[OK] Processing $InputFile..."

# ... do the actual work ...

Write-Output "PROGRESS:50"
Write-Output "[OK] Mode: $Mode"

Write-Output "PROGRESS:100"
Write-Output "[OK] Done."
```

### Batch (.bat)

```bat
@echo off
setlocal enabledelayedexpansion

REM Parse --param_id value pairs
set "INPUT_FILE="
set "MODE=fast"

:parse
if "%~1"=="" goto run
if /i "%~1"=="--input_file" ( set "INPUT_FILE=%~2" & shift & shift & goto parse )
if /i "%~1"=="--mode" ( set "MODE=%~2" & shift & shift & goto parse )
shift
goto parse

:run
echo PROGRESS:0
echo [OK] Processing %INPUT_FILE%...

REM ... do the actual work ...

echo PROGRESS:50
echo [OK] Mode: %MODE%

echo PROGRESS:100
echo [OK] Done.
endlocal
exit /b 0
```

### JavaScript (.js)

```javascript
// My Tool — does something useful.

function parseArgs(argv) {
    const params = {};
    for (let i = 2; i < argv.length; i += 2) {
        const key = argv[i].replace(/^--/, '');
        params[key] = argv[i + 1] || '';
    }
    return params;
}

const args = parseArgs(process.argv);

if (!args.input_file) {
    console.error('[ERROR] No --input_file specified');
    process.exit(1);
}

console.log('PROGRESS:0');
console.log(`[OK] Processing ${args.input_file}...`);

// ... do the actual work ...

console.log('PROGRESS:50');
console.log(`[OK] Mode: ${args.mode || 'fast'}`);

console.log('PROGRESS:100');
console.log('[OK] Done.');
```

---

## How to create a .toolpouch package

### Python (recommended for AI agents)

```python
import zipfile
from pathlib import Path

def create_toolpouch(
    output_path: str,
    tool_folder_name: str,
    tool_toml_content: str,
    script_filename: str,
    script_content: str,
    extra_files: dict[str, str] | None = None,
) -> Path:
    """Create a .toolpouch ZIP package.

    Args:
        output_path: Where to write the .toolpouch file.
        tool_folder_name: Name of the root folder inside the ZIP.
            Must be filesystem-safe (letters, numbers, underscores).
        tool_toml_content: The full tool.toml file content as a string.
        script_filename: The script's filename (e.g. "my_tool.py").
        script_content: The script's content as a string.
        extra_files: Optional {filename: content} for additional files
            (e.g. a package.json for Node tools).

    Returns:
        Path to the created .toolpouch file.
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        # tool.toml — must be at <root>/tool.toml
        zf.writestr(f"{tool_folder_name}/tool.toml", tool_toml_content)
        # The script — must be at <root>/<script_filename>
        zf.writestr(f"{tool_folder_name}/{script_filename}", script_content)
        # Any extra files
        if extra_files:
            for fname, content in extra_files.items():
                zf.writestr(f"{tool_folder_name}/{fname}", content)

    return output


# ---- Example usage ----

tool_toml = """[tool]
name = "Line Counter"
description = "Counts lines in a text file"
icon = "ti-file-text"
script = "line_counter.py"
long_running = false

[[params]]
id = "input_file"
label = "Input file"
type = "file"
filter = "*.txt *.md *.log"
placeholder = "Select a text file"
required = true
icon = "ti-file-text"
"""

script = '''"""Line Counter — counts lines in a text file."""
import argparse
import sys
from pathlib import Path


def progress(pct):
    print(f"PROGRESS:{pct}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_file", required=True)
    args = parser.parse_args()

    path = Path(args.input_file)
    if not path.exists():
        print(f"[ERROR] File not found: {path}", flush=True)
        sys.exit(1)

    progress(0)
    print(f"[OK] Reading {path.name}...", flush=True)

    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    progress(50)
    print(f"[OK] Total lines: {len(lines)}", flush=True)
    print(f"[OK] Non-empty lines: {len([l for l in lines if l.strip()])}", flush=True)
    print(f"[OK] Blank lines: {len([l for l in lines if not l.strip()])}", flush=True)

    progress(100)
    print("[OK] Done.", flush=True)


if __name__ == "__main__":
    main()
'''

create_toolpouch(
    output_path="line_counter.toolpouch",
    tool_folder_name="line_counter",
    tool_toml_content=tool_toml,
    script_filename="line_counter.py",
    script_content=script,
)
```

### Command line (zip tool)

```bash
# 1. Create the folder structure
mkdir -p line_counter
# 2. Write tool.toml and the script into the folder
# 3. Zip it with the folder as the root
zip -r line_counter.toolpouch line_counter/
```

---

## Security: path-traversal guard

Tool Pouch validates .toolpouch archives before extracting. Your
package will be **rejected** if:

1. Any file path in the ZIP starts with `/` (absolute path)
2. Any file path contains `..` (parent-directory escape)
3. The `tool.toml`'s `script` field resolves to a path OUTSIDE the
   tool folder (e.g. `script = "../evil.py"`)
4. The ZIP doesn't contain exactly one root folder
5. The ZIP doesn't contain a `tool.toml`
6. The script file referenced by `tool.toml` doesn't exist in the ZIP

These are security guards — don't try to work around them.

---

## Dependency declaration

If your script needs third-party packages, declare them in
`[[dependencies]]` entries in the `tool.toml`. This makes them show up
in Tool Pouch's Dependency Manager, where the user can install them
with one click.

**For Python:**
- `import` = the name you use in `import X` (e.g. `fitz`, `bs4`, `PIL`)
- `package` = the pip package name (e.g. `PyMuPDF`, `beautifulsoup4`, `pillow`)
- If import == package (e.g. `requests`), you can omit `package`

**For Node:**
- Create a `package.json` in the tool folder alongside the script
- Declare deps in the `dependencies` section as usual
- Tool Pouch reads it automatically; no `[[dependencies]]` needed

**For PowerShell:**
- Declare each module in a `[[dependencies]]` entry with
  `ecosystem = "powershell"`

**For Batch:**
- No dependencies possible (batch tools use only built-in Windows
  commands). If a batch tool needs Python/Node, it's really a
  Python/Node tool — use the right extension.

---

## Checklist for AI agents

Before delivering a `.toolpouch` file to the user, verify:

- [ ] The ZIP contains exactly ONE root folder
- [ ] The root folder contains a `tool.toml`
- [ ] The `tool.toml` has `[tool]` with `name`, `description`, `script`
- [ ] The script file referenced by `tool.toml` exists in the folder
- [ ] Every param has a unique `id` (alphanumeric + underscore)
- [ ] Dropdown params have at least one `option`
- [ ] The script follows the stdout protocol (`PROGRESS:N`, `[OK]`, etc.)
- [ ] The script accepts all params as `--param_id value` CLI args
- [ ] No `__pycache__` or `.pyc` files in the archive
- [ ] No absolute paths or `..` in any archive entry
- [ ] Third-party dependencies are declared in `[[dependencies]]`
- [ ] The file extension is `.toolpouch` (not `.zip`)

---

## Delivering the package

Tell the user:

> "I've created `line_counter.toolpouch` for you. Double-click it to
> install it into Tool Pouch — it'll appear in the sidebar and be
> selected automatically."

If the user doesn't have Tool Pouch installed yet, they need to
install it first. The `.toolpouch` file association only works after
Tool Pouch is installed.

---

## Common mistakes

1. **Forgetting `flush=True`** in Python `print()` — output may be
   buffered and not appear until the script exits. Always use
   `print(..., flush=True)` for protocol lines.

2. **Using `print()` for errors in Node.js** — `console.log()` goes to
   stdout, `console.error()` goes to stderr. Tool Pouch merges them,
   but `[ERROR]` prefix only works if the line is on stdout. Use
   `console.log('[ERROR] ...')` for error lines you want colorized.

3. **Not handling missing optional params** — if a param is optional
   and the user leaves it empty, Tool Pouch does NOT pass it. Your
   script should check for its presence, not assume it's always there.

4. **Using `sys.argv[1]` directly** — always use argparse (Python) or
   the `--param_id value` parsing loop (Batch/Node). The order of
   args is not guaranteed.

5. **Forgetting `exit /b 0`** in batch — without this, the exit code
   may be non-zero even on success, making Tool Pouch report failure.
