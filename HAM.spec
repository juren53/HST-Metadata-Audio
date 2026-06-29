# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

datas = [
    ('__init__.py', '.'),
    ('gui/resources/icons', 'gui/resources/icons'),
]

hiddenimports = [
    # PyQt6
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
    # Third-party
    'mutagen',
    'mutagen.id3',
    'mutagen.mp3',
    'PIL',
    'yaml',
    'colorama',
    'tqdm',
    # External shared modules
    'theme_manager',
    'theme_manager.core',
    'theme_manager.dialog',
    'icon_loader',
    # pyqt-app-info
    'pyqt_app_info',
    'pyqt_app_info.qt',
    'pyqt_app_info.info',
    'pyqt_app_info.tools',
    # HAM packages
    '__init__',
    'gui',
    'gui.main_window',
    'gui.theme',
    'gui.zoom_manager',
    'gui.widgets',
    'gui.widgets.batch_list_widget',
    'gui.widgets.batch_info_panel',
    'gui.widgets.step_widget',
    'gui.widgets.log_widget',
    'gui.dialogs',
    'gui.dialogs.new_batch_dialog',
    'gui.dialogs.batch_info_dialog',
    'core',
    'core.pipeline',
    'steps',
    'steps.base_step',
    'steps.step1_csv_prep',
    'steps.step2_csv_validation',
    'steps.step3_metadata_embed',
    'steps.step4_thumbnail_embed',
    'steps.step5_validation',
    'utils',
    'utils.batch_registry',
    'utils.path_manager',
    'utils.logger',
    'utils.validator',
    'utils.file_utils',
    'config',
    'config.config_manager',
    'config.settings',
]

a = Analysis(
    ['ham_gui.py'],
    pathex=[
        '.',
        r'C:\Users\juren\Projects\ThemeManager',
        r'C:\Users\juren\Projects\Icon_Manager_Module',
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets'],
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
    name='HAM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gui\\resources\\icons\\app.ico',
    version='version_info.txt',
)
