"""Dopisz opisy taksacyjne do bazy - na podstawie warstwy punktowej (pole
GRUPA: INNE WYL, L ENERG, SUKCESJA, DROGI L, LZ-Ł, ZRĄB - patrz
warstwa_opisow_dock.py) i warstwy WYDZ (pole ADR_LES) dopisuje do
wskazanej bazy Taksatora F_SUBAREA.AREA_TYPE_CD. Dodatkowo do
SUBAREA_INFO: dla LZ-Ł stały tekst "LZ ze względu na powierzchnię", dla
INNE WYL treść pola INF_ROZNE punktu (jeśli warstwa punktowa je ma).

Przed zapisem kontrole geometryczne (patrz `waliduj_geometrie`), wszystkie
sprawdzane naraz - jeśli którakolwiek nie przejdzie, generowane są warstwy
memory z lokalizacją problemów i zapis do bazy jest wstrzymywany:

1. WYDZ musi mieć uzupełniony ADR_LES na każdym poligonie.
2. Każdy punkt musi leżeć na dokładnie jednym poligonie WYDZ (nie 0 - poza
   WYDZ, nie >1 - nakładające się wydzielenia).
3. Dwa różne punkty nie mogą leżeć na tym samym wydzieleniu (konflikt przy
   zapisie AREA_TYPE_CD - który wpis miałby wygrać).
4. Punkt GRUPA='LZ-Ł' musi leżeć na wydzieleniu z WYDZ='Lz'.
5. GRUPA punktu musi być jedną z wartości z `GRUPY_VALIDNE`.

Po geometrii - druga kontrola, tym razem względem bazy (patrz
`zapisz_do_bazy`): jeśli wydzielenie ma już inną, niepustą wartość
AREA_TYPE_CD niż ta z punktu, zapis dla całości jest wstrzymywany i
zgłaszany jako konflikt (zamiast cichego nadpisania) - dopiero gdy
wszystkie pary są bezkonfliktowe, wykonywana jest kopia zapasowa bazy i
faktyczny zapis.
"""
import glob
import os

from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)
from qgis.core import (
    QgsFeature, QgsField, QgsProject, QgsSpatialIndex, QgsVectorLayer,
    QgsWkbTypes,
)

from .baza_wrapper import Baza

GRUPY_VALIDNE = ('INNE WYL', 'L ENERG', 'SUKCESJA', 'DROGI L', 'LZ-Ł', 'ZRĄB')
INFO_LZ = 'LZ ze względu na powierzchnię'
GRUPA_WYMAGA_INF_ROZNE = 'INNE WYL'


def _warstwy_wektorowe(typ_geometrii):
    return [
        lyr for lyr in QgsProject.instance().mapLayers().values()
        if isinstance(lyr, QgsVectorLayer)
        and lyr.geometryType() == typ_geometrii
    ]


def _warstwa_pkt_bledow(crs, tytul, punkty_z_opisem):
    """punkty_z_opisem: lista (QgsGeometry punktowa, opis)."""
    lyr = QgsVectorLayer(f'Point?crs={crs.authid()}', tytul, 'memory')
    lyr.dataProvider().addAttributes(
        [QgsField('OPIS', QVariant.String, '', 150)])
    lyr.updateFields()
    feats = []
    for geom, opis in punkty_z_opisem:
        f = QgsFeature(lyr.fields())
        f.setGeometry(geom)
        f['OPIS'] = opis
        feats.append(f)
    lyr.dataProvider().addFeatures(feats)
    QgsProject.instance().addMapLayer(lyr)
    return lyr


def _warstwa_poly_bledow(wydz_lyr, wydz_feats, fidy, tytul):
    lyr = QgsVectorLayer(
        f'MultiPolygon?crs={wydz_lyr.crs().authid()}', tytul, 'memory')
    lyr.dataProvider().addAttributes(wydz_lyr.fields().toList())
    lyr.updateFields()
    feats = [wydz_feats[fid] for fid in fidy]
    lyr.dataProvider().addFeatures(feats)
    QgsProject.instance().addMapLayer(lyr)
    return lyr


