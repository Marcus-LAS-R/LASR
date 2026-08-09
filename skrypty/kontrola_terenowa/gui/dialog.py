"""Dialog "Materiały do kontroli terenowej".

Wejście: warstwa, która zawiera WYŁĄCZNIE kontrolowane wydzielenia (nie
ma wymogu konkretnej nazwy, nie wymaga zaznaczenia ani obecności w
bieżącym projekcie - brane są wszystkie jej obiekty), DZKAT, OBR,
warstwa Nadleśnictw (pole `ins_name`), katalog z bazami .mdb i katalog
docelowy. Logika przebiegu jest w core/przetworz.py - ten plik tylko
zbiera dane z widżetów i pokazuje raport na koniec.

Każda z 4 warstw ma osobny picker (combo + przycisk "Z pliku…") -
domyślnie wypełniony warstwami poligonowymi z bieżącego projektu, ale
niezależnie od tego można wczytać dowolny .shp z dysku bez dodawania go
do projektu.
"""

import os

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout,
)
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

from ..core import baza_finder
from ..core import przetworz as logika

POLE_NAZWA_NADL = 'ins_name'


def _warstwy_poligonowe_z_toc():
    return [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if isinstance(lyr, QgsVectorLayer)
        and lyr.geometryType() == QgsWkbTypes.PolygonGeometry
    ]


def _domyslny_indeks(warstwy, fragmenty):
    for frag in fragmenty:
        for i, lyr in enumerate(warstwy):
            if frag in lyr.name().lower():
                return i
    return 0


class _WarstwaPicker:
    """Combo + przycisk "Z pliku…" do wskazania jednej warstwy - domyślnie
    z TOC bieżącego projektu, albo doładowywalnej z dowolnego pliku .shp
    bez dodawania go do projektu."""

    def __init__(self, parent_widget, layout, etykieta, fragmenty_domyslne,
                 warstwy_toc):
        self._parent = parent_widget
        self._warstwy = list(warstwy_toc)

        row = QHBoxLayout()
        row.addWidget(QLabel(etykieta))

        self.combo = QComboBox()
        self.combo.addItems([lyr.name() for lyr in self._warstwy])
        if self._warstwy:
            self.combo.setCurrentIndex(
                _domyslny_indeks(self._warstwy, fragmenty_domyslne))
        row.addWidget(self.combo, 1)

        btn = QPushButton('Z pliku…')
        btn.clicked.connect(self._z_pliku)
        row.addWidget(btn)

        layout.addLayout(row)

    def _z_pliku(self):
        sciezka, _ = QFileDialog.getOpenFileName(
            self._parent, 'Wskaż warstwę', '', 'ESRI shp (*.shp)')
        if not sciezka:
            return

        lyr = QgsVectorLayer(
            sciezka, os.path.splitext(os.path.basename(sciezka))[0], 'ogr')
        if not lyr.isValid():
            QMessageBox.warning(
                self._parent, 'Błąd',
                'Nie udało się wczytać warstwy:\n' + sciezka)
            return

        self._warstwy.append(lyr)
        self.combo.addItem(lyr.name())
        self.combo.setCurrentIndex(self.combo.count() - 1)

    def wybrana(self):
        i = self.combo.currentIndex()
        return self._warstwy[i] if 0 <= i < len(self._warstwy) else None


class KontrolaTerenowaDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle('Materiały do kontroli terenowej')
        self.setMinimumSize(620, 460)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        opis = QLabel(
            'Generuje dla wydzieleń z warstwy kontrolowanych wydzieleń '
            '(wszystkie jej obiekty): tabelę opisu taksacyjnego (OT), '
            'protokół kontroli terenowej i eksport KML. Warstwy '
            'domyślnie z bieżącego projektu, przyciskiem "Z pliku…" '
            'można wczytać dowolny .shp z dysku.'
        )
        opis.setWordWrap(True)
        layout.addWidget(opis)

        warstwy_toc = _warstwy_poligonowe_z_toc()

        self.picker_wydz = _WarstwaPicker(
            self, layout, 'Warstwa kontrolowanych wydzieleń (wszystkie obiekty):',
            ['wydz_kontrola', 'kontrola'], warstwy_toc)
        self.picker_dzkat = _WarstwaPicker(
            self, layout, 'Warstwa DZKAT:', ['dzkat'], warstwy_toc)
        self.picker_obr = _WarstwaPicker(
            self, layout, 'Warstwa OBR:', ['obr'], warstwy_toc)
        self.picker_nadl = _WarstwaPicker(
            self, layout, 'Warstwa Nadleśnictw:',
            ['inspectorate', 'nadlesnictw'], warstwy_toc)

        row = QHBoxLayout()
        row.addWidget(QLabel('Katalog z bazami (*.mdb):'))
        self.pole_bazy = QLineEdit()
        self.pole_bazy.setPlaceholderText(
            'Wpisz/wklej ścieżkę albo wskaż przyciskiem…')
        row.addWidget(self.pole_bazy, 1)
        btn_bazy = QPushButton('Wskaż...')
        btn_bazy.clicked.connect(self._wybierz_katalog_bazami)
        row.addWidget(btn_bazy)
        layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel('Katalog docelowy (OT / protokoły):'))
        self.pole_docelowy = QLineEdit()
        self.pole_docelowy.setPlaceholderText(
            'Wpisz/wklej ścieżkę albo wskaż przyciskiem…')
        row.addWidget(self.pole_docelowy, 1)
        btn_doc = QPushButton('Wskaż...')
        btn_doc.clicked.connect(self._wybierz_katalog_docelowy)
        row.addWidget(btn_doc)
        layout.addLayout(row)

        self.chk_ot_razem = QCheckBox(
            'OT: jeden wspólny plik (zamiast osobno na Nadleśnictwo)')
        layout.addWidget(self.chk_ot_razem)

        self.chk_protokol_razem = QCheckBox(
            'Protokół: jeden wspólny plik (zamiast osobno na Nadleśnictwo)')
        layout.addWidget(self.chk_protokol_razem)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('Generuj')
        buttons.accepted.connect(self._uruchom)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _wybierz_katalog_bazami(self):
        # Zwykly natywny wybor folderu - wersja z widocznymi (wyszarzonymi)
        # plikami .mdb w tle (jak w baza_polacz.PolaczBazy.pobierz_katalog())
        # ma w Qt problem z wklejaniem sciezki do pola Directory, wiec
        # rezygnujemy z tej wygody na rzecz normalnego wklejania
        kat = QFileDialog.getExistingDirectory(
            self, 'Katalog z bazami danych', self.pole_bazy.text().strip())
        if kat:
            self.pole_bazy.setText(kat)

    def _wybierz_katalog_docelowy(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Katalog docelowy', self.pole_bazy.text().strip())
        if kat:
            self.pole_docelowy.setText(kat)

    def _uruchom(self):
        wydz = self.picker_wydz.wybrana()
        dzkat = self.picker_dzkat.wybrana()
        obr = self.picker_obr.wybrana()
        nadl = self.picker_nadl.wybrana()

        if None in (wydz, dzkat, obr, nadl):
            QMessageBox.warning(
                self, 'Brak warstw',
                'Wskaż wszystkie wymagane warstwy (wydzielenia, DZKAT, '
                'OBR, Nadleśnictwa).')
            return

        if len({id(wydz), id(dzkat), id(obr), id(nadl)}) != 4:
            QMessageBox.warning(
                self, 'Powtórzona warstwa',
                'Warstwa wydzieleń, DZKAT, OBR i Nadleśnictwa muszą być '
                'różnymi warstwami.')
            return

        if wydz.featureCount() == 0:
            QMessageBox.warning(
                self, 'Pusta warstwa',
                'Warstwa kontrolowanych wydzieleń nie ma żadnych '
                'obiektów.')
            return

        if POLE_NAZWA_NADL not in [f.name() for f in nadl.fields()]:
            QMessageBox.warning(
                self, 'Brak pola',
                'Warstwa Nadleśnictw nie ma pola "' + POLE_NAZWA_NADL + '".')
            return

        katalog_bazami = self.pole_bazy.text().strip()
        katalog_docelowy = self.pole_docelowy.text().strip()

        if not katalog_bazami or not os.path.isdir(katalog_bazami):
            QMessageBox.warning(
                self, 'Brak katalogu', 'Wskaż katalog z bazami (.mdb).')
            return

        if not baza_finder.znajdz_bazy(katalog_bazami):
            QMessageBox.warning(
                self, 'Brak baz',
                'We wskazanym katalogu nie znaleziono żadnego pliku '
                '.mdb:\n' + katalog_bazami)
            return

        if not katalog_docelowy:
            QMessageBox.warning(
                self, 'Brak katalogu', 'Wskaż katalog docelowy.')
            return

        try:
            import docxtpl  # noqa: F401
        except ImportError:
            QMessageBox.critical(
                self, 'Brak pakietu docxtpl',
                'Do generowania plików .docx wymagany jest pakiet '
                'docxtpl. Zainstaluj go w Pythonie QGIS-a (powłoka '
                'OSGeo4W):\n\npython -m pip install docxtpl')
            return

        raport = logika.uruchom(
            self.iface, wydz, dzkat, obr, nadl, POLE_NAZWA_NADL,
            katalog_bazami, katalog_docelowy,
            self.chk_ot_razem.isChecked(), self.chk_protokol_razem.isChecked(),
        )
        self._pokaz_raport(raport)
        self.accept()

    def _pokaz_raport(self, raport):
        linie = ['MATERIAŁY DO KONTROLI TERENOWEJ', '=' * 40, '']

        linie.append('Pliki OT: ' + str(len(raport.pliki_ot)))
        for p in raport.pliki_ot:
            linie.append('  ' + p)

        linie.append('')
        linie.append('Pliki protokołów: ' + str(len(raport.pliki_protokol)))
        for p in raport.pliki_protokol:
            linie.append('  ' + p)

        linie.append('')
        if raport.plik_dzkat_kontrola:
            linie.append('DZKAT_kontrola: ' + raport.plik_dzkat_kontrola)
        else:
            linie.append('DZKAT_kontrola: nie powstał (patrz błędy KML niżej)')

        if raport.bledy_kml:
            linie.append('')
            linie.append('Błędy KML:')
            for b in raport.bledy_kml:
                linie.append('  ' + b)

        if raport.niedopasowane_baza:
            linie.append('')
            linie.append(
                'Wydzielenia bez dopasowanej bazy (pominięte w OT i '
                'protokole) — ' + str(len(raport.niedopasowane_baza)) + ':')
            for e in raport.niedopasowane_baza:
                linie.append('  ' + e)

        if raport.niedopasowane_nadl:
            linie.append('')
            linie.append(
                'Wydzielenia bez dopasowanego Nadleśnictwa (trafiły do '
                'grupy "' + logika.NADL_BRAK + '") — ' +
                str(len(raport.niedopasowane_nadl)) + ':')
            for e in raport.niedopasowane_nadl:
                linie.append('  ' + e)

        if raport.bledy_baz:
            linie.append('')
            linie.append('Błędy baz:')
            for b in raport.bledy_baz:
                linie.append('  ' + b)

        dialog = QDialog(self.parent())
        dialog.setWindowTitle('Raport')
        dialog.setMinimumSize(560, 440)
        lay = QVBoxLayout(dialog)
        pole = QTextEdit()
        pole.setReadOnly(True)
        pole.setPlainText('\n'.join(linie))
        lay.addWidget(pole)
        zamknij = QPushButton('Zamknij')
        zamknij.clicked.connect(dialog.accept)
        lay.addWidget(zamknij)
        dialog.exec_()
