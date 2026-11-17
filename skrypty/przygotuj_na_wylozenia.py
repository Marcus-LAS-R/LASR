# -*- coding: utf-8 -*-
"""Przygotuj na wyłożenia (menu Generuj).

Wskazuje się folder obiektu. Dla każdego zaznaczonego folderu gminy/obrębu
z SHP/WYDZ.shp skrypt ustala obręby (MUNICIP/COMMUNITY albo ADR_LES),
grupuje je po gminach (TERYT z SHP/GMIN.shp albo z nazwy folderu - miasto
i obszar wiejski razem) i kopiuje (bez pakowania) do
<docelowy>/pUPUL_<Nazwa_gminy>/ podfoldery Mapy, Atlasy, Operaty,
Operaty_BDO. Folder gminy ma mniej niż 490 MB - większa gmina dzielona
po obrębach na pUPUL_<Nazwa>_1, _2...

Pliki i kopiowanie - przygotuj_na_wylozenia_pliki.py.
"""
import os
import platform
import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QProgressDialog, QPushButton, QVBoxLayout,
)
from qgis.core import Qgis, QgsFeatureRequest

from . import przygotuj_na_wylozenia_pliki as pw
from .przyciski import QDialogButtonBox, QMessageBox
from .spakuj_do_opiniowania import (
    _nazwy_obrebow, _pole, _tekst, _warstwa, _sciezka_wydz,
    foldery_kandydaci, numery_obrebu,
)
from .znacznik_czasu import znacznik

_TYTUL = 'Przygotuj na wyłożenia'
_POLA_ID_GMINY = ('IDJEDNOSTK', 'JPT_KOD_JE', 'TERYT')
_POLA_NAZWY = ('NAZWAWLASN', 'JPT_NAZWA_', 'NAZWA', 'NAME')


def _gminy_z_shp(folder):
    """{municip: (teryt6, nazwa)} z SHP/GMIN.shp (id 301703_5 -> '035',
    '301703'); pod None (teryt6, nazwa), gdy gmina w warstwie jest jedna."""
    lyr = _warstwa(os.path.join(folder, 'SHP', 'GMIN.shp'))
    if lyr is None:
        return {}
    i_id, i_nazwa = _pole(lyr, _POLA_ID_GMINY), _pole(lyr, _POLA_NAZWY)
    wyn, wszystkie = {}, []
    zad = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
    for f in lyr.getFeatures(zad):
        nazwa = _tekst(f[i_nazwa]) if i_nazwa >= 0 else ''
        teryt = None
        if i_id >= 0:
            m = re.match(r'^(\d{4})(\d{2})_?(\d)', _tekst(f[i_id]))
            if m:
                teryt = m.group(1) + m.group(2)
                wyn[m.group(2) + m.group(3)] = (teryt, nazwa)
        wszystkie.append((teryt, nazwa))
    if len(wszystkie) == 1:
        wyn[None] = wszystkie[0]
    return wyn


