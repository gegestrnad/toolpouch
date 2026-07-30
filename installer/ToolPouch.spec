# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Tool Pouch v3.

Built for ``--onedir`` (spec §7 explicitly says NOT --onefile). Bundles:
  - main.py and all core/ + ui/ + deps/ Python code
  - assets/ (icon)
  - tools/ (sample tools — seeded into the install dir on first launch)
  - ui/themes/*.json (theme files — needed at runtime)

CRITICALLY (spec §7): the Python bundled here is for the UI PROCESS
ONLY. The RuntimeResolver for .py tool scripts still looks for a
SEPARATE system Python on PATH first, falling back to the distinct
installer/python-embed/ interpreter — never this bundled one. This is
verified by Phase 8's "which interpreter actually launched the tool
script" test (see BUILD.md → "Verify the system-first invariant").
"""
from PyInstaller.utils.hooks import collect_all

datas = [
    ('tools', 'tools'),
    ('assets', 'assets'),
    ('assets/lang_icons', 'assets/lang_icons'),
    ('ui/themes', 'ui/themes'),
]
binaries = []
hiddenimports = [
    'darkdetect',
    'tkinterdnd2',
    'PIL',
    'PIL.Image',
]
# CustomTkinter ships data files (fonts, themes); collect them.
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# Pillow (PIL) — used by CTkImage for sidebar language icons. Must be
# collected explicitly so PyInstaller bundles all of PIL's submodules
# and C extensions, not just the top-level package.
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy Qt deps so they can't sneak in transitively.
        'PySide6', 'PyQt6', 'PyQt5',
        # We don't use any of these in the host UI; excluding them
        # shaves megabytes off the bundle.
        # NOTE: PIL is NOT excluded — CTkImage (used for sidebar language
        # icons) depends on it transitively through customtkinter.
        'unittest', 'pydoc', 'doctest',
        'http', 'email', 'xmlrpc',
        'numpy', 'pandas',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ToolPouch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed app — no console pop-up on launch
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ToolPouch',
)
