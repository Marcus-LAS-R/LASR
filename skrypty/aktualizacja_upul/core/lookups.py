"""Wczytywanie słowników FTR/FAS i logika doboru bonitacji dla F2.

Cel
---
F2 i F3 muszą wielokrotnie odpytywać `F_TABLICA_ROZSZERZONA` (FTR) i
`F_AROD_STOREY` (FAS) — typowo dziesiątki/setki tysięcy zapytań przy
pełnej bazie. Strategia: wczytujemy obie tabele JEDEN raz do dwóch
słowników w pamięci (`O(N)` raz na operację), a potem każdy lookup
to `O(1)` dostęp po kluczu — znacznie szybciej niż per-row JOIN w Access.

Tradeoff: zużycie RAM rośnie liniowo z rozmiarem FTR/FAS, ale w realnych
bazach to są tysiące, nie miliony wierszy — pamięciowo bezpieczne.

Dodatkowo `pick_site_class()` zawiera nietrywialną logikę doboru
„najbliższej dostępnej bonitacji" dla rekordów, które po Etapie A F2
mają SITE_CLASS_CD do uzupełnienia.
"""


def load_ftr(cursor, ftr_table):
    """Wczytuje `F_TABLICA_ROZSZERZONA` do dwóch indeksów w pamięci.

    Zwraca DWA słowniki bo F2/F3/F4 mają dwa różne pytania do FTR:

    1. „Daj mi wartości BHD/HEIGHT/VOLUME dla DOKŁADNEGO klucza
       `(SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD)`" → `by_key`.
    2. „Jakie bonitacje są w ogóle dostępne dla tego gatunku?" — używane
       przez `pick_site_class()` do wyboru najbliższej alternatywy →
       `by_species`.

    Algorytm:

    1. Jedno `SELECT * FROM FTR` (cała tabela).
    2. Dla każdego wiersza:
       a. Wpisz do `by_key[(SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD)]` słownik
          z BHD/HEIGHT/VOLUME (gotowy do `ftr_row["BHD"]` w F2/F3/F4).
       b. Dorzuć SITE_CLASS_CD do zbioru `by_species[SPECIES_CD]`.

    Args:
        cursor: Kursor DB.
        ftr_table: Nazwa tabeli FTR (zwykle `config.table('ftr')`).

    Returns:
        Krotka `(by_key, by_species)`:

        * `by_key`: dict `{(species, age, site_class): {"BHD": ..., "HEIGHT": ..., "VOLUME": ...}}`
        * `by_species`: dict `{species: set(site_class_cd, ...)}`
    """
    cursor.execute(
        f"SELECT SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD, BHD, HEIGHT, VOLUME FROM {ftr_table}"
    )
    by_key = {}
    by_species = {}
    for species, age, site_class, bhd, height, volume in cursor.fetchall():
        # Access CHAR-y wracają z paddingiem („II " zamiast „II"). Bez stripa
        # klucze FTR i wartości z FSS rozjeżdżają się i każdy lookup pudłuje.
        site_class = site_class.strip() if isinstance(site_class, str) else site_class
        key = (species, age, site_class)
        by_key[key] = {"BHD": bhd, "HEIGHT": height, "VOLUME": volume}
        by_species.setdefault(species, set()).add(site_class)
    return by_key, by_species


def load_fas_density(cursor, fas_table, storey_cd="DRZEW"):
    """Wczytuje mapę `ARODES_INT_NUM → STANDDENSITY_INDEX` z tabeli FAS.

    `STANDDENSITY_INDEX` (zwarcie) jest potrzebne w formule masy (F2/F3) —
    każdy rekord FSS ma `ARODES_INT_NUM`, którym dowiązuje się do swojego
    wydzielenia w FAS (D2.2 — łączenie po `ARODES_INT_NUM`).

    Filtr `STOREY_CD` jest konieczny — FAS może mieć wiele wierszy na ARODES
    (np. DRZEW + PODSZ z różnymi STANDDENSITY_INDEX). Bierzemy tylko piętro
    odpowiadające przetwarzanym rekordom FSS.

    Args:
        cursor: Kursor DB.
        fas_table: Nazwa tabeli FAS (zwykle `config.table('fas')`).
        storey_cd: Piętro do filtrowania (zwykle `config.storey_drzew`).

    Returns:
        Dict `{arodes_int_num: standdensity_index}`. Brak klucza oznacza,
        że dla danego wydzielenia nie da się policzyć masy — F2/F3 raportują
        skip z powodu „brak FAS".
    """
    cursor.execute(
        f"SELECT ARODES_INT_NUM, STANDDENSITY_INDEX FROM {fas_table} "
        f"WHERE STOREY_CD = '{storey_cd}'"
    )
    return {arodes: density for arodes, density in cursor.fetchall()}


