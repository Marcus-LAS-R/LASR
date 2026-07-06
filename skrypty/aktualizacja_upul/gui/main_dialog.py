"""Główny dialog wtyczki — wybór bazy, uruchamianie F1–F4.

Pojedyncze okno z całym workflowem (zgodnie z decyzją projektową — jeden
dialog zamiast 4 osobnych wpisów w menu QGIS).

Układ
-----
* **Pole `.mdb`** + przycisk „Wybierz…" — `QFileDialog`. Po wyborze pliku
  automatycznie ładuje etykietę „Wersja bazy: …" (zapytanie do
  `_LRT_VERSIONS`, jeśli istnieje).
* **Notatka** — opcjonalny tekst lądujący w `_LRT_VERSIONS.USER_NOTE` dla
  bieżącej operacji (kontekst audytowy, np. „test po Jankowicach").
* **4 przyciski F1/F2/F3/F4** — uruchamiają odpowiedni moduł z `core/*`,
  zawsze w trybie commit (z potwierdzeniem przed zapisem) — kopia
  bezpieczeństwa pliku .mdb (`_backup_mdb`, do `Kopie_manipulacyjne/` obok
  bazy — ten sam wzorzec co inne operacje niszczące w tej wtyczce) powstaje
  przed każdą operacją.

Cykl pracy z połączeniem DB
---------------------------
Każde wywołanie tworzy ŚWIEŻE połączenie i zamyka je w `finally`. Powód:
operacje mogą trwać sekundy/minuty, a w tym czasie inny proces może
chcieć dotknąć pliku — trzymanie persistent connection w dialogu
prowadziłoby do locków. Koszt re-connect-u jest pomijalny przy Access.
"""

import os

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout,
)

from ..core import f1_aktualizacja, f2_uzupelnienie, f3_korekta_masy, f4_korekta_bhd
from ..core.db import connect
from ... import kopie_manipulacyjne


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
    """Kopiuje plik MDB do Kopie_manipulacyjne/ - ten sam wzorzec kopii
    bezpieczeństwa co inne operacje niszczące w tej wtyczce, patrz
    `kopie_manipulacyjne.zrob_kopie_manipulacyjna`.

    Wywoływane przed każdym uruchomieniem F1–F4. Jeśli coś pójdzie nie
    tak, ma pełny plik sprzed operacji.

    Args:
        mdb_path: Ścieżka oryginalnego pliku .mdb / .accdb.
        operation: Kod operacji (`F1`/`F2`/`F3`/`F4`) — pochodzi z
            `module.OPERATION`.

    Returns:
        Ścieżka do utworzonego folderu kopii, albo None przy błędzie.
    """
    return kopie_manipulacyjne.zrob_kopie_manipulacyjna(mdb_path, [], operation)


class MainDialog(QDialog):
    """Okno modalne — wszystkie operacje wtyczki w jednym miejscu.

    Cykl życia: instancja jest tworzona przez `LasRToolPlugin.run()` raz na
    kliknięcie akcji w QGIS. Pokazujemy modalnie (`exec_()`) i zamykamy.

    Attributes:
        config: Załadowana konfiguracja (`Config`).
        mdb_edit: Pole tekstowe ze ścieżką wybranego pliku (read-only).
        current_version_label: Etykieta „Wersja bazy: …".
        note_edit: Pole notatki użytkownika.
    """

    def __init__(self, config, parent=None):
        """Konstruktor — buduje UI od razu (Qt-pattern).

        Args:
            config: Instancja `Config` — przekazywana dalej do operacji.
            parent: QWidget rodzic (zwykle `iface.mainWindow()`).
        """
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Aktualizacja bazy UPUL")
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
        settings = QSettings("LAS_R", "AktualizacjaBazyUPUL")
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
        2. Wymagaj potwierdzenia w `QMessageBox` (zmiana zostanie
           zapisana do bazy na stałe — jedyne zabezpieczenie to kopia
           pliku .mdb tworzona przed operacją, patrz `_backup_mdb`).
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
        dry_run = False
        confirm = QMessageBox.question(
            self, "Potwierdzenie",
            f"Zmiany zostaną zapisane do bazy.\n\nUruchomić {label}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        backup_path = _backup_mdb(mdb_path, module.OPERATION)
        if backup_path is None:
            QMessageBox.critical(
                self, "Błąd kopii bezpieczeństwa",
                "Nie udało się utworzyć kopii bezpieczeństwa - przerwano, "
                "nic nie zmieniono.",
            )
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
            backup_path: Ścieżka folderu kopii bezpieczeństwa w
                Kopie_manipulacyjne/ (zawsze podana - operacja bez
                udanej kopii jest przerywana wcześniej).
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
            msg += f"\nKopia bezpieczeństwa: {backup_path}"
        QMessageBox.information(self, "Raport", msg)
        if report.report_path and os.path.isfile(report.report_path):
            answer = QMessageBox.question(
                self, "Raport TXT",
                "Czy chcesz otworzyć plik raportu?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                os.startfile(report.report_path)
