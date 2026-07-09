# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Linux portable/USB launcher.

Build: pyinstaller build/netscanx-linux.spec  (must run on Linux -- PyInstaller
does not cross-compile)
Output: dist/NetScanX-Start-Linux

NOTE (build-validation TODO): see netscanx-windows.spec for the full
rationale. FAT32/exFAT-formatted USB drives do not preserve the Unix
executable bit, so this binary may need `chmod +x NetScanX-Start-Linux` or
"Run as program" via the file manager before it launches -- documented in
README.md's Portable/USB Mode section.
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
    name="NetScanX-Start-Linux",
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
