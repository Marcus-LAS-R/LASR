"""Konwerter bazy PUL -> UPUL (Lasy Państwowe -> lasy prywatne/gminne).

Adres leśny (F_ARODES.ADRESS_FOREST) jest wyznaczany na nowo, bo REG_CD/
INS_CD (RDLP/Nadleśnictwo) źródła PUL bywają błędne (np. wpisane ręcznie
przez pracownika) - NIE są kopiowane wprost. Warstwa wydzieleń jest
WYŁĄCZNIE lokalizatorem geometrycznym (założenie: całe nadleśnictwo/
leśnictwo leży w jednym obrębie ewidencyjnym) - jej atrybuty (ODDZ/WYDZ/
GRP) nie są używane w ogóle. Jeden wspólny adres administracyjny (MUNICIP/
COMMUNITY/nazwa) jest wyznaczany geometrycznie z całej tej warstwy
względem warstwy obrębów ewidencyjnych (core/spatial_match.py), a ODDZ/
WYDZ (litera wydzielenia) dla każdego wydzielenia pochodzą z parsowania
adresu źródłowego PUL (core/adres.rozbierz_adres_pul). Reszta danych
(F_PARCEL/V_ADDRESS/dane taksacyjne) jest strukturalnie niemal identyczna
w obu formatach i kopiowana generycznie przez Laczenie (baza_polacz.py).

Kierunek UPUL->PUL nie jest jeszcze zaimplementowany - core/adres.py i
core/spatial_match.py są już na tyle generyczne, żeby go dodać bez zmian
w silniku kopiowania (core/kopia_pul_upul.py), patrz komentarze tamże.
"""

import os

from PyQt5.QtWidgets import QDialog
from qgis.core import Qgis, QgsVectorLayer

from ..baza_wrapper import Baza
from ..pw import PasekPostepu
from ..baza_kontrola_slownikow_wgSULMN import KontrolaSlownikowWiele

from .gui.dialog import KonwersjaPulUpulDialog
from .core.dopasuj_arodes import zbuduj_slownik_arodes_pul
from .core.spatial_match import dopasuj_administracje, klucz_teryt_z_obreb
from .core.kopia_pul_upul import KopiaPULdoUPUL
from .core.raport import zapisz_raport_konfliktow, zapisz_raport_konwersji


def uruchom(iface):
    dlg = KonwersjaPulUpulDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False
    return _uruchom_konwersje(iface, dlg.wybor())


def _blad(iface, tekst):
    iface.messageBar().clearWidgets()
    iface.messageBar().pushMessage('BŁĄD', tekst, Qgis.Critical, 0)


