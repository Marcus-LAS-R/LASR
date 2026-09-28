"""Raporty TXT trzymane obok bazy - na wierzchu tylko najnowszy z rodziny.

Raporty z przygotowania i kontroli Ls/DZKAT, rozliczenia powierzchni oraz
zabiegów leżą obok bazy (nie w Raporty - tam trafiają pozostałe raporty
i waypointy CSV, patrz waypointy.katalog_raportow). Raport z przygotowania
i z kontroli tej samej warstwy to jedna rodzina - kontrola zastępuje
pierwotny raport z przygotowania. Po zapisaniu nowego raportu starsze
z tej samej rodziny przenoszone są do Raporty/Archiwum.

Raport otwarty w programie, który blokuje plik (np. Word), zostaje na
miejscu - bez obejść (kopii, zmiany nazwy); użytkownik dostaje komunikat.
Notatnik/Notepad++ nie blokują pliku, więc taki raport zostanie
przeniesiony.
"""
import os

from qgis.core import Qgis

from .waypointy import katalog_raportow

# rodzina -> przedrostki nazw plików raportów
RODZINY = {
    'LS': ('ls_raport_', 'ls_kontrola_'),
    'DZKAT': ('dzkat_raport_', 'dzkat_kontrola_'),
    'ROZLICZENIE': ('raport_rozliczPow_', 'raport_spr_rozliczPow_'),
    'ZABIEGI': ('raport_zabiegi_',),
}


def archiwizuj_starsze(nowy_raport, rodzina, iface=None):
    """Przenosi do <katalog raportu>/Raporty/Archiwum raporty TXT tej samej
    rodziny leżące obok nowego raportu i nie nowsze od niego (porównanie
    daty modyfikacji). Zwraca listę plików, których nie udało się
    przenieść (zablokowane - np. otwarte w edytorze); gdy podano iface -
    komunikat w pasku."""
    katalog = os.path.dirname(os.path.abspath(nowy_raport))
    nowy = os.path.normcase(os.path.abspath(nowy_raport))
    czas_nowego = os.path.getmtime(nowy_raport)
    przedrostki = RODZINY[rodzina]

    do_archiwum = []
    for nazwa in os.listdir(katalog):
        sc = os.path.join(katalog, nazwa)
        if (not nazwa.lower().endswith('.txt')
                or not nazwa.startswith(przedrostki)
                or os.path.normcase(sc) == nowy
                or not os.path.isfile(sc)
                or os.path.getmtime(sc) > czas_nowego):
            continue
        do_archiwum.append(sc)

    if not do_archiwum:
        return []

    archiwum = os.path.join(katalog_raportow(katalog), 'Archiwum')
    os.makedirs(archiwum, exist_ok=True)
    zablokowane = []
    for sc in do_archiwum:
        try:
            os.replace(sc, os.path.join(archiwum, os.path.basename(sc)))
        except OSError:
            zablokowane.append(sc)

    if zablokowane and iface is not None:
        iface.messageBar().pushMessage(
            'Raporty',
            'Nie przeniesiono do Raporty/Archiwum (plik otwarty?): ' +
            ', '.join(os.path.basename(x) for x in zablokowane),
            Qgis.Warning, 10)
    return zablokowane
