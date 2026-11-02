# -*- coding: utf-8 -*-
"""Spakuj do opiniowania przez Nadleśnictwo (menu Generuj).

Wskazuje się folder obiektu i warstwę nadleśnictw. Dla każdego folderu
gminy/obrębu z SHP/WYDZ.shp skrypt ustala, które obręby leżą w których
nadleśnictwach (obręb należy do nadleśnictwa, gdy choć jedno jego
wydzielenie ma w nim ponad 20% powierzchni - jeden obręb może należeć do
kilku), a potem pakuje mapy, atlasy z legendami i operaty *_BDO.pdf do
<NADLESNICTWO>.zip (od 500 MB: <NADLESNICTWO>_1.zip, _2.zip..., obręb nigdy
nie jest rozdzielany) i tworzy obok XLSX z arkuszem dla każdego nadleśnictwa.

Pliki i ZIP-y - spakuj_do_opiniowania_pliki.py.
"""
import os
import platform
import re
from .znacznik_czasu import znacznik
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QProgressDialog, QPushButton, QVBoxLayout,
)
from qgis.core import (
    Qgis, QgsCoordinateTransform, QgsFeature, QgsFeatureRequest, QgsProject,
    QgsSpatialIndex, QgsVectorLayer,
)

from . import spakuj_do_opiniowania_pliki as sp
from .baza_polacz_wyszukaj import pomin_folder
from .przyciski import QDialogButtonBox, QMessageBox

_TYTUL = 'Spakuj do opiniowania przez Nadleśnictwo'
_USTAWIENIE_NADL = 'Las-R/spakuj_opiniowanie/warstwa_nadlesnictw'

PROG_UDZIALU = 0.20

_POLA_NAZWY = ('NAZWAWLASN', 'JPT_NAZWA_', 'NAZWA', 'NAME')
_POLA_ID_OBREBU = ('IDOBREBU', 'JPT_KOD_JE', 'TERYT')
_POLA_ID_GMINY = ('IDJEDNOSTK', 'JPT_KOD_JE', 'TERYT')


def _sciezka_wydz(folder):
    return os.path.join(folder, 'SHP', 'WYDZ.shp')


def foldery_kandydaci(obiekt):
    """[(etykieta, ścieżka, czy ma SHP/WYDZ.shp)]. Wskazany folder trafia
    na listę tylko wtedy, gdy sam ma WYDZ.shp (wskazano gminę, nie obiekt)."""
    wyn = []
    if os.path.isfile(_sciezka_wydz(obiekt)):
        wyn.append((os.path.basename(os.path.normpath(obiekt)), obiekt, True))
    try:
        nazwy = sorted(os.listdir(obiekt), key=str.lower)
    except OSError:
        return wyn
    for n in nazwy:
        sc = os.path.join(obiekt, n)
        if not os.path.isdir(sc) or pomin_folder(n) or \
                n.lower() == sp.FOLDER_WYNIKOWY.lower():
            continue
        wyn.append((n, sc, os.path.isfile(_sciezka_wydz(sc))))
    return wyn


# -------------------------------------------------------------- atrybuty

def _tekst(wartosc):
    if wartosc is None or (hasattr(wartosc, 'isNull') and wartosc.isNull()):
        return ''
    if isinstance(wartosc, float) and wartosc == int(wartosc):
        wartosc = int(wartosc)
    return str(wartosc).strip()


def numery_obrebu(municip, community, adr_les):
    """(MUNICIP, COMMUNITY) z pól WYDZ, a gdy puste - z adresu leśnego
    (R030420013-101...). Gdy nie da się ustalić: (None, None)."""
    municip, community = _tekst(municip), _tekst(community)
    if municip and community:
        return municip.zfill(3), community.zfill(4)
    m = re.match(r'^[A-Za-z]?\d{2}(\d{3})(\d{4})-', _tekst(adr_les))
    return (m.group(1), m.group(2)) if m else (None, None)


def _pole(warstwa, kandydaci):
    for nazwa in kandydaci:
        i = warstwa.fields().lookupField(nazwa)
        if i >= 0:
            return i
    return -1


def _warstwa(sciezka):
    if not os.path.isfile(sciezka):
        return None
    lyr = QgsVectorLayer(sciezka, os.path.basename(sciezka), 'ogr')
    return lyr if lyr.isValid() else None


