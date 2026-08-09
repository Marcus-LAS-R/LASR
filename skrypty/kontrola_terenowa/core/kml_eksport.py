"""Eksport KML dla materiałów do kontroli terenowej - cienka otoczka na
shp_eksport_kml.EksportujKML (dokładnie ta sama logika co istniejące
polecenie menu "Wyeksportuj do KML", ŁĄCZNIE z podziałem na paczki po
1999 obiektów w zapisz_cz() - KML/Google Earth ma twardy limit liczby
obiektów w jednym pliku, więc tej granicy nie wolno przy okazji
"uproszczeń" zgubić).

Uruchamiane dla warstw OBR, kontrolowanych wydzieleń i DZKAT_kontrola
(patrz core/przetworz.py) - bez grupowania per baza - wynik trafia do
jednego wspólnego katalogu "kml" utworzonego w katalogu docelowym (a nie
osobno przy każdej bazie .mdb).
"""

from ...shp_eksport_kml import EksportujKML


def eksportuj_warstwy(iface, warstwy, katalog_docelowy):
    """warstwy: lista (layer, nazwa) do przetworzenia. Zwraca listę
    opisów błędów (pusta lista = wszystko OK)."""
    bledy = []
    for layer, nazwa in warstwy:
        eksporter = EksportujKML(iface)
        eksporter.ls = layer
        eksporter.nazwa = nazwa
        eksporter.kat = katalog_docelowy
        try:
            eksporter.przetworz()
            eksporter.zapisz_kml()
        except Exception as e:  # nopep8
            bledy.append(
                'Błąd eksportu KML dla warstwy ' + nazwa + ': ' + str(e))
    return bledy
