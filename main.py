"""VibranceHub — замена NVIDIA Control Panel для насыщенности и фильтров.

Запуск:   python main.py
          pythonw main.py --minimized    (сразу в трей)
Сборка exe: build_exe.bat
"""
import sys


def main() -> int:
    args = sys.argv[1:]
    start_minimized = '--minimized' in args

    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    app.setApplicationName('VibranceHub')
    app.setOrganizationName('VibranceHub')
    app.setStyle('Fusion')

    from app.ui.theme import apply_theme
    apply_theme(app)

    from app.core.applier import Applier
    from app.core.config import Config
    from app.core.gamma import create_gamma_ctrl
    from app.core.nvapi import create_backend
    from app.ui.main_window import MainWindow

    cfg = Config()
    nvapi, nv_err = create_backend()
    gamma, g_err = create_gamma_ctrl()
    applier = Applier(nvapi, gamma, cfg)

    win = MainWindow(cfg, applier, nv_err=nv_err, g_err=g_err)
    app.setWindowIcon(win.windowIcon())

    if start_minimized or cfg.start_minimized:
        win.hide()
    else:
        win.show()

    rc = app.exec()
    if cfg.restore_on_exit:
        applier.restore_original()
    return rc


if __name__ == '__main__':
    sys.exit(main())
