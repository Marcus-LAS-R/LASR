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
    QComboBox, QDialog, QHBoxLayout, QLabel, QVBoxLayout,
)
from ...przyciski import QDialogButtonBox, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

from ..core import utworz_klon_txt as logika
from ...funkcje import etykiety_warstw, indeks_domyslnej


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

        self.combo_klon.addItems(etykiety_warstw(self._odcinki))
        self.combo_notatki.addItems(etykiety_warstw(self._notatki))
        self.combo_wydz.addItems(etykiety_warstw(self._wydzielenia))

        # domyślnie warstwa aktywna albo z obiektu aktywnej (funkcje.
        # indeks_domyslnej); bez dopasowania nazwy - brak wyboru
        self.combo_klon.setCurrentIndex(indeks_domyslnej(
            self._odcinki, lambda lyr: lyr.name().upper() == 'OPIS_KLON'))
        self.combo_notatki.setCurrentIndex(indeks_domyslnej(
            self._notatki, lambda lyr: lyr.name().upper() == 'OPIS_NOTATKI'))
        self.combo_wydz.setCurrentIndex(indeks_domyslnej(
            self._wydzielenia, lambda lyr: lyr.name().upper() == 'WYDZ'))

    def _wybrany_klon(self):
        i = self.combo_klon.currentIndex()
        return self._odcinki[i] if 0 <= i < len(self._odcinki) else None

    def _wybrane_notatki(self):
        i = self.combo_notatki.currentIndex()
        return self._notatki[i] if 0 <= i < len(self._notatki) else None

    def _wybrane_wydz(self):
        i = self.combo_wydz.currentIndex()
        return self._wydzielenia[i] if 0 <= i < len(self._wydzielenia) else None

    def _domyslny_katalog_raportow(self, wydz_lyr, klon_lyr):
        """Katalog "na poziomie SHP i bazy" - bez pytania użytkownika o
        lokalizację, ten sam wzorzec co warstwa_opisow_dock._folder_opis():
        najpierw folder samego (zapisanego) projektu QGIS, w przeciwnym
        razie folder nadrzędny względem SHP wybranej warstwy WYDZ (a gdy
        i to zawiedzie - względem warstwy Klon, np. gdy leży w SHP_opis
        obok, ale WYDZ akurat nie ma pliku na dysku)."""
        projekt = QgsProject.instance().absolutePath()
        if projekt:
            return projekt

        for lyr in (wydz_lyr, klon_lyr):
            try:
                zrodlo = lyr.dataProvider().dataSourceUri().split('|')[0]
                if zrodlo and os.path.isfile(zrodlo):
                    return os.path.dirname(os.path.dirname(zrodlo))
            except Exception:
                continue
        return ''

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

        katalog = self._domyslny_katalog_raportow(wydz, klon)
        if not katalog:
            QMessageBox.warning(
                self, "Brak lokalizacji",
                "Nie udało się ustalić lokalizacji projektu/warstw na "
                "dysku - nie wiadomo, gdzie zapisać raporty. Zapisz "
                "projekt QGIS na dysku i spróbuj ponownie.")
            return

        sciezka_klon = os.path.join(katalog, 'KLON.txt')
        sciezka_notatki = os.path.join(katalog, 'NOTATKI_zmiany.txt')

        logika.zapisz_plik(wynik_klon['pary'], sciezka_klon)
        logika.zapisz_plik(wynik_notatki['pary'], sciezka_notatki)

        QMessageBox.information(
            self, "OK",
            f"Zapisano {len(wynik_klon['pary'])} par adresów do:\n"
            f"{sciezka_klon}\n\n"
            f"Zapisano {len(wynik_notatki['pary'])} notatek do:\n"
            f"{sciezka_notatki}")
        self.accept()
