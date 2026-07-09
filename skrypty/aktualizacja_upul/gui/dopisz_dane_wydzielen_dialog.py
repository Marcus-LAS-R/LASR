"""Dialog "Dopisz dane do wydzieleń" - odpowiednik "Join attributes by
location" z QGIS Processing, ale zapisujący wynik bezpośrednio do
wskazanej warstwy docelowej (WYDZ) zamiast tworzyć nową warstwę.

Domyślnie warstwa źródłowa to pierwsza punktowa warstwa w projekcie,
której nazwa zawiera "stare" (np. WYDZ_PKT_stare), a docelowa to pierwsza
poligonowa warstwa nazwana "WYDZ" (bez "stare" w nazwie). Lista pól do
dopisania jest budowana dynamicznie z pól warstwy źródłowej - dla każdego
pola użytkownik wybiera osobno, czy uzupełniać tylko puste komórki, czy
zawsze nadpisywać wartością ze źródła.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit,
    QVBoxLayout, QWidget,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

from ..core import dopisz_dane_wydzielen as logika

_TRYBY = ["Uzupełnij puste", "Nadpisz"]
_TRYB_DO_KOD = {
    "Uzupełnij puste": logika.TRYB_PUSTE,
    "Nadpisz": logika.TRYB_NADPISZ,
}


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
        self.setMinimumSize(620, 480)
        self._zrodla = []
        self._cele = []
        self._build_ui()
        self._wczytaj_warstwy()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Dopisuje dane z warstwy punktowej (stare wydzielenia) do "
            "warstwy poligonowej (nowe wydzielenia) na podstawie "
            "położenia punktu wewnątrz poligonu.\n"
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

        layout.addWidget(QLabel("Pola do dopisania:"))
        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels(["Dopisz", "Pole", "Tryb"])
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.setColumnWidth(0, 60)
        self.tabela.setColumnWidth(1, 220)
        layout.addWidget(self.tabela)

        zaznacz_row = QHBoxLayout()
        zaznacz_btn = QPushButton("Zaznacz wszystkie")
        zaznacz_btn.clicked.connect(lambda: self._zaznacz_wszystkie(True))
        zaznacz_row.addWidget(zaznacz_btn)
        odznacz_btn = QPushButton("Odznacz wszystkie")
        odznacz_btn.clicked.connect(lambda: self._zaznacz_wszystkie(False))
        zaznacz_row.addWidget(odznacz_btn)
        layout.addLayout(zaznacz_row)

        self.combo_zrodlo.currentIndexChanged.connect(self._wypelnij_pola)

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

        self._wypelnij_pola()

    def _wypelnij_pola(self):
        self.tabela.setRowCount(0)
        lyr = self._wybrane_zrodlo()
        if lyr is None:
            return
        for pole in lyr.fields():
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)

            chk = QCheckBox()
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.addWidget(chk)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            self.tabela.setCellWidget(row, 0, chk_widget)

            nazwa_item = QTableWidgetItem(pole.name())
            nazwa_item.setFlags(nazwa_item.flags() & ~Qt.ItemIsEditable)
            self.tabela.setItem(row, 1, nazwa_item)

            combo_tryb = QComboBox()
            combo_tryb.addItems(_TRYBY)
            self.tabela.setCellWidget(row, 2, combo_tryb)

    def _zaznacz_wszystkie(self, stan):
        for row in range(self.tabela.rowCount()):
            self.tabela.cellWidget(row, 0).findChild(QCheckBox).setChecked(stan)

    def _wybrane_zrodlo(self):
        i = self.combo_zrodlo.currentIndex()
        return self._zrodla[i] if 0 <= i < len(self._zrodla) else None

    def _wybrany_cel(self):
        i = self.combo_cel.currentIndex()
        return self._cele[i] if 0 <= i < len(self._cele) else None

    def _wybor_pol(self):
        wybor = []
        for row in range(self.tabela.rowCount()):
            chk = self.tabela.cellWidget(row, 0).findChild(QCheckBox)
            if not chk.isChecked():
                continue
            nazwa = self.tabela.item(row, 1).text()
            tryb_tekst = self.tabela.cellWidget(row, 2).currentText()
            wybor.append((nazwa, _TRYB_DO_KOD[tryb_tekst]))
        return wybor

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

        wybor_pol = self._wybor_pol()
        if not wybor_pol:
            QMessageBox.warning(
                self, "Brak pól",
                "Zaznacz przynajmniej jedno pole do dopisania.")
            return

        raport = logika.wykonaj(zrodlo, cel, wybor_pol)
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
