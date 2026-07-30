# Embeddable Python — for TOOL EXECUTION FALLBACK ONLY

## What this is

Spec §4 + §7 mandate a **separate, deliberately-minimal** embeddable
Python that lives next to the frozen app and is used *only* as a
fallback for executing `.py` tool scripts when no system Python is found
on PATH.

**CRITICAL — read this twice:**

This interpreter is NOT the one that runs the Tool Pouch UI. The UI
runs on the Python that PyInstaller bundles inside `dist\ToolPouch\` —
that's a different interpreter, used for one purpose only (running
CustomTkinter). When the user runs a `.py` tool, `RuntimeResolver`
looks for system Python on PATH first; if it finds one, it uses that.
If it doesn't, *then* it falls back to the `python-embed\python.exe`
shipped here.

This separation is the **single most important invariant** in the whole
v3 design. If a future maintainer "simplifies" by reusing the
PyInstaller-bundled Python for tool execution too, they will silently
recreate v2's "bundles everything, ignores what's on the PC" problem
(see `DECISIONS.md`).

## How to populate this folder

Download the official CPython embeddable package from python.org:

  https://www.python.org/downloads/windows/

Pick the **Windows embeddable package (64-bit)** matching the Python
version you build the host with (e.g. for Python 3.12 →
`python-3.12.x-embed-amd64.zip`).

Unzip it into this folder so that the structure is:

```
installer/python-embed/
├── python.exe
├── python312.dll
├── python312.zip       # stdlib (frozen)
├── LICENSE.txt
└── ...
```

### Make pip available (optional but recommended)

The embeddable package ships WITHOUT pip by design. If you want users
to be able to install Python tool dependencies from the Dependency
Manager when they're running on the embedded Python:

1. Download `get-pip.py` from https://bootstrap.pypa.io/get-pip.py
2. Edit `python312._pth` (it's there after extraction): uncomment the
   `import site` line.
3. Run `python.exe get-pip.py` from this folder.

Without this, the Python Dependency Provider will report "pip not
available" for users running on the embedded fallback. The user gets a
clear actionable error message in that case — they're told to install
Python from python.org, which is the better experience anyway.

## Build-time

`installer/toolpouch.iss` looks for `python-embed\*` and bundles it
into the installer under `{app}\python-embed\`. If this folder is
empty (you chose not to ship a fallback), the Inno Setup `Check:
DirExists(...)` directive skips it silently — the installer still
builds, just without the fallback. In that case `.py` tools require
system Python to be installed, and users get a clear error message
pointing them to python.org if they try to run one without.

## Footprint

A minimal embeddable Python is ~10-15 MB extracted. This is a
deliberate, clearly-labeled fallback, not the app's primary
interpreter (spec §1.7).
