"""Podmień kwerendy w bazach.

W każdej bazie .mdb bezpośrednio we wskazanym folderze - opcjonalnie
także w jego podfolderach, jeden poziom niżej (pomijane jak w Połącz bazy:
Archiwum, Kopie_manipulacyjne, foldery od '_') - bez *_BDO i bez samej
bazy źródłowej, usuwa wszystkie kwerendy poza siedmioma chronionymi
(baza_wrapper.KWERENDY_CHRONIONE - zostają nietknięte, brakujące nie są
dogrywane) i wgrywa kwerendy z bazy źródłowej (też bez chronionych).
Tabele F_TABLICA i F_TABLICA_ROZSZERZONA są kopiowane ze źródła (w bazie
docelowej zastępowane); gdy źródło ich nie ma - w docelowej bez zmian.

Kwerendy tymczasowe Accessa (nazwy od '~', np. źródła formularzy) są
pomijane po obu stronach. Kwerendy odwołujące się do innych kwerend -
wgrywane w kilku przebiegach, aż wszystkie wejdą albo przebieg nic nie
doda. Kwerenda, której DAO nie przyjmuje (np. __V6 z TPU - alias dłuższy
niż 64 znaki), zostaje w starej wersji - uwaga w raporcie. Jet przy
zapisie normalizuje SQL (kolejność warunków JOIN, AND), treść bez zmian.
Przed zmianą kopia bazy w Kopie_manipulacyjne; błąd tabel/usuwania ->
baza przywracana z kopii (DAO nie ma transakcji na obiektach). Raport
w <folder>\\Raporty.
"""
import os
import glob
import shutil
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
    QGridLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
)
from qgis.core import Qgis, QgsMessageLog

from .baza_wrapper import KWERENDY_CHRONIONE, baza_zajeta, pokaz_blokade_bazy
from .baza_polacz_wyszukaj import czy_bdo, pomin_folder
from .kopie_manipulacyjne import zrob_kopie_manipulacyjna
from .pw import PasekPostepu
from .waypointy import katalog_raportow

_TYTUL = 'Podmień kwerendy w bazach'
_LOG = 'Las-R'
TABELE_ZE_ZRODLA = ('F_TABLICA', 'F_TABLICA_ROZSZERZONA')


def _dao():
    import win32com.client
    # dynamic.Dispatch zamiast Dispatch - omija nieaktualny cache gen_py
    # (patrz Baza.usun_kwerendy)
    return win32com.client.dynamic.Dispatch('DAO.DBEngine.120')


def _do_podmiany(nazwa):
    return nazwa not in KWERENDY_CHRONIONE and not nazwa.startswith('~')


def _tabele(db):
    return {t.Name.upper(): t.Name for t in db.TableDefs}


def odczytaj_zrodlo(sc):
    """([(nazwa, sql)] kwerend do wgrania, [nazwy tabel z TABELE_ZE_ZRODLA
    obecnych w źródle])."""
    db = _dao().OpenDatabase(sc, False, True)  # tylko odczyt
    try:
        kwerendy = [(q.Name, q.SQL) for q in db.QueryDefs
                    if _do_podmiany(q.Name)]
        tabele = _tabele(db)
        return kwerendy, [t for t in TABELE_ZE_ZRODLA if t.upper() in tabele]
    finally:
        db.Close()


def policz_kwerendy(sc):
    db = _dao().OpenDatabase(sc, False, True)
    try:
        return sum(1 for q in db.QueryDefs if _do_podmiany(q.Name))
    finally:
        db.Close()


