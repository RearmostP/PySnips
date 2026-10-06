# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
datas = [
    (str(root / 'assets'), 'assets'),
    (str(root / 'data/system_data/version.json'), 'data/system_data'),
]
datas += [
    (str(path), str(path.parent.relative_to(root)))
    for path in sorted((root / 'core/ui').rglob('*.ui'))
]

a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root)],
    datas=datas,
    hiddenimports=[
        # The updater is not connected to the UI yet, but belongs in the bundle.
        'core.updater.updater',
        # Markdown selects these extensions by name at runtime.
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.tables',
        'markdown.extensions.sane_lists',
    ],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='PySnips',
    console=False,
    icon=str(root / 'assets/icons/pysnips-multisize.ico'),
    contents_directory='.',
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name='PySnips', upx=False)
