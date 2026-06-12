"""Wersjonowanie i rollback operacji F1–F4 — infrastruktura wspólna.

Cel
---
Każdy commit dowolnej operacji (F1/F2/F3/F4) tworzy **wersję** w bazie:

1. Wpis w `_LRT_VERSIONS` z metadanymi (id, operacja, timestamp, status,
   liczba zmienionych rekordów, opcjonalna notatka użytkownika).
2. Zestaw wpisów w `_LRT_SNAPSHOTS` (long format, jeden wiersz = jedno
   zmienione pole) z PARĄ `OLD_VALUE` / `NEW_VALUE`.

Pozwala to później:

* przeglądać historię zmian w GUI (`gui/version_browser.py`),
* eksportować wersję do CSV dla audytu,
* przywrócić poprzedni stan rekordów (`rollback()`).

Decyzje projektowe (zatwierdzone defaulty z `_draft-analiza-instrukcji.md`):

* D0.1 — snapshoty są w tej samej bazie MDB (nie w osobnym pliku).
* D0.2 — granulacja per-pole (long format) — kompakt i precyzyjnie.
* D0.4 — tabele `_LRT_*` są tworzone automatycznie przy pierwszym commicie.
* D0.5 — brak limitu wersji; klient ręcznie czyści jeśli baza puchnie.

Modele
------
* `VersionManager` — fasada „na bazie": tworzy tabele, otwiera sesje,
  listuje wersje, robi rollback, eksportuje do CSV.
* `VersionSession` — kontekst pojedynczej operacji: zbiera zmiany do bufora
  i flush-uje je w `commit()`.
"""

import datetime

from .db import table_exists


# Stałe statusu wersji w tabeli `_LRT_VERSIONS`.
# „committed" — operacja zapisana, zmiany aktywne w bazie.
# „rolled_back" — wersja była commitnięta, ale później cofnięta.
STATUS_COMMITTED = "committed"
STATUS_ROLLED_BACK = "rolled_back"


