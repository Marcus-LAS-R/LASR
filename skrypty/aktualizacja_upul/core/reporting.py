"""Raport tekstowy operacji F1–F4 — zapisywany obok pliku MDB.

Cel
---
Każda operacja (dry-run lub commit) tworzy plik `.txt` z podsumowaniem:

* metadane (operacja, tryb, timestamp, ścieżka MDB, VERSION_ID przy commit),
* liczniki (przetworzono / zmieniono / pominięto),
* tabela pominięć (`SPEC_STOR_INT_NUM`, `ARODES_INT_NUM`, kolumna, powód).

Klient ma dzięki temu audytowalną „receptę" co plugin zrobił bez konieczności
otwierania bazy. Pliki nie są kasowane — narastają w katalogu MDB. Klient
sam czyści, jeśli zaczyna być ich za dużo (D0.5 — brak limitu).
"""

import datetime
import os


class Report:
    """Zbiera wyniki operacji i serializuje je do pliku tekstowego.

    Typowy cykl użycia w `core/f*_*.py`:

    1. `report = Report('F1', mdb_path, dry_run=True)` na początku operacji.
    2. W pętli po rekordach: `report.processed += 1`, ewentualnie
       `report.skip(pk, kol, powod)` przy pominięciu.
    3. Po committed-version: `report.version_id = session.version_id`,
       `report.changed += N`.
    4. Na końcu: `report.write()` — zwraca ścieżkę pliku.

    Attributes:
        operation: Identyfikator operacji ('F1'/'F2'/'F3'/'F4') — do nazwy
            pliku i nagłówka raportu.
        mdb_path: Ścieżka pliku bazy — raport ląduje w tym samym katalogu.
        dry_run: True jeśli operacja była dry-run (wpływa na nazwę pliku i
            sekcję „Tryb" w nagłówku).
        started_at: `datetime` momentu utworzenia raportu — używany do
            timestampu w nazwie pliku.
        processed: Liczba rekordów wchodzących pod filtr operacji.
        changed: Liczba rekordów faktycznie zaplanowanych/zmienionych.
        skipped: Lista słowników opisujących pominięte rekordy.
        version_id: VERSION_ID z `_LRT_VERSIONS` (tylko commit, inaczej None).
    """

    def __init__(self, operation, mdb_path, dry_run):
        """Konstruktor — inicjalizuje liczniki na zero i zapamiętuje kontekst.

        Args:
            operation: Identyfikator operacji ('F1'..'F4', 'ROLLBACK').
            mdb_path: Ścieżka pliku MDB (do umieszczenia raportu obok).
            dry_run: Czy operacja była uruchomiona w trybie dry-run.
        """
        self.operation = operation
        self.mdb_path = mdb_path
        self.dry_run = dry_run
        self.started_at = datetime.datetime.now()
        self.processed = 0
        self.changed = 0
        self.skipped = []
        self.fallback_ones = []
        self.anomaly_bhd = []
        self.version_id = None
        self.report_path = None

    def skip(self, pk_value, column, reason, arodes_int_num=None):
        """Rejestruje rekord pominięty wraz z powodem.

        Operacje F1–F4 wołają tę metodę zawsze, gdy rekord wchodzi pod filtr,
        ale nie da się go bezpiecznie zmienić (NULL w kluczowej kolumnie,
        brak FTR/FAS, dominant bez bonitacji, itp.).

        Args:
            pk_value: Wartość klucza głównego rekordu (`SPEC_STOR_INT_NUM`).
            column: Nazwa kolumny, której dotyczy pominięcie (do diagnozy
                w raporcie — np. „HEIGHT", „BHD/HEIGHT/VOLUME").
            reason: Krótki, czytelny powód po polsku (np. „brak FTR dla
                (SO,40,II)").
            arodes_int_num: Opcjonalnie ARODES_INT_NUM — kolumna w tabeli
                pominięć, pozwala klientowi szybko zlokalizować wydzielenie.
        """
        self.skipped.append({
            "pk_value": pk_value,
            "arodes_int_num": arodes_int_num,
            "column": column,
            "reason": reason,
        })

    def write(self):
        """Zapisuje raport do pliku `.txt` obok pliku MDB.

        Algorytm:

        1. Zbuduj nazwę: `raport_{operation}_{commit|dryrun}_{timestamp}.txt`.
           Timestamp jest „kompaktowy" (`YYYYMMDD_HHMMSS`) — w katalogu kilka
           raportów sortuje się alfabetycznie chronologicznie.
        2. Otwórz plik w UTF-8 (polskie znaki w powodach pominięć).
        3. Nagłówek: operacja, tryb, ścieżka MDB, czas startu, VERSION_ID
           (jeśli to commit), liczniki.
        4. Sekcja „POMINIĘTE" z tabelą TSV:
           `SPEC_STOR_INT_NUM | ARODES_INT_NUM | KOLUMNA | POWÓD`.
           Format TSV bo łatwo wkleić do Excela do dalszej analizy.

        Returns:
            Ścieżka utworzonego pliku — używane przez GUI do otwarcia pliku
            po commit.

        Raises:
            FileNotFoundError: Gdy katalog pliku MDB nie istnieje (świadomy
                fail-fast — `mdb_path` powinien być sprawdzony wcześniej).
        """
        mdb_dir = os.path.dirname(self.mdb_path)
        ts = self.started_at.strftime("%d-%m-%Y_%H-%M-%S")
        mode = "dryrun" if self.dry_run else "commit"
        path = os.path.join(mdb_dir, f"raport_{self.operation}_{mode}_{ts}.txt")

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Operacja: {self.operation}\n")
            f.write(f"Tryb: {'DRY-RUN' if self.dry_run else 'COMMIT'}\n")
            f.write(f"Plik MDB: {self.mdb_path}\n")
            f.write(f"Start: {self.started_at.isoformat(timespec='seconds')}\n")
            if self.version_id is not None:
                f.write(f"VERSION_ID: {self.version_id}\n")
            f.write(f"Rekordy przetworzone: {self.processed}\n")
            f.write(f"Rekordy zmienione: {self.changed}\n")
            f.write(f"Rekordy pominięte: {len(self.skipped)}\n")
            if self.fallback_ones:
                f.write(f"Rekordy uzupełnione wartością 1: {len(self.fallback_ones)}\n")
            f.write("\n=== POMINIĘTE ===\n")
            f.write("SPEC_STOR_INT_NUM\tARODES_INT_NUM\tKOLUMNA\tPOWÓD\n")
            for s in self.skipped:
                f.write(
                    f"{s['pk_value']}\t"
                    f"{s['arodes_int_num'] if s['arodes_int_num'] is not None else ''}\t"
                    f"{s['column']}\t{s['reason']}\n"
                )
            if self.fallback_ones:
                f.write("\n=== UZUPEŁNIONE WARTOŚCIĄ 1 (VOLUME/VOLUME_TEMP) ===\n")
                f.write("SPEC_STOR_INT_NUM\tARODES_INT_NUM\tKOLUMNA\n")
                for r in self.fallback_ones:
                    f.write(
                        f"{r['pk_value']}\t"
                        f"{r['arodes_int_num'] if r['arodes_int_num'] is not None else ''}\t"
                        f"{r['column']}\n"
                    )
            if self.anomaly_bhd:
                f.write("\n=== ANOMALIE BHD (candidate >= 2x HEIGHT — bez zmian) ===\n")
                f.write("SPEC_STOR_INT_NUM\tARODES_INT_NUM\tBHD_obecne\tHEIGHT\tBHD_FTR\n")
                for r in self.anomaly_bhd:
                    f.write(
                        f"{r['pk_value']}\t"
                        f"{r['arodes_int_num'] if r['arodes_int_num'] is not None else ''}\t"
                        f"{r['bhd']}\t{r['height']}\t{r['candidate']}\n"
                    )
        self.report_path = path
        return path
