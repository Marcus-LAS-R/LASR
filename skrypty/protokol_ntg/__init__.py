"""NTG materiały (narada techniczno-gospodarcza): warstwy i baza, mapy,
protokół DOCX, prezentacja. Gotowe: przygotowanie warstw i bazy
(gui/przygotuj_dialog.py) i mapy (gui/mapy_dialog.py).
"""


def generuj_mapy(iface):
    from .gui.mapy_dialog import GenerujMapyDialog
    GenerujMapyDialog(iface, parent=iface.mainWindow()).exec_()


def przygotuj_warstwy(iface):
    from .gui.przygotuj_dialog import PrzygotujDialog
    PrzygotujDialog(iface, parent=iface.mainWindow()).exec_()