class VersionManager:
    """Fasada do operacji na rejestrze wersji w jednej bazie MDB.

    Tworzona raz per połączenie. Wszystkie metody używają tego samego
    `conn.cursor()` — to bezpieczne, bo operacje są sekwencyjne.

    Attributes:
        conn: Otwarte połączenie `pyodbc.Connection` (w testach FakeConnection).
        config: Obiekt `Config` — używany do pobrania nazw tabel
            (`_LRT_VERSIONS`, `_LRT_SNAPSHOTS`, `F_STOREY_SPECIES`).
        versions_table: Nazwa tabeli rejestru (zwykle `_LRT_VERSIONS`).
        snapshots_table: Nazwa tabeli snapshotów (zwykle `_LRT_SNAPSHOTS`).
    """

    def __init__(self, conn, config):
        """Konstruktor — zapamiętuje uchwyty, nie dotyka jeszcze bazy.

        Args:
            conn: Otwarte połączenie do MDB.
            config: Instancja `Config` z nazwami tabel.
        """
        self.conn = conn
        self.config = config
        self.versions_table = config.table("versions")
        self.snapshots_table = config.table("snapshots")

    def ensure_tables(self):
        """Tworzy `_LRT_VERSIONS`/`_LRT_SNAPSHOTS` jeśli jeszcze nie istnieją.

        D0.4 — pierwszy commit u nowego klienta sam tworzy infrastrukturę,
        klient nie musi nic ręcznie szykować. Wywoływane przez `open()` na
        starcie każdej sesji wersji.

        Schemat tabel zaprojektowany pod Access SQL (typy `LONG`, `TEXT(n)`,
        `DATETIME`). `OLD_VALUE` i `NEW_VALUE` są tekstowe — uniwersalny cast
        (D0.2), kosztem utraty typu źródłowego (przy rollback liczymy na
        sterownik ODBC, że zamieni string z powrotem na liczbę).

        Idempotentne: po obu sprawdzeniach commitujemy raz, nawet jeśli nic
        nie utworzono.
        """
        cursor = self.conn.cursor()
        if not table_exists(cursor, self.versions_table):
            # Nawiasy kwadratowe wokół [TIMESTAMP] i [STATUS] — to słowa
            # zarezerwowane w Access SQL, bez escape `Syntax error in field
            # definition`.
            cursor.execute(
                f"CREATE TABLE [{self.versions_table}] ("
                "[VERSION_ID] LONG, "
                "[OPERATION] TEXT(16), "
                "[TIMESTAMP] DATETIME, "
                "[USER_NOTE] TEXT(255), "
                "[AFFECTED_ROWS] LONG, "
                "[STATUS] TEXT(16)"
                ")"
            )
        if not table_exists(cursor, self.snapshots_table):
            cursor.execute(
                f"CREATE TABLE [{self.snapshots_table}] ("
                "[VERSION_ID] LONG, "
                "[TABLE_NAME] TEXT(64), "
                "[PK_FIELD] TEXT(64), "
                "[PK_VALUE] LONG, "
                "[COLUMN_NAME] TEXT(64), "
                "[OLD_VALUE] TEXT(255), "
                "[NEW_VALUE] TEXT(255)"
                ")"
            )
        self.conn.commit()

    def next_version_id(self):
        """Zwraca następny wolny `VERSION_ID` (MAX+1).

        Nie używamy `AUTOINCREMENT` Accessa, bo:

        * tabela jest tworzona przez plugin, a Access wymaga osobnego
          DDL dla autoincrement, co komplikuje cross-version support;
        * MAX+1 jest atomowe w ramach naszej transakcji (sesja Pythona to
          jeden writer).

        Returns:
            Int — najnowszy używany VERSION_ID powiększony o 1. Dla pustej
            tabeli zwraca 1.
        """
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT MAX(VERSION_ID) FROM {self.versions_table}")
        row = cursor.fetchone()
        return (row[0] or 0) + 1

    def open(self, operation, user_note=""):
        """Otwiera nową sesję wersji dla pojedynczej operacji.

        Wzorzec: F1/F2/F3/F4 (i sam rollback) wołają `open(...)` na początku
        swojej fazy commit, rejestrują wszystkie zmiany przez `record_change`,
        a na końcu `commit(affected_rows)` zapisuje wersję + snapshoty.

        Args:
            operation: Identyfikator operacji ('F1'..'F4', 'ROLLBACK').
            user_note: Opcjonalna notatka z GUI (np. „test po Jankowicach").

        Returns:
            Obiekt `VersionSession` z nadanym `version_id`.
        """
        self.ensure_tables()
        return VersionSession(
            conn=self.conn,
            versions_table=self.versions_table,
            snapshots_table=self.snapshots_table,
            version_id=self.next_version_id(),
            operation=operation,
            user_note=user_note,
        )

    def list_versions(self):
        """Zwraca listę wersji od najnowszej do najstarszej.

        Używane w GUI do zaludnienia tabeli wersji i dropdown-u rollback-u.
        Bezpieczne dla nowej bazy — zwraca pustą listę gdy tabela jeszcze
        nie istnieje (klient nie musi nic prewencyjnie tworzyć).

        Returns:
            Lista słowników z kluczami: `version_id`, `operation`, `timestamp`,
            `user_note`, `affected_rows`, `status`.
        """
        cursor = self.conn.cursor()
        if not table_exists(cursor, self.versions_table):
            return []
        cursor.execute(
            f"SELECT VERSION_ID, OPERATION, [TIMESTAMP], USER_NOTE, AFFECTED_ROWS, [STATUS] "
            f"FROM {self.versions_table} ORDER BY VERSION_ID DESC"
        )
        return [
            {
                "version_id": r[0],
                "operation": r[1],
                "timestamp": r[2],
                "user_note": r[3],
                "affected_rows": r[4],
                "status": r[5],
            }
            for r in cursor.fetchall()
        ]

    def current_version(self):
        """Najnowsza wersja w bazie — pojedynczy dict albo None.

        Używana w `MainDialog` do etykiety „Wersja bazy: …" — daje
        natychmiastową informację, co plugin ostatnio zrobił z tym plikiem
        (niezależnie od tego, czy stan operacji to `committed` czy
        `rolled_back` — w obu przypadkach ważne, że TO BYŁA ostatnia akcja).

        Returns:
            Dict (jak w `list_versions`) lub None gdy baza nie ma `_LRT_VERSIONS`
            (nigdy nieruszana) albo tabela jest pusta.
        """
        cursor = self.conn.cursor()
        if not table_exists(cursor, self.versions_table):
            return None
        cursor.execute(
            f"SELECT VERSION_ID, OPERATION, [TIMESTAMP], USER_NOTE, AFFECTED_ROWS, [STATUS] "
            f"FROM {self.versions_table} ORDER BY VERSION_ID DESC"
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return {
            "version_id": row[0],
            "operation": row[1],
            "timestamp": row[2],
            "user_note": row[3],
            "affected_rows": row[4],
            "status": row[5],
        }

    def get_snapshots(self, version_id):
        """Pobiera wszystkie pola zmienione w jednej wersji.

        Używane w GUI (tab „Wersje" → panel szczegółów po zaznaczeniu
        wersji) i przez `rollback()` (do odtworzenia OLD_VALUE).

        Wynik sortowany po `PK_VALUE, COLUMN_NAME` — daje czytelne grupowanie
        „dla rekordu X zmieniono: kolumna A, B, C".

        Args:
            version_id: Identyfikator wersji w `_LRT_VERSIONS`.

        Returns:
            Lista słowników: `table`, `pk_field`, `pk_value`, `column`,
            `old_value`, `new_value`. Pusta lista gdy tabela snapshotów nie
            istnieje lub wersja nie ma snapshotów (np. rollback bez zmian).
        """
        cursor = self.conn.cursor()
        if not table_exists(cursor, self.snapshots_table):
            return []
        cursor.execute(
            f"SELECT TABLE_NAME, PK_FIELD, PK_VALUE, COLUMN_NAME, OLD_VALUE, NEW_VALUE "
            f"FROM {self.snapshots_table} WHERE VERSION_ID = ? "
            f"ORDER BY PK_VALUE, COLUMN_NAME",
            [version_id],
        )
        return [
            {
                "table": r[0],
                "pk_field": r[1],
                "pk_value": r[2],
                "column": r[3],
                "old_value": r[4],
                "new_value": r[5],
            }
            for r in cursor.fetchall()
        ]

    def get_record_history(self, pk_value, table=None, pk_field=None):
        """Historia zmian jednego rekordu — przekrój wszystkich wersji.

        Używane w GUI (tab „Rekord") — operator wpisuje `SPEC_STOR_INT_NUM`
        i widzi w kolejności chronologicznej, KTÓRA operacja, KIEDY i CO
        zmieniła w tym konkretnym rekordzie.

        Algorytm:

        1. JOIN `_LRT_SNAPSHOTS s` ↔ `_LRT_VERSIONS v` po `VERSION_ID`.
        2. Filtr `s.PK_VALUE = ?` + `TABLE_NAME` + `PK_FIELD` (parametry
           wiążemy `?` — nie sklejamy stringów, chronimy się przed SQLi
           nawet w naszej lokalnej bazie).
        3. Sortowanie po `VERSION_ID` rosnąco → chronologicznie, najstarsza
           zmiana u góry.

        Args:
            pk_value: Wartość klucza (`SPEC_STOR_INT_NUM`).
            table: Nazwa tabeli operacyjnej. Domyślnie `config.table('fss')`.
            pk_field: Nazwa kolumny klucza. Domyślnie `SPEC_STOR_INT_NUM`.

        Returns:
            Lista słowników z kluczami `version_id`, `operation`, `timestamp`,
            `status`, `column`, `old_value`, `new_value`. Pusta lista gdy
            tabela snapshotów nie istnieje lub rekord nigdy nie był ruszany.
        """
        cursor = self.conn.cursor()
        if not table_exists(cursor, self.snapshots_table):
            return []
        table = table or self.config.table("fss")
        pk_field = pk_field or "SPEC_STOR_INT_NUM"
        cursor.execute(
            f"SELECT s.VERSION_ID, v.OPERATION, v.[TIMESTAMP], v.[STATUS], "
            f"s.COLUMN_NAME, s.OLD_VALUE, s.NEW_VALUE "
            f"FROM {self.snapshots_table} s INNER JOIN {self.versions_table} v "
            f"ON s.VERSION_ID = v.VERSION_ID "
            f"WHERE s.PK_VALUE = ? AND s.TABLE_NAME = ? AND s.PK_FIELD = ? "
            f"ORDER BY s.VERSION_ID, s.COLUMN_NAME",
            [pk_value, table, pk_field],
        )
        return [
            {
                "version_id": r[0],
                "operation": r[1],
                "timestamp": r[2],
                "status": r[3],
                "column": r[4],
                "old_value": r[5],
                "new_value": r[6],
            }
            for r in cursor.fetchall()
        ]

    def export_version_csv(self, version_id, path):
        """Zapisuje wersję wraz ze snapshotami do pliku CSV (separator `;`).

        Format wyjściowy (flat, jeden snapshot = jeden wiersz):

            VERSION_ID;OPERATION;TIMESTAMP;STATUS;USER_NOTE;TABLE;PK_FIELD;
            PK_VALUE;COLUMN;OLD_VALUE;NEW_VALUE

        Metadane wersji powtarzane są w każdym wierszu — kosztem redundancji
        zyskujemy „jeden plik = pełen kontekst", łatwy do zaimportowania do
        Excela czy analizy w pandas. Separator `;` (a nie `,`) bo polskie
        Excel-e mają domyślnie taką konfigurację (i wartości mogą zawierać
        przecinki).

        Specjalny przypadek: wersja bez snapshotów (np. rollback nie znalazł
        pól do cofnięcia) — zapisujemy 1 wiersz z metadanymi i pustymi
        kolumnami snapshotu, żeby plik miał spójną strukturę.

        Args:
            version_id: Identyfikator wersji do eksportu.
            path: Pełna ścieżka pliku wyjściowego (rozszerzenie `.csv`).

        Returns:
            Liczba snapshotów zapisanych (`len(snapshots)`). 0 oznacza
            wersję bez zmian pól (lub nieistniejącą — wtedy plik ma sam
            wiersz z pustymi metadanymi).
        """
        import csv

        meta = next((v for v in self.list_versions() if v["version_id"] == version_id), None)
        snapshots = self.get_snapshots(version_id)

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([
                "VERSION_ID", "OPERATION", "TIMESTAMP", "STATUS", "USER_NOTE",
                "TABLE", "PK_FIELD", "PK_VALUE", "COLUMN", "OLD_VALUE", "NEW_VALUE",
            ])
            if not snapshots:
                writer.writerow([
                    version_id,
                    meta["operation"] if meta else "",
                    meta["timestamp"] if meta else "",
                    meta["status"] if meta else "",
                    meta["user_note"] if meta else "",
                    "", "", "", "", "", "",
                ])
                return len(snapshots)
            for s in snapshots:
                writer.writerow([
                    version_id,
                    meta["operation"] if meta else "",
                    meta["timestamp"] if meta else "",
                    meta["status"] if meta else "",
                    meta["user_note"] if meta else "",
                    s["table"], s["pk_field"], s["pk_value"],
                    s["column"], s["old_value"], s["new_value"],
                ])
        return len(snapshots)

    def rollback(self, version_id, user_note=""):
        """Cofa wszystkie zmiany zarejestrowane w danej wersji.

        Algorytm:

        1. Wczytaj snapshoty `_LRT_SNAPSHOTS` dla `version_id`.
        2. Brak snapshotów → 0 (nic do cofania, np. ROLLBACK bez efektu).
        3. Otwórz NOWĄ sesję wersji o operacji `ROLLBACK` — sam rollback
           też dostaje swój wpis, żeby można było „cofnąć cofnięcie"
           i żeby historia była pełna.
        4. Dla każdego snapshotu:
           a. Pobierz BIEŻĄCĄ wartość pola z bazy (`_fetch_value`) — to
              będzie `OLD_VALUE` w nowym snapshocie ROLLBACK.
           b. UPDATE pola z powrotem na `OLD_VALUE` z oryginalnego snapshotu.
           c. Zapisz wpis w sesji ROLLBACK: stan przed cofnięciem → stan po.
           d. Dorzuć `pk_value` do zbioru zmienionych (do liczenia
              affected_rows — liczymy unikalne rekordy, nie pola).
        5. Commit sesji ROLLBACK (zapis do `_LRT_VERSIONS` + jej snapshotów).
        6. Oznacz oryginalną wersję jako `STATUS='rolled_back'` w
           `_LRT_VERSIONS` — żeby UI mogło ją wyróżnić.
        7. Globalny commit i zwrot liczby cofniętych pól (NIE rekordów —
           bo to bardziej szczegółowy miernik).

        Args:
            version_id: Wersja do cofnięcia.
            user_note: Opcjonalna notatka z GUI — łączy się z domyślnym
                opisem `"rollback Vxx :: <note>"`.

        Returns:
            Liczba przywróconych pól (rozmiar snapshotu). 0 gdy nic do
            cofania.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT TABLE_NAME, PK_FIELD, PK_VALUE, COLUMN_NAME, OLD_VALUE, NEW_VALUE "
            f"FROM {self.snapshots_table} WHERE VERSION_ID = ?",
            [version_id],
        )
        snapshots = cursor.fetchall()
        if not snapshots:
            return 0

        rollback_session = self.open("ROLLBACK", user_note=f"rollback V{version_id} :: {user_note}")
        affected_pks = set()

        for table_name, pk_field, pk_value, column_name, old_value, new_value in snapshots:
            current = self._fetch_value(cursor, table_name, pk_field, pk_value, column_name)
            cursor.execute(
                f"UPDATE {table_name} SET {column_name} = ? WHERE {pk_field} = ?",
                [_coerce(old_value), pk_value],
            )
            rollback_session.record_change(
                table=table_name,
                pk_field=pk_field,
                pk_value=pk_value,
                column=column_name,
                old_value=current,
                new_value=old_value,
            )
            affected_pks.add(pk_value)

        rollback_session.commit(affected_rows=len(affected_pks))
        cursor.execute(
            f"UPDATE {self.versions_table} SET [STATUS] = ? WHERE VERSION_ID = ?",
            [STATUS_ROLLED_BACK, version_id],
        )
        self.conn.commit()
        return len(snapshots)

    def _fetch_value(self, cursor, table, pk_field, pk_value, column):
        """Pomocnik — czyta aktualną wartość jednej kolumny dla danego klucza.

        Używane wewnątrz `rollback()` żeby zapisać „stan przed cofnięciem"
        w snapshocie ROLLBACK. Prywatne (`_`) — szczegół implementacyjny.

        Args:
            cursor: Aktywny kursor.
            table: Nazwa tabeli operacyjnej.
            pk_field: Kolumna klucza (np. `SPEC_STOR_INT_NUM`).
            pk_value: Wartość klucza.
            column: Nazwa kolumny do odczytania.

        Returns:
            Aktualna wartość pola lub None gdy rekord nie istnieje
            (skrajnie rzadkie — ktoś usunął rekord ręcznie między commitem
            a rollbackiem).
        """
        cursor.execute(
            f"SELECT {column} FROM {table} WHERE {pk_field} = ?", [pk_value]
        )
        row = cursor.fetchone()
        return row[0] if row else None


class VersionSession:
    """Bufor zmian dla jednej operacji — zbiera i flush-uje w `commit()`.

    Wzorzec: F1–F4 wołają `record_change(...)` raz na każde modyfikowane
    pole (NIE rekord — long format snapshotów). Wszystkie wpisy są
    przechowywane w pamięci do momentu `commit()`, kiedy idą JEDNYM batchem
    INSERT-ów wraz z wpisem w `_LRT_VERSIONS`.

    Dzięki temu cała operacja jest atomowa względem rejestru wersji:
    albo zapisuje się komplet (wersja + wszystkie snapshoty), albo
    nic (przy wyjątku robimy `conn.rollback()` w GUI).

    Attributes:
        conn: Połączenie DB.
        versions_table: Nazwa tabeli rejestru.
        snapshots_table: Nazwa tabeli snapshotów.
        version_id: Nadany ID wersji (z `next_version_id`).
        operation: Identyfikator operacji.
        user_note: Notatka z GUI.
        _pending: Lista krotek (table, pk_field, pk_value, column, old, new)
            do zapisania w commit-cie. Prywatna — nie modyfikować z zewnątrz.
    """

    def __init__(self, conn, versions_table, snapshots_table, version_id, operation, user_note):
        """Konstruktor — nie woła bazy, tylko inicjalizuje bufor.

        Args:
            conn: Połączenie DB.
            versions_table: Nazwa tabeli rejestru wersji.
            snapshots_table: Nazwa tabeli snapshotów.
            version_id: Numer wersji (już zarezerwowany).
            operation: 'F1'/'F2'/'F3'/'F4'/'ROLLBACK'.
            user_note: Opcjonalny opis od użytkownika.
        """
        self.conn = conn
        self.versions_table = versions_table
        self.snapshots_table = snapshots_table
        self.version_id = version_id
        self.operation = operation
        self.user_note = user_note
        self._pending = []

    def record_change(self, table, pk_field, pk_value, column, old_value, new_value):
        """Dodaje zmianę jednego pola do bufora — nie dotyka bazy.

        Args:
            table: Nazwa tabeli, której rekord zmienia.
            pk_field: Nazwa kolumny klucza.
            pk_value: Wartość klucza zmienianego rekordu.
            column: Nazwa zmienianej kolumny.
            old_value: Wartość przed zmianą (cokolwiek typu — castowane na
                string w commit-cie).
            new_value: Wartość po zmianie.
        """
        self._pending.append((table, pk_field, pk_value, column, old_value, new_value))

    def commit(self, affected_rows):
        """Flush bufora do bazy — wstawia wpis wersji + wszystkie snapshoty.

        Algorytm:

        1. Jeden INSERT do `_LRT_VERSIONS` z metadanymi (timestamp = teraz).
        2. Pętla po `_pending`: INSERT do `_LRT_SNAPSHOTS` per pole.
           Wartości OLD/NEW konwertowane przez `_stringify` (None pozostaje
           None, reszta → `str()`).
        3. `conn.commit()` — utrwalenie wszystkiego.

        Args:
            affected_rows: Liczba UNIKALNYCH rekordów zmienionych w operacji
                (rachunek robi wywołujący — F1/F2/F3/F4 — bo to różni się
                od liczby pól w `_pending`).
        """
        cursor = self.conn.cursor()
        cursor.execute(
            f"INSERT INTO {self.versions_table} "
            "(VERSION_ID, OPERATION, [TIMESTAMP], USER_NOTE, AFFECTED_ROWS, [STATUS]) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                self.version_id,
                self.operation,
                datetime.datetime.now(),
                self.user_note,
                affected_rows,
                STATUS_COMMITTED,
            ],
        )
        for table, pk_field, pk_value, column, old_value, new_value in self._pending:
            cursor.execute(
                f"INSERT INTO {self.snapshots_table} "
                "(VERSION_ID, TABLE_NAME, PK_FIELD, PK_VALUE, COLUMN_NAME, OLD_VALUE, NEW_VALUE) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    self.version_id,
                    table,
                    pk_field,
                    pk_value,
                    column,
                    _stringify(old_value),
                    _stringify(new_value),
                ],
            )
        self.conn.commit()


def _stringify(value):
    """Konwertuje wartość na string z zachowaniem None.

    Snapshoty trzymamy jako TEXT (D0.2 — uniwersalny cast). Wyjątek: None
    chcemy zachować jako prawdziwy NULL w bazie, żeby rollback umiał
    odróżnić „pole było puste" od „pole było stringiem 'None'".

    Args:
        value: Dowolna wartość (int, float, str, datetime, None).

    Returns:
        `str(value)` albo None.
    """
    if value is None:
        return None
    return str(value)


def _coerce(text_value):
    """Odwrotność `_stringify` przy rollbacku.

    Po wczytaniu snapshotu wartość jest stringiem (lub None). Access ODBC
    przy UPDATE liczbowej kolumny zaakceptuje stringa i sam zrobi cast.
    Jedyne czego musimy pilnować: jeśli historycznie zapisaliśmy string
    `"None"` (np. stary kod), traktujmy go jak prawdziwy NULL.

    Args:
        text_value: Wartość z `_LRT_SNAPSHOTS.OLD_VALUE`.

    Returns:
        None gdy wejście to None lub literalny "None", inaczej string
        do wstawienia w UPDATE.
    """
    if text_value is None or text_value == "None":
        return None
    return text_value