def podmien(sc, sc_zrodla, kwerendy, tabele):
    """Podmiana w jednej bazie (bez kopii - robi ją wywołujący). Zwraca
    dict: usuniete, wgrane, tabele, bledy [opis] (krytyczne - wywołujący
    przywraca bazę z kopii), uwagi [opis] (kwerenda ze źródła, której DAO
    nie przyjmuje, np. alias > 64 znaki - zostaje stara wersja albo brak).

    Kwerenda istniejąca w bazie jest najpierw przemianowywana na nazwę
    tymczasową, a usuwana dopiero po udanym utworzeniu nowej - przy
    niepowodzeniu wraca stara wersja."""
    wynik = {'usuniete': 0, 'wgrane': 0, 'tabele': [], 'bledy': [],
             'uwagi': []}
    db = _dao().OpenDatabase(sc)
    try:
        # tabele najpierw - kwerendy mogą z nich korzystać
        istniejace = _tabele(db)
        zrodlo_sql = sc_zrodla.replace("'", "''")
        for t in tabele:
            try:
                if t.upper() in istniejace:
                    db.Execute('DROP TABLE [%s]' % istniejace[t.upper()])
                db.Execute("SELECT * INTO [%s] FROM [%s] IN '%s'" % (
                    t, t, zrodlo_sql))
                wynik['tabele'].append(t)
            except Exception as e:
                wynik['bledy'].append('tabela %s: %s' % (t, e))
        if wynik['bledy']:
            return wynik

        w_bazie = {q.Name.upper(): q.Name for q in db.QueryDefs
                   if _do_podmiany(q.Name)}
        ze_zrodla = {n.upper() for n, _ in kwerendy}

        # kwerendy spoza źródła - usuwane od razu
        for klucz, nazwa in list(w_bazie.items()):
            if klucz in ze_zrodla:
                continue
            try:
                db.QueryDefs.Delete(nazwa)
                wynik['usuniete'] += 1
            except Exception as e:
                wynik['bledy'].append('usuwanie kwerendy %s: %s' % (nazwa, e))
        if wynik['bledy']:
            return wynik

        # te same nazwy - stara wersja odstawiona pod nazwę tymczasową
        stare = {}
        for i, (nazwa, _sql) in enumerate(kwerendy):
            if nazwa.upper() in w_bazie:
                tymcz = '~LASR_stara_%d' % i
                try:
                    db.QueryDefs(w_bazie[nazwa.upper()]).Name = tymcz
                except Exception as e:
                    wynik['bledy'].append('przemianowanie kwerendy %s: %s' % (
                        nazwa, e))
                    return wynik
                stare[nazwa] = tymcz

        oczekujace = list(kwerendy)
        ostatnie = {}
        while oczekujace:
            nastepne = []
            for nazwa, sql in oczekujace:
                try:
                    db.CreateQueryDef(nazwa, sql)
                    wynik['wgrane'] += 1
                    if nazwa in stare:
                        db.QueryDefs.Delete(stare.pop(nazwa))
                        wynik['usuniete'] += 1
                except Exception as e:
                    ostatnie[nazwa] = _opis_bledu(e)
                    nastepne.append((nazwa, sql))
            if len(nastepne) == len(oczekujace):
                break
            oczekujace = nastepne

        for nazwa, _sql in oczekujace:
            if nazwa in stare:
                try:
                    db.QueryDefs(stare.pop(nazwa)).Name = nazwa
                    los = 'zostaje stara wersja'
                except Exception as e:
                    wynik['bledy'].append(
                        'przywrócenie starej kwerendy %s: %s' % (nazwa, e))
                    continue
            else:
                los = 'w bazie jej nie będzie'
            wynik['uwagi'].append('kwerenda %s nie wgrana (%s) - %s' % (
                nazwa, ostatnie.get(nazwa, ''), los))
    finally:
        db.Close()
    return wynik


