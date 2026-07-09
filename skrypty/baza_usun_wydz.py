import os
import glob

from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorLayer
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from .baza_wrapper import Baza
from . import kopie_manipulacyjne


class _WyborDialog(QDialog):
    """ Wybór warstwy WYDZ (z TOC) i bazy Taksatora przed usunięciem -
    domyślnie ładuje warstwę nazwaną dokładnie "WYDZ", jeśli taka jest w
    projekcie, i próbuje samodzielnie zgadnąć bazę leżącą dwa poziomy
    wyżej (ten sam katalog, którego szukałaby stara wersja skryptu przez
    baza_wrapper.znajdz_baze_do_wydz z poz=2). """

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle('Skasuj wydzielenia w bazie')
        self.setMinimumWidth(480)

        self._warstwy = [
            lyr for lyr in QgsProject.instance().mapLayers().values()
            if isinstance(lyr, QgsVectorLayer)
        ]

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            'Wydzielenia, których nie ma już w zaznaczonej warstwie, '
            'zostaną trwale usunięte z bazy.'
        ))

        warstwa_row = QHBoxLayout()
        warstwa_row.addWidget(QLabel('Warstwa WYDZ:'))
        self.combo_warstwa = QComboBox()
        self.combo_warstwa.addItems([lyr.name() for lyr in self._warstwy])
        warstwa_row.addWidget(self.combo_warstwa, 1)
        layout.addLayout(warstwa_row)

        baza_row = QHBoxLayout()
        baza_row.addWidget(QLabel('Baza Taksatora:'))
        self.edit_baza = QLineEdit()
        baza_row.addWidget(self.edit_baza, 1)
        przegladaj_btn = QPushButton('Wybierz…')
        przegladaj_btn.clicked.connect(self._wybierz_baze)
        baza_row.addWidget(przegladaj_btn)
        layout.addLayout(baza_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self._warstwy:
            indeks = next(
                (i for i, lyr in enumerate(self._warstwy)
                 if lyr.name().upper() == 'WYDZ'), 0)
            self.combo_warstwa.setCurrentIndex(indeks)

        self.combo_warstwa.currentIndexChanged.connect(self._zgadnij_baze)
        self._zgadnij_baze()

    def _zgadnij_baze(self):
        lyr = self.warstwa()
        if lyr is None:
            return
        try:
            sc = lyr.dataProvider().dataSourceUri().split('|')[0]
            kat = os.path.dirname(sc)
            poziom = '..' if lyr.name().upper() == 'ODDZ' else os.path.join('..', '..')
            kandydaci = glob.glob(os.path.join(kat, poziom, '*.mdb'))
        except Exception:
            kandydaci = []
        if len(kandydaci) == 1:
            self.edit_baza.setText(os.path.abspath(kandydaci[0]))

    def _wybierz_baze(self):
        kat_start = os.path.dirname(self.edit_baza.text().strip())
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę Taksatora', kat_start,
            'Access MDB (*.mdb);;SQLite (*.sqlite)')
        if sc:
            self.edit_baza.setText(sc)

    def warstwa(self):
        i = self.combo_warstwa.currentIndex()
        return self._warstwy[i] if 0 <= i < len(self._warstwy) else None

    def baza_sc(self):
        return self.edit_baza.text().strip() or None


def usun_wydz(iface):
    dlg = _WyborDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False

    lyr = dlg.warstwa()

    if lyr is None or not lyr.isValid():
        iface.messageBar().pushMessage(
            "BŁĄD", "Zaznacz poprawną warstwę WYDZ", Qgis.Critical, 10
        )
        return False

    if "ADR_LES" not in [x.name() for x in lyr.fields()]:
        iface.messageBar().pushMessage(
            "BŁĄD", "W wybranej warstwie brakuje kolumny ADR_LES",
            Qgis.Critical, 10
        )
        return False

    baza_sc = dlg.baza_sc()
    if not baza_sc:
        iface.messageBar().pushMessage(
            "BRAK BAZY", "Bez bazy ani rusz!", Qgis.Critical, 10
        )
        return False

    baza = Baza(baza_sc)
    if not baza.polacz():
        iface.messageBar().pushMessage(
            "BAZA", "Nie mogłem podłączyć się do bazy", Qgis.Critical, 10
        )
        return False

    f_arod = baza.pobierz_wydzielenia()
    if f_arod is False:
        iface.messageBar().pushMessage(
            "BAZA", "Nie znalazłem żadnych wydzieleń w bazie", Qgis.Warning, 10
        )
        return False

    spis_wydz_lyr = [f["ADR_LES"] for f in lyr.getFeatures()]
    brak_baza = [vv for fi, vv in f_arod.items() if fi not in spis_wydz_lyr]

    QgsMessageLog.logMessage(
        'usun_wydz: w bazie ' + str(len(f_arod)) + ' wydzieleń, '
        'brakuje w warstwie ' + str(len(brak_baza)),
        'Las-R', Qgis.Info
    )

    if len(brak_baza) == 0:
        iface.messageBar().pushMessage(
            "BRAK", "Nie ma wydzieleń do usunięcia", Qgis.Warning, 10
        )
        return True

    tresc = (
        'W bazie znaleziono ' + str(len(brak_baza)) + ' wydzieleń, '
        'których nie ma już w zaznaczonej warstwie.\n\n'
        'Te wydzielenia zostaną TRWALE USUNIĘTE z bazy, wraz z '
        'powiązanymi rekordami (gatunki, zabiegi, błędy itd.), oraz '
        'opróżnionymi przez to oddziałami/leśnictwami.\n\n'
    )
    if len(brak_baza) == len(f_arod):
        tresc += (
            'UWAGA: to jest CAŁA zawartość wydzieleń w bazie (100%) - '
            'sprawdź, czy wskazano właściwą warstwę/bazę!\n\n'
        )
    tresc += (
        'Przed usunięciem zostanie zrobiona kopia bazy i warstwy WYDZ w '
        'folderze Kopie_manipulacyjne (w katalogu bazy), ale tej operacji '
        'nie da się wycofać inaczej, niż przywracając tę kopię.\n\n'
        'Czy na pewno usunąć?'
    )

    odp = QMessageBox.question(
        iface.mainWindow(),
        'Skasuj wydzielenia w bazie',
        tresc,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    if odp != QMessageBox.Yes:
        iface.messageBar().pushMessage(
            "PRZERWANO", "Nie usunięto żadnych rekordów", Qgis.Info, 10
        )
        return False

    folder_kopii = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
        baza_sc, [lyr], 'usun_wydz_z_bazy'
    )
    if folder_kopii is None:
        iface.messageBar().pushMessage(
            "BŁĄD", "Nie udało się utworzyć kopii bezpieczeństwa - "
            "przerwano, nic nie usunięto", Qgis.Critical, 10
        )
        return False

    res = baza.usun_rekordy(brak_baza)
    if res:
        iface.messageBar().pushMessage(
            "OK", "Usunięto " + str(len(brak_baza)) + " wydzieleń z bazy "
            "(kopia zapasowa zachowana)", Qgis.Success, 10
        )
        return True

    iface.messageBar().pushMessage(
        "BŁĄD", "Coś poszło nie tak, zmiany wycofane - sprawdź log Las-R",
        Qgis.Critical, 10
    )
    return False
