"""Słownik TD (typ drzewostanu docelowego) wg typu siedliskowego lasu (TSL) -
używany przez utworz_baze_z_BDL.py do automatycznego uzupełniania
F_AROD_GOAL. DOMYSLNY pochodzi od użytkownika (materialy/TSL_slownik.jpg,
domyślny słownik TPU) i jest NIENARUSZALNY - edycje użytkownika (przez
td_slownik_dialog.TdSlownikDialog) trafiają do QSettings, nigdy do tej
stałej; "Resetuj" w dialogu usuwa zapis w QSettings, więc wczytaj() znowu
zwraca DOMYSLNY."""

import json

from PyQt5.QtCore import QSettings

_ORGANIZACJA = 'LAS_R'
_APLIKACJA = 'UtworzBazaZBDL'
_KLUCZ_USTAWIENIA = 'td_slownik_json'

DOMYSLNY = {
    'BB': ('SO',),
    'BGB': ('ŚW',),
    'BMB': ('SO',),
    'BGŚW': ('ŚW',),
    'BMGB': ('ŚW',),
    'BMGŚW': ('ŚW',),
    'BMGW': ('ŚW',),
    'BMŚW': ('SO',),
    'BMW': ('SO',),
    'BMWYZŚW': ('JD', 'SO'),
    'BMWYZW': ('JD', 'BK'),
    'BS': ('SO',),
    'BŚW': ('SO',),
    'BW': ('SO',),
    'BWG': ('ŚW',),
    'LGŚW': ('ŚW', 'JD', 'BK'),
    'LGW': ('JD',),
    'LŁ': ('JS', 'DB'),
    'LŁG': ('JS', 'OL'),
    'LŁWYZ': ('OL',),
    'LMB': ('OL',),
    'LMGŚW': ('ŚW', 'BK', 'JD'),
    'LMGW': ('ŚW', 'BK', 'JD'),
    'LMŚW': ('SO', 'DB'),
    'LMW': ('SO', 'JD'),
    'LMWYZŚW': ('SO', 'JD', 'BK'),
    'LMWYZW': ('DB', 'SO'),
    'LŚW': ('DB',),
    'LW': ('DB',),
    'LWYZŚW': ('JD', 'BK'),
    'LWYZW': ('BK', 'JD'),
    'OL': ('OL',),
    'OLJ': ('JS', 'OL'),
    'OLJG': ('JS', 'OL'),
    'OLJWYZ': ('ŚW',),
}


def _domyslny_kopia():
    return {tsl: list(gatunki) for tsl, gatunki in DOMYSLNY.items()}


def wczytaj():
    """Zwraca aktualny słownik TD jako {tsl: [gatunek, ...]} - z QSettings,
    jeśli użytkownik go tam zapisał, inaczej kopię DOMYSLNY. Zawsze nowy
    słownik/listy (bezpieczne do modyfikacji przez wywołującego)."""
    surowy = QSettings(_ORGANIZACJA, _APLIKACJA).value(_KLUCZ_USTAWIENIA)
    if not surowy:
        return _domyslny_kopia()
    try:
        dane = json.loads(surowy)
    except (TypeError, ValueError):
        return _domyslny_kopia()
    return {str(tsl): [str(g) for g in gatunki] for tsl, gatunki in dane.items()}


def zapisz(slownik):
    """Zapisuje podany słownik ({tsl: [gatunek, ...]}) jako bieżący w
    QSettings - nadpisuje ewentualny wcześniejszy zapis użytkownika."""
    tekst = json.dumps(slownik, ensure_ascii=False)
    QSettings(_ORGANIZACJA, _APLIKACJA).setValue(_KLUCZ_USTAWIENIA, tekst)


def resetuj():
    """Usuwa zapisany w QSettings słownik użytkownika - kolejne wczytaj()
    ponownie zwróci kopię DOMYSLNY (niezmienionego)."""
    QSettings(_ORGANIZACJA, _APLIKACJA).remove(_KLUCZ_USTAWIENIA)
