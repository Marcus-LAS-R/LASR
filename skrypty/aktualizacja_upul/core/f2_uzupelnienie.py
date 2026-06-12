"""F2 — Uzupełnienie braków + korekta HEIGHT i BHD z `F_TABLICA_ROZSZERZONA`.

Cel operacji
------------
Po F1 (postarzenie o 10 lat) drzewostan ma już nowy wiek, ale HEIGHT/BHD
zostały policzone z przybliżonej `growth_table`. F2 sprowadza HEIGHT oraz
BHD do prawdziwych wartości z tablicy wzorcowej (FTR) — i przy okazji
uzupełnia braki w VOLUME/VOLUME_TEMP dla gatunków towarzyszących.

Operacja jest dwuetapowa
------------------------
* **Etap A — uzupełnienie `SITE_CLASS_CD`**.
  W FTR klucz to `(SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD)`. Bez bonitacji
  nie ma jak nic doczytać. Zasada: bonitacja dziedziczy się od **dominanta
  grupy** (`SPECIES_RANK_ORDER = 1` w danym `ARODES_INT_NUM`).
  Gdy dla rekordu w FTR nie ma dokładnie tej bonitacji co u dominanta,
  bierzemy najbliższą dostępną dla gatunku (logika w `pick_site_class`).

* **Etap B — wymiary**.
  Po Etapie A każdy rekord ma już SITE_CLASS_CD (lub został zaraportowany
  i pominięty). Wczytujemy z FTR `(SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD)`
  i:
  * `HEIGHT := FTR.HEIGHT` **zawsze** (nadpisujemy także istniejące).
  * `BHD := FTR.BHD` **zawsze** (nadpisujemy także istniejące).
    Powód dla obu: terenowe pomiary wpadają do bazy po F1–F4, więc to co
    jest na tym etapie pochodzi z F1 (`growth_table`) i jest tylko
    przybliżeniem. F4 (korekta `BHD<HEIGHT`) zostaje jako safety-net dla
    danych wprowadzanych ręcznie po F1–F4.
  * `VOLUME := obliczona_masa` gdy `FSS.VOLUME IS NULL`.
  * `VOLUME_TEMP := obliczona_masa` gdy `FSS.VOLUME_TEMP IS NULL`.
  Wartości BHD/HEIGHT mogą być zaokrąglone (D2.3 — `config.round_ftr_values`).

Filtr operacji
--------------
* `STOREY_CD = 'DRZEW'`
* `PART_CD ∈ 1..10` (z konfigu) — inne wartości (`MJS`, `PJD`) cicho pomijane.

Wynik
-----
Pola zmieniane: `SITE_CLASS_CD`, `VOLUME`, `VOLUME_TEMP` — tylko gdy były
NULL. `HEIGHT` i `BHD` — zawsze, gdy FTR ma wartość i różni się od FSS.
"""

from .formula import obliczona_masa, parse_part_cd
from .lookups import load_fas_density, load_ftr, pick_site_class
from .reporting import Report
from .versioning import VersionManager


OPERATION = "F2"
PK = "SPEC_STOR_INT_NUM"
DOMINANT_RANK = 1


