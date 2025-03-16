# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['start_app.py'],
    pathex=[],
    binaries=[],
    datas=[('backend/templates', 'backend/templates'), ('backend/static', 'backend/static')],
    hiddenimports=[
        'openpyxl',
        'redis',
        'uvicorn',
        'fastapi',
        'starlette',
        'pydantic',
        'jinja2',
        'passlib',
        'passlib.handlers.bcrypt',
        'bcrypt',
        'python-jose',
        'python-multipart',
        'python-dotenv',
        'httpx'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='leaderboard',
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
