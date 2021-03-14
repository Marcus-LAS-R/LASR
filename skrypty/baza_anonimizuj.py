import os
import glob
from PyQt5.QtWidgets import QFileDialog

from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza


def Anonimizuj(iface):
    bazy_kat = QFileDialog().getExistingDirectory(
        iface.mainWindow(),
        "Katalog z bazami danych",
        '')
    bazy_sc = glob.glob(os.path.join(bazy_kat, '*.mdb'))
    bazy_sc += glob.glob(os.path.join(bazy_kat, '*.MDB'))
    ile_baz = len(bazy_sc)
    if ile_baz == 0:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie znalazłem żadnej bazy taksatora...',
            Qgis.Critical,
            10
        )

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

        baza.utworz_kopie('anonimizacja')
        baza.anonimizuj_vaddress()
        ile_ok += 1

        QgsMessageLog.logMessage('\n'+20*'-', 'Las-R', Qgis.Info)

    iface.messageBar().pushMessage(
        "OK",
        'Zanonimizowanych baz: ' + str(ile_ok),
        Qgis.Success,
        10
    )
