"""Dialog konwersji shapefile'i ze starego standardu na nowy (patrz
`core/shp_standard.py`).

Układ okna w kolejności pracy: folder źródłowy -> tabela warstw ->
folder docelowy.

Domyślnie lista warstw do konwersji wypełniana jest warstwami wektorowymi
obecnymi w bieżącym projekcie (TOC). Wskazanie folderu źródłowego
zastępuje listę wszystkimi plikami SHP z tego folderu (bez podfolderów).
Przycisk "Dodaj warstwę z pliku…" pozwala dorzucić dowolne pliki SHP spoza
projektu, bez dodawania ich do TOC. Folder docelowy (wspólny dla
wszystkich konwertowanych w tym uruchomieniu warstw) wybiera użytkownik
przyciskiem "Wybierz…" - okno otwiera się domyślnie jeden poziom wyżej niż
folder z warstwami źródłowymi. Folder nie jest tworzony automatycznie -
jeśli wskazany nie istnieje, dialog pyta o potwierdzenie przed
utworzeniem. Oryginały nie są zmieniane.

Kodowanie źródła: pliki wyjściowe są zawsze zapisywane jako UTF-8, ale to
nie gwarantuje poprawności polskich znaków, jeśli ODCZYT starego pliku był
błędny. Kodowanie odczytu jest zgadywane i ustawiane dla KAŻDEJ warstwy
osobno (kolumna "Kodowanie") - w jednym zestawie bywają pliki w różnych
kodowaniach (Kruszwica: DZKAT w UTF-8, OBREBY_AFT z PRG w CP1250).
Sprawdzone na próbce z materialy/shp_stary_standard: pliki .cpg w tym
zestawie danych deklarują "UTF-8", ale surowe bajty w DBF wcale nie są
poprawnym UTF-8 - są Windows-1250 (np. "OPIS" w PNSW.dbf: bajt 0xEA to w
CP1250 "ę" - stąd domyślne, jawne wymuszenie CP1250 w tym dialogu zamiast
ufania (błędnemu) .cpg.
"""

import os
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)
from qgis.core import QgsProject, QgsVectorLayer

from ..core import shp_standard


TYPY = [
    "— pomiń —", "DZKAT", "EWID", "LS", "WYDZ", "WYDZ_POL", "PNSW", "OBR",
    "GMIN", "ODDZ", "KLU", "UZYTKI",
]

# etykiety w UI dla kodowan z shp_standard.KANDYDACI_KODOWAN (ten sam
# zestaw testuje "Zgadnij kodowanie") + opcja "bez wymuszania"
_ETYKIETY_KODOWAN = {
    "CP1250": "Windows-1250 (typowe dla starych plików tego zestawu)",
    "UTF-8": "UTF-8",
    "ISO-8859-2": "ISO-8859-2 (Latin-2)",
    "CP852": "CP852 (DOS, Europa Środkowa)",
}
# etykieta w UI -> kodowanie do wymuszenia przez setEncoding() (None =
# nie wymuszaj, zostaw tak jak QGIS sam zgadl/ustawil dla warstwy)
KODOWANIA = {
    _ETYKIETY_KODOWAN.get(k, k): k for k in shp_standard.KANDYDACI_KODOWAN
}
KODOWANIA["Systemowe / auto (bez wymuszania)"] = None


class KonwersjaShpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Konwersja SHP do nowego standardu")
        self.setMinimumSize(900, 420)
        self.warstwy = []  # rownolegle do wierszy tabeli
        self._build_ui()
        self._wczytaj_z_toc()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Warstwy do przekonwertowania na aktualny standard pól.\n"
            "Oryginały nie są zmieniane."
        ))

        wej_row = QHBoxLayout()
        wej_row.addWidget(QLabel("Folder źródłowy:"))
        self.edit_folder_wej = QLineEdit()
        self.edit_folder_wej.setPlaceholderText(
            "Opcjonalnie: folder ze starymi SHP (zastępuje warstwy z "
            "projektu)…")
        self.edit_folder_wej.setToolTip(
            "Po wskazaniu folderu (Wybierz… albo wpisanie ścieżki i Enter) "
            "lista warstw jest zastępowana wszystkimi plikami SHP z tego "
            "folderu (bez podfolderów).")
        self.edit_folder_wej.returnPressed.connect(
            lambda: self._wczytaj_folder(self.edit_folder_wej.text().strip()))
        wej_row.addWidget(self.edit_folder_wej, 1)
        wej_btn = QPushButton("Wybierz…")
        wej_btn.clicked.connect(self._wybierz_folder_wej)
        wej_row.addWidget(wej_btn)
        layout.addLayout(wej_row)

        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(
            ["Konwertuj", "Nazwa warstwy", "Typ docelowy", "Kodowanie",
             "Ścieżka"])
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.setColumnWidth(0, 70)
        self.tabela.setColumnWidth(1, 200)
        self.tabela.setColumnWidth(2, 110)
        self.tabela.setColumnWidth(3, 150)
        layout.addWidget(self.tabela)

        kodowanie_row = QHBoxLayout()
        kodowanie_row.addWidget(QLabel(
            "Kodowanie odczytu (zapis wyniku zawsze UTF-8):"))
        self.combo_kodowanie = QComboBox()
        self.combo_kodowanie.addItems(list(KODOWANIA.keys()))
        kodowanie_row.addWidget(self.combo_kodowanie, 1)
        wszystkim_btn = QPushButton("Ustaw wszystkim")
        wszystkim_btn.setToolTip(
            "Ustawia wybrane kodowanie w kolumnie \"Kodowanie\" "
            "zaznaczonym warstwom (a jeśli żadna nie jest zaznaczona - "
            "wszystkim).")
        wszystkim_btn.clicked.connect(self._ustaw_wszystkim)
        kodowanie_row.addWidget(wszystkim_btn)
        zgadnij_btn = QPushButton("Zgadnij kodowanie")
        zgadnij_btn.setToolTip(
            "Dla każdej zaznaczonej warstwy (a jeśli żadna nie jest "
            "zaznaczona - dla wszystkich) osobno sprawdza wartości tekstowe "
            "i wybiera kodowanie dające poprawny polski tekst.")
        zgadnij_btn.clicked.connect(self._zgadnij_kodowanie)
        kodowanie_row.addWidget(zgadnij_btn)
        probka_btn = QPushButton("Zobacz próbkę")
        probka_btn.setToolTip(
            "Pokazuje przykładowe wartości tekstowe zaznaczonych warstw "
            "zdekodowane każdym z kandydujących kodowań obok siebie - do "
            "ręcznej weryfikacji, które daje poprawny polski tekst.")
        probka_btn.clicked.connect(self._pokaz_probke)
        kodowanie_row.addWidget(probka_btn)
        layout.addLayout(kodowanie_row)

        dodaj_btn = QPushButton("Dodaj warstwę z pliku…")
        dodaj_btn.clicked.connect(self._dodaj_z_pliku)
        dodaj_row = QHBoxLayout()
        dodaj_row.addWidget(dodaj_btn)
        dodaj_row.addStretch(1)
        layout.addLayout(dodaj_row)


        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Folder docelowy:"))
        self.edit_folder = QLineEdit()
        self.edit_folder.setPlaceholderText(
            "Wskaż folder, do którego mają trafić przekonwertowane warstwy…")
        folder_row.addWidget(self.edit_folder, 1)
        folder_btn = QPushButton("Wybierz…")
        folder_btn.clicked.connect(self._wybierz_folder)
        folder_row.addWidget(folder_btn)
        layout.addLayout(folder_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Konwertuj")
        buttons.accepted.connect(self._uruchom)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _wybierz_folder(self):
        """Standardowe (natywne) okno wyboru folderu docelowego. Domyślnie
        otwiera się jeden poziom wyżej niż folder z warstwami źródłowymi -
        użytkownik stamtąd wybiera albo tworzy właściwy folder."""
        start = self.edit_folder.text().strip()
        if not start:
            start = shp_standard.folder_startowy_dla_wyboru(self.warstwy)
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder docelowy", start)
        if folder:
            self.edit_folder.setText(folder)

    def _wybierz_folder_wej(self):
        start = self.edit_folder_wej.text().strip()
        if not start:
            start = shp_standard.folder_startowy_dla_wyboru(self.warstwy)
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz folder źródłowy", start)
        if folder:
            self.edit_folder_wej.setText(folder)
            self._wczytaj_folder(folder)

    def _wczytaj_folder(self, folder):
        """Zastępuje listę warstw wszystkimi SHP z folderu (bez
        podfolderów)."""
        if not folder:
            return
        if not os.path.isdir(folder):
            QMessageBox.warning(
                self, "Błąd", f'Folder "{folder}" nie istnieje.')
            return
        sciezki = sorted(
            os.path.join(folder, n) for n in os.listdir(folder)
            if n.lower().endswith(".shp"))
        if not sciezki:
            QMessageBox.information(
                self, "Folder źródłowy",
                f'W folderze "{folder}" nie ma plików SHP.')
            return
        self.tabela.setRowCount(0)
        self.warstwy = []
        self._dodaj_pliki(sciezki)

    def _wczytaj_z_toc(self):
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer):
                self._dodaj_wiersz(lyr)

    def _dodaj_z_pliku(self):
        sciezki, _ = QFileDialog.getOpenFileNames(
            self, "Wybierz warstwy SHP", self.edit_folder_wej.text().strip(),
            "ESRI shp (*.shp)")
        self._dodaj_pliki(sciezki)

    def _dodaj_pliki(self, sciezki):
        for sc in sciezki:
            juz_jest = any(
                os.path.normcase(os.path.normpath(
                    w.dataProvider().dataSourceUri().split("|")[0]))
                == os.path.normcase(os.path.normpath(sc))
                for w in self.warstwy
            )
            if juz_jest:
                continue
            lyr = QgsVectorLayer(
                sc, os.path.splitext(os.path.basename(sc))[0], "ogr")
            if not lyr.isValid():
                QMessageBox.warning(
                    self, "Błąd", f"Nie udało się wczytać warstwy:\n{sc}")
                continue
            self._dodaj_wiersz(lyr)

    def _dodaj_wiersz(self, lyr):
        row = self.tabela.rowCount()
        self.tabela.insertRow(row)
        self.warstwy.append(lyr)

        chk = QCheckBox()
        chk.setChecked(True)
        chk_widget = QWidget()
        chk_layout = QHBoxLayout(chk_widget)
        chk_layout.addWidget(chk)
        chk_layout.setAlignment(Qt.AlignCenter)
        chk_layout.setContentsMargins(0, 0, 0, 0)
        self.tabela.setCellWidget(row, 0, chk_widget)

        nazwa_item = QTableWidgetItem(lyr.name())
        nazwa_item.setFlags(nazwa_item.flags() & ~Qt.ItemIsEditable)
        self.tabela.setItem(row, 1, nazwa_item)

        combo = QComboBox()
        combo.addItems(TYPY)
        zgadywany = shp_standard.zgadnij_typ(
            lyr.name(), [f.name() for f in lyr.fields()])
        if zgadywany in TYPY:
            combo.setCurrentText(zgadywany)
        self.tabela.setCellWidget(row, 2, combo)

        combo_kod = QComboBox()
        combo_kod.addItems(list(KODOWANIA.keys()))
        self._ustaw_kodowanie_wiersza(
            combo_kod, shp_standard.zgadnij_kodowanie_warstwy(lyr))
        self.tabela.setCellWidget(row, 3, combo_kod)

        try:
            sciezka = lyr.dataProvider().dataSourceUri().split("|")[0]
        except Exception:  # nopep8
            sciezka = ""
        sciezka_item = QTableWidgetItem(sciezka)
        sciezka_item.setFlags(sciezka_item.flags() & ~Qt.ItemIsEditable)
        sciezka_item.setForeground(QColor("gray"))
        self.tabela.setItem(row, 4, sciezka_item)

    def _zaznaczone_lub_wszystkie_warstwy(self):
        """Zwraca zaznaczone (checkbox "Konwertuj") warstwy, a jesli zadna
        nie jest zaznaczona - wszystkie w tabeli. Wspolne dla "Zgadnij
        kodowanie" i "Zobacz próbkę"."""
        zaznaczone = [
            self.warstwy[row] for row in range(self.tabela.rowCount())
            if self.tabela.cellWidget(row, 0).findChild(QCheckBox).isChecked()
        ]
        return zaznaczone or list(self.warstwy)

    @staticmethod
    def _ustaw_kodowanie_wiersza(combo, kod):
        """kod None (warstwa bez znaków spoza ASCII) -> UTF-8, kodowanie
        nie ma wtedy znaczenia."""
        kod = kod or "UTF-8"
        for etykieta, k in KODOWANIA.items():
            if k == kod:
                combo.setCurrentText(etykieta)
                return

    def _zaznaczone_lub_wszystkie_wiersze(self):
        wiersze = [
            row for row in range(self.tabela.rowCount())
            if self.tabela.cellWidget(row, 0).findChild(QCheckBox).isChecked()
        ]
        return wiersze or list(range(self.tabela.rowCount()))

    def _ustaw_wszystkim(self):
        etykieta = self.combo_kodowanie.currentText()
        for row in self._zaznaczone_lub_wszystkie_wiersze():
            self.tabela.cellWidget(row, 3).setCurrentText(etykieta)

    def _zgadnij_kodowanie(self):
        """Zgaduje kodowanie każdej zaznaczonej warstwy (a jeśli żadna nie
        jest zaznaczona - wszystkich) osobno i ustawia je w kolumnie
        "Kodowanie"."""
        wiersze = self._zaznaczone_lub_wszystkie_wiersze()
        if not wiersze:
            QMessageBox.information(
                self, "Zgadnij kodowanie", "Brak warstw do analizy.")
            return

        linie = []
        for row in wiersze:
            lyr = self.warstwy[row]
            kod = shp_standard.zgadnij_kodowanie_warstwy(lyr)
            self._ustaw_kodowanie_wiersza(self.tabela.cellWidget(row, 3), kod)
            linie.append(
                f"{lyr.name()}: {kod}" if kod else
                f"{lyr.name()}: bez polskich znaków (UTF-8)")

        QMessageBox.information(
            self, "Zgadnij kodowanie",
            "Wykryte kodowania:\n\n" + "\n".join(linie) +
            "\n\nSprawdź wynik (\"Zobacz próbkę\") i popraw ręcznie, "
            "jeśli to konieczne.")

    def _pokaz_probke(self):
        """Pokazuje tabelę porównawczą: te same surowe wartości tekstowe
        zdekodowane każdym z kandydujących kodowań obok siebie, żeby
        ręcznie ocenić, które daje poprawny polski tekst."""
        warstwy = self._zaznaczone_lub_wszystkie_warstwy()
        if not warstwy:
            QMessageBox.information(
                self, "Zobacz próbkę", "Brak warstw do analizy.")
            return

        probka = shp_standard.probka_do_podgladu(warstwy)
        if not probka:
            QMessageBox.information(
                self, "Zobacz próbkę",
                "Nie udało się zebrać próbki tekstu (brak pól tekstowych "
                "albo obiektów w zaznaczonych warstwach).")
            return

        zdekodowane = shp_standard.zdekoduj_probke(probka)

        dialog = QDialog(self)
        dialog.setWindowTitle("Podgląd próbki wartości tekstowych")
        dialog.setMinimumSize(780, 420)
        lay = QVBoxLayout(dialog)
        lay.addWidget(QLabel(
            "Ta sama wartość zdekodowana każdym z kandydujących kodowań - "
            "wybierz w liście powyżej to, które daje poprawny polski "
            "tekst."))

        kolumny = shp_standard.KANDYDACI_KODOWAN
        tabela = QTableWidget(len(probka), len(kolumny))
        tabela.setHorizontalHeaderLabels(kolumny)
        for i, wiersz in enumerate(zdekodowane):
            for j, kod in enumerate(kolumny):
                item = QTableWidgetItem(wiersz[kod])
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                tabela.setItem(i, j, item)
        tabela.resizeColumnsToContents()
        lay.addWidget(tabela)

        zamknij = QPushButton("Zamknij")
        zamknij.clicked.connect(dialog.accept)
        lay.addWidget(zamknij)
        dialog.exec_()

    def _uruchom(self):
        do_konwersji = []
        for row in range(self.tabela.rowCount()):
            chk = self.tabela.cellWidget(row, 0).findChild(QCheckBox)
            combo = self.tabela.cellWidget(row, 2)
            typ = combo.currentText()
            kod = KODOWANIA[self.tabela.cellWidget(row, 3).currentText()]
            if chk.isChecked() and typ != TYPY[0]:
                do_konwersji.append((self.warstwy[row], typ, kod))

        if not do_konwersji:
            QMessageBox.information(
                self, "Konwersja SHP",
                "Nie zaznaczono żadnej warstwy z wybranym typem docelowym.")
            return

        folder_wyjsciowy = self.edit_folder.text().strip()
        if not folder_wyjsciowy:
            QMessageBox.warning(
                self, "Brak folderu docelowego",
                "Wskaż folder, do którego mają trafić przekonwertowane "
                "warstwy.")
            return

        # folder wyjsciowy NIE jest tworzony automatycznie - jesli nie
        # istnieje, pytamy wprost czy go utworzyc
        if not os.path.isdir(folder_wyjsciowy):
            odp = QMessageBox.question(
                self, "Folder nie istnieje",
                f'Folder "{folder_wyjsciowy}" nie istnieje.\n\n'
                "Utworzyć go?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if odp != QMessageBox.Yes:
                return
            try:
                os.makedirs(folder_wyjsciowy)
            except OSError as e:
                QMessageBox.critical(
                    self, "Błąd",
                    f"Nie udało się utworzyć folderu:\n{e}")
                return

        # ostrzezenie o kolizjach - wszystkie warstwy licza sie teraz do
        # JEDNEGO wspolnego folderu, wiec dwie rozne warstwy o tej samej
        # nazwie pliku nadpisalyby sie nawzajem
        nazwy_plikow = {}
        for lyr, _typ, _kod in do_konwersji:
            try:
                sc = lyr.dataProvider().dataSourceUri().split("|")[0]
            except Exception:  # nopep8
                continue
            nazwy_plikow.setdefault(os.path.basename(sc), []).append(sc)
        kolizje = {n: s for n, s in nazwy_plikow.items() if len(s) > 1}
        if kolizje:
            opis = "\n".join(
                f"  {n}:\n    " + "\n    ".join(s)
                for n, s in kolizje.items()
            )
            odp = QMessageBox.question(
                self, "Zduplikowane nazwy plików",
                "Kilka zaznaczonych warstw zapisze się pod tą samą nazwą "
                "we wspólnym folderze docelowym - kolejna nadpisze "
                "poprzednią:\n\n" + opis + "\n\nKontynuować mimo to?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if odp != QMessageBox.Yes:
                return

        for lyr, _typ, kod in do_konwersji:
            if kod:
                lyr.dataProvider().setEncoding(kod)

        raporty = []
        for lyr, typ, _kod in do_konwersji:
            try:
                raporty.append(shp_standard.konwertuj_warstwe(
                    lyr, typ, folder_wyjsciowy))
            except Exception as e:  # nopep8
                raporty.append({
                    "nazwa": lyr.name(), "typ": typ, "sciezka": None,
                    "obiekty": 0, "pola_zmapowane": [], "pola_brakujace": [],
                    "naprawione": [], "liczba_naprawionych": 0,
                    "bledy": [f"Konwersja przerwana błędem: {e}"],
                })

        self._pokaz_raport(raporty)
        self.accept()

    def _zbuduj_tekst_raportu(self, raporty):
        linie = ["RAPORT KONWERSJI SHP DO NOWEGO STANDARDU", "=" * 60, ""]
        for r in raporty:
            linie.append(f"Warstwa: {r['nazwa']}  (typ docelowy: {r['typ']})")
            if r.get("sciezka"):
                linie.append(f"  Zapisano: {r['sciezka']}")
            else:
                linie.append("  NIE ZAPISANO (patrz błędy poniżej)")
            linie.append(f"  Przetworzonych obiektów: {r['obiekty']}")

            if r["pola_zmapowane"]:
                linie.append("  Zmapowane pola:")
                for nowe, stare in r["pola_zmapowane"]:
                    linie.append(f"    {stare}  ->  {nowe}")

            if r["pola_brakujace"]:
                linie.append(
                    "  BRAK ŹRÓDŁA dla pól (puste w wyniku, wymagają "
                    "uzupełnienia inną metodą, np. z bazy taksatora):")
                for p in r["pola_brakujace"]:
                    linie.append(f"    {p}")

            if r.get("liczba_naprawionych"):
                linie.append(
                    "  Naprawione polskie znaki (podwójne kodowanie w "
                    "źródle, np. LZ-Ĺ\\x81 -> LZ-Ł): "
                    f"{r['liczba_naprawionych']}")
                for n in r["naprawione"]:
                    linie.append(f"    {n}")

            if r["bledy"]:
                linie.append(f"  Błędy / ostrzeżenia ({len(r['bledy'])}):")
                for b in r["bledy"][:50]:
                    linie.append(f"    {b}")
                if len(r["bledy"]) > 50:
                    linie.append(
                        f"    ... i {len(r['bledy']) - 50} więcej "
                        "(patrz log Las-R)")

            linie.append("")
        return "\n".join(linie)

    def _pokaz_raport(self, raporty):
        tekst = self._zbuduj_tekst_raportu(raporty)

        for r in raporty:
            if r.get("sciezka"):
                folder = os.path.dirname(r["sciezka"])
                czas = datetime.now().strftime("%Y%m%d_%H%M%S")
                rap_sc = os.path.join(
                    folder, f"raport_konwersji_{czas}.txt")
                try:
                    with open(rap_sc, "w", encoding="utf-8") as f:
                        f.write(tekst)
                except Exception:  # nopep8
                    pass
                break

        dialog = QDialog(self.parent())
        dialog.setWindowTitle("Raport konwersji")
        dialog.setMinimumSize(680, 520)
        lay = QVBoxLayout(dialog)
        pole = QTextEdit()
        pole.setReadOnly(True)
        pole.setPlainText(tekst)
        lay.addWidget(pole)
        zamknij = QPushButton("Zamknij")
        zamknij.clicked.connect(dialog.accept)
        lay.addWidget(zamknij)
        dialog.exec_()
