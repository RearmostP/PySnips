# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'updater_main.py')],
    pathex=[str(root)],
    datas=[
        (str(root / 'assets/languages'), 'assets/languages'),
        (str(root / 'assets/icons/pysnips-multisize.ico'), 'assets/icons'),
        (str(root / 'assets/updater.qss'), 'assets'),
        (str(root / 'data/system_data/version.json'), 'data/system_data'),
    ],
)
pyz = PYZ(a.pure)
# Binaries and data belong in EXE, with no COLLECT: this is genuinely ONEFILE.
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name='PySnipsUpdater', console=False, upx=False,
          icon=str(root / 'assets/icons/pysnips-multisize.ico'))
