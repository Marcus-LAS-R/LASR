"""Wspólny format zapisu/odczytu "waypointów" dla Nawigatora błędów.

Waypointy to lista błędów z raportów kontrolnych (Kontrola Ls, Kontrola
słownikowa SULMN) zapisana jako CSV, po której Nawigator błędów potrafi
skakać na mapie (patrz skrypty/nawigator_dock.py). Plik pełni też rolę
stanu roboczego - kolumny status/data_oznaczenia pozwalają przerwać
przeglądanie i wrócić do niego później.
"""
import csv
import os
import tempfile

NAGLOWEK = [
    'zrodlo', 'sekcja', 'typ_klucza', 'klucz', 'opis', 'status',
    'data_oznaczenia',
]


def wiersz(zrodlo, sekcja, typ_klucza, klucz, opis):
    """Buduje jeden świeży wiersz waypointów (bez oznaczenia)."""
    return {
        'zrodlo': zrodlo,
        'sekcja': sekcja,
        'typ_klucza': typ_klucza,
        'klucz': str(klucz),
        'opis': opis,
        'status': '',
        'data_oznaczenia': '',
    }


def zapisz(sciezka, wiersze):
    """Zapisuje listę wierszy do pliku CSV. Nadpisuje atomowo (plik
    tymczasowy w tym samym katalogu + podmiana), żeby przerwanie zapisu
    (np. zamknięcie QGIS) nie uszkodziło już istniejącego pliku."""
    kat = os.path.dirname(sciezka) or '.'
    fd, tmp_sc = tempfile.mkstemp(dir=kat, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as plik:
            writer = csv.DictWriter(plik, fieldnames=NAGLOWEK, delimiter=';')
            writer.writeheader()
            for w in wiersze:
                writer.writerow({k: w.get(k, '') for k in NAGLOWEK})
        os.replace(tmp_sc, sciezka)
    except Exception:
        if os.path.exists(tmp_sc):
            os.remove(tmp_sc)
        raise


def wczytaj(sciezka):
    """Wczytuje listę wierszy (dict) z pliku CSV zapisanego przez zapisz()."""
    with open(sciezka, 'r', newline='', encoding='utf-8') as plik:
        reader = csv.DictReader(plik, delimiter=';')
        return [dict(w) for w in reader]
