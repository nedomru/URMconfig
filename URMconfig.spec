# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('utils', 'utils'), # Utils folder
        ('assets', 'assets') # Assets folder
    ],
    hiddenimports=[
        'psutil',
        'wmi',
        'cv2',
        'pyaudio',
        'requests',
        'ftplib',
        'utils.cpu',
        'utils.gpu',
        'utils.internet',
        'utils.peripherals',
        'utils.system',
        'utils.ftp',
        'utils.updater'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='URMconfig',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app-logo.png'
)