def _nazwy_obrebow(folder):
    """{community: nazwa} z SHP/OBR.shp (id: 180304_2.0013, ...)."""
    lyr = _warstwa(os.path.join(folder, 'SHP', 'OBR.shp'))
    if lyr is None:
        return {}
    i_id, i_nazwa = _pole(lyr, _POLA_ID_OBREBU), _pole(lyr, _POLA_NAZWY)
    if i_id < 0 or i_nazwa < 0:
        return {}
    wyn = {}
    zad = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
    for f in lyr.getFeatures(zad):
        m = re.search(r'(\d{4})$', _tekst(f[i_id]))
        if m:
            wyn[m.group(1)] = _tekst(f[i_nazwa])
    return wyn


def _nazwy_gmin(folder):
    """{municip: nazwa} z SHP/GMIN.shp (id: 180304_2 -> 042), a pod None
    nazwa, gdy gmina w warstwie jest jedna."""
    lyr = _warstwa(os.path.join(folder, 'SHP', 'GMIN.shp'))
    if lyr is None:
        return {}
    i_id, i_nazwa = _pole(lyr, _POLA_ID_GMINY), _pole(lyr, _POLA_NAZWY)
    if i_nazwa < 0:
        return {}
    wyn, nazwy = {}, []
    zad = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
    for f in lyr.getFeatures(zad):
        nazwa = _tekst(f[i_nazwa])
        nazwy.append(nazwa)
        if i_id >= 0:
            m = re.match(r'^\d{4}(\d{2})_?(\d)', _tekst(f[i_id]))
            if m:
                wyn[m.group(1) + m.group(2)] = nazwa
    if len(nazwy) == 1:
        wyn[None] = nazwy[0]
    return wyn


# ------------------------------------------------------------ nadleśnictwa

def wczytaj_nadlesnictwa(sciezka):
    """(warstwa, {klucz: {nazwa, rdlp}}, [(klucz, geometria)]) albo opis
    błędu jako str. Klucz: (reg_cd, ins_cd) - nazwy się powtarzają."""
    lyr = _warstwa(sciezka)
    if lyr is None:
        return 'Nie udało się wczytać warstwy nadleśnictw.'
    if not lyr.crs().isValid():
        return 'Warstwa nadleśnictw nie ma określonego układu współrzędnych.'
    i_nazwa = lyr.fields().lookupField('ins_name')
    if i_nazwa < 0:
        return 'Warstwa nadleśnictw nie ma pola ins_name.'
    i_reg = lyr.fields().lookupField('reg_cd')
    i_ins = lyr.fields().lookupField('ins_cd')
    i_rdlp = lyr.fields().lookupField('reg_name')
    info, geometrie = {}, []
    for f in lyr.getFeatures():
        nazwa = _tekst(f[i_nazwa])
        if not nazwa or not f.hasGeometry():
            continue
        klucz = (_tekst(f[i_reg]), _tekst(f[i_ins])) \
            if i_reg >= 0 and i_ins >= 0 else nazwa
        info[klucz] = {'nazwa': nazwa,
                       'rdlp': _tekst(f[i_rdlp]) if i_rdlp >= 0 else ''}
        geometrie.append((klucz, f.geometry()))
    if not geometrie:
        return 'Warstwa nadleśnictw nie zawiera obiektów z geometrią i nazwą.'
    return lyr, info, geometrie


class _Nadlesnictwa:
    """Geometrie i indeks przestrzenny w układzie danej warstwy WYDZ."""

    def __init__(self, warstwa, geometrie):
        self.crs = warstwa.crs()
        self.geometrie = geometrie
        self.pamiec = {}

    def w_ukladzie(self, crs):
        klucz = crs.toWkt()
        if klucz not in self.pamiec:
            tr = QgsCoordinateTransform(self.crs, crs, QgsProject.instance())
            indeks, lista = QgsSpatialIndex(), []
            for nr, (kl, geom) in enumerate(self.geometrie):
                g = type(geom)(geom)
                g.transform(tr)
                f = QgsFeature(nr)
                f.setGeometry(g)
                indeks.addFeature(f)
                lista.append((kl, g))
            self.pamiec[klucz] = (indeks, lista)
        return self.pamiec[klucz]


