"""Rozdziel bazy na UPUL i ISL.

Dzieli bazę na dwie nowe bazy (<nazwa>_UPUL / <nazwa>_ISL, kopie pliku
źródłowego) według sumy powierzchni użytku LS w obrębach ewidencyjnych -
tryb automatyczny (ISL: LS < 10,0000 ha) albo ręczny (obręby ISL
wskazuje użytkownik). Obręby bez LS są usuwane z obu baz. Opcjonalnie
dzieli też wszystkie warstwy SHP z folderu (SHP_UPUL / SHP_ISL). Baza
i warstwy źródłowe nie są zmieniane. Szczegóły - core/rozdziel.py.
"""

import os
import shutil

from PyQt5.QtWidgets import QDialog, QMessageBox
from qgis.core import Qgis

from ..baza_wrapper import Baza
from ..pw import PasekPostepu
from ..waypointy import katalog_raportow

from .gui.dialog import RozdzielUpulIslDialog
from .core import rozdziel as R

_TYTUL = 'Rozdziel bazy na UPUL i ISL'


def _blad(iface, tekst):
    iface.messageBar().clearWidgets()
    iface.messageBar().pushMessage('BŁĄD', tekst, Qgis.Critical, 0)


def uruchom(iface):
    dlg = RozdzielUpulIslDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False
    return _rozdziel(iface, dlg.wybor())


def _grupy_niepuste(przydzial):
    return [g for g in (R.UPUL, R.ISL) if g in przydzial.values()]


