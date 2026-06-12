"""Wczytywanie i udostępnianie konfiguracji wtyczki (`config/constants.json`).

Cel
---
Wszystkie stałe operacyjne (przyrosty wiekowe F1, mnożnik VOLUME, skala
bonitacji, współczynnik formuły masy, progi PART_CD, nazwy tabel w MDB)
żyją w jednym pliku JSON obok wtyczki. Dzięki temu:

* klient/dev może podmienić wartości bez edycji kodu i bez przepakowywania
  wtyczki — wystarczy zapisać nowy `constants.json` i ponownie kliknąć akcję;
* wszystkie 4 operacje (F1–F4) i mechanizm rollback widzą tę samą prawdę —
  brak ryzyka, że gdzieś w kodzie został „magic number" niespójny z plikiem;
* testy ładują ten sam plik co produkcja (fixture `config` w `conftest.py`).

Klasa `Config` to cienka warstwa nad słownikiem JSON: czyta plik raz przy
starcie operacji i wystawia accessor-y o czytelnych nazwach (`f1_volume_multiplier`,
`bonitacja_scale`, itd.). Brak setterów — config jest read-only w trakcie
działania (świadoma decyzja: jakakolwiek zmiana wymaga edycji pliku
+ ponownego uruchomienia operacji, co eliminuje stan ukryty w UI).
"""

import json
import os


_CONFIG_FILENAME = "constants.json"


