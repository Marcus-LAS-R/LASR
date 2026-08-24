"""Budowa i zapis raportów konwersji PUL -> UPUL, wzorem
raport_aktualizacji_struktury_*.txt (baza_aktualizuj_strukture.py)."""

import os
from datetime import datetime


def zapisz_raport_konfliktow(katalog, konflikty):
    """konflikty: {(oddz,wydz): [(obreb_lesny,lesnictwo,arodes_int_num,
    adres_pelny), ...]}. Zwraca ścieżkę raportu."""
    czas = datetime.now().isoformat().replace(':', '')[:-7]
    rap_sc = os.path.join(katalog, 'konflikty_oddz_wydz_' + czas + '.txt')

    with open(rap_sc, 'w', encoding='utf-8') as plik:
        plik.write('KONWERSJA PUL -> UPUL - KONFLIKTY KLUCZA (ODDZ,WYDZ)\r\n')
        plik.write(
            'Ta sama para (oddział,wydzielenie) występuje w więcej niż '
            'jednym obrębie leśnym/leśnictwie źródła - konwersja przerwana, '
            'popraw dane u źródła (np. dopisz rozróżnienie do warstwy '
            'wydzieleń) i uruchom ponownie.\r\n')
        plik.write('=' * 72 + '\r\n\r\n')
        for (oddz, wydz), warianty in sorted(konflikty.items()):
            plik.write('ODDZ=' + oddz + ' WYDZ=' + wydz + ':\r\n')
            for obreb_lesny, lesnictwo, arodes_int_num, adres in warianty:
                plik.write(
                    '   obręb leśny=' + obreb_lesny + ' leśnictwo=' +
                    lesnictwo + ' ARODES_INT_NUM=' + str(arodes_int_num) +
                    ' adres=' + adres + '\r\n')
            plik.write('\r\n')

    return rap_sc


def zapisz_raport_konwersji(katalog, parametry, kopia, dopasowanie_administracji,
                             liczba_wydzielen_pul, liczba_nieaktywnych=0):
    """kopia: obiekt KopiaPULdoUPUL po zakończonym przebiegu.
    dopasowanie_administracji: DopasowanieAdministracji, wspólny dla całej
    warstwy wydzieleń (patrz spatial_match.dopasuj_administracje) -
    ODDZ/WYDZ każdego wydzielenia pochodzą z adresu PUL (TEMP_ADRESS_FOREST),
    nie z tej warstwy. liczba_nieaktywnych: ile wydzieleń źródła PUL
    pominięto z powodu TEMP_ACT_ADRESS != '1'. Zwraca ścieżkę raportu."""
    czas = datetime.now().isoformat().replace(':', '')[:-7]
    rap_sc = os.path.join(katalog, 'raport_konwersji_pul_upul_' + czas + '.txt')

    with open(rap_sc, 'w', encoding='utf-8') as plik:
        plik.write('KONWERSJA PUL -> UPUL - RAPORT\r\n')
        plik.write('=' * 72 + '\r\n\r\n')

        plik.write('Parametry uruchomienia:\r\n')
        for nazwa, wartosc in parametry.items():
            plik.write('  ' + nazwa + ': ' + str(wartosc) + '\r\n')
        plik.write('\r\n')

        plik.write(
            'Adres administracyjny wyznaczony z geometrii warstwy '
            'wydzieleń: ' + str(dopasowanie_administracji.klucz_teryt) +
            ' "' + dopasowanie_administracji.nazwa_obrebu + '" (udział '
            'powierzchni: ' + '{:.1%}'.format(dopasowanie_administracji.udzial) +
            ')')
        if dopasowanie_administracji.status == 'graniczne':
            plik.write(
                ' - GRANICZNE (< 98%), warstwa wydzieleń zahacza o więcej '
                'niż jeden obręb ewidencyjny - zweryfikuj ręcznie, czy '
                'wybrany obręb jest właściwy dla całej partii.')
        plik.write('\r\n\r\n')

        if kopia.l_bez_adresu:
            plik.write(
                'Wydzielenia BEZ adresu (nieskopiowane w ogóle): ' +
                str(len(kopia.l_bez_adresu)) + '\r\n')
            for _oddz, _wydz, powod in kopia.l_bez_adresu:
                plik.write('  ' + powod + '\r\n')
            plik.write('\r\n')

        plik.write('Tabele bez odpowiednika w PUL:\r\n')
        if kopia.wlasciciel_wpisany:
            plik.write(
                '  V_ADDRESS: wpisano "Skarb Państwa"\r\n'
                '  V_PARCEL_PARTICIPATION: wpisano 1/1 dla ' +
                str(kopia.l_wlasciciel_udzialy) + ' działek\r\n')
        else:
            plik.write(
                '  V_ADDRESS / V_PARCEL_PARTICIPATION: pominięto (brak '
                'skopiowanych działek F_PARCEL)\r\n')
        plik.write(
            '  F_AROD_DAMAGE: pominięto (brak odpowiednika 1:1 w PUL - '
            'dane o uszkodzeniach są tam rozproszone w innych tabelach)\r\n')
        plik.write('\r\n')

        if kopia.l_kolumny_pominiete:
            plik.write(
                'Kolumny bez odpowiednika w źródle (pozostały puste w '
                'bazie wynikowej):\r\n')
            for tabela, kolumny in kopia.l_kolumny_pominiete.items():
                plik.write(
                    '  ' + tabela + ': ' + ', '.join(sorted(kolumny)) +
                    '\r\n')
            plik.write('\r\n')

        if kopia.l_bledy_wpisu or kopia.l_bledy_odczytu:
            plik.write('BŁĘDY:\r\n\r\n')
            for tabela, opis_wiersza, blad in kopia.l_bledy_wpisu:
                plik.write('Tabela: ' + tabela + '\r\n')
                plik.write('Wiersz: ' + opis_wiersza + '\r\n')
                plik.write('Błąd:   ' + blad + '\r\n\r\n')
            for baza_sc, tabela, blad in kopia.l_bledy_odczytu:
                plik.write('Baza:   ' + baza_sc + '\r\n')
                plik.write('Tabela: ' + tabela + '\r\n')
                plik.write('Błąd:   ' + blad + '\r\n\r\n')

        plik.write('Podsumowanie:\r\n')
        plik.write(
            '  Aktywnych wydzieleń w bazie źródłowej PUL '
            "(TEMP_ACT_ADRESS='1'): " + str(liczba_wydzielen_pul) + '\r\n')
        plik.write(
            '  Pominiętych jako nieaktywne (TEMP_ACT_ADRESS!=\'1\'): ' +
            str(liczba_nieaktywnych) + '\r\n')
        plik.write(
            '  Skopiowanych do bazy wynikowej: ' + str(len(kopia.sl_arodes)) +
            '\r\n')
        plik.write(
            '  Bez adresu: ' + str(len(kopia.l_bez_adresu)) + '\r\n')

    return rap_sc
