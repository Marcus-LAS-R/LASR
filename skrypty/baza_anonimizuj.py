import os
import glob
import shutil
from PyQt5.QtWidgets import QFileDialog, QDialog

from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza
from .ui.ui_baza_anonimizuj import Ui_Dialog


def Anonimizuj(iface):
    dlg = QDialog(iface.mainWindow())
    ui = Ui_Dialog()
    ui.setupUi(dlg)
    ui.pushButton_ok.clicked.connect(dlg.accept)
    ui.pushButton_cancel.clicked.connect(dlg.reject)
    if dlg.exec_() != QDialog.Accepted:
        return

    usun_kwerendy = ui.checkBox_kwerendy.isChecked()

    bazy_kat = QFileDialog().getExistingDirectory(
        iface.mainWindow(),
        "Katalog z bazami danych",
        '')
    if not bazy_kat:
        return
    bazy_sc = glob.glob(os.path.join(bazy_kat, '*.mdb'))
    if len(bazy_sc) == 0:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie znalazłem żadnej bazy taksatora... (mdb ma byc malymi literami!)',
            Qgis.Critical,
            10
        )
        return

    ile_ok = 0
    for sc in bazy_sc:
        nazwa = os.path.splitext(os.path.basename(sc))[0]
        sc_bdo = os.path.join(os.path.dirname(sc), nazwa + '_BDO.mdb')

        shutil.copy2(sc, sc_bdo)

        baza = Baza(sc_bdo)
        if not baza.polacz():
            QgsMessageLog.logMessage(
                'Nie mogłem połączyć się z bazą: ' + sc_bdo,
                'Las-R'
            )
            continue

        QgsMessageLog.logMessage(
            '\n' + 20*'-' + '\nPrzetwarzam bazę: ' + sc_bdo,
            'Las-R', Qgis.Info
        )

        baza.anonimizuj_vaddress()
        if usun_kwerendy:
            baza.usun_kwerendy()
        ile_ok += 1

        QgsMessageLog.logMessage('\n' + 20*'-', 'Las-R', Qgis.Info)

    iface.messageBar().pushMessage(
        'OK',
        'Zanonimizowanych baz: ' + str(ile_ok),
        Qgis.Success,
        10
    )
