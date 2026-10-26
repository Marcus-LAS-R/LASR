# -*- coding: utf-8 -*-
"""Dialog "Przygotuj protokół NTG" - logika w core/protokol.py, tu: dane
do wpisania (zapamiętywane), wybór zaproszonych, zapis DOCX."""
import os
import platform
from datetime import date

from qgis.PyQt.QtCore import QDate, QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox,
    QVBoxLayout,
)

from ..core import protokol as core
from ..core import przygotuj
from ..core.mapa_ogolna import POLE_NAZWA_NADL

KLUCZ = "LASR/protokol_ntg/"
KLUCZ_P = KLUCZ + "protokol/"
TYTUL = "NTG - Przygotuj protokół"

# (klucz, etykieta, domyślnie zaznaczone)
ZAPROSZENI = (
    ("dglp", "Dyrekcja Generalna LP", False),
    ("rdlp", "Regionalna Dyrekcja LP", True),
    ("nadl", "Nadleśnictwa (z warstwy NADL)", True),
    ("rdos", "RDOŚ", False),
    ("pwis", "PWIS", False),
    ("starostwo", "Starostwo Powiatowe", True),
    ("gminy", "Przedstawiciele gmin", False),
)


class ProtokolDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(TYTUL)
        self.setMinimumWidth(640)
        self.nadl, self.rdlp_z_warstwy = [], []
        self._buduj_ui()
        self._folder_zmieniony()

    # ------------------------------------------------------------ UI

    def _buduj_ui(self):
        ust = QSettings()
        uklad = QVBoxLayout(self)
        opis = QLabel(
            "Protokół narady techniczno-gospodarczej (DOCX) z bazy "
            "Baza_NTG_polaczona_BDO.mdb i warstw z folderu NTG (wynik "
            "\"Przygotuj warstwy i bazę\"). "
            "Fragmenty do sprawdzenia są w dokumencie podświetlone na żółto.")
        opis.setWordWrap(True)
        uklad.addWidget(opis)

        siatka = QGridLayout()
        self.e_wzor = QLineEdit(ust.value(KLUCZ_P + "wzor", ""))
        self.e_wzor.setPlaceholderText("szablon docxtpl, np. SZABLON_NTG.docx")
        obiekt = ust.value(KLUCZ + "obiekt", "")
        self.e_folder = QLineEdit(ust.value(
            KLUCZ_P + "folder",
            os.path.join(obiekt, przygotuj.FOLDER_EKSPORTU) if obiekt
            else ""))
        self.e_folder.editingFinished.connect(self._folder_zmieniony)
        for i, (etyk, pole, fn) in enumerate((
                ("Wzór protokołu (.docx):", self.e_wzor, self._wskaz_wzor),
                ("Folder NTG:", self.e_folder, self._wskaz_folder))):
            b = QPushButton("Wskaż...")
            b.clicked.connect(fn)
            siatka.addWidget(QLabel(etyk), i, 0)
            siatka.addWidget(pole, i, 1)
            siatka.addWidget(b, i, 2)
        uklad.addLayout(siatka)
        self.l_stan = QLabel()
        self.l_stan.setWordWrap(True)
        uklad.addWidget(self.l_stan)

        form = QFormLayout()
        dzis = QDate.currentDate()
        self.e_miejsc = QLineEdit(ust.value(KLUCZ_P + "miejscowosc", ""))
        self.d_narady = QDateEdit(dzis)
        self.d_narady.setCalendarPopup(True)
        rz = QHBoxLayout()
        rz.addWidget(self.e_miejsc)
        rz.addWidget(QLabel("data:"))
        rz.addWidget(self.d_narady)
        form.addRow("Miejscowość narady:", rz)

        self.e_tytul = QPlainTextEdit(ust.value(KLUCZ_P + "tytul", ""))
        self.e_tytul.setFixedHeight(60)
        self.e_tytul.setPlaceholderText("Opracowanie Uproszczonych Planów "
                                        "Urządzenia Lasu ...")
        form.addRow("Tytuł zadania:", self.e_tytul)

        self.e_umowa = QLineEdit(ust.value(KLUCZ_P + "nr_umowy", ""))
        d_um = QDate.fromString(ust.value(KLUCZ_P + "data_umowy", ""),
                                Qt.ISODate)
        self.d_umowy = QDateEdit(d_um if d_um.isValid() else dzis)
        self.d_umowy.setCalendarPopup(True)
        rz = QHBoxLayout()
        rz.addWidget(self.e_umowa)
        rz.addWidget(QLabel("z dnia:"))
        rz.addWidget(self.d_umowy)
        form.addRow("Nr umowy:", rz)

        # lata planu - domyślnie od początku przyszłego roku, na 10 lat
        self.s_od = QSpinBox()
        self.s_od.setRange(2000, 2100)
        self.s_od.setValue(date.today().year + 1)
        self.s_do = QSpinBox()
        self.s_do.setRange(2000, 2110)
        self.s_do.setValue(self.s_od.value() + 9)
        self.s_od.valueChanged.connect(lambda v: self.s_do.setValue(v + 9))
        rz = QHBoxLayout()
        rz.addWidget(self.s_od)
        rz.addWidget(QLabel("-"))
        rz.addWidget(self.s_do)
        rz.addStretch()
        form.addRow("Lata planu:", rz)

        self.c_rdlp = QComboBox()
        self.c_rdlp.addItems(sorted(core.RDLP, key=core.klucz_pl))
        rdlp = ust.value(KLUCZ_P + "rdlp", "")
        if rdlp in core.RDLP:
            self.c_rdlp.setCurrentText(rdlp)
        form.addRow("RDLP:", self.c_rdlp)

        self.e_starostwo = QLineEdit(ust.value(KLUCZ_P + "starostwo", ""))
        self.e_starostwo.setPlaceholderText("miejscownik, np. Jarosławiu")
        form.addRow("Starostwo Powiatowe w:", self.e_starostwo)

        self.e_otwierajacy = QLineEdit(ust.value(KLUCZ_P + "otwierajacy",
                                                 ""))
        self.e_otwierajacy.setPlaceholderText(
            "imię, nazwisko i funkcja, np. Jan Kowalski Naczelnik ...")
        form.addRow("Naradę otworzył Sz. P.:", self.e_otwierajacy)

        self.e_kontrola = QLineEdit(ust.value(KLUCZ_P + "data_kontroli", ""))
        self.e_kontrola.setPlaceholderText("np. 16 października 2026 r.")
        form.addRow("Kontrola prac terenowych z dnia:", self.e_kontrola)
        uklad.addLayout(form)

        grupa = QGroupBox("Na posiedzenie zaproszeni zostali przedstawiciele "
                          "(Wykonawca zawsze):")
        siatka = QGridLayout(grupa)
        self.ch_zapr = {}
        for i, (k, etyk, dom) in enumerate(ZAPROSZENI):
            ch = QCheckBox(etyk)
            ch.setChecked(ust.value(KLUCZ_P + "zapr_" + k, dom, type=bool))
            siatka.addWidget(ch, i // 2, i % 2)
            self.ch_zapr[k] = ch
        uklad.addWidget(grupa)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.button(QDialogButtonBox.Ok).setText("Utwórz protokół")
        przyciski.accepted.connect(self._uruchom)
        przyciski.rejected.connect(self.reject)
        uklad.addWidget(przyciski)

    # ------------------------------------------------------------ folder

    def _sciezki(self):
        f = self.e_folder.text().strip()
        return (os.path.join(f, przygotuj.NAZWA_BAZY),
                os.path.join(f, przygotuj.FOLDER_SHP,
                             przygotuj.NAZWA_NADL + ".shp"),
                os.path.join(f, przygotuj.FOLDER_SHP, "WYDZ.shp"))

    def _wskaz_wzor(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Wzór protokołu NTG", self.e_wzor.text().strip(),
            "Dokument Word (*.docx)")
        if f:
            self.e_wzor.setText(os.path.normpath(f))

    def _wskaz_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Folder NTG",
                                             self.e_folder.text().strip())
        if f:
            self.e_folder.setText(os.path.normpath(f))
            self._folder_zmieniony()

    def _folder_zmieniony(self):
        baza, nadl, wydz = self._sciezki()
        stan = []
        if not os.path.isfile(baza):
            stan.append("brak %s" % przygotuj.NAZWA_BAZY)
        self.nadl, self.rdlp_z_warstwy = [], []
        if os.path.isfile(nadl) and os.path.isfile(wydz):
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self.nadl, self.rdlp_z_warstwy = core.nadlesnictwa(
                    nadl, wydz, POLE_NAZWA_NADL)
            finally:
                QApplication.restoreOverrideCursor()
            stan.append("nadleśnictwa: " + (", ".join(self.nadl) or "brak"))
            if len(self.rdlp_z_warstwy) == 1 and \
                    self.rdlp_z_warstwy[0] in core.RDLP:
                self.c_rdlp.setCurrentText(self.rdlp_z_warstwy[0])
        else:
            stan.append("brak SHP\\NADL.shp lub SHP\\WYDZ.shp - nadleśnictwa "
                        "nie zostaną wpisane")
        self.l_stan.setText("<i>%s</i>" % "; ".join(stan))

    # ------------------------------------------------------------ przebieg

    def _zapamietaj(self):
        ust = QSettings()
        ust.setValue(KLUCZ_P + "wzor", self.e_wzor.text().strip())
        ust.setValue(KLUCZ_P + "folder", self.e_folder.text().strip())
        ust.setValue(KLUCZ_P + "miejscowosc", self.e_miejsc.text().strip())
        ust.setValue(KLUCZ_P + "tytul", self.e_tytul.toPlainText().strip())
        ust.setValue(KLUCZ_P + "nr_umowy", self.e_umowa.text().strip())
        ust.setValue(KLUCZ_P + "data_umowy",
                     self.d_umowy.date().toString(Qt.ISODate))
        ust.setValue(KLUCZ_P + "rdlp", self.c_rdlp.currentText())
        ust.setValue(KLUCZ_P + "starostwo", self.e_starostwo.text().strip())
        ust.setValue(KLUCZ_P + "otwierajacy",
                     self.e_otwierajacy.text().strip())
        ust.setValue(KLUCZ_P + "data_kontroli", self.e_kontrola.text().strip())
        for k, ch in self.ch_zapr.items():
            ust.setValue(KLUCZ_P + "zapr_" + k, ch.isChecked())

    def _kontekst(self):
        d_um = self.d_umowy.date().toPyDate()
        starostwo = self.e_starostwo.text().strip()
        return {
            "miejscowosc": self.e_miejsc.text().strip(),
            "data_narady": self.d_narady.date().toString("dd.MM.yyyy"),
            "tytul": " ".join(self.e_tytul.toPlainText().split()),
            "nr_umowy": self.e_umowa.text().strip(),
            "data_umowy": d_um.strftime("%d.%m.%Y"),
            "data_umowy_sl": core.data_slownie(d_um),
            "rok_od": self.s_od.value(),
            "rok_do": self.s_do.value(),
            "starostwo": starostwo,
            "otwierajacy": self.e_otwierajacy.text().strip().rstrip("."),
            "data_kontroli": self.e_kontrola.text().strip().rstrip("."),
            "zaproszeni": core.zaproszeni(
                {k for k, ch in self.ch_zapr.items() if ch.isChecked()},
                self.c_rdlp.currentText(), self.nadl, starostwo),
        }

    def _uruchom(self):
        wzor = self.e_wzor.text().strip()
        if not wzor.lower().endswith(".docx") or not os.path.isfile(wzor):
            QMessageBox.warning(self, TYTUL, "Wskaż wzór protokołu (.docx).")
            return
        baza, _nadl, _wydz = self._sciezki()
        if not os.path.isfile(baza):
            QMessageBox.warning(self, TYTUL, "W folderze NTG nie ma %s - "
                                "najpierw \"Przygotuj warstwy i bazę\"."
                                % przygotuj.NAZWA_BAZY)
            return
        braki = [n for n, e in (("miejscowość", self.e_miejsc),
                                ("nr umowy", self.e_umowa),
                                ("starostwo", self.e_starostwo))
                 if not e.text().strip()]
        if not self.e_tytul.toPlainText().strip():
            braki.append("tytuł zadania")
        if braki and QMessageBox.question(
                self, TYTUL, "Nie wpisano: %s.\n\nUtworzyć protokół mimo to?"
                % ", ".join(braki)) != QMessageBox.Yes:
            return
        self._zapamietaj()
        kontekst = self._kontekst()
        folder = self.e_folder.text().strip()
        nazwa = "Protokol_NTG_%s_%s.docx" % (
            "".join(z for z in kontekst["miejscowosc"]
                    if z.isalnum() or z in "-_") or "obiekt",
            self.d_narady.date().toString("yyyy.MM.dd"))
        wynik = os.path.join(folder, nazwa)
        if os.path.exists(wynik) and QMessageBox.question(
                self, TYTUL, "Plik %s już istnieje - nadpisać?" % nazwa) \
                != QMessageBox.Yes:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            dane = core.DaneProtokolu(baza)
            kontekst.update(dane.policz())
            core.generuj(kontekst, wynik, wzor)
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, TYTUL, "Nie można zapisać %s - plik "
                                 "jest otwarty w Wordzie?" % wynik)
            return
        except Exception as e:  # noqa: BLE001 - pokazujemy użytkownikowi
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, TYTUL, "Błąd: %s" % e)
            return
        QApplication.restoreOverrideCursor()
        self.accept()

        tekst = "Utworzono protokół:\n%s" % wynik
        if dane.ostrzezenia:
            rap = przygotuj.zapisz_raport(
                folder, ["Przygotuj protokół NTG - ostrzeżenia", ""] +
                dane.ostrzezenia, nazwa="protokol")
            tekst += ("\n\nOstrzeżenia (%d) - raport: %s\n\n%s"
                      % (len(dane.ostrzezenia), rap,
                         "\n".join(dane.ostrzezenia[:10])))
        tekst += "\n\nOtworzyć protokół?"
        if QMessageBox.question(self.iface.mainWindow(), TYTUL, tekst) == \
                QMessageBox.Yes and platform.system()[:3] == "Win":
            os.startfile(wynik)