def run(conn, config, mdb_path, dry_run, user_note=""):
    """Wykonuje F2 — pełen cykl Etap A + Etap B + raport + opcjonalny commit.

    Algorytm
    --------
    1. **Wczytanie słowników** w pamięci (lookupy):
       * `load_ftr` → dwa indeksy: `(species, age, site_class) → {BHD,HEIGHT,VOLUME}`
         i `species → {site_class_cd, ...}` (do `pick_site_class`).
       * `load_fas_density` → `ARODES_INT_NUM → STANDDENSITY_INDEX`.

    2. **SELECT rekordów FSS** ze `STOREY_CD='DRZEW'`. Pobieramy wszystkie
       wymagane kolumny ZA JEDNYM razem (znacznie taniej niż per-row).
       Grupujemy w pamięci po `ARODES_INT_NUM`.

    3. **Pętla po grupach**:
       * Znajdź dominanta (`RANK = 1`). Brak → cała grupa do raportu.
       * `bonitacja_grupy = dominant.SITE_CLASS_CD`. NULL → cała grupa do raportu.
       * **Pętla po członkach** grupy:
         a. Parsuj `PART_CD`. None (poza zakresem) → cichy skip
            (rekord poza filtrem operacji, nie raportujemy).
         b. **Etap A**: jeśli `SITE_CLASS_CD IS NULL`, dobierz przez
            `pick_site_class(bonitacja_grupy, species, by_species, scale_index)`.
            Brak → `report.skip(...)`, kontynuuj.
         c. **Etap B**: pobierz `ftr_row` z `by_key`. Brak →
            `report.skip(...)`, zapamiętaj jednak zmianę SITE_CLASS_CD jeśli
            była (nie tracimy jej tylko dlatego, że brak FTR dla pozostałych pól).
         d. Dla każdego pola wymiarowego (BHD, HEIGHT) — dodaj do `changes`
            tylko gdy FSS ma NULL (NIE nadpisujemy istniejących wartości).
         e. Dla VOLUME/VOLUME_TEMP — sprawdź `STANDDENSITY_INDEX`. Brak →
            skip; jest → policz `obliczona_masa()` i dodaj te z NULL-em.
         f. Jeśli powstały jakiekolwiek `changes` → dodaj wpis do `plan`.

    4. **Dry-run**: tylko liczniki + raport.

    5. **Commit**: per wpis w `plan` dynamiczny UPDATE z N kolumnami i
       `record_change` per pole → standardowy flow VersionSession.

    Args:
        conn: Połączenie do MDB.
        config: Konfiguracja (tabele, filtry, formuła).
        mdb_path: Ścieżka pliku (do raportu).
        dry_run: True → bez UPDATE/snapshotów.
        user_note: Notatka z GUI.

    Returns:
        Instancja `Report` z licznikami, listą pominięć i (commit) `version_id`.
    """
    report = Report(OPERATION, mdb_path, dry_run)
    fss = config.table("fss")
    cursor = conn.cursor()

    ftr_by_key, ftr_by_species = load_ftr(cursor, config.table("ftr"))
    fas_density = load_fas_density(cursor, config.table("fas"), config.storey_drzew)

    cursor.execute(
        f"SELECT {PK}, ARODES_INT_NUM, SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD, "
        f"PART_CD, SPECIES_RANK_ORDER, BHD, HEIGHT, VOLUME, VOLUME_TEMP "
        f"FROM {fss} WHERE STOREY_CD = '{config.storey_drzew}'"
    )
    rows = cursor.fetchall()

    # Grupowanie po ARODES_INT_NUM — potrzebne do znalezienia dominanta i
    # przeniesienia jego bonitacji na resztę gatunków w tym samym wydzieleniu.
    groups = {}
    for row in rows:
        pk, arodes, species, age, site_class, part_cd, rank, bhd, height, volume, volume_temp = row
        # Access CHAR-y wracają z paddingiem („II " zamiast „II"). Czyścimy
        # od razu i pamiętamy oryginał — gdy odbiega od stripped, F2 nadpisuje
        # FSS, żeby istniejące rekordy z paddingiem dostały czystą wartość.
        site_class_raw = site_class
        site_class_clean = site_class.strip() if isinstance(site_class, str) else site_class
        groups.setdefault(arodes, []).append({
            "pk": pk, "arodes": arodes, "species": species, "age": age,
            "site_class": site_class_clean, "site_class_raw": site_class_raw,
            "part_cd_raw": part_cd, "rank": rank,
            "bhd": bhd, "height": height, "volume": volume, "volume_temp": volume_temp,
        })

    plan = []
    for arodes, members in groups.items():
        # Etap A.1 — znajdź dominanta. Brak → wszyscy do raportu, kolejna grupa.
        dominant = next((m for m in members if m["rank"] == DOMINANT_RANK), None)
        if dominant is None:
            for m in members:
                report.processed += 1
                report.skip(m["pk"], "SITE_CLASS_CD",
                            f"grupa ARODES={arodes} bez SPECIES_RANK_ORDER=1",
                            arodes_int_num=arodes)
            continue

        bonitacja_grupy = dominant["site_class"]
        if bonitacja_grupy is None:
            # Etap A.2 — dominant ma pustą bonitację: bez niej nie ma jak
            # uzupełnić pozostałych. Cała grupa do raportu.
            for m in members:
                report.processed += 1
                report.skip(m["pk"], "SITE_CLASS_CD",
                            f"dominant grupy ARODES={arodes} ma puste SITE_CLASS_CD",
                            arodes_int_num=arodes)
            continue

        for m in members:
            report.processed += 1
            part_cd = parse_part_cd(m["part_cd_raw"], config.part_cd_min, config.part_cd_max)
            if part_cd is None:
                # PART_CD spoza zakresu — rekord poza filtrem operacji, cichy skip.
                continue

            changes = []
            new_site_class = m["site_class"]

            if new_site_class is None:
                # Etap A — dobór bonitacji dla rekordu.
                picked, reason = pick_site_class(
                    bonitacja_grupy, m["species"], ftr_by_species, config.bonitacja_index
                )
                if picked is None:
                    report.skip(m["pk"], "SITE_CLASS_CD", reason, arodes_int_num=arodes)
                    continue
                changes.append(("SITE_CLASS_CD", m["site_class_raw"], picked))
                new_site_class = picked
            elif m["site_class_raw"] != new_site_class:
                # Istniejąca bonitacja miała białe znaki — czyścimy w bazie.
                changes.append(("SITE_CLASS_CD", m["site_class_raw"], new_site_class))

            # Guard: IA tylko dla gatunków SO* — istniejące IA w FSS dla innych
            # gatunków korygujemy do I przed lookupem FTR.
            if new_site_class == "IA" and not m["species"].startswith("SO"):
                old_raw = next((o for c, o, n in changes if c == "SITE_CLASS_CD"), m["site_class_raw"])
                changes = [(c, o, n) for c, o, n in changes if c != "SITE_CLASS_CD"]
                changes.append(("SITE_CLASS_CD", old_raw, "I"))
                new_site_class = "I"

            ftr_row = ftr_by_key.get((m["species"], m["age"], new_site_class))
            density = fas_density.get(m["arodes"])

            if ftr_row is None:
                # Brak wzorca w FTR — wymiarów nie ruszamy, ale zmianę
                # SITE_CLASS_CD zachowujemy (jeśli była).
                report.skip(m["pk"], "BHD/HEIGHT/VOLUME",
                            f"brak FTR dla ({m['species']},{m['age']},{new_site_class})",
                            arodes_int_num=arodes)
                if changes:
                    plan.append({"pk": m["pk"], "changes": changes})
                continue

            # Etap B — HEIGHT i BHD zawsze sprowadzamy do wartości z FTR
            # (przybliżenie z F1.growth_table → prawdziwa wartość po nowym
            # wieku i bonitacji; terenowe pomiary wpadną po F1–F4).
            if ftr_row["BHD"] is not None:
                value = round(ftr_row["BHD"]) if config.round_ftr_values else ftr_row["BHD"]
                if m["bhd"] is None or m["bhd"] < value:
                    changes.append(("BHD", m["bhd"], value))
            if ftr_row["HEIGHT"] is not None:
                value = round(ftr_row["HEIGHT"]) if config.round_ftr_values else ftr_row["HEIGHT"]
                if m["height"] is None or m["height"] < value:
                    changes.append(("HEIGHT", m["height"], value))

            # VOLUME/VOLUME_TEMP wymagają formuły z FAS — sprawdź density.
            needs_volume = m["volume"] is None or m["volume_temp"] is None
            if needs_volume:
                if density is None:
                    report.skip(m["pk"], "VOLUME",
                                f"brak FAS dla ARODES={m['arodes']}",
                                arodes_int_num=arodes)
                else:
                    masa = obliczona_masa(
                        ftr_row["VOLUME"], density, part_cd,
                        config.volume_zero_replacement,
                        config.volume_formula_coefficient,
                    )
                    if m["volume"] is None:
                        changes.append(("VOLUME", m["volume"], masa))
                    if m["volume_temp"] is None:
                        changes.append(("VOLUME_TEMP", m["volume_temp"], masa))

            if changes:
                plan.append({"pk": m["pk"], "changes": changes})

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

    cursor.execute(
        f"UPDATE {fss} SET SITE_CLASS_CD = Trim(SITE_CLASS_CD) "
        f"WHERE SITE_CLASS_CD IS NOT NULL"
    )

    session.commit(affected_rows=report.changed)
    report.version_id = session.version_id
    report.write()
    return report
