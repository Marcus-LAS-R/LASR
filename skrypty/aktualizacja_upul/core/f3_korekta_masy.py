"""F3 — Korekta masy: przeliczenie `VOLUME`/`VOLUME_TEMP` od zera.

Cel operacji
------------
W przeciwieństwie do F2 (które tylko wypełnia puste pola), F3 **NADPISUJE
istniejące** wartości `VOLUME` i `VOLUME_TEMP` świeżo policzonymi z
formuły:

    masa = ROUND(FTR.VOLUME * 0.1 * PART_CD * FAS.STANDDENSITY_INDEX)

Ma to sens po F1 (postarzenie) i F2 (uzupełnienie wymiarów), bo dopiero
wtedy mamy spójny SPECIES_AGE i SITE_CLASS_CD do prawidłowego lookup-u
w FTR. Niemniej D3.1 — F3 jest **niezależna od F2** w sensie technicznym
(GUI może co najwyżej ostrzegać, że są jeszcze rekordy bez SITE_CLASS_CD).

Filtr
-----
* `STOREY_CD = 'DRZEW'`
* `PART_CD ∈ 1..10`

Pomijanie i raport
------------------
Rekord trafia do raportu, gdy:

* brak dopasowania w FTR po `(SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD)`
  (np. SITE_CLASS_CD jest NULL → klucz nigdy nie pasuje);
* brak `STANDDENSITY_INDEX` w FAS dla `ARODES_INT_NUM` rekordu.

Wynik
-----
Pola zmieniane: `VOLUME`, `VOLUME_TEMP` (zawsze obie tę samą wartość).
"""

from .formula import obliczona_masa, parse_part_cd
from .lookups import load_fas_density, load_ftr
from .reporting import Report
from .versioning import VersionManager


OPERATION = "F3"
PK = "SPEC_STOR_INT_NUM"


