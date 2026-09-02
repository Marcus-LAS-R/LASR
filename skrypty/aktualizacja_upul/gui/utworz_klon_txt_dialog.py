"""Dialog "Utwórz raporty KLON i NOTATKI" - na podstawie warstwy odcinków
"Klon", warstwy punktowej notatek (opis_notatki) i warstwy wydzieleń WYDZ
buduje dwa pliki: KLON.txt (instrukcja dla "Klonuj opisy wydzieleń",
baza_klonuj_wydz.py) oraz NOTATKI_zmiany.txt (adres leśny TAB treść
notatki).

Domyślnie warstwa odcinków to pierwsza liniowa warstwa nazwana
"OPIS_KLON", warstwa notatek to pierwsza punktowa warstwa nazwana
"OPIS_NOTATKI", a warstwa wydzieleń to pierwsza poligonowa warstwa
nazwana "WYDZ".

Obie kontrole (Klon i notatki) muszą przejść, zanim cokolwiek zostanie
zapisane - błąd w jednej blokuje zapis OBU plików (patrz
`logika.wykonaj` i `logika.wykonaj_notatki`).
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
        self.setWindowTitle("Utwórz raporty KLON i NOTATKI")
        self.setMinimumSize(480, 200)
        self._odcinki = []
        self._notatki = []
        self._wydzielenia = []
        self._build_ui()
        self._wczytaj_warstwy()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Buduje KLON.txt (do wczytania w \"Klonuj opisy wydzieleń\") "
            "na podstawie odcinków warstwy Klon - początek odcinka to "
            "wydzielenie źródłowe, koniec to docelowe - oraz "
            "NOTATKI_zmiany.txt (adres leśny + treść notatki) na "
            "podstawie warstwy punktowej notatek.\n"
            "Oba końce każdego odcinka Klon muszą leżeć na wydzieleniu "
            "WYDZ, nie mogą leżeć w tym samym poligonie, a kilka źródeł "
            "klonujących do tego samego celu jest błędem. Każdy punkt "
            "notatek musi leżeć na jakimś WYDZ (kilka notatek na jednym "
            "wydzieleniu jest dopuszczalne). Błąd w którejkolwiek warstwie "
            "blokuje zapis obu plików."
        ))

        klon_row = QHBoxLayout()
        klon_row.addWidget(QLabel("Warstwa odcinków (opis_klon):"))
        self.combo_klon = QComboBox()
        klon_row.addWidget(self.combo_klon, 1)
        layout.addLayout(klon_row)

        notatki_row = QHBoxLayout()
        notatki_row.addWidget(QLabel("Warstwa notatek (opis_notatki):"))
        self.combo_notatki = QComboBox()
        notatki_row.addWidget(self.combo_notatki, 1)
        layout.addLayout(notatki_row)

        wydz_row = QHBoxLayout()
        wydz_row.addWidget(QLabel("Warstwa wydzieleń (WYDZ):"))
        self.combo_wydz = QComboBox()
        wydz_row.addWidget(self.combo_wydz, 1)
        layout.addLayout(wydz_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Utwórz raporty")
        buttons.accepted.connect(self._uruchom)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _wczytaj_warstwy(self):
        self._odcinki = _warstwy_wektorowe(QgsWkbTypes.LineGeometry)
        self._notatki = _warstwy_wektorowe(QgsWkbTypes.PointGeometry)
        self._wydzielenia = _warstwy_wektorowe(QgsWkbTypes.PolygonGeometry)

        self.combo_klon.addItems([lyr.name() for lyr in self._odcinki])
        self.combo_notatki.addItems([lyr.name() for lyr in self._notatki])
        self.combo_wydz.addItems([lyr.name() for lyr in self._wydzielenia])

        if self._odcinki:
            i = next(
                (i for i, lyr in enumerate(self._odcinki)
                 if lyr.name().upper() == 'OPIS_KLON'), 0)
            self.combo_klon.setCurrentIndex(i)

        if self._notatki:
            i = next(
                (i for i, lyr in enumerate(self._notatki)
                 if lyr.name().upper() == 'OPIS_NOTATKI'), 0)
            self.combo_notatki.setCurrentIndex(i)

        if self._wydzielenia:
            i = next(
                (i for i, lyr in enumerate(self._wydzielenia)
                 if lyr.name().upper() == 'WYDZ'), 0)
            self.combo_wydz.setCurrentIndex(i)

    def _wybrany_klon(self):
        i = self.combo_klon.currentIndex()
        return self._odcinki[i] if 0 <= i < len(self._odcinki) else None

    def _wybrane_notatki(self):
        i = self.combo_notatki.currentIndex()
        return self._notatki[i] if 0 <= i < len(self._notatki) else None

    def _wybrane_wydz(self):
        i = self.combo_wydz.currentIndex()
        return self._wydzielenia[i] if 0 <= i < len(self._wydzielenia) else None

    def _domyslna_sciezka(self, lyr, nazwa_pliku):
        try:
            zrodlo = lyr.dataProvider().dataSourceUri().split('|')[0]
            if zrodlo and os.path.isfile(zrodlo):
                return os.path.join(os.path.dirname(zrodlo), nazwa_pliku)
        except Exception:
            pass
        return nazwa_pliku

    def _uruchom(self):
        klon = self._wybrany_klon()
        notatki = self._wybrane_notatki()
        wydz = self._wybrane_wydz()
        if klon is None or notatki is None or wydz is None:
            QMessageBox.warning(
                self, "Brak warstw",
                "W projekcie brakuje warstwy liniowej (Klon), punktowej "
                "(notatki) i/lub poligonowej (WYDZ).")
            return

        wynik_klon = logika.wykonaj(klon, wydz)
        wynik_notatki = logika.wykonaj_notatki(notatki, wydz)

        if not wynik_klon['ok'] or not wynik_notatki['ok']:
            komunikaty = []
            if not wynik_klon['ok']:
                komunikaty.append(wynik_klon['komunikat'])
            if not wynik_notatki['ok']:
                komunikaty.append(wynik_notatki['komunikat'])
            QMessageBox.warning(
                self, "Popraw dane", '\n\n'.join(komunikaty))
            return

        if not wynik_klon['pary'] and not wynik_notatki['pary']:
            QMessageBox.information(
                self, "Brak danych",
                "Warstwa Klon i warstwa notatek nie zawierają żadnych "
                "danych do przetworzenia.")
            return

        sciezka_klon, _ = QFileDialog.getSaveFileName(
            self, "Zapisz KLON.txt",
            self._domyslna_sciezka(klon, 'KLON.txt'), "Plik tekstowy (*.txt)")
        if not sciezka_klon:
            return

        sciezka_notatki = os.path.join(
            os.path.dirname(sciezka_klon), 'NOTATKI_zmiany.txt')

        logika.zapisz_plik(wynik_klon['pary'], sciezka_klon)
        logika.zapisz_plik(wynik_notatki['pary'], sciezka_notatki)

        QMessageBox.information(
            self, "OK",
            f"Zapisano {len(wynik_klon['pary'])} par adresów do:\n"
            f"{sciezka_klon}\n\n"
            f"Zapisano {len(wynik_notatki['pary'])} notatek do:\n"
            f"{sciezka_notatki}")
        self.accept()