def pick_site_class(group_site_class, species_cd, by_species, scale_index):
    """Wybiera SITE_CLASS_CD dla rekordu w Etapie A F2.

    Kontekst: w jednej grupie `ARODES_INT_NUM` rekord z `SPECIES_RANK_ORDER=1`
    (dominant) ma bonitację `group_site_class`. Pozostałe gatunki w tej grupie
    powinny dziedziczyć tę bonitację, ALE tylko jeśli w FTR istnieje
    odpowiadający wpis dla `(species_cd, group_site_class)`. Gdy nie istnieje,
    instrukcja każe wybrać **najbliższą dostępną** bonitację dla `species_cd`.

    Algorytm:

    1. Pobierz zbiór dostępnych bonitacji dla `species_cd` z `by_species`
       (przygotowany w `load_ftr`).
    2. Brak gatunku w FTR → zwróć `(None, "brak gatunku w FTR")` —
       rekord do raportu.
    3. `group_site_class` jest wśród dostępnych → bezpośredni hit, zwróć.
    4. Skonwertuj `group_site_class` i wszystkie dostępne wartości na indeksy
       w skali (`bonitacja_scale` z konfigu, np. `IA=0, I=1, ..., V=5`).
       Wartości nieindeksowalne (poza skalą — niespodzianka w danych) →
       raport z odpowiednim powodem.
    5. Posortuj dostępne po indeksie. `min_idx` to NAJLEPSZA dostępna,
       `max_idx` to NAJGORSZA dostępna.
    6. Reguła z instrukcji:
       * `target < min` (group lepsza niż wszystkie dostępne, np. dominant ma
         IA, a gatunek X nie ma IA) → wybierz **MIN** (najlepsza dostępna,
         „IA → I").
       * `target > max` (group gorsza niż wszystkie, np. IV gdy gatunek tylko
         do III) → wybierz **MAX** (najgorsza dostępna, „IV → III").
       * `target` mieści się w dostępnym zakresie, ale nie ma dokładnego —
         wybierz pierwszą o indeksie ≥ target (zachowawcze: schodzimy raczej
         „w gorsze").

    Args:
        group_site_class: Bonitacja dominanta grupy (string lub None).
        species_cd: Kod gatunku rekordu, dla którego dobieramy bonitację.
        by_species: Dict z `load_ftr` (gatunek → zbiór dostępnych bonitacji).
        scale_index: Callable mapujące string → int (zwykle
            `config.bonitacja_index`). Zwraca None dla wartości spoza skali.

    Returns:
        Krotka `(picked, reason)`:

        * `picked` — wybrana bonitacja (string) lub None gdy się nie da.
        * `reason` — None przy sukcesie, krótki opis powodu przy porażce
          (gotowy do `report.skip(..., reason)`).
    """
    available = by_species.get(species_cd, set())
    if not available:
        return None, "brak gatunku w FTR"
    if group_site_class in available:
        picked = group_site_class
    else:
        target_idx = scale_index(group_site_class)
        if target_idx is None:
            return None, f"bonitacja '{group_site_class}' poza skalą"

        indexed = [(scale_index(sc), sc) for sc in available if scale_index(sc) is not None]
        if not indexed:
            return None, "brak bonitacji w skali dla gatunku w FTR"

        indexed.sort()
        min_idx, min_sc = indexed[0]
        max_idx, max_sc = indexed[-1]

        if target_idx < min_idx:
            picked = min_sc
        elif target_idx > max_idx:
            picked = max_sc
        else:
            picked = next(sc for idx, sc in indexed if idx >= target_idx)

    if picked == "IA" and not species_cd.startswith("SO"):
        picked = "I"

    return picked, None
