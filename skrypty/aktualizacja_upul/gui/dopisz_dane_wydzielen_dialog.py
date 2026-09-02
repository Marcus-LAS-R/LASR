"""Dialog "Dopisz dane do wydzieleń" - odpowiednik "Join attributes by
location" z QGIS Processing, ale zapisujący wynik bezpośrednio do
wskazanej warstwy docelowej (WYDZ) zamiast tworzyć nową warstwę.

Domyślnie warstwa źródłowa to pierwsza punktowa warstwa w projekcie,
której nazwa zawiera "stare" (np. WYDZ_PKT_stare), a docelowa to pierwsza
poligonowa warstwa nazwana "WYDZ" (bez "stare" w nazwie). Dopisywane są
zawsze tylko pola ODDZ i WYDZ (tryb: uzupełnij puste).
"""

from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

from ..core import dopisz_dane_wydzielen as logika

_POLA_DOPISYWANE = [
    ('ODDZ', logika.TRYB_PUSTE),
    ('WYDZ', logika.TRYB_PUSTE),
]


def _warstwy_wektorowe(typ_geometrii):
    return [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if isinstance(lyr, QgsVectorLayer)
        and lyr.geometryType() == typ_geometrii
    ]


class DopiszDaneWydzielenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dopisz dane do wydzieleń")
        self.setMinimumSize(480, 160)
        self._zrodla = []
        self._cele = []
        self._build_ui()
        self._wczytaj_warstwy()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Dopisuje ODDZ i WYDZ z warstwy punktowej (stare wydzielenia) "
            "do warstwy poligonowej (nowe wydzielenia) na podstawie "
            "położenia punktu wewnątrz poligonu — tylko tam, gdzie pole "
            "docelowe jest puste.\n"
            "Wydzielenia, w których trafi więcej niż jeden stary punkt "
            "(scalenie), są pomijane i zgłoszone w raporcie."
        ))

        zrodlo_row = QHBoxLayout()
        zrodlo_row.addWidget(QLabel("Warstwa źródłowa (stare punkty):"))
        self.combo_zrodlo = QComboBox()
        zrodlo_row.addWidget(self.combo_zrodlo, 1)
        layout.addLayout(zrodlo_row)

        cel_row = QHBoxLayout()
        cel_row.addWidget(QLabel("Warstwa docelowa (WYDZ):"))
        self.combo_cel = QComboBox()
        cel_row.addWidget(self.combo_cel, 1)
        layout.addLayout(cel_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Dopisz dane")
        buttons.accepted.connect(self._uruchom)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _wczytaj_warstwy(self):
        self._zrodla = _warstwy_wektorowe(QgsWkbTypes.PointGeometry)
        self._cele = _warstwy_wektorowe(QgsWkbTypes.PolygonGeometry)

        self.combo_zrodlo.addItems([lyr.name() for lyr in self._zrodla])
        self.combo_cel.addItems([lyr.name() for lyr in self._cele])

        if self._zrodla:
            indeks_zrodlo = next(
                (i for i, lyr in enumerate(self._zrodla)
                 if 'stare' in lyr.name().lower()), 0)
            self.combo_zrodlo.setCurrentIndex(indeks_zrodlo)

        if self._cele:
            indeks_cel = next(
                (i for i, lyr in enumerate(self._cele)
                 if lyr.name().upper().startswith('WYDZ')
                 and 'stare' not in lyr.name().lower()), 0)
            self.combo_cel.setCurrentIndex(indeks_cel)

    def _wybrane_zrodlo(self):
        i = self.combo_zrodlo.currentIndex()
        return self._zrodla[i] if 0 <= i < len(self._zrodla) else None

    def _wybrany_cel(self):
        i = self.combo_cel.currentIndex()
        return self._cele[i] if 0 <= i < len(self._cele) else None

    def _uruchom(self):
        zrodlo = self._wybrane_zrodlo()
        cel = self._wybrany_cel()
        if zrodlo is None or cel is None:
            QMessageBox.warning(
                self, "Brak warstw",
                "W projekcie brakuje warstwy punktowej i/lub poligonowej "
                "do wskazania jako źródło/cel.")
            return
        if zrodlo is cel:
            QMessageBox.warning(
                self, "Ta sama warstwa",
                "Warstwa źródłowa i docelowa muszą być różne.")
            return

        raport = logika.wykonaj(zrodlo, cel, _POLA_DOPISYWANE)
        self._pokaz_raport(raport)
        self.accept()

    def _pokaz_raport(self, raport):
        linie = [
            "RAPORT — DOPISZ DANE DO WYDZIELEŃ", "=" * 40, "",
            f"Zaktualizowanych wydzieleń: {raport['zaktualizowane']}",
        ]

        if raport['zmiany_na_pole']:
            linie.append("")
            linie.append("Zmienione wartości per pole:")
            for nazwa, ile in raport['zmiany_na_pole'].items():
                linie.append(f"  {nazwa}: {ile}")

        if raport['pola_pominiete']:
            linie.append("")
            linie.append(
                "Pola pominięte (brak takiej kolumny w warstwie "
                "docelowej):")
            for nazwa in raport['pola_pominiete']:
                linie.append(f"  {nazwa}")

        if raport['scalenia_pominiete']:
            linie.append("")
            linie.append(
                "Pominięte wydzielenia ze scaleniem (więcej niż jeden "
                f"stary punkt w środku) — {len(raport['scalenia_pominiete'])}:")
            for etykieta in raport['scalenia_pominiete']:
                linie.append(f"  {etykieta}")

        dialog = QDialog(self.parent())
        dialog.setWindowTitle("Raport")
        dialog.setMinimumSize(520, 420)
        lay = QVBoxLayout(dialog)
        pole = QTextEdit()
        pole.setReadOnly(True)
        pole.setPlainText("\n".join(linie))
        lay.addWidget(pole)
        zamknij = QPushButton("Zamknij")
        zamknij.clicked.connect(dialog.accept)
        lay.addWidget(zamknij)
        dialog.exec_()
