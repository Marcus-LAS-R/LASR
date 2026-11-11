# -*- coding: utf-8 -*-
"""Zapis atrybutów warstw przez bufor edycji warstwy (a nie wprost przez
dostawcę danych), żeby otwarte tabele atrybutów i inne widoki od razu
widziały zmiany.

Dlaczego: `lyr.dataProvider().changeAttributeValues(...)` zapisuje prosto do
pliku i nie wysyła sygnałów warstwy - tabela atrybutów (czyta z pamięci
podręcznej warstwy) pokazuje stare wartości do czasu ponownego otwarcia.
Zapis przez `lyr.changeAttributeValues(fid, ...)` w trybie edycji wysyła
sygnały i tabela odświeża się sama.

Dodatkowo skrypty często otwierają warstwę z pliku jako osobny obiekt
(`QgsVectorLayer(sciezka, ...)`), a nie biorą jej z projektu - wtedy tabela
otwarta na warstwie z projektu należy do innego obiektu i nie dostanie
sygnałów. `odswiez_powiazane()` przeładowuje warstwy projektu wskazujące na
ten sam plik.
"""
import os

from qgis.core import Qgis, QgsMessageLog, QgsProject


def _plik_zrodla(lyr):
    try:
        uri = lyr.dataProvider().dataSourceUri()
    except Exception:
        return None
    sc = uri.split('|')[0]
    if not sc or not os.path.exists(sc):
        return None
    return os.path.normcase(os.path.abspath(sc))


def odswiez_powiazane(lyr, takze_ta=False):
    """Przeładowuje warstwy projektu, które wskazują na ten sam plik co
    `lyr` (z pominięciem warstw w trybie edycji - przeładowanie nie może
    zgubić niezapisanych zmian użytkownika). Po przeładowaniu otwarte tabele
    atrybutów pokazują aktualne wartości z pliku.

    takze_ta=True - przeładuj też samą `lyr` (po zmianach zrobionych wprost
    przez dostawcę danych, np. truncate()+addFeatures())."""
    if takze_ta and not lyr.isEditable():
        lyr.reload()
        lyr.triggerRepaint()
    sc = _plik_zrodla(lyr)
    if sc is None:
        return
    for inna in QgsProject.instance().mapLayers().values():
        if inna is lyr or not hasattr(inna, 'isEditable'):
            continue
        if inna.isEditable() or _plik_zrodla(inna) != sc:
            continue
        inna.reload()
        inna.triggerRepaint()


def zmien_atrybuty(lyr, zmiany):
    """Zamiennik `lyr.dataProvider().changeAttributeValues(zmiany)` - ten sam
    format argumentu: {fid: {indeks_pola: wartosc}}.

    Zmiany idą przez bufor edycji warstwy i są od razu zatwierdzane (zapis
    na dysk - skrypty po zapisie często czytają plik, np. dissolve). Jeśli
    warstwa była już w trybie edycji, zatwierdzane są też wcześniejsze
    zmiany z bufora (tak jak przy dotychczasowym commitChanges() w
    skryptach), a warstwa wraca do trybu edycji. Na koniec przeładowuje
    inne warstwy projektu na tym samym pliku.

    Zwraca True/False (False - nie udało się włączyć edycji albo zatwierdzić
    zmian; szczegóły w logu Las-R, zmiany wycofane)."""
    if not zmiany:
        return True

    byla_w_edycji = lyr.isEditable()
    if not byla_w_edycji and not lyr.startEditing():
        QgsMessageLog.logMessage(
            f'zmien_atrybuty: nie można włączyć edycji warstwy {lyr.name()}',
            'Las-R', Qgis.Critical)
        return False

    ok = True
    for fid, atrybuty in zmiany.items():
        if not lyr.changeAttributeValues(fid, atrybuty):
            ok = False

    if not lyr.commitChanges(not byla_w_edycji):
        QgsMessageLog.logMessage(
            f'zmien_atrybuty: błąd zapisu warstwy {lyr.name()}: '
            + '; '.join(lyr.commitErrors()), 'Las-R', Qgis.Critical)
        lyr.rollBack(not byla_w_edycji)
        return False

    odswiez_powiazane(lyr)
    return ok