class Config:
    """Niemutowalny pojemnik na stałe operacyjne wtyczki.

    Reprezentuje zawartość `config/constants.json` jako obiekt z accessor-ami.
    Konstruktor jest „prywatny" w sensie konwencji — w produkcji używa się
    classmethod `Config.load(plugin_dir)`, który czyta plik z dysku.

    Attributes:
        _data: Surowy słownik JSON. Prefiks `_` oznacza, że nikt poza klasą
            nie powinien po nim chodzić bezpośrednio (preferuj accessor-y).
    """

    def __init__(self, data):
        """Konstruktor — przyjmuje już sparsowany słownik.

        Bezpośrednie wywołanie używane głównie w testach. W produkcji wołaj
        `Config.load(plugin_dir)`.

        Args:
            data: Słownik o strukturze `constants.json` (klucze `f1`, `f2_f3`,
                `f4`, `filters`, `tables`).
        """
        self._data = data

    @classmethod
    def load(cls, plugin_dir):
        """Wczytuje konfigurację z `<plugin_dir>/config/constants.json`.

        Args:
            plugin_dir: Ścieżka katalogu wtyczki (zwykle `os.path.dirname(__file__)`
                z `plugin.py`).

        Returns:
            Nowa instancja `Config` z wczytanymi danymi.

        Raises:
            FileNotFoundError: Gdy plik nie istnieje (świadomy fail-fast —
                wtyczka bez configu nie powinna ruszyć).
            json.JSONDecodeError: Gdy plik istnieje, ale ma niepoprawny JSON
                (literówka po edycji ręcznej).
        """
        path = os.path.join(plugin_dir, "config", _CONFIG_FILENAME)
        with open(path, "r", encoding="utf-8") as f:
            return cls(json.load(f))

    # ---- F1 (aktualizacja +10 lat) ------------------------------------------

    @property
    def f1_growth_table(self):
        """Tabela przyrostów wiekowych dla F1.

        Returns:
            Lista słowników z kluczami `min_age`, `max_age` (lub None dla
            otwartego przedziału w górę), `height_delta`, `bhd_delta`.
            Używana przez `growth_delta()` do dopasowania przyrostu do wieku.
        """
        return self._data["f1"]["growth_table"]

    @property
    def f1_volume_multiplier(self):
        """Mnożnik VOLUME/VOLUME_TEMP w F1.

        Domyślnie `1.1` (D1.2 — instrukcja, nie `1.12` z dawnego kodu).
        """
        return self._data["f1"]["volume_multiplier"]

    @property
    def f1_filter_storey_drzew(self):
        """Czy F1 ma filtrować tylko `STOREY_CD='DRZEW'`.

        Domyślnie `False` (D1.1 — instrukcja nie wymaga, F1 rusza całą tabelę).
        """
        return self._data["f1"]["filter_storey_drzew"]

    # ---- F2/F3 (uzupełnienie z FTR + formuła masy) --------------------------

    @property
    def volume_zero_replacement(self):
        """Wartość zastępcza dla `FTR.VOLUME = 0` w formule masy.

        Instrukcja: „zerowy VOLUME w FTR → przy obliczeniach traktować jako 1".
        """
        return self._data["f2_f3"]["volume_zero_replacement"]

    @property
    def volume_formula_coefficient(self):
        """Współczynnik `0.1` w `obliczona_masa = ROUND(ftr_volume * 0.1 * PART_CD * standdensity)`."""
        return self._data["f2_f3"]["volume_formula_coefficient"]

    @property
    def bonitacja_scale(self):
        """Skala bonitacji od najlepszej do najgorszej.

        Domyślnie `["IA","I","II","III","IV","V"]` (D2.1 — wymaga empirycznej
        weryfikacji przy pierwszym smoke teście). Pozycja w liście = indeks
        porządkowy używany przez `pick_site_class()` do wyboru najbliższej
        dostępnej bonitacji.
        """
        return self._data["f2_f3"]["bonitacja_scale"]

    @property
    def round_ftr_values(self):
        """Czy zaokrąglać wartości BHD/HEIGHT pobrane z FTR (D2.3 — domyślnie True)."""
        return self._data["f2_f3"]["round_ftr_values"]

    # ---- F4 (korekta BHD<HEIGHT) --------------------------------------------

    @property
    def f4_fallback_bhd_equals_height(self):
        """D4.1 — czy gdy brak FTR ma być twardy fallback `BHD := HEIGHT`.

        Domyślnie `True`. Gdy `False`, F4 raportuje skip i nie ruszuje rekordu.
        """
        return self._data["f4"]["fallback_bhd_equals_height"]

    # ---- Filtry wspólne -----------------------------------------------------

    @property
    def storey_drzew(self):
        """Wartość filtra `STOREY_CD` dla rekordów drzewostanu (zwykle 'DRZEW')."""
        return self._data["filters"]["storey_drzew"]

    @property
    def part_cd_min(self):
        """Minimalny PART_CD akceptowany przez F2/F3/F4 (zwykle 1)."""
        return self._data["filters"]["part_cd_min"]

    @property
    def part_cd_max(self):
        """Maksymalny PART_CD akceptowany przez F2/F3/F4 (zwykle 10).

        Rekordy z PART_CD spoza [min, max] (np. 'MJS', 'PJD') są **nietykalne**.
        """
        return self._data["filters"]["part_cd_max"]

    # ---- Nazwy tabel w MDB --------------------------------------------------

    def table(self, key):
        """Zwraca nazwę tabeli w bazie MDB dla danego klucza logicznego.

        Centralizacja nazw w jednym miejscu pozwala je zmieniać (np. gdyby
        klient miał inną konwencję nazewniczą) bez przeszukiwania kodu.

        Args:
            key: Klucz logiczny — jeden z: `'fss'`, `'ftr'`, `'fas'`,
                `'versions'`, `'snapshots'`.

        Returns:
            Nazwa tabeli w bazie (string).

        Raises:
            KeyError: Gdy klucz nie istnieje w konfigu — świadomy fail-fast
                na literówkę typu `config.table('fas_')`.
        """
        return self._data["tables"][key]

    # ---- Pomocnicze przeliczenia --------------------------------------------

    def growth_delta(self, age):
        """Dopasowuje wiek do przedziału w `f1.growth_table` i zwraca przyrosty.

        Algorytm:

        1. Iteruj przedziały z `f1_growth_table` (zakładamy, że nie nachodzą).
        2. Sprawdź `min_age ≤ age ≤ max_age` (lub `max_age is None` dla
           ostatniego, otwartego przedziału „>100").
        3. Pierwsze dopasowanie → zwróć krotkę `(height_delta, bhd_delta)`.
        4. Brak dopasowania (np. age=5, przedziały zaczynają się od 11) →
           zwróć `(0, 0)` — wiek za młody na przyrost (świadome zachowanie:
           instrukcja F1 wymienia tylko 11+).

        Args:
            age: Wiek w latach (int) — zwykle `SPECIES_AGE + 10` (po starzeniu F1).

        Returns:
            Krotka `(height_delta, bhd_delta)` — wartości do dodania do HEIGHT i BHD.
        """
        for row in self.f1_growth_table:
            lo = row["min_age"]
            hi = row["max_age"]
            if age >= lo and (hi is None or age <= hi):
                return row["height_delta"], row["bhd_delta"]
        return 0, 0

    def bonitacja_index(self, value):
        """Mapuje wartość bonitacji na indeks porządkowy w skali.

        Indeks rośnie od najlepszej do najgorszej bonitacji:
        `IA=0, I=1, II=2, III=3, IV=4, V=5`. Pozwala porównywać bonitacje
        liczbowo (np. „która jest gorsza") w `pick_site_class()`.

        Args:
            value: Wartość bonitacji (string) z bazy lub None.

        Returns:
            Indeks (int 0..N-1) gdy wartość jest w skali, inaczej None.
            None używane jako sygnał „nieznana bonitacja" — do raportowania.
        """
        scale = self.bonitacja_scale
        if value in scale:
            return scale.index(value)
        return None