def waliduj_geometrie(pkt_lyr, wydz_lyr):
    """Waliduje warstwę punktową względem WYDZ (patrz kontrole 1-5 w
    docstringu modułu).

    Returns:
        Dict z kluczem 'ok'. Gdy False - dodatkowo 'komunikat' (str), a
        warstwy błędów są już dodane do projektu. Gdy True - dodatkowo
        'pary': lista (adr_les, grupa, pkt_fid).
    """
    pkt_feats = {f.id(): f for f in pkt_lyr.getFeatures()}
    wydz_feats = {f.id(): f for f in wydz_lyr.getFeatures()}

    si = QgsSpatialIndex()
    for f in wydz_feats.values():
        si.insertFeature(f)

    # 1. puste ADR_LES w WYDZ
    adr_les_puste = [
        fid for fid, f in wydz_feats.items()
        if str(f['ADR_LES']).strip() in ('', 'None', 'NULL')
    ]

    # 2. dopasowanie punkt -> wydzielenia (wszystkie trafienia, do
    # wykrycia niejednoznaczności)
    trafienia = {}
    for pfid, pf in pkt_feats.items():
        geom = pf.geometry()
        trafienia[pfid] = [
            wfid for wfid in si.intersects(geom.boundingBox())
            if wydz_feats[wfid].geometry().contains(geom)
        ]

    poza_wydz = [pfid for pfid, t in trafienia.items() if len(t) == 0]
    niejednoznaczne = [pfid for pfid, t in trafienia.items() if len(t) > 1]
    jednoznaczne = {
        pfid: t[0] for pfid, t in trafienia.items() if len(t) == 1
    }

    # 3. dublety - kilka różnych punktów w tym samym wydzieleniu
    wg_wydz = {}
    for pfid, wfid in jednoznaczne.items():
        wg_wydz.setdefault(wfid, []).append(pfid)
    dublety_wydz = {wfid for wfid, pfidy in wg_wydz.items() if len(pfidy) > 1}
    dublety = {
        pfid for wfid in dublety_wydz for pfid in wg_wydz[wfid]
    }

    # 5. GRUPA spoza whitelisty
    grupa_nieznana = [
        pfid for pfid, pf in pkt_feats.items()
        if str(pf['GRUPA']).strip() not in GRUPY_VALIDNE
    ]

    # 4. LZ-Ł musi trafiać w WYDZ='Lz' - liczone tylko dla punktów już
    # jednoznacznych, bez dubletu i z poprawną GRUPA
    lzl_niezgodne = []
    for pfid, wfid in jednoznaczne.items():
        if pfid in dublety or pfid in grupa_nieznana:
            continue
        if str(pkt_feats[pfid]['GRUPA']).strip() != 'LZ-Ł':
            continue
        if str(wydz_feats[wfid]['WYDZ']).strip().upper() != 'LZ':
            lzl_niezgodne.append(pfid)

    bledy = {}
    if adr_les_puste:
        bledy['adr_les_puste'] = adr_les_puste
    if poza_wydz:
        bledy['poza_wydz'] = poza_wydz
    if niejednoznaczne:
        bledy['niejednoznaczne'] = niejednoznaczne
    if dublety_wydz:
        bledy['dublety'] = sorted(dublety)
        bledy['dublety_wydz'] = sorted(dublety_wydz)
    if grupa_nieznana:
        bledy['grupa_nieznana'] = grupa_nieznana
    if lzl_niezgodne:
        bledy['lzl_niezgodne'] = lzl_niezgodne

    if bledy:
        return _raport_bledow_geometrii(
            bledy, pkt_feats, wydz_feats, pkt_lyr.crs(), wydz_lyr)

    ma_inf_rozne = 'INF_ROZNE' in {pole.name() for pole in pkt_lyr.fields()}

    def _inf_rozne(pf):
        if not ma_inf_rozne:
            return ''
        wartosc = pf['INF_ROZNE']
        return str(wartosc).strip() if wartosc is not None else ''

    pary = [
        (wydz_feats[wfid]['ADR_LES'], str(pkt_feats[pfid]['GRUPA']).strip(),
         _inf_rozne(pkt_feats[pfid]), pfid)
        for pfid, wfid in jednoznaczne.items()
    ]
    return {'ok': True, 'pary': pary}


