import os

from .core.config import Config
from .gui.main_dialog import MainDialog


def uruchom(iface):
    plugin_dir = os.path.dirname(__file__)
    try:
        config = Config.load(plugin_dir)
    except Exception as e:
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(
            iface.mainWindow(),
            "Błąd konfiguracji",
            f"Nie udało się wczytać config/constants.json:\n{e}",
        )
        return
    dialog = MainDialog(config, parent=iface.mainWindow())
    dialog.exec_()
