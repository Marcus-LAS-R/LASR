"""Okno „Historia wersji" — przegląd rejestru `_LRT_VERSIONS` i diff snapshotów.

Cel
---
Daje operatorowi audytowalny widok WSZYSTKICH zmian zrobionych przez plugin:

* co, kiedy i przez kogo (notatka) zostało wykonane,
* które rekordy i które pola zmieniły wartość,
* historia per-rekord (jak ewoluował konkretny `SPEC_STOR_INT_NUM`),
* eksport do CSV — wymóg klientów dla audytu zewnętrznego.

Struktura
---------
Trzy obszary w jednym `QDialog`:

* **U góry** — etykieta `current_label` z bieżącą wersją bazy (HTML).
* **W środku** — `QTabWidget`:
  * Tab „Wersje": `versions_table` + `snapshots_table` poniżej.
  * Tab „Rekord": pole wpisania `SPEC_STOR_INT_NUM` + `history_table`.
* **Na dole** — wspólne przyciski: Odśwież / Eksport CSV / Zamknij.

Tabele są sortowalne (klik w nagłówek) i tylko-do-odczytu — to przeglądarka,
nie edytor. Wszystkie dane pochodzą z `VersionManager` (warstwa core).
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)


# Nazwy kolumn w trzech tabelach — single source of truth dla nagłówków i
# pomocnik przy ewentualnym dodaniu/przemianowaniu pola.
VERSION_COLUMNS = ["VERSION_ID", "OPERATION", "TIMESTAMP", "AFFECTED_ROWS", "STATUS", "USER_NOTE"]
SNAPSHOT_COLUMNS = ["PK_VALUE", "COLUMN", "OLD_VALUE", "NEW_VALUE"]
HISTORY_COLUMNS = ["VERSION_ID", "OPERATION", "TIMESTAMP", "STATUS", "COLUMN", "OLD_VALUE", "NEW_VALUE"]


class VersionBrowserDialog(QDialog):
    """Okno modalne — przeglądarka wersji i snapshotów.

    Otwierane przez `MainDialog._open_history()`. Trzymane open
    zwracając kontrolę po `accept()` (przycisk „Zamknij"). Połączeniem do
    bazy zarządza `MainDialog` — tutaj dostajemy gotowy `VersionManager`.

    Attributes:
        manager: Instancja `VersionManager` na otwartym connection.
        current_label: Etykieta HTML z bieżącą wersją bazy.
        versions_table: Tabela wszystkich wersji (`_LRT_VERSIONS`).
        snapshots_table: Tabela snapshotów zaznaczonej wersji.
        history_table: Tabela historii jednego rekordu.
        record_input: Pole wpisania `SPEC_STOR_INT_NUM` dla tabu „Rekord".
    """

    def __init__(self, manager, parent=None):
        """Konstruktor — buduje UI i od razu ładuje listę wersji.

        Args:
            manager: `VersionManager` na otwartym połączeniu.
            parent: QWidget rodzic (zwykle `MainDialog`).
        """
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("LAS_R_TOOL — historia wersji")
        self.resize(900, 600)
        self._build_ui()
        self._reload_versions()

    # ---- konstrukcja UI -----------------------------------------------------

    def _build_ui(self):
        """Składa wszystkie widgety w pionowy layout.

        Kolejność: etykieta wersji → `QTabWidget` z dwoma tabami →
        pasek akcji (Odśwież/Eksport/Zamknij).
        """
        layout = QVBoxLayout(self)

        self.current_label = QLabel()
        # RichText pozwala użyć <b>, <i>, <code> — czytelniejsza etykieta.
        self.current_label.setTextFormat(Qt.RichText)
        layout.addWidget(self.current_label)

        tabs = QTabWidget()
        tabs.addTab(self._build_versions_tab(), "Wersje")
        tabs.addTab(self._build_record_tab(), "Rekord")
        layout.addWidget(tabs)

        actions = QHBoxLayout()
        self.refresh_btn = QPushButton("Odśwież")
        self.refresh_btn.clicked.connect(self._reload_versions)
        self.export_btn = QPushButton("Eksport wybranej wersji do CSV…")
        self.export_btn.clicked.connect(self._export_selected_csv)
        close_btn = QPushButton("Zamknij")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(self.refresh_btn)
        actions.addWidget(self.export_btn)
        actions.addStretch(1)  # spych Zamknij na prawo
        actions.addWidget(close_btn)
        layout.addLayout(actions)

    def _build_versions_tab(self) -> QWidget:
        """Tab „Wersje" — dwie pionowo ustawione tabele (lista + szczegóły).

        Górna tabela (`versions_table`) listuje operacje z `_LRT_VERSIONS`.
        Dolna (`snapshots_table`) pokazuje zmienione pola wybranej wersji.

        Returns:
            Skonfigurowany `QWidget` gotowy do osadzenia w `QTabWidget`.
        """
        widget = QWidget()
        v = QVBoxLayout(widget)

        self.versions_table = QTableWidget(0, len(VERSION_COLUMNS))
        self.versions_table.setHorizontalHeaderLabels(VERSION_COLUMNS)
        # `SelectRows + SingleSelection` — klik wybiera CAŁY wiersz, jeden naraz.
        # To pasuje do semantyki „wybierz jedną wersję żeby zobaczyć jej snapshoty".
        self.versions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.versions_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.versions_table.setSortingEnabled(True)
        # `NoEditTriggers` — przeglądarka, nie edytor. Bez tego użytkownik
        # mógłby pomyłkowo dwukliknąć i wpisać tekst (tylko lokalnie, ale
        # myli interakcję).
        self.versions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.versions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        # Sygnał `itemSelectionChanged` — wywołuje się przy zmianie zaznaczenia
        # wiersza, więc snapshoty na dole odświeżają się natychmiast.
        self.versions_table.itemSelectionChanged.connect(self._on_version_selected)
        v.addWidget(QLabel("Lista operacji w `_LRT_VERSIONS` (kliknij wiersz → szczegóły poniżej):"))
        v.addWidget(self.versions_table, 2)  # stretch=2 — większy udział wysokości

        v.addWidget(QLabel("Zmienione pola (snapshoty z `_LRT_SNAPSHOTS`):"))
        self.snapshots_table = QTableWidget(0, len(SNAPSHOT_COLUMNS))
        self.snapshots_table.setHorizontalHeaderLabels(SNAPSHOT_COLUMNS)
        self.snapshots_table.setSortingEnabled(True)
        self.snapshots_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.snapshots_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        v.addWidget(self.snapshots_table, 3)  # stretch=3 — jeszcze więcej dla szczegółów

        return widget

    def _build_record_tab(self) -> QWidget:
        """Tab „Rekord" — wpisz PK, zobacz wszystkie zmiany w nim.

        Layout: poziomy wiersz z labelem + QLineEdit + przyciskiem „Pokaż",
        pod nim duża tabela `history_table` z wynikami JOIN-a po VERSION_ID.

        Returns:
            Skonfigurowany `QWidget`.
        """
        widget = QWidget()
        v = QVBoxLayout(widget)

        row = QHBoxLayout()
        row.addWidget(QLabel("SPEC_STOR_INT_NUM:"))
        self.record_input = QLineEdit()
        self.record_input.setPlaceholderText("np. 12345")
        # Enter w polu == klik w „Pokaż historię" — szybsze dla operatora,
        # który wpisuje serię PK-ów.
        self.record_input.returnPressed.connect(self._load_record_history)
        show_btn = QPushButton("Pokaż historię")
        show_btn.clicked.connect(self._load_record_history)
        row.addWidget(self.record_input, 1)
        row.addWidget(show_btn)
        v.addLayout(row)

        self.history_table = QTableWidget(0, len(HISTORY_COLUMNS))
        self.history_table.setHorizontalHeaderLabels(HISTORY_COLUMNS)
        self.history_table.setSortingEnabled(True)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        v.addWidget(self.history_table)

        return widget

    # ---- data loaders --------------------------------------------------------

    def _reload_versions(self):
        """Pobiera wersje z bazy i renderuje obie tabele od nowa.

        Wywoływane przy starcie i po kliknięciu „Odśwież". W przypadku błędu
        połączenia/zapytania pokazuje messagebox i pozostawia poprzedni stan UI
        (nie czyści tabel — operator nadal widzi „coś" zamiast pustego okna).
        """
        try:
            versions = self.manager.list_versions()
            current = self.manager.current_version()
        except Exception as e:
            QMessageBox.critical(self, "Błąd odczytu", str(e))
            return
        self._render_current(current)
        self._render_versions(versions)
        self._clear_table(self.snapshots_table)  # po reloadzie nie ma zaznaczenia

    def _render_current(self, current):
        """Aktualizuje etykietę „Wersja bazy" na górze okna.

        Args:
            current: Dict z `current_version()` albo None gdy baza pusta.
        """
        if current is None:
            self.current_label.setText(
                "<b>Wersja bazy:</b> brak wpisów w <code>_LRT_VERSIONS</code> "
                "(baza jeszcze nietknięta przez LAS_R_TOOL)."
            )
            return
        self.current_label.setText(
            f"<b>Wersja bazy:</b> V{current['version_id']} — "
            f"{current['operation']} — {current['timestamp']} — "
            f"<i>{current['status']}</i> — "
            f"rows={current['affected_rows']}"
        )

    def _render_versions(self, versions):
        """Wypełnia `versions_table` listą wersji.

        Sortowanie: wyłączamy na czas wypełniania (Qt by się gubił przy
        wstawianiu wierszy z aktywnym sort), włączamy po skończeniu.

        Args:
            versions: Lista dictów z `list_versions()`.
        """
        self.versions_table.setSortingEnabled(False)
        self.versions_table.setRowCount(len(versions))
        for r, v in enumerate(versions):
            self._set_cell(self.versions_table, r, 0, v["version_id"], numeric=True)
            self._set_cell(self.versions_table, r, 1, v["operation"])
            self._set_cell(self.versions_table, r, 2, v["timestamp"])
            self._set_cell(self.versions_table, r, 3, v["affected_rows"], numeric=True)
            self._set_cell(self.versions_table, r, 4, v["status"])
            self._set_cell(self.versions_table, r, 5, v["user_note"])
        self.versions_table.setSortingEnabled(True)
        self.versions_table.resizeColumnsToContents()

    def _on_version_selected(self):
        """Handler `itemSelectionChanged` — odświeża tabelę snapshotów.

        Algorytm:

        1. Pobierz `version_id` z aktualnie zaznaczonego wiersza
           (przez `Qt.UserRole` — odporne na sortowanie kolumn).
        2. Brak zaznaczenia → wyczyść `snapshots_table`.
        3. Pobierz snapshoty z managera, w razie błędu — messagebox.
        4. Wyrenderuj.
        """
        version_id = self._selected_version_id()
        if version_id is None:
            self._clear_table(self.snapshots_table)
            return
        try:
            snapshots = self.manager.get_snapshots(version_id)
        except Exception as e:
            QMessageBox.critical(self, "Błąd odczytu", str(e))
            return
        self._render_snapshots(snapshots)

    def _render_snapshots(self, snapshots):
        """Wypełnia `snapshots_table` — pola zmienione w jednej wersji.

        Args:
            snapshots: Lista dictów z `get_snapshots(version_id)`.
        """
        self.snapshots_table.setSortingEnabled(False)
        self.snapshots_table.setRowCount(len(snapshots))
        for r, s in enumerate(snapshots):
            self._set_cell(self.snapshots_table, r, 0, s["pk_value"], numeric=True)
            self._set_cell(self.snapshots_table, r, 1, s["column"])
            self._set_cell(self.snapshots_table, r, 2, s["old_value"])
            self._set_cell(self.snapshots_table, r, 3, s["new_value"])
        self.snapshots_table.setSortingEnabled(True)
        self.snapshots_table.resizeColumnsToContents()

    def _load_record_history(self):
        """Handler „Pokaż historię" — wczytuje historię jednego rekordu.

        Algorytm:

        1. Pobierz tekst z `record_input`. Pusty → nic nie rób (cichy ignore).
        2. Sparsuj jako int. Niepoprawny → `QMessageBox.warning`.
        3. `manager.get_record_history(pk)`. Błąd → messagebox.
        4. Wyrenderuj w `history_table`.
        """
        raw = self.record_input.text().strip()
        if not raw:
            return
        try:
            pk = int(raw)
        except ValueError:
            QMessageBox.warning(self, "Niepoprawny PK", "Podaj liczbę całkowitą.")
            return
        try:
            history = self.manager.get_record_history(pk)
        except Exception as e:
            QMessageBox.critical(self, "Błąd odczytu", str(e))
            return
        self._render_history(history)

    def _render_history(self, history):
        """Wypełnia `history_table` chronologiczną historią rekordu.

        Args:
            history: Lista dictów z `get_record_history(pk)`.
                Pusta lista → tabela wyzeruje wiersze (rekord nigdy nieruszany).
        """
        self.history_table.setSortingEnabled(False)
        self.history_table.setRowCount(len(history))
        for r, h in enumerate(history):
            self._set_cell(self.history_table, r, 0, h["version_id"], numeric=True)
            self._set_cell(self.history_table, r, 1, h["operation"])
            self._set_cell(self.history_table, r, 2, h["timestamp"])
            self._set_cell(self.history_table, r, 3, h["status"])
            self._set_cell(self.history_table, r, 4, h["column"])
            self._set_cell(self.history_table, r, 5, h["old_value"])
            self._set_cell(self.history_table, r, 6, h["new_value"])
        self.history_table.setSortingEnabled(True)
        self.history_table.resizeColumnsToContents()

    def _export_selected_csv(self):
        """Handler „Eksport CSV" — zapisuje wybraną wersję do pliku.

        Algorytm:

        1. Pobierz `version_id` z zaznaczonego wiersza. Brak → komunikat.
        2. `QFileDialog.getSaveFileName` z propozycją nazwy `wersja_V{id}.csv`.
        3. Anulowano (puste path) → koniec.
        4. `manager.export_version_csv(version_id, path)` → zwraca liczbę
           zapisanych wierszy. Błąd → messagebox.
        5. Sukces → messagebox z liczbą wierszy i ścieżką.
        """
        version_id = self._selected_version_id()
        if version_id is None:
            QMessageBox.information(self, "Eksport CSV", "Najpierw zaznacz wersję w tabeli.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Zapisz eksport CSV", f"wersja_V{version_id}.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            count = self.manager.export_version_csv(version_id, path)
        except Exception as e:
            QMessageBox.critical(self, "Błąd eksportu", str(e))
            return
        QMessageBox.information(
            self, "Eksport CSV",
            f"Zapisano {count} wierszy snapshotów do:\n{path}",
        )

    # ---- helpers -------------------------------------------------------------

    def _selected_version_id(self):
        """Zwraca `version_id` z zaznaczonego wiersza `versions_table` lub None.

        Czemu używamy `Qt.UserRole`, a nie `item.text()`?
        Po sortowaniu kolumn tekst widoczny w komórce może być przesortowany
        leksykograficznie („10" < „2" jako string), ale `Qt.UserRole`
        trzyma oryginalną wartość int (ustawioną w `_set_cell`).

        Returns:
            Int `version_id` lub None gdy nic nie zaznaczono / parser zawiódł.
        """
        row = self.versions_table.currentRow()
        if row < 0:
            return None
        item = self.versions_table.item(row, 0)
        if item is None:
            return None
        try:
            return int(item.data(Qt.UserRole) if item.data(Qt.UserRole) is not None else item.text())
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _set_cell(table, row, col, value, numeric=False):
        """Tworzy `QTableWidgetItem` z odpowiednim typem danych.

        Dla kolumn numerycznych ustawia `Qt.EditRole` jako int, co aktywuje
        prawidłowe sortowanie (numerycznie zamiast leksykograficznie).
        Wartość None → pusty tekst (czytelniej niż "None").

        Args:
            table: `QTableWidget` do którego wstawiamy.
            row, col: Pozycja komórki.
            value: Wartość do wyświetlenia (dowolnego typu).
            numeric: True → traktuj jako liczbę dla sortowania.
        """
        text = "" if value is None else str(value)
        item = QTableWidgetItem(text)
        if numeric and value is not None:
            try:
                item.setData(Qt.EditRole, int(value))
                item.setData(Qt.UserRole, int(value))
            except (TypeError, ValueError):
                # Wartość deklarowana jako numeric, ale nieprzeliczalna
                # (np. „rolled_back" w niewłaściwej kolumnie) — zapisz oryginał
                # do UserRole, żeby `_selected_version_id` mógł sobie poradzić.
                item.setData(Qt.UserRole, value)
        else:
            item.setData(Qt.UserRole, value)
        table.setItem(row, col, item)

    @staticmethod
    def _clear_table(table):
        """Krótka helper-funkcja — zeruje wiersze tabeli (nagłówki zostają).

        Używane gdy reset stanu UI bez przebudowy widget-a.
        """
        table.setRowCount(0)
