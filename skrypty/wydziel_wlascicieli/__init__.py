"""Wydziel właścicieli do nowej bazy.

Eksportuje zaznaczonych właścicieli (V_ADDRESS) - wraz ze wszystkimi
współwłaścicielami z ich grup rejestrowych (F_PARCEL.LAND_REGISTER_NR) - z
bazy źródłowej do już istniejącej bazy docelowej, opcjonalnie z opisem
taksacyjnym (F_ARODES i tabele-dzieci) i/lub grafiką (DZKAT/LS/WYDZ/PNSW),
opcjonalnie usuwając wyeksportowane dane ze źródła. Kopia bezpieczeństwa
bazy (i, jeśli dotyczy, warstw SHP źródłowych) powstaje raz, zanim
cokolwiek zostanie zmienione w źródle - przed samym eksportem, nie dopiero
przed uprzątnięciem.
"""

import os

from PyQt5.QtWidgets import QDialog, QMessageBox
from qgis.core import Qgis, QgsProject, QgsVectorLayer

from ..baza_wrapper import Baza
from ..pw import PasekPostepu
from .. import kopie_manipulacyjne

from .gui.dialog import WydzielWlascicieliDialog
from .core import eksport

# style do wizualnej kontroli wydzieleń mieszanych (patrz _uruchom_eksport) -
# wskazane przez użytkownika, poza katalogiem wtyczki
_STYL_DZIALKI_WLASCIWE = (
    r'C:\Praca\Podrecznik\Do_QGIS\QGIS style\_NOWE\WYDZ_z_wieloma_kartami.qml')
_STYL_DZIALKI_OBCE = (
    r'C:\Praca\Podrecznik\Do_QGIS\QGIS style\_NOWE\WYDZ_bez_kart.qml')


def _blad(iface, tekst):
    iface.messageBar().clearWidgets()
    iface.messageBar().pushMessage('BŁĄD', tekst, Qgis.Critical, 0)


def _dodaj_warstwe_ze_stylem(sciezka, nazwa, styl_sc):
    lyr = QgsVectorLayer(sciezka, nazwa, 'ogr')
    if not lyr.isValid():
        return
    if os.path.isfile(styl_sc):
        lyr.loadNamedStyle(styl_sc)
    QgsProject.instance().addMapLayer(lyr)


def uruchom(iface):
    dlg = WydzielWlascicieliDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        baza = dlg.zrodlo_baza()
        if baza is not None:
            baza.zamknij()
        return False

    wybor = dlg.wybor()
    baza = dlg.zrodlo_baza()
    return _uruchom_eksport(iface, baza, wybor)


