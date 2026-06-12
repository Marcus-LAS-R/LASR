"""Główny dialog wtyczki — wybór bazy, uruchamianie F1–F4, rollback, historia.

Pojedyncze okno z całym workflowem (zgodnie z decyzją projektową — jeden
dialog z 5 przyciskami zamiast 4 osobnych wpisów w menu QGIS).

Układ
-----
* **Pole `.mdb`** + przycisk „Wybierz…" — `QFileDialog`. Po wyborze pliku
  automatycznie ładuje etykietę „Wersja bazy: …" (zapytanie do
  `_LRT_VERSIONS`, jeśli istnieje).
* **Notatka** — opcjonalny tekst lądujący w `_LRT_VERSIONS.USER_NOTE` dla
  bieżącej operacji (kontekst audytowy, np. „test po Jankowicach").
* **Dry-run** — domyślnie WŁĄCZONY. Operacje są nieodwracalne na realnej
  bazie, więc świadomie wymuszamy „najpierw symulacja". Klient wyłącza
  checkbox dopiero gdy raport wygląda OK.
* **4 przyciski F1/F2/F3/F4** — uruchamiają odpowiedni moduł z `core/*`.
* **„Historia / przegląd wersji…"** — otwiera `VersionBrowserDialog` z
  pełnym widokiem `_LRT_VERSIONS` + snapshotów + historii rekordu.
* **„Rollback wersji…"** — szybki dropdown do cofnięcia konkretnej wersji
  (alternatywa: można otworzyć Historię i też zrobić rollback z niej —
  tutaj zostaje dla szybkiego dostępu).

Cykl pracy z połączeniem DB
---------------------------
Każde wywołanie tworzy ŚWIEŻE połączenie i zamyka je w `finally`. Powód:
operacje mogą trwać sekundy/minuty, a w tym czasie inny proces może
chcieć dotknąć pliku — trzymanie persistent connection w dialogu
prowadziłoby do locków. Koszt re-connect-u jest pomijalny przy Access.
"""

import os
import shutil
from datetime import datetime

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QGroupBox,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout,
)

from ..core import f1_aktualizacja, f2_uzupelnienie, f3_korekta_masy, f4_korekta_bhd
from ..core.db import connect
from ..core.versioning import VersionManager
from .version_browser import VersionBrowserDialog


# Mapowanie label widoczny w UI → moduł `core` z funkcją `run(...)`.
# Tablica zamiast if/elif — łatwiej dodać kolejną operację (gdyby kiedyś
# pojawiła się F5: wystarczy importować moduł i dorzucić wpis).
OPERATIONS = [
    ("F1 — Aktualizacja +10 lat", f1_aktualizacja),
    ("F2 — Uzupełnienie wymiarów d-stanu", f2_uzupelnienie),
    ("F3 — Korekta masy wg zadrzewienia", f3_korekta_masy),
    ("F4 — Korekta BHD < HEIGHT", f4_korekta_bhd),
]


def _backup_mdb(mdb_path, operation):
    """Kopiuje plik MDB obok oryginału z sufiksem `_OP_YYYY-MM-DD_HH-MM-SS`.

    Wywoływane przed każdym COMMIT-em F1–F4 (dry-run pomijany). Jeśli klient
    zgubi rollback albo coś pójdzie nie tak, ma pełny plik sprzed operacji.

    Args:
        mdb_path: Ścieżka oryginalnego pliku .mdb / .accdb.
        operation: Kod operacji (`F1`/`F2`/`F3`/`F4`) — pochodzi z
            `module.OPERATION`.

    Returns:
        Ścieżka utworzonej kopii.
    """
    base, ext = os.path.splitext(mdb_path)
    ts = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    backup_path = f"{base}_{operation}_{ts}{ext}"
    shutil.copy2(mdb_path, backup_path)
    return backup_path