def przypisz_folder(folder, nadl, przypisania, obreby, uwagi, postep=None):
    """Dopisuje obręby folderu do obreby i do przypisania (mutuje oba).
    Zwraca False, gdy przerwano."""
    etykieta = os.path.basename(os.path.normpath(folder))
    lyr = _warstwa(_sciezka_wydz(folder))
    if lyr is None:
        uwagi.append(f'{etykieta}: nie udało się wczytać SHP/WYDZ.shp - '
                     'folder pominięty')
        return True
    if not lyr.crs().isValid():
        uwagi.append(f'{etykieta}: WYDZ.shp nie ma określonego układu '
                     'współrzędnych - folder pominięty')
        return True

    indeks, lista = nadl.w_ukladzie(lyr.crs())
    i_mun = lyr.fields().lookupField('MUNICIP')
    i_com = lyr.fields().lookupField('COMMUNITY')
    i_adr = lyr.fields().lookupField('ADR_LES')
    gminy, obr = _nazwy_gmin(folder), _nazwy_obrebow(folder)

    ile = lyr.featureCount()
    bez_numeru = 0
    for nr, f in enumerate(lyr.getFeatures(), 1):
        if postep and nr % 25 == 0 and postep(etykieta, nr, ile) is False:
            return False
        municip, community = numery_obrebu(
            f[i_mun] if i_mun >= 0 else None,
            f[i_com] if i_com >= 0 else None,
            f[i_adr] if i_adr >= 0 else None)
        if community is None:
            bez_numeru += 1
            continue

        klucz_ob = (folder, municip, community)
        if klucz_ob not in obreby:
            obreby[klucz_ob] = {
                'folder': folder, 'nazwa_folderu': etykieta,
                'municip': municip, 'community': community,
                'nazwa_gminy': gminy.get(municip) or gminy.get(None) or '',
                'nazwa_obrebu': obr.get(community, ''),
            }
        if not f.hasGeometry():
            continue
        geom = f.geometry()
        if not geom.isGeosValid():
            geom = geom.makeValid()
        pole = geom.area()
        if pole <= 0:
            continue
        for id_nadl in indeks.intersects(geom.boundingBox()):
            klucz_n, g_nadl = lista[id_nadl]
            if klucz_ob in przypisania.get(klucz_n, ()):
                continue
            czesc = g_nadl.intersection(geom)
            if not czesc.isEmpty() and czesc.area() / pole > PROG_UDZIALU:
                przypisania.setdefault(klucz_n, set()).add(klucz_ob)
    if bez_numeru:
        uwagi.append(f'{etykieta}: {bez_numeru} wydz. bez numeru obrębu '
                     '(puste MUNICIP/COMMUNITY i ADR_LES) - pominięte')
    return True


# ----------------------------------------------------------------- okna

class SpakujDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL)
        self.resize(600, 560)
        self._docelowy_reczny = False

        uklad = QVBoxLayout(self)
        siatka = QGridLayout()
        siatka.addWidget(QLabel('Folder obiektu:'), 0, 0)
        self.le_obiekt = QLineEdit()
        siatka.addWidget(self.le_obiekt, 0, 1)
        b = QPushButton('Wskaż...')
        b.clicked.connect(self._wskaz_obiekt)
        siatka.addWidget(b, 0, 2)

        siatka.addWidget(QLabel('Warstwa nadleśnictw:'), 1, 0)
        self.le_nadl = QLineEdit(QSettings().value(_USTAWIENIE_NADL, '', str))
        siatka.addWidget(self.le_nadl, 1, 1)
        b = QPushButton('Wskaż...')
        b.clicked.connect(self._wskaz_nadl)
        siatka.addWidget(b, 1, 2)
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

        box = QGroupBox('Co spakować')
        lay = QVBoxLayout(box)
        self.cb_rodzaje = {
            sp.MAPY: QCheckBox('Mapy'),
            sp.ATLASY: QCheckBox('Atlasy z legendami'),
            sp.OPERATY: QCheckBox('Operaty BDO (tylko *_BDO.pdf)'),
        }
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

    def _wskaz_nadl(self):
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż warstwę nadleśnictw', self.le_nadl.text(),
            'Shapefile (*.shp)')
        if sc:
            self.le_nadl.setText(os.path.normpath(sc))

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
            self.le_docel.setText(os.path.join(obiekt, sp.FOLDER_WYNIKOWY))
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
        return [r for r in sp.RODZAJE if self.cb_rodzaje[r].isChecked()]

    def _odswiez_rodzaje(self, *_):
        """Do wyboru tylko to, co jest w zaznaczonych folderach; rodzaj,
        który się właśnie pojawił, jest od razu zaznaczony."""
        dostepne = sp.dostepne_rodzaje(self.wybrane_foldery())
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
        if not os.path.isfile(self.le_nadl.text().strip()):
            QMessageBox.warning(self, _TYTUL, 'Wskaż warstwę nadleśnictw.')
            return
        if not self.wybrane_foldery():
            QMessageBox.warning(self, _TYTUL, 'Zaznacz co najmniej jeden '
                                'folder.')
            return
        if not self.wybrane_rodzaje():
            QMessageBox.warning(self, _TYTUL, 'Zaznacz, co spakować '
                                '(mapy, atlasy, operaty BDO).')
            return
        if not self.le_docel.text().strip():
            QMessageBox.warning(self, _TYTUL, 'Wskaż folder docelowy.')
            return
        QSettings().setValue(_USTAWIENIE_NADL, self.le_nadl.text().strip())
        self.accept()