def _potwierdz_nadpisanie(iface, sciezki):
    istniejace = [s for s in sciezki if os.path.exists(s)]
    if not istniejace:
        return True
    odp = QMessageBox.question(
        iface.mainWindow(), _TYTUL,
        'Istnieją już wyniki poprzedniego rozdzielenia:\n\n' +
        '\n'.join(istniejace) + '\n\nNadpisać je?',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    return odp == QMessageBox.Yes


def _potwierdz_konflikty(iface, konflikty):
    obce = sum(len(o) for _, _, o in konflikty)
    odp = QMessageBox.question(
        iface.mainWindow(), 'Wydzielenia na granicy UPUL/ISL',
        f'Wykryto {len(konflikty)} wydzieleń, których rozliczenie '
        f'powierzchni obejmuje łącznie {obce} działek z obrębów trafiających '
        'do drugiej bazy (albo usuwanych jako obręby bez LS).\n\n'
        'Jeśli będziesz kontynuować, wydzielenie trafi do bazy wg obrębu '
        'z adresu leśnego, a jego rozliczenie na działkach z drugiej bazy '
        'zostanie usunięte - trzeba będzie ponownie rozliczyć powierzchnię.'
        '\n\nJeśli wybierzesz "Nie", powstanie raport txt ze szczegółami.\n\n'
        'Kontynuować?',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    return odp == QMessageBox.Yes


def _rozdziel(iface, wybor):  # noqa
    baza_sc = wybor['baza_sc']
    przydzial = wybor['przydzial']
    folder_shp = wybor['folder_shp']
    katalog = os.path.dirname(baza_sc)

    grupy = _grupy_niepuste(przydzial)
    sciezki = {g: s for g, s in R.sciezki_wynikowe(baza_sc).items()
               if g in grupy}
    katalogi_shp = {g: os.path.join(katalog, 'SHP_' + g) for g in grupy} \
        if folder_shp else {}
    if not _potwierdz_nadpisanie(
            iface, list(sciezki.values()) + list(katalogi_shp.values())):
        return False

    # --- analiza wydzieleń (baza źródłowa tylko czytana) ---
    baza = Baza(baza_sc, pomin_blokade=True)
    if not baza.polacz():
        _blad(iface, 'Nie udało się połączyć z bazą źródłową.')
        return False
    try:
        analiza = R.analizuj_wydzielenia(baza, przydzial)
    finally:
        baza.zamknij()

    if analiza['konflikty'] and not _potwierdz_konflikty(
            iface, analiza['konflikty']):
        rap = R.zapisz_raport_konfliktow(
            katalog_raportow(katalog), analiza['konflikty'])
        _blad(iface, 'Przerwano - nic nie utworzono. Wydzielenia na granicy '
              'UPUL/ISL: ' + rap)
        return False

    iface.messageBar().clearWidgets()
    postep = PasekPostepu(iface).stworz_pasek(_TYTUL)
    postep.setValue(0)
    krok = 70 // max(len(grupy), 1)

    # --- bazy wynikowe ---
    wyniki_baz = {}
    for i, g in enumerate(grupy):
        sc = sciezki[g]
        try:
            R.skopiuj_baze(baza_sc, sc)
        except OSError as e:
            wyniki_baz[g] = (f'nie udało się skopiować bazy ({e})', None)
            continue
        kopia = Baza(sc)
        if not kopia.polacz():
            wyniki_baz[g] = ('nie udało się połączyć z kopią bazy', None)
            continue
        try:
            licz = R.wyczysc_kopie(kopia, przydzial, g,
                                   analiza['arodes_grupa'],
                                   analiza['obreby_adr'])
        finally:
            kopia.zamknij()
        if licz is None:
            # niedokończonej kopii nie zostawiamy - wyglądałaby na wynik
            try:
                os.remove(sc)
            except OSError:
                pass
            wyniki_baz[g] = ('błąd czyszczenia kopii - szczegóły w logu '
                             'Las-R, kopia usunięta', None)
            continue
        R.kompaktuj(sc)
        wyniki_baz[g] = (sc, licz)
        postep.setValue(10 + krok * (i + 1))

    # --- grafika ---
    raport_grafiki = []
    if folder_shp:
        for kat in katalogi_shp.values():
            if os.path.isdir(kat):
                shutil.rmtree(kat, ignore_errors=True)
        raport_grafiki = R.podziel_grafike(folder_shp, katalogi_shp, przydzial)
    postep.setValue(95)

    rap = R.zapisz_raport(
        katalog_raportow(katalog), baza_sc, wybor['tryb'], wybor['obreby'],
        przydzial, analiza, wyniki_baz, raport_grafiki)
    postep.setValue(100)
    iface.messageBar().clearWidgets()

    # --- podsumowanie ---
    bledy = [g for g, (_, licz) in wyniki_baz.items() if licz is None]
    bledy_shp = [x[0] for x in raport_grafiki if x[4]]
    tresc = ', '.join(
        f'{g}: {os.path.basename(sc)} ({analiza["liczba_wydz"][g]} wydz.)'
        for g, (sc, licz) in wyniki_baz.items() if licz is not None)
    for g in (R.UPUL, R.ISL):
        if g not in grupy:
            tresc += f'. Brak obrębów {g} - baza {g} nie powstała'
    if folder_shp:
        tresc += '. Grafika: ' + ', '.join(katalogi_shp.values())
    tresc += '. Raport: ' + rap

    if bledy or bledy_shp:
        iface.messageBar().pushMessage(
            'ROZDZIELENIE Z BŁĘDAMI',
            tresc + '. Błędy: ' + ', '.join(bledy + bledy_shp) +
            ' - szczegóły w raporcie i logu Las-R', Qgis.Warning, 0)
    else:
        iface.messageBar().pushMessage(
            'ROZDZIELENIE ZAKOŃCZONE', tresc, Qgis.Success, 0)

    if analiza['rozliczenie_puste']:
        QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            'Rozliczenie powierzchni wydzieleń (F_AROD_LAND_USE) w bazie '
            'źródłowej było puste.\n\nPo rozdzieleniu rozlicz powierzchnię '
            'wydzieleń w obu bazach.')
    elif analiza['konflikty']:
        QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            f'{len(analiza["konflikty"])} wydzieleń miało rozliczenie na '
            'działkach z obrębów drugiej bazy - ich rozliczenie jest teraz '
            'niepełne.\n\nPonownie rozlicz powierzchnię wydzieleń (lista '
            'w raporcie).')

    return not bledy
