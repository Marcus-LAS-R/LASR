# -*- coding: utf-8 -*-
"""Utwórz płyty na oddanie (menu Generuj).

Wskazuje się folder oddania. Dla zaznaczonych folderów gmin (z SHP/WYDZ.shp)
skrypt ustala obręby i gminy (jak Przygotuj na wyłożenia) i tworzy w
<oddanie>/_Plyty_na_oddanie/ wybrane płyty (bez pakowania):
  - Calosciowa - [SULMN] + dla każdej gminy Bazy_danych, SHP, Operaty,
    Operaty_BDO, Mapy, Atlasy, [Raporty],
  - Gm.<Nazwa> - to samo dla jednej gminy (miasto i obszar wiejski razem),
  - PGLLP      - [SULMN] + Operaty_BDO, Mapy, Atlasy.
Co trafia na płyty - osobna lista dla każdego rodzaju płyty (zakładki,
pp.ZAWARTOSC; domyślne pp.DOMYSLNE_PLYT: Całościowa i gminy - wszystko poza
SULMN, Raporty, docx i plikami ogólnymi, PGLLP - operaty BDO, mapy,
atlasy). Mapy/atlasy z PLOTOWANIE folderu gminy i z _MAPY/PLOTOWANIE
(luzem albo w folderze gminy, także atlas/legenda całej gminy); SHP
i OGOLNE z _MAPY, a gdy brak - z _MAPY/_ROBOCZE. Bazy i SHP
przygotowywane raz dla sumy zaznaczeń.
Bazy: najnowsza .mdb z folderu gminy, dwie kopie bez kwerend
(<część>.mdb i <część>_anonim.mdb - zanonimizowana jak Anonimizuj bazy TPU),
skompaktowane. SHP: warstwy z _MAPY/<gmina>/<obręby>/SHP połączone
silnikiem Połącz warstwy SHP (EPSG:2180, bez duplikatów), opcjonalnie pliki
ogólne (_MAPY/<gmina>/OGOLNE -> SHP/OGOLNE). Raporty (opcja) - raporty
TPU z <folder gminy>/Raporty_TPU (Generuj › Zestawienia raportów TPU) bez
danych osobowych: bez raportów 3, 5, 8, Zestawienie raportów bez ich
arkuszy (tpu_raporty_pliki.raporty_na_plyte). Płyta większa niż 4,7 GB -
ostrzeżenie.

Plan, pliki, kopiowanie - plyty_na_oddanie_pliki.py. Źródła nie są
zmieniane.
"""
import os
import platform
import shutil

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QProgressDialog, QPushButton, QRadioButton, QTabWidget,
    QVBoxLayout, QWidget,
)
from qgis.core import Qgis, QgsMessageLog

from . import plyty_na_oddanie_pliki as pp
from . import przygotuj_na_wylozenia_pliki as pw
from .baza_anonimizuj import anonimizuj_baze
from .baza_wrapper import Baza
from .przyciski import QDialogButtonBox, QMessageBox
from .przygotuj_na_wylozenia import obreby_folderu
from .rozdziel_upul_isl.core.rozdziel import kompaktuj
from .shp_polacz_warstwy import polacz_warstwe
from .spakuj_do_opiniowania import foldery_kandydaci
from .znacznik_czasu import znacznik

_TYTUL = 'Utwórz płyty na oddanie'


def _log(tekst, poziom=Qgis.Info):
    QgsMessageLog.logMessage(f'{_TYTUL}: {tekst}', 'Las-R', poziom)


# ----------------------------------------------------------------- okna