def _potwierdz_mieszane(iface, mieszane):
    """Wydzielenie to jednostka gospodarki leśnej niezależna od granic
    własności - może obejmować działki z różnych grup rejestrowych
    (F_PARCEL.LAND_REGISTER_NR). Pokazuje same liczniki (szczegóły -
    adresy i PARCELID - trafiają do raportu txt tylko przy "Nie", patrz
    zapisz_raport_wydzielen_mieszanych) i pyta czy mimo to kontynuować.
    Zwraca True (kontynuuj) / False (przerwij)."""
    liczba_dzialek = len({p for _, obce, _ in mieszane for p in obce})
    tresc = (
        f'Wykryto {len(mieszane)} wydzieleń zawierających łącznie '
        f'{liczba_dzialek} działek, które nie powinny się w nich znaleźć '
        '(należą do innej grupy rejestrowej niż eksportowany właściciel).\n\n'
        'Jeśli wybierzesz "Nie", powstanie raport txt ze szczegółami '
        '(adres leśny i PARCELID działek do rozdzielenia).\n\n'
        'Jeśli będziesz kontynuować, opis tych wydzieleń zostanie '
        'wyeksportowany/usunięty w całości, razem z cudzą działką.\n'
        'Kontynuować mimo to?'
    )

    odp = QMessageBox.question(
        iface.mainWindow(), 'Wykryto wydzielenia mieszane', tresc,
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    return odp == QMessageBox.Yes


def _wczytaj_warstwy_shp(folder):
    warstwy = []
    for nazwa in ('DZKAT', 'LS', 'WYDZ', 'PNSW'):
        sc = os.path.join(folder, nazwa + '.shp')
        if os.path.isfile(sc):
            warstwy.append(QgsVectorLayer(sc, nazwa, 'ogr'))
    return warstwy


def _uruchom_eksport(iface, baza, wybor):  # noqa
    addr_wybrani = wybor['addr_wybrani']
    cel_sc = wybor['cel_sc']
    opcja_opisy = wybor['opcja_opisy']
    opcja_grafika = wybor['opcja_grafika']
    opcja_uprzatnij = wybor['opcja_uprzatnij']
    folder_shp = wybor['folder_shp']

    baza0 = Baza(cel_sc)
    if not baza0.polacz():
        baza.zamknij()
        _blad(iface, 'Nie udało się połączyć z bazą docelową.')
        return False

    postep = PasekPostepu(iface).stworz_pasek('Wydziel właścicieli do nowej bazy')
    postep.setValue(0)

    addr_final, parcels_final = eksport.policz_zbior_eksportu(baza, addr_wybrani)
    if not parcels_final:
        baza.zamknij()
        baza0.zamknij()
        _blad(iface, 'Zaznaczeni właściciele nie mają żadnych działek w '
              'bazie źródłowej - przerwano.')
        return False

    arodes_wszystkie = eksport.policz_arodes_wydziel(baza, parcels_final)
    arodes_opisy = arodes_wszystkie if opcja_opisy else set()

    # --- kontrola grup rejestrowych - PRZED jakąkolwiek zmianą w źródle ---
    grupy_dozwolone = eksport.policz_grupy_rejestrowe_wlasciciela(baza, addr_wybrani)
    mieszane = eksport.policz_wydzielenia_mieszane(
        baza, arodes_wszystkie, grupy_dozwolone)
    if mieszane and not _potwierdz_mieszane(iface, mieszane):
        katalog_zrodla = os.path.dirname(baza.baza)
        rap_sc = eksport.zapisz_raport_wydzielen_mieszanych(katalog_zrodla, mieszane)
        komunikat = ('Przerwano - nic nie zmieniono. Wydzielenia do '
                     'rozdzielenia przed ponownym uruchomieniem: ' + rap_sc)

        if folder_shp:
            warstwy = eksport.zapisz_warstwy_wydzielen_mieszanych(
                folder_shp, os.path.join(katalog_zrodla, 'SHP'), mieszane)
            if warstwy.get('Dzialki_wlasciwe'):
                _dodaj_warstwe_ze_stylem(
                    warstwy['Dzialki_wlasciwe'], 'Dzialki_wlasciwe',
                    _STYL_DZIALKI_WLASCIWE)
            if warstwy.get('Dzialki_obce'):
                _dodaj_warstwe_ze_stylem(
                    warstwy['Dzialki_obce'], 'Dzialki_obce', _STYL_DZIALKI_OBCE)
            if any(warstwy.values()):
                komunikat += '. Warstwy SHP: ' + os.path.join(katalog_zrodla, 'SHP')

        baza.zamknij()
        baza0.zamknij()
        _blad(iface, komunikat)
        return False

    # klucze do dopasowania grafiki - policzone TERAZ (baza źródłowa jeszcze
    # nietknięta), żeby uprzątnięcie (które usuwa F_PARCEL/F_ARODES) nie
    # sprawiło, że te same zapytania zwrócą później pusty zbiór
    klucze_dzialek = adresy_wydz = None
    if opcja_grafika and folder_shp:
        klucze_dzialek = eksport.policz_klucze_dzialek(baza, parcels_final)
        adresy_wydz = eksport.policz_adresy_wydz(baza, arodes_wszystkie)

    postep.setValue(10)

    # --- kopia bezpieczeństwa - PRZED jakąkolwiek zmianą w źródle ---
    warstwy_do_kopii = _wczytaj_warstwy_shp(folder_shp) if (
        opcja_grafika and folder_shp) else []
    folder_kopii = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
        baza.baza, warstwy_do_kopii, 'wydziel_wlascicieli')
    if folder_kopii is None:
        baza.zamknij()
        baza0.zamknij()
        _blad(iface, 'Nie udało się utworzyć kopii bezpieczeństwa - '
              'przerwano, nic nie zmieniono.')
        return False

    postep.setValue(20)

    # --- eksport do bazy docelowej ---
    ekst = eksport.EksportWlascicieli(baza0, baza, opcja_opisy)
    ekst.p_f_max()
    if opcja_opisy:
        ekst.p_f_arodes(arodes_opisy)
    ekst.p_f_community()
    ekst.p_pozostale_nadrzedne(parcels_final, addr_final)
    ekst.p_tabele()
    ekst.d_tabele()

    postep.setValue(60)

    # --- raport końcowy - PRZED uprzątnięciem, które kasuje dane z niego ---
    arodes_raport = arodes_opisy if opcja_opisy else (
        arodes_wszystkie if opcja_grafika else set())
    rap_eksportu = eksport.zapisz_raport_eksportu(
        os.path.dirname(baza.baza), baza, addr_wybrani, addr_final,
        parcels_final, arodes_raport)

    # --- grafika ---
    ile_shp_eksport = {}
    if opcja_grafika and folder_shp:
        folder_docelowy = os.path.join(
            os.path.dirname(cel_sc), 'SHP_eksport_wlascicieli')
        ile_shp_eksport = eksport.eksportuj_grafike(
            folder_shp, folder_docelowy, klucze_dzialek, adresy_wydz)

    postep.setValue(80)

    # --- uprzątnięcie źródła ---
    ile_shp_usuniete = {}
    if opcja_uprzatnij:
        if not eksport.uprzatnij_baze(baza, parcels_final, arodes_opisy, addr_final):
            baza.zamknij()
            baza0.zamknij()
            _blad(iface, 'Eksport zakończony, ale uprzątnięcie bazy '
                  'źródłowej nie powiodło się w trakcie - część danych '
                  'mogła już zostać usunięta zanim wystąpił błąd. Sprawdź '
                  'log Las-R i w razie wątpliwości przywróć kopię '
                  'zapasową: ' + folder_kopii)
            return False
        if opcja_grafika and folder_shp:
            ile_shp_usuniete = eksport.uprzatnij_shp(
                folder_shp, klucze_dzialek, adresy_wydz)
            iface.mapCanvas().refreshAllLayers()

    postep.setValue(100)

    baza.zamknij()
    baza0.zamknij()

    bledy = len(ekst.l_bledy_wpisu) + len(ekst.l_bledy_odczytu)
    iface.messageBar().clearWidgets()
    tresc = (
        'Wyeksportowano {addr}/{addr_z} właścicieli ({wsp} współwłaścicieli), '
        '{dz} działek'
    ).format(
        addr=len(addr_final), addr_z=len(addr_wybrani),
        wsp=len(addr_final) - len(addr_wybrani), dz=len(parcels_final))
    if opcja_opisy:
        tresc += ', {w} wydzieleń'.format(w=len(arodes_opisy))
    if ile_shp_eksport:
        tresc += '. Grafika: ' + ', '.join(
            f'{k}={v}' for k, v in ile_shp_eksport.items())
    if ile_shp_usuniete:
        tresc += '. Usunięto z SHP źródłowych: ' + ', '.join(
            f'{k}={v}' for k, v in ile_shp_usuniete.items())
    tresc += '. Kopia zapasowa: ' + folder_kopii + '. Raport: ' + rap_eksportu

    if bledy:
        iface.messageBar().pushMessage(
            'EKSPORT Z BŁĘDAMI',
            tresc + f'. Wystąpiło {bledy} błędów odczytu/zapisu - sprawdź log Las-R.',
            Qgis.Warning, 0)
    else:
        iface.messageBar().pushMessage('EKSPORT ZAKOŃCZONY', tresc, Qgis.Success, 0)

    return True