class MainDialog(QDialog):
    """Okno modalne — wszystkie operacje wtyczki w jednym miejscu.

    Cykl życia: instancja jest tworzona przez `LasRToolPlugin.run()` raz na
    kliknięcie akcji w QGIS. Pokazujemy modalnie (`exec_()`) i zamykamy.

    Attributes:
        config: Załadowana konfiguracja (`Config`).
        mdb_edit: Pole tekstowe ze ścieżką wybranego pliku (read-only).
        current_version_label: Etykieta „Wersja bazy: …".
        note_edit: Pole notatki użytkownika.
        dry_run: Checkbox — True przed commitem na realnej bazie.
    """

    def __init__(self, config, parent=None):
        """Konstruktor — buduje UI od razu (Qt-pattern).

        Args:
            config: Instancja `Config` — przekazywana dalej do operacji.
            parent: QWidget rodzic (zwykle `iface.mainWindow()`).
        """
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("LAS_R_TOOL")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self):
        """Tworzy widget-y i pakuje je w layout pionowy.

        Trzymane w osobnej metodzie żeby konstruktor pozostał czytelny.
        Wszystkie sygnał-slot przypięcia są tu — łatwiej audytować jednym
        spojrzeniem co reaguje na co.
        """
        layout = QVBoxLayout(self)

        # ---- wiersz wyboru pliku MDB ----------------------------------------
        layout.addWidget(QLabel("Plik bazy .mdb:"))
        mdb_row = QHBoxLayout()
        self.mdb_edit = QLineEdit()
        self.mdb_edit.setReadOnly(True)  # ścieżka tylko przez file dialog — brak literówek
        browse_btn = QPushButton("Wybierz…")
        browse_btn.clicked.connect(self._browse)
        mdb_row.addWidget(self.mdb_edit, 1)
        mdb_row.addWidget(browse_btn)
        layout.addLayout(mdb_row)

        self.dry_run = QCheckBox("Dry-run (bez zapisu i bez snapshotu)")
        self.dry_run.setChecked(False)
        layout.addWidget(self.dry_run)

        # ---- 4 przyciski operacji w QGroupBox -------------------------------
        ops_box = QGroupBox("Operacje")
        ops_layout = QVBoxLayout(ops_box)
        for label, module in OPERATIONS:
            btn = QPushButton(label)
            # Domyślne argumenty lambdy (`m=module, l=label`) — kluczowe!
            # Inaczej wszystkie przyciski przejęłyby ostatnią parę z pętli
            # (problem closure'a w pętli Pythona).
            btn.clicked.connect(lambda _checked, m=module, l=label: self._run_operation(m, l))
            ops_layout.addWidget(btn)
        layout.addWidget(ops_box)

        # ---- przyciski historii i rollback ----------------------------------
        history_btn = QPushButton("Historia / przegląd wersji…")
        history_btn.clicked.connect(self._open_history)
        layout.addWidget(history_btn)

        rollback_btn = QPushButton("Rollback wersji…")
        rollback_btn.clicked.connect(self._rollback)
        layout.addWidget(rollback_btn)

        # ---- przycisk Zamknij -----------------------------------------------
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---- handlers wyboru pliku ----------------------------------------------

    def _browse(self):
        """Handler „Wybierz…" — `QFileDialog` + odświeżenie etykiety wersji.

        Filtr na *.mdb i *.accdb (klient ma stare bazy w obu formatach,
        sterownik Access ODBC obsługuje oba). Ostatnio wybrany plik jest
        zapamiętywany w QSettings i ustawiany jako punkt startowy dialogu.
        """
        settings = QSettings("LAS_R", "LAS_R_TOOL")
        last_dir = settings.value("last_mdb_dir", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik MDB", last_dir, "MDB files (*.mdb *.accdb)"
        )
        if path:
            settings.setValue("last_mdb_dir", os.path.dirname(path))
            self.mdb_edit.setText(path)

    def _mdb_path(self):
        """Zwraca ścieżkę z `mdb_edit` po walidacji, lub None z ostrzeżeniem.

        Wspólny prolog wszystkich akcji wymagających bazy — eliminuje
        powielenie sprawdzeń.

        Returns:
            String ze ścieżką (po sprawdzeniu, że plik istnieje) lub None
            gdy pole jest puste / plik nie istnieje.
        """
        path = self.mdb_edit.text().strip()
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "Brak pliku", "Najpierw wybierz istniejący plik .mdb.")
            return None
        return path

    # ---- handler uruchomienia operacji F1–F4 --------------------------------

    def _run_operation(self, module, label):
        """Wykonuje jedną z operacji F1–F4 — wspólna ścieżka dla każdego przycisku.

        Algorytm:

        1. Sprawdź ścieżkę pliku.
        2. Pobierz tryb (dry-run vs commit). Jeśli commit — wymagaj
           potwierdzenia w `QMessageBox` (zmiana nieodwracalna bez rollbacku).
        3. Otwórz połączenie. Błąd → `QMessageBox.critical` i koniec.
        4. Wywołaj `module.run(conn, config, mdb_path, dry_run, user_note)`.
           Wyjątek → `conn.rollback()`, komunikat błędu, koniec.
        5. Zamknij połączenie w `finally`.
        6. Pokaż podsumowanie raportu w `QMessageBox`.
        7. Odśwież etykietę wersji bazy (po commicie może być nowa wersja).

        Args:
            module: Moduł z `core/*` z funkcją `run(...)`.
            label: Tekst przycisku — do tytułu komunikatów i potwierdzenia.
        """
        mdb_path = self._mdb_path()
        if mdb_path is None:
            return
        dry_run = self.dry_run.isChecked()
        if not dry_run:
            confirm = QMessageBox.question(
                self, "Potwierdzenie",
                f"Tryb COMMIT: zmiany zostaną zapisane do bazy.\n\nUruchomić {label}?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return

        try:
            backup_path = _backup_mdb(mdb_path, module.OPERATION)
        except Exception as e:
            QMessageBox.critical(self, "Błąd kopii bezpieczeństwa", str(e))
            return

        note = ""
        try:
            conn = connect(mdb_path)
        except Exception as e:
            QMessageBox.critical(self, "Błąd połączenia", str(e))
            return

        try:
            if module is f1_aktualizacja:
                prior = None
                try:
                    check_conn = connect(mdb_path)
                    prior = f1_aktualizacja.prior_run(check_conn, self.config)
                except Exception:
                    pass
                finally:
                    try:
                        check_conn.close()
                    except Exception:
                        pass
                if prior:
                    ts = prior["timestamp"]
                    who = prior["user_note"] or "—"
                    answer = QMessageBox.question(
                        self, "F1 już uruchomiona",
                        f"F1 była już uruchomiona na tej bazie:\n"
                        f"  Kiedy: {ts}\n"
                        f"  Przez: {who}\n\n"
                        f"Uruchomić ponownie?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if answer != QMessageBox.Yes:
                        return
            report = module.run(conn, self.config, mdb_path, dry_run=dry_run, user_note=note)
        except Exception as e:
            # Cokolwiek poszło źle wewnątrz operacji — wycofujemy transakcję.
            # Bez tego częściowy commit zostawiłby bazę w niespójnym stanie.
            conn.rollback()
            QMessageBox.critical(self, f"Błąd {label}", str(e))
            return
        finally:
            conn.close()

        self._show_report_summary(label, report, backup_path)

    def _show_report_summary(self, label, report, backup_path=None):
        """Pokazuje krótkie podsumowanie raportu (pełny plik .txt jest obok bazy).

        Args:
            label: Tekst przycisku — do tytułu okna.
            report: Instancja `Report` zwrócona z operacji.
            backup_path: Ścieżka kopii bezpieczeństwa (None dla dry-run).
        """
        msg = (
            f"{label} ({'dry-run' if report.dry_run else 'commit'})\n"
            f"Przetworzono: {report.processed}\n"
            f"Zmieniono: {report.changed}\n"
            f"Pominięto: {len(report.skipped)}"
        )
        if report.fallback_ones:
            msg += f"\nUzupełniono wartością 1: {len(report.fallback_ones)}"
        if report.anomaly_bhd:
            msg += f"\nAnomalie BHD (candidate >= 2x HEIGHT): {len(report.anomaly_bhd)}"
        if report.version_id is not None:
            msg += f"\nVERSION_ID: {report.version_id}"
        if backup_path is not None:
            msg += f"\nKopia bezpieczeństwa: {os.path.basename(backup_path)}"
        QMessageBox.information(self, "Raport", msg)
        if report.report_path and os.path.isfile(report.report_path):
            answer = QMessageBox.question(
                self, "Raport TXT",
                "Czy chcesz otworzyć plik raportu?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                os.startfile(report.report_path)

    # ---- handlery historii i rollback ---------------------------------------

    def _open_history(self):
        """Otwiera okno `VersionBrowserDialog` z pełną historią wersji.

        Tworzy `VersionManager` na świeżym połączeniu i przekazuje do
        dialogu. Po zamknięciu okna (`exec_` wraca) — zamykamy połączenie
        i odświeżamy etykietę (operator mógł zrobić rollback z poziomu
        Historii).
        """
        mdb_path = self._mdb_path()
        if mdb_path is None:
            return
        try:
            conn = connect(mdb_path)
        except Exception as e:
            QMessageBox.critical(self, "Błąd połączenia", str(e))
            return
        try:
            manager = VersionManager(conn, self.config)
            dialog = VersionBrowserDialog(manager, parent=self)
            dialog.exec_()
        finally:
            conn.close()

    def _rollback(self):
        """Szybki rollback — dropdown z listą wersji bez otwierania pełnej Historii.

        Algorytm:

        1. Wczytaj listę wersji (`list_versions`).
        2. Brak wersji → informacja i koniec.
        3. `QInputDialog.getItem` z listą napisów typu
           `V{id} — {op} — {ts} — rows={n} — {status}` (sortowane DESC
           bo `list_versions` tak zwraca).
        4. Potwierdzenie (drugi `QMessageBox`).
        5. `manager.rollback(version_id, user_note)`.
        6. Komunikat z liczbą cofniętych pól.
        7. Odświeżenie etykiety wersji.
        """
        mdb_path = self._mdb_path()
        if mdb_path is None:
            return
        try:
            conn = connect(mdb_path)
        except Exception as e:
            QMessageBox.critical(self, "Błąd połączenia", str(e))
            return

        try:
            manager = VersionManager(conn, self.config)
            versions = manager.list_versions()
            if not versions:
                QMessageBox.information(self, "Rollback", "Brak zapisanych wersji w tej bazie.")
                return
            choices = [
                f"V{v['version_id']} — {v['operation']} — {v['timestamp']} — "
                f"rows={v['affected_rows']} — {v['status']}"
                for v in versions
            ]
            choice, ok = QInputDialog.getItem(
                self, "Wybierz wersję do cofnięcia", "Wersja:", choices, 0, False
            )
            if not ok:
                return
            # Mapujemy zaznaczony tekst z powrotem na `version_id` przez indeks
            # w liście (zawsze 1:1 odpowiada `versions`).
            version_id = versions[choices.index(choice)]["version_id"]
            confirm = QMessageBox.question(
                self, "Potwierdź rollback",
                f"Cofnąć wersję V{version_id}?\n(Operacja sama zapisze snapshot ROLLBACK.)",
                QMessageBox.Yes | QMessageBox.No,
            )
            if confirm != QMessageBox.Yes:
                return
            count = manager.rollback(version_id, user_note="")
            QMessageBox.information(self, "Rollback", f"Cofnięto {count} pól w wersji V{version_id}.")
        except Exception as e:
            conn.rollback()
            QMessageBox.critical(self, "Błąd rollback", str(e))
        finally:
            conn.close()
