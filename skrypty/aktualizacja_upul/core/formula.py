"""Wspólne, czyste funkcje obliczeniowe — parser PART_CD i formuła masy.

Cel
---
F2, F3 i F4 mają wspólny filtr (`PART_CD ∈ 1..10`) i wspólną formułę masy
(F2 dla pustych VOLUME, F3 do nadpisywania). Wydzielenie ich tutaj:

* eliminuje powielenie logiki w trzech plikach (DRY),
* pozwala testować jednostkowo (`test_formula.py`) bez DB,
* daje jedno miejsce do zmiany jeśli klient zmieni interpretację formuły.

Wszystko jest **czyste**: brak side-effectów, brak importów z innych modułów
pluginu. Wejście → wyjście, łatwe do reasonowania.
"""


def parse_part_cd(value, lo, hi):
    """Parsuje `FSS.PART_CD` (string typu „1", „5", „10") na int z zakresu.

    Kolumna `PART_CD` w bazie jest tekstowa (instrukcja: „udział gatunku jako
    wartość liczbowa, string parsowalny na int 1–10"). Wartości spoza zakresu
    (`'MJS'`, `'PJD'`, NULL, ujemne, > 10) oznaczają rekord **nietykalny** —
    poza filtrem operacyjnym F2/F3/F4. Zwracamy wtedy None, a wywołujący po
    prostu pomija rekord (bez wpisu w raporcie — to nie błąd, to świadome
    wykluczenie z filtra).

    Args:
        value: Wartość pola `PART_CD` z bazy (string, int lub None).
        lo: Dolna granica zakresu akceptowanego (zwykle `config.part_cd_min`).
        hi: Górna granica zakresu (zwykle `config.part_cd_max`).

    Returns:
        Int z zakresu [lo, hi], lub None gdy wartość jest nieparsowalna lub
        spoza zakresu.

    Examples:
        >>> parse_part_cd("5", 1, 10)
        5
        >>> parse_part_cd("MJS", 1, 10) is None
        True
        >>> parse_part_cd("11", 1, 10) is None
        True
        >>> parse_part_cd(None, 1, 10) is None
        True
    """
    if value is None:
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if lo <= n <= hi:
        return n
    return None


def obliczona_masa(ftr_volume, standdensity, part_cd, zero_replacement, coefficient):
    """Wspólna formuła masy drzewa dla F2 i F3.

    Wzór z instrukcji:

        obliczona_masa = ROUND(ftr_volume * coefficient * PART_CD * standdensity)

    gdzie:

    * `ftr_volume`   — `F_TABLICA_ROZSZERZONA.VOLUME` dla danej kombinacji
      `(SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD)`. Gdy w FTR jest 0 — instrukcja
      mówi: „traktować jako 1" (parametr `zero_replacement`).
    * `coefficient`  — `0.1` z konfiguracji (parametr `volume_formula_coefficient`).
    * `PART_CD`      — udział gatunku w wydzieleniu (1..10, już sparsowany int).
    * `standdensity` — `F_AROD_STOREY.STANDDENSITY_INDEX` dla `ARODES_INT_NUM`
      rekordu.

    Algorytm:

    1. Jeśli `ftr_volume` jest 0 lub None → użyj `zero_replacement`
       (świadomy efekt — chronimy przed degeneracją wzoru do 0 dla
       niekompletnych wpisów w FTR).
    2. Pomnóż 4 czynniki.
    3. Zaokrąglij do najbliższej liczby całkowitej (`round()` w Pythonie używa
       banker's rounding, ale dla naszych wartości to nie ma znaczenia —
       wynik i tak będzie zapisany do MDB jako Long).

    Args:
        ftr_volume: Wartość VOLUME z `F_TABLICA_ROZSZERZONA` (float/None/0).
        standdensity: `STANDDENSITY_INDEX` z `F_AROD_STOREY` (float).
        part_cd: Udział gatunku (int 1..10).
        zero_replacement: Wartość zastępcza dla `ftr_volume in (0, None)`.
        coefficient: Współczynnik `0.1` z konfiguracji.

    Returns:
        Int — wyliczona masa zaokrąglona.
    """
    if ftr_volume == 0 or ftr_volume is None:
        ftr_volume = zero_replacement
    return round(ftr_volume * coefficient * part_cd * standdensity)
