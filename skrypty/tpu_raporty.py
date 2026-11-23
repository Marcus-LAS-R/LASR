# -*- coding: utf-8 -*-
"""Zestawienia raportów TPU (menu Generuj).

Generuje raporty Taksatora PU dla wybranych obrębów bazy jednym
uruchomieniem - bez klikania w Taksatorze (biblioteka raportów Taksatora
przez pomocnika .NET, tpu_raporty_pomocnik.cs). Okno: baza .mdb, lista
raportów (na górze "Zestawienie raportów" - domyślnie jedyne zaznaczone,
pod nim 18 raportów Taksatora), lista obrębów z F_COMMUNITY bazy
(domyślnie wszystkie).

Wynik: <folder bazy>/Raporty_TPU/<folder raportu>/<gmina>-<obręb>-<nazwa>
.xlsx (nazwy jak w Taksatorze); raport raport_tpu_<znacznik>.txt
w Raporty_TPU. Baza źródłowa nie jest zmieniana: raporty liczone na
tymczasowej kopii (bez hasła; starsza struktura bazy aktualizowana na kopii
procedurą Taksatora). Excel składa zestawienie z 16 raportów i zapisuje xlsx.

Wymaga zainstalowanego Taksatora PU (2.0.56+) i Excela. Plan, pomocnik,
Excel - tpu_raporty_pliki.py; na płyty (bez danych osobowych) -
plyty_na_oddanie_pliki.
"""
import os
import platform
import queue
import shutil
import tempfile
import threading
import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QProgressDialog,
    QPushButton, QSplitter, QVBoxLayout, QWidget,
)
from qgis.core import Qgis, QgsMessageLog, QgsSettings

from . import tpu_raporty_pliki as tp
from .baza_wrapper import Baza
from .przyciski import QDialogButtonBox, QMessageBox
from .rozdziel_upul_isl.core.rozdziel import _haslo_bazy
from .znacznik_czasu import znacznik

_TYTUL = 'Zestawienia raportów TPU'
_KLUCZ_BAZY = 'lasr/tpu_raporty/baza'


def _log(tekst, poziom=Qgis.Info):
    QgsMessageLog.logMessage(f'{_TYTUL}: {tekst}', 'Las-R', poziom)


class Przerwano(Exception):
    pass


# ----------------------------------------------------------------- okno

class _Lista(QWidget):
    """Lista z polami wyboru + Wszystko/Nic."""

    def __init__(self, tytul, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.etykieta = QLabel(tytul)
        lay.addWidget(self.etykieta)
        self.lw = QListWidget()
        lay.addWidget(self.lw, 1)
        h = QHBoxLayout()
        for tekst, stan in (('Wszystko', Qt.Checked), ('Nic', Qt.Unchecked)):
            b = QPushButton(tekst)
            b.clicked.connect(lambda _, s=stan: self.ustaw(s))
            h.addWidget(b)
        h.addStretch()
        lay.addLayout(h)

    def dodaj(self, tekst, dane, zaznaczona, podpowiedz=''):
        it = QListWidgetItem(tekst)
        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked if zaznaczona else Qt.Unchecked)
        it.setData(Qt.UserRole, dane)
        if podpowiedz:
            it.setToolTip(podpowiedz)
        self.lw.addItem(it)

    def ustaw(self, stan):
        for i in range(self.lw.count()):
            self.lw.item(i).setCheckState(stan)

    def wybrane(self):
        return [self.lw.item(i).data(Qt.UserRole)
                for i in range(self.lw.count())
                if self.lw.item(i).checkState() == Qt.Checked]


class RaportyDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL)
        self.resize(760, 640)
        self.obreby = []

        uklad = QVBoxLayout(self)
        siatka = QGridLayout()
        siatka.addWidget(QLabel('Baza TPU (.mdb):'), 0, 0)
        self.le_baza = QLineEdit()
        siatka.addWidget(self.le_baza, 0, 1)
        b = QPushButton('Wskaż...')
        b.clicked.connect(self._wskaz_baze)
        siatka.addWidget(b, 0, 2)
        siatka.setColumnStretch(1, 1)
        uklad.addLayout(siatka)

        self.lab_info = QLabel()
        self.lab_info.setWordWrap(True)
        uklad.addWidget(self.lab_info)

        podzial = QSplitter(Qt.Horizontal)
        self.raporty = _Lista('Raporty:')
        for rid, nazwa, _, osobowe in tp.RAPORTY:
            tekst = nazwa if rid == tp.ZESTAWIENIE else f'{rid}. {nazwa}'
            self.raporty.dodaj(
                tekst, rid, rid == tp.ZESTAWIENIE,
                f'Folder wyników: {tp.FOLDER_RAPORTOW}\\{tp.FOLDERY[rid]}' +
                ('\nZawiera dane osobowe - nie trafia na płyty' if osobowe
                 and rid != tp.ZESTAWIENIE else '') +
                ('\n16 raportów jako arkusze jednego pliku (na płyty bez '
                 'arkuszy z danymi osobowymi)' if rid == tp.ZESTAWIENIE
                 else ''))
        f = self.raporty.lw.item(0).font()
        f.setBold(True)
        self.raporty.lw.item(0).setFont(f)
        podzial.addWidget(self.raporty)
        self.lista_obrebow = _Lista('Obręby w bazie:')
        podzial.addWidget(self.lista_obrebow)
        podzial.setSizes([480, 280])
        uklad.addWidget(podzial, 1)

        self.bb = QDialogButtonBox(QDialogButtonBox.Ok |
                                   QDialogButtonBox.Cancel)
        self.bb.button(QDialogButtonBox.Ok).setText('Uruchom')
        self.bb.accepted.connect(self._akceptuj)
        self.bb.rejected.connect(self.reject)
        uklad.addWidget(self.bb)

        self.taksator = tp.katalog_taksatora()
        self.le_baza.editingFinished.connect(self._wczytaj_obreby)
        ostatnia = QgsSettings().value(_KLUCZ_BAZY, '')
        if ostatnia and os.path.isfile(ostatnia):
            self.le_baza.setText(ostatnia)
        self._wczytaj_obreby()

    def _wskaz_baze(self):
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę TPU', self.le_baza.text(),
            'Baza TPU (*.mdb)')
        if sc:
            self.le_baza.setText(os.path.normpath(sc))
            self._wczytaj_obreby()

    def baza(self):
        return self.le_baza.text().strip()

    def _wczytaj_obreby(self):
        self.lista_obrebow.lw.clear()
        self.obreby = []
        info = []
        if not self.taksator:
            info.append('UWAGA: nie znaleziono Taksatora PU (rejestr '
                        f'{tp.KLUCZ_REJESTRU}, {tp.KATALOG_DOMYSLNY}) - '
                        'raporty nie powstaną.')
        sc = self.baza()
        if sc and os.path.isfile(sc):
            b = Baza(sc)
            try:
                if b.polacz():
                    self.obreby = tp.obreby_z_bazy(b.pobierz_obreby() or [])
            except Exception as e:
                info.append(f'Nie udało się odczytać obrębów z bazy: {e}')
            finally:
                b.zamknij()
            for o in self.obreby:
                self.lista_obrebow.dodaj(
                    f"{o['municip']}-{o['community']} {o['nazwa']}", o, True)
            info.append(f'Wynik: {tp.folder_raportow(sc)}')
            if sc and not self.obreby:
                info.append('Brak obrębów w F_COMMUNITY bazy.')
        self.lista_obrebow.etykieta.setText(
            f'Obręby w bazie ({len(self.obreby)}):')
        self.lab_info.setText('\n'.join(info))

    def _akceptuj(self):
        if not self.taksator:
            QMessageBox.warning(
                self, _TYTUL, 'Nie znaleziono zainstalowanego Taksatora PU '
                '(ReportsHelper.dll) - raportów nie da się wygenerować.')
            return
        if not os.path.isfile(self.baza()):
            QMessageBox.warning(self, _TYTUL, 'Wskaż istniejącą bazę .mdb.')
            return
        if not self.raporty.wybrane():
            QMessageBox.warning(self, _TYTUL, 'Zaznacz co najmniej jeden '
                                'raport.')
            return
        if not self.lista_obrebow.wybrane():
            QMessageBox.warning(self, _TYTUL, 'Zaznacz co najmniej jeden '
                                'obręb.')
            return
        QgsSettings().setValue(_KLUCZ_BAZY, self.baza())
        self.accept()


# ------------------------------------------------------------- przebieg

def kopia_bez_hasla(baza, katalog):
    """Kopia bazy w katalogu tymczasowym BEZ hasła (biblioteka Taksatora nie
    zna hasła pw baz po kompaktowaniu we wtyczce). Zwykła kopia pliku (baza
    może być otwarta w Taksatorze), hasło zdejmowane z kopii przez DAO."""
    import win32com.client
    kopia = os.path.join(katalog, 'baza.mdb')
    shutil.copy2(baza, kopia)
    silnik = win32com.client.dynamic.Dispatch('DAO.DBEngine.120')
    haslo = _haslo_bazy(silnik, kopia)
    if haslo:
        db = silnik.OpenDatabase(kopia, True, False, f';pwd={haslo}')
        try:
            db.NewPassword(haslo, '')
        finally:
            db.Close()
    return kopia


