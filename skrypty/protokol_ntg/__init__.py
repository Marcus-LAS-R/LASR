"""NTG materiały (narada techniczno-gospodarcza): warstwy i baza, mapy,
protokół DOCX, prezentacja. Gotowe: przygotowanie warstw i bazy
(gui/przygotuj_dialog.py), mapy (gui/mapy_dialog.py) i protokół
(gui/protokol_dialog.py, wzór DOCX wskazywany w oknie - poza wtyczką).
"""


def generuj_mapy(iface):
    from .gui.mapy_dialog import GenerujMapyDialog
    GenerujMapyDialog(iface, parent=iface.mainWindow()).exec_()


def przygotuj_warstwy(iface):
    from .gui.przygotuj_dialog import PrzygotujDialog
    PrzygotujDialog(iface, parent=iface.mainWindow()).exec_()


def przygotuj_protokol(iface):
    from .gui.protokol_dialog import ProtokolDialog
    ProtokolDialog(iface, parent=iface.mainWindow()).exec_()
