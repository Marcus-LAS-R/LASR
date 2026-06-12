"""F1 — Aktualizacja drzewostanu o +10 lat (postarzenie + przyrosty wymiarów).

Cel operacji
------------
Po 10 latach od poprzedniego pomiaru baza jest „przeterminowana". F1 robi:

1. Wiek: `SPECIES_AGE += 10` dla każdego rekordu, gdzie wiek nie jest NULL.
2. Wymiary (`HEIGHT`, `BHD`): przyrost wg tabeli klas wiekowych z
   `config/constants.json` (sekcja `f1.growth_table`) — przedziały
   `11–20`, `21–40`, `41–60`, `61–80`, `81–100`, `>100`.
3. Masa: `VOLUME *= 1.1`, `VOLUME_TEMP *= 1.1` (mnożnik z configu).

Filtr
-----
* `SPECIES_AGE IS NOT NULL` — bez wieku nie ma jak liczyć przyrostów.
* D1.1 — domyślnie **NIE** filtrujemy `STOREY_CD='DRZEW'` (instrukcja
  nie wymaga; flaga w configu `f1.filter_storey_drzew` pozwala włączyć,
  jeśli klient kiedyś zażąda).

Pomijanie NULL-i (D1.4)
-----------------------
Jeśli którakolwiek z kolumn `HEIGHT/BHD/VOLUME/VOLUME_TEMP` jest NULL —
zmieniamy **tylko** `SPECIES_AGE` i raportujemy rekord. Powód: `NULL + 4`
w SQL daje NULL, czyli bezmyślne UPDATE zniszczyłoby dotychczasowe wartości
(historyczna pułapka starego kodu, który robił UPDATE bez WHERE).
"""

import os

from .db import table_exists
from .reporting import Report
from .versioning import VersionManager


def prior_run(conn, config):
    """Zwraca dict {timestamp, user_note} ostatniego committed F1, lub None."""
    cursor = conn.cursor()
    vtable = config.table("versions")
    if not table_exists(cursor, vtable):
        return None
    cursor.execute(
        f"SELECT TOP 1 [TIMESTAMP], USER_NOTE FROM {vtable} "
        f"WHERE OPERATION = 'F1' AND [STATUS] = 'committed' "
        f"ORDER BY VERSION_ID DESC"
    )
    row = cursor.fetchone()
    return {"timestamp": row[0], "user_note": row[1]} if row else None


def _os_username():
    return os.environ.get("USERNAME") or os.environ.get("USER") or "?"


OPERATION = "F1"
PK = "SPEC_STOR_INT_NUM"
AGE_INCREMENT = 10
VOLUME_COLUMNS = ("VOLUME", "VOLUME_TEMP")
DIMENSION_COLUMNS = ("HEIGHT", "BHD")


