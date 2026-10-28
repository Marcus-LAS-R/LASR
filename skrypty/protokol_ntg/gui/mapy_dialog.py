# -*- coding: utf-8 -*-
"""Dialog "Generuj mapy" (NTG materiały).

Mapa ogólna obiektu (core/mapa_ogolna.py) i mapy gmin TSL / zabiegi / formy
ochrony przyrody (core/mapy_gmin.py).
Warstwy domyślnie z bieżącego projektu, "Z pliku..." wczytuje dowolny .shp.
Ścieżki warstw nadleśnictw i form ochrony przyrody, wybór map, tytuł
i powiat są zapamiętywane (QSettings).
"""
import os

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)
from ...przyciski import QDialogButtonBox, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes

from ..core import mapa_ogolna, mapy_gmin

KLUCZ = "LASR/protokol_ntg/"
TYTUL = "NTG - Generuj mapy"


def _warstwy_poligonowe():
    return [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if isinstance(lyr, QgsVectorLayer)
        and lyr.geometryType() == QgsWkbTypes.PolygonGeometry
        and not lyr.name().startswith("NTG_")
    ]


class _Picker:
    """Combo z warstwami projektu + "Z pliku...". Domyślna warstwa: pierwsza,
    której nazwa (bez wielkości liter) równa się / zaczyna od wzorca."""

    def __init__(self, dialog, siatka, wiersz, etykieta, wzorce, warstwy,
                 klucz_pliku=None):
        self._dialog = dialog
        self._warstwy = list(warstwy)
        self._klucz = klucz_pliku
        siatka.addWidget(QLabel(etykieta), wiersz, 0)
        self.combo = QComboBox()
        self.combo.addItems([lyr.name() for lyr in self._warstwy])
        siatka.addWidget(self.combo, wiersz, 1)
        btn = QPushButton("Z pliku...")
        btn.clicked.connect(self._z_pliku)
        siatka.addWidget(btn, wiersz, 2)

        idx = self._domyslny(wzorce)
        if idx is not None:
            self.combo.setCurrentIndex(idx)
        else:
            self.combo.setCurrentIndex(-1)
            zapisany = QSettings().value(KLUCZ + klucz_pliku, "") \
                if klucz_pliku else ""
            if zapisany and os.path.isfile(zapisany):
                self._dodaj(zapisany)

    def _domyslny(self, wzorce):
        nazwy = [lyr.name().lower() for lyr in self._warstwy]
        for wz in wzorce:
            if wz in nazwy:
                return nazwy.index(wz)
        for wz in wzorce:
            for i, n in enumerate(nazwy):
                if n.startswith(wz):
                    return i
        return None

    def _dodaj(self, sciezka):
        lyr = QgsVectorLayer(
            sciezka, os.path.splitext(os.path.basename(sciezka))[0], "ogr")
        if not lyr.isValid():
            QMessageBox.warning(self._dialog, "Błąd",
                                "Nie udało się wczytać warstwy:\n" + sciezka)
            return
        self._warstwy.append(lyr)
        self.combo.addItem(lyr.name())
        self.combo.setCurrentIndex(self.combo.count() - 1)
        if self._klucz:
            QSettings().setValue(KLUCZ + self._klucz, sciezka)

    def _z_pliku(self):
        sciezka, _ = QFileDialog.getOpenFileName(
            self._dialog, "Wskaż warstwę", "", "ESRI shp (*.shp)")
        if sciezka:
            self._dodaj(sciezka)

    def wybrana(self):
        i = self.combo.currentIndex()
        return self._warstwy[i] if 0 <= i < len(self._warstwy) else None


class GenerujMapyDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(TYTUL)
        self.setMinimumWidth(640)
        self._buduj_ui()

    def _buduj_ui(self):
        uklad = QVBoxLayout(self)
        opis = QLabel(
            "Mapy do prezentacji NTG (A4 poziomo): mapa ogólna obiektu oraz "
            "dla każdej gminy mapy TSL, zabiegów i form ochrony przyrody "
            "(atlas po gminach, kadr do gminy). Layouty i grupy warstw NTG "
            "są przebudowywane przy każdym uruchomieniu; style warstw "
            "wejściowych bez zmian.")
        opis.setWordWrap(True)
        uklad.addWidget(opis)

        grupa = QGroupBox("Mapy")
        rz = QHBoxLayout(grupa)
        ust = QSettings()
        self.chk_mapy = {}
        for k, etyk in (("OGOLNA", "Ogólna"), ("TSL", "TSL"),
                        ("ZAB", "Zabiegi"), ("FOP", "Formy ochrony przyrody")):
            cb = QCheckBox(etyk)
            cb.setChecked(ust.value(KLUCZ + "mapa_" + k, True, type=bool))
            rz.addWidget(cb)
            self.chk_mapy[k] = cb
        uklad.addWidget(grupa)

        siatka = QGridLayout()
        warstwy = _warstwy_poligonowe()
        self.p_ls = _Picker(self, siatka, 0, "Obszar opracowania (Ls):",
                            ["ls"], warstwy)
        self.p_gmin = _Picker(self, siatka, 1, "Gminy:",
                              ["gmin", "gminy"], warstwy)
        self.p_obr = _Picker(self, siatka, 2, "Obręby:",
                             ["obr", "obreby"], warstwy)
        self.p_wydz = _Picker(self, siatka, 3,
                              "Wydzielenia z metadanymi (STL, ZABIEG):",
                              ["wydz_dopisane"], warstwy)
        self.p_nadl = _Picker(self, siatka, 4, "Nadleśnictwa (pole %s):"
                              % mapa_ogolna.POLE_NAZWA_NADL,
                              ["nadl", "nadlesnictwa", "inspectorate"],
                              warstwy, klucz_pliku="nadl")
        self.p_fop = _Picker(self, siatka, 5,
                             "Formy ochrony przyrody (pole %s):"
                             % mapy_gmin.POLE_FOP,
                             ["f_ochrony", "fop", "ochrona"], warstwy,
                             klucz_pliku="fop")

        siatka.addWidget(QLabel("Tytuł mapy ogólnej:"), 6, 0)
        self.e_tytul = QLineEdit(ust.value(KLUCZ + "tytul",
                                           mapa_ogolna.TYTUL_DOMYSLNY))
        siatka.addWidget(self.e_tytul, 6, 1, 1, 2)
        siatka.addWidget(QLabel("Powiat:"), 7, 0)
        self.e_powiat = QLineEdit(ust.value(KLUCZ + "powiat", ""))
        self.e_powiat.setPlaceholderText("np. jarosławski")
        siatka.addWidget(self.e_powiat, 7, 1, 1, 2)

        siatka.addWidget(QLabel("Folder na PNG:"), 8, 0)
        self.e_folder = QLineEdit(self._folder_domyslny())
        siatka.addWidget(self.e_folder, 8, 1)
        btn = QPushButton("Wskaż...")
        btn.clicked.connect(self._wskaz_folder)
        siatka.addWidget(btn, 8, 2)
        uklad.addLayout(siatka)

        self.chk_podklad = QCheckBox(
            "Podkład: mapa topograficzna GUGiK (WMTS, przybielona; "
            "wymaga internetu)")
        self.chk_podklad.setChecked(
            ust.value(KLUCZ + "podklad", True, type=bool))
        uklad.addWidget(self.chk_podklad)
        self.chk_png = QCheckBox(
            "Zapisz mapy do PNG (300 dpi; mapy gmin - plik na gminę)")
        self.chk_png.setChecked(True)
        uklad.addWidget(self.chk_png)
        self.chk_otworz = QCheckBox("Otwórz layout po wygenerowaniu")
        self.chk_otworz.setChecked(True)
        uklad.addWidget(self.chk_otworz)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.button(QDialogButtonBox.Ok).setText("Generuj")
        przyciski.accepted.connect(self._uruchom)
        przyciski.rejected.connect(self.reject)
        uklad.addWidget(przyciski)

    @staticmethod
    def _folder_domyslny():
        dom = QgsProject.instance().homePath()
        return os.path.join(dom, "NTG_mapy") if dom else ""

    def _wskaz_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Folder na PNG",
                                             self.e_folder.text().strip())
        if f:
            self.e_folder.setText(f)

    def _sprawdz(self, mapy, w):
        """w: {klucz: warstwa|None} - tylko warstwy potrzebne wybranym
        mapom."""
        if not mapy:
            return "Zaznacz co najmniej jedną mapę."
        potrzebne = {"GMIN", "OBR"}
        if "OGOLNA" in mapy:
            potrzebne |= {"LS", "NADL"}
        if "TSL" in mapy or "ZAB" in mapy:
            potrzebne.add("WYDZ")
        if "FOP" in mapy:
            potrzebne |= {"FOP", "LS"}
        opisy = {"LS": "Ls", "GMIN": "gminy", "OBR": "obręby",
                 "WYDZ": "wydzielenia z metadanymi", "NADL": "nadleśnictwa",
                 "FOP": "formy ochrony przyrody"}
        brak = [opisy[k] for k in sorted(potrzebne) if w[k] is None]
        if brak:
            return "Wskaż warstwy: " + ", ".join(brak) + "."
        uzyte = [w[k] for k in potrzebne]
        if len({id(x) for x in uzyte}) != len(uzyte):
            return "Każda z warstw musi być inna."
        braki = []
        if not mapa_ogolna.pole(w["GMIN"], mapa_ogolna.POLA_ID_GMINY):
            braki.append("Gminy: brak pola kodu (%s)"
                         % "/".join(mapa_ogolna.POLA_ID_GMINY))
        if not mapa_ogolna.pole(w["OBR"], mapa_ogolna.POLA_ID_OBREBU):
            braki.append("Obręby: brak pola kodu (%s)"
                         % "/".join(mapa_ogolna.POLA_ID_OBREBU))
        for nazwa, k in (("Gminy", "GMIN"), ("Obręby", "OBR")):
            if not mapa_ogolna.pole(w[k], mapa_ogolna.POLA_NAZWY):
                braki.append("%s: brak pola nazwy (%s)"
                             % (nazwa, "/".join(mapa_ogolna.POLA_NAZWY)))
        sprawdz_pola = [("NADL", "Nadleśnictwa",
                         [mapa_ogolna.POLE_NAZWA_NADL]),
                        ("WYDZ", "Wydzielenia", list(mapy_gmin.POLA_WYDZ)),
                        ("FOP", "Formy ochrony przyrody",
                         [mapy_gmin.POLE_FOP])]
        for k, nazwa, pola in sprawdz_pola:
            if k in potrzebne:
                for p in pola:
                    if not mapa_ogolna.pole(w[k], [p]):
                        braki.append("%s: brak pola %s" % (nazwa, p))
        return "\n".join(braki)

    def _uruchom(self):
        mapy = [k for k, cb in self.chk_mapy.items() if cb.isChecked()]
        w = {"LS": self.p_ls.wybrana(), "GMIN": self.p_gmin.wybrana(),
             "OBR": self.p_obr.wybrana(), "WYDZ": self.p_wydz.wybrana(),
             "NADL": self.p_nadl.wybrana(), "FOP": self.p_fop.wybrana()}
        blad = self._sprawdz(mapy, w)
        if blad:
            QMessageBox.warning(self, TYTUL, blad)
            return

        folder = None
        if self.chk_png.isChecked():
            folder = self.e_folder.text().strip()
            if not folder:
                QMessageBox.warning(self, TYTUL, "Wskaż folder na PNG.")
                return
            os.makedirs(folder, exist_ok=True)

        tytul, powiat = self.e_tytul.text().strip(), self.e_powiat.text().strip()
        ust = QSettings()
        ust.setValue(KLUCZ + "tytul", tytul)
        ust.setValue(KLUCZ + "powiat", powiat)
        for k, cb in self.chk_mapy.items():
            ust.setValue(KLUCZ + "mapa_" + k, cb.isChecked())
        z_podkladem = self.chk_podklad.isChecked()
        ust.setValue(KLUCZ + "podklad", z_podkladem)

        projekt = QgsProject.instance()
        layouty, komunikaty = [], []
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if "OGOLNA" in mapy:
                png = os.path.join(folder, "Mapa_ogolna_NTG.png") \
                    if folder else None
                layout, ok = mapa_ogolna.generuj(
                    projekt, w["GMIN"], w["OBR"], w["LS"], w["NADL"], tytul,
                    powiat, png, z_podkladem)
                layouty.append(layout)
                komunikaty.append(self._opis(layout, ok, ""))
            gminne = [k for k in ("TSL", "ZAB", "FOP") if k in mapy]
            if gminne:
                for layout, ok, kom in mapy_gmin.generuj(
                        projekt, gminne, w["GMIN"], w["OBR"], w["WYDZ"],
                        w["LS"], w["FOP"], powiat, folder, z_podkladem):
                    layouty.append(layout)
                    komunikaty.append(self._opis(
                        layout, ok, kom, layout.atlas().count()))
        except Exception as e:  # noqa: BLE001 - pokazujemy użytkownikowi
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, TYTUL, "Błąd:\n%s" % e)
            return
        QApplication.restoreOverrideCursor()

        self.accept()
        if self.chk_otworz.isChecked() and layouty:
            self.iface.openLayoutDesigner(layouty[0])
        tekst = "\n".join(komunikaty)
        if folder:
            tekst += "\n\nPNG: " + folder
        QMessageBox.information(self.iface.mainWindow(), TYTUL, tekst)

    @staticmethod
    def _opis(layout, ok, kom, stron=None):
        t = "Layout \"%s\"" % layout.name()
        if stron is not None:
            t += " - gmin: %d" % stron
        if ok is False:
            t += " - BŁĄD zapisu PNG %s" % kom
        return t
