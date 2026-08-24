"""Słownik {(oddz,wydz): stary ARODES_INT_NUM} bazy źródłowej PUL -
jedyny dostępny klucz łączący geometrię wydzielenia (warstwa SHP ma tylko
pola ODDZ+WYDZ, bez obrębu leśnego/leśnictwa) z konkretnym wierszem
F_ARODES źródła. zbuduj_slownik_arodes_pul() zwraca też konflikty (ta sama
para w >1 obrębie leśnym/leśnictwie źródła) - te BLOKUJĄ całą konwersję,
zamiast być zgadywane (patrz plan: precheck kolizji kluczy).

Adres brany jest z TEMP_ADRESS_FOREST (nie ADRESS_FOREST) i tylko dla
wydzieleń z TEMP_ACT_ADRESS='1' (checkbox "aktywny adres" w bazie PUL) -
na wyraźne życzenie użytkownika. Zweryfikowane na materialy/PUL/
RZI_Wroclaw_Pstraze_2026_08_23.mdb: 5 wydzieleń (a,b,c,d,f) w F_ARODES,
tylko a i b mają TEMP_ACT_ADRESS='1'.
"""

from .adres import rozbierz_adres_pul


def _jest_aktywny(wartosc):
    """TEMP_ACT_ADRESS to pole Yes/No (Access) - pyodbc zwraca je jako
    Python bool (True/False), NIE jako string '1'/'0' (zweryfikowane na
    materialy/PUL/RZI_Wroclaw_Pstraze_2026_08_23.mdb) - stąd rozróżnienie
    typu zamiast prostego porównania stringów."""
    if isinstance(wartosc, bool):
        return wartosc
    return str(wartosc).strip() in ('1', 'T', 'True', '-1')


def zbuduj_slownik_arodes_pul(baza_pul):
    """Zwraca (slownik, konflikty, liczba_nieaktywnych).

    slownik: {(oddz,wydz): arodes_int_num} - tylko dla par bez kolizji,
    tylko wydzielenia z TEMP_ACT_ADRESS='1'.
    konflikty: {(oddz,wydz): [(obreb_lesny,lesnictwo,arodes_int_num,
    adres_pelny), ...]} - tylko dla par występujących >1 raz w źródle
    (liczone wyłącznie wśród aktywnych wydzieleń).
    liczba_nieaktywnych: ile wydzieleń pominięto z powodu
    TEMP_ACT_ADRESS != '1' (do raportu/podsumowania).
    """
    wiersze = baza_pul.pobierz(
        "select TEMP_ADRESS_FOREST, ARODES_INT_NUM, TEMP_ACT_ADRESS "
        "from F_ARODES where ARODES_TYP_CD = 'WYDZIEL';")
    if wiersze is False:
        return {}, {}, 0

    grupy = {}
    liczba_nieaktywnych = 0
    for adr, arodes_int_num, aktywny in wiersze:
        if not _jest_aktywny(aktywny):
            liczba_nieaktywnych += 1
            continue
        rozbite = rozbierz_adres_pul(adr)
        if rozbite is None:
            continue
        klucz = (rozbite['oddz'], rozbite['wydz'])
        grupy.setdefault(klucz, []).append(
            (rozbite['obreb_lesny'], rozbite['lesnictwo'], arodes_int_num, adr))

    slownik = {}
    konflikty = {}
    for klucz, warianty in grupy.items():
        if len(warianty) == 1:
            slownik[klucz] = warianty[0][2]
        else:
            konflikty[klucz] = warianty
    return slownik, konflikty, liczba_nieaktywnych
