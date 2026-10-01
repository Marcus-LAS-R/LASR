"""Podmień wybrane zabiegi.

W wybranej bazie, w zakresie: cała baza / obręby / formy ochrony
przyrody, podmienia zabiegi wg reguł "źródło -> cel, nowy %" albo je
usuwa, poprawiając odnowienia, PIEL i AGROT tak jak "Dopisz/sprawdź
zabiegi". Przed zapisem kopia bazy (Kopie_manipulacyjne), zapis w jednej
transakcji, raport przed/po w Raporty. Szczegóły - core/podmien.py.
"""

import os

from PyQt5.QtWidgets import QDialog, QMessageBox
from qgis.core import Qgis

from ..baza_wrapper import Baza
from ..waypointy import katalog_raportow
from .. import kopie_manipulacyjne

from .gui.dialog import PodmienZabiegiDialog
from .core import podmien as P

_TYTUL = 'Podmień wybrane zabiegi'


def _blad(iface, tekst):
    iface.messageBar().clearWidgets()
    iface.messageBar().pushMessage('BŁĄD', tekst, Qgis.Critical, 0)


def uruchom(iface):
    dlg = PodmienZabiegiDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False
    return _podmien(iface, dlg.wybor())


def _podmien(iface, wybor):
    baza_sc = wybor['baza_sc']
    baza = Baza(baza_sc)
    if not baza.polacz():
        _blad(iface, 'Nie udało się połączyć z bazą.')
        return False

    try:
        wydz = P.wydzielenia_w_zakresie(
            baza, wybor['zakres'], wybor['wybrane'])
        plany = P.zaplanuj(baza, wydz, wybor['reguly'], wybor['uwaga'])
    except Exception:
        baza.zamknij()
        raise
    s = P.podsumuj(plany)
    if s['wydzielenia'] == 0:
        baza.zamknij()
        iface.messageBar().pushMessage(
            _TYTUL, 'Brak wydzieleń do zmiany w wybranym zakresie '
            f'(pominiętych: {s["pominiete"]}).', Qgis.Info, 10)
        return False

    odp = QMessageBox.question(
        iface.mainWindow(), _TYTUL,
        f'Zmiany obejmą {s["wydzielenia"]} wydzieleń '
        f'(pominiętych: {s["pominiete"]}).\n\n'
        'Reguły: ' + '; '.join(P.opis_reguly(*r) for r in wybor['reguly']) +
        '\n\nPrzed zapisem zostanie utworzona kopia bazy. Kontynuować?',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if odp != QMessageBox.Yes:
        baza.zamknij()
        return False

    # kopia bezpieczeństwa przed zapisem - połączenie zamknięte na czas
    # kopiowania pliku
    baza.zamknij()
    folder_kopii = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
        baza_sc, [], 'podmiana_zabiegow')
    if folder_kopii is None:
        _blad(iface, 'Nie udało się utworzyć kopii bazy - przerwano, nic '
              'nie zmieniono.')
        return False
    if not baza.polacz():
        _blad(iface, 'Nie udało się ponownie połączyć z bazą.')
        return False

    try:
        wynik = P.zapisz(baza, plany)
    finally:
        baza.zamknij()

    katalog = katalog_raportow(os.path.dirname(baza_sc))
    rap = P.zapisz_raport(katalog, baza_sc, wybor['reguly'],
                          wybor['zakres_opis'], wybor['uwaga'], plany,
                          folder_kopii)

    iface.messageBar().clearWidgets()
    if wynik is None:
        _blad(iface, 'Błąd zapisu - wycofano wszystkie zmiany (szczegóły w '
              'logu Las-R). Raport planowanych zmian: ' + rap)
        return False

    zapisane, licz = wynik
    z_uwagami = len([p for p in plany
                     if not p.pominiete and p.ma_zmiany() and p.uwagi])
    tresc = (
        f'Zmieniono {zapisane} wydzieleń (wpisy: zmienione '
        f'{licz["zmienione"]}, usunięte {licz["usuniete"]}, dodane '
        f'{licz["dodane"]}; uwagi dopisane: {licz["uwagi"]}). '
        f'Pominięte: {s["pominiete"]}. Kopia: {folder_kopii}. Raport: {rap}')
    if z_uwagami or s['pominiete']:
        iface.messageBar().pushMessage(
            'PODMIANA ZAKOŃCZONA - SPRAWDŹ RAPORT',
            tresc + f'. Wydzieleń z uwagami do sprawdzenia: {z_uwagami}',
            Qgis.Warning, 0)
    else:
        iface.messageBar().pushMessage(
            'PODMIANA ZAKOŃCZONA', tresc, Qgis.Success, 0)
    return True