def _postep_okno(iface):
    pd = QProgressDialog('', 'Przerwij', 0, 100, iface.mainWindow())
    pd.setWindowTitle(_TYTUL)
    pd.setWindowModality(Qt.WindowModal)
    pd.setMinimumDuration(0)
    pd.setValue(0)
    return pd


def _czytaj(strumien, kolejka):
    for linia in iter(strumien.readline, b''):
        kolejka.put(linia)
    kolejka.put(None)


def generuj_xls(exe, taksator, kopia, zadania, katalog, postep):
    """Pomocnik w jednym procesie dla wszystkich zadań. postep(zrobione)
    -> False przerywa (proces zabity, Przerwano). Zwraca {plik .xls: błąd}."""
    plik = os.path.join(katalog, 'zadania.txt')
    tp.zapisz_zadania(zadania, plik)
    po_nr = {str(nr): sc for nr, _, _, sc in zadania}
    bledy, zrobione, ogolne = {}, 0, []
    proc = tp.proces_raportow(exe, taksator, kopia, plik)
    kolejka = queue.Queue()
    watek = threading.Thread(target=_czytaj, args=(proc.stdout, kolejka),
                             daemon=True)
    watek.start()
    try:
        while True:
            try:
                linia = kolejka.get(timeout=0.1)
            except queue.Empty:
                if postep(zrobione) is False:
                    raise Przerwano()
                continue
            if linia is None:
                break
            p = tp.parsuj(tp._tekst(linia))
            if p[0] == 'OK':
                zrobione += 1
            elif p[0] == 'BLAD':
                if p[1] in po_nr:
                    zrobione += 1
                    bledy[po_nr[p[1]]] = p[2]
                else:
                    ogolne.append(p[2] or p[1])
            if postep(zrobione) is False:
                raise Przerwano()
        proc.wait()
    except BaseException:
        proc.kill()
        proc.wait()
        raise
    if ogolne:
        raise tp.BladPomocnika('; '.join(ogolne))
    for _, _, _, sc in zadania:  # bez komunikatu i bez pliku
        if sc not in bledy and not os.path.isfile(sc):
            bledy[sc] = 'raport nie powstał'
    return bledy


def zapisz_xlsx(wyniki, bledy_xls, postep):
    """Excel: zestawienia i raporty .xlsx. postep(nr) -> False przerywa.
    Zwraca {cel: błąd}."""
    bledy = {}
    with tp.Excel() as xl:
        for nr, w in enumerate(wyniki):
            if postep(nr) is False:
                raise Przerwano()
            if any(sc in bledy_xls for _, sc in w['zrodla']):
                continue
            try:
                if w['raport'] == tp.ZESTAWIENIE:
                    xl.zloz(w['zrodla'], w['cel'])
                else:
                    xl.zapisz_xlsx(w['zrodla'][0][1], w['cel'])
            except Exception as e:
                bledy[w['cel']] = str(e)
                _log(f"{w['cel']}: {e}", Qgis.Warning)
    return bledy


def _pokaz_koniec(iface, tekst, raport, folder):
    msg = QMessageBox(iface.mainWindow())
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(_TYTUL)
    msg.setText(tekst)
    msg.addButton('Zamknij', QMessageBox.RejectRole)
    pokaz = msg.addButton('Zamknij i pokaż raport', QMessageBox.AcceptRole)
    otworz = msg.addButton('Otwórz folder', QMessageBox.ActionRole)
    msg.exec_()
    if platform.system()[:3] != 'Win':
        return
    if msg.clickedButton() == pokaz:
        os.startfile(raport)
    elif msg.clickedButton() == otworz:
        os.startfile(folder)