class PodgladDialog(QDialog):
    """Lista nadleśnictwo -> obręby przed pakowaniem."""

    def __init__(self, tekst, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL)
        self.resize(640, 560)
        uklad = QVBoxLayout(self)
        uklad.addWidget(QLabel('Sprawdź, co trafi do których plików:'))
        pole = QPlainTextEdit(tekst)
        pole.setReadOnly(True)
        pole.setFont(QFont('Consolas', 9))
        uklad.addWidget(pole, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText('Spakuj')
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

def analizuj(foldery, sciezka_nadl, postep=None):
    """(przypisania, obreby, nadlesnictwa, uwagi), None gdy przerwano, albo
    opis błędu jako str."""
    wynik = wczytaj_nadlesnictwa(sciezka_nadl)
    if isinstance(wynik, str):
        return wynik
    warstwa, info, geometrie = wynik
    nadl = _Nadlesnictwa(warstwa, geometrie)
    przypisania, obreby, uwagi = {}, {}, []
    for folder in foldery:
        if not przypisz_folder(folder, nadl, przypisania, obreby, uwagi,
                               postep):
            return None
    return przypisania, obreby, info, uwagi


def obreby_poza(przypisania, obreby):
    przypisane = set().union(*przypisania.values()) if przypisania else set()
    return [ob for k, ob in obreby.items() if k not in przypisane]


def spakuj_plan(plan, folder, postep=None):
    """Tworzy wszystkie ZIP-y. postep(tekst, bajty) zwraca False = przerwij.
    Zwraca (lista błędów, liczba ZIP-ów); przerwanie -> sp.Przerwano."""
    bledy, ile = [], 0
    for poz in plan:
        for cz in poz['czesci']:
            def _p(bajty, plik=cz['plik']):
                return postep(plik, bajty) if postep else True
            bledy += sp.spakuj_czesc(folder, cz, _p)
            ile += 1
    return bledy, ile


def zapisz_raport(folder, tekst):
    sciezka = os.path.join(
        folder, 'raport_opiniowanie_%s.txt'
        % znacznik())
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
    if msg.clickedButton() == pokaz:
        if platform.system()[:3] == 'Win':
            os.startfile(raport)


def uruchom(iface):
    dlg = SpakujDialog(iface.mainWindow())
    if dlg.exec_() != QDialog.Accepted:
        return
    docel = dlg.le_docel.text().strip()
    rodzaje = dlg.wybrane_rodzaje()

    pd = _postep_okno(iface)
    pd.setLabelText('Sprawdzanie wydzieleń...')

    def postep_analizy(etykieta, nr, ile):
        pd.setLabelText(f'{etykieta}: wydzielenie {nr}/{ile}')
        pd.setValue(min(99, int(100 * nr / max(ile, 1))))
        QApplication.processEvents()
        return not pd.wasCanceled()

    wynik = analizuj(dlg.wybrane_foldery(), dlg.le_nadl.text().strip(),
                     postep_analizy)
    pd.close()
    if wynik is None:
        return
    if isinstance(wynik, str):
        QMessageBox.warning(iface.mainWindow(), _TYTUL, wynik)
        return
    przypisania, obreby, info, uwagi = wynik
    if not przypisania:
        QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            'Żaden obręb nie leży w nadleśnictwie z warstwy (próg: ponad '
            '20% wydzielenia). Sprawdź warstwę nadleśnictw.')
        return

    plan = sp.zaplanuj(przypisania, obreby, info, rodzaje)
    poza = obreby_poza(przypisania, obreby)
    opis = sp.opis_planu(plan, poza, uwagi, rodzaje)
    if PodgladDialog(opis, iface.mainWindow()).exec_() != QDialog.Accepted:
        return

    istniejace = sp.istniejace_wyniki(docel, plan)
    if istniejace:
        odp = QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            f'W folderze\n{docel}\nsą już pliki, które zostaną zastąpione:'
            f'\n\n{chr(10).join(istniejace)}\n\nNadpisać je?',
            QMessageBox.Yes | QMessageBox.Abort, QMessageBox.Abort)
        if odp != QMessageBox.Yes:
            return
    try:
        os.makedirs(docel, exist_ok=True)
        # sama próba otwarcia: plik zablokowany np. przez Excela wychodzi
        # od razu, nie po pakowaniu, i nic jeszcze nie jest ruszone
        for nazwa in istniejace:
            with open(os.path.join(docel, nazwa), 'r+b'):
                pass
    except OSError as e:
        QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            f'Nie udało się przygotować folderu docelowego (plik otwarty '
            f'w innym programie?):\n{e}')
        return

    razem = max(sum(cz['rozmiar'] for p in plan for cz in p['czesci']), 1)
    zrobione = [0]
    pd = _postep_okno(iface)

    def postep_zip(plik, bajty):
        zrobione[0] += bajty
        pd.setLabelText(f'Pakowanie: {plik}')
        pd.setValue(min(99, int(100 * zrobione[0] / razem)))
        QApplication.processEvents()
        return not pd.wasCanceled()

    try:
        bledy, ile_zip = spakuj_plan(plan, docel, postep_zip)
    except sp.Przerwano:
        pd.close()
        raport = zapisz_raport(docel, 'PRZERWANO PAKOWANIE - część ZIP-ów '
                               'nie powstała albo pochodzi z poprzedniego '
                               'przebiegu, zestawienia XLSX nie zmieniono.'
                               '\n\nPlan:\n\n' + opis)
        iface.messageBar().pushMessage(
            _TYTUL, f'Przerwano pakowanie, raport: {raport}',
            Qgis.Warning, 0)
        return
    except OSError as e:
        pd.close()
        QMessageBox.critical(iface.mainWindow(), _TYTUL,
                             f'Błąd zapisu ZIP-a:\n{e}')
        return
    pd.close()

    # ZIP-y z poprzedniego przebiegu, których ten nie zastąpił (np. _3, gdy
    # części jest teraz mniej) - dopiero po udanym pakowaniu
    nowe = {cz['plik'].lower() for p in plan for cz in p['czesci']}
    for nazwa in istniejace:
        if nazwa.lower().endswith('.zip') and nazwa.lower() not in nowe:
            try:
                os.remove(os.path.join(docel, nazwa))
            except OSError as e:
                bledy.append(f'Nie usunięto starego pliku {nazwa}: {e}')

    try:
        sp.zapisz_xlsx(os.path.join(docel, sp.PLIK_XLSX), plan)
    except (OSError, ImportError) as e:
        bledy.append(f'{sp.PLIK_XLSX}: {e}')

    tekst = opis
    if bledy:
        tekst += '\nBŁĘDY:\n' + '\n'.join(f'  {b}' for b in bledy) + '\n'
    raport = zapisz_raport(docel, tekst)

    podsumowanie = f'Utworzono ZIP-y: {ile_zip}.\nFolder: {docel}'
    if bledy:
        podsumowanie += f'\n\nBŁĘDY: {len(bledy)} - szczegóły w raporcie.'
    _pokaz_koniec(iface, podsumowanie, raport)
