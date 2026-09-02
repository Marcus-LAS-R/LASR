"""Dialog "Utwórz KLON.txt" - na podstawie warstwy odcinków "Klon" i
warstwy wydzieleń WYDZ buduje plik instrukcji do narzędzia "Klonuj opisy
wydzieleń" (baza_klonuj_wydz.py).

Domyślnie warstwa odcinków to pierwsza liniowa warstwa nazwana "Klon",
a warstwa wydzieleń to pierwsza poligonowa warstwa nazwana "WYDZ".
"""

import os

from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
    QMessageBox, QVBoxLayout,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

from ..core import utworz_klon_txt as logika


def _warstwy_wektorowe(typ_geometrii):
    return [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if isinstance(lyr, QgsVectorLayer)
        and lyr.geometryType() == typ_geometrii
    ]


class UtworzKlonTxtDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Utwórz KLON.txt")
        self.setMinimumSize(480, 160)
        self._odcinki = []
        self._wydzielenia = []
        self._build_ui()
        self._wczytaj_warstwy()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Buduje plik KLON.txt (do wczytania w \"Klonuj opisy "
            "wydzieleń\") na podstawie odcinków warstwy Klon - początek "
            "odcinka to wydzielenie źródłowe, koniec to docelowe.\n"
            "Oba końce każdego odcinka muszą leżeć na wydzieleniu WYDZ, nie "
            "mogą leżeć w tym samym poligonie, a kilka źródeł klonujących "
            "do tego samego celu jest błędem."
        ))

        klon_row = QHBoxLayout()
        klon_row.addWidget(QLabel("Warstwa odcinków (Klon):"))
        self.combo_klon = QComboBox()
        klon_row.addWidget(self.combo_klon, 1)
        layout.addLayout(klon_row)

        wydz_row = QHBoxLayout()
        wydz_row.addWidget(QLabel("Warstwa wydzieleń (WYDZ):"))
        self.combo_wydz = QComboBox()
        wydz_row.addWidget(self.combo_wydz, 1)
        layout.addLayout(wydz_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Utwórz KLON.txt")
        buttons.accepted.connect(self._uruchom)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _wczytaj_warstwy(self):
        self._odcinki = _warstwy_wektorowe(QgsWkbTypes.LineGeometry)
        self._wydzielenia = _warstwy_wektorowe(QgsWkbTypes.PolygonGeometry)

        self.combo_klon.addItems([lyr.name() for lyr in self._odcinki])
        self.combo_wydz.addItems([lyr.name() for lyr in self._wydzielenia])

        if self._odcinki:
            i = next(
                (i for i, lyr in enumerate(self._odcinki)
                 if lyr.name().upper() == 'KLON'), 0)
            self.combo_klon.setCurrentIndex(i)

        if self._wydzielenia:
            i = next(
                (i for i, lyr in enumerate(self._wydzielenia)
                 if lyr.name().upper() == 'WYDZ'), 0)
            self.combo_wydz.setCurrentIndex(i)

    def _wybrany_klon(self):
        i = self.combo_klon.currentIndex()
        return self._odcinki[i] if 0 <= i < len(self._odcinki) else None

    def _wybrane_wydz(self):
        i = self.combo_wydz.currentIndex()
        return self._wydzielenia[i] if 0 <= i < len(self._wydzielenia) else None

    def _domyslna_sciezka(self, klon_lyr):
        try:
            zrodlo = klon_lyr.dataProvider().dataSourceUri().split('|')[0]
            if zrodlo and os.path.isfile(zrodlo):
                return os.path.join(os.path.dirname(zrodlo), 'KLON.txt')
        except Exception:
            pass
        return 'KLON.txt'

    def _uruchom(self):
        klon = self._wybrany_klon()
        wydz = self._wybrane_wydz()
        if klon is None or wydz is None:
            QMessageBox.warning(
                self, "Brak warstw",
                "W projekcie brakuje warstwy liniowej (Klon) i/lub "
                "poligonowej (WYDZ).")
            return

        wynik = logika.wykonaj(klon, wydz)
        if not wynik['ok']:
            QMessageBox.warning(self, "Popraw warstwę Klon", wynik['komunikat'])
            return

        if not wynik['pary']:
            QMessageBox.information(
                self, "Brak odcinków",
                "Warstwa Klon nie zawiera żadnych odcinków do przetworzenia.")
            return

        sciezka, _ = QFileDialog.getSaveFileName(
            self, "Zapisz KLON.txt", self._domyslna_sciezka(klon),
            "Plik tekstowy (*.txt)")
        if not sciezka:
            return

        logika.zapisz_plik(wynik['pary'], sciezka)
        QMessageBox.information(
            self, "OK",
            f"Zapisano {len(wynik['pary'])} par adresów do pliku:\n{sciezka}")
        self.accept()