def run(conn, config, mdb_path, dry_run, user_note=""):
    """Wykonuje F3 — przeliczenie VOLUME/VOLUME_TEMP dla całej tabeli FSS (filtr DRZEW).

    Algorytm
    --------
    1. **Wczytaj słowniki**:
       * `load_ftr` → `by_key` (drugi indeks `by_species` nie jest tu używany,
         bo F3 nie dobiera bonitacji — wymaga jej w komplecie po Etapie A F2).
       * `load_fas_density` → `arodes → density`.

    2. **SELECT rekordów FSS** ze STOREY_CD='DRZEW', wszystkie kolumny
       potrzebne do formuły + obecne VOLUME/VOLUME_TEMP (do `old_value`
       w snapshocie).

    3. **Pętla po wierszach**:
       a. Parsuj `PART_CD`. None → cichy skip (poza filtrem).
       b. Sprawdź `(SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD)` w `ftr_by_key`.
          Brak → `report.skip` z powodem o braku FTR, kontynuuj.
       c. Sprawdź `arodes` w `fas_density`. Brak → `report.skip`, kontynuuj.
       d. Policz `masa = obliczona_masa(...)`.
       e. Dodaj do `plan` dwie zmiany: `VOLUME → masa` i `VOLUME_TEMP → masa`.

    4. **Dry-run**: tylko liczniki + raport.

    5. **Commit**: standardowy flow — `VersionManager.open('F3')`, per wpis
       UPDATE + 2 snapshoty pól, `session.commit`.

    Args:
        conn: Połączenie do MDB.
        config: Konfiguracja (zero replacement, coefficient, tabele).
        mdb_path: Ścieżka pliku — do raportu.
        dry_run: True → bez UPDATE.
        user_note: Notatka GUI.

    Returns:
        Instancja `Report` z wynikami.
    """
    report = Report(OPERATION, mdb_path, dry_run)
    fss = config.table("fss")
    cursor = conn.cursor()

    ftr_by_key, _ = load_ftr(cursor, config.table("ftr"))
    fas_density = load_fas_density(cursor, config.table("fas"), config.storey_drzew)

    cursor.execute(
        f"SELECT {PK}, ARODES_INT_NUM, SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD, "
        f"PART_CD, VOLUME, VOLUME_TEMP "
        f"FROM {fss} WHERE STOREY_CD = '{config.storey_drzew}'"
    )
    rows = cursor.fetchall()

    plan = []
    for pk, arodes, species, age, site_class, part_cd_raw, volume, volume_temp in rows:
        report.processed += 1
        part_cd = parse_part_cd(part_cd_raw, config.part_cd_min, config.part_cd_max)
        if part_cd is None:
            # Rekord poza filtrem operacji — cichy skip (nie raportujemy).
            continue

        # FTR ma klucze stripowane (Access CHAR padding) — czyścimy też FSS.
        site_class = site_class.strip() if isinstance(site_class, str) else site_class
        # Guard: IA tylko dla SO* — dla pozostałych gatunków używamy I do lookupa.
        if site_class == "IA" and not (species or "").startswith("SO"):
            site_class = "I"
        ftr_row = ftr_by_key.get((species, age, site_class))
        if ftr_row is None:
            report.skip(pk, "VOLUME",
                        f"brak FTR dla ({species},{age},{site_class})",
                        arodes_int_num=arodes)
            continue

        density = fas_density.get(arodes)
        if density is None:
            report.skip(pk, "VOLUME",
                        f"brak FAS dla ARODES={arodes}",
                        arodes_int_num=arodes)
            continue

        masa = obliczona_masa(
            ftr_row["VOLUME"], density, part_cd,
            config.volume_zero_replacement,
            config.volume_formula_coefficient,
        )

        plan.append({
            "pk": pk,
            "changes": [
                ("VOLUME", volume, masa),
                ("VOLUME_TEMP", volume_temp, masa),
            ],
        })

    if dry_run:
        report.changed = len(plan)
        report.write()
        return report

    versions = VersionManager(conn, config)
    session = versions.open(OPERATION, user_note=user_note)
    for entry in plan:
        pk = entry["pk"]
        changes = entry["changes"]
        sets = ", ".join(f"{col} = ?" for col, _o, _n in changes)
        params = [new for _c, _o, new in changes] + [pk]
        cursor.execute(f"UPDATE {fss} SET {sets} WHERE {PK} = ?", params)
        for col, old, new in changes:
            session.record_change(
                table=fss, pk_field=PK, pk_value=pk,
                column=col, old_value=old, new_value=new,
            )
        report.changed += 1

    # Walidacja końcowa: rekordy z kompletem danych ale VOLUME/VOLUME_TEMP = NULL lub 0
    # otrzymują wartość 1 (minimalną niezerową) — zabezpieczenie przed pustymi masami.
    _fallback_where = (
        f"WHERE STOREY_CD = '{config.storey_drzew}' "
        f"AND SPECIES_CD IS NOT NULL "
        f"AND PART_CD IS NOT NULL "
        f"AND SPECIES_AGE IS NOT NULL "
        f"AND BHD IS NOT NULL "
        f"AND HEIGHT IS NOT NULL "
        f"AND SITE_CLASS_CD IS NOT NULL "
        f"AND (VOLUME IS NULL OR VOLUME = 0 OR VOLUME_TEMP IS NULL OR VOLUME_TEMP = 0)"
    )
    cursor.execute(
        f"SELECT {PK}, ARODES_INT_NUM, "
        f"IIF(VOLUME IS NULL OR VOLUME = 0, 1, 0) AS v_null, "
        f"IIF(VOLUME_TEMP IS NULL OR VOLUME_TEMP = 0, 1, 0) AS vt_null "
        f"FROM {fss} {_fallback_where}"
    )
    for pk_val, arodes_val, v_null, vt_null in cursor.fetchall():
        cols = "/".join(filter(None, [
            "VOLUME" if v_null else None,
            "VOLUME_TEMP" if vt_null else None,
        ]))
        report.fallback_ones.append({"pk_value": pk_val, "arodes_int_num": arodes_val, "column": cols})

    cursor.execute(
        f"UPDATE {fss} SET "
        f"VOLUME = IIF(VOLUME IS NULL OR VOLUME = 0, 1, VOLUME), "
        f"VOLUME_TEMP = IIF(VOLUME_TEMP IS NULL OR VOLUME_TEMP = 0, 1, VOLUME_TEMP) "
        f"{_fallback_where}"
    )

    session.commit(affected_rows=report.changed)
    report.version_id = session.version_id
    report.write()
    return report
