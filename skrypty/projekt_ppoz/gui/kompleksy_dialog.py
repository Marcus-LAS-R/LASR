# -*- coding: utf-8 -*-
"""Dialog "Wyznacz kompleksy leśne pow. 300 ha" (PPOŻ materiały) - logika
w core/kompleksy.py, tu: wybór warstwy/bazy/odległości, postęp, zapis,
raport i warstwy w projekcie."""
import os
import random
import shutil

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QGridLayout,
    QLabel, QLineEdit, QProgressDialog, QPushButton, QVBoxLayout,
)
from ...przyciski import QDialogButtonBox, QMessageBox
from qgis.core import (
    QgsCategorizedSymbolRenderer, QgsFillSymbol, QgsProject,
    QgsRendererCategory, QgsVectorLayer,
)

from ..core import kompleksy as core
from .przygotuj_dialog import FOLDER_EKSPORTU, NAZWA_BAZY

KLUCZ = "LASR/projekt_ppoz/kompleksy/"
TYTUL = "PPOŻ - Wyznacz kompleksy leśne pow. 300 ha"
FOLDER_WYNIKU = "Kompleksy_300ha"
GRUPA = "PPOŻ - kompleksy pow. 300 ha"


def _domyslna_wydz():
    """WYDZ.shp z folderu eksportu "Przygotuj warstwy i bazę" (PPOŻ)."""
    obiekt = QSettings().value("LASR/projekt_ppoz/obiekt", "")
    if obiekt:
        sc = os.path.join(obiekt, FOLDER_EKSPORTU, "SHP", "WYDZ.shp")
        if os.path.isfile(sc):
            return sc
    return ""


class KompleksyDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(TYTUL)
        self.setMinimumWidth(680)
        self._buduj_ui()

    def _buduj_ui(self):
        uklad = QVBoxLayout(self)
        opis = QLabel(
            "Wyznacza kompleksy leśne bez względu na własność: nasze "
            "wydzielenia (WYDZ) + wydzielenia z BDL (PGL LP i poza PGL LP wg "
            "PUL, wszystkie rodzaje powierzchni). Poligony oddalone o nie "
            "więcej niż odległość łączenia tworzą jeden kompleks. Zostają "
            "kompleksy powyżej %d ha z naszymi wydzieleniami. Powierzchnie "
            "wydzieleń w tabeli - z bazy." % core.PROG_HA)
        opis.setWordWrap(True)
        uklad.addWidget(opis)

        ust = QSettings()
        siatka = QGridLayout()
        self.e_wydz = QLineEdit(ust.value(KLUCZ + "wydz", "") or
                                _domyslna_wydz())
        self.e_wydz.editingFinished.connect(self._wydz_zmieniona)
        self.e_baza = QLineEdit(ust.value(KLUCZ + "baza", ""))
        self.e_wynik = QLineEdit(ust.value(KLUCZ + "wynik", ""))
        for i, (etyk, pole, fn) in enumerate((
                ("Warstwa WYDZ (.shp):", self.e_wydz, self._wskaz_wydz),
                ("Baza TPU (.mdb):", self.e_baza, self._wskaz_baze),
                ("Folder wyniku:", self.e_wynik, self._wskaz_wynik))):
            siatka.addWidget(QLabel(etyk), i, 0)
            siatka.addWidget(pole, i, 1)
            b = QPushButton("Wskaż...")
            b.clicked.connect(fn)
            siatka.addWidget(b, i, 2)

        self.s_odl = QDoubleSpinBox()
        self.s_odl.setDecimals(1)
        self.s_odl.setRange(0.0, 1000.0)
        self.s_odl.setSingleStep(0.1)
        self.s_odl.setSuffix(" m")
        self.s_odl.setValue(float(ust.value(KLUCZ + "odl",
                                            core.ODLEGLOSC_DOMYSLNA)))
        siatka.addWidget(QLabel("Odległość łączenia (<=):"), 3, 0)
        siatka.addWidget(self.s_odl, 3, 1)

        self.s_zapas = QDoubleSpinBox()
        self.s_zapas.setDecimals(0)
        self.s_zapas.setRange(100.0, 20000.0)
        self.s_zapas.setSingleStep(500.0)
        self.s_zapas.setSuffix(" m")
        self.s_zapas.setValue(float(ust.value(KLUCZ + "zapas",
                                              core.ZAPAS_DOMYSLNY)))
        self.s_zapas.setToolTip(
            "Pas wokół WYDZ, z którego na początku pobierane są lasy z BDL. "
            "Kompleksy do %d ha wychodzące poza ten pas są dociągane "
            "automatycznie; większe - nie (dostają NIEPELNY = T)."
            % core.PROG_HA)
        siatka.addWidget(QLabel("Zapas pobierania z BDL:"), 4, 0)
        siatka.addWidget(self.s_zapas, 4, 1)
        uklad.addLayout(siatka)

        self.c_projekt = QCheckBox("Dodaj wynik do projektu")
        self.c_projekt.setChecked(True)
        uklad.addWidget(self.c_projekt)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.button(QDialogButtonBox.Ok).setText("Wyznacz")
        przyciski.accepted.connect(self._uruchom)
        przyciski.rejected.connect(self.reject)
        uklad.addWidget(przyciski)
        if not self.e_baza.text() or not self.e_wynik.text():
            self._wydz_zmieniona()

    # ------------------------------------------------------------ pola

    def _wydz_zmieniona(self):
        """Baza i folder wyniku domyślnie z folderu eksportu PPOŻ:
        <eksport>\\SHP\\WYDZ.shp -> <eksport>\\Baza_PPOZ..., <eksport>\\
        Kompleksy_300ha."""
        wydz = self.e_wydz.text().strip()
        if not wydz:
            return
        kat = os.path.dirname(wydz)
        eksport = os.path.dirname(kat) \
            if os.path.basename(kat).upper() == "SHP" else kat
        baza = os.path.join(eksport, NAZWA_BAZY)
        if os.path.isfile(baza):
            self.e_baza.setText(baza)
        self.e_wynik.setText(os.path.join(eksport, FOLDER_WYNIKU))

    def _wskaz_wydz(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Warstwa WYDZ", self.e_wydz.text().strip(),
            "ESRI shp (*.shp)")
        if f:
            self.e_wydz.setText(os.path.normpath(f))
            self._wydz_zmieniona()

    def _wskaz_baze(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Baza TPU", self.e_baza.text().strip() or
            os.path.dirname(self.e_wydz.text().strip()), "Access (*.mdb)")
        if f:
            self.e_baza.setText(os.path.normpath(f))

    def _wskaz_wynik(self):
        f = QFileDialog.getExistingDirectory(self, "Folder wyniku",
                                             self.e_wynik.text().strip())
        if f:
            self.e_wynik.setText(os.path.normpath(f))

    # ------------------------------------------------------------ przebieg

    def _blad(self, tekst):
        QMessageBox.warning(self, TYTUL, tekst)

    def _uruchom(self):
        wydz = self.e_wydz.text().strip()
        baza = self.e_baza.text().strip()
        wynik = self.e_wynik.text().strip()
        if not os.path.isfile(wydz):
            return self._blad("Wskaż warstwę WYDZ (.shp).")
        if not os.path.isfile(baza):
            return self._blad("Wskaż bazę TPU (.mdb).")
        if not wynik:
            return self._blad("Wskaż folder wyniku.")
        wynik = os.path.normpath(wynik)
        if os.path.normcase(wynik) == os.path.normcase(
                os.path.dirname(os.path.abspath(wydz))):
            return self._blad("Folder wyniku nie może być folderem warstwy "
                              "WYDZ (wynik nadpisałby dane).")
        istn = [n for n in (core.NAZWA_KOMPLEKSY + ".shp",
                            core.NAZWA_WYDZ + ".shp", core.NAZWA_XLSX,
                            core.FOLDER_OSOBNO)
                if os.path.exists(os.path.join(wynik, n))]
        if istn and QMessageBox.question(
                self, TYTUL, "W folderze wyniku są już: %s - zostaną "
                "NADPISANE (warstwy z tego folderu zostaną usunięte z "
                "projektu).\n\nKontynuować?" % ", ".join(istn),
                QMessageBox.Yes | QMessageBox.Abort) != QMessageBox.Yes:
            return
        ust = QSettings()
        ust.setValue(KLUCZ + "wydz", wydz)
        ust.setValue(KLUCZ + "baza", baza)
        ust.setValue(KLUCZ + "wynik", wynik)
        ust.setValue(KLUCZ + "odl", self.s_odl.value())
        ust.setValue(KLUCZ + "zapas", self.s_zapas.value())
        self.accept()
        self._wykonaj(wydz, baza, wynik, round(self.s_odl.value(), 1),
                      self.s_zapas.value(), self.c_projekt.isChecked())

    def _usun_z_projektu(self, folder):
        prj = QgsProject.instance()
        kat = os.path.normcase(os.path.abspath(folder))
        for lyr in list(prj.mapLayers().values()):
            zr = lyr.source().split("|")[0]
            if os.path.normcase(os.path.abspath(zr)).startswith(kat + os.sep):
                prj.removeMapLayer(lyr.id())

    def _wykonaj(self, wydz, baza, wynik, odl, zapas, do_projektu):
        okno = self.iface.mainWindow()
        pd = QProgressDialog("", "Przerwij", 0, 0, okno)
        pd.setWindowTitle(TYTUL)
        pd.setWindowModality(Qt.WindowModal)
        pd.setMinimumDuration(0)

        def postep(tekst, *_):
            pd.setLabelText(tekst)
            QApplication.processEvents()
            return not pd.wasCanceled()

        raport = [TYTUL, "WYDZ: " + wydz, "Baza: " + baza,
                  "Odległość łączenia: <= %.1f m" % odl,
                  "Zapas pobierania BDL: %.0f m" % zapas,
                  "Próg: > %d ha" % core.PROG_HA, ""]
        try:
            postep("Wczytywanie WYDZ i bazy...")
            lyr, wydz_geom = core.wczytaj_wydz(wydz)
            pow_w, nazwy = core.dane_z_bazy(baza)
            raport.append("Poligonów WYDZ: %d" % len(wydz_geom))

            gr, kompleksy, n_kom, limit, niepewne = core.wyznacz(
                wydz_geom, odl, zapas, postep, raport.append)
            raport.append("Pobrane komórki BDL (%.0f x %.0f m): %d"
                          % (core.bdl.ROZMIAR_KOMORKI,
                             core.bdl.ROZMIAR_KOMORKI, n_kom))
            if limit:
                raport.append("!!! Osiągnięto limit pobierania (%d komórek "
                              "/ %d rund)" % (core.MAX_KOMOREK,
                                              core.MAX_RUND))
            for pole, n in niepewne:
                raport.append("!!! Kompleks %.2f ha (naszych poligonów: %d) "
                              "nie został dociągnięty do końca - może mieć "
                              "ponad %d ha" % (pole, n, core.PROG_HA))

            postep("Powierzchnie i kontury kompleksów...")
            tabele = {}
            for k in kompleksy:
                core.powierzchnie(gr, k)
                tabele[k["nr"]] = core.wiersze_kompleksu(lyr, gr, k, pow_w,
                                                         nazwy)

            postep("Zapis warstw i tabeli...")
            self._usun_z_projektu(wynik)
            os.makedirs(wynik, exist_ok=True)
            shutil.rmtree(os.path.join(wynik, core.FOLDER_OSOBNO),
                          ignore_errors=True)
            core.zapisz_warstwy(wynik, lyr, gr, kompleksy, wydz_geom)
            xlsx = os.path.join(wynik, core.NAZWA_XLSX)
            if kompleksy:
                core.zapisz_xlsx(xlsx, kompleksy, tabele)

            raport += ["", "Kompleksów > %d ha: %d" % (core.PROG_HA,
                                                       len(kompleksy))]
            for k in kompleksy:
                w = tabele[k["nr"]]
                braki = [x[4] for x in w if x[5] is None]
                raport.append(
                    "  nr %d: %.4f ha (nasze %.4f, PGL LP %.4f, inne %.4f), "
                    "wydzieleń: %d%s" % (
                        k["nr"], k["pole"], k["pow_nasze"], k["pow_pgl"],
                        k["pow_inne"], len(w),
                        " - KONTUR NIEPEŁNY (wychodzi poza pobrany obszar "
                        "BDL, zwiększ zapas)" if k["niepelny"] else ""))
                if braki:
                    raport.append("    !!! brak w bazie (%d): %s"
                                  % (len(braki), ", ".join(braki)))
        except core.Przerwano:
            pd.close()
            self.iface.messageBar().pushMessage(TYTUL, "Przerwano.")
            return
        except Exception as e:  # noqa: BLE001 - pokazujemy użytkownikowi
            pd.close()
            raport.append("BŁĄD: %s" % e)
            rap = core.zapisz_raport(wynik, raport) \
                if os.path.isdir(wynik) else ""
            QMessageBox.critical(okno, TYTUL, "Błąd: %s\n\nRaport: %s"
                                 % (e, rap))
            return
        pd.close()

        rap = core.zapisz_raport(wynik, raport)
        if do_projektu:
            self._dodaj_do_projektu(wynik)
        tekst = "Gotowe.\n\n%s\n\nWynik: %s\nRaport: %s" % (
            "\n".join(raport[7:]), wynik, rap)
        if not kompleksy:
            tekst += "\n\nNie ma kompleksów > %d ha - tabela XLSX nie " \
                "została utworzona." % core.PROG_HA
        ostrz = limit or niepewne or any(k["niepelny"] for k in kompleksy)
        (QMessageBox.warning if ostrz else QMessageBox.information)(
            okno, TYTUL, tekst)

    def _dodaj_do_projektu(self, wynik):
        prj = QgsProject.instance()
        korzen = prj.layerTreeRoot()
        grupa = korzen.findGroup(GRUPA) or korzen.insertGroup(0, GRUPA)
        for nazwa, wypelnienie in ((core.NAZWA_WYDZ, True),
                                   (core.NAZWA_KOMPLEKSY, False)):
            lyr = QgsVectorLayer(os.path.join(wynik, nazwa + ".shp"), nazwa,
                                 "ogr")
            if not lyr.isValid():
                continue
            _styl_kategorie(lyr, wypelnienie)
            prj.addMapLayer(lyr, False)
            grupa.insertLayer(0, lyr)


def _styl_kategorie(lyr, wypelnienie):
    """Każdy kompleks w innym kolorze (NR_KOMPL); kompleksy - sam kontur."""
    los = random.Random(7)
    kategorie = []
    for nr in sorted(lyr.uniqueValues(lyr.fields().indexOf("NR_KOMPL"))):
        kolor = QColor.fromHsv(los.randrange(360), 200, 220)
        if wypelnienie:
            sym = QgsFillSymbol.createSimple({
                "color": "%d,%d,%d,140" % (kolor.red(), kolor.green(),
                                           kolor.blue()),
                "outline_color": "80,80,80", "outline_width": "0.1"})
        else:
            sym = QgsFillSymbol.createSimple({
                "style": "no", "outline_color": kolor.name(),
                "outline_width": "0.8"})
        kategorie.append(QgsRendererCategory(nr, sym, "Kompleks %s" % nr))
    if kategorie:
        lyr.setRenderer(QgsCategorizedSymbolRenderer("NR_KOMPL", kategorie))
