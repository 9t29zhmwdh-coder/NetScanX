# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows portable/USB launcher.

Build: pyinstaller build/netscanx-windows.spec
Output: dist/NetScanX-Start-Windows.exe

NOTE (build-validation TODO): the hiddenimports list below is a starting
point based on known PyInstaller pain points with scapy/zeroconf/uvicorn.
It MUST be validated by actually running the frozen binary through
`discover`, `services`, and `dashboard` on a clean machine without the dev
environment before trusting a release build -- see the release checklist
in CONTRIBUTING.md. The `datas` mapping for dashboard/static is the #1
build-validation risk: if the package-relative path isn't preserved, the
dashboard will 404 on its CSS/JS.
"""
import os

SPECROOT = os.path.dirname(os.path.abspath(SPEC))
PROJECT_ROOT = os.path.dirname(SPECROOT)

hiddenimports = [
    "scapy.layers.all",
    "scapy.arch.windows",
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
    name="NetScanX-Start-Windows",
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
