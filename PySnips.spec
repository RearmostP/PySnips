# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
datas = [
    (str(root / 'assets'), 'assets'),
    (str(root / 'data/system_data/version.json'), 'data/system_data'),
]
datas += [
    (str(path), str(path.parent.relative_to(root)))
    for path in sorted((root / 'core/ui').rglob('*.ui'))
]
datas += collect_data_files('googleapiclient')

a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    datas=datas,
    hiddenimports=[
        # Markdown selects these extensions by name at runtime.
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.tables',
        'markdown.extensions.sane_lists',
        'keyring.backends.Windows',
    ] + collect_submodules('keyring.backends'),
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='PySnips',
    console=False,
    icon=str(root / 'assets/icons/pysnips-multisize.ico'),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name='PySnips', upx=False)
