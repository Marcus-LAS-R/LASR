"""Materiały do kontroli terenowej - dla ręcznie zaznaczonych wydzieleń
generuje tabelę opisu taksacyjnego (OT), protokół kontroli terenowej i
eksport KML. Patrz core/przetworz.py dla opisu całego przebiegu.
"""

from .gui.dialog import KontrolaTerenowaDialog


def uruchom(iface):
    dialog = KontrolaTerenowaDialog(iface, parent=iface.mainWindow())
    dialog.exec_()