def run(conn, config, mdb_path, dry_run, user_note=""):
    """Wykonuje operację F1 — pełen cykl: filtruj, oblicz, zapisz, zaraportuj.

    Algorytm
    --------
    1. **SELECT** rekordów z `F_STOREY_SPECIES` spełniających filtr:
       `SPECIES_AGE IS NOT NULL` (opcjonalnie + `STOREY_CD='DRZEW'`).
    2. **Pętla po wierszach** — buduje listę `plan` (lokalna, w pamięci):
       * Dla każdego: `new_age = age + 10`.
       * Jeśli jakaś kolumna wymiarowa jest NULL → zapisz pomijający `skip`
         i wsadź do planu TYLKO zmianę `SPECIES_AGE` (bez ryzyka degradacji).
       * Inaczej: `(h_delta, b_delta) = config.growth_delta(new_age)`,
         `new_height = height + h_delta`, analogicznie BHD,
         `new_volume = volume * multiplier`, analogicznie VOLUME_TEMP.
       * Plan: `[{pk, changes: [(col, old, new), ...]}, ...]`.
    3. **Dry-run**: tylko liczniki + plik raportu, brak UPDATE i snapshotów.
    4. **Commit**:
       * `VersionManager.open('F1', user_note)` → nowa sesja wersji.
       * Per rekord: UPDATE FSS + `session.record_change` dla każdej kolumny.
       * `session.commit(affected_rows=changed)` → zapis `_LRT_VERSIONS`
         i wszystkich snapshotów.
       * `report.version_id` wypełnione → trafia do raportu i GUI.

    Args:
        conn: Otwarte połączenie do MDB.
        config: Instancja `Config` (mnożniki, growth_table, nazwy tabel).
        mdb_path: Ścieżka pliku MDB — używana tylko do umieszczenia raportu
            obok bazy (nie do otwierania nowego połączenia).
        dry_run: True → tylko symulacja, False → faktyczny commit + snapshot.
        user_note: Opcjonalna notatka z GUI — ląduje w `_LRT_VERSIONS.USER_NOTE`.

    Returns:
        Instancja `Report` z wypełnionymi licznikami, listą pominięć i
        (w trybie commit) `version_id`. Plik raportu .txt jest już zapisany
        na dysku — GUI ma tylko podsumować ekrn.
    """
    if not user_note:
        user_note = _os_username()
    report = Report(OPERATION, mdb_path, dry_run)
    fss = config.table("fss")

    where = "SPECIES_AGE IS NOT NULL"
    if config.f1_filter_storey_drzew:
        where += f" AND STOREY_CD = '{config.storey_drzew}'"

    cursor = conn.cursor()
    cursor.execute(
        f"SELECT {PK}, SPECIES_AGE, HEIGHT, BHD, VOLUME, VOLUME_TEMP "
        f"FROM {fss} WHERE {where}"
    )
    rows = cursor.fetchall()

    plan = []
    multiplier = config.f1_volume_multiplier

    for pk, age, height, bhd, volume, volume_temp in rows:
        report.processed += 1
        new_age = age + AGE_INCREMENT

        if any(v is None for v in (height, bhd, volume, volume_temp)):
            # NULL w wymiarach — chronimy istniejące wartości (D1.4):
            # zmieniamy tylko wiek, resztę pomijamy z odpowiednim wpisem w raporcie.
            report.skip(pk, "HEIGHT/BHD/VOLUME/VOLUME_TEMP", "NULL w jednej z kolumn — pomijam wymiary")
            plan.append({"pk": pk, "changes": [("SPECIES_AGE", age, new_age)]})
            continue

        h_delta, b_delta = config.growth_delta(new_age)
        new_height = height + h_delta
        new_bhd = bhd + b_delta
        new_volume = volume * multiplier
        new_volume_temp = volume_temp * multiplier

        plan.append({
            "pk": pk,
            "changes": [
                ("SPECIES_AGE", age, new_age),
                ("HEIGHT", height, new_height),
                ("BHD", bhd, new_bhd),
                ("VOLUME", volume, new_volume),
                ("VOLUME_TEMP", volume_temp, new_volume_temp),
            ],
        })

    if dry_run:
        report.changed = sum(1 for p in plan if p.get("changes"))
        report.write()
        return report

    # Sortuj malejąco po starym SPECIES_AGE — zapobiega przejściowym kolizjom
    # w unikalnym indeksie gdy dwa rekordy mają wiek różniący się o 10 lat
    # (np. 20→30 trafiłoby w istniejące 30, zanim ono stałoby się 40).
    plan.sort(
        key=lambda e: next((old for col, old, _ in e["changes"] if col == "SPECIES_AGE"), 0),
        reverse=True,
    )

    versions = VersionManager(conn, config)
    session = versions.open(OPERATION, user_note=user_note)
    for entry in plan:
        pk = entry["pk"]
        changes = entry["changes"]
        # Dynamicznie składamy UPDATE — kolumny zależą od tego, czy rekord miał
        # NULL-e (wtedy tylko SPECIES_AGE) czy pełny zestaw 5 pól.
        sets = ", ".join(f"{col} = ?" for col, _old, _new in changes)
        params = [new for _col, _old, new in changes] + [pk]
        cursor.execute(f"UPDATE {fss} SET {sets} WHERE {PK} = ?", params)
        for col, old, new in changes:
            session.record_change(
                table=fss, pk_field=PK, pk_value=pk,
                column=col, old_value=old, new_value=new,
            )
        report.changed += 1

    session.commit(affected_rows=report.changed)
    report.version_id = session.version_id
    report.write()
    return report
