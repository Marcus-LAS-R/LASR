"""F4 — Korekta `BHD < HEIGHT` (pierśnica nie może być mniejsza od wysokości).

Cel operacji
------------
Fizyczna nieścisłość: w drzewostanie pierśnica (BHD — diameter at breast
height, mierzona w cm) wyrażona w tych samych jednostkach co wysokość
nie może być od niej mniejsza. W bazach klienta zdarzają się takie błędy
po pomiarach. F4 je wykrywa i koryguje:

1. Wczytaj wzorzec z `F_TABLICA_ROZSZERZONA` po
   `(SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD)`.
2. `kandydat = FTR.BHD` (z opcjonalnym zaokrągleniem — D2.3).
3. Jeśli `kandydat ≥ HEIGHT` → `BHD := kandydat` (preferowane —
   wartość z tablicy wzorcowej).
4. Jeśli `kandydat < HEIGHT` → `BHD := HEIGHT` (twardy fallback —
   instrukcja wymusza zachowanie nierówności BHD ≥ HEIGHT).
5. Jeśli BRAK rekordu w FTR → ten sam fallback `BHD := HEIGHT`, jeśli
   `config.f4_fallback_bhd_equals_height` (D4.1 — domyślnie True).
   Inaczej tylko raport, bez UPDATE.

Filtr operacji
--------------
* `STOREY_CD = 'DRZEW'`
* `PART_CD ∈ 1..10`
* `BHD IS NOT NULL AND HEIGHT IS NOT NULL AND BHD < HEIGHT`
  (filtr na poziomie SQL — od razu wycina rekordy poprawne, brak
  marnowania pamięci na wczytywanie zdrowych danych).

D4.2 — odrzucamy obecną w starym kodzie logikę „HEIGHT + offset wg klasy
wiekowej". Nie ma jej w instrukcji.

Wynik
-----
Pole zmieniane: `BHD` (tylko dla rekordów wchodzących pod filtr).
"""

from .formula import parse_part_cd
from .lookups import load_ftr
from .reporting import Report
from .versioning import VersionManager


OPERATION = "F4"
PK = "SPEC_STOR_INT_NUM"


def run(conn, config, mdb_path, dry_run, user_note=""):
    """Wykonuje F4 — korekta BHD dla rekordów gdzie BHD<HEIGHT.

    Algorytm
    --------
    1. **Wczytaj `by_key` z FTR** (drugi indeks `by_species` niepotrzebny).

    2. **SELECT rekordów FSS** z pełnym filtrem `BHD<HEIGHT` (po stronie SQL,
       nie iterujemy zdrowych rekordów).

    3. **Pętla po wierszach**:
       a. Parsuj `PART_CD`. None → cichy skip (poza filtrem).
       b. Pobierz `ftr_row` z `by_key`. Brak lub `FTR.BHD IS NULL`:
          - `fallback_bhd_equals_height = True` → `new_bhd = HEIGHT`,
            wpis do raportu (informacyjny — operator wie, że fallback ruszył).
          - `False` → tylko wpis do raportu, kontynuuj bez zmiany.
       c. Jest FTR → `candidate = round(FTR.BHD)` (D2.3) lub bez round.
          - `candidate ≥ HEIGHT` → `new_bhd = candidate` (preferowane).
          - `candidate < HEIGHT` → `new_bhd = HEIGHT` (fallback hard, bo
            instrukcja wymaga BHD ≥ HEIGHT).
       d. Jeśli `new_bhd == bhd` (nic by się nie zmieniło) → pomijamy
          dodawanie do planu (nie generujemy zbędnych UPDATE-ów).
       e. Inaczej do `plan`: `[("BHD", bhd, new_bhd)]`.

    4. **Dry-run**: tylko liczniki + raport.

    5. **Commit**: standardowy flow z `VersionManager` — per wpis JEDEN
       UPDATE i JEDEN snapshot (F4 zmienia tylko jedną kolumnę).

    Args:
        conn: Połączenie do MDB.
        config: Konfiguracja (fallback flag, tabele).
        mdb_path: Ścieżka pliku — do raportu.
        dry_run: True → bez UPDATE.
        user_note: Notatka GUI.

    Returns:
        Instancja `Report` z licznikami i listą pominięć.
    """
    report = Report(OPERATION, mdb_path, dry_run)
    fss = config.table("fss")
    cursor = conn.cursor()

    ftr_by_key, _ = load_ftr(cursor, config.table("ftr"))

    cursor.execute(
        f"SELECT {PK}, ARODES_INT_NUM, SPECIES_CD, SPECIES_AGE, SITE_CLASS_CD, "
        f"PART_CD, BHD, HEIGHT "
        f"FROM {fss} "
        f"WHERE STOREY_CD = '{config.storey_drzew}' "
        f"AND BHD IS NOT NULL AND HEIGHT IS NOT NULL AND BHD < HEIGHT"
    )
    rows = cursor.fetchall()

    plan = []
    for pk, arodes, species, age, site_class, part_cd_raw, bhd, height in rows:
        report.processed += 1
        part_cd = parse_part_cd(part_cd_raw, config.part_cd_min, config.part_cd_max)
        if part_cd is None:
            # Rekord poza filtrem (np. PART='MJS') — cichy skip.
            continue

        # FTR ma klucze stripowane (Access CHAR padding) — czyścimy też FSS.
        site_class = site_class.strip() if isinstance(site_class, str) else site_class
        # Guard: IA tylko dla SO* — dla pozostałych gatunków używamy I do lookupa.
        if site_class == "IA" and not (species or "").startswith("SO"):
            site_class = "I"
        ftr_row = ftr_by_key.get((species, age, site_class))
        if ftr_row is None or ftr_row["BHD"] is None:
            # Brak wzorca w FTR — działanie zależy od flagi z configu (D4.1).
            if not config.f4_fallback_bhd_equals_height:
                report.skip(pk, "BHD",
                            f"brak FTR dla ({species},{age},{site_class}); fallback wyłączony",
                            arodes_int_num=arodes)
                continue
            new_bhd = height
            report.skip(pk, "BHD",
                        f"brak FTR dla ({species},{age},{site_class}); fallback BHD=HEIGHT",
                        arodes_int_num=arodes)
        else:
            candidate = round(ftr_row["BHD"]) if config.round_ftr_values else ftr_row["BHD"]
            if candidate >= 2 * height:
                # Anomalia — FTR.BHD ponad 2x HEIGHT: dane podejrzane, nie ruszamy.
                report.anomaly_bhd.append({
                    "pk_value": pk, "arodes_int_num": arodes,
                    "bhd": bhd, "height": height, "candidate": candidate,
                })
                continue
            new_bhd = candidate if candidate >= height else height

        if new_bhd == bhd:
            # Wyliczona wartość taka sama jak obecna — UPDATE byłby no-op.
            continue

        plan.append({"pk": pk, "changes": [("BHD", bhd, new_bhd)]})

    if dry_run:
        report.changed = len(plan)
        report.write()
        return report

    versions = VersionManager(conn, config)
    session = versions.open(OPERATION, user_note=user_note)
    for entry in plan:
        pk = entry["pk"]
        col, old, new = entry["changes"][0]
        cursor.execute(f"UPDATE {fss} SET {col} = ? WHERE {PK} = ?", [new, pk])
        session.record_change(
            table=fss, pk_field=PK, pk_value=pk,
            column=col, old_value=old, new_value=new,
        )
        report.changed += 1

    session.commit(affected_rows=report.changed)
    report.version_id = session.version_id
    report.write()
    return report