def _raport_bledow_geometrii(bledy, pkt_feats, wydz_feats, pkt_crs, wydz_lyr):
    czesci = []

    if 'adr_les_puste' in bledy:
        _warstwa_poly_bledow(
            wydz_lyr, wydz_feats, bledy['adr_les_puste'],
            'Opisy - WYDZ bez adresu leśnego')
        czesci.append(
            f"{len(bledy['adr_les_puste'])} wydzielenie(a) WYDZ bez "
            "uzupełnionego adresu leśnego")

    if 'poza_wydz' in bledy:
        pkty = [(pkt_feats[fid].geometry(), 'poza WYDZ')
                for fid in bledy['poza_wydz']]
        _warstwa_pkt_bledow(pkt_crs, 'Opisy - punkty poza WYDZ', pkty)
        czesci.append(f"{len(bledy['poza_wydz'])} punkt(ów) poza WYDZ")

    if 'niejednoznaczne' in bledy:
        pkty = [(pkt_feats[fid].geometry(), 'nakładające się WYDZ')
                for fid in bledy['niejednoznaczne']]
        _warstwa_pkt_bledow(pkt_crs, 'Opisy - punkty niejednoznaczne', pkty)
        czesci.append(
            f"{len(bledy['niejednoznaczne'])} punkt(ów) leży na więcej niż "
            "jednym WYDZ (nakładające się wydzielenia)")

    if 'dublety_wydz' in bledy:
        _warstwa_poly_bledow(
            wydz_lyr, wydz_feats, bledy['dublety_wydz'],
            'Opisy - dublety w wydzieleniu')
        czesci.append(
            f"{len(bledy['dublety_wydz'])} wydzielenie(a) mają więcej niż "
            f"1 punkt ({len(bledy['dublety'])} punkt(ów) łącznie dzieli "
            "wydzielenie z innym punktem)")

    if 'grupa_nieznana' in bledy:
        pkty = [(pkt_feats[fid].geometry(), 'nieznana wartość GRUPA')
                for fid in bledy['grupa_nieznana']]
        _warstwa_pkt_bledow(pkt_crs, 'Opisy - nieznana GRUPA', pkty)
        czesci.append(
            f"{len(bledy['grupa_nieznana'])} punkt(ów) ma wartość GRUPA "
            "spoza listy (" + ', '.join(GRUPY_VALIDNE) + ")")

    if 'lzl_niezgodne' in bledy:
        pkty = [(pkt_feats[fid].geometry(), "LZ-Ł poza WYDZ='Lz'")
                for fid in bledy['lzl_niezgodne']]
        _warstwa_pkt_bledow(
            pkt_crs, "Opisy - LZ-Ł niezgodne z WYDZ='Lz'", pkty)
        czesci.append(
            f"{len(bledy['lzl_niezgodne'])} punkt(ów) GRUPA=LZ-Ł leży na "
            "wydzieleniu, które NIE ma WYDZ='Lz'")

    komunikat = (
        'Znaleziono błędy do poprawy:\n- ' + '\n- '.join(czesci) +
        '\n\nSzczegóły w dodanych warstwach memory. Popraw dane i uruchom '
        'ponownie.'
    )
    return {'ok': False, 'komunikat': komunikat}


