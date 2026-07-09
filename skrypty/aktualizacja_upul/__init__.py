import os

from .core.config import Config
from .gui.main_dialog import MainDialog
from .gui.konwersja_shp_dialog import KonwersjaShpDialog
from .gui.dopisz_dane_wydzielen_dialog import DopiszDaneWydzielenDialog


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


def uruchom_konwersja_shp(iface):
    """Konwersja SHP ze starego standardu pól na obecnie obowiązujący.

    Osobna pozycja menu — nie wymaga pliku .mdb, działa na warstwach z
    TOC bieżącego projektu i/lub plikach wskazanych ręcznie w dialogu.
    """
    dialog = KonwersjaShpDialog(parent=iface.mainWindow())
    dialog.exec_()


def uruchom_dopisz_dane_wydzielen(iface):
    """Dopisz dane do wydzieleń - odpowiednik "Join attributes by
    location", zapisujący wynik od razu do wskazanej warstwy WYDZ.

    Osobna pozycja menu — działa na warstwach z TOC bieżącego projektu,
    nie wymaga pliku .mdb.
    """
    dialog = DopiszDaneWydzielenDialog(parent=iface.mainWindow())
    dialog.exec_()
