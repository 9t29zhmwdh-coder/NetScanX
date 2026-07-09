# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the macOS portable/USB launcher.

Build: pyinstaller build/netscanx-macos.spec  (must run on macOS -- PyInstaller
does not cross-compile)
Output: dist/NetScanX-Start-macOS

NOTE (build-validation TODO): see netscanx-windows.spec for the full
rationale. On macOS additionally expect an "unidentified developer"
Gatekeeper warning on first run since this binary is not code-signed /
notarized -- documented in README.md's Portable/USB Mode section.
"""
import os

SPECROOT = os.path.dirname(os.path.abspath(SPEC))
PROJECT_ROOT = os.path.dirname(SPECROOT)

hiddenimports = [
    "scapy.layers.all",
    "zeroconf._utils.ipaddress",
    "zeroconf._handlers.answers",
    "uvicorn.lifespan.on",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "aiosqlite",
    "sqlalchemy.dialects.sqlite.aiosqlite",
]

a = Analysis(
    [os.path.join(PROJECT_ROOT, "netscanx", "__main__frozen__.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (
            os.path.join(PROJECT_ROOT, "netscanx", "dashboard", "static"),
            os.path.join("netscanx", "dashboard", "static"),
        ),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NetScanX-Start-macOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