def zapisz_do_bazy(baza_sc, pary):
    """pary: lista (adr_les, grupa, inf_rozne, pkt_fid).

    Returns:
        Dict z kluczem 'ok' i 'komunikat' (raport do pokazania
        użytkownikowi niezależnie od wyniku).
    """
    baza = Baza(baza_sc)
    if not baza.polacz():
        return {'ok': False, 'komunikat': 'Nie udało się połączyć z bazą.'}

    wydzielenia = baza.pobierz_wydzielenia()
    if not wydzielenia:
        baza.zamknij()
        return {
            'ok': False,
            'komunikat': 'Nie udało się pobrać wydzieleń z bazy.'}

    brak_w_bazie = []
    konflikty = []  # (adr_les, obecna_wartosc, nowa_wartosc)
    do_zapisu = []  # (arodes_int_num, grupa, adr_les, inf_rozne)

    for adr_les, grupa, inf_rozne, _pfid in pary:
        if adr_les not in wydzielenia:
            brak_w_bazie.append(adr_les)
            continue

        aint = wydzielenia[adr_les]
        wynik = baza.pobierz(
            'select AREA_TYPE_CD from F_SUBAREA where ARODES_INT_NUM = '
            + str(aint) + ';')
        obecna = ''
        if wynik and wynik[0][0] is not None:
            obecna = str(wynik[0][0])

        if obecna.strip() not in ('', grupa):
            konflikty.append((adr_les, obecna, grupa))
            continue

        do_zapisu.append((aint, grupa, adr_les, inf_rozne))

    if brak_w_bazie or konflikty:
        czesci = []
        if brak_w_bazie:
            pokazane = brak_w_bazie[:20]
            czesci.append(
                f'{len(brak_w_bazie)} adres(ów) leśnych nieobecnych w '
                'bazie: ' + ', '.join(pokazane) +
                (', ...' if len(brak_w_bazie) > len(pokazane) else ''))
        if konflikty:
            pokazane = konflikty[:20]
            opisy = [
                f'{a} (jest: {o!r}, ma być: {n!r})' for a, o, n in pokazane
            ]
            czesci.append(
                f'{len(konflikty)} wydzielenie(a) mają już inną wartość '
                'AREA_TYPE_CD niż wynika z punktu: ' + '; '.join(opisy) +
                (', ...' if len(konflikty) > len(pokazane) else ''))
        baza.zamknij()
        return {
            'ok': False,
            'komunikat': 'Znaleziono błędy do poprawy:\n- ' +
            '\n- '.join(czesci) +
            '\n\nNic nie zostało zapisane do bazy. Popraw dane i uruchom '
            'ponownie.'
        }

    if not do_zapisu:
        baza.zamknij()
        return {'ok': True, 'komunikat': 'Brak zmian do zapisania.'}

    baza.utworz_kopie('dopisz_opisy_taksacyjne')
    if not baza.polacz():
        return {
            'ok': False,
            'komunikat': 'Nie udało się połączyć z bazą po kopii '
            'zapasowej.'}

    zapisano = 0
    bledy_zapisu = []
    for aint, grupa, adr_les, inf_rozne in do_zapisu:
        if grupa == 'LZ-Ł':
            dopisek = INFO_LZ
        elif grupa == GRUPA_WYMAGA_INF_ROZNE and inf_rozne:
            dopisek = inf_rozne
        else:
            dopisek = ''

        if dopisek:
            wynik = baza.pobierz(
                'select SUBAREA_INFO from F_SUBAREA where '
                'ARODES_INT_NUM = ' + str(aint) + ';')
            info_obecne = ''
            if wynik and wynik[0][0] is not None:
                info_obecne = str(wynik[0][0])

            if dopisek in info_obecne:
                info_nowe = info_obecne
            elif info_obecne.strip():
                info_nowe = info_obecne.rstrip() + '; ' + dopisek
            else:
                info_nowe = dopisek

            ok = baza.wpisz_tab([
                'update F_SUBAREA set AREA_TYPE_CD = ?, SUBAREA_INFO = ? '
                'where ARODES_INT_NUM = ?;',
                (grupa, info_nowe, aint)
            ])
        else:
            ok = baza.wpisz_tab([
                'update F_SUBAREA set AREA_TYPE_CD = ? '
                'where ARODES_INT_NUM = ?;',
                (grupa, aint)
            ])

        if ok:
            zapisano += 1
        else:
            bledy_zapisu.append(adr_les)

    baza.zamknij()

    komunikat = f'Zapisano {zapisano} wydzieleń.'
    if bledy_zapisu:
        komunikat += (
            f'\nBłędy zapisu ({len(bledy_zapisu)}): ' +
            ', '.join(bledy_zapisu[:20]))
    return {'ok': True, 'komunikat': komunikat}


class DopiszOpisyTaksDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Dopisz opisy taksacyjne do bazy')
        self.setMinimumSize(520, 200)
        self._wydzielenia_lyr = []
        self._punkty_lyr = []
        self._build_ui()
        self._wczytaj_warstwy()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            'Na podstawie warstwy punktowej (pole GRUPA) i warstwy WYDZ '
            '(pole ADR_LES) dopisuje do bazy F_SUBAREA.AREA_TYPE_CD (dla '
            'LZ-Ł i INNE WYL dodatkowo SUBAREA_INFO).\n'
            'Każdy punkt musi leżeć na dokładnie jednym WYDZ, bez dubletów '
            'w jednym wydzieleniu; LZ-Ł musi leżeć na wydzieleniu z '
            "WYDZ='Lz'."
        ))

        wydz_row = QHBoxLayout()
        wydz_row.addWidget(QLabel('Warstwa WYDZ:'))
        self.combo_wydz = QComboBox()
        wydz_row.addWidget(self.combo_wydz, 1)
        layout.addLayout(wydz_row)

        pkt_row = QHBoxLayout()
        pkt_row.addWidget(QLabel('Warstwa punktowa (opis_pkt):'))
        self.combo_pkt = QComboBox()
        pkt_row.addWidget(self.combo_pkt, 1)
        layout.addLayout(pkt_row)

        baza_row = QHBoxLayout()
        baza_row.addWidget(QLabel('Baza Taksatora:'))
        self.line_baza = QLineEdit()
        baza_row.addWidget(self.line_baza, 1)
        self.btn_baza = QPushButton('...')
        self.btn_baza.clicked.connect(self._wybierz_baze)
        baza_row.addWidget(self.btn_baza)
        layout.addLayout(baza_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText('Uruchom')
        buttons.accepted.connect(self._uruchom)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _wczytaj_warstwy(self):
        self._wydzielenia_lyr = _warstwy_wektorowe(QgsWkbTypes.PolygonGeometry)
        self._punkty_lyr = _warstwy_wektorowe(QgsWkbTypes.PointGeometry)

        self.combo_wydz.addItems([lyr.name() for lyr in self._wydzielenia_lyr])
        self.combo_pkt.addItems([lyr.name() for lyr in self._punkty_lyr])

        if self._wydzielenia_lyr:
            i = next(
                (i for i, lyr in enumerate(self._wydzielenia_lyr)
                 if lyr.name().upper() == 'WYDZ'), 0)
            self.combo_wydz.setCurrentIndex(i)

        if self._punkty_lyr:
            i = next(
                (i for i, lyr in enumerate(self._punkty_lyr)
                 if lyr.name().upper() == 'OPIS_PKT'), 0)
            self.combo_pkt.setCurrentIndex(i)

        self._zgadnij_baze()

    def _zgadnij_baze(self):
        if self.line_baza.text().strip():
            return
        lyr = self._wybrane_pkt() or self._wybrane_wydz()
        if lyr is None:
            return
        try:
            sc = lyr.dataProvider().dataSourceUri().split('|')[0]
        except Exception:
            return
        if not sc or not os.path.isfile(sc):
            return
        kandydaci = glob.glob(os.path.join(os.path.dirname(sc), '..', '*.mdb'))
        if len(kandydaci) == 1:
            self.line_baza.setText(os.path.abspath(kandydaci[0]))

    def _wybierz_baze(self):
        kat = os.path.dirname(self.line_baza.text().strip())
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę Taksatora', kat, 'Access MDB (*.mdb)')
        if sc:
            self.line_baza.setText(sc)

    def _wybrane_wydz(self):
        i = self.combo_wydz.currentIndex()
        if 0 <= i < len(self._wydzielenia_lyr):
            return self._wydzielenia_lyr[i]
        return None

    def _wybrane_pkt(self):
        i = self.combo_pkt.currentIndex()
        if 0 <= i < len(self._punkty_lyr):
            return self._punkty_lyr[i]
        return None

    def _uruchom(self):
        wydz = self._wybrane_wydz()
        pkt = self._wybrane_pkt()
        if wydz is None or pkt is None:
            QMessageBox.warning(
                self, 'Brak warstw',
                'W projekcie brakuje warstwy poligonowej (WYDZ) i/lub '
                'punktowej (opis_pkt).')
            return

        baza_sc = self.line_baza.text().strip()
        if not baza_sc or not os.path.isfile(baza_sc):
            QMessageBox.warning(
                self, 'Brak bazy', 'Wskaż plik bazy Taksatora.')
            return

        wynik = waliduj_geometrie(pkt, wydz)
        if not wynik['ok']:
            QMessageBox.warning(self, 'Popraw dane', wynik['komunikat'])
            return

        if not wynik['pary']:
            QMessageBox.information(
                self, 'Brak punktów',
                'Warstwa punktowa nie zawiera żadnych punktów do '
                'przetworzenia.')
            return

        wynik_bazy = zapisz_do_bazy(baza_sc, wynik['pary'])
        if not wynik_bazy['ok']:
            QMessageBox.warning(self, 'Popraw dane', wynik_bazy['komunikat'])
            return

        QMessageBox.information(self, 'OK', wynik_bazy['komunikat'])
        self.accept()


def uruchom(iface=None):
    dlg = DopiszOpisyTaksDialog(iface.mainWindow() if iface else None)
    dlg.exec_()