class _ListaZawartosci(QWidget):
    """Lista "co wgrać" jednego rodzaju płyty + Wszystko/Nic/Domyślnie."""

    def __init__(self, rodzaj, parent=None):
        super().__init__(parent)
        self.rodzaj = rodzaj
        self.domyslne = pp.DOMYSLNE_PLYT[rodzaj]
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.lw = QListWidget()
        self.pozycje = {}
        for klucz, etykieta in pp.ZAWARTOSC:
            it = QListWidgetItem(etykieta)
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if self.domyslne[klucz]
                             else Qt.Unchecked)
            it.setData(Qt.UserRole, klucz)
            self.lw.addItem(it)
            self.pozycje[klucz] = it
        self.lw.setMinimumHeight(
            self.lw.sizeHintForRow(0) * len(pp.ZAWARTOSC) + 6)
        lay.addWidget(self.lw)
        h = QHBoxLayout()
        for tekst, stan in (('Wszystko', True), ('Nic', False),
                            ('Domyślnie', None)):
            b = QPushButton(tekst)
            b.clicked.connect(lambda _, s=stan: self.ustaw(s))
            h.addWidget(b)
        h.addStretch()
        lay.addLayout(h)

    def ustaw(self, stan):
        """Wszystko (True) / Nic (False) / Domyślnie (None) - aktywne
        pozycje."""
        for klucz, it in self.pozycje.items():
            if it.flags() & Qt.ItemIsEnabled:
                zazn = self.domyslne[klucz] if stan is None else stan
                it.setCheckState(Qt.Checked if zazn else Qt.Unchecked)

    def wlacz(self, klucz, wlacz):
        """Pozycja nieaktywna - odznaczona; po ponownym włączeniu jak
        domyślnie."""
        it = self.pozycje[klucz]
        byla = bool(it.flags() & Qt.ItemIsEnabled)
        self.lw.blockSignals(True)
        if wlacz:
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            if not byla:
                it.setCheckState(Qt.Checked if self.domyslne[klucz]
                                 else Qt.Unchecked)
        else:
            it.setFlags(Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Unchecked)
        self.lw.blockSignals(False)

    def zaznaczona(self, klucz):
        it = self.pozycje[klucz]
        return bool(it.flags() & Qt.ItemIsEnabled) and \
            it.checkState() == Qt.Checked

    def opcje(self):
        return {k: self.zaznaczona(k) for k in self.pozycje}


class PlytyDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL)
        self.resize(660, 860)
        self._docelowy_reczny = False

        uklad = QVBoxLayout(self)
        siatka = QGridLayout()
        siatka.addWidget(QLabel('Folder oddania:'), 0, 0)
        self.le_obiekt = QLineEdit()
        siatka.addWidget(self.le_obiekt, 0, 1)
        b = QPushButton('Wskaż...')
        b.clicked.connect(self._wskaz_obiekt)
        siatka.addWidget(b, 0, 2)
        siatka.setColumnStretch(1, 1)
        uklad.addLayout(siatka)

        uklad.addWidget(QLabel('Foldery gmin:'))
        self.lw_foldery = QListWidget()
        uklad.addWidget(self.lw_foldery, 1)
        h = QHBoxLayout()
        for tekst, stan in (('Zaznacz wszystkie', Qt.Checked),
                            ('Odznacz wszystkie', Qt.Unchecked)):
            b = QPushButton(tekst)
            b.clicked.connect(lambda _, s=stan: self._zaznacz(s))
            h.addWidget(b)
        h.addStretch()
        uklad.addLayout(h)

        box = QGroupBox('Płyty do utworzenia i co na nie wgrać')
        lay = QVBoxLayout(box)
        h = QHBoxLayout()
        self.cb_plyty = {p: QCheckBox(pp.ETYKIETY_PLYT[p]) for p in pp.PLYTY}
        opisy = {
            pp.CALOSC: 'jedna płyta ze wszystkimi gminami',
            pp.GMINY: 'osobna płyta dla każdej gminy (miasto i obszar '
                      'wiejski razem)',
            pp.PGLLP: 'jedna płyta dla PGL LP',
        }
        for p, cb in self.cb_plyty.items():
            cb.setToolTip(opisy[p])
            h.addWidget(cb)
        h.addStretch()
        lay.addLayout(h)
        self.zakladki = QTabWidget()
        self.listy = {}
        for p in pp.PLYTY:
            lista = _ListaZawartosci(p)
            lista.lw.itemChanged.connect(self._odswiez_sulmn)
            self.listy[p] = lista
            self.zakladki.addTab(lista, pp.ETYKIETY_PLYT[p])
        lay.addWidget(self.zakladki)

        h = QHBoxLayout()
        self.lab_sulmn = QLabel('Plik SULMN:')
        h.addWidget(self.lab_sulmn)
        self.le_sulmn = QLineEdit()
        h.addWidget(self.le_sulmn, 1)
        self.btn_sulmn = QPushButton('Wskaż...')
        self.btn_sulmn.clicked.connect(self._wskaz_sulmn)
        h.addWidget(self.btn_sulmn)
        lay.addLayout(h)
        uklad.addWidget(box)

        box = QGroupBox('Wielkość nośnika')
        lay = QVBoxLayout(box)
        self.rb_limit = QRadioButton(
            f'Mniej niż {pp.gb(pp.LIMIT_DVD)} (DVD)')
        self.rb_bez_limitu = QRadioButton('Brak limitu')
        self.rb_limit.setChecked(True)
        lay.addWidget(self.rb_limit)
        lay.addWidget(self.rb_bez_limitu)
        uklad.addWidget(box)

        h = QHBoxLayout()
        h.addWidget(QLabel('Folder docelowy:'))
        self.le_docel = QLineEdit()
        h.addWidget(self.le_docel, 1)
        b = QPushButton('Wskaż...')
        b.clicked.connect(self._wskaz_docelowy)
        h.addWidget(b)
        uklad.addLayout(h)

        self.bb = QDialogButtonBox(QDialogButtonBox.Ok |
                                   QDialogButtonBox.Cancel)
        self.bb.button(QDialogButtonBox.Ok).setText('Dalej')
        self.bb.accepted.connect(self._akceptuj)
        self.bb.rejected.connect(self.reject)
        uklad.addWidget(self.bb)

        for p, cb in self.cb_plyty.items():
            cb.toggled.connect(self._odswiez_zakladki)
        self.cb_plyty[pp.CALOSC].setChecked(True)
        self.le_obiekt.editingFinished.connect(self._odswiez_foldery)
        self.le_docel.textEdited.connect(self._docelowy_edytowany)
        self.lw_foldery.itemChanged.connect(self._odswiez_rodzaje)
        self._odswiez_rodzaje()
        self._odswiez_zakladki()

    # --- wybór
    def _wskaz_obiekt(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder oddania', self.le_obiekt.text())
        if kat:
            self.le_obiekt.setText(os.path.normpath(kat))
            self._odswiez_foldery()

    def _wskaz_docelowy(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder docelowy',
            self.le_docel.text() or self.le_obiekt.text())
        if kat:
            self.le_docel.setText(os.path.normpath(kat))
            self._docelowy_reczny = True

    def _wskaz_sulmn(self):
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż plik SULMN',
            self.le_sulmn.text() or self.le_obiekt.text(),
            'Wszystkie pliki (*.*)')
        if sc:
            self.le_sulmn.setText(os.path.normpath(sc))

    def _docelowy_edytowany(self, _):
        self._docelowy_reczny = True

    def _zaznacz(self, stan):
        self.lw_foldery.blockSignals(True)
        for i in range(self.lw_foldery.count()):
            it = self.lw_foldery.item(i)
            if it.flags() & Qt.ItemIsEnabled:
                it.setCheckState(stan)
        self.lw_foldery.blockSignals(False)
        self._odswiez_rodzaje()

    def _odswiez_foldery(self):
        obiekt = self.le_obiekt.text().strip()
        if not self._docelowy_reczny and obiekt:
            self.le_docel.setText(os.path.join(obiekt, pp.FOLDER_WYNIKOWY))
        self.lw_foldery.blockSignals(True)
        self.lw_foldery.clear()
        for nazwa, sc, ma_wydz in foldery_kandydaci(obiekt):
            it = QListWidgetItem(
                nazwa if ma_wydz else f'{nazwa}  (brak SHP/WYDZ.shp)')
            it.setData(Qt.UserRole, sc)
            if ma_wydz:
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked)
            else:
                it.setFlags(Qt.NoItemFlags)
            self.lw_foldery.addItem(it)
        self.lw_foldery.blockSignals(False)
        self._odswiez_rodzaje()

    def wybrane_foldery(self):
        return [self.lw_foldery.item(i).data(Qt.UserRole)
                for i in range(self.lw_foldery.count())
                if self.lw_foldery.item(i).checkState() == Qt.Checked]

    def _odswiez_rodzaje(self, *_):
        """Mapy/atlasy do wyboru tylko, gdy są w zaznaczonych folderach."""
        dostepne = pp.dostepne_mapy(self.wybrane_foldery())
        for lista in self.listy.values():
            for rodzaj, klucz in ((pw.MAPY, 'mapy'), (pw.ATLASY, 'atlasy')):
                lista.wlacz(klucz, rodzaj in dostepne)
        self._odswiez_sulmn()

    def _odswiez_zakladki(self, *_):
        """Zakładka listy aktywna tylko dla zaznaczonej płyty; widoczna
        pierwsza aktywna."""
        for i, p in enumerate(pp.PLYTY):
            self.zakladki.setTabEnabled(i, self.cb_plyty[p].isChecked())
        if not self.cb_plyty[pp.PLYTY[self.zakladki.currentIndex()]] \
                .isChecked():
            for i, p in enumerate(pp.PLYTY):
                if self.cb_plyty[p].isChecked():
                    self.zakladki.setCurrentIndex(i)
                    break
        self._odswiez_sulmn()

    def _odswiez_sulmn(self, *_):
        """Ścieżka SULMN aktywna, gdy SULMN zaznaczony na liście którejś
        z wybranych płyt."""
        aktywny = any(self.listy[p].zaznaczona('sulmn')
                      for p in self.wybrane_plyty())
        for w in (self.lab_sulmn, self.le_sulmn, self.btn_sulmn):
            w.setEnabled(aktywny)

    def wybrane_plyty(self):
        return [p for p in pp.PLYTY if self.cb_plyty[p].isChecked()]

    def opcje_plyt(self):
        return {p: self.listy[p].opcje() for p in self.wybrane_plyty()}

    def limit(self):
        return pp.LIMIT_DVD if self.rb_limit.isChecked() else None

    def sulmn(self):
        if not any(o.get('sulmn') for o in self.opcje_plyt().values()):
            return None
        return self.le_sulmn.text().strip() or None

    def _akceptuj(self):
        if not os.path.isdir(self.le_obiekt.text().strip()):
            QMessageBox.warning(self, _TYTUL, 'Wskaż istniejący folder '
                                'oddania.')
            return
        if not self.wybrane_foldery():
            QMessageBox.warning(self, _TYTUL, 'Zaznacz co najmniej jeden '
                                'folder gminy.')
            return
        if not self.wybrane_plyty():
            QMessageBox.warning(self, _TYTUL, 'Zaznacz, jakie płyty '
                                'utworzyć.')
            return
        puste = [pp.ETYKIETY_PLYT[p] for p, o in self.opcje_plyt().items()
                 if not any(o.values())]
        if puste:
            QMessageBox.warning(self, _TYTUL, 'Nic nie jest zaznaczone do '
                                'wgrania na płytę: ' + ', '.join(puste))
            return
        sulmn = self.sulmn()
        if any(o.get('sulmn') for o in self.opcje_plyt().values()) and \
                not (sulmn and os.path.isfile(sulmn)):
            QMessageBox.warning(self, _TYTUL, 'Wskaż istniejący plik SULMN '
                                'albo odznacz go na listach płyt.')
            return
        if not self.le_docel.text().strip():
            QMessageBox.warning(self, _TYTUL, 'Wskaż folder docelowy.')
            return
        self.accept()