def uruchom(iface):  # noqa
    dlg = RaportyDialog(iface.mainWindow())
    if dlg.exec_() != QDialog.Accepted:
        return
    baza, taksator = dlg.baza(), dlg.taksator
    raporty, obreby = dlg.raporty.wybrane(), dlg.lista_obrebow.wybrane()
    folder = tp.folder_raportow(baza)

    tmp = tempfile.mkdtemp(prefix='lasr_tpu_')
    wyniki, zadania = tp.zaplanuj(baza, raporty, obreby,
                                  os.path.join(tmp, 'xls'))
    jest = tp.istniejace(wyniki)
    if jest:
        odp = QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            f'W folderze\n{folder}\njest już {len(jest)} z {len(wyniki)} '
            'plików raportów - zostaną zastąpione.\n\nKontynuować?',
            QMessageBox.Yes | QMessageBox.Abort, QMessageBox.Abort)
        if odp != QMessageBox.Yes:
            shutil.rmtree(tmp, ignore_errors=True)
            return

    start = time.time()
    uwagi = []
    powt = tp.powtorzone_obreby(obreby)
    if powt:
        uwagi.append('UWAGA: numery obrębów w kilku gminach bazy (Taksator '
                     'wybiera raport po samym numerze obrębu - sprawdź '
                     'wyniki): ' + ', '.join(powt))
    pd = _postep_okno(iface)

    def etap(tekst, wartosc):
        pd.setLabelText(tekst)
        pd.setValue(wartosc)
        QApplication.processEvents()
        if pd.wasCanceled():
            raise Przerwano()

    bledy_xls, bledy_excel = {}, {}
    try:
        etap('Przygotowanie pomocnika Taksatora...', 0)
        exe = tp.kompiluj_pomocnika()
        etap('Kopia bazy...', 1)
        kopia = kopia_bez_hasla(baza, tmp)
        etap('Sprawdzanie wersji bazy...', 2)
        wersja, wymagana = tp.wersja_bazy(exe, taksator, kopia)
        if wersja > wymagana:
            raise tp.BladPomocnika(
                f'baza ma nowszą strukturę ({wersja}) niż obsługuje '
                f'zainstalowany Taksator ({wymagana}) - zaktualizuj Taksatora')
        if wersja < wymagana:
            etap(f'Aktualizacja struktury kopii bazy {wersja} -> '
                 f'{wymagana}...', 3)
            przed, po = tp.aktualizuj_baze(exe, taksator, kopia)
            uwagi.append(f'Struktura bazy {przed} starsza niż wymaga '
                         f'Taksator ({wymagana}) - zaktualizowana na '
                         f'tymczasowej kopii ({przed} -> {po}); baza '
                         'źródłowa bez zmian.')
            if po < wymagana:
                raise tp.BladPomocnika(
                    f'nie udało się zaktualizować kopii bazy ({po})')
        ile = max(len(zadania), 1)

        def postep_raportow(zrobione):
            pd.setLabelText(f'Raporty Taksatora: {zrobione}/{len(zadania)}')
            pd.setValue(5 + int(60 * zrobione / ile))
            QApplication.processEvents()
            return not pd.wasCanceled()
        bledy_xls = generuj_xls(exe, taksator, kopia, zadania, tmp,
                                postep_raportow)

        def postep_excel(nr):
            w = wyniki[nr]
            pd.setLabelText(f"Excel: {tp.FOLDERY[w['raport']]} "
                            f"{os.path.basename(w['cel'])} "
                            f'({nr + 1}/{len(wyniki)})')
            pd.setValue(65 + int(35 * nr / max(len(wyniki), 1)))
            QApplication.processEvents()
            return not pd.wasCanceled()
        bledy_excel = zapisz_xlsx(wyniki, bledy_xls, postep_excel)
    except Przerwano:
        pd.close()
        shutil.rmtree(tmp, ignore_errors=True)
        iface.messageBar().pushMessage(
            _TYTUL, 'Przerwano - pliki zapisane do tej pory zostały w '
            f'{folder}.', Qgis.Warning, 0)
        return
    except Exception as e:
        pd.close()
        shutil.rmtree(tmp, ignore_errors=True)
        _log(f'błąd: {e}', Qgis.Critical)
        QMessageBox.critical(iface.mainWindow(), _TYTUL, f'Błąd:\n{e}')
        return
    pd.close()
    shutil.rmtree(tmp, ignore_errors=True)

    ok = sum(1 for w in wyniki if os.path.isfile(w['cel']) and
             w['cel'] not in bledy_excel and
             not any(sc in bledy_xls for _, sc in w['zrodla']))
    czas = time.time() - start
    tekst = (f'Baza: {baza}\nTaksator PU: {taksator}\n'
             f'Obręby: {len(obreby)}, raporty: ' +
             ', '.join(tp.NAZWY[r] if r == tp.ZESTAWIENIE else str(r)
                       for r in raporty) +
             f'\nUtworzono plików: {ok}/{len(wyniki)}, czas: '
             f'{int(czas // 60)} min {int(czas % 60)} s\n\n' +
             tp.opis_wynikow(wyniki, bledy_xls, bledy_excel))
    if uwagi:
        tekst += '\nUWAGI\n' + '\n'.join(f'  {u}' for u in uwagi) + '\n'
    os.makedirs(folder, exist_ok=True)
    raport = os.path.join(folder, f'raport_tpu_{znacznik()}.txt')
    with open(raport, 'w', encoding='utf-8') as f:
        f.write(tekst)
    podsumowanie = f'Utworzono plików: {ok}/{len(wyniki)}.\nFolder: {folder}'
    if ok < len(wyniki):
        podsumowanie += (f'\n\nBŁĘDY: {len(wyniki) - ok} - szczegóły '
                         'w raporcie.')
    _pokaz_koniec(iface, podsumowanie, raport, folder)
