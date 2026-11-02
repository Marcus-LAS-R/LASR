# -*- coding: utf-8 -*-
"""Kopie manipulacyjne jako ZIP-y - jedna kopia to jeden plik, także gdy
obejmuje bazę razem z warstwą. Bazy pakują się do ok. 10% rozmiaru w ułamku
sekundy (poziom 6: wyraźnie lepszy stosunek zysku do czasu niż 9 i LZMA, a ZIP
otworzy się w Eksploratorze na każdym komputerze). Bez QGIS-a."""
import os
import shutil
import zipfile

POZIOM = 6


def spakuj(sciezka_zip, pliki):
    """Tworzy ZIP z [(ścieżka źródła, nazwa w ZIP-ie)]. Przez plik tymczasowy
    i z kontrolą sum: na miejscu docelowym pojawia się tylko sprawdzony ZIP.
    Błąd leci do wywołującego - bez kopii operacja nie może ruszyć."""
    tymczasowy = sciezka_zip + '.tmp'
    try:
        with zipfile.ZipFile(tymczasowy, 'w', zipfile.ZIP_DEFLATED,
                             compresslevel=POZIOM, allowZip64=True) as zf:
            for zrodlo, nazwa in pliki:
                zf.write(zrodlo, nazwa)
        with zipfile.ZipFile(tymczasowy) as zf:
            zly = zf.testzip()
            if zly is not None:
                raise zipfile.BadZipFile(f'uszkodzony plik w kopii: {zly}')
        os.replace(tymczasowy, sciezka_zip)
    except BaseException:
        if os.path.exists(tymczasowy):
            os.remove(tymczasowy)
        raise
    return sciezka_zip


def wypakuj_plik(sciezka_zip, nazwa, cel):
    """Przywraca jeden plik z kopii (nadpisuje cel)."""
    with zipfile.ZipFile(sciezka_zip) as zf, zf.open(nazwa) as zr, \
            open(cel, 'wb') as doc:
        shutil.copyfileobj(zr, doc)
