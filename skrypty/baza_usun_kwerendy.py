import os
import glob
from PyQt5.QtWidgets import QFileDialog

from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza


def UsunKwerendy(iface):
    bazy_kat = QFileDialog().getExistingDirectory(
        iface.mainWindow(),
        "Katalog z bazami danych",
        '')
    bazy_sc = glob.glob(os.path.join(bazy_kat, '*.mdb'))
    if len(bazy_sc) == 0:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie znalazłem żadnej bazy taksatora... (mdb ma być małymi literami!)',
            Qgis.Critical,
            10
        )
        return

    ile_ok = 0
    ile_kwerend = 0
    for sc in bazy_sc:
        baza = Baza(sc)
        if not baza.polacz():
            QgsMessageLog.logMessage(
                'Nie mogłem połączyć się z bazą: ' + sc,
                'Las-R'
            )
            continue

        QgsMessageLog.logMessage(
            '\n' + 20*'-' + '\nPrzetwarzam bazę: ' + sc,
            'Las-R', Qgis.Info
        )

        usuniete = baza.usun_kwerendy()
        ile_ok += 1
        ile_kwerend += len(usuniete)

        QgsMessageLog.logMessage(
            f'Usunięto {len(usuniete)} kwerend\n' + 20*'-',
            'Las-R', Qgis.Info
        )

    iface.messageBar().pushMessage(
        'OK',
        f'Przetworzono baz: {ile_ok}, usunięto kwerend łącznie: {ile_kwerend}',
        Qgis.Success,
        10
    )