class PodgladDialog(QDialog):
    """Płyty -> gminy, braki, szacowane rozmiary przed utworzeniem."""

    def __init__(self, tekst, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL)
        self.resize(700, 600)
        uklad = QVBoxLayout(self)
        uklad.addWidget(QLabel('Sprawdź, co trafi na które płyty:'))
        pole = QPlainTextEdit(tekst)
        pole.setReadOnly(True)
        pole.setFont(QFont('Consolas', 9))
        uklad.addWidget(pole, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Utwórz płyty')
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        uklad.addWidget(bb)


def _postep_okno(iface):
    pd = QProgressDialog('', 'Przerwij', 0, 100, iface.mainWindow())
    pd.setWindowTitle(_TYTUL)
    pd.setWindowModality(Qt.WindowModal)
    pd.setMinimumDuration(0)
    pd.setValue(0)
    return pd


# ----------------------------------------------------------- przygotowanie

class _Pomin(Exception):
    pass


def _usun(sc):
    try:
        os.remove(sc)
    except OSError:
        pass


def przygotuj_bazy(cz, katalog, bledy, zwykla_tez=True, anonim_tez=True):
    """<katalog>/<część>.mdb (bez kwerend) i/lub <część>_anonim.mdb
    (zanonimizowana, bez kwerend) - skompaktowane (usunięte dane nie
    zostają w pliku)."""
    if not cz['baza'] or not (zwykla_tez or anonim_tez):
        return
    os.makedirs(katalog, exist_ok=True)
    zwykla = os.path.join(katalog, cz['nazwa'] + '.mdb')
    anonim = os.path.join(katalog, cz['nazwa'] + pp.PRZYROSTEK_ANONIM +
                          '.mdb')

    try:
        if not zwykla_tez:
            raise _Pomin()
        shutil.copy2(cz['baza'], zwykla)
        b = Baza(zwykla)
        if not b.polacz():
            raise RuntimeError('nie udało się połączyć z kopią bazy')
        try:
            b.usun_kwerendy()
        finally:
            b.zamknij()
        kompaktuj(zwykla)
    except _Pomin:
        pass
    except Exception as e:
        _usun(zwykla)
        bledy.append(f"{cz['nazwa']}: baza zwykła - {e}")
        _log(f"{cz['nazwa']}: baza zwykła - {e}", Qgis.Critical)

    if not anonim_tez:
        return
    try:
        shutil.copy2(cz['baza'], anonim)
        if not anonimizuj_baze(anonim, usun_kwerendy=True):
            raise RuntimeError('nie udało się połączyć z kopią bazy')
        kompaktuj(anonim)
    except Exception as e:
        # niezanonimizowana kopia nie może zostać pod nazwą _anonim
        _usun(anonim)
        bledy.append(f"{cz['nazwa']}: baza zanonimizowana - {e}")
        _log(f"{cz['nazwa']}: baza zanonimizowana - {e}", Qgis.Critical)


def przygotuj_shp(cz, katalog, bledy, uwagi):
    """Połączone warstwy obrębów części + OGOLNE w <katalog>/OGOLNE."""
    if not cz['shp'] and not cz['ogolne']:
        return
    os.makedirs(katalog, exist_ok=True)
    for nazwa, zrodla in sorted(cz['shp'].items()):
        try:
            wynik = polacz_warstwe(nazwa, zrodla, katalog,
                                   usun_duplikaty=True,
                                   szukaj_nakladan=False)
        except Exception as e:
            bledy.append(f"{cz['nazwa']}: SHP {nazwa} - {e}")
            continue
        if wynik is None:
            continue
        if wynik['blad_zapisu']:
            bledy.append(f"{cz['nazwa']}: SHP {nazwa} - "
                         f"{wynik['blad_zapisu']}")
        if wynik['duplikaty']:
            uwagi.append(f"{cz['nazwa']}: SHP {nazwa} - pominięto "
                         f"{wynik['duplikaty']} duplikatów geometrii")
        uwagi += [f"{cz['nazwa']}: {u}" for u in wynik['uwagi']]
    for p in cz['ogolne']:
        cel = os.path.join(katalog, pp.OGOLNE, os.path.basename(p))
        os.makedirs(os.path.dirname(cel), exist_ok=True)
        try:
            shutil.copy2(p, cel)
        except OSError as e:
            bledy.append(f'{p}: {e}')


# --------------------------------------------------------------- przebieg

def _zapytaj_o_podzial(iface, plan, duze, przyg, limit, uwagi):
    """Alarm o płytach większych niż limit: Tak - podziel po gminach,
    Nie - zostaw w całości, Anuluj - przerwij (None)."""
    lista = '\n'.join(f'  {n}: {pp.gb(r)}' for n, r in duze.items())
    odp = QMessageBox.warning(
        iface.mainWindow(), _TYTUL,
        f'Płyty większe niż {pp.gb(limit)} - nie zmieszczą się na DVD:\n\n'
        f'{lista}\n\nPodzielić je po gminach na części (_1, _2...)?\n\n'
        'Tak - podziel, Nie - zostaw w całości, Anuluj - przerwij.',
        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
        QMessageBox.Yes)
    if odp == QMessageBox.Cancel:
        return None
    if odp != QMessageBox.Yes:
        uwagi.append('Płyty większe niż limit zostawione w całości na '
                     'życzenie: ' + ', '.join(duze))
        return plan
    nowy = pp.podziel_plyty(plan, przyg, limit)
    nadal = pp.za_duze(nowy, przyg, limit)
    if nadal:
        uwagi.append('Po podziale nadal za duże (jedna gmina większa niż '
                     f'{pp.gb(limit)} - gminy się nie dzieli): ' +
                     ', '.join(nadal))
        QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            'Po podziale nadal większe niż limit (jedna gmina nie mieści się '
            'na płycie, gminy się nie dzieli):\n\n' +
            '\n'.join(f'  {n}: {pp.gb(r)}' for n, r in nadal.items()))
    return nowy


