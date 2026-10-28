"""PPOŻ materiały (projekt ochrony przeciwpożarowej): przygotowanie warstw
i bazy (gui/przygotuj_dialog.py - jak w NTG: łączenie SHP i baz TPU,
anonimizacja) oraz warstwy pomocnicze: kompleksy leśne pow. 300 ha
(gui/kompleksy_dialog.py, lasy z BDL przez usługę REST WMS_BDL).
"""


def przygotuj_warstwy(iface):
    from .gui.przygotuj_dialog import PrzygotujPpozDialog
    PrzygotujPpozDialog(iface, parent=iface.mainWindow()).exec_()


def kompleksy_300ha(iface):
    from .gui.kompleksy_dialog import KompleksyDialog
    KompleksyDialog(iface, parent=iface.mainWindow()).exec_()
