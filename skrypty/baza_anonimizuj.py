import os
import glob
import shutil
from PyQt5.QtWidgets import QFileDialog, QDialog

from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza
from .ui.ui_baza_anonimizuj import Ui_Dialog


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.pushButton_folder.clicked.connect(self._wybierz_folder)
        self.ui.lineEdit_folder.textChanged.connect(self._aktualizuj)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        self._aktualizuj()

    def _wybierz_folder(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Katalog z bazami danych', self.ui.lineEdit_folder.text())
        if sc:
            self.ui.lineEdit_folder.setText(sc)

    def _aktualizuj(self):
        self.ui.pushButton_ok.setEnabled(
            os.path.isdir(self.ui.lineEdit_folder.text().strip()))

    def folder(self):
        return self.ui.lineEdit_folder.text().strip()

    def usun_kwerendy(self):
        return self.ui.checkBox_kwerendy.isChecked()


def Anonimizuj(iface):
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return

    bazy_kat = dlg.folder()
    usun_kwerendy = dlg.usun_kwerendy()

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
