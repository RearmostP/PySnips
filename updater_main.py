# python -m PyInstaller --clean --noconfirm PySnipsUpdater.spec

"""PyInstaller entry point; development uses python -m core.updater."""
from core.updater.app import main

if __name__ == '__main__':
    raise SystemExit(main())
