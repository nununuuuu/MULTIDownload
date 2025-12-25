# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\mypython\\MULTIDownload\\icon\\1.ico', '.')],
    hiddenimports=['mutagen', 'brotli', 'certifi', 'requests', 'urllib3', 'websockets', 'sqlite3', 'optparse', 'email', 'http.client', 'http.cookies', 'http.cookiejar', 'xml.etree.ElementTree', 'pycryptodomex', 'Cryptodome', 'ctypes', 'curl_cffi', 'hmac', 'html', 'html.entities', 'html.parser', 'http.server', 'mimetypes', 'typing', 'fileinput', 'inspect', 'platform', 'shlex', 'textwrap', 'difflib', 'threading', 'subprocess', 'yt_dlp_ejs', 'yt_dlp_ejs.yt', 'yt_dlp_ejs.yt.solver', 'secretstorage'],
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
    [],
    exclude_binaries=True,
    name='MULTIDownload',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\mypython\\MULTIDownload\\icon\\1.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MULTIDownload',
)
