# -*- coding: utf-8 -*-
"""Dialog "Przygotuj warstwy i bazę" (NTG materiały) - logika w
core/przygotuj.py, tu: wybór folderów, pytania do użytkownika, postęp,
raport."""
import os
import shutil

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QGridLayout,
    QLabel, QLineEdit, QMessageBox, QProgressDialog, QPushButton,
    QVBoxLayout,
)
from qgis.core import QgsVectorLayer

from ...baza_anonimizuj import anonimizuj_baze
from ...baza_polacz_wyszukaj import (
    WyborBazyWFolderzeDialog, sciezka_wzgledna, znajdz_bazy)
from ..core import przygotuj as core
from ..core.mapa_ogolna import (
    POLA_ID_GMINY, POLA_ID_OBREBU, POLE_NAZWA_NADL, pole)

KLUCZ = "LASR/protokol_ntg/"
TYTUL = "NTG - Przygotuj warstwy i bazę"


class PrzygotujDialog(QDialog):
    # podklasy (np. PPOŻ) zmieniają folder eksportu, nazwę bazy i tytuł
    TYTUL = TYTUL
    KLUCZ = KLUCZ
    SKROT = "NTG"
    FOLDER_EKSPORTU = core.FOLDER_EKSPORTU
    NAZWA_BAZY = core.NAZWA_BAZY
    NAZWA_BAZY_STARA = core.NAZWA_BAZY_STARA   # None = nic nie usuwamy
    NADL_WYMAGANE = True

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(self.TYTUL)
        self.setMinimumWidth(680)
        self._eksport_reczny = False
        self._buduj_ui()

    def _buduj_ui(self):
        uklad = QVBoxLayout(self)
        opis = QLabel(
            "Łączy warstwy (WYDZ, ODDZ, OBR, GMIN, LS) ze wszystkich folderów "
            "obiektu, w których jest WYDZ.shp, oraz bazy TPU. Zostawia tylko "
            "gminy i obręby, w których połączona baza ma wydzielenia (kody "
            "TERYT), oraz nadleśnictwa wokół obiektu, tworzy "
            "WYDZ_DOPISANE. Wynik (SHP, baza, raporty) w folderze eksportu.")
        opis.setWordWrap(True)
        uklad.addWidget(opis)

        ust = QSettings()
        siatka = QGridLayout()
        self.e_obiekt = QLineEdit(ust.value(self.KLUCZ + "obiekt", ""))
        self.e_obiekt.textEdited.connect(self._obiekt_zmieniony)
        self.e_nadl = QLineEdit(ust.value(self.KLUCZ + "nadl", ""))
        self.e_eksport = QLineEdit()
        self.e_eksport.textEdited.connect(self._eksport_edytowany)
        for i, (etyk, pole, fn) in enumerate((
                ("Folder obiektu:", self.e_obiekt, self._wskaz_obiekt),
                ("Granice nadleśnictw (.shp, pole %s)%s:"
                 % (POLE_NAZWA_NADL,
                    "" if self.NADL_WYMAGANE else ", opcjonalnie"),
                 self.e_nadl, self._wskaz_nadl),
                ("Folder eksportu:", self.e_eksport, self._wskaz_eksport))):
            siatka.addWidget(QLabel(etyk), i, 0)
            siatka.addWidget(pole, i, 1)
            b = QPushButton("Wskaż...")
            b.clicked.connect(fn)
            siatka.addWidget(b, i, 2)
        uklad.addLayout(siatka)
        self._obiekt_zmieniony()

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.button(QDialogButtonBox.Ok).setText("Przygotuj")
        przyciski.accepted.connect(self._uruchom)
        przyciski.rejected.connect(self.reject)
        uklad.addWidget(przyciski)

    # ------------------------------------------------------------ pola

    def _obiekt_zmieniony(self, *_):
        if not self._eksport_reczny:
            ob = self.e_obiekt.text().strip()
            self.e_eksport.setText(
                os.path.join(ob, self.FOLDER_EKSPORTU) if ob else "")

    def _eksport_edytowany(self, _):
        self._eksport_reczny = True

    def _wskaz_obiekt(self):
        f = QFileDialog.getExistingDirectory(self, "Folder obiektu",
                                             self.e_obiekt.text().strip())
        if f:
            self.e_obiekt.setText(os.path.normpath(f))
            self._obiekt_zmieniony()

    def _wskaz_nadl(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Granice nadleśnictw", self.e_nadl.text().strip(),
            "ESRI shp (*.shp)")
        if f:
            self.e_nadl.setText(os.path.normpath(f))

    def _wskaz_eksport(self):
        f = QFileDialog.getExistingDirectory(self, "Folder eksportu",
                                             self.e_eksport.text().strip())
        if f:
            self.e_eksport.setText(os.path.normpath(f))
            self._eksport_reczny = True

    # ------------------------------------------------------------ przebieg

    def _blad(self, tekst):
        QMessageBox.warning(self, self.TYTUL, tekst)
        return False

    def _sprawdz_wejscie(self, obiekt, nadl, eksport):
        if not os.path.isdir(obiekt):
            return self._blad("Wskazany folder obiektu nie istnieje.")
        if not eksport:
            return self._blad("Wskaż folder eksportu.")
        if not nadl and not self.NADL_WYMAGANE:
            return True
        if not os.path.isfile(nadl):
            return self._blad("Wskaż plik .shp z granicami nadleśnictw.")
        lyr = QgsVectorLayer(nadl, "nadl", "ogr")
        if not lyr.isValid():
            return self._blad("Nie da się otworzyć warstwy nadleśnictw.")
        if POLE_NAZWA_NADL not in [f.name() for f in lyr.fields()]:
            return self._blad("Warstwa nadleśnictw nie ma pola %s."
                              % POLE_NAZWA_NADL)
        return True

    def _wybierz_bazy(self, obiekt, eksport):
        """Lista baz do połączenia albo None (przerwano/brak)."""
        poziom, foldery, _glebsze = znajdz_bazy(obiekt, False)
        foldery = {f: b for f, b in foldery.items()
                   if not core._wewnatrz(f, eksport)}
        if not foldery:
            self._blad("W folderze obiektu nie ma baz TPU (*.mdb).")
            return None
        wiele = {f: b for f, b in foldery.items() if len(b) > 1}
        wybor = {}
        if wiele:
            dlg = WyborBazyWFolderzeDialog(self.iface, wiele, obiekt)
            if dlg.exec_() != QDialog.Accepted:
                return None
            wybor = dlg.wybor()
        lista = []
        for f, b in foldery.items():
            if len(b) == 1:
                lista.append(b[0])
            elif wybor.get(f):
                lista.append(wybor[f])
        if not lista:
            self._blad("Nie wybrano żadnej bazy.")
            return None
        return sorted(lista)

    def _potwierdz(self, obiekt, eksport, foldery_shp, bazy, gmin_zewn):
        szczeg = ["FOLDERY Z WARSTWAMI:"]
        szczeg += ["  %s: %s" % (f, ", ".join(sorted(w)))
                   for f, w in foldery_shp]
        szczeg += ["", "BAZY:"] + ["  " + sciezka_wzgledna(b, obiekt)
                                   for b in bazy]
        tekst = ("Folderów z WYDZ.shp: %d\nBaz TPU: %d\n"
                 % (len(foldery_shp), len(bazy)))
        if gmin_zewn:
            tekst += "Gminy z pliku: %s\n" % gmin_zewn
        istn = [p for p in (os.path.join(eksport, core.FOLDER_SHP),
                            os.path.join(eksport, self.NAZWA_BAZY))
                if os.path.exists(p)]
        stara = os.path.join(eksport, self.NAZWA_BAZY_STARA) \
            if self.NAZWA_BAZY_STARA else None
        tekst += "\nWynik: %s (baza zanonimizowana, kwerendy zostają)" \
            % eksport
        if istn:
            tekst += ("\n\n!!! W folderze eksportu są już: %s - zostaną "
                      "NADPISANE." % ", ".join(os.path.basename(p)
                                               for p in istn))
        if stara and os.path.exists(stara):
            tekst += ("\n\n!!! %s (z wcześniejszej wersji, bez anonimizacji) "
                      "zostanie USUNIĘTA." % self.NAZWA_BAZY_STARA)
            istn.append(stara)
        tekst += "\n\nKontynuować?"
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning if istn else QMessageBox.Question)
        msg.setWindowTitle(self.TYTUL)
        msg.setText(tekst)
        msg.setDetailedText("\n".join(szczeg))
        tak = msg.addButton("Tak", QMessageBox.AcceptRole)
        msg.addButton("Nie", QMessageBox.RejectRole)
        msg.exec_()
        return msg.clickedButton() == tak

    def _uruchom(self):
        obiekt = os.path.normpath(self.e_obiekt.text().strip())
        nadl = self.e_nadl.text().strip()
        eksport = os.path.normpath(self.e_eksport.text().strip()) \
            if self.e_eksport.text().strip() else ""
        if not self._sprawdz_wejscie(obiekt, nadl, eksport):
            return
        ust = QSettings()
        ust.setValue(self.KLUCZ + "obiekt", obiekt)
        ust.setValue(self.KLUCZ + "nadl", nadl)

        foldery_shp = core.szukaj_folderow_shp(obiekt, eksport)
        if not foldery_shp:
            self._blad("W folderze obiektu nie znaleziono żadnego WYDZ.shp.")
            return
        zrodla = core.zrodla_warstw(foldery_shp)

        bazy = self._wybierz_bazy(obiekt, eksport)
        if bazy is None:
            return

        gmin_zewn = None
        if "GMIN" not in zrodla:
            QMessageBox.information(
                self, self.TYTUL, "W folderach obiektu nie ma warstwy GMIN - "
                "wskaż warstwę gmin (np. PRG, EGiB).")
            gmin_zewn, _ = QFileDialog.getOpenFileName(
                self, "Warstwa gmin", obiekt, "ESRI shp (*.shp)")
            if not gmin_zewn:
                return

        if not self._potwierdz(obiekt, eksport, foldery_shp, bazy,
                               gmin_zewn):
            return

        self.accept()
        self._wykonaj(obiekt, nadl, eksport, zrodla, bazy, gmin_zewn)

    def _wykonaj(self, obiekt, nadl, eksport, zrodla, bazy, gmin_zewn):
        okno = self.iface.mainWindow()
        pd = QProgressDialog("", "Przerwij", 0, 100, okno)
        pd.setWindowTitle(self.TYTUL)
        pd.setWindowModality(Qt.WindowModal)
        pd.setMinimumDuration(0)

        def krok(tekst, proc):
            pd.setLabelText(tekst)
            pd.setValue(proc)
            QApplication.processEvents()
            return not pd.wasCanceled()

        def postep(k, n):
            QApplication.processEvents()
            return not pd.wasCanceled()

        shp = os.path.join(eksport, core.FOLDER_SHP)
        robocze = os.path.join(eksport, core.FOLDER_ROBOCZY)
        raport = ["Przygotuj warstwy i bazę (%s)" % self.SKROT,
                  "Obiekt: " + obiekt,
                  "Eksport: " + eksport, ""]
        try:
            if os.path.isdir(shp):
                shutil.rmtree(shp)
            os.makedirs(shp)

            if not krok("Łączenie warstw WYDZ, ODDZ, LS...", 5):
                return self._przerwano(pd)
            wyniki = core.polacz_warstwy(zrodla, core.WARSTWY_LACZONE, shp,
                                         postep)
            if wyniki is None:
                return self._przerwano(pd)
            if not krok("Łączenie warstw GMIN, OBR...", 30):
                return self._przerwano(pd)
            if gmin_zewn:
                # wskazany plik też przez łączenie - duplikaty, EPSG:2180
                zrodla["GMIN"] = [("(wskazany plik)", gmin_zewn)]
            wyn2 = core.polacz_warstwy(zrodla, core.WARSTWY_WYCINANE,
                                       robocze, postep)
            if wyn2 is None:
                return self._przerwano(pd)
            wyniki += wyn2
            raport.append("Raport łączenia warstw: " +
                          core.pw.zapisz_raport(eksport, wyniki))
            for r in wyniki:
                raport.append("  %s: %d obiektów, usunięte duplikaty: %d"
                              % (r["nazwa"], r["zapisano"], r["duplikaty"])
                              + (" BŁĄD ZAPISU: " + r["blad_zapisu"]
                                 if r["blad_zapisu"] else ""))
            for brak in [n for n in core.WARSTWY_LACZONE + ("OBR",)
                         if n not in zrodla]:
                raport.append("  BRAK warstwy %s w folderach obiektu" % brak)

            if not krok("Łączenie baz TPU (%d)..." % len(bazy), 40):
                return self._przerwano(pd)
            baza_sc = os.path.join(eksport, self.NAZWA_BAZY)
            if os.path.exists(baza_sc):
                os.remove(baza_sc)
            ok, kom, bledy = core.polacz_bazy(
                bazy, baza_sc, os.path.join(eksport, "Raporty"))
            raport.append("Bazy: " + kom)
            for b, t, w, e in bledy:
                raport.append("  BŁĄD %s | %s | %s | %s" % (b, t, w, e))
            if not ok:
                pd.close()
                rap = core.zapisz_raport(eksport, raport, skrot=self.SKROT)
                QMessageBox.critical(okno, self.TYTUL, "Łączenie baz przerwane: "
                                     "%s\n\nRaport: %s" % (kom, rap))
                return

            if not krok("Anonimizacja bazy...", 65):
                return self._przerwano(pd)
            if not anonimizuj_baze(baza_sc, usun_kwerendy=False):
                raise RuntimeError("Nie udało się zanonimizować bazy " +
                                   baza_sc)
            raport.append("Baza zanonimizowana (kwerendy zostawione): " +
                          self.NAZWA_BAZY)
            stara = os.path.join(eksport, self.NAZWA_BAZY_STARA) \
                if self.NAZWA_BAZY_STARA else None
            if stara and os.path.exists(stara):
                os.remove(stara)
                raport.append("Usunięto %s z wcześniejszej wersji (bez "
                              "anonimizacji)" % self.NAZWA_BAZY_STARA)

            if not krok("Wybór gmin i obrębów z wydzieleniami w bazie...",
                        70):
                return self._przerwano(pd)
            kody = core.obreby_z_bazy(baza_sc)
            raport.append("Obrębów z wydzieleniami w bazie: %d" % len(kody))
            for nazwa, pola_id, dlugosc in (
                    ("GMIN", POLA_ID_GMINY, 7), ("OBR", POLA_ID_OBREBU, 11)):
                zrodlo = os.path.join(robocze, nazwa + ".shp")
                if not os.path.exists(zrodlo):
                    continue
                pole_kodu = pole(QgsVectorLayer(zrodlo, nazwa, "ogr"),
                                 pola_id)
                if not pole_kodu:
                    raise RuntimeError("%s: brak pola kodu TERYT (%s)"
                                       % (nazwa, "/".join(pola_id)))
                n, odrz, bez, znalezione = core.wytnij_objete(
                    zrodlo, os.path.join(shp, nazwa + ".shp"), kody=kody,
                    pole_kodu=pole_kodu, dlugosc=dlugosc, nazwa=nazwa)
                raport.append("%s: zostawiono %d, usunięto %d (bez wydzieleń "
                              "w bazie)%s" % (nazwa, n, odrz,
                                              ", w tym bez kodu w polu %s: %d"
                                              % (pole_kodu, bez) if bez else ""))
                brak = sorted({k[:dlugosc] for k in kody} - znalezione)
                if brak:
                    raport.append("  !!! w bazie są, w warstwie %s brak "
                                  "(%d):" % (nazwa, len(brak)))
                    raport += ["    " + core.opis_kodu(k) for k in brak]

            if not krok("Nadleśnictwa wokół obiektu...", 80):
                return self._przerwano(pd)
            if nadl:
                gmin_sc = os.path.join(shp, "GMIN.shp")
                prost = core.zasieg_z_zapasem(
                    gmin_sc if os.path.exists(gmin_sc)
                    else os.path.join(shp, "WYDZ.shp"))
                n, odrz, _, _ = core.wytnij_objete(
                    nadl, os.path.join(shp, core.NAZWA_NADL + ".shp"),
                    prostokat=prost, nazwa=core.NAZWA_NADL)
                raport.append("Nadleśnictwa: zostawiono %d, usunięto %d" %
                              (n, odrz))
            else:
                raport.append("Nadleśnictwa: nie wskazano warstwy - pominięto")

            if not krok("Dopisywanie metadanych (WYDZ_DOPISANE)...", 85):
                return self._przerwano(pd)
            core.dopisz_metadane(self.iface, os.path.join(shp, "WYDZ.shp"),
                                 baza_sc)
            raport.append("WYDZ_DOPISANE: utworzono")
        except Exception as e:  # noqa: BLE001 - pokazujemy użytkownikowi
            pd.close()
            raport.append("BŁĄD: %s" % e)
            rap = core.zapisz_raport(eksport, raport, skrot=self.SKROT)
            QMessageBox.critical(okno, self.TYTUL, "Błąd: %s\n\nRaport: %s"
                                 % (e, rap))
            return
        finally:
            shutil.rmtree(robocze, ignore_errors=True)
        pd.close()

        rap = core.zapisz_raport(eksport, raport, skrot=self.SKROT)
        tekst = ("Gotowe.\n\n%s\n\nRaport: %s"
                 % ("\n".join(raport[4:]), rap))
        if bledy:
            QMessageBox.warning(
                okno, self.TYTUL,
                "Bazy połączone z błędami (szczegóły w raporcie).\n\n" + tekst)
        else:
            QMessageBox.information(okno, self.TYTUL, tekst)

    def _przerwano(self, pd):
        pd.close()
        self.iface.messageBar().pushMessage(self.TYTUL, "Przerwano.")
