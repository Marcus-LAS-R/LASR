"""Cienka warstwa nad `pyodbc` — połączenie z MDB i pomocnicze zapytania.

Cel
---
Wyizolować całą wiedzę o sterowniku ODBC i kwerendach systemowych w jednym
miejscu. Reszta `core/*` operuje na obiekcie kursora (mockowanego w testach
przez FakeCursor) i nie wie nic o tym, że pod spodem jest Access.

Zależności środowiskowe (Windows-only)
--------------------------------------
* Pakiet Python `pyodbc` (`pip install pyodbc` w Pythonie QGIS-a).
* Sterownik systemowy „Microsoft Access Driver (*.mdb, *.accdb)" —
  instalowany razem z „Microsoft Access Database Engine 2016 Redistributable".
* Sterownik MUSI mieć tę samą bitność co Python (32 vs 64) — najczęstsza
  przyczyna „Data source name not found" w VM.

Na Macu pyodbc nie jest instalowane — `tests/conftest.py` stubuje moduł.
"""

import pyodbc


def connect(mdb_path):
    """Otwiera połączenie do pliku MDB/ACCDB w trybie ręcznego commitu.

    `autocommit=False` jest ŚWIADOMĄ decyzją — wszystkie operacje F1–F4 i
    rollback chcą atomowych transakcji (cała wersja albo nic). Connection
    musi być potem domknięte przez `conn.close()` w wywołującym (zwykle
    `finally` w `MainDialog._run_operation`).

    Args:
        mdb_path: Pełna ścieżka do pliku `.mdb`/`.accdb`. Musi istnieć —
            sterownik Access nie tworzy plików.

    Returns:
        Obiekt `pyodbc.Connection`.

    Raises:
        pyodbc.Error: Gdy sterownik nie jest zainstalowany, plik nie istnieje
            albo bitność sterownika nie pasuje do Pythona.
    """
    conn_str = (
        "DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={mdb_path};"
    )
    return pyodbc.connect(conn_str, autocommit=False)


def table_exists(cursor, table_name):
    """Sprawdza, czy w bazie istnieje tabela o danej nazwie.

    Używa metadanych ODBC (`cursor.tables(table=..., tableType='TABLE')`)
    zamiast `SELECT 1 FROM tablename`, bo to drugie wywala wyjątek i przy
    okazji może popsuć transakcję.

    Algorytm:

    1. Spytaj sterownik o tabele o nazwie `table_name`.
    2. Iteruj wynik i sprawdź dokładne dopasowanie (case-sensitive, Access
       jest case-insensitive dla nazw, ale wynik metadanych zwraca taką
       jak w katalogu — porównujemy 1:1).
    3. Każdy `pyodbc.Error` (np. wadliwa sesja) → False — wywołujący ma
       fallback (tworzy tabelę, gdy nie istnieje).

    Args:
        cursor: Obiekt `pyodbc.Cursor` (lub kompatybilny — w testach FakeCursor).
        table_name: Nazwa tabeli do sprawdzenia.

    Returns:
        True jeśli tabela istnieje, False w przeciwnym razie lub przy błędzie.
    """
    try:
        rows = cursor.tables(table=table_name, tableType="TABLE").fetchall()
        return any(r.table_name == table_name for r in rows)
    except pyodbc.Error:
        return False


def fetch_dicts(cursor, sql, params=None):
    """Wykonuje SELECT i zwraca wyniki jako listę słowników `{kolumna: wartość}`.

    Wygodniejsze niż natywne krotki pyodbc, gdy chcemy odwoływać się do pól
    po nazwie. Funkcja zaimportowana defensywnie — nie jest używana wewnątrz
    F1–F4 (tam preferujemy ręczne rozpakowywanie krotek dla wydajności),
    ale przydatna w eksploracji bazy/ad-hoc skryptach.

    Args:
        cursor: Obiekt kursora.
        sql: Tekst SQL z parametryzacją `?` (Access ODBC).
        params: Lista parametrów do bind lub None.

    Returns:
        Lista słowników z kolumnami SELECT-a.
    """
    cursor.execute(sql, params or [])
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]