def _uruchom_konwersje(iface, wybor):  # noqa
    baza_pul_sc = wybor['baza_pul_sc']
    cel_sc = wybor['cel_sc']
    katalog_raportow = (
        os.path.dirname(cel_sc) or os.path.dirname(baza_pul_sc))

    wydz_lyr = QgsVectorLayer(wybor['wydz_sc'], 'wydz', 'ogr')
    obreby_lyr = QgsVectorLayer(wybor['obreby_sc'], 'obreby', 'ogr')

    if not wydz_lyr.isValid():
        _blad(iface, 'Nie udało się wczytać warstwy wydzieleń.')
        return False
    if not obreby_lyr.isValid():
        _blad(iface, 'Nie udało się wczytać warstwy obrębów ewidencyjnych.')
        return False

    postep = PasekPostepu(iface).stworz_pasek('Konwersja PUL → UPUL')
    postep.setValue(0)

    baza_pul = Baza(baza_pul_sc)
    if not baza_pul.polacz():
        _blad(iface, 'Nie udało się połączyć z bazą PUL (źródłową).')
        return False

    # 1. Precheck kolizji (ODDZ,WYDZ) - blokuje całą konwersję. ODDZ/WYDZ
    # pochodzą z TEMP_ADRESS_FOREST (tylko wydzielenia z TEMP_ACT_ADRESS
    # ='1'), więc para musi być jednoznaczna w całej bazie źródłowej,
    # żeby dwa różne wydzielenia (z różnych obrębów leśnych/leśnictw) nie
    # dostały tego samego nowego adresu UPUL.
    slownik_arodes_pul, konflikty, liczba_nieaktywnych = \
        zbuduj_slownik_arodes_pul(baza_pul)
    if konflikty:
        baza_pul.zamknij()
        rap_sc = zapisz_raport_konfliktow(katalog_raportow, konflikty)
        _blad(
            iface,
            'Znaleziono ' + str(len(konflikty)) + ' kolidujących par '
            '(ODDZ,WYDZ) w bazie źródłowej - konwersja przerwana. '
            'Raport: ' + rap_sc)
        return False
    if not slownik_arodes_pul:
        baza_pul.zamknij()
        _blad(
            iface,
            'Baza PUL nie zawiera żadnych aktywnych wydzieleń (F_ARODES, '
            "ARODES_TYP_CD='WYDZIEL', TEMP_ACT_ADRESS='1') - pominięto " +
            str(liczba_nieaktywnych) + ' nieaktywnych.')
        return False

    postep.setValue(10)

    # 2. JEDEN adres administracyjny dla całej warstwy wydzieleń (nie per
    # poligon) - warstwa jest wyłącznie lokalizatorem geometrycznym.
    dopasowanie = dopasuj_administracje(
        wydz_lyr, obreby_lyr, klucz_teryt_z_obreb, postep)
    if dopasowanie.klucz_teryt is None:
        baza_pul.zamknij()
        _blad(
            iface,
            'Warstwa wydzieleń nie pokrywa się z żadnym obrębem '
            'ewidencyjnym z wskazanej warstwy - nie da się wyznaczyć '
            'adresu administracyjnego, konwersja przerwana.')
        return False

    postep.setValue(40)

    # 3. Połączenie z bazą docelową - dane ładowane wprost do niej (bez
    # pośredniego kopiowania do osobnego pliku)
    baza0 = Baza(cel_sc)
    if not baza0.polacz():
        baza_pul.zamknij()
        _blad(iface, 'Nie udało się połączyć z bazą docelową.')
        return False

    postep.setValue(50)

    # 4. Kopiowanie - F_ARODES/F_COMMUNITY z jednego wspólnego adresu
    # administracyjnego + ODDZ/WYDZ z adresu PUL, reszta (F_PARCEL/
    # V_ADDRESS/dane taksacyjne) generycznie przez Laczenie
    kopia = KopiaPULdoUPUL(baza0, baza_pul)
    kopia.p_f_max()
    kopia.p_f_community(dopasowanie)
    kopia.p_f_arodes(slownik_arodes_pul, dopasowanie)
    kopia.p_pozostale_nadrzedne()
    kopia.p_tabele()
    kopia.d_tabele()

    postep.setValue(90)

    baza0.zamknij()
    baza_pul.zamknij()

    rap_sc = zapisz_raport_konwersji(
        katalog_raportow,
        {'Baza PUL (źródłowa)': baza_pul_sc,
         'Warstwa wydzieleń': wybor['wydz_sc'],
         'Warstwa obrębów ewidencyjnych': wybor['obreby_sc'],
         'Baza docelowa': cel_sc},
        kopia, dopasowanie, len(slownik_arodes_pul), liczba_nieaktywnych)

    iface.messageBar().clearWidgets()
    _podsumuj(
        iface, kopia, dopasowanie, len(slownik_arodes_pul),
        liczba_nieaktywnych, rap_sc)

    # 5. Kontrola słownikowa końcowa (informacyjna, nieblokująca)
    ile_blednych, rap_slow = KontrolaSlownikowWiele(
        katalog_raportow, [cel_sc])
    if ile_blednych > 0:
        iface.messageBar().pushMessage(
            'Kontrola słownikowa',
            'W bazie wynikowej znaleziono ' + str(ile_blednych) +
            ' wartości spoza słownika. Raport: ' + rap_slow,
            Qgis.Warning, 0)
    else:
        iface.messageBar().pushMessage(
            'Kontrola słownikowa',
            'Baza wynikowa zgodna ze słownikiem, raport: ' + rap_slow,
            Qgis.Success, 10)

    return True


def _podsumuj(iface, kopia, dopasowanie, liczba_wydzielen_pul,
               liczba_nieaktywnych, rap_sc):
    iface.messageBar().clearWidgets()
    skopiowane = len(kopia.sl_arodes)
    bez_adresu = len(kopia.l_bez_adresu)
    bledy = len(kopia.l_bledy_wpisu) + len(kopia.l_bledy_odczytu)
    nieaktywne = (
        ' (pominięto też ' + str(liczba_nieaktywnych) +
        ' z TEMP_ACT_ADRESS≠1)' if liczba_nieaktywnych else '')

    if bledy:
        iface.messageBar().pushMessage(
            'KONWERSJA Z BŁĘDAMI',
            'Skopiowano ' + str(skopiowane) + '/' + str(liczba_wydzielen_pul) +
            ' aktywnych wydzieleń' + nieaktywne + ', ' + str(bledy) +
            ' błędów zapisu/odczytu. Raport: ' + rap_sc,
            Qgis.Warning, 0)
    elif bez_adresu:
        iface.messageBar().pushMessage(
            'KONWERSJA CZĘŚCIOWA',
            'Skopiowano ' + str(skopiowane) + '/' + str(liczba_wydzielen_pul) +
            ' aktywnych wydzieleń' + nieaktywne + ', ' + str(bez_adresu) +
            ' pominiętych. Raport: ' + rap_sc,
            Qgis.Warning, 0)
    elif dopasowanie.status == 'graniczne':
        iface.messageBar().pushMessage(
            'KONWERSJA ZAKOŃCZONA (z ostrzeżeniem)',
            'Skopiowano wszystkie ' + str(skopiowane) +
            ' aktywnych wydzieleń' + nieaktywne + ', ale dopasowanie do '
            'obrębu ewidencyjnego jest graniczne (' +
            '{:.0%}'.format(dopasowanie.udzial) + ') - zweryfikuj adres '
            'administracyjny ręcznie. Raport: ' + rap_sc,
            Qgis.Warning, 10)
    else:
        iface.messageBar().pushMessage(
            'KONWERSJA ZAKOŃCZONA',
            'Skopiowano wszystkie ' + str(skopiowane) +
            ' aktywnych wydzieleń' + nieaktywne + '. Raport: ' + rap_sc,
            Qgis.Success, 10)
