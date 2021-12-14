import os
import platform
import glob
from qgis.core import Qgis, QgsMessageLog
from PyQt5.QtWidgets import QFileDialog
from .baza_wrapper import Baza


def dopisz_ownership_do_bazy(iface):
    bazy_kat = QFileDialog().getExistingDirectory(
        iface.mainWindow(),
        "Katalog z bazami danych",
        '')

    if platform.system()[:3] == 'Win':
        bazy_sc = glob.glob(os.path.join(bazy_kat, '*.mdb'))
    else:
        bazy_sc = glob.glob(os.path.join(bazy_kat, '*.sqlite'))

    ile_baz = len(bazy_sc)
    if ile_baz == 0:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie znalazłem żadnej bazy taksatora...',
            Qgis.Critical,
            10
        )
        return

    bledy = 0
    ile_ok = 0
    for sc in bazy_sc:
        baza = Baza(sc)
        # jezeli nie mozna polaczyc sie z bazą pomin ją
        if not baza.polacz():
            QgsMessageLog.logMessage(
                'Nie mogłem połączyć sięz bazą: ' + sc,
                'Las-R'
            )
            continue

        QgsMessageLog.logMessage(
            '\n'+20*'-'+'\nPrzetwarzam bazę: ' + sc,
            'Las-R', Qgis.Info
        )

        baza.utworz_kopie('dopisz_ownership')
        if not baza.dopisz_ownership():
            QgsMessageLog.logMessage(
                'Nie udało się dopisać własności do OWNERSHIP_CD w F_PARCEL',
                'Las-R', Qgis.Info
            )
            bledy += 1
        else:
            ile_ok += 1

        QgsMessageLog.logMessage('\n'+20*'-', 'Las-R', Qgis.Info)

    if bledy == 0:
        iface.messageBar().pushMessage(
            "OK",
            f'Dopisałem ownership w {ile_ok} bazie/bazach, (szczegóły '
            'w logu Las-R)',
            Qgis.Success,
            10
        )
    else:
        iface.messageBar().pushMessage(
            "BŁĄD",
            f'Dopisałem ownership w {ile_ok} bazie/bazach, (szczegóły '
            ', Błędów: ' + str(bledy),
            Qgis.Warning,
            10
        )