def obreby_folderu(folder, gminy, uwagi, postep=None):
    """Dopisuje obręby folderu do gminy: {klucz gminy: {nazwa, obreby}}.
    Zwraca False, gdy przerwano."""
    etykieta = os.path.basename(os.path.normpath(folder))
    lyr = _warstwa(_sciezka_wydz(folder))
    if lyr is None:
        uwagi.append(f'{etykieta}: nie udało się wczytać SHP/WYDZ.shp - '
                     'folder pominięty')
        return True
    i_mun = lyr.fields().lookupField('MUNICIP')
    i_com = lyr.fields().lookupField('COMMUNITY')
    i_adr = lyr.fields().lookupField('ADR_LES')
    gm_shp, obr = _gminy_z_shp(folder), _nazwy_obrebow(folder)

    ile, bez_numeru, widziane = lyr.featureCount(), 0, set()
    zad = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
    for nr, f in enumerate(lyr.getFeatures(zad), 1):
        if postep and nr % 200 == 0 and postep(etykieta, nr, ile) is False:
            return False
        municip, community = numery_obrebu(
            f[i_mun] if i_mun >= 0 else None,
            f[i_com] if i_com >= 0 else None,
            f[i_adr] if i_adr >= 0 else None)
        if community is None:
            bez_numeru += 1
            continue
        if (municip, community) in widziane:
            continue
        widziane.add((municip, community))

        teryt, nazwa = gm_shp.get(municip) or (None, '')
        teryt = teryt or pw.teryt_z_folderu(etykieta, municip)
        if not nazwa and municip not in gm_shp and None in gm_shp:
            nazwa = gm_shp[None][1]
        klucz = teryt or (etykieta, municip[:2])
        g = gminy.setdefault(klucz, {'nazwa': '', 'obreby': []})
        if not g['nazwa']:
            g['nazwa'] = pw.nazwa_gminy(nazwa) or pw.nazwa_z_folderu(etykieta)
        g['obreby'].append({
            'folder': folder, 'nazwa_folderu': etykieta,
            'municip': municip, 'community': community,
            'nazwa_obrebu': obr.get(community, ''),
        })
    if bez_numeru:
        uwagi.append(f'{etykieta}: {bez_numeru} wydz. bez numeru obrębu '
                     '(puste MUNICIP/COMMUNITY i ADR_LES) - pominięte')
    return True


# ----------------------------------------------------------------- okna

class WylozeniaDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL)
        self.resize(600, 540)
        self._docelowy_reczny = False

        uklad = QVBoxLayout(self)
        siatka = QGridLayout()
        siatka.addWidget(QLabel('Folder obiektu:'), 0, 0)
        self.le_obiekt = QLineEdit()
        siatka.addWidget(self.le_obiekt, 0, 1)
        b = QPushButton('Wskaż...')
        b.clicked.connect(self._wskaz_obiekt)
        siatka.addWidget(b, 0, 2)
        siatka.setColumnStretch(1, 1)
        uklad.addLayout(siatka)

        uklad.addWidget(QLabel('Foldery gmin/obrębów:'))
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

        box = QGroupBox('Co skopiować')
        lay = QVBoxLayout(box)
        self.cb_rodzaje = {r: QCheckBox(pw.ETYKIETY[r]) for r in pw.RODZAJE}
        for cb in self.cb_rodzaje.values():
            lay.addWidget(cb)
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
        self.bb.button(QDialogButtonBox.Ok).setText('Przygotuj')
        self.bb.accepted.connect(self._akceptuj)
        self.bb.rejected.connect(self.reject)
        uklad.addWidget(self.bb)

        self.le_obiekt.editingFinished.connect(self._odswiez_foldery)
        self.le_docel.textEdited.connect(self._docelowy_edytowany)
        self.lw_foldery.itemChanged.connect(self._odswiez_rodzaje)
        self._odswiez_rodzaje()

    def _wskaz_obiekt(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder obiektu', self.le_obiekt.text())
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
            self.le_docel.setText(os.path.join(obiekt, pw.FOLDER_WYNIKOWY))
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

    def wybrane_rodzaje(self):
        return [r for r in pw.RODZAJE if self.cb_rodzaje[r].isChecked()]

    def _odswiez_rodzaje(self, *_):
        """Do wyboru tylko to, co jest w zaznaczonych folderach."""
        dostepne = pw.dostepne_rodzaje(self.wybrane_foldery())
        for rodzaj, cb in self.cb_rodzaje.items():
            jest = rodzaj in dostepne
            if jest and not cb.isEnabled():
                cb.setChecked(True)
            elif not jest:
                cb.setChecked(False)
            cb.setEnabled(jest)

    def _akceptuj(self):
        if not os.path.isdir(self.le_obiekt.text().strip()):
            QMessageBox.warning(self, _TYTUL, 'Wskaż istniejący folder '
                                'obiektu.')
            return
        if not self.wybrane_foldery():
            QMessageBox.warning(self, _TYTUL, 'Zaznacz co najmniej jeden '
                                'folder.')
            return
        if not self.wybrane_rodzaje():
            QMessageBox.warning(self, _TYTUL, 'Zaznacz, co skopiować '
                                '(mapy, atlasy, operaty).')
            return
        if not self.le_docel.text().strip():
            QMessageBox.warning(self, _TYTUL, 'Wskaż folder docelowy.')
            return
        self.accept()


class PodgladDialog(QDialog):
    """Gminy -> foldery -> obręby przed kopiowaniem."""

    def __init__(self, tekst, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL)
        self.resize(640, 560)
        uklad = QVBoxLayout(self)
        uklad.addWidget(QLabel('Sprawdź, co trafi do których folderów:'))
        pole = QPlainTextEdit(tekst)
        pole.setReadOnly(True)
        pole.setFont(QFont('Consolas', 9))
        uklad.addWidget(pole, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Kopiuj')
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


# --------------------------------------------------------------- przebieg

def zapisz_raport(folder, tekst):
    sciezka = os.path.join(folder, 'raport_wylozenia_%s.txt' % znacznik())
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


def uruchom(iface):
    dlg = WylozeniaDialog(iface.mainWindow())
    if dlg.exec_() != QDialog.Accepted:
        return
    docel = dlg.le_docel.text().strip()
    rodzaje = dlg.wybrane_rodzaje()

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
    pd.close()
    if not gminy:
        QMessageBox.warning(iface.mainWindow(), _TYTUL,
                            'Nie znaleziono żadnego obrębu w WYDZ.shp '
                            'zaznaczonych folderów.')
        return

    plan = pw.zaplanuj(gminy, rodzaje)
    opis = pw.opis_planu(plan, uwagi, rodzaje)
    if PodgladDialog(opis, iface.mainWindow()).exec_() != QDialog.Accepted:
        return
    if not any(p['czesci'] for p in plan):
        QMessageBox.warning(iface.mainWindow(), _TYTUL,
                            'Brak plików do skopiowania.')
        return

    istniejace = pw.istniejace_wyniki(docel, plan)
    if istniejace:
        odp = QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            f'W folderze\n{docel}\nsą już foldery, które zostaną zastąpione '
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

    razem = max(sum(cz['rozmiar'] for p in plan for cz in p['czesci']), 1)
    zrobione = [0]
    pd = _postep_okno(iface)
    bledy, ile = [], 0
    try:
        for poz in plan:
            for cz in poz['czesci']:
                def _p(bajty, folder=cz['folder']):
                    zrobione[0] += bajty
                    pd.setLabelText(f'Kopiowanie: {folder}')
                    pd.setValue(min(99, int(100 * zrobione[0] / razem)))
                    QApplication.processEvents()
                    return not pd.wasCanceled()
                bledy += pw.kopiuj_czesc(docel, cz, _p)
                ile += 1
    except pw.Przerwano:
        pd.close()
        pw.usun_tymczasowe(docel, plan)
        raport = zapisz_raport(docel, 'PRZERWANO KOPIOWANIE - foldery '
                               'z poprzedniego przebiegu bez zmian.'
                               '\n\nPlan:\n\n' + opis)
        iface.messageBar().pushMessage(
            _TYTUL, f'Przerwano kopiowanie, raport: {raport}',
            Qgis.Warning, 0)
        return
    except OSError as e:
        pd.close()
        pw.usun_tymczasowe(docel, plan)
        QMessageBox.critical(iface.mainWindow(), _TYTUL,
                             f'Błąd kopiowania:\n{e}')
        return
    pd.close()
    bledy += pw.podmien(docel, plan, istniejace)

    tekst = opis
    if bledy:
        tekst += '\nBŁĘDY:\n' + '\n'.join(f'  {b}' for b in bledy) + '\n'
    raport = zapisz_raport(docel, tekst)
    podsumowanie = f'Utworzono foldery: {ile}.\nFolder: {docel}'
    if bledy:
        podsumowanie += f'\n\nBŁĘDY: {len(bledy)} - szczegóły w raporcie.'
    _pokaz_koniec(iface, podsumowanie, raport)