def zapisz_raport(folder, tekst):
    sciezka = os.path.join(folder, 'raport_plyty_%s.txt' % znacznik())
    with open(sciezka, 'w', encoding='utf-8') as f:
        f.write(tekst)
    return sciezka


def _pokaz_koniec(iface, tekst, raport):
    msg = QMessageBox(iface.mainWindow())
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(_TYTUL)
    msg.setText(tekst)
    msg.addButton('Zamknij', QMessageBox.RejectRole)
    pokaz = msg.addButton('Zamknij i pokaż raport', QMessageBox.AcceptRole)
    msg.exec_()
    if msg.clickedButton() == pokaz and platform.system()[:3] == 'Win':
        os.startfile(raport)


def uruchom(iface):  # noqa
    dlg = PlytyDialog(iface.mainWindow())
    if dlg.exec_() != QDialog.Accepted:
        return
    docel = dlg.le_docel.text().strip()
    plyty, sulmn, limit = dlg.wybrane_plyty(), dlg.sulmn(), dlg.limit()
    opcje_plyt = dlg.opcje_plyt()
    opcje = pp.suma_opcji(*opcje_plyt.values())  # pliki/bazy/SHP - raz

    # --- analiza: obręby -> gminy -> części
    pd = _postep_okno(iface)
    pd.setLabelText('Sprawdzanie obrębów...')

    def postep_analizy(etykieta, nr, ile):
        pd.setLabelText(f'{etykieta}: wydzielenie {nr}/{ile}')
        pd.setValue(min(99, int(100 * nr / max(ile, 1))))
        QApplication.processEvents()
        return not pd.wasCanceled()

    gminy, uwagi = {}, []
    for folder in dlg.wybrane_foldery():
        if not obreby_folderu(folder, gminy, uwagi, postep_analizy):
            pd.close()
            return
    if not gminy:
        pd.close()
        QMessageBox.warning(iface.mainWindow(), _TYTUL,
                            'Nie znaleziono żadnego obrębu w WYDZ.shp '
                            'zaznaczonych folderów.')
        return
    pd.setLabelText('Wyszukiwanie plików...')
    QApplication.processEvents()
    czesci = [pp.uzupelnij_czesc(c, opcje) for c in pp.czesci_z_gmin(gminy)]
    pd.close()

    plan = pp.zaplanuj(czesci, plyty, sulmn, opcje_plyt)
    opis = pp.opis_planu(plan, czesci, uwagi, limit=limit)
    if PodgladDialog(opis, iface.mainWindow()).exec_() != QDialog.Accepted:
        return

    istniejace = pp.istniejace_wyniki(docel, plan)
    if istniejace:
        odp = QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            f'W folderze\n{docel}\nsą już płyty, które zostaną zastąpione '
            f'(razem z zawartością):\n\n{chr(10).join(istniejace)}'
            '\n\nZastąpić je?',
            QMessageBox.Yes | QMessageBox.Abort, QMessageBox.Abort)
        if odp != QMessageBox.Yes:
            return
    try:
        os.makedirs(docel, exist_ok=True)
    except OSError as e:
        QMessageBox.warning(iface.mainWindow(), _TYTUL,
                            f'Nie udało się utworzyć folderu docelowego:\n{e}')
        return

    bledy, uwagi_przyg = [], []
    przyg = os.path.join(docel, pp.FOLDER_PRZYGOTOWANIA)
    pd = _postep_okno(iface)
    try:
        # --- bazy i SHP raz na część (używane na kilku płytach)
        if pp.potrzebne_przygotowanie(plan):
            shutil.rmtree(przyg, ignore_errors=True)
            for i, cz in enumerate(czesci):
                pd.setLabelText(f"Bazy i SHP: {cz['nazwa']}")
                pd.setValue(int(50 * i / max(len(czesci), 1)))
                QApplication.processEvents()
                if pd.wasCanceled():
                    raise pp.Przerwano()
                kat = os.path.join(przyg, cz['nazwa'])
                przygotuj_bazy(cz, os.path.join(kat, pp.BAZY), bledy,
                               opcje['bazy'], opcje['anonim'])
                QApplication.processEvents()
                przygotuj_shp(cz, os.path.join(kat, pp.SHP), bledy,
                              uwagi_przyg)

        # --- limit DVD: dokładny rozmiar (bazy i SHP już przygotowane)
        if limit:
            pd.setLabelText('Sprawdzanie wielkości płyt...')
            QApplication.processEvents()
            duze = pp.za_duze(plan, przyg, limit)
            if duze:
                plan = _zapytaj_o_podzial(iface, plan, duze, przyg, limit,
                                          uwagi_przyg)
                if plan is None:
                    raise pp.Przerwano()

        # --- kopiowanie płyt
        razem = max(sum(pp.szacuj_rozmiar(p) for p in plan), 1)
        zrobione = [0]
        for p in plan:
            def _p(bajty, nazwa=p['nazwa']):
                zrobione[0] += bajty
                pd.setLabelText(f'Kopiowanie: {nazwa}')
                pd.setValue(min(99, 50 + int(50 * zrobione[0] / razem)))
                QApplication.processEvents()
                return not pd.wasCanceled()
            bledy += pp.kopiuj_plyte(docel, p, przyg, _p)
    except pp.Przerwano:
        pd.close()
        pp.usun_tymczasowe(docel, plan)
        raport = zapisz_raport(docel, 'PRZERWANO - płyty z poprzedniego '
                               'przebiegu bez zmian.\n\nPlan:\n\n' + opis)
        iface.messageBar().pushMessage(
            _TYTUL, f'Przerwano, raport: {raport}', Qgis.Warning, 0)
        return
    except Exception as e:
        pd.close()
        pp.usun_tymczasowe(docel, plan)
        _log(f'błąd: {e}', Qgis.Critical)
        QMessageBox.critical(iface.mainWindow(), _TYTUL, f'Błąd:\n{e}')
        return
    pd.close()
    bledy += pp.podmien(docel, plan, istniejace)
    shutil.rmtree(przyg, ignore_errors=True)

    rozmiary = pp.rozmiary_plyt(docel, plan)
    tekst = pp.opis_planu(plan, czesci, uwagi + uwagi_przyg, rozmiary,
                          limit)
    if bledy:
        tekst += '\nBŁĘDY:\n' + '\n'.join(f'  {b}' for b in bledy) + '\n'
    raport = zapisz_raport(docel, tekst)

    duze = [n for n, r in rozmiary.items() if limit and r > limit]
    podsumowanie = (f'Utworzono płyty: {len(plan)}.\nFolder: {docel}\n\n' +
                    '\n'.join(f'{n}: {pp.gb(r)}' for n, r in rozmiary.items()))
    if duze:
        podsumowanie += (f'\n\nUWAGA: większe niż {pp.gb(limit)} '
                         '(nie zmieszczą się na DVD): ' + ', '.join(duze))
    if bledy:
        podsumowanie += f'\n\nBŁĘDY: {len(bledy)} - szczegóły w raporcie.'
    _pokaz_koniec(iface, podsumowanie, raport)
