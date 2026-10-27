# -*- coding: utf-8 -*-
"""Dialog "Stwórz prezentację" NTG - logika w core/prezentacja.py
(znaczniki wzoru opisane tam), zestawienia z core/protokol.py. Dane
wspólne z protokołem (miejscowość, tytuł, umowa...) - te same ustawienia
co w oknie protokołu."""
import os
import platform
from datetime import date

from qgis.PyQt.QtCore import QDate, QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QApplication, QDateEdit, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout,
)

from ..core import protokol as core
from ..core import przygotuj
from .protokol_dialog import KLUCZ, KLUCZ_P

KLUCZ_PR = KLUCZ + "prezentacja/"
TYTUL = "NTG - Stwórz prezentację"
FOLDER_MAP = "NTG_mapy"   # domyślny folder PNG w "Generuj mapy"


class PrezentacjaDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(TYTUL)
        self.setMinimumWidth(640)
        self._buduj_ui()
        self._folder_zmieniony()

    # ------------------------------------------------------------ UI

    def _buduj_ui(self):
        ust = QSettings()
        uklad = QVBoxLayout(self)
        opis = QLabel(
            "Prezentacja na naradę (PPTX) ze wzoru ze znacznikami {{...}}: "
            "tabele z bazy Baza_NTG_polaczona_BDO.mdb (dla każdej gminy "
            "osobny slajd), mapy PNG z \"Generuj mapy\". Slajdy bez "
            "znaczników i miejsca na zdjęcia zostają bez zmian.")
        opis.setWordWrap(True)
        uklad.addWidget(opis)

        siatka = QGridLayout()
        # wzór poza wtyczką (jak wzór protokołu) - zapamiętany ostatni
        self.e_wzor = QLineEdit(ust.value(KLUCZ_PR + "wzor", ""))
        self.e_wzor.setPlaceholderText("prezentacja ze znacznikami, .pptx")
        self.e_wzor.setToolTip(
            "Wzór prezentacji ze znacznikami {{...}} (przycisk "
            "\"Znaczniki we wzorze...\") - plik poza wtyczką, edytowany "
            "ręcznie.")
        obiekt = ust.value(KLUCZ + "obiekt", "")
        self.e_folder = QLineEdit(ust.value(
            KLUCZ_P + "folder",
            os.path.join(obiekt, przygotuj.FOLDER_EKSPORTU) if obiekt
            else ""))
        self.e_folder.editingFinished.connect(self._folder_zmieniony)
        self.e_mapy = QLineEdit(ust.value(KLUCZ_PR + "mapy", ""))
        self.e_mapy.setPlaceholderText("folder PNG z \"Generuj mapy\"")
        for i, (etyk, pole, fn) in enumerate((
                ("Wzór prezentacji (.pptx):", self.e_wzor, self._wskaz_wzor),
                ("Folder NTG:", self.e_folder, self._wskaz_folder),
                ("Folder z mapami PNG:", self.e_mapy, self._wskaz_mapy))):
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
        # data narady pamiętana (wspólna z drugim oknem NTG) - protokół i
        # prezentacja powstają zwykle na tę samą naradę
        d_nar = QDate.fromString(ust.value(KLUCZ_P + "data_narady", ""),
                                 Qt.ISODate)
        self.d_narady = QDateEdit(d_nar if d_nar.isValid() else dzis)
        self.d_narady.setCalendarPopup(True)
        rz = QHBoxLayout()
        rz.addWidget(self.e_miejsc)
        rz.addWidget(QLabel("data:"))
        rz.addWidget(self.d_narady)
        form.addRow("Miejscowość narady:", rz)

        self.e_tytul = QPlainTextEdit(ust.value(KLUCZ_P + "tytul", ""))
        self.e_tytul.setFixedHeight(60)
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

        self.e_starostwo = QLineEdit(ust.value(KLUCZ_P + "starostwo", ""))
        self.e_starostwo.setPlaceholderText("miejscownik, np. Jarosławiu")
        form.addRow("Starostwo Powiatowe w:", self.e_starostwo)
        uklad.addLayout(form)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.button(QDialogButtonBox.Ok).setText("Utwórz prezentację")
        b_zn = przyciski.addButton("Znaczniki we wzorze...",
                                   QDialogButtonBox.HelpRole)
        b_zn.clicked.connect(self._pokaz_znaczniki)
        przyciski.accepted.connect(self._uruchom)
        przyciski.rejected.connect(self.reject)
        uklad.addWidget(przyciski)

    def _pokaz_znaczniki(self):
        from ..core import prezentacja
        QMessageBox.information(self, TYTUL, prezentacja.__doc__.split(
            "\n\nBiblioteka")[0])

    # ------------------------------------------------------------ ścieżki

    def _baza(self):
        return os.path.join(self.e_folder.text().strip(),
                            przygotuj.NAZWA_BAZY)

    def _wskaz_wzor(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Wzór prezentacji NTG", self.e_wzor.text().strip(),
            "Prezentacja PowerPoint (*.pptx)")
        if f:
            self.e_wzor.setText(os.path.normpath(f))

    def _wskaz_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Folder NTG",
                                             self.e_folder.text().strip())
        if f:
            self.e_folder.setText(os.path.normpath(f))
            self._folder_zmieniony()

    def _wskaz_mapy(self):
        f = QFileDialog.getExistingDirectory(
            self, "Folder z mapami PNG",
            self.e_mapy.text().strip() or self.e_folder.text().strip())
        if f:
            self.e_mapy.setText(os.path.normpath(f))
            self._folder_zmieniony()

    def _folder_zmieniony(self):
        # mapy domyślnie w <folder NTG>\NTG_mapy, jeśli taki jest
        dom = os.path.join(self.e_folder.text().strip(), FOLDER_MAP)
        if not self.e_mapy.text().strip() and os.path.isdir(dom):
            self.e_mapy.setText(dom)
        stan = []
        if not os.path.isfile(self._baza()):
            stan.append("brak %s" % przygotuj.NAZWA_BAZY)
        mapy = self.e_mapy.text().strip()
        if os.path.isdir(mapy):
            png = [f for f in os.listdir(mapy) if f.lower().endswith(".png")]
            stan.append("map PNG: %d" % len(png))
        else:
            stan.append("brak folderu z mapami - zamiast map napis "
                        "\"Brak mapy\"")
        self.l_stan.setText("<i>%s</i>" % "; ".join(stan))

    # ------------------------------------------------------------ przebieg

    def _zapamietaj(self):
        ust = QSettings()
        ust.setValue(KLUCZ_PR + "wzor", self.e_wzor.text().strip())
        ust.setValue(KLUCZ_PR + "mapy", self.e_mapy.text().strip())
        ust.setValue(KLUCZ_P + "folder", self.e_folder.text().strip())
        ust.setValue(KLUCZ_P + "miejscowosc", self.e_miejsc.text().strip())
        ust.setValue(KLUCZ_P + "data_narady",
                     self.d_narady.date().toString(Qt.ISODate))
        ust.setValue(KLUCZ_P + "tytul", self.e_tytul.toPlainText().strip())
        ust.setValue(KLUCZ_P + "nr_umowy", self.e_umowa.text().strip())
        ust.setValue(KLUCZ_P + "data_umowy",
                     self.d_umowy.date().toString(Qt.ISODate))
        ust.setValue(KLUCZ_P + "starostwo", self.e_starostwo.text().strip())

    def _teksty(self):
        return {
            "miejscowosc": self.e_miejsc.text().strip(),
            "data_narady": self.d_narady.date().toString("dd.MM.yyyy"),
            "tytul": " ".join(self.e_tytul.toPlainText().split()),
            "nr_umowy": self.e_umowa.text().strip(),
            "data_umowy": self.d_umowy.date().toString("dd.MM.yyyy"),
            "rok_od": self.s_od.value(),
            "rok_do": self.s_do.value(),
            "starostwo": self.e_starostwo.text().strip(),
        }

    def _uruchom(self):
        wzor = self.e_wzor.text().strip()
        if not wzor.lower().endswith(".pptx") or not os.path.isfile(wzor):
            QMessageBox.warning(self, TYTUL,
                                "Wskaż wzór prezentacji (.pptx).")
            return
        baza = self._baza()
        if not os.path.isfile(baza):
            QMessageBox.warning(self, TYTUL, "W folderze NTG nie ma %s - "
                                "najpierw \"Przygotuj warstwy i bazę\"."
                                % przygotuj.NAZWA_BAZY)
            return
        self._zapamietaj()
        teksty = self._teksty()
        folder = self.e_folder.text().strip()
        nazwa = "Prezentacja_NTG_%s_%s.pptx" % (
            "".join(z for z in teksty["miejscowosc"]
                    if z.isalnum() or z in "-_") or "obiekt",
            self.d_narady.date().toString("yyyy.MM.dd"))
        wynik = os.path.join(folder, nazwa)
        if os.path.exists(wynik) and QMessageBox.question(
                self, TYTUL, "Plik %s już istnieje - nadpisać?" % nazwa) \
                != QMessageBox.Yes:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            from ..core import prezentacja
            dane = core.DaneProtokolu(baza)
            tabele = dane.policz()
            tabele_gmin = dane.policz_gminy()
            nazwy = {gm: dane.nazwa_gminy(gm) for gm in tabele_gmin}
            teksty["gminy"] = ", ".join(nazwy.values())
            slajdy, ostrz = prezentacja.generuj(
                wzor, wynik, teksty, tabele, tabele_gmin, nazwy,
                self.e_mapy.text().strip())
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, TYTUL, "Nie można zapisać %s - plik "
                                 "jest otwarty w PowerPoincie?" % wynik)
            return
        except Exception as e:  # noqa: BLE001 - pokazujemy użytkownikowi
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, TYTUL, "Błąd: %s" % e)
            return
        QApplication.restoreOverrideCursor()
        self.accept()

        ostrz = dane.ostrzezenia + ostrz
        tekst = "Utworzono prezentację (%d slajdów):\n%s" % (slajdy, wynik)
        if ostrz:
            rap = przygotuj.zapisz_raport(
                folder, ["Stwórz prezentację NTG - ostrzeżenia", ""] + ostrz,
                nazwa="prezentacja")
            tekst += ("\n\nOstrzeżenia (%d) - raport: %s\n\n%s"
                      % (len(ostrz), rap, "\n".join(ostrz[:10])))
        tekst += "\n\nOtworzyć prezentację?"
        if QMessageBox.question(self.iface.mainWindow(), TYTUL, tekst) == \
                QMessageBox.Yes and platform.system()[:3] == "Win":
            os.startfile(wynik)