def _opis_bledu(e):
    """Czytelny opis błędu DAO/COM (sam komunikat Jet, jeśli jest)."""
    try:
        return str(e.args[2][2])
    except Exception:
        return str(e)


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle(_TYTUL)
        self.setMinimumWidth(620)
        lay = QGridLayout(self)
        lay.addWidget(QLabel('Folder z bazami docelowymi (bez *_BDO):'),
                      0, 0, 1, 2)
        self.le_folder = QLineEdit()
        lay.addWidget(self.le_folder, 1, 0)
        b = QPushButton('Przeglądaj...')
        b.clicked.connect(self._folder)
        lay.addWidget(b, 1, 1)
        self.cb_podfoldery = QCheckBox(
            'Także bazy w podfolderach (jeden poziom niżej, np. folder '
            'obrębu/gminy)')
        self.cb_podfoldery.setToolTip(
            'Pomijane foldery: Archiwum, Kopie_manipulacyjne, kopie, '
            'zaczynające się od "_" (jak w Połącz bazy TPU).')
        lay.addWidget(self.cb_podfoldery, 2, 0, 1, 2)
        lay.addWidget(QLabel(
            'Baza źródłowa kwerend (oraz F_TABLICA, F_TABLICA_ROZSZERZONA):'),
            3, 0, 1, 2)
        self.le_zrodlo = QLineEdit()
        lay.addWidget(self.le_zrodlo, 4, 0)
        b = QPushButton('Przeglądaj...')
        b.clicked.connect(self._zrodlo)
        lay.addWidget(b, 4, 1)
        uw = QLabel(
            'Kwerendy chronione (' + ', '.join(sorted(KWERENDY_CHRONIONE)) +
            ') pozostają w bazach nietknięte.')
        uw.setWordWrap(True)
        lay.addWidget(uw, 5, 0, 1, 2)
        self.przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.przyciski.button(QDialogButtonBox.Ok).setText('Dalej')
        self.przyciski.button(QDialogButtonBox.Cancel).setText('Anuluj')
        self.przyciski.accepted.connect(self.accept)
        self.przyciski.rejected.connect(self.reject)
        lay.addWidget(self.przyciski, 6, 0, 1, 2)
        self.le_folder.textChanged.connect(self._ok)
        self.le_zrodlo.textChanged.connect(self._ok)
        self._ok()

    def _folder(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Folder z bazami docelowymi', self.folder())
        if sc:
            self.le_folder.setText(os.path.normpath(sc))

    def _zrodlo(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Baza źródłowa kwerend', self.folder(),
            'Bazy Access (*.mdb)')[0]
        if sc:
            self.le_zrodlo.setText(os.path.normpath(sc))

    def _ok(self, *_):
        self.przyciski.button(QDialogButtonBox.Ok).setEnabled(
            bool(self.folder()) and bool(self.zrodlo()))

    def folder(self):
        return self.le_folder.text().strip().strip('"')

    def zrodlo(self):
        return self.le_zrodlo.text().strip().strip('"')

    def podfoldery(self):
        return self.cb_podfoldery.isChecked()


def _blad(iface, tekst):
    iface.messageBar().clearWidgets()
    iface.messageBar().pushMessage('BŁĄD', tekst, Qgis.Critical, 0)


def _ta_sama(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(os.path.abspath(a)) == \
            os.path.normcase(os.path.abspath(b))


def bazy_do_podmiany(folder, zrodlo, podfoldery=False):
    """Bazy .mdb w folderze (i w podfolderach jeden poziom niżej, poza
    pomijanymi), bez *_BDO i bez bazy źródłowej."""
    katalogi = [folder]
    if podfoldery:
        katalogi += sorted(
            os.path.join(folder, n) for n in os.listdir(folder)
            if os.path.isdir(os.path.join(folder, n)) and not pomin_folder(n))
    return [sc for k in katalogi
            for sc in sorted(glob.glob(os.path.join(k, '*.mdb')))
            if not czy_bdo(sc) and not _ta_sama(sc, zrodlo)]


def uruchom(iface):
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return
    folder, zrodlo = dlg.folder(), dlg.zrodlo()
    if not os.path.isdir(folder):
        return _blad(iface, 'Folder nie istnieje: ' + folder)
    if not os.path.isfile(zrodlo):
        return _blad(iface, 'Baza źródłowa nie istnieje: ' + zrodlo)

    bazy = bazy_do_podmiany(folder, zrodlo, dlg.podfoldery())
    if not bazy:
        return _blad(iface, 'W folderze%s nie ma baz do podmiany (pomijane '
                            '*_BDO i baza źródłowa).' % (
                                ' ani w podfolderach' if dlg.podfoldery()
                                else ''))
    for sc in [zrodlo] + bazy:
        if baza_zajeta(sc):
            pokaz_blokade_bazy(sc)
            return

    try:
        kwerendy, tabele = odczytaj_zrodlo(zrodlo)
        do_usuniecia = {sc: policz_kwerendy(sc) for sc in bazy}
    except Exception as e:
        return _blad(iface, 'Błąd odczytu kwerend (DAO): ' + str(e))
    if not kwerendy:
        return _blad(iface, 'Baza źródłowa nie ma kwerend poza chronionymi - '
                            'przerwano, nic nie zmieniono.')

    tekst = (
        'Baz do podmiany: %d (folder: %s).\n\n'
        'Z każdej zostaną TRWALE USUNIĘTE wszystkie kwerendy poza '
        'chronionymi - łącznie %d.\n'
        'Zostaną wgrane kwerendy z bazy źródłowej: %d w każdej bazie.\n'
        'Tabele ze źródła (zastąpią istniejące): %s.\n\n'
        'Przed zmianą każda baza zostanie skopiowana do '
        'Kopie_manipulacyjne.\n\nKontynuować?' % (
            len(bazy), folder, sum(do_usuniecia.values()), len(kwerendy),
            ', '.join(tabele) or 'brak w źródle - bez zmian'))
    msg = QMessageBox(QMessageBox.Warning, _TYTUL, tekst,
                      QMessageBox.Yes | QMessageBox.No, iface.mainWindow())
    msg.setDefaultButton(QMessageBox.No)
    msg.setDetailedText('Bazy (kwerend do usunięcia):\n' + '\n'.join(
        '  %s (%d)' % (os.path.relpath(sc, folder), n)
        for sc, n in do_usuniecia.items()))
    if msg.exec_() != QMessageBox.Yes:
        return

    postep = PasekPostepu(iface).stworz_pasek(_TYTUL, 0, len(bazy))
    wyniki = []
    for i, sc in enumerate(bazy):
        postep.setValue(i)
        QApplication.processEvents()
        kopia_kat = zrob_kopie_manipulacyjna(sc, [], 'podmien_kwerendy')
        if kopia_kat is None:
            wyniki.append((sc, None, 'nie udało się zrobić kopii - baza '
                                     'pominięta, bez zmian'))
            continue
        kopia = os.path.join(kopia_kat, os.path.basename(sc))
        try:
            w = podmien(sc, zrodlo, kwerendy, tabele)
        except Exception as e:
            w = {'usuniete': 0, 'wgrane': 0, 'tabele': [], 'uwagi': [],
                 'bledy': ['%s: %s' % (type(e).__name__, e)]}
        uwaga = ''
        if w['bledy']:
            try:
                shutil.copyfile(kopia, sc)
                uwaga = 'BŁĘDY - baza przywrócona z kopii, bez zmian'
            except Exception as e:
                uwaga = ('BŁĘDY i NIE UDAŁO SIĘ PRZYWRÓCIĆ kopii (%s) - '
                         'przywróć ręcznie z %s' % (e, kopia))
        wyniki.append((sc, w, uwaga))
    postep.setValue(len(bazy))

    rap = _raport(folder, zrodlo, kwerendy, tabele, wyniki)
    ok = sum(1 for _, w, u in wyniki if w is not None and not u)
    z_uwagami = sum(1 for _, w, u in wyniki
                    if w is not None and not u and w['uwagi'])
    iface.messageBar().clearWidgets()
    iface.messageBar().pushMessage(
        _TYTUL, 'Podmieniono kwerendy w %d z %d baz%s. Raport: %s' % (
            ok, len(bazy), (' (z uwagami: %d)' % z_uwagami
                            if z_uwagami else ''), rap),
        Qgis.Success if ok == len(bazy) and not z_uwagami else Qgis.Warning,
        0)


def _raport(folder, zrodlo, kwerendy, tabele, wyniki):
    czas = datetime.now().strftime('%Y%m%dT%H%M%S')
    sc = os.path.join(katalog_raportow(folder),
                      'raport_podmien_kwerendy_' + czas + '.txt')
    w = ['---- ' + _TYTUL.upper() + ' ----', '',
         'Folder: ' + folder, 'Baza źródłowa: ' + zrodlo,
         'Kwerend ze źródła: %d' % len(kwerendy),
         'Tabele ze źródła: ' + (', '.join(tabele) or 'brak'),
         'Chronione (nietknięte): ' + ', '.join(sorted(KWERENDY_CHRONIONE)),
         '']
    for baza, wyn, uwaga in wyniki:
        w.append('=' * 70)
        w.append(baza)
        if wyn is not None:
            w.append('  usunięto: %d, wgrano: %d / %d, tabele: %s' % (
                wyn['usuniete'], wyn['wgrane'], len(kwerendy),
                ', '.join(wyn['tabele']) or '-'))
            w.extend('  !!! ' + b for b in wyn['bledy'])
            w.extend('  uwaga: ' + u for u in wyn['uwagi'])
        if uwaga:
            w.append('  >>> ' + uwaga)
    with open(sc, 'w', encoding='utf-8') as f:
        f.write('\n'.join(w) + '\n')
    QgsMessageLog.logMessage(_TYTUL + ' - raport: ' + sc, _LOG, Qgis.Info)
    return sc
